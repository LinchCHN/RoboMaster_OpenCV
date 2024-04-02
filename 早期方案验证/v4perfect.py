import cv2
import numpy as np
import serial.tools.list_ports
#import struct
#import re  # 导入正则表达式模块
def decrease_brightness(img, factor):
    # 创建一个与图像大小相同的全黑图像
    darkened_img = np.zeros_like(img)
    # 将图像与全黑图像按权重相加，减小亮度
    darkened_img = cv2.addWeighted(img, 1 - factor, darkened_img, factor, 0)
    return darkened_img
video = cv2.VideoCapture(0)
# 设置摄像头参数
video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
video.set(cv2.CAP_PROP_FPS, 60)
if video.isOpened():
    print("摄像头0已成功打开。")
else:
    print("无法打开摄像头0，请检查摄像头是否连接正常。")
    exit()
fps = 0
start_time = cv2.getTickCount()
while True:
    # 从摄像头读取一帧
    ret, img = video.read()
    # 如果读取失败，退出循环
    if not ret:
        break
    # 调用函数应用光圈效果
    #darkened_img = decrease_brightness(img, 0.8)
    img = decrease_brightness(img, 0.8)
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
    _,contours, _ = cv2.findContours(image=blue_mask, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
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
        #中心坐标
        middle_point = [(center_point1[0] + center_point2[0]) / 2, (center_point1[1] + center_point2[1]) / 2]
        #print(point1, point2, point3, point4)
        #print("Center Points:", center_point1, center_point2)
        print("Middle Point:", middle_point)
        # 定义矩形为多边形并在原始图像上绘制它
        pts = np.array([point1, point2, point4, point3], np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        #cv2.circle(img, (int(center_point1[0]), int(center_point1[1])), radius=5, color=(255, 0, 0), thickness=-1)
        #cv2.circle(img, (int(center_point2[0]), int(center_point2[1])), radius=5, color=(0, 0, 255), thickness=-1)
        cv2.circle(img, (int(middle_point[0]), int(middle_point[1])), radius=5, color=(0, 255, 255), thickness=-1)
        # # 获取可用的串口列表
        # available_ports = list(serial.tools.list_ports.comports())
        # # 打开串口
        # # 如果有可用的串口，则打开第一个串口
        # if available_ports:
        #     port = available_ports[0][0]
        #     ser = serial.Serial(port, 9600)
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
        #hex_middle_point_2 = int((middle_point[0] % 1) * 100)
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
        #hex_middle_point_5 = int((middle_point[1] % 1) * 100)
            
        #hex_string = f'0x0A 0x0B 0x{hex_middle_point_0} 0x{hex_middle_point_1} 0x{hex_middle_point_2} 0x{hex_middle_point_3} 0x{hex_middle_point_4} 0x{hex_middle_point_5} 0x0C 0x0D'
        hex_string = f'{hex_middle_point_0}{hex_middle_point_1}{hex_middle_point_3}{hex_middle_point_4}'
        print("Hex String:", hex_string)

        def send_string_to_com(input_string, com_port='COM3', baudrate=115200, timeout=1):
            try:
                # 将字符串编码为字节数据
                byte_data = input_string.encode('utf-8')
                # 打开串口
                with serial.Serial(com_port, baudrate=baudrate, timeout=timeout) as ser:
                    # 将字节写入串口
                    ser.write(byte_data)
                    print("成功发送字符串到USB。")
                    # 发送换行符
                    ser.write(b'\n')
            except Exception as e:
                print(f"发送字符串到USB时发生错误：{e}")
            # 使用函数发送字符串到COM3端口，波特率为115200
        string_to_send = hex_string
        send_string_to_com(string_to_send)

    # 显示摄像头画面
    end_time = cv2.getTickCount()
    elapsed_time = (end_time - start_time)/1/cv2.getTickFrequency()
    fps = 1 / elapsed_time
    start_time = cv2.getTickCount()
    # 在图像上显示帧率
    cv2.putText(img, "FPS: {:.2f}".format(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Press ESC Get the fuck out of here.", img)
    #cv2.imshow('Blurred Image', darkened_img)
    # 检查是否按下 'esc' 键以退出循环
    if cv2.waitKey(1) & 0xFF == 27:
        break
video.release() 
cv2.destroyAllWindows()





