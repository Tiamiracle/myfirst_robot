# ubuntu24\.04\+ROS jazzy\+Nav2\+Gazebo\+Rviz 环境下绘制地图

# 环境说明及安装

## ubuntu24\.04

目前linux下主流环境ubuntu，当前推荐的版本是24\.04版本，ubuntu有3中安装方式：

1、由u盘安装纯正的linux环境，电脑在启动时可以直接进入Ubuntu环境。

2、采用虚拟机工具安装，在虚拟环境运行。

3、采用windows下以wsl形式安装，安装方式如下：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzE4MzMwNWU4MWU5Zjk0NDI3M2FmZmI2MjllMDVhMTRfNTVjMWVlY2I2OTRiMTNmNTk2MDYyNTQxMGI0ZDRlMjdfSUQ6NzY1MDg3NTg3NjU2ODk5Mjk4NV8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

## ROS2环境

### ros2官方网址：https://www\.ros\.org/blog/getting\-started/

ros2有多个版本，而且版本差异比较大，各版本命令会有差异，所以此项目中我们推荐jazzy版本，这个版本也是和ubuntu24\.04官方最推荐的版本

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTE4OTE5N2EyNWRhN2NmMDA0OWEzNGUwZDUzZDcwYWRfN2EyYmJhNDQ5ZGU5MzBlN2E4NjUxYjYwODEwYTFjZjhfSUQ6NzY1MDg3NzYxNTc1ODExNzgyNl8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

### ros2的安装方式

```Bash
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | sudo tee /usr/share/keyrings/ros-archive-keyring.gpg >/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
sudo apt update

sudo apt install ros-jazzy-desktop -y  # 基础版
# 或安装完整版（含Gazebo仿真）
sudo apt install ros-jazzy-desktop-full -y
【此处注意：默认安装了ros2对应的新版本的gazebo8.11，这版本和之前的版本差异较大】

ros2删除的命令：
sudo apt list --installed | grep ros-
sudo apt remove --purge $(dpkg -l | grep "^ii.*ros-" | awk '{print $2}')
sudo apt autoremove
```

## gazebo仿真软件

如上面ros2 安装了desktop\-full版本，则系统会自动安装gazebo，在ubuntu 命令窗口下输入：gz sim 可以看到gazebo的界面，这一版本和gazebo前期的版本差异很大，使用ros2中的使用命令也发生了变化，大家在查找资料的时候注意版本。

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmIwZTUwZTJjYjhiMmQ0OWU2ZmZjOWY5YjUxNTJkYmVfNjZjOWQzZjgxZDc4ZDYyYmZiNWZjMTc4MDA4MGM0NjlfSUQ6NzY1MDg4MTU4NzIxMDYxOTg3Ml8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

## rviz介绍

RViz（Robot Visualization） 是 ROS / ROS 2 中最核心的 3D 可视化工具，作用是把抽象的机器人数据变成你能"看见"的东西——传感器数据、机器人模型、路径规划、地图等，全部在一个三维窗口里实时展示。

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2E2YzM0ZGM2ZDY1OWE5OGE1YWZiMDBkNzc4MDYzM2FfZmFkZjBiNDFlYzgwNTc4MjVjZDNlMzM2ODU3OTMzNmNfSUQ6NzY1MTIwMTE4MDQ1MDAxNjIxN18xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

## Nav2介绍

nav2作为机器人导航ROS2官方推荐的项目，对机器人导航控制做了比较全面的底层支持，具有非常丰富的插件接口，可以方便的进行扩展，对于机器人控制感兴趣的朋友非常值得深入的学习和研究。

官方网址：https://docs\.nav2\.org/concepts/index\.html\#

二进制安装方式命令：

```Plain Text
sudo apt install ros-jazzy-navigation2
sudo apt install ros-jazzy-nav2-bringup
sudo apt install ros-jazzy-nav2-minimal-tb*
sudo apt install ros-jazzy-turtlebot3-gazebo
```

对源码感兴趣的同学，可以采用源码安装：

