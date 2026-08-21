from __future__ import annotations

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
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
    from app.services.log_service import LogService
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..services.log_service import LogService


class LogPage(BasePage):
    """日志页。

    仅加载并显示当天日志，界面最多显示最近 100 条；
    日志按天写入项目根目录 log/YYYYMMDD.txt，使用逗号分隔格式。
    """

    MAX_DISPLAY_ROWS = 100

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "日志",
            "查看当天系统运行日志，支持按级别筛选。",
            parent,
        )
        self.config_service = ConfigService()
        self.log_service = LogService()
        self._build_ui()
        self._load_today_logs()
        self.set_result("检测结果：已加载当天日志")
        self.set_tip("操作提示：仅显示当天日志，最多 100 条；日志保存在项目根目录 log 目录。")

    def _build_ui(self) -> None:
        group = QGroupBox("运行日志")
        layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("级别"))

        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "DEBUG", "INFO", "WARN", "ERROR"])
        toolbar.addWidget(self.level_combo)

        self.add_test_log_button = QPushButton("添加测试日志")
        self.clear_button = QPushButton("清空日志")
        self.export_button = QPushButton("导出 CSV")
        self.save_filter_button = QPushButton("保存筛选")
        toolbar.addWidget(self.add_test_log_button)
        toolbar.addWidget(self.clear_button)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.save_filter_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["时间", "级别", "来源", "消息"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.log_table, 1)

        self.add_to_content(group, stretch=1)

        self.level_combo.currentTextChanged.connect(self._apply_filter)
        self.add_test_log_button.clicked.connect(self._add_random_log)
        self.clear_button.clicked.connect(self._clear_logs)
        self.export_button.clicked.connect(self._export_placeholder)
        self.save_filter_button.clicked.connect(self._save_filter_config)

    def _load_today_logs(self) -> None:
        self.log_table.setRowCount(0)
        for time_text, level, source, message in self.log_service.load_today(self.MAX_DISPLAY_ROWS):
            self._add_row_to_table(time_text, level, source, message)
        self._apply_filter(self.level_combo.currentText())

    def _append_log(self, level: str, source: str, message: str) -> None:
        time_text = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.log_service.append(level, source, message)
        self._add_row_to_table(time_text, level, source, message)
        self._trim_to_latest()
        self._apply_filter(self.level_combo.currentText())

    def _add_row_to_table(self, time_text: str, level: str, source: str, message: str) -> None:
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        time_item = QTableWidgetItem(time_text)
        level_item = QTableWidgetItem(level)
        source_item = QTableWidgetItem(source)
        message_item = QTableWidgetItem(message)

        if level == "ERROR":
            level_item.setForeground(Qt.GlobalColor.red)
        elif level == "WARN":
            level_item.setForeground(Qt.GlobalColor.yellow)
        elif level == "INFO":
            level_item.setForeground(Qt.GlobalColor.green)

        for column, item in enumerate([time_item, level_item, source_item, message_item]):
            self.log_table.setItem(row, column, item)
        self.log_table.scrollToBottom()

    def _trim_to_latest(self) -> None:
        while self.log_table.rowCount() > self.MAX_DISPLAY_ROWS:
            self.log_table.removeRow(0)

    def _apply_filter(self, level: str) -> None:
        for row in range(self.log_table.rowCount()):
            item = self.log_table.item(row, 1)
            match = level == "全部" or (item is not None and item.text() == level)
            self.log_table.setRowHidden(row, not match)

    def _add_random_log(self) -> None:
        levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        selected = self.level_combo.currentText()
        level = selected if selected != "全部" else "INFO"
        if level not in levels:
            level = "INFO"
        self._append_log(level, "demo", "这是一条测试日志")

    def _clear_logs(self) -> None:
        answer = QMessageBox.question(
            self,
            "清空日志",
            "确定清空当天日志吗？该操作会删除当天的日志文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.log_service.clear_today()
        self.log_table.setRowCount(0)
        self.set_result("检测结果：当天日志已清空")

    def _export_placeholder(self) -> None:
        self.set_tip(
            f"操作提示：当天日志已按 CSV 格式保存到 {self.log_service.today_file()}。"
        )

    def _save_filter_config(self) -> None:
        self.config_service.save_page_config(
            "log",
            {"level_filter": self.level_combo.currentText()},
        )
        self.set_tip("操作提示：日志筛选条件已保存到 config/log.yaml。")

    def auto_save_config(self) -> None:
        self._save_filter_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].LogPage))
