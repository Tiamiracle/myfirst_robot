#!/usr/bin/env python3
"""
Keyboard teleop for the 4-DOF suction arm of myfirst_robot.

How it works
------------
The Gazebo plugin `libgazebo_ros_joint_pose_trajectory.so` subscribes to
`/set_joint_trajectory` (trajectory_msgs/JointTrajectory) and moves the joints
KINEMATICALLY via Joint::SetPosition. Two consequences this node deals with:

  1. header.frame_id MUST be "world", otherwise the plugin logs
     "Plugin needs a reference link [] as frame_id, aborting." and does nothing.
  2. The plugin does NOT hold a pose: once a trajectory finishes it stops
     calling SetPosition and gravity drags the arm down. So we REPUBLISH the
     current target at a fixed rate (default 20 Hz) to keep the arm where you
     put it.

Keys
----
  W / S   : shoulder up / down     (joint2_shoulder_pitch)
  A / D   : base yaw left / right  (joint1_base_yaw)
  Q / E   : elbow up / down        (joint3_elbow_pitch)
  R / F   : wrist up / down        (joint4_wrist_pitch)
  SPACE   : go to home pose (all zeros)
  [ / ]   : decrease / increase step size
  X       : quit
  Ctrl+C  : quit

Run (on the VM, in a REAL terminal — it needs a TTY for raw keyboard input):
  python3 <path>/scripts/arm_keyboard_teleop.py
e.g.
  python3 ~/ros2_myfirstrobot/src/myfirst_robot/scripts/arm_keyboard_teleop.py
or, after `colcon build`:
  python3 ~/ros2_myfirstrobot/install/myfirst_robot/share/myfirst_robot/scripts/arm_keyboard_teleop.py
"""
import select
import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration


# Joint order must match the `positions` order below and the SDF joint names.
JOINTS = [
    'joint1_base_yaw',
    'joint2_shoulder_pitch',
    'joint3_elbow_pitch',
    'joint4_wrist_pitch',
]
JOINTS_SHORT = ['yaw', 'shldr', 'elbow', 'wrist']

# (lower, upper) in radians, same as the SDF joint limits.
LIMITS = [
    (-3.1416, 3.1416),
    (-2.0, 2.0),
    (-2.0, 2.0),
    (-2.0, 2.0),
]

HOME = [0.0, 0.0, 0.0, 0.0]

# key -> (joint_index, direction)
KEYMAP = {
    'w': (1, +1), 's': (1, -1),   # shoulder
    'a': (0, +1), 'd': (0, -1),   # base yaw
    'q': (2, +1), 'e': (2, -1),   # elbow
    'r': (3, +1), 'f': (3, -1),   # wrist
}

STEP_DEFAULT = 0.06
STEP_MIN = 0.01
STEP_MAX = 0.50
PUB_HZ = 20.0

HELP = """
================= ARM KEYBOARD TELEOP =================
  W / S   : shoulder up / down     (joint2_shoulder_pitch)
  A / D   : base yaw left / right  (joint1_base_yaw)
  Q / E   : elbow up / down        (joint3_elbow_pitch)
  R / F   : wrist up / down        (joint4_wrist_pitch)
  SPACE   : home pose (all zeros)
  [ / ]   : step -  / step +
  X       : quit     (Ctrl+C also quits)
  NOTE    : hold a key to move continuously (terminal key repeat)
=======================================================
"""


class ArmKeyboardTeleop(Node):
    def __init__(self):
        super().__init__('arm_keyboard_teleop')
        self.pub = self.create_publisher(JointTrajectory, '/set_joint_trajectory', 10)
        self.target = list(HOME)
        self.step = STEP_DEFAULT
        self.timer = self.create_timer(1.0 / PUB_HZ, self.publish_cmd)

    def publish_cmd(self):
        msg = JointTrajectory()
        msg.header.frame_id = 'world'          # MUST: else plugin aborts
        msg.joint_names = JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = [float(v) for v in self.target]
        pt.time_from_start = Duration(sec=0, nanosec=100_000_000)
        msg.points = [pt]
        self.pub.publish(msg)

    def apply_key(self, ch):
        """Update the target joint angles from a single keypress."""
        key = ch.lower() if ch.isalpha() else ch
        if key in KEYMAP:
            j, sign = KEYMAP[key]
            lo, hi = LIMITS[j]
            self.target[j] = max(lo, min(hi, self.target[j] + sign * self.step))
        elif key == ' ':
            self.target = list(HOME)
        elif key == '[':
            self.step = max(STEP_MIN, self.step - 0.01)
        elif key == ']':
            self.step = min(STEP_MAX, self.step + 0.01)

    def status_line(self):
        parts = ['%s=%+.2f' % (JOINTS_SHORT[i], self.target[i]) for i in range(4)]
        return 'step=%.2f | %s' % (self.step, '  '.join(parts))


def main():
    rclpy.init()
    node = ArmKeyboardTeleop()

    if not sys.stdin.isatty():
        node.get_logger().error('stdin is not a TTY; run this in a real terminal.')
        node.destroy_node()
        rclpy.shutdown()
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    sys.stdout.write(HELP)
    sys.stdout.write(node.status_line() + '\n')
    sys.stdout.flush()

    try:
        tty.setcbreak(fd)                      # single-key, no echo; ISIG kept
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=1.0 / PUB_HZ)
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch.lower() == 'x':
                    break
                node.apply_key(ch)
                sys.stdout.write('\r' + node.status_line() + '   ')
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write('\narm_keyboard_teleop stopped.\n')
        sys.stdout.flush()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
