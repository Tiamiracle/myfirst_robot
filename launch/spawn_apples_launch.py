import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    project_dir = get_package_share_directory('myfirst_robot')
    orchard_launch = os.path.join(project_dir, 'launch', 'my_robot_orchard_launch.py')
    script_path = os.path.join(project_dir, 'scripts', 'spawn_apples.py')
    start_detector = LaunchConfiguration('start_detector', default='False')

    declare_start_detector = DeclareLaunchArgument(
        'start_detector',
        default_value='False',
        description='Whether to start the HSV apple detector',
    )

    # 1) Bring up the Fortress orchard, robot and ROS-GZ service bridges.
    include_orchard = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(orchard_launch),
        launch_arguments={
            'use_rviz': LaunchConfiguration('use_rviz', default='True'),
            'start_detector': start_detector,
        }.items(),
    )

    # 2) Start the persistent fruit manager after UserCommands is available.
    spawn_apples = TimerAction(
        period=6.0,
        actions=[
            LogInfo(msg='[fruit_manager] creating static apples on tree crowns...'),
            ExecuteProcess(cmd=['python3', script_path], output='screen'),
        ],
    )

    return LaunchDescription([
        declare_start_detector,
        include_orchard,
        spawn_apples,
    ])
