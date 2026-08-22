from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
    from app.widgets.point_cloud_view import PointCloudView
    from drivers.pointcloud import FilePointCloudDriver
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..widgets.point_cloud_view import PointCloudView
    from drivers.pointcloud import FilePointCloudDriver


class PointCloudDevicePage(BasePage):
    """点云设备管理页。

    - 文件点云设备：点击“打开本地点云”直接加载 .ply/.pcd/.xyz/.pts 文件。
    - 真实3D相机：枚举/打开/采集（预留，接入真实 SDK 后启用）。
    左侧三维点云显示，右侧负责设备操作与预处理。
    """

    point_cloud_metrics_changed = pyqtSignal(dict)
    point_cloud_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "点云设备管理",
            "打开本地点云文件或接入真实 3D 相机，查看三维点云并做预处理。",
            parent,
        )
        self.config_service = ConfigService()
        self.driver = FilePointCloudDriver()
        self._device_opened = False
        self._pending_device_id: str | None = None
        self._build_ui()
        self._load_config()
        self._on_device_type_changed(self.device_type_combo.currentIndex())
        self.set_result("检测结果：设备未连接")

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        splitter.addWidget(self._build_view_area())
        right = self._build_control_area()
        right.setMinimumWidth(360)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 360])
        self.add_to_content(splitter, stretch=1)

    def _build_view_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        self.point_cloud_view = PointCloudView()
        layout.addWidget(self.point_cloud_view, 1)
        return container

    def _build_control_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        device_group = QGroupBox("点云设备控制")
        device_form = QFormLayout(device_group)
        device_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(["文件点云设备", "真实3D相机"])
        device_form.addRow("设备类型", self.device_type_combo)

        self.device_mode_stack = QStackedWidget()
        self.device_mode_stack.addWidget(self._build_file_mode_widget())
        self.device_mode_stack.addWidget(self._build_real_mode_widget())
        device_form.addRow("", self.device_mode_stack)
        layout.addWidget(device_group)

        view_group = QGroupBox("视图控制")
        view_row = QHBoxLayout(view_group)
        self.front_view_button = QPushButton("正视图")
        self.side_view_button = QPushButton("侧视图")
        self.top_view_button = QPushButton("俯视图")
        view_row.addWidget(self.front_view_button)
        view_row.addWidget(self.side_view_button)
        view_row.addWidget(self.top_view_button)
        layout.addWidget(view_group)

        self.axes_check = QCheckBox("显示坐标系")
        self.axes_check.setChecked(True)
        layout.addWidget(self.axes_check)

        preprocess_group = QGroupBox("预处理")
        preprocess_form = QFormLayout(preprocess_group)
        preprocess_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.voxel_check = QCheckBox("体素降采样")
        self.voxel_size_spin = QDoubleSpinBox()
        self.voxel_size_spin.setRange(0.01, 1000.0)
        self.voxel_size_spin.setDecimals(3)
        self.voxel_size_spin.setValue(0.5)
        self.voxel_size_spin.setSuffix(" mm")

        self.outlier_check = QCheckBox("离群点去除")
        self.nb_neighbors_spin = QSpinBox()
        self.nb_neighbors_spin.setRange(1, 1000)
        self.nb_neighbors_spin.setValue(20)
        self.std_ratio_spin = QDoubleSpinBox()
        self.std_ratio_spin.setRange(0.1, 10.0)
        self.std_ratio_spin.setDecimals(2)
        self.std_ratio_spin.setValue(2.0)

        preprocess_form.addRow("", self.voxel_check)
        preprocess_form.addRow("体素尺寸", self.voxel_size_spin)
        preprocess_form.addRow("", self.outlier_check)
        preprocess_form.addRow("邻域点数", self.nb_neighbors_spin)
        preprocess_form.addRow("标准差倍数", self.std_ratio_spin)
        layout.addWidget(preprocess_group)

        self.save_button = QPushButton("保存设备配置")
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        self.device_type_combo.currentIndexChanged.connect(self._on_device_type_changed)
        self.save_button.clicked.connect(self._save_config)
        self.front_view_button.clicked.connect(lambda: self.point_cloud_view.set_front_view())
        self.side_view_button.clicked.connect(lambda: self.point_cloud_view.set_side_view())
        self.top_view_button.clicked.connect(lambda: self.point_cloud_view.set_top_view())
        self.axes_check.toggled.connect(self.point_cloud_view.set_axes_visible)
        return container

    def _build_file_mode_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.open_local_button = QPushButton("打开本地点云")
        layout.addWidget(self.open_local_button)

        self.data_dir_label = QLabel(f"示例目录：{self.driver.data_dir}")
        self.data_dir_label.setWordWrap(True)
        self.data_dir_label.setStyleSheet("color: #9d9d9d;")
        layout.addWidget(self.data_dir_label)

        self.open_local_button.clicked.connect(self._open_local_point_cloud)
        return widget

    def _build_real_mode_widget(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.device_list_combo = QComboBox()
        self.device_list_combo.setStyleSheet(
            "QComboBox { background-color: #123a56; color: #ffffff; border: 2px solid #4ec9b0; border-radius: 4px; padding: 4px 8px; font-weight: 600; }"
        )
        self.enumerate_button = QPushButton("枚举设备")
        self.open_device_button = QPushButton("打开设备")
        self.open_device_button.setCheckable(True)
        self.capture_button = QPushButton("采集单帧")

        form.addRow("设备列表", self.device_list_combo)
        form.addRow("", self.enumerate_button)
        form.addRow("", self.open_device_button)
        form.addRow("", self.capture_button)

        self.enumerate_button.clicked.connect(self._enumerate_devices)
        self.open_device_button.clicked.connect(self._toggle_device)
        self.capture_button.clicked.connect(self._capture_once)
        return widget

    def _on_device_type_changed(self, index: int) -> None:
        self.device_mode_stack.setCurrentIndex(index)
        if index == 0:
            self.set_tip("操作提示：点击“打开本地点云”加载 .ply/.pcd/.xyz/.pts 文件。")
        else:
            self.set_tip("操作提示：真实 3D 相机为预留，接入 SDK 后可枚举并打开设备。")

    def _open_local_point_cloud(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开本地点云",
            "",
            "点云文件 (*.ply *.pcd *.xyz *.xyzrgb *.pts);;所有文件 (*.*)",
        )
        if not file_path:
            return
        try:
            if not self.driver.open(file_path):
                self.set_result("检测结果：点云文件打开失败或为空")
                return
            self._device_opened = True
            self._load_current_cloud(display_name=Path(file_path).name)
        except Exception as exc:  # noqa: BLE001
            self.set_result(f"检测结果：点云加载失败：{exc}")
            QMessageBox.warning(self, "加载失败", f"无法加载该点云文件：\n{exc}")

    def _enumerate_devices(self) -> None:
        self.device_list_combo.clear()
        if self.device_type_combo.currentText() != "真实3D相机":
            return

        # 插入点：接入真实 3D 相机 SDK 后，替换为真实设备枚举。
        demo_devices = [f"3D相机 CAM-{index:03d}" for index in range(1, 4)]
        for name in demo_devices:
            self.device_list_combo.addItem(name, name)

        if self._pending_device_id:
            index = self.device_list_combo.findData(self._pending_device_id)
            if index >= 0:
                self.device_list_combo.setCurrentIndex(index)

        self.set_result(f"检测结果：已枚举 {len(demo_devices)} 台相机（演示数据）")
        self.set_tip("操作提示：当前为预留演示，接入真实 SDK 后返回真实设备。")

    def _toggle_device(self, checked: bool) -> None:
        self._device_opened = checked
        self.open_device_button.setText("关闭设备" if checked else "打开设备")
        if not checked:
            self.driver.close()
            self.point_cloud_view.clear()
            self.point_cloud_changed.emit(None)
            self._emit_metrics(None)
            self.set_result("检测结果：设备已关闭")
            return

        # 插入点：接入真实 3D 相机 SDK 后，替换为真实打开逻辑。
        device = self.device_list_combo.currentText() or "设备"
        self.set_result(f"检测结果：{device} 为演示设备，真实 SDK 尚未接入")
        self.set_tip("操作提示：请在 drivers/pointcloud 中按统一接口接入真实相机 SDK。")
        self.open_device_button.setChecked(False)

    def _capture_once(self) -> None:
        if not self.driver.is_opened():
            self.set_result("检测结果：真实相机 SDK 尚未接入，无法采集")
            return
        self._load_current_cloud()

    def _load_current_cloud(self, display_name: str | None = None) -> None:
        pcd = self.driver.capture()
        if pcd is None:
            self.set_result("检测结果：未采集到点云")
            return
        pcd = self._apply_preprocessing(pcd)
        self.point_cloud_view.set_point_cloud(pcd)
        self.point_cloud_changed.emit(pcd)
        self._emit_metrics(pcd)
        name = display_name or self.device_list_combo.currentText() or "设备"
        self.set_result(f"检测结果：{name} 共 {len(pcd.points):,} 点")
        self.set_tip("操作提示：可拖动旋转、右键平移、滚轮缩放；可在模板编辑页进行平面拟合。")

    def _apply_preprocessing(self, pcd):
        from algorithms.pointcloud import remove_outliers, voxel_downsample

        if self.voxel_check.isChecked():
            pcd = voxel_downsample(pcd, self.voxel_size_spin.value())
        if self.outlier_check.isChecked():
            pcd = remove_outliers(
                pcd,
                self.nb_neighbors_spin.value(),
                self.std_ratio_spin.value(),
            )
        return pcd

    def _emit_metrics(self, pcd) -> None:
        if pcd is not None and len(pcd.points) > 0:
            self.point_cloud_metrics_changed.emit(
                {"fps": "--", "point_count": int(len(pcd.points))}
            )
        else:
            self.point_cloud_metrics_changed.emit({"fps": "--", "point_count": "--"})

    def _save_config(self) -> None:
        data = {
            "device_type": self.device_type_combo.currentText(),
            "device": self.device_list_combo.currentData() or "",
            "voxel_enabled": self.voxel_check.isChecked(),
            "voxel_size": self.voxel_size_spin.value(),
            "outlier_enabled": self.outlier_check.isChecked(),
            "nb_neighbors": self.nb_neighbors_spin.value(),
            "std_ratio": self.std_ratio_spin.value(),
        }
        self.config_service.save_page_config("pointcloud_device", data)
        self.set_tip("操作提示：设备配置已保存到 config/pointcloud_device.yaml。")

    def _load_config(self) -> None:
        data = self.config_service.load_page_config("pointcloud_device")
        if not data:
            return
        self.device_type_combo.setCurrentText(
            str(data.get("device_type", self.device_type_combo.currentText()))
        )
        self._pending_device_id = str(data.get("device") or "") or None
        self.voxel_check.setChecked(bool(data.get("voxel_enabled", False)))
        self.voxel_size_spin.setValue(float(data.get("voxel_size", self.voxel_size_spin.value())))
        self.outlier_check.setChecked(bool(data.get("outlier_enabled", False)))
        self.nb_neighbors_spin.setValue(int(data.get("nb_neighbors", self.nb_neighbors_spin.value())))
        self.std_ratio_spin.setValue(float(data.get("std_ratio", self.std_ratio_spin.value())))

    def auto_save_config(self) -> None:
        self._save_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].PointCloudDevicePage))
