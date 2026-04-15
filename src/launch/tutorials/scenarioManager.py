import rclpy
from rclpy.node import Node
import json
import os
import random
import math
from geometry_msgs.msg import PoseStamped
from tf2_ros import TransformListener, Buffer

class ScenarioManager(Node):
    def __init__(self):
        super().__init__('scenario_manager')
        
        # Parameters
        self.declare_parameter('json_path', 'src/physics_connectors/Gazebo/worlds/world/target_points.json')
        self.declare_parameter('arrival_threshold', 2.0) # mètres
        
        # TF to follow the drone
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publisher for the current goal
        self.goal_pub = self.create_publisher(PoseStamped, '/current_goal', 10)
        
        # Loading the waypoints from the JSON file
        path = self.get_parameter('json_path').get_parameter_value().string_value
        if not os.path.isfile(path):
            self.get_logger().error(f"JSON file doesn't exist: {path}")
            rclpy.shutdown()
            return

        with open(path, 'r') as f:
            self.waypoints = json.load(f)
        
        self.current_waypoint = None
        self.select_new_goal()
        
        # Timer to check the distance (10Hz)
        self.timer = self.create_timer(0.1, self.control_loop)

    def select_new_goal(self):
        # Select a new random waypoint different from the current one
        new_wp = random.choice(self.waypoints)
        while len(self.waypoints) > 1 and new_wp == self.current_waypoint:
            new_wp = random.choice(self.waypoints)
            
        self.current_waypoint = new_wp
        self.get_logger().info(f"Nouvel objectif : {new_wp['name']} ({new_wp["position"]['x']}, {new_wp["position"]['y']})")

    def control_loop(self):
        # 1. Publish current goal
        goal_msg = PoseStamped()
        goal_msg.header.stamp = self.get_clock().now().to_msg()
        goal_msg.header.frame_id = 'world'
        goal_msg.pose.position.x = float(self.current_waypoint["position"]['x'])
        goal_msg.pose.position.y = float(self.current_waypoint["position"]['y'])
        goal_msg.pose.position.z = float(self.current_waypoint["position"]['z'])
        self.goal_pub.publish(goal_msg)

        # 2. Check the drone's position via TF
        try:
            # Listen to the frame of the drone into the world
            now = rclpy.time.Time()
            trans = self.tf_buffer.lookup_transform(
                'world', 
                'x500_lidar_2d_0/link/base_link', 
                now)
            
            dx = trans.transform.translation.x - self.current_waypoint["position"]['x']
            dy = trans.transform.translation.y - self.current_waypoint["position"]['y']
            distance = math.sqrt(dx**2 + dy**2)

            if distance < self.get_parameter('arrival_threshold').get_parameter_value().double_value:
                self.get_logger().info("Cible atteinte !")
                self.select_new_goal()

        except Exception as e:
            # TF peut mettre quelques secondes à démarrer au début
            pass

def main(args=None):
    rclpy.init(args=args)
    node = ScenarioManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()