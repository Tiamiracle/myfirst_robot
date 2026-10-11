#!/usr/bin/env python3
"""
Batch-spawn apples onto tree crowns and ATTACH them via gazebo_ros_link_attacher.

Design intent (Module 1 -> Module 3 handoff):
  - Apples are DYNAMIC, real-physics entities (model/apple_model/model.sdf has
    mass + inertia + gravity, NO static, NO disabled gravity).
  - After spawning, each apple is PHYSICALLY ATTACHED to the parent tree's
    tree_canopy link via gazebo_ros_link_attacher, so it hangs on the tree
    with real physics instead of falling.
  - During picking: call /link_attacher_node/detach first, then grab/remove.

Service used:
  /link_attacher_node/attach  (gazebo_ros_link_attacher/srv/Attach)
    model_name_1 / link_name_1  -> apple (apple_body)
    model_name_2 / link_name_2  -> tree_xx (tree_canopy)

Run: python3 spawn_apples.py   (after gzserver + /spawn_entity + /link_attacher_node/attach are up)
"""
import os
import time
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity
from geometry_msgs.msg import Pose, Quaternion
from gazebo_ros_link_attacher.srv import Attach

# Tree info: (tree_name, x, y) - tree_name must match myworld_orchard.sdf <name> tags
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
        # Correct service type from gazebo_ros_link_attacher
        self.attach_cli = self.create_client(Attach, '/link_attacher_node/attach')

        self.get_logger().info('apple_spawner started; target: %d apples'
                               % (len(TREES) * len(APPLE_OFFSETS)))

    def wait_services(self, timeout=30.0):
        """Wait for BOTH /spawn_entity and /link_attacher_node/attach."""
        start = time.time()
        spawn_ok = False
        attach_ok = False
        while not (spawn_ok and attach_ok):
            if time.time() - start > timeout:
                self.get_logger().error('Services not ready after %.1fs, abort'
                                       % timeout)
                return False
            if not spawn_ok:
                if self.spawn_cli.wait_for_service(timeout_sec=0.5):
                    spawn_ok = True
                    self.get_logger().info('/spawn_entity ready')
                else:
                    self.get_logger().info('waiting for /spawn_entity ...')
            if not attach_ok:
                if self.attach_cli.wait_for_service(timeout_sec=0.5):
                    attach_ok = True
                    self.get_logger().info('/link_attacher_node/attach ready')
                else:
                    self.get_logger().info('waiting for /link_attacher_node/attach ...')
        return True

    def spawn_all(self):
        if not self.wait_services():
            return

        idx = 1
        attached = 0
        for (tree_name, tx, ty) in TREES:
            for (dx, dy, dz) in APPLE_OFFSETS:
                name = 'apple_%02d' % idx
                x = float(tx + dx)
                y = float(ty + dy)
                z = float(dz)

                # === Step 1: spawn apple model (unique name) ===
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
                    if fut.result() is None or not fut.result().success:
                        self.get_logger().error('spawn %s failed: %s'
                                               % (name, getattr(fut.result(), 'status_message', 'no result')))
                        idx += 1
                        continue
                except Exception as e:  # noqa: BLE001
                    self.get_logger().error('spawn %s error: %s' % (name, e))
                    idx += 1
                    continue

                # Give Gazebo a tick to register the new model before attaching
                time.sleep(0.15)

                # === Step 2: physically attach apple to tree canopy ===
                areq = Attach.Request()
                areq.model_name_1 = name
                areq.link_name_1 = 'apple_body'
                areq.model_name_2 = tree_name
                areq.link_name_2 = 'tree_canopy'
                try:
                    fut2 = self.attach_cli.call_async(areq)
                    rclpy.spin_until_future_complete(self, fut2, timeout_sec=5.0)
                    if fut2.result() is not None and fut2.result().ok:
                        attached += 1
                        self.get_logger().info(
                            'OK %s attached to %s @ (%.2f, %.2f, %.2f)'
                            % (name, tree_name, x, y, z))
                    else:
                        self.get_logger().warn('attach %s failed (service ok=%s)'
                                              % (name, getattr(fut2.result(), 'ok', 'n/a')))
                except Exception as e:  # noqa: BLE001
                    self.get_logger().warn('attach %s error: %s' % (name, e))

                idx += 1

        self.get_logger().info(
            '=== Done: %d/%d apples spawned AND attached ==='
            % (attached, len(TREES) * len(APPLE_OFFSETS)))


def main(args=None):
    rclpy.init(args=args)
    node = AppleSpawner()
    node.spawn_all()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
