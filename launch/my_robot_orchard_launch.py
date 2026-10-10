import os
import xacro
import tempfile
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition
from launch.substitutions import Command

def generate_launch_description():
    # 包路径获取
    bringup_dir = get_package_share_directory('nav2_bringup')
    project_dir = get_package_share_directory('myfirst_robot')
    launch_dir = os.path.join(bringup_dir, 'launch')
    use_sim_time = LaunchConfiguration('use_sim_time', default='True')
    use_namespace = LaunchConfiguration('use_namespace')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    use_rviz = LaunchConfiguration('use_rviz')

    # ========== 模型文件（果园版） ==========
    sdf_file = os.path.join(project_dir, 'model', 'myrobotv52.sdf')
    urdf_file = os.path.join(project_dir, 'model', 'myrobotv52.urdf')
    world_file = os.path.join(project_dir, 'model', 'myworld_orchard.sdf')

    # 启动参数配置
    declare_robot_name_cmd = DeclareLaunchArgument(
        'robot_name', default_value='myrobotv5', description='name of the robot'
    )

    declare_robot_sdf_cmd = DeclareLaunchArgument(
        'robot_sdf',
        default_value=sdf_file,
        description='Full path to robot sdf file to spawn the robot in gazebo',
    )

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config_file',
        default_value=os.path.join(bringup_dir, 'rviz', 'nav2_default_view.rviz'),
        description='Full path to the RVIZ config file to use',
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz', default_value='True', description='Whether to start RVIZ'
    )

    declare_use_namespace_cmd = DeclareLaunchArgument(
        'use_namespace',
        default_value='false',
        description='Whether to apply a namespace to the navigation stack',
    )

    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace', default_value='', description='Top-level namespace'
    )

    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to orchard world model file to load',
    )

    # 读取机器人URDF（给robot_state_publisher用）
    with open(urdf_file, 'r') as infp:
        robot_description = infp.read()

    # ========== 1. Gazebo（果园世界） ==========
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': world_file,
            'use_sim_time': use_sim_time,
            'verbose': 'true'
        }.items()
    )

    # ========== 2. Robot State Publisher ==========
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time,
             'robot_description': robot_description}
        ]
    )

    # ========== 3. Spawn机器人到果园入口位置 ==========
    # 果园入口在南围栏缺口处，机器人从(0, -12)附近进入
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'myrobotv5',
            '-file', sdf_file,
            '-x', '0.0',      # X: 果园西侧起始
            '-y', '-12.0',     # Y: 靠近南围栏入口
            '-z', '0.8',       # Z: 避免穿模
            '-R', '0.0',
            '-P', '0.0',
            '-Y', '1.5707963'  # Yaw: 朝北（朝向果树方向）
        ],
        output='screen'
    )

    # ========== 4. RViz ==========
    rviz_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'rviz_launch.py')),
        condition=IfCondition(use_rviz),
        launch_arguments={
            'namespace': LaunchConfiguration('namespace'),
            'use_namespace': use_namespace,
            'use_sim_time': use_sim_time,
            'rviz_config': rviz_config_file,
        }.items(),
    )

    return LaunchDescription([
        declare_world_cmd,
        gazebo,
        declare_robot_name_cmd,
        declare_robot_sdf_cmd,
        declare_namespace_cmd,
        spawn_robot,
        start_robot_state_publisher_cmd,
        declare_use_rviz_cmd,
        declare_use_namespace_cmd,
        declare_rviz_config_file_cmd,
        rviz_cmd,
    ])
