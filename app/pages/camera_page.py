from __future__ import annotations

import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
    from app.widgets.camera_image_view import CameraImageView
    from drivers.camera.usb_camera import UsbCameraCaptureThread, UsbCameraDriver
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..widgets.camera_image_view import CameraImageView
    from drivers.camera.usb_camera import UsbCameraCaptureThread, UsbCameraDriver


class CameraPage(BasePage):
    """相机管理页。

    只负责相机枚举、打开/关闭、驱动选择和相机参数调整；
    ROI 配置已迁移到模板编辑页。

    """

    camera_metrics_changed = pyqtSignal(dict)
    image_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "相机管理",
            "选择 USB/GIGE 相机、驱动并调整采集参数。",
            parent,
        )
        self.config_service = ConfigService()
        self.camera_opened = False
        self.usb_driver = UsbCameraDriver()
        self.capture_thread: UsbCameraCaptureThread | None = None
        self._last_frame_time = time.perf_counter()
        self._build_ui()
        self._load_config()
        self.set_result("检测结果：相机未连接")
        self.set_tip("操作提示：请先选择相机类型和驱动，再枚举并打开相机。")

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        splitter.addWidget(self._build_image_area())
        right = self._build_control_area()
        right.setMinimumWidth(360)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 360])
        self.add_to_content(splitter, stretch=1)

    def _build_image_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_view = CameraImageView()
        layout.addWidget(self.image_view, 1)
        return container

    def _build_control_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        control_group = QGroupBox("相机控制")
        control_form = QFormLayout(control_group)
        control_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.camera_type_combo = QComboBox()
        self.camera_type_combo.addItems(["USB 相机", "GIGE 相机"])

        self.driver_combo = QComboBox()
        self.driver_combo.addItems(["DirectShow", "Basler Pylon", "HIKVISION SDK", "GigE Vision"])

        self.camera_list_combo = QComboBox()
        self.camera_list_combo.setStyleSheet(
            "QComboBox { background-color: #123a56; color: #ffffff; border: 2px solid #4ec9b0; border-radius: 4px; padding: 4px 8px; font-weight: 600; }"
        )
        self.enumerate_button = QPushButton("枚举相机")

        self.open_camera_button = QPushButton("打开相机")
        self.open_camera_button.setCheckable(True)

        control_form.addRow("相机类型", self.camera_type_combo)
        control_form.addRow("驱动选择", self.driver_combo)
        control_form.addRow("相机列表", self.camera_list_combo)
        control_form.addRow("", self.enumerate_button)
        control_form.addRow("", self.open_camera_button)

        preview_buttons = QHBoxLayout()
        self.start_preview_button = QPushButton("开始预览")
        self.stop_preview_button = QPushButton("停止预览")
        self.capture_button = QPushButton("拍照")
        preview_buttons.addWidget(self.start_preview_button)
        preview_buttons.addWidget(self.stop_preview_button)
        preview_buttons.addWidget(self.capture_button)
        self.start_preview_button.clicked.connect(self._start_preview)
        self.stop_preview_button.clicked.connect(self._stop_preview)
        self.capture_button.clicked.connect(self._capture)
        preview_container = QWidget()
        preview_container.setLayout(preview_buttons)
        control_form.addRow("", preview_container)
        layout.addWidget(control_group)

        self.open_local_image_button = QPushButton("打开本地图像")
        layout.addWidget(self.open_local_image_button)
        self.open_local_image_button.clicked.connect(self._open_local_image)

        param_group = QGroupBox("相机参数")
        param_form = QFormLayout(param_group)
        param_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.exposure_spin = QDoubleSpinBox()
        self.exposure_spin.setRange(0.0, 100000.0)
        self.exposure_spin.setDecimals(1)
        self.exposure_spin.setValue(5000.0)
        self.exposure_spin.setSuffix(" us")

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(0.0, 48.0)
        self.gain_spin.setDecimals(2)
        self.gain_spin.setValue(1.00)

        self.frame_rate_spin = QDoubleSpinBox()
        self.frame_rate_spin.setRange(0.1, 500.0)
        self.frame_rate_spin.setDecimals(1)
        self.frame_rate_spin.setValue(30.0)
        self.frame_rate_spin.setSuffix(" fps")

        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["连续采集", "软件触发", "硬件触发"])

        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.addItems(["Mono8", "Mono10", "BayerRG8", "RGB8"])

        param_form.addRow("曝光时间", self.exposure_spin)
        param_form.addRow("增益", self.gain_spin)
        param_form.addRow("帧率", self.frame_rate_spin)
        param_form.addRow("触发模式", self.trigger_combo)
        param_form.addRow("像素格式", self.pixel_format_combo)
        self.center_cross_button = QPushButton("十字线居中")
        param_form.addRow("", self.center_cross_button)
        self.save_button = QPushButton("保存相机配置")
        param_form.addRow("", self.save_button)
        layout.addWidget(param_group)

        layout.addStretch(1)

        self.enumerate_button.clicked.connect(self._enumerate_cameras)
        self.open_camera_button.clicked.connect(self._toggle_camera)
        self.save_button.clicked.connect(self._save_config)
        self.center_cross_button.clicked.connect(self.image_view.center_cross)
        return container

    def _enumerate_cameras(self) -> None:
        # 插入点：接入具体相机 SDK 后，替换为真实设备枚举逻辑。
        camera_type = self.camera_type_combo.currentText()
        driver = self.driver_combo.currentText()
        self.camera_list_combo.clear()
        if camera_type == "USB 相机":
            devices = self.usb_driver.enumerate_devices()
            for device in devices:
                self.camera_list_combo.addItem(device["name"], device["id"])
            self.set_result(f"检测结果：已枚举 {len(devices)} 台 USB 相机")
        else:
            demo_cameras = [
                f"{camera_type} / {driver} / CAM-00{index + 1}"
                for index in range(3)
            ]
            self.camera_list_combo.addItems(demo_cameras)
            self.set_result(f"检测结果：已枚举 {len(demo_cameras)} 台相机")

    def _toggle_camera(self, checked: bool) -> None:
        self.camera_opened = checked
        self.open_camera_button.setText("关闭相机" if checked else "打开相机")
        camera = self.camera_list_combo.currentText() or "未选择"
        if checked and self.camera_type_combo.currentText() == "USB 相机":
            device_id = self.camera_list_combo.currentData()
            if device_id is None:
                self.set_result("检测结果：未选择 USB 相机")
                self.open_camera_button.setChecked(False)
                return
            ok = self.usb_driver.open(int(device_id))
            if not ok:
                self.set_result("检测结果：USB 相机打开失败")
                self.open_camera_button.setChecked(False)
                return
            self.set_result(f"检测结果：USB 相机 {camera} 已打开")
        else:
            self._stop_preview()
            self.usb_driver.close()
            self.set_result(
                f"检测结果：相机 {camera} {'已打开' if checked else '已关闭'}"
            )
        if not checked:
            self._emit_camera_metrics(0, "--")

    def _open_local_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开本地图像",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;所有文件 (*.*)",
        )
        if not file_path:
            return
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.set_result("检测结果：本地图像打开失败")
            return
        self._stop_preview()
        self.image_view.set_pixmap(pixmap)
        self.image_changed.emit(pixmap)
        self._emit_camera_metrics(0, f"{pixmap.width()}x{pixmap.height()}")
        self.set_result(f"检测结果：已打开本地图像 {file_path}")

    def _start_preview(self) -> None:
        if not self.usb_driver.is_opened():
            self.set_result("检测结果：请先打开 USB 相机")
            return
        self._stop_preview()
        self._last_frame_time = time.perf_counter()
        self.capture_thread = UsbCameraCaptureThread(self.usb_driver, self)
        self.capture_thread.frame_ready.connect(self._update_preview_frame)
        self.capture_thread.start()
        self.set_tip("操作提示：USB 相机预览已启动。")

    def _stop_preview(self) -> None:
        if self.capture_thread is not None:
            self.capture_thread.stop()
            self.capture_thread.wait(1000)
            self.capture_thread.deleteLater()
            self.capture_thread = None
        self.set_tip("操作提示：USB 相机预览已停止。")

    def _capture(self) -> None:
        self._stop_preview()
        frame = self.usb_driver.read_frame()
        if frame is None:
            self.set_result("检测结果：拍照失败，相机未取到图像")
            return
        pixmap = self._frame_to_pixmap(frame)
        self.image_view.set_pixmap(pixmap)
        self.image_changed.emit(pixmap)
        height, width = frame.shape[:2]
        self._emit_camera_metrics(1, f"{width}x{height}")
        self.set_result(f"检测结果：拍照完成，图像大小 {width}x{height}")

    def _update_preview_frame(self, frame) -> None:
        now = time.perf_counter()
        delta = now - self._last_frame_time
        self._last_frame_time = now
        fps = 1.0 / delta if delta > 0 else 0.0
        height, width = frame.shape[:2]
        pixmap = self._frame_to_pixmap(frame)
        self.image_view.set_pixmap(pixmap)
        self.image_changed.emit(pixmap)
        self._emit_camera_metrics(round(fps, 1), f"{width}x{height}")

    def _frame_to_pixmap(self, frame) -> QPixmap:
        height, width = frame.shape[:2]
        qimage = QImage(frame.data, width, height, 3 * width, QImage.Format.Format_RGB888).rgbSwapped().copy()
        return QPixmap.fromImage(qimage)

    def _emit_camera_metrics(self, fps: float, image_size: str) -> None:
        self.camera_metrics_changed.emit({"fps": fps, "image_size": image_size})

    def _save_config(self) -> None:
        data = {
            "camera_type": self.camera_type_combo.currentText(),
            "driver": self.driver_combo.currentText(),
            "camera": self.camera_list_combo.currentText(),
            "exposure": self.exposure_spin.value(),
            "gain": self.gain_spin.value(),
            "frame_rate": self.frame_rate_spin.value(),
            "trigger": self.trigger_combo.currentText(),
            "pixel_format": self.pixel_format_combo.currentText(),
        }
        self.config_service.save_page_config("camera", data)
        self.set_tip("操作提示：相机配置已保存到 config/camera.yaml。")

    def _load_config(self) -> None:
        data = self.config_service.load_page_config("camera")
        if not data:
            return
        self.camera_type_combo.setCurrentText(str(data.get("camera_type", self.camera_type_combo.currentText())))
        self.driver_combo.setCurrentText(str(data.get("driver", self.driver_combo.currentText())))
        self.exposure_spin.setValue(float(data.get("exposure", self.exposure_spin.value())))
        self.gain_spin.setValue(float(data.get("gain", self.gain_spin.value())))
        self.frame_rate_spin.setValue(float(data.get("frame_rate", self.frame_rate_spin.value())))
        self.trigger_combo.setCurrentText(str(data.get("trigger", self.trigger_combo.currentText())))
        self.pixel_format_combo.setCurrentText(str(data.get("pixel_format", self.pixel_format_combo.currentText())))

    def auto_save_config(self) -> None:
        self._save_config()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_preview()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].CameraPage))
