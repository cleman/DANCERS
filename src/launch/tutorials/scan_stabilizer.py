import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy
import tf2_ros
import tf_transformations
import numpy as np
from copy import deepcopy

def interpolate_small_gaps(ranges, max_gap=3):
        ranges = np.array(ranges)
        valid = np.isfinite(ranges)

        i = 0
        while i < len(ranges):
            if not valid[i]:
                start = i
                while i < len(ranges) and not valid[i]:
                    i += 1
                end = i

                if start > 0 and end < len(ranges):
                    if (end - start) <= max_gap:
                        ranges[start:end] = np.linspace(
                            ranges[start-1],
                            ranges[end],
                            end - start
                        )
            i += 1

        return ranges

class ScanStabilizer(Node):
    def __init__(self):
        super().__init__('scan_stabilizer')

        # Params
        self.declare_parameter('z_threshold', 0.15)
        self.z_threshold = self.get_parameter('z_threshold').value

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        #self.robot_frame = 'x500_lidar_2d_0/link/base_link'

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        self.sub = self.create_subscription(LaserScan, '/scan', self.callback, qos)
        self.pub = self.create_publisher(LaserScan, '/scan_stabilized', 10)

        self.add_on_set_parameters_callback(self.param_callback)


    def param_callback(self, params):
        for p in params:
            if p.name == 'z_threshold':
                self.z_threshold = p.value
        return rclpy.parameter.ParameterEventHandler()._result_successful()


    def callback(self, msg):
        try:
            # Drone dans le repère Monde
            tf = self.tf_buffer.lookup_transform(
                'world', 
                msg.header.frame_id, 
                rclpy.time.Time())
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}")
            return
        
        self.get_logger().info("TF OK")
        
        # --- Pose Drone ---
        pos = np.array([
            tf.transform.translation.x,
            tf.transform.translation.y,
            tf.transform.translation.z
        ])

        quat = [
            tf.transform.rotation.x,
            tf.transform.rotation.y,
            tf.transform.rotation.z,
            tf.transform.rotation.w
        ]
        
        mat_rot = tf_transformations.quaternion_matrix(quat)

        # Drone Yaw
        _, _, yaw_drone = tf_transformations.euler_from_quaternion(quat)
        
        # Data preparation
        ranges = np.array(msg.ranges)
        angles = msg.angle_min + np.arange(len(msg.ranges)) * msg.angle_increment
        
        # Filter valid ranges
        valid = np.isfinite(ranges) & (ranges > msg.range_min)
        self.get_logger().info(f"Points valides: {np.sum(valid)}/{len(ranges)}")
        if np.sum(valid) == 0:
            return
        
        ranges = ranges[valid]
        angles = angles[valid]

        # LiDAR points
        x = ranges * np.cos(angles)
        y = ranges * np.sin(angles)

        P_lidar = np.vstack((x, y, np.zeros_like(x), np.ones_like(x)))  # (4, N)

        # World projection
        P_world = (mat_rot @ P_lidar)[:3, :] + pos.reshape(3, 1)  # (3, N)

        # Z-filter
        z_cutoff = min(pos[2]-self.z_threshold, self.z_threshold)  # Seuil dynamique basé sur la hauteur du drone
        mask = P_world[2, :] > z_cutoff
        self.get_logger().info(f"Points au-dessus z_threshold ({z_cutoff}m): {np.sum(mask)}")
        if np.sum(mask) == 0:
            return
        
        P_world = P_world[:, mask]

        # Horizontal coordinates
        dx = P_world[0, :] - pos[0]
        dy = P_world[1, :] - pos[1]

        dist = np.sqrt(dx**2 + dy**2)
        angle_world = np.arctan2(dy, dx)

        # Relative angle
        angle_rel = angle_world - yaw_drone
        angle_rel = np.arctan2(np.sin(angle_rel), np.cos(angle_rel))

        # Indexation
        indices = ((angle_rel - msg.angle_min) / msg.angle_increment).astype(np.int32)

        valid_idx = (indices >= 0) & (indices < len(msg.ranges))
        indices = indices[valid_idx]
        dist = dist[valid_idx]

        # Scan reconstruction
        new_ranges = np.full(len(msg.ranges), np.inf)

        order = np.argsort(indices)
        indices_sorted = indices[order]
        dist_sorted = dist[order]

        unique_idx, first = np.unique(indices_sorted, return_index=True)
        new_ranges[unique_idx] = np.minimum.reduceat(dist_sorted, first)
        
        # Small gap interpolation
        new_ranges = interpolate_small_gaps(new_ranges, max_gap=3)

        # Publish
        out = deepcopy(msg)
        out.header.frame_id = "x500_lidar_2d_0/link/base_link_stabilized" # Nom de la frame créée dans le relay
        out.ranges = new_ranges.tolist()
        self.get_logger().info(f"Publication de {len(new_ranges)} ranges")
        self.pub.publish(out)


def main():
    rclpy.init()
    node = ScanStabilizer()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()