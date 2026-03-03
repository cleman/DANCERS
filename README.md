# DANCERS (Student Branch Fork)

This repository is a fork of the original [DANCERS](https://github.com/Chroma-CITI/DANCERS) project. The purpose of this fork is to provide a simplified and lighter version for the "master-etudiants" branch by removing files not essential for the coursework.

---

## About the Original DANCERS Project

DANCERS is a co-simulator suited for multi-robot simulation. It merges any multi-robot simulator with any network simulator to enable the study of Networked Multi-Robot Systems (NMRS).

The complete documentation for the original DANCERS project can be found in the [wiki](https://github.com/Chroma-CITI/DANCERS/wiki). It includes installation instructions and tutorials of increasing complexity showing what can be done with DANCERS.

DANCERS was first introduced in [a conference paper at SIMPAR 2025](https://ieeexplore.ieee.org/document/10979148).

---

## Installation -- Compile from source

These instructions are basically the content of the Dockerfile, but with more explanations. They were tested on Ubuntu 22.04 and Ubuntu 24.04.

The easiest way to compile DANCERS is with the `colcon` tool from ROS2. 

1. [Install ROS2](https://docs.ros.org/en/humble/Installation.html) (DANCERS was developed and tested with ROS2 Humble and ROS2 Kilted)
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
If you have any problem with the first build, start only with dancers_msgs
```bash
colcon build --cmake-args -DCMAKE_CXX_FLAGS='-w' --select-packages dancers_msgs
```
7. Finally, you can test if DANCERS was properly installed by running the tutorials:
```sh
cd sim_ws
python3 src/launch/tutorials/launch_tutorial_1.py
```