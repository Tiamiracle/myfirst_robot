from setuptools import find_packages, setup
from glob import glob

package_name = 'myfirst_robot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',[
            'launch/my_robot_nav2_launchv3_hourse.py',
            'launch/my_robot_orchard_launch.py',
            'launch/spawn_apples_launch.py',
        ]),
        ('share/' + package_name + '/scripts',[
            'scripts/spawn_apples.py',
            'scripts/arm_keyboard_teleop.py',
        ]),
        ('share/' + package_name + '/model', glob('model/*.sdf') + glob('model/*.urdf')),
        ('share/' + package_name + '/model/tree_model', [
            'model/tree_model/model.sdf',
            'model/tree_model/model.config',
        ]),
        ('share/' + package_name + '/model/apple_model', [
            'model/apple_model/model.sdf',
            'model/apple_model/model.config',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='idlity',
    maintainer_email='15993308@qq.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