```Bash
source /opt/ros/jazzy/install/setup.bash
mkdir -p ~/nav2_ws/src && cd ~/nav2_ws
git clone https://github.com/ros-navigation/navigation2.git --branch jazzy ./src/navigation2
git clone https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation.git --branch jazzy ./src/nav2_minimal_turtlebot_simulation

安装依赖包：
rosdep install -r -y   --from-paths ./src    --ignore-src

编译项目：
colcon build   --symlink-install --parallel-workers 8
```



# 绘制地图

要绘制地图，需要具备几个条件：

a、有一个装有雷达的小车的模型

b、在gazebo中可以控制小车行走

c、计算小车行走路径，保存地图

下面我们就这三部分内容分别说明一下。

## 小车模型及世界模型

### 小车模型文件格式

小车的模型有两种方式编写。一种是ros2中对机器人模型通过urdf文件格式进行了规范及定义。另外一种是在gazebo中通过sdf文件格式对机器人也进行了格式规范定义。

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmI0NDVkYjhiNTRkNTE0YjI1OTgyNGVlY2M2MGQwMjRfZTQ0OTAyM2Y0YjBiYzIwNGFhNDFkN2YyMjI0MGE0OTFfSUQ6NzY1MDg4ODIzMTUzNDk4ODI2Nl8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

这两种模型文件都可以用来描述机器人模型，在gazebo进行仿真时，系统需要将urdf转换成sdf文件在gazebo中展示，所以，在本项目中，我直接采用sdf文件格式来描述小车，内容如下：

