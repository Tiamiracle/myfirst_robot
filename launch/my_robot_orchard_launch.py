import os
import tempfile
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # ==================== 路径配置 ====================
    project_dir = get_package_share_directory("myfirst_robot")
    sdf_file = os.path.join(project_dir, "model", "myrobotv52.sdf")
    urdf_file = os.path.join(project_dir, "model", "myrobotv52.urdf")
    world_file = os.path.join(project_dir, "model", "myworld_orchard.sdf")

    # Gazebo 模型路径（让 gz sim 能找到模型）
    model_path = os.path.join(project_dir, "model")
    os.environ["GZ_SIM_RESOURCE_PATH"] = (
        model_path + ":" + os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    )
    os.environ["GAZEBO_MODEL_PATH"] = (
        model_path + ":" + os.environ.get("GAZEBO_MODEL_PATH", "")
    )

    # Nav2 路径
    bringup_dir = get_package_share_directory("nav2_bringup")
    launch_dir = os.path.join(bringup_dir, "launch")

    # ==================== 声明参数 ====================
    use_sim_time = LaunchConfiguration("use_sim_time", default="True")
    use_rviz = LaunchConfiguration("use_rviz", default="True")
    rviz_config_file = LaunchConfiguration(
        "rviz_config_file",
        default=os.path.join(bringup_dir, "rviz", "nav2_default_view.rviz"),
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="True", description="Use simulation clock"
    )
    declare_rviz_config = DeclareLaunchArgument(
        "rviz_config_file",
        default_value=os.path.join(bringup_dir, "rviz", "nav2_default_view.rviz"),
        description="RViz config file path",
    )
    declare_use_rviz = DeclareLaunchArgument(
        "use_rviz", default_value="True", description="Whether to start RViz"
    )
    declare_world = DeclareLaunchArgument(
        "world", default_value=world_file, description="Path to orchard world SDF"
    )

    # ==================== 读取URDF给robot_state_publisher ====================
    with open(urdf_file, "r") as f:
        robot_description = f.read()

    # ========== 1. 启动 Gazebo Sim (Fortress) ==========
    # 使用 ros_gz_sim 的 GzSim action，替代 Classic 的 gazebo.launch.py
    gz_sim = ExecuteProcess(
        cmd=[
            "ign",
            "gazebo",
            "-r",
            "--render-engine",
            "ogre",
            world_file,
        ],  # 添加 --render-engine ogre
        output="screen",
    )
    # ========== 2. Robot State Publisher (读取URDF发布TF) ==========
    robot_state_pub = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "robot_description": robot_description,
            }
        ],
    )

    # ========== 3. Spawn 机器人到果园入口 ==========
    # 使用 ros_gz_sim 的 create 工具，替代 gazebo_ros spawn_entity.py
    spawn_robot = ExecuteProcess(
        cmd=[
            "ros2",
            "run",
            "ros_gz_sim",
            "create",
            "-file",
            sdf_file,
            "-name",
            "vehicle_blue",
            "-x",
            "0.0",
            "-y",
            "-12.0",
            "-z",
            "0.8",
            "-R",
            "0.0",
            "-P",
            "0.0",
            "-Y",
            "1.5707963",
        ],
        output="screen",
    )

    # 延迟5秒等Gazebo完全启动后再spawn
    delayed_spawn = TimerAction(
        period=5.0,
        actions=[spawn_robot],
    )

    # ========== 4. ROS-GZ Bridge (核心！桥接ROS2和Gazebo话题) ==========
    # 格式: <ros_topic>@<ros_msg_type>]<gz_topic>
    # ] 表示 ROS -> Gazebo 方向

    bridge_args = [
        # --- 底盘控制：ROS /cmd_vel -> gz /cmd_vel ---
        "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
        # --- 激光雷达：gz /scan -> ROS /scan ---
        "/scan[sensor_msgs/msg/LaserScan]ignition.msgs.LaserScan",
        # --- 关节状态：gz /joint_states -> ROS /joint_states ---
        "/joint_states[sensor_msgs/msg/JointState]ignition.msgs.Model",
        # --- 力传感器：gz /finger*_force -> ROS /finger*_force ---
        "/finger1_force[geometry_msgs/msg/WrenchStamped]ignition.msgs.Wrench",
        "/finger2_force[geometry_msgs/msg/WrenchStamped]ignition.msgs.Wrench",
        "/finger3_force[geometry_msgs/msg/WrenchStamped]ignition.msgs.Wrench",
        # --- 机械臂位置控制：ROS /arm/*_cmd -> gz /*/cmd_pos ---
        "/arm/lift_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/rot_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/shoulder_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/forearm_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/wrist_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger1_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger2_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger3_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        # --- 里程计：gz /odom -> ROS /odom ---
        "/odom[nav_msgs/msg/Odometry]ignition.msgs.Odometry",
        # --- TF树：gz /world/pose -> ROS /tf (scene broadcaster) ---
        "/tf[tf2_msgs/msg/TFMessage]ignition.msgs.Pose_V",
        "/tf_static[tf2_msgs/msg/TFMessage]ignition.msgs.Pose_V",
    ]

    parameter_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=bridge_args,
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ========== 5. RViz ==========
    rviz_cmd = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        condition=IfCondition(use_rviz),
        parameters=[{"use_sim_time": use_sim_time}],
    )

    return LaunchDescription(
        [
            declare_use_sim_time,
            declare_rviz_config,
            declare_use_rviz,
            declare_world,
            gz_sim,
            robot_state_pub,
            delayed_spawn,
            parameter_bridge,
            rviz_cmd,
        ]
    )
