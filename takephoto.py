import cv2

cap = cv2.VideoCapture(0)

ret, frame = cap.read()

if ret:
    cv2.imwrite("photo.jpg", frame)
    print("Saved photo.jpg")

cap.release()