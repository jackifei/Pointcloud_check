from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
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
    QScrollArea,
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
    from app.widgets import RoiCanvas, RoiEditorDialog
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..widgets import RoiCanvas, RoiEditorDialog


def _default_template(name: str) -> dict:
    """生成新模板的默认数据。"""
    return {
        "name": name,
        "model_file": "",
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


class FlowPage(BasePage):
    """模板编辑页。

    左侧“产品模板”模块用模板下拉框切换当前模板，模板列表仅用于选中后复制/删除；
    右侧包含 ROI Config、Detection Config、Model Config、Other Config 四个配置区。
    """

    FUNCTION_OPTIONS = ["功能1", "功能2", "功能3", "功能4", "功能5"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "模板编辑",
            "创建产品模板，并配置 ROI、检测参数、模型和其他参数。",
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
        self.template_panel.setMinimumWidth(300)
        splitter.addWidget(self.template_panel)
        splitter.addWidget(self._build_config_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 900])
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
        layout.addWidget(template_group, 1)

        self.template_combo.currentTextChanged.connect(self._on_template_combo_changed)
        self.new_template_button.clicked.connect(self._new_template)
        self.copy_template_button.clicked.connect(self._copy_template)
        self.delete_template_button.clicked.connect(self._delete_template)
        self.save_template_button.clicked.connect(self._save_current_template)
        return container

    def _build_config_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.addWidget(self._build_roi_group())
        layout.addWidget(self._build_detection_group())
        layout.addWidget(self._build_other_group())
        layout.addWidget(self._build_model_group())
        layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _build_roi_group(self) -> QGroupBox:
        group = QGroupBox("ROI Config")
        layout = QVBoxLayout(group)

        self.roi_canvas = RoiCanvas()
        layout.addWidget(self.roi_canvas, 1)

        button_row = QHBoxLayout()
        self.edit_roi_button = QPushButton("编辑 ROI")
        self.crosshair_check = QCheckBox("显示十字线")
        self.crosshair_check.setChecked(True)
        button_row.addWidget(self.edit_roi_button)
        button_row.addWidget(self.crosshair_check)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.edit_roi_button.clicked.connect(self._open_roi_editor)
        self.crosshair_check.toggled.connect(self.roi_canvas.set_crosshair_visible)
        return group

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
            enable_row.addWidget(self._wrap_with_border(check))
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

    @staticmethod
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

    def _build_model_group(self) -> QGroupBox:
        group = QGroupBox("Model Config")
        layout = QVBoxLayout(group)

        self.model_dir_label = QLabel("Model Config: 未创建")
        self.model_dir_label.setWordWrap(True)
        layout.addWidget(self.model_dir_label)

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

        self._populate_other_params([])
        return group

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

        model_dir = self.config_service.template_dir(name) / "Model Config"
        self.model_dir_label.setText(f"Model Config: {model_dir}")
        self.model_file_label.setText(f"模型文件：{data.get('model_file') or '未加载'}")

        self.roi_canvas.set_rois(deepcopy(data.get("rois", [])))

        detection = data.get("detection") or {}
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

        self._populate_other_params(data.get("other_params", []))

        self.set_result(f"检测结果：模板「{name}」已加载")
        self.set_tip("操作提示：配置完成后点击“保存当前模板”写入模板目录。")

    def set_roi_image(self, pixmap) -> None:
        """接收相机管理页广播的图像，用于 ROI 配置区实时显示。"""
        self.roi_canvas.set_pixmap(pixmap)

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
        data.update(
            {
                "name": name,
                "rois": self.roi_canvas.get_rois(),
                "detection": {
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
                },
                "other_params": self._collect_other_params(),
            }
        )
        self.templates[name] = data
        self._persist_template(name, data)
        self.set_tip(f"操作提示：模板「{name}」已保存到模板目录。")

    def _persist_template(self, name: str, data: dict) -> None:
        payload = {
            "name": data.get("name", name),
            "model_file": data.get("model_file", ""),
            "rois": data.get("rois", []),
            "detection": data.get("detection", {}),
            "other_params": data.get("other_params", []),
        }
        self.config_service.save_template(name, payload)
        self.config_service.ensure_template_dirs(name)
        self.config_service.save_template_category(name, "ROI Config", "roi.yaml", {"rois": payload["rois"]})
        self.config_service.save_template_category(name, "Detection Config", "detection.yaml", {"detection": payload["detection"]})
        self.config_service.save_template_category(name, "Model Config", "model.yaml", {"model_file": payload["model_file"]})
        self.config_service.save_template_category(name, "Other Config", "other.yaml", {"other_params": payload["other_params"]})

    def _open_roi_editor(self) -> None:
        dialog = RoiEditorDialog(
            self.roi_canvas.get_rois(),
            self,
            pixmap=self.roi_canvas.pixmap(),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.roi_canvas.set_rois(dialog.selected_rois())
        if self.current_template_name in self.templates:
            self.templates[self.current_template_name]["rois"] = self.roi_canvas.get_rois()
        self.set_tip("操作提示：ROI 配置已更新，点击“保存当前模板”可写入模板目录。")

    def _load_model(self) -> None:
        if not self.current_template_name:
            self.set_tip("操作提示：请先选择模板。")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载模型",
            "",
            "模型文件 (*.pt *.pth *.onnx *.engine *.bin);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self.templates[self.current_template_name]["model_file"] = file_path
        self.model_file_label.setText(f"模型文件：{file_path}")
        self.set_result(f"检测结果：模型已加载：{file_path}")

    def _release_model(self) -> None:
        if not self.current_template_name:
            self.set_tip("操作提示：请先选择模板。")
            return
        self.templates[self.current_template_name]["model_file"] = ""
        self.model_file_label.setText("模型文件：未加载")
        self.set_result("检测结果：模型已释放")

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

    def auto_save_config(self) -> None:
        self._save_current_template()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].FlowPage))
