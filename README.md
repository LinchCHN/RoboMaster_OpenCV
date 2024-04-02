此方案为2024赛季RoboMaster装甲板识别视觉代码框架

****
>   本识别的写法主要面向视觉新人，以最基础的计算机图形学为主，高效识别红蓝装甲


本地环境配置：

* CUDA12.2 PyTorch
* OpenCV3.4.2：[编译安装](https://github.com/opencv/opencv.git)
* python3.8
* numpy  serial：python 包，用于数据处理和串口打开，安装方式：```pip install numpy```  ```serial同```
* mvsdk 本战队使用的是MindVision的摄像头，import一个官方的SDK


硬件配置：

-   Nuc8 和Nuc12：由于没有合适的 USB 3.0 的滑环，minipc直接装在yaw轴之上，供电需要走拓展接口，需要考虑供电性能，尤其是Nuc12，20v6A的供电需要较粗的接线和加粗布线的拓展pcb
-   USB 转 TTL：实现和A板的通信，TTL可以直接接在接近nuc开关一侧，优点是开机上电且不同版本该usb口固定为com3，需要安装ch340驱动，以便收发通信
-   camera-imu：MindVision 相机，需要安装相机驱动，本地封装代码时需把mvsdk复制到pyinstaller所产生的exe文件之下
-   

