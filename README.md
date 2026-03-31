# DANCERS (Student Branch Fork)

This repository is a fork of the original [DANCERS](https://github.com/Chroma-CITI/DANCERS) project. The purpose of this fork is to provide a simplified and lighter version for the "master-etudiants" branch by removing files not essential for the coursework.

---

## About the Original DANCERS Project

DANCERS is a co-simulator suited for multi-robot simulation. It merges any multi-robot simulator with any network simulator to enable the study of Networked Multi-Robot Systems (NMRS).

The complete documentation for the original DANCERS project can be found in the [wiki](https://github.com/Chroma-CITI/DANCERS/wiki). It includes installation instructions and tutorials of increasing complexity showing what can be done with DANCERS.

DANCERS was first introduced in [a conference paper at SIMPAR 2025](https://ieeexplore.ieee.org/document/10979148).

---

## Installation -- Compile from source

These instructions are basically the content of the Dockerfile, but with more explanations. They were tested on Ubuntu 22.04 and Ubuntu 24.04.

The easiest way to compile DANCERS is with the `colcon` tool from ROS2. 

1. [Install ROS2](https://docs.ros.org/en/humble/Installation.html) (DANCERS was developed and tested with ROS2 Humble and ROS2 Jazzy)
2. Install dependencies
```sh
sudo apt update && apt install -y --no-install-recommends git cmake wget lsb-release gnupg libqt5gui5 ubuntu-gnome-desktop g++ python3 freeglut3-dev tmux nano gdb
```
3. If you wish to use Gazebo, install it (DANCERS was developed and tested with Gazebo Garden and Harmonic)
```sh
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg 
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt update && sudo apt install -y \
    gz-harmonic
```
4. If you wish to use the PX4 Autopilot, install it (DANCERS was developed and tested with PX4 1.14 and 1.16)
```sh
git clone https://github.com/PX4/PX4-Autopilot.git --recursive --branch release/1.16

# If you want to use Gazebo Harmonic with the PX4 Autopilot, you need this commit, but it is not needed for Gazebo Garden:
git fetch https://github.com/jmackay2/PX4-Autopilot.git fix_gazebo_harmonic:fix_gazebo_harmonic
git cherry-pick bf4408b772f2bc398a5398dabd4bfa67a96ec1b5

cd PX4-Autopilot 

./Tools/setup/ubuntu.sh

make px4_sitl_default

# Install MicroXRCE-DDS Agent
git clone https://github.com/eProsima/Micro-XRCE-DDS-Agent.git && \
    cd Micro-XRCE-DDS-Agent && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make && \
    make install && \
    ldconfig /usr/local/lib/
```
5. Source ROS2 in the `.bashrc`
```sh
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /home/$USERNAME/sim_ws/install/setup.bash" >> ~/.bashrc
```
6. Build DANCERS
```sh
git clone -b v1.0 https://github.com/Chroma-CITI/DANCERS sim_ws --recursive
cd sim_ws
colcon build --cmake-args -DCMAKE_CXX_FLAGS='-w'
export GZ_SIM_RESOURCE_PATH=/home/$USERNAME/PX4-Autopilot/Tools/simulation/gz/models 
export ROS_WS=/home/$USERNAME/sim_ws
```
If you have a with the first build, try to start only with dancers_msgs
```bash
colcon build --cmake-args -DCMAKE_CXX_FLAGS='-w' --select-packages dancers_msgs
```
7. Finally, you can test if DANCERS was properly installed by running the tutorials:
```sh
cd sim_ws
python3 src/launch/tutorials/launch_tutorial_1.py
```

## Usage Guide

### 1. Launching the simulation

The main tutorial script handles the orchestration of Gazebo, PX4, SLAM and Nav2 components within a `tmux` session.

**Launch without a specific world:**
```sh
python3 src/launch/tutorials/launch_tutorial_M1.py
```

**Launch with a specific world (e.g., "walls"):**
```sh
python3 src/launch/tutorials/launch_tutorial_M1.py -w walls
```

Worlds file are located in: `src/physics_connector/Gazebo/worlds`.

### 2. Managing the Environment (Tmux)

The simulation runs multiple processes in a `tmux` session named `dancers_1`.
* **Detach from session:** `Ctrl+b` then `d`
* **Reattach to session:** `tmux attach-session -t dancers_1`
* **Kill the session:** `tmux kill-session -t dancers_1`

### 3. Drone Control & Modes
The default mode is `Offboard`. \
You can switch how the drone is controlled via ROS2 parameters:

* **Position Mode (Manuel/Controller):**
```sh
ros2 param set /waypoint_control control_mode position
```

* **Offboard Mode (Computer/Autonomous):**
```sh
roos2 param set /waypoint_control control_mode offboard
```

**Sending a Waypoint Command:**
To send a single waypoint (x, y, z) to the drone:
```sh
ros2 topic pub /px4_0/waypoint geometry_msgs/msg/Point "{x: 2.0, y: 3.0, z: 1.0}" --once
```

### 4. Local Mapping (Nav2)
The simulation includes a local costmap for obstacle avoidance.

* **Configuration file:** `src/launch/tutorials/nav2_params.yaml``(includes wall inflation parameters).

* **Costmap Topics:** You can visualize or access the costmap via:
    * `/costmap`
    * `/costmap_update`

### 5. Ground Control Station
It is necessary to launch **QGroundControl** alongside the simultion to monitor the PX4 heartbeat, home setup, and flight modes.

### 6. Global Mapping
The simulation includes slam_toolbox tools to build a global map.
The map is available on the topic `/map`.