from __future__ import annotations

import cv2

from PyQt6.QtCore import QThread, pyqtSignal


class UsbCameraDriver:
    """基于 OpenCV 的 USB 相机驱动。

    只负责 USB 相机的枚举、打开、关闭和取帧；
    相机管理页通过该驱动显示画面。
    """

    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self.device_id: int | None = None

    @staticmethod
    def enumerate_devices(max_index: int = 6) -> list[dict]:
        devices: list[dict] = []
        for index in range(max_index):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture.isOpened():
                devices.append({"id": index, "name": f"USB Camera {index}"})
            capture.release()
        return devices

    def open(self, device_id: int) -> bool:
        self.close()
        self._capture = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)
        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            return False
        self.device_id = device_id
        return True

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self.device_id = None

    def is_opened(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    def read_frame(self):
        if not self.is_opened():
            return None
        ok, frame = self._capture.read()
        return frame if ok else None


class UsbCameraCaptureThread(QThread):
    """独立采集线程。

    通过 frame_ready 信号把 OpenCV 图像帧发送到 Qt 主线程。
    """

    frame_ready = pyqtSignal(object)

    def __init__(self, driver: UsbCameraDriver, parent=None) -> None:
        super().__init__(parent)
        self.driver = driver
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running and self.driver.is_opened():
            frame = self.driver.read_frame()
            if frame is not None:
                self.frame_ready.emit(frame)
            self.msleep(1)

    def stop(self) -> None:
        self._running = False
