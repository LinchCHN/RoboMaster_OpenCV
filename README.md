此方案为天禄战队2023-2024赛季RoboMaster装甲板识别视觉代码框架

****
>   本识别的写法主要面向本战队视觉新人的教学，以最基础的计算机图形学为主，高效识别红蓝装甲


本地环境配置：

* CUDA12.2 + PyTorch + Anaconda  
* OpenCV3.4.2：[编译安装](https://github.com/opencv/opencv.git)
* python3.8：不想报错的话至少配置一个3.5+的环境，编辑器使用顺手的就行，Linch使用的是jupyter（方便方案验证）和PyCharm（使用顺手）这两个在运行代码的时候会根据版本不同出现libtiff等库的不通用，在本代码中可以选择性加减```_,```来防止contours的报错
* numpy  serial：python 包，用于数据处理和串口打开，安装方式：```pip install numpy```  ```serial同```
* mvsdk 本战队使用的是MindVision的摄像头，import一个官方的SDK



硬件配置：

-   Nuc8 和Nuc12：由于没有合适的 USB 3.0 的滑环，minipc直接装在yaw轴之上，供电需要走拓展接口，需要考虑供电性能，尤其是Nuc12，20v6A的供电需要较粗的接线和加粗布线的拓展pcb
-   USB 转 TTL：实现和A板的通信，TTL可以直接接在接近nuc开关一侧，优点是开机上电且不同版本该usb口固定为com3，需要安装ch340驱动，以便收发通信
-   camera-imu：MindVision 相机，需要安装相机驱动，本地封装代码时需把mvsdk复制到pyinstaller所产生的exe文件之下
-   bat文件，开机自启方便调试


框架
```txt
├── MindVison12m: 距离函数适用于12m的镜头的各个版本的历史版本
├── MindVison8m: 距离函数适用于8m的镜头的各个版本的历史版本
├── 方案验证: 验证了usb免驱摄像头在曝光时间短，或小光圈等低照明环境下使用hsv结合计算机图形学识别装甲的可能性的各个版本的代码
├── README.md：本文档
├── blue12mm：一个可以用来展示代码效果的版本，若使用以上配置搭建环境，可以使用mindvision相机调节光圈观察装甲板识别效果
```

<br>
后续将抽空整理跟进加入弹道补偿和不同装甲识别以及小陀螺状态装甲位置预测的算法，以及能量机关的识别击打方案
从PCB到Keil到机器学习没什么能战队留下的，遂留下点基础教程。如果您觉得本项目有用的请点一个 Star ！：）
