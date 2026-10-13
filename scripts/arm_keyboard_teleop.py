#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
果园采摘机械臂键盘控制脚本（完全按照PDF第5章 orchard_robot 关节定义）

关节列表（与PDF SDF一致）：
  platform_joint         - 升降平台 (prismatic Z轴, 范围 0 ~ 0.8m)
  arm_rot_joint          - 手臂旋转 (revolute Z轴, 范围 -pi ~ pi)
  arm_upper_pitch_joint  - 大臂俯仰 (revolute Y轴, 范围 -0.785 ~ 1.57)
  arm_forearm_extend_joint - 前臂伸缩 (prismatic X轴, 范围 0 ~ 0.3m)
  wrist_rotate_joint     - 腕部旋转 (revolute X轴, 范围 -1.57 ~ 1.57)
  finger1_joint          - 手指1/右手指 (revolute Y轴, 范围 -0.6 ~ 0.6)
  finger2_joint          - 手指2/左手指 (revolute Y轴, 范围 -0.6 ~ 0.6)
  finger3_joint          - 手指3/上手指 (revolute Y轴, 范围 -0.6 ~ 0.6)

控制话题格式（Gazebo Harmonic / gz-sim JointPositionController）:
  /model/vehicle_blue/joint/{joint_name}/cmd_pos

键盘映射：
  ┌─────────┬──────────┬──────────┬──────────┐
  │   O/P   │    W     │    R/F   │    U/J   │
  │ 手指3开合│  大臂俯仰 │  升降平台 │  手指1   │
  │ (上)    │  上/下    │  上/下    │  (右)    │
  ├─────────┼──────────┼──────────┼──────────┤
  │    A    │    S D   │    T/G   │    I/K   │
  │ 手臂旋转│          │  前臂伸缩 │  手指2   │
  │ 左/右   │  (备用)  │  伸/缩   │  (左)    │
  ├─────────┼──────────┼──────────┼──────────┤
  │         │    Q  E  │          │  SPACE   │
  │         │  腕部旋转 │          │  归零位  │
  │         │  左/右   │          │  X:退出  │
  └─────────┴──────────┴──────────┴──────────┘

运行：
  ros2 run myfirst_robot arm_keyboard_teleop.py
"""

import select
import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

# ======================== 关节配置（按PDF第5章精确定义）========================
JOINTS = [
    "platform_joint",
    "arm_rot_joint",
    "arm_upper_pitch_joint",
    "arm_forearm_extend_joint",
    "wrist_rotate_joint",
    "finger1_joint",
    "finger2_joint",
    "finger3_joint",
]
JOINTS_SHORT = ["lift", "rot", "shldr", "fore", "wrist", "fin1", "fin2", "fin3"]

# (lower, upper) — 与PDF SDF joint limit完全一致
LIMITS = [
    (0.0, 0.8),           # platform_joint: 0 ~ 0.8 m
    (-3.14, 3.14),        # arm_rot_joint: -pi ~ pi rad
    (-0.785, 1.57),       # arm_upper_pitch_joint: -45deg ~ 90deg
    (0.0, 0.3),           # arm_forearm_extend_joint: 0 ~ 0.3 m
    (-1.57, 1.57),        # wrist_rotate_joint: -90deg ~ 90deg
    (-0.6, 0.6),          # finger1_joint: -0.6 ~ 0.6 rad
    (-0.6, 0.6),          # finger2_joint: -0.6 ~ 0.6 rad
    (-0.6, 0.6),          # finger3_joint: -0.6 ~ 0.6 rad
]

HOME = [
    0.50,   # platform_joint            升降平台抬高 0.5m
    0.00,   # arm_rot_joint             旋转不转
    -0.45,   # arm_upper_pitch_joint     大臂向上仰约 26°
    0.15,   # arm_forearm_extend_joint  前臂伸出 0.15m
    0.30,   # wrist_rotate_joint        腕部略旋转
    0.25,   # finger1_joint             右手指张开
    0.25,   # finger2_joint             左手指张开
    0.25,   # finger3_joint             上手指张开
]

# 每个关节的cmd_pos topic（gz-sim JointPositionController格式）
CMD_TOPICS = [
    "/model/vehicle_blue/joint/platform_joint/cmd_pos",
    "/model/vehicle_blue/joint/arm_rot_joint/cmd_pos",
    "/model/vehicle_blue/joint/arm_upper_pitch_joint/cmd_pos",
    "/model/vehicle_blue/joint/arm_forearm_extend_joint/cmd_pos",
    "/model/vehicle_blue/joint/wrist_rotate_joint/cmd_pos",
    "/model/vehicle_blue/joint/finger1_joint/cmd_pos",
    "/model/vehicle_blue/joint/finger2_joint/cmd_pos",
    "/model/vehicle_blue/joint/finger3_joint/cmd_pos",
]

STEP_DEFAULT = 0.02
STEP_MIN = 0.005
STEP_MAX = 0.50
PUB_HZ = 50.0

HELP = """
================= ORCHARD ARM KEYBOARD TELEOP (PDF v5) ================
  W / S   : shoulder up / down         (arm_upper_pitch_joint)
  A / D   : arm rotate left / right    (arm_rot_joint)
  Q / E   : wrist rotate left / right  (wrist_rotate_joint)
  R / F   : lift platform up / down    (platform_joint)
  T / G   : forearm extend / retract   (arm_forearm_extend_joint)
  U / J   : finger1( right ) open/close (finger1_joint)
  I / K   : finger2( left  ) open/close (finger2_joint)
  O / P   : finger3( top   ) open/close (finger3_joint)
  SPACE   : home pose (all zeros)
  [ / ]   : step -  / step +
  X       : quit     (Ctrl+C also quits)
  NOTE    : hold a key to move continuously (terminal key repeat)
