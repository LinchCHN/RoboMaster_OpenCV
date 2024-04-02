#coding=utf-8
import cv2
import numpy as np
import serial.tools.list_ports
#import struct
#import re # 导入正则表达式模块

import mvsdk

def main_loop():
	# 枚举相机
	DevList = mvsdk.CameraEnumerateDevice()
	nDev = len(DevList)
	if nDev < 1:
		print("No camera was found!")
		return
	for i, DevInfo in enumerate(DevList):
		print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
	i = 0 if nDev == 1 else int(input("Select camera: "))
	DevInfo = DevList[i]
	print(DevInfo)
	# 打开相机
	hCamera = 0
	try:
		hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
	except mvsdk.CameraException as e:
		print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
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
	fps = 0
	start_time = cv2.getTickCount()
	while (cv2.waitKey(1) & 0xFF) != 27:  # 27对应esc键的ASCII码
		# 从相机取一帧图片
		try:
			pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
			mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
			mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
			# 此时图片已经存储在pFrameBuffer中，对于彩色相机pFrameBuffer=RGB数据，黑白相机pFrameBuffer=8位灰度数据
			# 把pFrameBuffer转换成opencv的图像格式以进行后续算法处理
			frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
			frame = np.frombuffer(frame_data, dtype=np.uint8)
			frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )
			frame = cv2.flip(frame, 0)
			frame = cv2.resize(frame, (640,480), interpolation = cv2.INTER_LINEAR)

			# 将图像从BGR转换为HSV颜色空间
			hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
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
			contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)[:4]
			# 存储矩形宽度、高度和点的数组
			rects = []
			# 遍历前5个轮廓
			for cont in contours:
				# 获取边界矩形的坐标和尺寸
				x, y, w, h = cv2.boundingRect(cont)
				# 检查有效矩形的条件
				#if h / w >= 2 and h / whole_h > 0.1 and h > w:
				if h / w >= 1.59 and h / w <= 2.49 and h / whole_h > 0.010 and h > w and h / whole_h < 0.9 :
					# print("h:", h)
					# print("w:", w)
					# print("x:", x)
					# print("y:", y)
					# print("h / w:", h / w)
					# print(" h / whole_h:", h / whole_h)
					rects.append([x, y, w, h])
			# 找到面积最接近的两个矩形
			min_value = float('inf')
			best_rects = []
			for i in range(len(rects) - 1):
				for j in range(i + 1, len(rects)):
					value = abs(rects[i][2] * rects[i][3] - rects[j][2] * rects[j][3])
					# 计算xy坐标差距
					y_diff = abs(rects[i][1] - rects[j][1])
					x_diff = abs(rects[i][0] - rects[j][0])
					ratio_range = x_diff / h
					#print("x_diff:", x_diff)
					# print("y_diff:", y_diff)
					# print("value:", value)    # 矩形面积差
					# print("ratio_range:", ratio_range)
					# 添加额外的条件：y坐标差距不能太大
					out = 21914 * x_diff ** -1.063
					print("out:", out)
					if value <= min_value and y_diff <= 25 and 1 <= ratio_range <= 3.7:  # 可改
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
				#print("Middle Point:", middle_point)
				# 定义矩形为多边形并在原始图像上绘制它
				pts = np.array([point1, point2, point4, point3], np.int32).reshape((-1, 1, 2))
				cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
				# cv2.circle(img, (int(center_point1[0]), int(center_point1[1])), radius=5, color=(255, 0, 0), thickness=-1)
				# cv2.circle(img, (int(center_point2[0]), int(center_point2[1])), radius=5, color=(0, 0, 255), thickness=-1)
				cv2.circle(frame, (int(middle_point[0]), int(middle_point[1])), radius=5, color=(0, 255, 255),thickness=-1)

				test_middle_point = int(((int(middle_point[0]) + int(middle_point[1])) / 10) % 10)

				hex_string = f'{int(middle_point[0]):03}{int(middle_point[1]):03}{test_middle_point}'
				#print("Hex String:", hex_string)

				# def send_string_to_com(input_string, com_port='COM3', baudrate=115200, timeout=1):
				# 	try:
				# 		# 将字符串编码为字节数据
				# 		byte_data = input_string.encode('utf-8')
				# 		# 打开串口
				# 		with serial.Serial(com_port, baudrate=baudrate, timeout=timeout) as ser:
				# 			# 将字节写入串口
				# 			ser.write(byte_data)
				# 			#print("成功发送字符串到USB。")
				# 			# 发送换行符
				# 			ser.write(b'\n')
				# 	except Exception as e:
				# # 		#print(f"发送字符串到USB时发生错误：{e}")
				# 
				#
				# # 使用函数发送字符串到COM3端口，波特率为115200
				# string_to_send = hex_string
				# send_string_to_com(string_to_send)

			# 显示摄像头画面
			end_time = cv2.getTickCount()
			elapsed_time = (end_time - start_time)/3/cv2.getTickFrequency()
			fps = 1 / elapsed_time
			start_time = cv2.getTickCount()
			# 在图像上显示帧率
			cv2.putText(frame, "FPS: {:.2f}".format(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
			cv2.imshow("Press ESC Get the fuck out of here.", frame)
		except mvsdk.CameraException as e:
			if e.error_code == mvsdk.CAMERA_STATUS_TIME_OUT:
				# 忽略超时错误
				continue
			elif e.error_code == mvsdk.CAMERA_STATUS_NOT_SUPPORTED:
				print("Not supported error: {}".format(e.message))
			else:
				print("Camera error({}): {}".format(e.error_code, e.message))
				break
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
