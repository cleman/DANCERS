#!/usr/bin/env python3
"""
gz_pose_relay.py

Subscribes DIRECTLY to the Gazebo transport topic /world/default/pose/info
(no ros_gz_bridge needed) using gz-transport Python bindings.

Extracts the pose of a target model by name and publishes it as a TF
transform on /tf in the ROS 2 environment.

Requirements:
  - ROS 2 (Humble or later)
  - Gazebo Harmonic (gz-transport 13 + gz-msgs 11)
      └─ adjust version suffixes below for other Gazebo releases:
         Fortress  → gz.transport10 / gz.msgs8
         Garden    → gz.transport12 / gz.msgs9
         Ionic     → gz.transport14 / gz.msgs12
  - tf2_ros

Run:
  ros2 run <your_package> gz_pose_relay
  # or with overrides:
  ros2 run <your_package> gz_pose_relay --ros-args \
      -p target_model:=x500_lidar_2d_0 \
      -p parent_frame:=world \
      -p child_frame:=x500_lidar_2d_0/base_link \
      -p gz_world:=default
"""

import threading

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

from gz.transport14 import Node as GzNode   # was transport13
from gz.msgs.pose_v_pb2 import Pose_V
import math

class GzPoseRelay(Node):

    def __init__(self):
        super().__init__('gz_pose_relay')

        # ── ROS 2 parameters ──────────────────────────────────────────────────
        self.declare_parameter('target_model', 'x500_lidar_2d_0')
        self.declare_parameter('parent_frame',  'world')
        self.declare_parameter('child_frame',   'x500_lidar_2d_0/link/base_link')
        self.declare_parameter('gz_world',      'default')

        self.target_model = self.get_parameter('target_model').value
        self.parent_frame  = self.get_parameter('parent_frame').value
        self.child_frame   = self.get_parameter('child_frame').value
        gz_world           = self.get_parameter('gz_world').value

        gz_topic = f'/world/{gz_world}/pose/info'

        # ── TF broadcaster ────────────────────────────────────────────────────
        self.tf_broadcaster = TransformBroadcaster(self)

        # ── gz-transport subscriber ───────────────────────────────────────────
        # GzNode.subscribe() is thread-safe; the callback fires on a gz
        # internal thread, so we guard TF publishing with a lock.
        self._lock = threading.Lock()
        self._gz_node = GzNode()

        ok = self._gz_node.subscribe(Pose_V, gz_topic, self._gz_pose_cb)
        if not ok:
            self.get_logger().error(
                f"Failed to subscribe to gz topic '{gz_topic}'. "
                "Is Gazebo running and reachable?"
            )
        else:
            self.get_logger().info(
                f"Subscribed to gz topic '{gz_topic}' directly (no bridge). "
                f"Relaying '{self.target_model}' as TF "
                f"[{self.parent_frame} → {self.child_frame}]"
            )

    # ── gz callback (runs on gz-transport internal thread) ────────────────────
    def _gz_pose_cb(self, msg: Pose_V) -> None:
        """
        gz.msgs.Pose_V protobuf layout:
            Header  header
                Time stamp        (sec, nsec)
            repeated Pose pose[]
                string  name
                uint32  id
                Vector3d position  (x, y, z)
                Quaternion orientation (x, y, z, w)
        """
        for p in msg.pose:
            if p.name != self.target_model:
                continue

            # --- TF Réelle ---
            t = TransformStamped()
            t.header.stamp.sec     = msg.header.stamp.sec
            t.header.stamp.nanosec = msg.header.stamp.nsec
            t.header.frame_id      = self.parent_frame
            t.child_frame_id       = self.child_frame

            t.transform.translation.x = p.position.x
            t.transform.translation.y = p.position.y
            t.transform.translation.z = p.position.z

            t.transform.rotation.x = p.orientation.x
            t.transform.rotation.y = p.orientation.y
            t.transform.rotation.z = p.orientation.z
            t.transform.rotation.w = p.orientation.w

            with self._lock:
                self.tf_broadcaster.sendTransform(t)
            
            # --- TF Stabilisée ---
            ts = TransformStamped()
            ts.header.stamp = t.header.stamp
            ts.header.frame_id = self.parent_frame
            ts.child_frame_id = self.child_frame + "_stabilized" # ex: .../base_link_stabilized

            ts.transform.translation = t.transform.translation # Même position

            # On annule Roll et Pitch, on ne garde que le Yaw
            # Pour cela, on convertit le quaternion en Euler, on reset, et on revient
            q = p.orientation
            # Calcul simplifié du Yaw uniquement à partir du quaternion
            siny_cosp = 2 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
            yaw = math.atan2(siny_cosp, cosy_cosp)

            # Nouveau quaternion (Rotation pure autour de Z)
            ts.transform.rotation.x = 0.0
            ts.transform.rotation.y = 0.0
            ts.transform.rotation.z = math.sin(yaw / 2)
            ts.transform.rotation.w = math.cos(yaw / 2)

            with self._lock:
                self.tf_broadcaster.sendTransform(ts)

            return  # stop after the first match

        self.get_logger().warn(
            f"Model '{self.target_model}' not found in pose/info message.",
            throttle_duration_sec=5.0,
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = GzPoseRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()