```XML
<?xml version="1.0"?>
<sdf version="1.7">
  <model name="vehicle_blue">
    <link name="base_footprint">
      <inertial>
        <mass>0</mass>
        <inertia>
          <ixx>0.1</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.1</iyy>
          <iyz>0</iyz>
          <izz>0.1</izz>
        </inertia>
      </inertial>
    </link>
    <link name="base_link">
      <visual name="base_link_visual_0">
        <geometry>
          <box>
            <size>0.667 0.333 0.167</size>
          </box>
        </geometry>
        <material>
          <ambient>0.00000392 0.00000392 1.00000000 1.00000000</ambient>
          <diffuse>0.00000392 0.00000392 1.00000000 1.00000000</diffuse>
        </material>
      </visual>
      <collision name="base_link_collision_0">
        <pose>0 0 0.05 0 0 0</pose>
        <geometry>
          <box>
            <size>0.667 0.333 0.167</size>
          </box>
        </geometry>
      </collision>
      <inertial>
        <mass>1.14395</mass>
        <inertia>
          <ixx>0.095329</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.381317</iyy>
          <iyz>0</iyz>
          <izz>0.476646</izz>
        </inertia>
      </inertial>
    </link>
    <link name="left_wheel">
      <pose>-0.167 0.2 0 0 0 0</pose>
      <visual name="left_wheel_visual_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.133</radius>
            <length>0.067</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>1.00000000 0.00000392 0.00000392 1.00000000</ambient>
          <diffuse>1.00000000 0.00000392 0.00000392 1.00000000</diffuse>
        </material>
      </visual>
      <collision name="left_wheel_collision_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.133</radius>
            <length>0.067</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>1</mass>
        <inertia>
          <ixx>0.043333</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.08</iyy>
          <iyz>0</iyz>
          <izz>0.043333</izz>
        </inertia>
      </inertial>
    </link>
    <link name="right_wheel">
      <pose>-0.167 -0.2 0 0 0 0</pose>
      <visual name="right_wheel_visual_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.133</radius>
            <length>0.067</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>1.00000000 0.00000392 0.00000392 1.00000000</ambient>
          <diffuse>1.00000000 0.00000392 0.00000392 1.00000000</diffuse>
        </material>
      </visual>
      <collision name="right_wheel_collision_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.133</radius>
            <length>0.067</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>1</mass>
        <inertia>
          <ixx>0.043333</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.08</iyy>
          <iyz>0</iyz>
          <izz>0.043333</izz>
        </inertia>
      </inertial>
    </link>
    <link name="caster_wheel">
      <pose>0.33 0 0 0 0 0</pose>
      <visual name="caster_wheel_visual_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.13</radius>
            <length>0.01</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>0.50000000 0.50000000 0.50000000 1.00000000</ambient>
          <diffuse>0.50000000 0.50000000 0.50000000 1.00000000</diffuse>
        </material>
      </visual>
      <collision name="caster_wheel_collision_0">
        <pose>0 0 0 1.5707963 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.13</radius>
            <length>0.01</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>0.1</mass>
        <inertia>
          <ixx>0.00008</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.00008</iyy>
          <iyz>0</iyz>
          <izz>0.00008</izz>
        </inertia>
      </inertial>
    </link>
    <link name="laser_cylinder_link">
      <pose>0.3 0 0.12 0 0 0</pose>
      <visual name="laser_cylinder_link_visual_0">
        <geometry>
          <cylinder>
            <radius>0.01</radius>
            <length>0.3</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>0.00000000 0.00000000 0.00000000 0.80000000</ambient>
          <diffuse>0.00000000 0.00000000 0.00000000 0.80000000</diffuse>
        </material>
      </visual>
      <collision name="laser_cylinder_link_collision_0">
        <pose>0 0 0.05 0 0 0</pose>
        <geometry>
          <cylinder>
            <radius>0.01</radius>
            <length>0.05</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>0.01</mass>
        <inertia>
          <ixx>0.043333</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.08</iyy>
          <iyz>0</iyz>
          <izz>0.043333</izz>
        </inertia>
      </inertial>
    </link>

    <link name="laser_link">
      <pose>0.3 0 0.27 0 0 0</pose>
      <visual name="laser_link_visual_0">
        <geometry>
          <cylinder>
            <radius>0.02</radius>
            <length>0.05</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>0.00000000 0.00000000 0.00000000 0.80000000</ambient>
          <diffuse>0.00000000 0.00000000 0.00000000 0.80000000</diffuse>
        </material>
      </visual>
      <collision name="laser_link_collision_0">
        <geometry>
          <cylinder>
            <radius>0.02</radius>
            <length>0.02</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>0.03</mass>
        <inertia>
          <ixx>0</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0</iyy>
          <iyz>0</iyz>
          <izz>0</izz>
        </inertia>
      </inertial>

      <sensor name="hls_lfcd_lds" type="gpu_lidar">
          <always_on>true</always_on>
          <visualize>true</visualize>
          <pose>0 0 0 0 0 0</pose>
          <update_rate>5</update_rate>
          <topic>/scan</topic>
          <gz_frame_id>laser_link</gz_frame_id>
          <ray>
              <scan>
                  <horizontal>
                      <samples>360</samples>
                      <resolution>1.000000</resolution>
                      <min_angle>0.000000</min_angle>
                      <max_angle>6.280000</max_angle>
                  </horizontal>
              </scan>
              <range>
                  <min>0.00001</min>
                  <max>20.0</max>
                  <resolution>0.015000</resolution>
              </range>
              <noise>
                  <type>gaussian</type>
                  <mean>0.0</mean>
                  <stddev>0.01</stddev>
              </noise>
          </ray>
      </sensor>
    </link>

    <joint name="caster_joint" type="revolute">
      <parent>base_link</parent>
      <child>caster_wheel</child>
      <axis>
        <xyz>0 1 0</xyz>
        <use_parent_model_frame>false</use_parent_model_frame>
        <limit>
          <lower>-3.1415927</lower>
          <upper>3.1415927</upper>
          <effort>100</effort>
          <velocity>10</velocity>
        </limit>
      </axis>
    </joint>
    <joint name="base_joint" type="fixed">
      <parent>base_footprint</parent>
      <child>base_link</child>
    </joint>
    <joint name="left_wheel_joint" type="revolute">
      <parent>base_link</parent>
      <child>left_wheel</child>
      <axis>
        <xyz>0 1 0</xyz>
        <use_parent_model_frame>false</use_parent_model_frame>
        <limit>
          <lower>-1.79769e+308</lower>
          <upper>1.79769e+308</upper>
          <effort>100</effort>
          <velocity>10</velocity>
        </limit>
      </axis>
    </joint>
    <joint name="right_wheel_joint" type="revolute">
      <parent>base_link</parent>
      <child>right_wheel</child>
      <axis>
        <xyz>0 1 0</xyz>
        <use_parent_model_frame>false</use_parent_model_frame>
        <limit>
          <lower>-1.79769e+308</lower>
          <upper>1.79769e+308</upper>
          <effort>100</effort>
          <velocity>10</velocity>
        </limit>
      </axis>
    </joint>
    <joint name="laser_cylinder_joint" type="fixed">
      <parent>base_link</parent>
      <child>laser_cylinder_link</child>
    </joint>
    <joint name="laser_joint" type="fixed">
      <parent>laser_cylinder_link</parent>
      <child>laser_link</child>
    </joint>

          <plugin
              filename="gz-sim-diff-drive-system"
              name="gz::sim::systems::DiffDrive">
              <left_joint>left_wheel_joint</left_joint>
              <right_joint>right_wheel_joint</right_joint>
              <wheel_separation>0.4</wheel_separation>
              <wheel_radius>0.133</wheel_radius>
              <max_linear_acceleration>2.0</max_linear_acceleration>
              <min_linear_acceleration>-2.0</min_linear_acceleration>
              <max_angular_acceleration>3.0</max_angular_acceleration>
              <min_angular_acceleration>-3.0</min_angular_acceleration>
              <max_linear_velocity>1.5</max_linear_velocity>
              <min_linear_velocity>-1.5</min_linear_velocity>
              <max_angular_velocity>3.0</max_angular_velocity>
              <min_angular_velocity>-3.0</min_angular_velocity>
              <topic>/cmd_vel</topic>
              <odom_topic>/odom</odom_topic>
              <tf_topic>/tf</tf_topic>
              <frame_id>odom</frame_id>
              <child_frame_id>base_footprint</child_frame_id>
              <odom_publish_frequency>1000</odom_publish_frequency>
          </plugin>
          <plugin
              filename="gz-sim-joint-state-publisher-system"
              name="gz::sim::systems::JointStatePublisher">
              <joint_name>left_wheel_joint</joint_name>
              <joint_name>right_wheel_joint</joint_name>
              <topic>/joint_states</topic>
              <update_rate>30</update_rate>
          </plugin>

          <plugin
              filename="gz-sim-sensors-system"
              name="gz::sim::systems::Sensors">
              <render_engine>ogre2</render_engine>
          </plugin>
           <!-- <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>-->
          <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/> 
    </model>

</sdf>

```



