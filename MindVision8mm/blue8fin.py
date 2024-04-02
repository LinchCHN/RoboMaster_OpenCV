
#coding=utf-8
import cv2
import numpy as np
import serial.tools.list_ports
import mvsdk
def main_loop():
	DevList = mvsdk.CameraEnumerateDevice()
	nDev = len(DevList)
	if nDev < 1:
		print("没有™的摄像头!")
		return
	for i, DevInfo in enumerate(DevList):
		print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
	i = 0 if nDev == 1 else int(input("Select camera: "))
	DevInfo = DevList[i]
	print(DevInfo)
	hCamera = 0
	try:
		hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
	except mvsdk.CameraException as e:
		print("CameraInit Failed({}): {}".format(e.error_code, e.message))
		return
	cap = mvsdk.CameraGetCapability(hCamera)
	monoCamera = (cap.sIspCapacity.bMonoSensor != 0)
	if monoCamera:
		mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
	else:
		mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
	mvsdk.CameraSetTriggerMode(hCamera, 0)
	# 手动曝光，曝光时间30ms
	mvsdk.CameraSetAeState(hCamera, 0)
	mvsdk.CameraSetExposureTime(hCamera, 15 * 1000)
	# 让SDK内部取图线程开始工作
	mvsdk.CameraPlay(hCamera)
	FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)
	pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
	fps = 0
	start_time = cv2.getTickCount()
	while (cv2.waitKey(1) & 0xFF) != 27:  # 27对应esc键的ASCII码

		try:
			pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
			mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
			mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
			frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
			frame = np.frombuffer(frame_data, dtype=np.uint8)
			frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )
			frame = cv2.flip(frame, 0)
			frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
			# 将图像从BGR转换为HSV颜色空间
			hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
			# 定义蓝色的HSV范围
			lower_blue = np.array([100, 50, 50])
			upper_blue = np.array([130, 255, 255])
			blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
			blue_mask = cv2.GaussianBlur(blue_mask, (5, 5), 0)
			whole_h, _ = blue_mask.shape[:2]
			_, contours, _ = cv2.findContours(image=blue_mask, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
			contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)[0:5]
			rects = []
			for cont in contours:
				x, y, w, h = cv2.boundingRect(cont)
				if h / w >= 1.59 and h/w <= 2.49 and h / whole_h > 0.010 and h > w and h / whole_h < 0.9:
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
					if x_diff != 0:
						ratio_range = x_diff / h
						out = 21914 * x_diff ** -1.063
					else:
						# 当x_diff为0时，可以赋予一个默认值或者跳过后续依赖于out的计算
						out = float('0')  # 或者选择一个不会导致错误的默认值
						ratio_range = 2  # 或者根据需求设定其他合理值
					#print("x_diff:", x_diff)
					# print("y_diff:", y_diff)
					# print("value:", value)    # 矩形面积差
					# print("ratio_range:", ratio_range)
					# 添加额外的条件：y坐标差距不能太大
					#out = 43387 * x_diff ** -1.124
					#print("out:", out)
					if value <= min_value and y_diff <= 15 and 1 <= ratio_range <= 3.5:  # 可改
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
				print("8Middle Point:", middle_point)
				# 定义矩形为多边形并在原始图像上绘制它
				pts = np.array([point1, point2, point4, point3], np.int32).reshape((-1, 1, 2))
				cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
				cv2.circle(frame, (int(middle_point[0]), int(middle_point[1])), radius=5, color=(0, 255, 255),thickness=-1)

				test_middle_point = int(((int(middle_point[0]) + int(middle_point[1])) / 10) % 10)

				#out_value = int(out)
				hex_part1 = f'{int(middle_point[0]):03}{int(middle_point[1]):03}'
				#hex_part2 = format(out_value, '03x')  # 使用0填充将out转为长度为3的十六进制字符串
				hex_part2 = f'{int(out):05}'
				hex_string = hex_part1 + hex_part2
				print("Hex String with 'out':", hex_string)

				def send_string_to_com(input_string, com_port='COM3', baudrate=115200, timeout=1):
					try:
						byte_data = input_string.encode('utf-8')
						with serial.Serial(com_port, baudrate=baudrate, timeout=timeout) as ser:
							ser.write(byte_data)
							print("成功发送字符串到USB。")
							ser.write(b'\n')
					except Exception as e:
						print(f"发送字符串到USB时发生错误：{e}")
				string_to_send = hex_string
				send_string_to_com(string_to_send)

			# 显示摄像头画面
			end_time = cv2.getTickCount()
			elapsed_time = (end_time - start_time)/1/cv2.getTickFrequency()
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
