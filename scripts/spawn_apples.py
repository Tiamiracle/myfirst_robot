#!/usr/bin/env python3
"""
Batch-spawn apples onto tree crowns and ATTACH them to prevent falling.

Design intent (Module 1 -> Module 3 handoff):
  - Apples are DYNAMIC, pickable entities (see model/apple_model/model.sdf).
  - After spawning, each apple is ATTACHED to the parent tree's tree_canopy
    via gazebo_ros_link_attacher, so it won't fall due to gravity.
  - During picking: call /detach first, then grab/remove the apple.
  - Tree base positions MUST match model/myworld_orchard.sdf include poses.
  - Crown center is at z=1.55 (radius 0.65) in tree_model.

Run: python3 spawn_apples.py   (after gzserver + /spawn_entity + /attach are up)
"""
import os
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from gazebo_msgs.srv import SpawnEntity
from geometry_msgs.msg import Pose, Quaternion

# Tree info: (tree_name, x, y) - names must match myworld_orchard.sdf <name> tags
TREES = [
    ('tree_01', 6, 4), ('tree_02', 12, 4), ('tree_03', 18, 4),
    ('tree_04', 9, 0), ('tree_05', 15, 0), ('tree_06', 21, 0),
    ('tree_07', 6, -4), ('tree_08', 12, -4), ('tree_09', 18, -4),
]

# Per-tree apple offsets (dx, dy, dz) relative to tree base, within crown
APPLE_OFFSETS = [
    (0.20, 0.15, 1.42),
    (-0.18, 0.22, 1.62),
    (0.12, -0.22, 1.52),
]


class AppleSpawner(Node):
    def __init__(self):
        super().__init__('apple_spawner')
        here = os.path.dirname(os.path.abspath(__file__))
        share = os.path.dirname(here)  # share/myfirst_robot
        apple_sdf_path = os.path.join(share, 'model', 'apple_model', 'model.sdf')
        with open(apple_sdf_path, 'r') as f:
            self.apple_sdf = f.read()

        # Spawn entity client
        self.spawn_cli = self.create_client(SpawnEntity, '/spawn_entity')
        # Attach client - gazebo_ros_link_attacher provides /attach service
        self.attach_cli = self.create_client(SpawnEntity, '/attach')

        self.get_logger().info('apple_spawner node started, ready to spawn %d apples'
                               % (len(TREES) * len(APPLE_OFFSETS)))

    def wait_services(self, timeout=30.0):
        """Wait for both /spawn_entity and /attach services."""
        start = time.time()
        spawn_ready = False
        attach_ready = False

        while not (spawn_ready and attach_ready):
            if time.time() - start > timeout:
                self.get_logger().error('Services unavailable after %.1fs, aborting' % timeout)
                return False

            if not spawn_ready:
                if self.spawn_cli.wait_for_service(timeout_sec=0.5):
                    spawn_ready = True
                    self.get_logger().info('/spawn_entity ready')
                else:
                    self.get_logger().info('waiting for /spawn_entity ...')

            if not attach_ready:
                if self.attach_cli.wait_for_service(timeout_sec=0.5):
                    attach_ready = True
                    self.get_logger().info('/attach ready')
                else:
                    self.get_logger().info('waiting for /attach ...')

        return True

    def spawn_all(self):
        if not self.wait_services():
            return

        # Brief pause to let physics settle before attaching
        time.sleep(0.3)

        idx = 1
        success_count = 0
        for (tree_name, tx, ty) in TREES:
            for (dx, dy, dz) in APPLE_OFFSETS:
                name = 'apple_%02d' % idx
                x = float(tx + dx)
                y = float(ty + dy)
                z = float(dz)

                # === Step 1: Spawn the apple ===
                sdf = self.apple_sdf.replace(
                    '<model name="apple">', '<model name="%s">' % name, 1)

                req = SpawnEntity.Request()
                req.name = name
                req.xml = sdf
                req.robot_namespace = ''
                req.initial_pose = Pose()
                req.initial_pose.position.x = x
                req.initial_pose.position.y = y
                req.initial_pose.position.z = z
                req.initial_pose.orientation = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
                req.reference_frame = 'world'

                try:
                    fut = self.spawn_cli.call_async(req)
                    rclpy.spin_until_future_complete(self, fut, timeout_sec=5.0)
                    if fut.result() is None:
                        self.get_logger().error('spawn %s: no result' % name)
                        idx += 1
                        continue
                    if fut.result().success is False:
                        self.get_logger().warn('spawn %s failed: %s' % (name, fut.result().status_message))
                        idx += 1
                        continue
                except Exception as e:  # noqa: BLE001
                    self.get_logger().error('spawn %s error: %s' % (name, e))
                    idx += 1
                    continue

                # === Step 2: Attach apple body to tree canopy (prevent falling) ===
                # The /attach service from gazebo_ros_link_attacher accepts an XML
                # string specifying model_name_1/link_name_1 <-> model_name_2/link_name_2
                attach_xml = (
                    '<?xml version="1.0"?>'
                    '<request>'
                    '  <model_name_1>%s</model_name_1>'
                    '  <link_name_1>apple_body</link_name_1>'
                    '  <model_name_2>%s</model_name_2>'
                    '  <link_name_2>tree_canopy</link_name_2>'
                    '</request>'
                ) % (name, tree_name)

                attach_req = SpawnEntity.Request()
                attach_req.name = '%s_attach' % name
                attach_req.xml = attach_xml
                attach_req.robot_namespace = ''
                attach_req.reference_frame = 'world'

                try:
                    fut2 = self.attach_cli.call_async(attach_req)
                    rclpy.spin_until_future_complete(self, fut2, timeout_sec=5.0)
                    if fut2.result() is not None:
                        self.get_logger().info(
                            'OK %s -> %s (attached)' % (name, tree_name))
                        success_count += 1
                    else:
                        self.get_logger().warn('attach %s: no response' % name)
                except Exception as e:  # noqa: BLE001
                    self.get_logger().warn('attach %s error: %s' % (name, e))

                idx += 1

        self.get_logger().info(
            '=== Done: %d/%d apples spawned and attached ==='
            % (success_count, len(TREES) * len(APPLE_OFFSETS)))


def main(args=None):
    rclpy.init(args=args)
    node = AppleSpawner()
    node.spawn_all()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