### 模型编辑

这里要特别说明一下，小车模型如果编辑不正确，在加载gazebo的时候会出错，所以大家在编辑小车模型的时候需要特别注意，这个sdf文件有严格的规范要求，可以参见：http://sdformat\.org/

对于小车模型的编辑，可以使用：https://urdf\.d\-robotics\.cc/ 在线工具来进行导入编辑，编辑完成后可以导出为urdf或者sdf文件格式。



### 世界模型

世界模型文件是gazebo的整体环境模型，也是采用sdf文件来进行描述，使用https://urdf\.d\-robotics\.cc/打开显示不全，因为上面这个网站主要针对urdf文件，而urdf文件中只能包含一个model元素，所以会导致世界模型导入显示不完整。

```XML
<?xml version="1.0"?>
<sdf version="1.10">
  <world name="default">
    
    <!-- 🌍 地面（使用在线 Fuel URL） -->
    <include>
      <uri>https://fuel.gazebosim.org/1.0/OpenRobotics/models/Ground Plane</uri>
    </include>

    <!-- ☀️ 太阳光 -->
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 20 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <!-- ============================================ -->
    <!-- 🧱 外墙（4面，前墙带入户大门洞） -->
    <!-- ============================================ -->

    <!-- 后墙 (y=12) - 完整 -->
    <model name="wall_back">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>24 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>24 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>0 12 3 0 0 0</pose>
    </model>

    <!-- 前墙 (y=-12) - 带入户大门洞（门宽3m，分成左右两段） -->
    <model name="wall_front_left">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>10.5 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>10.5 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-6.75 -12 3 0 0 0</pose>
    </model>

    <model name="wall_front_right">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>10.5 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>10.5 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>6.75 -12 3 0 0 0</pose>
    </model>

    <!-- 左墙 (x=-12) - 完整 -->
    <model name="wall_left">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 24 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 24 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-12 0 3 0 0 0</pose>
    </model>

    <!-- 右墙 (x=12) - 完整 -->
    <model name="wall_right">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 24 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 24 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>12 0 3 0 0 0</pose>
    </model>

    <!-- ============================================ -->
    <!-- 🚪 房间分隔墙（墙上直接开门洞） -->
    <!-- ============================================ -->

    <!-- 主卧与次卧之间的墙 (x=0, y=8 to y=12) - 完整 -->
    <model name="wall_master_second">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 8 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 8 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>0 8 3 0 0 0</pose>
    </model>

    <!-- 主卧南墙 (y=4, x=-12 to x=0) - 带门洞（门宽2m，分成两段墙） -->
    <model name="wall_master_south_left">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-10.5 4 3 0 0 0</pose>
    </model>

    <model name="wall_master_south_right">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-3.5 4 3 0 0 0</pose>
    </model>

    <!-- 次卧南墙 (y=4, x=0 to x=12) - 带门洞（门宽2m，分成两段墙） -->
    <model name="wall_second_south_left">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>7 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>7 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>3.5 4 3 0 0 0</pose>
    </model>

    <model name="wall_second_south_right">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>3 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>10.5 4 3 0 0 0</pose>
    </model>

    <!-- 书房东墙 (x=-4, y=-6 to y=4) - 带门洞（门宽2m，分成两段墙） -->
    <model name="wall_study_east_bottom">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 5 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 5 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-4 -3.5 3 0 0 0</pose>
    </model>

    <model name="wall_study_east_top">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 3 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 3 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-4 2.5 3 0 0 0</pose>
    </model>

    <!-- 儿童房西墙 (x=4, y=-6 to y=4) - 带门洞（门宽2m，分成两段墙） -->
    <model name="wall_children_west_bottom">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 5 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 5 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>4 -3.5 3 0 0 0</pose>
    </model>

    <model name="wall_children_west_top">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>0.4 3 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>0.4 3 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>4 2.5 3 0 0 0</pose>
    </model>

    <!-- 客厅北墙 (y=-6, x=-4 to x=4) - 带厨房门洞（门宽3m，分成两段墙） -->
    <model name="wall_living_north_left">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>2.5 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>2.5 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>-2.75 -6 3 0 0 0</pose>
    </model>

    <model name="wall_living_north_right">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box>
              <size>2.5 0.4 6</size>
            </box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box>
              <size>2.5 0.4 6</size>
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
      </link>
      <pose>2.75 -6 3 0 0 0</pose>
    </model>

  </world>
</sdf>

```

