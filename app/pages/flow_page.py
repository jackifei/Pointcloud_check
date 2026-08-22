from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
    from app.widgets import PointCloudView, RoiCanvas
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..widgets import PointCloudView, RoiCanvas

from drivers.pointcloud import read_point_cloud


def _default_template(name: str) -> dict:
    """生成新模板的默认数据。"""
    return {
        "name": name,
        "model_file": "",
        "point_cloud_file": "",
        "rois": [
            {"name": "ROI-1", "shape": "rect", "cx": 150, "cy": 120, "w": 200, "h": 150, "angle": 0},
            {"name": "ROI-2", "shape": "rect", "cx": 440, "cy": 170, "w": 220, "h": 160, "angle": 0},
        ],
        "detection": {
            "confidence": 0.5,
            "detection_count": 20,
            "spare_1": "",
            "spare_2": "",
            "spare_3": "",
            "enable_1": False,
            "enable_2": False,
            "enable_3": False,
            "enable_4": False,
            "enable_5": False,
            "function_1": "功能1",
            "function_2": "功能2",
            "function_3": "功能3",
            "function_4": "功能4",
            "function_5": "功能5",
        },
        "other_params": [],
    }


def _wrap_with_border(widget: QWidget) -> QFrame:
    """给控件包一层带边框的容器，便于区分一组复选框。"""
    container = QFrame()
    container.setFrameShape(QFrame.Shape.NoFrame)
    container.setStyleSheet(
        "QFrame {"
        " border: 1px solid #3c3c3c;"
        " border-radius: 4px;"
        " padding: 2px 6px;"
        " background: #252526;"
        "}"
    )
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    return container


