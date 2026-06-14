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
        ('share/' + package_name + '/launch',['launch/my_robot_nav2_launchv3_hourse.py']),
        ('share/' + package_name + '/model',glob('model/*.sdf')),
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