## ros2的节点启动文件

在nav2安装后，可以通过ros2 launch nav2\_bringup tb3\_simulation\_launch\.py headless:=False命令来查看演示的小车导航程序。

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzAzYWIxZDZmZGI0YmJhNzUwOGM4ZTMyZGJjNTA3MDlfOTlhOWZlOTg2MWZhMGE2ZmEwYWNiNGJkYTdlZDE5OThfSUQ6NzY1MTIyMzU2NzQ0ODI4MDI0NV8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)

如果上图可以正常显示，说明nav2安装时成功的。

之后可以编辑自己的工程项目，加载自己的小车程序。

https://gitee\.com/idlity/myfirst\_robot\.git

上面是我编写的小车加载launch加载程序，大家可以免费下载。



### launch加载文件说明

在绘制地图的逻辑中，核心加载节点有下面几个：

1、打开ros\_gz\_sim加载世界模型

2、加载robot\_state\_publisher节点，发布关节坐标转换

3、使用spawn\_tb3\.launch\.py在gazebo中动态创建机器人模型

4、使用rviz\_launch\.py打开rviz

```Python
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

def generate_launch_description():
    sim_dir = get_package_share_directory('nav2_minimal_tb3_sim')
    bringup_dir = get_package_share_directory('nav2_bringup')
    project_dir = get_package_share_directory('myfirst_robot')
    launch_dir = os.path.join(bringup_dir, 'launch')
    use_sim_time = LaunchConfiguration('use_sim_time', default='True')
    use_namespace = LaunchConfiguration('use_namespace')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    use_rviz = LaunchConfiguration('use_rviz')

    sdf_file = os.path.join(project_dir, 'model', 'myrobotv52.sdf')

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

    with open(sdf_file, 'r') as infp:
        robot_description = infp.read()

    # ✅ 1. Gazebo 世界文件
    world_file = os.path.join(project_dir, 'model', 'myworld_simple_hourse.sdf')
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to world model file to load',
    )

    #使用gazebo打开世界模型
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': LaunchConfiguration('world'),##注意这里的参数，如果使用world则，无法加载，必须使用gz_args
            'use_sim_time': use_sim_time,
        }.items()
    )

    #2.启动发布机器人坐标服务
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time, 'robot_description': robot_description}
        ]
    )

    pose = {
        'x': LaunchConfiguration('x_pose', default='2.00'),
        'y': LaunchConfiguration('y_pose', default='0.50'),
        'z': LaunchConfiguration('z_pose', default='0.30'),
        'R': LaunchConfiguration('roll', default='0'),
        'P': LaunchConfiguration('pitch', default='0.00'),
        'Y': LaunchConfiguration('yaw', default='0.00'),
    }

    robot_name = LaunchConfiguration('robot_name')
    robot_sdf = LaunchConfiguration('robot_sdf')
    namespace = LaunchConfiguration('namespace')

    #3、在gazebo中创建机器人模型
    gz_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_dir, 'launch', 'spawn_tb3.launch.py')),
        launch_arguments={'namespace': namespace,
                            'use_sim_time': use_sim_time,
                            'robot_name': robot_name,
                            'robot_sdf': robot_sdf,
                            'x_pose': pose['x'],
                            'y_pose': pose['y'],
                            'z_pose': pose['z'],
                            'roll': pose['R'],
                            'pitch': pose['P'],
                            'yaw': pose['Y']}.items()
    )

    #4、打开rviz
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

    return LaunchDescription([
        declare_world_cmd,
        gazebo,
        start_robot_state_publisher_cmd,  # 先启动
        declare_robot_name_cmd,
        declare_robot_sdf_cmd,
        declare_namespace_cmd,
        gz_robot,

        declare_use_rviz_cmd,
        declare_use_namespace_cmd,
        declare_rviz_config_file_cmd,
        rviz_cmd,
    ])

```

