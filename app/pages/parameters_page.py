from __future__ import annotations

from PyQt6.QtCore import QTime, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService


class ParametersPage(BasePage):
    """系统参数页。

    相机参数已迁移到相机管理页，检测参数已迁移到模板编辑页；
    此处包含系统参数、计数方式、班次时间和存储路径。
    """

    SHIFT_COUNT = 6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "参数",
            "系统参数、OK/NG 计数方式、班次时间和存储路径。",
            parent,
        )
        self.config_service = ConfigService()
        self.shift_start_edits: list[QTimeEdit] = []
        self.shift_end_edits: list[QTimeEdit] = []
        self._build_ui()
        self._load_config()
        self.set_result("检测结果：系统参数已加载")
        self.set_tip("操作提示：修改后点击“保存系统参数”写入 config/system.yaml。")

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        system_group = QGroupBox("系统参数")
        form = QFormLayout(system_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["简体中文", "English"])

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARN", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")

        self.auto_save_check = QCheckBox("启用自动保存")
        self.auto_save_check.setChecked(True)

        form.addRow("界面语言", self.language_combo)
        form.addRow("日志级别", self.log_level_combo)
        form.addRow("", self.auto_save_check)
        layout.addWidget(system_group)

        layout.addWidget(self._build_counting_group())

        storage_group = QGroupBox("存储路径")
        storage_form = QFormLayout(storage_group)
        storage_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.result_dir_edit = QLineEdit()
        self.result_dir_edit.setPlaceholderText("选择检测结果存储目录")
        self.result_dir_button = QPushButton("选择")
        result_row = QWidget()
        result_layout = QHBoxLayout(result_row)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.addWidget(self.result_dir_edit, 1)
        result_layout.addWidget(self.result_dir_button)

        self.data_dir_edit = QLineEdit()
        self.data_dir_edit.setPlaceholderText("选择数据存储目录")
        self.data_dir_button = QPushButton("选择")
        data_row = QWidget()
        data_layout = QHBoxLayout(data_row)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.addWidget(self.data_dir_edit, 1)
        data_layout.addWidget(self.data_dir_button)

        storage_form.addRow("检测结果目录", result_row)
        storage_form.addRow("数据存储目录", data_row)
        layout.addWidget(storage_group)

        self.save_button = QPushButton("保存系统参数")
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        scroll.setWidget(container)
        self.add_to_content(scroll, stretch=1)

        self.save_button.clicked.connect(self._save_config)
        self.result_dir_button.clicked.connect(self._choose_result_dir)
        self.data_dir_button.clicked.connect(self._choose_data_dir)

    def _build_counting_group(self) -> QGroupBox:
        group = QGroupBox("计数设置")
        layout = QVBoxLayout(group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("OK/NG 计数方式"))
        self.counting_mode_combo = QComboBox()
        self.counting_mode_combo.addItem("日计数", "day")
        self.counting_mode_combo.addItem("班计数", "shift")
        mode_row.addWidget(self.counting_mode_combo)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        hint = QLabel("班计数模式下，清零时间按每班开始时间计算；日计数默认 0 点后进入第二天清零。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.shift_table = QTableWidget(self.SHIFT_COUNT, 3)
        self.shift_table.setHorizontalHeaderLabels(["班次", "开始时间", "结束时间"])
        header = self.shift_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.shift_table.verticalHeader().setVisible(False)
        self.shift_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.shift_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for index in range(self.SHIFT_COUNT):
            name_item = QTableWidgetItem(f"班{index + 1}")
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.shift_table.setItem(index, 0, name_item)

            start_edit = QTimeEdit(QTime(0, 0))
            start_edit.setDisplayFormat("HH:mm")
            end_edit = QTimeEdit(QTime(0, 0))
            end_edit.setDisplayFormat("HH:mm")
            self.shift_table.setCellWidget(index, 1, start_edit)
            self.shift_table.setCellWidget(index, 2, end_edit)
            self.shift_start_edits.append(start_edit)
            self.shift_end_edits.append(end_edit)

        layout.addWidget(self.shift_table)
        return group

    def _save_config(self) -> None:
        self.config_service.save_page_config(
            "system",
            {
                "language": self.language_combo.currentText(),
                "log_level": self.log_level_combo.currentText(),
                "auto_save": self.auto_save_check.isChecked(),
                "result_dir": self.result_dir_edit.text(),
                "data_dir": self.data_dir_edit.text(),
                "counting_mode": self.counting_mode_combo.currentData(),
                "shifts": self._collect_shifts(),
            },
        )
        self.set_tip("操作提示：系统参数已保存到 config/system.yaml。")

    def _load_config(self) -> None:
        data = self.config_service.load_page_config("system")
        if not data:
            return
        self.language_combo.setCurrentText(str(data.get("language", self.language_combo.currentText())))
        self.log_level_combo.setCurrentText(str(data.get("log_level", self.log_level_combo.currentText())))
        self.auto_save_check.setChecked(bool(data.get("auto_save", self.auto_save_check.isChecked())))
        self.result_dir_edit.setText(str(data.get("result_dir", "")))
        self.data_dir_edit.setText(str(data.get("data_dir", "")))
        self.counting_mode_combo.setCurrentIndex(
            self.counting_mode_combo.findData(data.get("counting_mode", "day"))
        )
        self._apply_shifts(data.get("shifts", []))

    def _collect_shifts(self) -> list[dict]:
        shifts: list[dict] = []
        for index in range(self.SHIFT_COUNT):
            shifts.append(
                {
                    "name": f"班{index + 1}",
                    "start": self.shift_start_edits[index].time().toString("HH:mm"),
                    "end": self.shift_end_edits[index].time().toString("HH:mm"),
                }
            )
        return shifts

    def _apply_shifts(self, shifts: list[dict]) -> None:
        for index in range(self.SHIFT_COUNT):
            shift = shifts[index] if index < len(shifts) else {}
            start = QTime.fromString(str(shift.get("start", "00:00")), "HH:mm")
            end = QTime.fromString(str(shift.get("end", "00:00")), "HH:mm")
            if start.isValid():
                self.shift_start_edits[index].setTime(start)
            if end.isValid():
                self.shift_end_edits[index].setTime(end)

    def _choose_result_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择检测结果存储目录")
        if directory:
            self.result_dir_edit.setText(directory)

    def _choose_data_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择数据存储目录")
        if directory:
            self.data_dir_edit.setText(directory)

    def auto_save_config(self) -> None:
        self._save_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].ParametersPage))
