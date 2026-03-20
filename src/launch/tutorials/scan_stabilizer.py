import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy
import tf2_ros
import tf_transformations
import math
import numpy as np
from copy import deepcopy

class ScanStabilizer(Node):
    def __init__(self):
        super().__init__('scan_stabilizer')

        self.declare_parameter('z_threshold', 0.15)
        self.declare_parameter('target_frame', 'world')

        # Paramètres
        self.target_frame = self.get_parameter('target_frame').value
        self.robot_frame = 'x500_lidar_2d_0/link/base_link'
        self.z_threshold = self.get_parameter('z_threshold').value # Tolérance de 15cm pour filtrer le sol

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Gestion de la QoS incompatible
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
            tf = self.tf_buffer.lookup_transform('world', msg.header.frame_id, msg.header.stamp)
        except Exception: return

        pos_drone = np.array([tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z])
        mat_rot = tf_transformations.quaternion_matrix([tf.transform.rotation.x, tf.transform.rotation.y, 
                                                        tf.transform.rotation.z, tf.transform.rotation.w])

        new_ranges = [float('inf')] * len(msg.ranges)

        #yaw_drone = math.atan2(mat_rot[1, 0], mat_rot[0, 0])
        _, _, yaw_drone = tf_transformations.euler_from_quaternion([
                tf.transform.rotation.x,
                tf.transform.rotation.y,
                tf.transform.rotation.z,
                tf.transform.rotation.w
            ])
        
        for i, r in enumerate(msg.ranges):
            if math.isinf(r) or r < msg.range_min: continue

            # 1. Position du point dans le repère Monde (Calcul complet)
            angle = msg.angle_min + i * msg.angle_increment
            P_lidar = np.array([r * math.cos(angle), r * math.sin(angle), 0.0, 1.0])
            P_world = (mat_rot @ P_lidar)[:3] + pos_drone

            # 3. CALCUL DE LA POSITION RELATIVE STABILISÉE
            # On cherche les coordonnées (x, y) du point par rapport au drone dans le plan World
            dx = P_world[0] - pos_drone[0]
            dy = P_world[1] - pos_drone[1]

            # 2. FILTRE SOL (Z-check)
            if P_world[2] > self.z_threshold:
                # 4. DISTANCE ET ANGLE RÉELS (Projetés)
                dist_horiz = math.sqrt(dx**2 + dy**2)
                angle_world = math.atan2(dy, dx) 

                # 5. RE-INDEXATION RELATIVE AU YAW DU DRONE
                # On ramène l'angle monde dans le référentiel local du drone (angle 0 = devant)
                angle_relatif = angle_world - yaw_drone
                
                # Normalisation entre -pi et pi (Wrap to pi)
                angle_relatif = math.atan2(math.sin(angle_relatif), math.cos(angle_relatif))

                # Calcul de l'index dans le repère du message LaserScan
                index = int((angle_relatif - msg.angle_min) / msg.angle_increment)
                
                # Gestion des bords du tableau
                if 0 <= index < len(new_ranges):
                    new_ranges[index] = min(new_ranges[index], dist_horiz)
                #new_ranges[i] = min(new_ranges[index], dist_horiz)

        # 4. ENVOI AVEC LA FRAME STABILISÉE
        out = deepcopy(msg)
        out.header.frame_id = "x500_lidar_2d_0/link/base_link_stabilized" # Nom de la frame créée dans le relay
        out.ranges = new_ranges
        self.pub.publish(out)


def main():
    rclpy.init()
    node = ScanStabilizer()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()