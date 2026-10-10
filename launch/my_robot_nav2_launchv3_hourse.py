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
    #包路径获取
    bringup_dir = get_package_share_directory('nav2_bringup')
    project_dir = get_package_share_directory('myfirst_robot')
    launch_dir = os.path.join(bringup_dir, 'launch')
    use_sim_time = LaunchConfiguration('use_sim_time', default='True')
    use_namespace = LaunchConfiguration('use_namespace')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    use_rviz = LaunchConfiguration('use_rviz')
    # 模型文件
    sdf_file = os.path.join(project_dir, 'model', 'myrobotv52.sdf')
    urdf_file = os.path.join(project_dir, 'model', 'myrobotv52.urdf')
    # 启动参数配置可命令行直接配置
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

    # with open(sdf_file, 'r') as infp:
    #     robot_description = infp.read()
    with open(urdf_file, 'r') as infp:
        robot_description = infp.read()

    # ✅ 1. Gazebo 世界文件
    world_file = os.path.join(project_dir, 'model', 'myworld_simple_hourse.sdf')
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to world model file to load',
    )

    #使用gazebo打开世界模型
    # gazebo = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([
    #         PathJoinSubstitution([
    #             FindPackageShare('ros_gz_sim'),
    #             'launch',
    #             'gz_sim.launch.py'
    #         ])
    #     ]),
    #     launch_arguments={
    #         'gz_args': LaunchConfiguration('world'),##注意这里的参数，如果使用world则，无法加载，必须使用gz_args
    #         'use_sim_time': use_sim_time,
    #     }.items()
    # )
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


    #启动发布机器人坐标服务
    # start_robot_state_publisher_cmd = Node(
    #     package='robot_state_publisher',
    #     executable='robot_state_publisher',
    #     name='robot_state_publisher',
    #     output='screen',
    #     parameters=[
    #         {'use_sim_time': use_sim_time, 'robot_description': robot_description}
    #     ]
    # )
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

    pose = {
        'x': LaunchConfiguration('x_pose', default='2.00'),
        'y': LaunchConfiguration('y_pose', default='0.50'),
        'z': LaunchConfiguration('z_pose', default='1.50'),
        'R': LaunchConfiguration('roll', default='3.14'),
        'P': LaunchConfiguration('pitch', default='0.00'),
        'Y': LaunchConfiguration('yaw', default='0.00'),
    }

    robot_name = LaunchConfiguration('robot_name')
    robot_sdf = LaunchConfiguration('robot_sdf')
    namespace = LaunchConfiguration('namespace')

    #在gazebo中创建机器人模型
    # gz_robot = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(sim_dir, 'launch', 'spawn_tb3.launch.py')),
    #     launch_arguments={'namespace': namespace,
    #                         'use_sim_time': use_sim_time,
    #                         'robot_name': robot_name,
    #                         'robot_sdf': robot_sdf,
    #                         'x_pose': pose['x'],
    #                         'y_pose': pose['y'],
    #                         'z_pose': pose['z'],
    #                         'roll': pose['R'],
    #                         'pitch': pose['P'],
    #                         'yaw': pose['Y']}.items()
    # )
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'myrobotv5',
            '-file', sdf_file,  # 直接加载完整SDF，带雷达、差速驱动
            '-x', '2.0',
            '-y', '0.5',
            '-z', '0.8',   # 不要设0，会穿模到地面下
            '-R', '0.0',   # 不要设3.14，机器人会倒扣180度
            '-P', '0.0',
            '-Y', '0.0'
        ],
        output='screen'
    )

    #打开rviz
    rviz_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'rviz_launch.py')),
        condition=IfCondition(use_rviz),
        launch_arguments={
            'namespace': namespace,
            'use_namespace': use_namespace,
            'use_sim_time': use_sim_time,
            'rviz_config': rviz_config_file,
        }.items(),
    )

    # return LaunchDescription([
    #     declare_world_cmd,A
    #     gazebo,
    #     start_robot_state_publisher_cmd,  # 先启动
    #     declare_robot_name_cmd,
    #     declare_robot_sdf_cmd,
    #     declare_namespace_cmd,
    #     # gz_robot,
    #     spawn_robot,
    #     declare_use_rviz_cmd,
    #     declare_use_namespace_cmd,
    #     declare_rviz_config_file_cmd,
    #     rviz_cmd,
    # ])
    return LaunchDescription([
        declare_world_cmd,
        gazebo,
        declare_robot_name_cmd,
        declare_robot_sdf_cmd,
        declare_namespace_cmd,
        spawn_robot,
        start_robot_state_publisher_cmd, # spawn完机器人再启动rsp
        declare_use_rviz_cmd,
        declare_use_namespace_cmd,
        declare_rviz_config_file_cmd,
        rviz_cmd,
    ])