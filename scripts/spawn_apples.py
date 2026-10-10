#!/usr/bin/env python3
"""
Batch-spawn apples onto tree crowns in the orchard world.

Design intent (Module 1 -> Module 3 handoff):
  - Apples are DYNAMIC, pickable entities (see model/apple_model/model.sdf).
  - They are NOT written into the world file, so they can later be removed
    one-by-one via the /delete_entity service to simulate "picking".
  - Tree base positions MUST match model/myworld_orchard.sdf include poses.
  - Crown center is at z=1.55 (radius 0.65) in tree_model. Apples are placed
    in the lower-mid crown so they read as "hanging on the tree".

Run: python3 spawn_apples.py   (after gzserver + /spawn_entity are up)
"""
import os
import time
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity
from geometry_msgs.msg import Pose, Quaternion

# Tree base (x, y) in world frame - keep in sync with myworld_orchard.sdf
TREES = [
    (6, 4), (12, 4), (18, 4),
    (9, 0), (15, 0), (21, 0),
    (6, -4), (12, -4), (18, -4),
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

        self.cli = self.create_client(SpawnEntity, '/spawn_entity')
        self.get_logger().info('apple_spawner node started, ready to spawn %d apples'
                               % (len(TREES) * len(APPLE_OFFSETS)))

    def wait_service(self, timeout=30.0):
        start = time.time()
        while not self.cli.wait_for_service(timeout_sec=1.0):
            if time.time() - start > timeout:
                self.get_logger().error('/spawn_entity unavailable, aborting')
                return False
            self.get_logger().info('waiting for /spawn_entity ...')
        return True

    def spawn_all(self):
        if not self.wait_service():
            return
        idx = 1
        for (tx, ty) in TREES:
            for (dx, dy, dz) in APPLE_OFFSETS:
                name = 'apple_%02d' % idx
                x = float(tx + dx)
                y = float(ty + dy)
                z = float(dz)
                # make the embedded model name unique to avoid SDF name clashes
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
                    fut = self.cli.call_async(req)
                    rclpy.spin_until_future_complete(self, fut, timeout_sec=5.0)
                    if fut.result() is not None:
                        self.get_logger().info(
                            'spawned %s @ (%.2f, %.2f, %.2f): %s'
                            % (name, x, y, z, fut.result().status_message))
                    else:
                        self.get_logger().error('spawn %s returned no result' % name)
                except Exception as e:  # noqa: BLE001
                    self.get_logger().error('error spawning %s: %s' % (name, e))
                idx += 1
        self.get_logger().info('all apple spawn requests sent')


def main(args=None):
    rclpy.init(args=args)
    node = AppleSpawner()
    node.spawn_all()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
