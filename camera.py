import sys
import time

import cv2


class Camera:
    def __init__(self, device_index=0, width=1920, height=1080):
        self.device_index = device_index
        self.width = width
        self.height = height
        self._cap = None

    def open(self):
        if self._cap is not None:
            return

        if sys.platform == "darwin":
            backend = cv2.CAP_AVFOUNDATION
        else:
            backend = cv2.CAP_V4L2

        cap = cv2.VideoCapture(self.device_index, backend)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        time.sleep(0.5)
        for _ in range(10):
            cap.read()

        self._cap = cap

    def read_frame(self):
        if self._cap is None:
            self.open()

        ret, frame = self._cap.read()
        if not ret:
            return None
        return frame

    def capture_frame(self):
        return self.read_frame()

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
