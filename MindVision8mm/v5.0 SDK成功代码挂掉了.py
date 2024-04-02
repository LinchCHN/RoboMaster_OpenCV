#coding=utf-8
import cv2
import numpy as np
import mvsdk
import serial.tools.list_ports

def main_loop():
    # 枚举相机
    DevList = mvsdk.CameraEnumerateDevice()
    nDev = len(DevList)
    if nDev < 1:
        print("未找到相机!")
        return

    for i, DevInfo in enumerate(DevList):
        print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
    i = 0 if nDev == 1 else int(input("选择相机: "))
    DevInfo = DevList[i]
    print(DevInfo)

    # 打开相机
    hCamera = 0
    try:
        hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
    except mvsdk.CameraException as e:
        print("相机初始化失败({}): {}".format(e.error_code, e.message))
        return

    # 获取相机特性描述
    cap = mvsdk.CameraGetCapability(hCamera)

    # 判断是黑白相机还是彩色相机
    monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

    # 黑白相机让ISP直接输出MONO数据，而不是扩展成R=G=B的24位灰度
    if monoCamera:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
    else:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

    # 相机模式切换成连续采集
    mvsdk.CameraSetTriggerMode(hCamera, 0)

    # 手动曝光，曝光时间30ms
    mvsdk.CameraSetAeState(hCamera, 0)
    mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

    # 让SDK内部取图线程开始工作
    mvsdk.CameraPlay(hCamera)

    # 计算RGB buffer所需的大小，这里直接按照相机的最大分辨率来分配
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

    # 分配RGB buffer，用来存放ISP输出的图像
    # 备注：从相机传输到PC端的是RAW数据，在PC端通过软件ISP转为RGB数据（如果是黑白相机就不需要转换格式，但是ISP还有其它处理，所以也需要分配这个buffer）
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

    while (cv2.waitKey(1) & 0xFF) != ord('q'):
        # 从相机取一帧图片
        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
            mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

            # 此时图片已经存储在pFrameBuffer中，对于彩色相机pFrameBuffer=RGB数据，黑白相机pFrameBuffer=8位灰度数据
            # 把pFrameBuffer转换成opencv的图像格式以进行后续算法处理
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))
            frame = cv2.flip(frame, 0)
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
            cv2.imshow("按q结束", frame)

        except mvsdk.CameraException as e:
            if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                print("CameraGetImageBuffer失败({}): {}".format(e.error_code, e.message))

            # 将图像从BGR转换为HSV颜色空间
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # 定义蓝色的HSV范围
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])

            # 创建蓝色的掩码
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

            # 对掩码应用高斯模糊
            blue_mask = cv2.GaussianBlur(blue_mask, (5, 5), 0)

            # 获取二值图像的尺寸
            whole_h, _ = blue_mask.shape[:2]

            # 在蓝色掩码中查找轮廓
            _, contours, _ = cv2.findContours(image=blue_mask, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)

            # 将轮廓转换为列表并按面积降序排列
            contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)[:5]

            # 存储矩形宽度、高度和点的数组
            rects = []

            # 遍历前5个轮廓
            for cont in contours:
                # 获取边界矩形的坐标和尺寸
                x, y, w, h = cv2.boundingRect(cont)

                # 检查有效矩形的条件
                if h / w >= 2 and h / whole_h > 0.1 and h > w:
                    rects.append([x, y, w, h])

            # 找到面积最接近的两个矩形
            min_value = float('inf')
            best_rects = []

            for i in range(len(rects) - 1):
                for j in range(i + 1, len(rects)):
                    value = abs(rects[i][2] * rects[i][3] - rects[j][2] * rects[j][3])
                    if value < min_value:
                        min_value = value
                        best_rects = [rects[i], rects[j]]

            # 如果找到了两个最近矩形
            if best_rects:
                # 计算并打印矩形的四个角点
                rectangle1, rectangle2 = best_rects
                point1 = [rectangle1[0] + rectangle1[2] / 2, rectangle1[1]]
                point2 = [rectangle1[0] + rectangle1[2] / 2, rectangle1[1] + rectangle1[3]]
                point3 = [rectangle2[0] + rectangle2[2] / 2, rectangle2[1]]
                point4 = [rectangle2[0] + rectangle2[2] / 2, rectangle2[1] + rectangle2[3]]

                # 两边两个点的中间坐标
                center_point1 = [(point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2]
                center_point2 = [(point3[0] + point4[0]) / 2, (point3[1] + point4[1]) / 2]
                # 中心坐标
                middle_point = [(center_point1[0] + center_point2[0]) / 2, (center_point1[1] + center_point2[1]) / 2]

                # print(point1, point2, point3, point4)
                # print("Center Points:", center_point1, center_point2)
                print("Middle Point:", middle_point)

                # 定义矩形为多边形并在原始图像上绘制它
                pts = np.array([point1, point2, point4, point3], np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

                # cv2.circle(img, (int(center_point1[0]), int(center_point1[1])), radius=5, color=(255, 0, 0), thickness=-1)
                # cv2.circle(img, (int(center_point2[0]), int(center_point2[1])), radius=5, color=(0, 0, 255), thickness=-1)
                cv2.circle(img, (int(middle_point[0]), int(middle_point[1])), radius=5, color=(0, 255, 255),
                           thickness=-1)

                # 获取可用的串口列表
                available_ports = list(serial.tools.list_ports.comports())
                # 打开串口
                # 如果有可用的串口，则打开第一个串口
                if available_ports:
                    port = available_ports[0][0]
                    ser = serial.Serial(port, 9600)

                    # 提取百位
                    hex_middle_point_0 = int(middle_point[0] // 100)
                    if hex_middle_point_0 < 10:
                        hex_middle_point_0 = f'0{hex_middle_point_0}'
                    else:
                        hex_middle_point_0 = str(hex_middle_point_0)
                    # 提取十位和个位
                    hex_middle_point_1 = int(middle_point[0] % 100)
                    if hex_middle_point_1 < 10:
                        hex_middle_point_1 = f'0{hex_middle_point_1}'
                    else:
                        hex_middle_point_1 = str(hex_middle_point_1)
                    # 提取小数点后两位
                    hex_middle_point_2 = int((middle_point[0] % 1) * 100)
                    # 提取百位以上2
                    hex_middle_point_3 = int(middle_point[1] // 100)
                    if hex_middle_point_3 < 10:
                        hex_middle_point_3 = f'0{hex_middle_point_3}'
                    else:
                        hex_middle_point_3 = str(hex_middle_point_3)
                    # 提取十位和个位2
                    hex_middle_point_4 = int(middle_point[1] % 100)
                    if hex_middle_point_4 < 10:
                        hex_middle_point_4 = f'0{hex_middle_point_4}'
                    else:
                        hex_middle_point_4 = str(hex_middle_point_4)
                    # 提取小数点后两位2
                    hex_middle_point_5 = int((middle_point[1] % 1) * 100)

                    hex_string = f'0x0A 0x0B 0x{hex_middle_point_0} 0x{hex_middle_point_1} 0x{hex_middle_point_2} 0x{hex_middle_point_3} 0x{hex_middle_point_4} 0x{hex_middle_point_5} 0x0C 0x0D'

                    print("Hex String:", hex_string)

                    byte_data = hex_string.encode('utf-8')

        # 发送数据到串口
        # if available_ports:
        #     port = available_ports[0][0]
        #     ser = serial.Serial(port, 9600)

            # try:
            #     # 将字节写入串口
            #     ser.write(byte_data)
            #     print("成功发送字符串到USB。")
            # except Exception as e:
            #     print(f"发送字符串到USB时发生错误：{e}")
            # finally:
            #     # 发送换行符
            #     ser.write(b'\n')
            #     # 关闭串口
            #     ser.close()
            # else:
            # print("未找到可用的 COM 端口。")

    # 关闭相机
    mvsdk.CameraUnInit(hCamera)

    # 释放帧缓存
    mvsdk.CameraAlignFree(pFrameBuffer)

def main():
    try:
        main_loop()
    finally:
        cv2.destroyAllWindows()

main()
