import cv2, time
from datetime import datetime

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# Prefer MJPG (often sharper + higher FPS on Pi)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

# Try 1920x1080 first, then change to 1280x720 if needed
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Let auto-exposure/white balance settle
time.sleep(0.5)
for _ in range(15):
    cap.read()

ret, frame = cap.read()
if ret:
    filename = datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")
    cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    print("Saved", filename , frame.shape)
else:
    print("Capture failed")

cap.release()