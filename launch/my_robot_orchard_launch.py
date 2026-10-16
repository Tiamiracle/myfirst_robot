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
    default_rviz_config = os.path.join(project_dir, "config", "orchard_camera.rviz")
    rviz_config_file = LaunchConfiguration("rviz_config_file", default=default_rviz_config)

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="True", description="Use simulation clock"
    )
    declare_rviz_config = DeclareLaunchArgument(
        "rviz_config_file",
        default_value=default_rviz_config,
        description="RViz config file path (defaults to RGB-D camera view)",
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
        # --- 底盘控制：ROS /cmd_vel -> gz /cmd_vel (这是对的，保留) ---
        "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
        # --- 激光雷达：gz /scan -> ROS /scan (修正了方括号) ---
        "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
        # --- RGB-D 相机：Gazebo -> ROS 2 ---
        "/camera/color/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image",
        "/camera/depth/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image",
        "/camera/color/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo",
        "/camera/depth/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo",
        # --- 关节状态：gz /joint_states -> ROS /joint_states (修正了方括号) ---
        "/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model",
        # --- 力传感器 (修正了方括号) ---
        "/finger1_force@geometry_msgs/msg/WrenchStamped[ignition.msgs.Wrench",
        "/finger2_force@geometry_msgs/msg/WrenchStamped[ignition.msgs.Wrench",
        "/finger3_force@geometry_msgs/msg/WrenchStamped[ignition.msgs.Wrench",
        # --- 机械臂位置控制 (这是对的，保留) ---
        "/arm/lift_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/rot_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/shoulder_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/forearm_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/wrist_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger1_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger2_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        "/arm/finger3_cmd@std_msgs/msg/Float64]ignition.msgs.Double",
        # --- 里程计 (修正了方括号) ---
        "/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
        # --- TF树 (修正了方括号) ---
        "/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
        "/tf_static@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
    ]

    # Entity service discovery happens only when parameter_bridge starts.
    # Keep these separate so Gazebo's UserCommands system has time to advertise
    # its services before this bridge process is created.
    entity_service_bridge_args = [
        "/world/orchard_world/create@ros_gz_interfaces/srv/SpawnEntity",
        "/world/orchard_world/remove@ros_gz_interfaces/srv/DeleteEntity",
        "/world/orchard_world/set_pose@ros_gz_interfaces/srv/SetEntityPose",
    ]

    parameter_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=bridge_args,
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    entity_service_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="orchard_entity_service_bridge",
        arguments=entity_service_bridge_args,
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Gazebo and the UserCommands world system are ready after the robot spawn
    # delay.  Starting later avoids a one-time service-discovery race.
    delayed_entity_service_bridge = TimerAction(
        period=6.0,
        actions=[entity_service_bridge],
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
            delayed_entity_service_bridge,
            rviz_cmd,
        ]
    )