class TemplateParamsDialog(QDialog):
    """模板参数弹窗，包含 Detection Config、Model Config、Other Config。"""

    FUNCTION_OPTIONS = ["功能1", "功能2", "功能3", "功能4", "功能5"]

    def __init__(self, template_data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("参数配置")
        self.resize(760, 620)

        self._detection = deepcopy(template_data.get("detection") or {})
        self._other_params = deepcopy(template_data.get("other_params") or [])
        self._model_file = str(template_data.get("model_file") or "")

        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_detection_group())
        layout.addWidget(self._build_model_group())
        layout.addWidget(self._build_other_group(), 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_detection_group(self) -> QGroupBox:
        group = QGroupBox("Detection Config")
        layout = QVBoxLayout(group)

        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("置信度"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.5)
        param_row.addWidget(self.confidence_spin)

        param_row.addWidget(QLabel("检测数量"))
        self.detection_count_spin = QSpinBox()
        self.detection_count_spin.setRange(1, 1000)
        self.detection_count_spin.setValue(20)
        param_row.addWidget(self.detection_count_spin)

        self.spare_edit_1 = QLineEdit()
        self.spare_edit_1.setPlaceholderText("备用参数1")
        param_row.addWidget(QLabel("备用参数1"))
        param_row.addWidget(self.spare_edit_1)

        self.spare_edit_2 = QLineEdit()
        self.spare_edit_2.setPlaceholderText("备用参数2")
        param_row.addWidget(QLabel("备用参数2"))
        param_row.addWidget(self.spare_edit_2)

        self.spare_edit_3 = QLineEdit()
        self.spare_edit_3.setPlaceholderText("备用参数3")
        param_row.addWidget(QLabel("备用参数3"))
        param_row.addWidget(self.spare_edit_3)
        param_row.addStretch(1)
        layout.addLayout(param_row)

        enable_row = QHBoxLayout()
        enable_row.addWidget(QLabel("启用项"))
        self.enable_check_1 = QCheckBox("是否启用1")
        self.enable_check_2 = QCheckBox("是否启用2")
        self.enable_check_3 = QCheckBox("是否启用3")
        self.enable_check_4 = QCheckBox("是否启用4")
        self.enable_check_5 = QCheckBox("是否启用5")
        for check in (
            self.enable_check_1,
            self.enable_check_2,
            self.enable_check_3,
            self.enable_check_4,
            self.enable_check_5,
        ):
            enable_row.addWidget(_wrap_with_border(check))
        enable_row.addStretch(1)
        layout.addLayout(enable_row)

        function_grid = QGridLayout()
        self.function_combo_1 = QComboBox()
        self.function_combo_2 = QComboBox()
        self.function_combo_3 = QComboBox()
        self.function_combo_4 = QComboBox()
        self.function_combo_5 = QComboBox()
        function_combos = [
            self.function_combo_1,
            self.function_combo_2,
            self.function_combo_3,
            self.function_combo_4,
            self.function_combo_5,
        ]
        for index, combo in enumerate(function_combos, start=1):
            combo.addItems(self.FUNCTION_OPTIONS)
            function_grid.addWidget(QLabel(f"功能选择{index}"), 0, index - 1)
            function_grid.addWidget(combo, 1, index - 1)
        layout.addLayout(function_grid)
        layout.addStretch(1)
        return group

    def _build_model_group(self) -> QGroupBox:
        group = QGroupBox("Model Config")
        layout = QVBoxLayout(group)

        self.model_file_label = QLabel("模型文件：未加载")
        self.model_file_label.setStyleSheet("color: #9d9d9d;")
        layout.addWidget(self.model_file_label)

        button_row = QHBoxLayout()
        self.load_model_button = QPushButton("加载模型")
        self.release_model_button = QPushButton("释放模型")
        button_row.addWidget(self.load_model_button)
        button_row.addWidget(self.release_model_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.load_model_button.clicked.connect(self._load_model)
        self.release_model_button.clicked.connect(self._release_model)
        return group

    def _build_other_group(self) -> QGroupBox:
        group = QGroupBox("Other Config")
        layout = QVBoxLayout(group)

        hint = QLabel("参数名称与参数值均可编辑，共 10 行。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.other_table = QTableWidget(10, 3)
        self.other_table.setHorizontalHeaderLabels(["序号", "参数名称", "参数值"])
        header = self.other_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.other_table.setColumnWidth(0, 48)
        self.other_table.verticalHeader().setVisible(False)
        layout.addWidget(self.other_table, 1)
        return group

    def _load_values(self) -> None:
        detection = self._detection
        self.confidence_spin.setValue(float(detection.get("confidence", 0.5)))
        self.detection_count_spin.setValue(int(detection.get("detection_count", 20)))
        self.spare_edit_1.setText(str(detection.get("spare_1", "")))
        self.spare_edit_2.setText(str(detection.get("spare_2", "")))
        self.spare_edit_3.setText(str(detection.get("spare_3", "")))
        self.enable_check_1.setChecked(bool(detection.get("enable_1", False)))
        self.enable_check_2.setChecked(bool(detection.get("enable_2", False)))
        self.enable_check_3.setChecked(bool(detection.get("enable_3", False)))
        self.enable_check_4.setChecked(bool(detection.get("enable_4", False)))
        self.enable_check_5.setChecked(bool(detection.get("enable_5", False)))
        self.function_combo_1.setCurrentText(str(detection.get("function_1", "功能1")))
        self.function_combo_2.setCurrentText(str(detection.get("function_2", "功能2")))
        self.function_combo_3.setCurrentText(str(detection.get("function_3", "功能3")))
        self.function_combo_4.setCurrentText(str(detection.get("function_4", "功能4")))
        self.function_combo_5.setCurrentText(str(detection.get("function_5", "功能5")))

        self.model_file_label.setText(f"模型文件：{self._model_file or '未加载'}")
        self._populate_other_params(self._other_params)

    def result_data(self) -> dict:
        detection = {
            "confidence": self.confidence_spin.value(),
            "detection_count": self.detection_count_spin.value(),
            "spare_1": self.spare_edit_1.text().strip(),
            "spare_2": self.spare_edit_2.text().strip(),
            "spare_3": self.spare_edit_3.text().strip(),
            "enable_1": self.enable_check_1.isChecked(),
            "enable_2": self.enable_check_2.isChecked(),
            "enable_3": self.enable_check_3.isChecked(),
            "enable_4": self.enable_check_4.isChecked(),
            "enable_5": self.enable_check_5.isChecked(),
            "function_1": self.function_combo_1.currentText(),
            "function_2": self.function_combo_2.currentText(),
            "function_3": self.function_combo_3.currentText(),
            "function_4": self.function_combo_4.currentText(),
            "function_5": self.function_combo_5.currentText(),
        }
        return {
            "detection": detection,
            "other_params": self._collect_other_params(),
            "model_file": self._model_file,
        }

    def _load_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载模型",
            "",
            "模型文件 (*.pt *.pth *.onnx *.engine *.bin);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self._model_file = file_path
        self.model_file_label.setText(f"模型文件：{file_path}")

    def _release_model(self) -> None:
        self._model_file = ""
        self.model_file_label.setText("模型文件：未加载")

    def _populate_other_params(self, params: list[dict]) -> None:
        self.other_table.setRowCount(10)
        self.other_table.setColumnCount(3)
        for row in range(10):
            name = ""
            value = ""
            if row < len(params):
                entry = params[row]
                if isinstance(entry, dict):
                    name = str(entry.get("name", ""))
                    value = str(entry.get("value", ""))
            seq_item = QTableWidgetItem(str(row + 1))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.other_table.setItem(row, 0, seq_item)
            self.other_table.setItem(row, 1, QTableWidgetItem(name))
            self.other_table.setItem(row, 2, QTableWidgetItem(value))

    def _collect_other_params(self) -> list[dict]:
        params: list[dict] = []
        for row in range(self.other_table.rowCount()):
            name_item = self.other_table.item(row, 1)
            value_item = self.other_table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            value = value_item.text().strip() if value_item else ""
            if name:
                params.append({"name": name, "value": value})
        return params


class FlowPage(BasePage):
    """模板编辑页。

    左侧产品模板列表；右侧顶部为三维点云 + 二维 ROI 画布，
    底部为操作按钮与平面拟合参数。
    """

    PLANE_COLORS = {
        "青色": "#4ec9b0",
        "红色": "#f48771",
        "绿色": "#39ff14",
        "蓝色": "#4fa3ff",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "模板编辑",
            "创建产品模板，配置 ROI、检测参数、模型和其他参数。",
            parent,
        )
        self.config_service = ConfigService()
        self.templates: dict[str, dict] = {}
        self.current_template_name = ""
        self._build_ui()
        self._load_template_list()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)

        self.template_panel = self._build_template_panel()
        self.template_panel.setMinimumWidth(210)
        splitter.addWidget(self.template_panel)
        splitter.addWidget(self._build_config_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([230, 1000])
        self.add_to_content(splitter, stretch=1)

    def _build_template_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        switch_group = QGroupBox("模板名称")
        switch_layout = QHBoxLayout(switch_group)
        self.template_combo = QComboBox()
        switch_layout.addWidget(self.template_combo, 1)
        layout.addWidget(switch_group)

        template_group = QGroupBox("产品模板")
        template_layout = QVBoxLayout(template_group)
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        template_layout.addWidget(self.template_list, 1)

        button_row = QHBoxLayout()
        self.new_template_button = QPushButton("新建模板")
        self.copy_template_button = QPushButton("复制模板")
        self.delete_template_button = QPushButton("删除模板")
        button_row.addWidget(self.new_template_button)
        button_row.addWidget(self.copy_template_button)
        button_row.addWidget(self.delete_template_button)
        template_layout.addLayout(button_row)

        self.save_template_button = QPushButton("保存当前模板")
        template_layout.addWidget(self.save_template_button)

        roi_list_group = QGroupBox("ROI列表")
        roi_list_layout = QVBoxLayout(roi_list_group)
        self.roi_table = QTableWidget(0, 2)
        self.roi_table.setHorizontalHeaderLabels(["名称", "顶点数"])
        roi_header = self.roi_table.horizontalHeader()
        roi_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        roi_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.roi_table.verticalHeader().setVisible(False)
        self.roi_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.roi_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        roi_list_layout.addWidget(self.roi_table, 1)
        delete_row = QHBoxLayout()
        self.delete_roi_button = QPushButton("删除选中多边形")
        delete_row.addWidget(self.delete_roi_button)
        delete_row.addStretch(1)
        roi_list_layout.addLayout(delete_row)

        self.template_splitter = QSplitter(Qt.Orientation.Vertical)
        self.template_splitter.setChildrenCollapsible(False)
        self.template_splitter.setHandleWidth(5)
        self.template_splitter.addWidget(template_group)
        self.template_splitter.addWidget(roi_list_group)
        self.template_splitter.setStretchFactor(0, 1)
        self.template_splitter.setStretchFactor(1, 1)
        self.template_splitter.setSizes([300, 160])
        layout.addWidget(self.template_splitter, 1)

        self.template_combo.currentTextChanged.connect(self._on_template_combo_changed)
        self.new_template_button.clicked.connect(self._new_template)
        self.copy_template_button.clicked.connect(self._copy_template)
        self.delete_template_button.clicked.connect(self._delete_template)
        self.save_template_button.clicked.connect(self._save_current_template)
        return container

    def _build_config_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 顶部：三维点云 + 二维 ROI 画布（右侧带多边形列表），最大化显示
        self.roi_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.roi_splitter.setChildrenCollapsible(False)
        self.roi_splitter.setHandleWidth(5)
        self.point_cloud_view = PointCloudView()
        self.roi_splitter.addWidget(self.point_cloud_view)

        self.roi_canvas = RoiCanvas()
        self.roi_right_panel = QWidget()
        roi_right_layout = QVBoxLayout(self.roi_right_panel)
        roi_right_layout.setContentsMargins(0, 0, 0, 0)
        roi_right_layout.setSpacing(0)
        roi_right_layout.addWidget(self.roi_canvas, 1)

        self.roi_splitter.addWidget(self.roi_right_panel)
        self.roi_splitter.setStretchFactor(0, 1)
        self.roi_splitter.setStretchFactor(1, 1)
        self.roi_splitter.setSizes([500, 500])
        layout.addWidget(self.roi_splitter, 1)

        self.fit_result_label = QLabel("拟合结果：--")
        self.fit_result_label.setWordWrap(True)
        self.fit_result_label.setStyleSheet("color: #9d9d9d;")
        layout.addWidget(self.fit_result_label)

        # 底部：视图控制 + 平面拟合参数（仅最小二乘）
        params_row = QHBoxLayout()
        self.front_view_button = QPushButton("正视图")
        self.side_view_button = QPushButton("侧视图")
        self.top_view_button = QPushButton("俯视图")
        self.axes_check = QCheckBox("显示坐标系")
        self.axes_check.setChecked(True)
        params_row.addWidget(self.front_view_button)
        params_row.addWidget(self.side_view_button)
        params_row.addWidget(self.top_view_button)
        params_row.addWidget(self.axes_check)

        params_row.addWidget(QLabel("平面尺寸"))
        self.plane_size_spin = QDoubleSpinBox()
        self.plane_size_spin.setRange(5.0, 700.0)
        self.plane_size_spin.setDecimals(1)
        self.plane_size_spin.setValue(200.0)
        self.plane_size_spin.setSuffix(" mm")
        params_row.addWidget(self.plane_size_spin)

        params_row.addWidget(QLabel("平面颜色"))
        self.plane_color_combo = QComboBox()
        self.plane_color_combo.addItems(list(self.PLANE_COLORS.keys()))
        params_row.addWidget(self.plane_color_combo)
        params_row.addStretch(1)
        layout.addLayout(params_row)

        # 底部：点云显示 + 多边形选择/平面拟合按钮，一行
        general_row = QHBoxLayout()
        self.load_point_cloud_button = QPushButton("加载点云参考")
        self.project_view_button = QPushButton("当前视角投影到 ROI")
        self.clear_point_cloud_button = QPushButton("清空点云")
        self.crosshair_check = QCheckBox("显示十字线")
        self.crosshair_check.setChecked(True)
        self.params_button = QPushButton("参数弹窗")
        for widget in (
            self.load_point_cloud_button,
            self.project_view_button,
            self.clear_point_cloud_button,
            self.crosshair_check,
            self.params_button,
        ):
            general_row.addWidget(widget)

        self.select_toggle_button = QPushButton("区域选择")
        self.select_toggle_button.setCheckable(True)
        self.clear_select_button = QPushButton("清除选择")
        self.fit_plane_button = QPushButton("拟合平面")
        self.clear_plane_button = QPushButton("清除平面")
        selection_frame = QFrame()
        selection_frame.setFrameShape(QFrame.Shape.StyledPanel)
        selection_frame.setStyleSheet(
            "QFrame { border: 1px solid #3c3c3c; border-radius: 4px; padding: 4px; }"
        )
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setContentsMargins(4, 4, 4, 4)
        selection_layout.setSpacing(4)
        selection_layout.addWidget(self.select_toggle_button)
        selection_layout.addWidget(self.clear_select_button)
        selection_layout.addWidget(self.fit_plane_button)
        selection_layout.addWidget(self.clear_plane_button)
        general_row.addWidget(selection_frame)
        general_row.addStretch(1)
        layout.addLayout(general_row)

        self.load_point_cloud_button.clicked.connect(self._open_point_cloud_file)
        self.project_view_button.clicked.connect(self._project_view_to_roi)
        self.clear_point_cloud_button.clicked.connect(self._clear_point_cloud)
        self.crosshair_check.toggled.connect(self.roi_canvas.set_crosshair_visible)
        self.params_button.clicked.connect(self._open_params_dialog)
        self.front_view_button.clicked.connect(lambda: self.point_cloud_view.set_front_view())
        self.side_view_button.clicked.connect(lambda: self.point_cloud_view.set_side_view())
        self.top_view_button.clicked.connect(lambda: self.point_cloud_view.set_top_view())
        self.axes_check.toggled.connect(self.point_cloud_view.set_axes_visible)

        self.select_toggle_button.toggled.connect(self.roi_canvas.set_drawing_polygon)
        self.roi_canvas.drawing_finished.connect(lambda: self.select_toggle_button.setChecked(False))
        self.clear_select_button.clicked.connect(self.roi_canvas.clear_rois)
        self.fit_plane_button.clicked.connect(self._fit_plane)
        self.clear_plane_button.clicked.connect(self._clear_plane)
        self.delete_roi_button.clicked.connect(self.roi_canvas.delete_selected_roi)

        self.roi_canvas.rois_changed.connect(self._on_rois_changed)
        self.roi_canvas.selection_changed.connect(self._on_roi_selection_changed)
        return container

    def _load_template_list(self) -> None:
        if not self.config_service.list_templates():
            self._create_template("默认产品A")
        self._refresh_template_list()

    def _refresh_template_list(self, select_name: str | None = None) -> None:
        names = self.config_service.list_templates()

        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItems(names)
        self.template_combo.blockSignals(False)

        self.template_list.clear()
        for name in names:
            self.config_service.ensure_template_dirs(name)
            self.template_list.addItem(QListWidgetItem(name))

        if select_name and select_name in names:
            self._set_current_template(select_name)
        elif names:
            self._set_current_template(names[0])

    def _set_current_template(self, name: str) -> None:
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentText(name)
        self.template_combo.blockSignals(False)
        self._sync_list_selection(name)
        self._load_template(name)

    def _sync_list_selection(self, name: str) -> None:
        items = self.template_list.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self.template_list.blockSignals(True)
            self.template_list.setCurrentItem(items[0])
            self.template_list.blockSignals(False)

    def _on_template_combo_changed(self, name: str) -> None:
        if not name:
            return
        self._sync_list_selection(name)
        self._load_template(name)

    def _load_template(self, name: str) -> None:
        data = self.config_service.load_template(name)
        if not data:
            data = _default_template(name)
        self.templates[name] = data
        self.current_template_name = name

        self.roi_canvas.set_rois(deepcopy(data.get("rois", [])))
        self._refresh_roi_table()

        point_cloud_file = str(data.get("point_cloud_file") or "")
        if point_cloud_file and Path(point_cloud_file).exists():
            self._load_point_cloud_file(Path(point_cloud_file))
        else:
            self.point_cloud_view.clear()
            self.roi_canvas.set_pixmap(None)

        # 按保存时的图像尺寸等比缩放到当前图像尺寸，保持 ROI 与背景图的比例
        saved_size = data.get("roi_image_size")
        current_pixmap = self.roi_canvas.pixmap()
        if (
            saved_size
            and current_pixmap is not None
            and not current_pixmap.isNull()
        ):
            saved_w = float(saved_size[0])
            saved_h = float(saved_size[1])
            current_w = current_pixmap.width()
            current_h = current_pixmap.height()
            if (
                saved_w > 0
                and saved_h > 0
                and (saved_w != current_w or saved_h != current_h)
            ):
                self.roi_canvas.rescale_rois(saved_w, saved_h, current_w, current_h)
                self._refresh_roi_table()
                self.templates.setdefault(name, {})["rois"] = self.roi_canvas.get_rois()

        self.point_cloud_view.clear_fitted_plane()
        self.fit_result_label.setText("拟合结果：--")

        self.set_result(f"检测结果：模板「{name}」已加载")
        self.set_tip("操作提示：ROI 在下方配置，检测/模型/其他参数点击“参数弹窗”配置。")

    def _open_params_dialog(self) -> None:
        name = self.current_template_name
        if not name:
            self.set_tip("操作提示：请先选择模板。")
            return
        data = self.templates.setdefault(name, _default_template(name))
        dialog = TemplateParamsDialog(data, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = dialog.result_data()
        data["detection"] = result["detection"]
        data["other_params"] = result["other_params"]
        data["model_file"] = result["model_file"]
        self.set_tip("操作提示：参数已更新，点击“保存当前模板”可写入模板目录。")

    def set_point_cloud(self, pcd) -> None:
        """接收点云设备管理页广播的点云，用于 ROI 配置区实时显示。"""
        self.point_cloud_view.set_point_cloud(pcd)
        if self.point_cloud_view.isVisible():
            self._project_view_to_roi()

    def _open_point_cloud_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载点云参考",
            "",
            "点云文件 (*.ply *.pcd *.xyz *.pts);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self._load_point_cloud_file(Path(file_path))
        if self.current_template_name:
            self.templates.setdefault(self.current_template_name, {})["point_cloud_file"] = file_path
        self.set_tip("操作提示：点云参考已加载，点击“保存当前模板”可写入模板目录。")

    def _load_point_cloud_file(self, path: Path) -> None:
        pcd = read_point_cloud(path)
        if pcd is None or len(pcd.points) == 0:
            self.set_result(f"检测结果：点云文件为空或格式不支持 {path.name}")
            return
        self.point_cloud_view.set_point_cloud(pcd)
        if self.point_cloud_view.isVisible():
            self._project_view_to_roi()
        self.set_result(f"检测结果：已加载点云 {path.name}（{len(pcd.points):,} 点）")

    def _project_view_to_roi(self) -> None:
        """把 3D 视图当前画面投影到右侧 ROI 画布作为编辑底图。"""
        if self.point_cloud_view.has_cloud():
            pixmap = self.point_cloud_view.grab()
            if not pixmap.isNull():
                self.roi_canvas.set_pixmap(pixmap)

    def _clear_point_cloud(self) -> None:
        self.point_cloud_view.clear()
        self.roi_canvas.set_pixmap(None)
        if self.current_template_name:
            self.templates.setdefault(self.current_template_name, {})["point_cloud_file"] = ""
        self.set_tip("操作提示：点云参考已清空。")

    def _refresh_roi_table(self) -> None:
        self.roi_table.setRowCount(0)
        for roi in self.roi_canvas.rois:
            row = self.roi_table.rowCount()
            self.roi_table.insertRow(row)
            name_item = QTableWidgetItem(str(roi.get("name", "")))
            count = len(roi.get("points", [])) if roi["shape"] == "polygon" else "-"
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.roi_table.setItem(row, 0, name_item)
            self.roi_table.setItem(row, 1, count_item)

    def _on_rois_changed(self) -> None:
        self._refresh_roi_table()
        if self.current_template_name:
            self.templates.setdefault(self.current_template_name, {})["rois"] = self.roi_canvas.get_rois()

    def _on_roi_selection_changed(self, index: int) -> None:
        if 0 <= index < self.roi_table.rowCount():
            self.roi_table.selectRow(index)
        else:
            self.roi_table.clearSelection()

    def _fit_plane(self) -> None:
        """对多边形框选出的点用最小二乘法做平面拟合并显示拟合平面。"""
        all_points = self.point_cloud_view.points()
        if all_points.shape[0] < 3:
            self.set_result("检测结果：请先加载点云")
            return
        image_points = self.point_cloud_view.project_points_to_image()
        mask = self.roi_canvas.points_inside_polygons(image_points)
        points = all_points[mask]
        if points.shape[0] < 3:
            self.set_result("检测结果：请先绘制多边形框选至少 3 个点")
            return

        from algorithms.pointcheck import fit_plane_least_squares

        result = fit_plane_least_squares(points)
        normal = result["normal"]
        center = result["center"]
        rms = result["rms"]
        a, b, c, d = result["a"], result["b"], result["c"], result["d"]

        color = self.PLANE_COLORS.get(
            self.plane_color_combo.currentText(),
            self.PLANE_COLORS["青色"],
        )
        self.point_cloud_view.set_fitted_plane(
            center=center,
            normal=normal,
            size=float(self.plane_size_spin.value()),
            color=color,
        )
        self.fit_result_label.setText(
            "拟合结果：平面方程 "
            f"{a:.4f}x + {b:.4f}y + {c:.4f}z + {d:.4f} = 0，"
            f"选中 {len(points):,} 点，RMS {rms:.4f}"
        )
        self.set_result(f"检测结果：平面拟合完成，RMS 误差 {rms:.4f}")
        self.set_tip("操作提示：可调整平面尺寸/颜色后重新拟合，或点击“清除平面”。")

    def _clear_plane(self) -> None:
        self.point_cloud_view.clear_fitted_plane()
        self.fit_result_label.setText("拟合结果：--")
        self.set_tip("操作提示：拟合平面已清除。")

    def _new_template(self) -> None:
        name, ok = QInputDialog.getText(self, "新建模板", "请输入模板名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        self._save_current_template()
        if self._create_template(name):
            self._refresh_template_list(name)

    def _create_template(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        if name in self.config_service.list_templates():
            QMessageBox.warning(self, "提示", "模板名称已存在。")
            return False
        self._persist_template(name, _default_template(name))
        return True

    def _copy_template(self) -> None:
        current = self.template_list.currentItem()
        if current is None:
            QMessageBox.information(self, "提示", "请先在列表中选择要复制的模板。")
            return
        source = current.text()
        target, ok = QInputDialog.getText(self, "复制模板", "请输入复制后的模板名称：")
        if not ok or not target.strip():
            return
        target = target.strip()
        if target in self.config_service.list_templates():
            QMessageBox.warning(self, "提示", "模板名称已存在。")
            return

        self._save_current_template()
        try:
            self.config_service.copy_template(source, target)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "复制失败", str(exc))
            return
        self._refresh_template_list(target)

    def _delete_template(self) -> None:
        current = self.template_list.currentItem()
        if current is None:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的模板。")
            return
        name = current.text()
        if len(self.config_service.list_templates()) <= 1:
            QMessageBox.information(self, "提示", "至少需要保留一个产品模板。")
            return

        answer = QMessageBox.question(
            self,
            "删除模板",
            f"确定删除模板「{name}」及其目录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.config_service.delete_template(name):
            self.templates.pop(name, None)
            self._refresh_template_list()
        else:
            QMessageBox.warning(self, "删除失败", "未能删除该模板目录。")

    def _save_current_template(self) -> None:
        name = self.current_template_name
        if not name:
            return
        data = self.templates.get(name, _default_template(name))
        pixmap = self.roi_canvas.pixmap()
        roi_image_size = (
            [pixmap.width(), pixmap.height()]
            if pixmap is not None and not pixmap.isNull()
            else []
        )
        data.update(
            {
                "name": name,
                "point_cloud_file": str(data.get("point_cloud_file", "")),
                "rois": self.roi_canvas.get_rois(),
                "roi_image_size": roi_image_size,
            }
        )
        self.templates[name] = data
        self._persist_template(name, data)
        self.set_tip(f"操作提示：模板「{name}」已保存到模板目录。")

    def _persist_template(self, name: str, data: dict) -> None:
        payload = {
            "name": data.get("name", name),
            "model_file": data.get("model_file", ""),
            "point_cloud_file": data.get("point_cloud_file", ""),
            "rois": data.get("rois", []),
            "roi_image_size": data.get("roi_image_size", []),
            "detection": data.get("detection", {}),
            "other_params": data.get("other_params", []),
        }
        self.config_service.save_template(name, payload)
        self.config_service.ensure_template_dirs(name)
        self.config_service.save_template_category(name, "ROI Config", "roi.yaml", {"rois": payload["rois"]})
        self.config_service.save_template_category(name, "Detection Config", "detection.yaml", {"detection": payload["detection"]})
        self.config_service.save_template_category(
            name,
            "Model Config",
            "model.yaml",
            {
                "model_file": payload["model_file"],
                "point_cloud_file": payload["point_cloud_file"],
            },
        )
        self.config_service.save_template_category(name, "Other Config", "other.yaml", {"other_params": payload["other_params"]})

    def auto_save_config(self) -> None:
        self._save_current_template()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].FlowPage))