===================================================================="""


class ArmKeyboardTeleop(Node):
    """机械臂键盘控制节点 - PDF orchard_robot 关节版 (gz-sim)"""

    def __init__(self):
        super().__init__("arm_keyboard_teleop")

        # 为每个关节创建独立的Float64发布器（gz-sim JointPositionController）
        self.pubs = []
        for topic in CMD_TOPICS:
            self.pubs.append(self.create_publisher(Float64, topic, 10))

        self.target = list(HOME)
        self.step = STEP_DEFAULT
        # 50Hz定时发布，保持关节位置
        self.timer = self.create_timer(1.0 / PUB_HZ, self.publish_cmd)

    def publish_cmd(self):
        """50Hz发布各关节位置到gz-sim cmd_pos话题"""
        for i, pub in enumerate(self.pubs):
            msg = Float64()
            msg.data = float(self.target[i])
            pub.publish(msg)

    def apply_key(self, ch):
        """根据按键更新目标关节位置"""
        key = ch.lower() if ch.isalpha() else ch

        if key in KEYMAP:
            j, sign = KEYMAP[key]
            lo, hi = LIMITS[j]
            self.target[j] = max(lo, min(hi, self.target[j] + sign * self.step))
        elif key == " ":
            self.target = list(HOME)
        elif key == "[":
            self.step = max(STEP_MIN, self.step - 0.01)
        elif key == "]":
            self.step = min(STEP_MAX, self.step + 0.01)

    def status_line(self):
        """生成状态行"""
        parts = ["%s=%+.3f" % (JOINTS_SHORT[i], self.target[i]) for i in range(len(JOINTS))]
        return "step=%.3f | %s" % (self.step, "  ".join(parts))


# 按键 -> (关节索引, 方向)
KEYMAP = {
    "w": (2, +1),
    "s": (2, -1),    # arm_upper_pitch_joint: 大臂俯仰
    "a": (1, +1),
    "d": (1, -1),    # arm_rot_joint: 手臂旋转
    "q": (4, +1),
    "e": (4, -1),    # wrist_rotate_joint: 腕部旋转
    "r": (0, +1),
    "f": (0, -1),    # platform_joint: 升降平台
    "t": (3, +1),
    "g": (3, -1),    # arm_forearm_extend_joint: 前臂伸缩
    "u": (5, +1),
    "j": (5, -1),    # finger1_joint: 手指1(右)
    "i": (6, +1),
    "k": (6, -1),    # finger2_joint: 手指2(左)
    "o": (7, +1),
    "p": (7, -1),    # finger3_joint: 手指3(上)
}


def main():
    rclpy.init()
    node = ArmKeyboardTeleop()

    if not sys.stdin.isatty():
        node.get_logger().error("stdin is not a TTY; run this in a real terminal.")
        node.destroy_node()
        rclpy.shutdown()
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    sys.stdout.write(HELP)
    sys.stdout.write(node.status_line() + "\n")
    sys.stdout.flush()

    try:
        tty.setcbreak(fd)
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=1.0 / PUB_HZ)
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch.lower() == "x":
                    break
                node.apply_key(ch)
                sys.stdout.write("\r" + node.status_line() + "   ")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\narm_keyboard_teleop stopped.\n")
        sys.stdout.flush()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
