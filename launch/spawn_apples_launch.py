import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, LogInfo, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    project_dir = get_package_share_directory('myfirst_robot')
    orchard_launch = os.path.join(project_dir, 'launch', 'my_robot_orchard_launch.py')
    script_path = os.path.join(project_dir, 'scripts', 'spawn_apples.py')

    # 1) Bring up the orchard: gzserver + robot + (optionally) rviz
    include_orchard = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(orchard_launch),
        launch_arguments={'use_rviz': LaunchConfiguration('use_rviz', default='True')}.items(),
    )

    # 2) After the world is loaded, spawn apples onto the tree crowns.
    #    TimerAction gives gzserver time to advertise /spawn_entity.
    spawn_apples = TimerAction(
        period=8.0,
        actions=[
            LogInfo(msg='[spawn_apples] spawning apples onto tree crowns...'),
            ExecuteProcess(cmd=['python3', script_path], output='screen'),
        ],
    )

    return LaunchDescription([
        include_orchard,
        spawn_apples,
    ])
