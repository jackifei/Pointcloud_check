from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .roi_canvas import RoiCanvas, normalize_roi


class RoiEditorDialog(QDialog):
    """ROI 大图编辑弹窗。

    支持绘制旋转矩形和圆形，旋转矩形可旋转；
    拖动圆形圆心或矩形中心可移动 ROI。
    """

    def __init__(
        self,
        rois: list[dict],
        parent: QWidget | None = None,
        pixmap=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ROI 创建与编辑")
        self.resize(1120, 720)
        self._updating = False
        self._initial_rois = [normalize_roi(roi) for roi in (rois or [])]
        self._build_ui()
        self.canvas.set_rois(self._initial_rois)
        if pixmap is not None:
            self.canvas.set_pixmap(pixmap)
        self._populate_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        hint = QLabel("选择绘制形状；双击空白处新增；拖动圆心或矩形中心可移动；选中旋转矩形后可用按钮旋转。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("绘制形状"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItem("旋转矩形", "rect")
        self.shape_combo.addItem("圆形", "circle")
        toolbar.addWidget(self.shape_combo)
        toolbar.addStretch(1)

        toolbar.addWidget(QLabel("旋转倍率"))
        self.rotation_step_combo = QComboBox()
        self.rotation_step_combo.addItem("精细 1°", 1.0)
        self.rotation_step_combo.addItem("中等 5°", 5.0)
        self.rotation_step_combo.addItem("最大 15°", 15.0)
        toolbar.addWidget(self.rotation_step_combo)

        self.rotate_forward_button = QPushButton("正转")
        self.rotate_backward_button = QPushButton("反转")
        toolbar.addWidget(self.rotate_forward_button)
        toolbar.addWidget(self.rotate_backward_button)

        self.crosshair_check = QCheckBox("显示十字线")
        self.crosshair_check.setChecked(True)
        toolbar.addWidget(self.crosshair_check)
        root.addLayout(toolbar)

        content = QHBoxLayout()
        self.canvas = RoiCanvas()
        self.canvas.set_selected_color("#ff3333")
        content.addWidget(self.canvas, 3)

        table_area = QVBoxLayout()
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["名称", "形状", "中心X", "中心Y", "宽/半径", "高", "角度"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table_area.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        add_button = QPushButton("添加 ROI")
        delete_button = QPushButton("删除选中")
        buttons.addWidget(add_button)
        buttons.addWidget(delete_button)
        table_area.addLayout(buttons)
        content.addLayout(table_area, 2)
        root.addLayout(content, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        apply_button = QPushButton("应用")
        cancel_button = QPushButton("取消")
        bottom.addWidget(apply_button)
        bottom.addWidget(cancel_button)
        root.addLayout(bottom)

        add_button.clicked.connect(self._add_roi)
        delete_button.clicked.connect(self._delete_selected_roi)
        apply_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.rotate_forward_button.clicked.connect(
            lambda: self._rotate_selected(float(self.rotation_step_combo.currentData()))
        )
        self.rotate_backward_button.clicked.connect(
            lambda: self._rotate_selected(-float(self.rotation_step_combo.currentData()))
        )
        self.crosshair_check.toggled.connect(self.canvas.set_crosshair_visible)
        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.add_requested.connect(self._add_roi_at)
        self.table.itemChanged.connect(self._on_table_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection)

    def selected_rois(self) -> list[dict]:
        return deepcopy(self.canvas.rois)

    def _populate_table(self) -> None:
        self._updating = True
        self.table.setRowCount(0)
        for roi in self.canvas.rois:
            self._append_roi_row(roi)
        self._updating = False

    def _append_roi_row(self, roi: dict) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        is_circle = roi["shape"] == "circle"
        values = [
            str(roi.get("name", "")),
            "圆形" if is_circle else "旋转矩形",
            f"{roi['cx']:.1f}",
            f"{roi['cy']:.1f}",
            f"{roi['radius']:.1f}" if is_circle else f"{roi['w']:.1f}",
            "" if is_circle else f"{roi['h']:.1f}",
            "" if is_circle else f"{roi['angle']:.1f}",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if column == 1 or (is_circle and column in (5, 6)):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, column, item)

    def _add_roi(self) -> None:
        pixmap = self.canvas.pixmap()
        if pixmap is not None and not pixmap.isNull():
            cx = pixmap.width() / 2.0
            cy = pixmap.height() / 2.0
        else:
            cx = 80.0 + len(self.canvas.rois) * 20.0
            cy = 80.0 + len(self.canvas.rois) * 20.0
        self._add_roi_at(cx, cy)

    def _add_roi_at(self, x: float, y: float) -> None:
        shape = self.shape_combo.currentData()
        name = f"ROI-{len(self.canvas.rois) + 1}"
        if shape == "circle":
            roi = {
                "name": name,
                "shape": "circle",
                "cx": float(x),
                "cy": float(y),
                "radius": 60.0,
            }
        else:
            roi = {
                "name": name,
                "shape": "rect",
                "cx": float(x),
                "cy": float(y),
                "w": 160.0,
                "h": 120.0,
                "angle": 0.0,
            }
        self.canvas.rois.append(roi)
        self._populate_table()
        self.canvas.selected_index = len(self.canvas.rois) - 1
        self.canvas.update()
        self.table.selectRow(len(self.canvas.rois) - 1)

    def _delete_selected_roi(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.canvas.rois):
            return
        self.canvas.rois.pop(row)
        self._populate_table()
        self.canvas.update()

    def _rotate_selected(self, delta: float) -> None:
        index = self.canvas.selected_index
        if index < 0 or index >= len(self.canvas.rois):
            return
        roi = self.canvas.rois[index]
        if roi["shape"] != "rect":
            return
        roi["angle"] = (roi["angle"] + delta) % 360.0
        self._populate_table()
        self.canvas.selected_index = index
        self.canvas.update()
        self.table.selectRow(index)

    def _on_canvas_selection(self, index: int) -> None:
        if index < 0 or index >= self.table.rowCount():
            self.table.clearSelection()
            return
        self.table.selectRow(index)

    def _on_table_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self.canvas.selected_index = rows[0].row()
        self.canvas.update()

    def _on_table_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row = item.row()
        column = item.column()
        if row >= len(self.canvas.rois):
            return
        roi = self.canvas.rois[row]
        text = item.text().strip()

        if column == 0:
            roi["name"] = text
        elif column == 2:
            roi["cx"] = self._to_float(text, roi["cx"])
        elif column == 3:
            roi["cy"] = self._to_float(text, roi["cy"])
        elif column == 4:
            value = self._to_float(text, roi.get("radius", roi.get("w", 1.0)))
            if roi["shape"] == "circle":
                roi["radius"] = max(1.0, value)
            else:
                roi["w"] = max(1.0, value)
        elif column == 5 and roi["shape"] == "rect":
            roi["h"] = max(1.0, self._to_float(text, roi["h"]))
        elif column == 6 and roi["shape"] == "rect":
            roi["angle"] = self._to_float(text, roi["angle"])

        self.canvas.selected_index = row
        self.canvas.update()

    @staticmethod
    def _to_float(text: str, default: float) -> float:
        try:
            return float(text)
        except ValueError:
            return default
