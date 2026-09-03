import cv2
cam = cv2.VideoCapture(0)
ret, frame = cam.read()
if ret:
    print('Camera working, frame captured!')
else:
    print('Camera not detected!')
cam.release()