## 编译运行

代码编辑好以后，在项目myfirst\_node下运行colcon build编译项目。

如果找不到colcon 命令，需要安装：sudo apt install python3\-colcon\-common\-extensions

编译通过，执行如下命令，启动运行：

```Plain Text
source ./install/setup.bash
ros2 launch myfirst_robot my_robot_nav2_launchv3_hourse.py
```

如果运行正常的话，会显示房间地图和小车，可以在gazebo中增加teleop来控制小车行走。

## 启动slam工具

使用如下命令，启动slam工具

```Plain Text
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=True
```

## 启动模拟，控制小车移动

在rviz中点击加载模型（robotModel），稍等片刻，即可以看到完整的小车，如果小车始终是白色，则说明小车的关节定义不完整，需要检查。

可以使用使用命令：ros2 run tf2\_tools view\_frames 查看消息树，如果消息树不完整，则小车会无法加载。



# 保存地图

在slam工具中已经内嵌了保存地图的工具，可以直接使用命令保存地图即可

```Plain Text
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap   "{name: {data: '/root/my_map'}}"
```

地图正确保存后，会生成两个文件my\_map\.yaml和my\_map\.pgm样式如下：

my\_map\.yaml的样式如下：

```YAML
image: my_map.pgm                #地图图片文件名，相对路径，与 YAML 文件同目录
mode: trinary                    #像素值解读模式
resolution: 0.050                #每个像素 = 0.05 米 = 5 厘米
origin: [-15.699, -16.428, 0]    #地图左下角第一个像素在世界坐标系中的位置 (x, y, yaw)
negate: 0                        #是否反转黑白：0=不反转，1=反转
occupied_thresh: 0.65            #像素值 ≥ 0.65 → 判定为障碍物
free_thresh: 0.196               #像素值 ≤ 0.196 → 判定为空闲区域
```



my\_map\.pgm内容如下：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWJiZDhiZWJmOWZiZWUzMDZjNGQ0ZTA3NjgwYTQyMWNfMTQ2YWQ5ZGRjZTkzOTJiNjgzYWZlNTkxNDdjZDQzODlfSUQ6NzY1MTIzMDczMjIyODA4NzAwNV8xNzgxNjE1NTQ5OjE3ODE3MDE5NDlfVjM)



