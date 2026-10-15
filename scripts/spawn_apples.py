#!/usr/bin/env python3
"""Manage orchard apples in Gazebo Fortress through ros_gz_bridge services.

Initial apples are spawned as static models. Detaching removes that static
model and recreates it dynamically at the same pose, so gravity makes it fall.

Commands::

  ros2 topic pub --once /fruit/detach std_msgs/msg/String "{data: apple_01}"
  ros2 topic pub --once /fruit/remove std_msgs/msg/String "{data: apple_01}"
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import rclpy
from geometry_msgs.msg import Pose
from rclpy.node import Node
from ros_gz_interfaces.msg import Entity
from ros_gz_interfaces.srv import DeleteEntity, SpawnEntity
from std_msgs.msg import String


WORLD_NAME = "orchard_world"
CREATE_SERVICE = f"/world/{WORLD_NAME}/create"
REMOVE_SERVICE = f"/world/{WORLD_NAME}/remove"

# These coordinates must stay aligned with model/myworld_orchard.sdf.
TREES = [
    ("tree_01", 6.0, 4.0), ("tree_02", 12.0, 4.0), ("tree_03", 18.0, 4.0),
    ("tree_04", 9.0, 0.0), ("tree_05", 15.0, 0.0), ("tree_06", 21.0, 0.0),
    ("tree_07", 6.0, -4.0), ("tree_08", 12.0, -4.0), ("tree_09", 18.0, -4.0),
]

# Local (x, y, z) offsets relative to each tree base.
APPLE_OFFSETS = [
    (0.15, 0.1125, 1.065),
    (-0.135, 0.165, 1.215),
    (0.09, -0.165, 1.14),
]


class FruitState(Enum):
    ON_TREE = "ON_TREE"
    DETACHED = "DETACHED"
    REMOVED = "REMOVED"


@dataclass
class Fruit:
    name: str
    tree_name: str
    pose: Pose
    state: FruitState = FruitState.ON_TREE


class FruitManager(Node):
    """Creates, detaches, and removes orchard apples."""

    def __init__(self) -> None:
        super().__init__("fruit_manager")
        self._apple_sdf = self._read_apple_sdf()
        self._fruits = self._build_fruit_table()

        self._spawn_client = self.create_client(SpawnEntity, CREATE_SERVICE)
        self._delete_client = self.create_client(DeleteEntity, REMOVE_SERVICE)
        self.create_subscription(String, "/fruit/detach", self._detach_callback, 10)
        self.create_subscription(String, "/fruit/remove", self._remove_callback, 10)
        self._spawn_queue = []
        self._last_wait_log = 0.0

        self.get_logger().info(
            f"fruit_manager ready: {len(self._fruits)} fruit templates; "
            "waiting for Fortress services"
        )
        self._spawn_timer = self.create_timer(0.5, self._spawn_when_ready)

    def _read_apple_sdf(self) -> str:
        # Installed location: share/myfirst_robot/scripts. The fallback supports
        # running directly from this source checkout.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(os.path.dirname(script_dir), "model", "apple_model", "model.sdf"),
            os.path.join(script_dir, "..", "model", "apple_model", "model.sdf"),
        ]
        for path in candidates:
            path = os.path.abspath(path)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as sdf_file:
                    return sdf_file.read()
        raise FileNotFoundError("Cannot find model/apple_model/model.sdf")

    @staticmethod
    def _make_pose(x: float, y: float, z: float) -> Pose:
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0
        return pose

    def _build_fruit_table(self) -> Dict[str, Fruit]:
        fruits: Dict[str, Fruit] = {}
        index = 1
        for tree_name, tree_x, tree_y in TREES:
            for offset_x, offset_y, offset_z in APPLE_OFFSETS:
                name = f"apple_{index:02d}"
                fruits[name] = Fruit(
                    name=name,
                    tree_name=tree_name,
                    pose=self._make_pose(tree_x + offset_x, tree_y + offset_y, offset_z),
                )
                index += 1
        return fruits

    def _spawn_when_ready(self) -> None:
        if not self._spawn_client.service_is_ready() or not self._delete_client.service_is_ready():
            if time.monotonic() - self._last_wait_log >= 5.0:
                self.get_logger().info(
                    f"waiting for {CREATE_SERVICE} and {REMOVE_SERVICE}"
                )
                self._last_wait_log = time.monotonic()
            return

        self._spawn_timer.cancel()
        self._spawn_queue = list(self._fruits.values())
        self.get_logger().info("Fortress entity services are ready; creating apples")
        self._spawn_next_static()

    def _spawn_next_static(self) -> None:
        if not self._spawn_queue:
            self.get_logger().info(
                f"all {len(self._fruits)} apples are ready on the trees"
            )
            return

        fruit = self._spawn_queue.pop(0)
        self._spawn_async(fruit, is_static=True, on_complete=self._static_spawn_done)

    def _static_spawn_done(self, fruit: Fruit, success: bool) -> None:
        if not success:
            self.get_logger().error(f"failed to create {fruit.name}")
        self._spawn_next_static()

    def _sdf_for(self, fruit_name: str, is_static: bool) -> str:
        """Return an SDF model with a unique name and the requested physics."""
        sdf = self._apple_sdf.replace(
            '<model name="apple">', f'<model name="{fruit_name}">', 1
        )
        static_tag = "true" if is_static else "false"
        return sdf.replace(
            f'<model name="{fruit_name}">',
            f'<model name="{fruit_name}">\n    <static>{static_tag}</static>',
            1,
        )

    def _spawn_async(self, fruit: Fruit, is_static: bool, on_complete) -> None:
        request = SpawnEntity.Request()
        request.entity_factory.name = fruit.name
        request.entity_factory.allow_renaming = False
        request.entity_factory.sdf = self._sdf_for(fruit.name, is_static)
        request.entity_factory.pose = fruit.pose
        request.entity_factory.relative_to = "world"

        future = self._spawn_client.call_async(request)

        def spawn_done(done_future) -> None:
            try:
                response = done_future.result()
                success = response is not None and response.success
            except Exception as error:  # noqa: BLE001
                self.get_logger().error(f"create {fruit.name} failed: {error}")
                success = False
            if success:
                mode = "static/on-tree" if is_static else "dynamic/detached"
                self.get_logger().info(f"created {fruit.name} ({mode})")
            on_complete(fruit, success)

        future.add_done_callback(spawn_done)

    def _delete_async(self, fruit_name: str, on_complete) -> None:
        request = DeleteEntity.Request()
        request.entity.name = fruit_name
        request.entity.type = Entity.MODEL

        future = self._delete_client.call_async(request)

        def delete_done(done_future) -> None:
            try:
                response = done_future.result()
                success = response is not None and response.success
            except Exception as error:  # noqa: BLE001
                self.get_logger().error(f"remove {fruit_name} failed: {error}")
                success = False
            on_complete(success)

        future.add_done_callback(delete_done)

    def _lookup_command_fruit(self, message: String, command: str) -> Optional[Fruit]:
        fruit_name = message.data.strip()
        fruit = self._fruits.get(fruit_name)
        if fruit is None:
            self.get_logger().error(f"{command}: unknown fruit '{fruit_name}'")
        return fruit

    def _detach_callback(self, message: String) -> None:
        fruit = self._lookup_command_fruit(message, "detach")
        if fruit is None:
            return
        if fruit.state != FruitState.ON_TREE:
            self.get_logger().warning(
                f"detach: {fruit.name} is {fruit.state.value}, expected ON_TREE"
            )
            return

        # Fortress has no generic runtime attach/detach service. Recreating at
        # an identical pose changes only this fruit from static to dynamic.
        def recreate_dynamic(removed: bool) -> None:
            if not removed:
                self.get_logger().error(f"detach: could not remove static {fruit.name}")
                return

            def detached_created(created: Fruit, spawned: bool) -> None:
                if not spawned:
                    self.get_logger().error(
                        f"detach: could not recreate dynamic {created.name}"
                    )
                    return
                created.state = FruitState.DETACHED
                self.get_logger().info(
                    f"detached {created.name}; gravity is now active"
                )

            self._spawn_async(fruit, is_static=False, on_complete=detached_created)

        self._delete_async(fruit.name, recreate_dynamic)

    def _remove_callback(self, message: String) -> None:
        fruit = self._lookup_command_fruit(message, "remove")
        if fruit is None:
            return
        if fruit.state == FruitState.REMOVED:
            self.get_logger().warning(f"remove: {fruit.name} is already removed")
            return
        def removed(success: bool) -> None:
            if not success:
                self.get_logger().error(f"remove: failed to remove {fruit.name}")
                return
            fruit.state = FruitState.REMOVED
            self.get_logger().info(f"removed {fruit.name}")

        self._delete_async(fruit.name, removed)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FruitManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
