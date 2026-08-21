from __future__ import annotations

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateTimeEdit,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
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
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService


class ResultQueryPage(BasePage):
    """检测结果查询页。

    支持按时间、产品模板、完成状态和报警状态筛选，可扩展到数据库或文件检索。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "结果查询",
            "可按时间范围查询检测记录，查看完成状态、提示与报警信息。",
            parent,
        )
        self.config_service = ConfigService()
        self._build_ui()
        self._append_demo_results()
        self._update_summary()

    def _build_ui(self) -> None:
        filter_group = QGroupBox("查询条件")
        layout = QVBoxLayout(filter_group)

        top = QHBoxLayout()
        top.addWidget(QLabel("开始时间"))
        self.start_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(-3))
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        top.addWidget(self.start_edit)

        top.addWidget(QLabel("结束时间"))
        self.end_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        top.addWidget(self.end_edit)

        top.addWidget(QLabel("产品/模板"))
        self.product_combo = QComboBox()
        self.product_combo.addItems(["全部", "默认产品A", "产品B", "产品C"])
        top.addWidget(self.product_combo)

        top.addWidget(QLabel("完成状态"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "已完成", "未完成"])
        top.addWidget(self.status_combo)

        top.addWidget(QLabel("报警"))
        self.alarm_combo = QComboBox()
        self.alarm_combo.addItems(["全部", "有报警", "无报警"])
        top.addWidget(self.alarm_combo)
        search_button = QPushButton("查询")
        reset_button = QPushButton("重置")
        export_button = QPushButton("导出 CSV")
        save_filter_button = QPushButton("保存条件")
        top.addWidget(search_button)
        top.addWidget(reset_button)
        top.addWidget(export_button)
        top.addWidget(save_filter_button)
        self.summary_label = QLabel("汇总：总数 0，完成 0，报警 0")
        top.addWidget(self.summary_label)
        top.addStretch(1)
        layout.addLayout(top)

        self.add_to_content(filter_group)

        result_group = QGroupBox("检测记录")
        result_layout = QVBoxLayout(result_group)

        self.result_table = QTableWidget(0, 7)
        self.result_table.setHorizontalHeaderLabels(
            ["检测时间", "产品/模板", "批次号", "完成状态", "检测结果", "提示信息", "报警信息"]
        )
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detail_edit = QPlainTextEdit()
        self.detail_edit.setReadOnly(True)
        self.detail_edit.setPlaceholderText("选中一条记录后，这里显示详细检测信息。")

        self.detail_splitter = QSplitter(Qt.Orientation.Vertical)
        self.detail_splitter.setChildrenCollapsible(False)
        self.detail_splitter.setHandleWidth(5)
        self.detail_splitter.addWidget(self.result_table)
        self.detail_splitter.addWidget(self.detail_edit)
        self.detail_splitter.setSizes([520, 150])
        result_layout.addWidget(self.detail_splitter, 1)

        self.add_to_content(result_group, stretch=1)

        search_button.clicked.connect(self._apply_filter)
        reset_button.clicked.connect(self._reset_filter)
        export_button.clicked.connect(self._export_placeholder)
        save_filter_button.clicked.connect(self._save_config)
        self.result_table.itemSelectionChanged.connect(self._show_detail)

    def _append_demo_results(self) -> None:
        now = QDateTime.currentDateTime()
        samples = [
            (now.addSecs(-3600 * 2), "默认产品A", "B20260816001", "已完成", "OK：2 个目标", "检测正常", ""),
            (now.addSecs(-3600 * 6), "产品B", "B20260816002", "未完成", "流程中断", "等待下一工位", "相机超时"),
            (now.addSecs(-3600 * 12), "默认产品A", "B20260815009", "已完成", "OK：1 个目标", "检测正常", ""),
            (now.addSecs(-3600 * 28), "产品C", "B20260815003", "已完成", "NG：缺料", "请复核物料", "缺料报警"),
            (now.addSecs(-3600 * 50), "产品B", "B20260814011", "已完成", "OK：3 个目标", "检测正常", ""),
        ]
        for row_data in samples:
            self._append_result_row(row_data)

    def _append_result_row(self, row_data: tuple) -> None:
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        dt = row_data[0]
        time_item = QTableWidgetItem(dt.toString("yyyy-MM-dd HH:mm:ss"))
        time_item.setData(Qt.ItemDataRole.UserRole, dt)
        self.result_table.setItem(row, 0, time_item)

        for column, value in enumerate(row_data[1:], start=1):
            item = QTableWidgetItem(value)
            self.result_table.setItem(row, column, item)

        alarm_item = self.result_table.item(row, 6)
        if alarm_item and alarm_item.text():
            alarm_item.setForeground(Qt.GlobalColor.red)

    def _apply_filter(self) -> None:
        start = self.start_edit.dateTime()
        end = self.end_edit.dateTime()
        product = self.product_combo.currentText()
        status = self.status_combo.currentText()
        alarm = self.alarm_combo.currentText()

        for row in range(self.result_table.rowCount()):
            time_item = self.result_table.item(row, 0)
            dt = time_item.data(Qt.ItemDataRole.UserRole) if time_item else None
            in_time = dt is not None and start <= dt <= end
            in_product = product == "全部" or self.result_table.item(row, 1).text() == product
            in_status = status == "全部" or self.result_table.item(row, 3).text() == status
            alarm_text = self.result_table.item(row, 6).text()
            in_alarm = (
                alarm == "全部"
                or (alarm == "有报警" and bool(alarm_text))
                or (alarm == "无报警" and not alarm_text)
            )
            self.result_table.setRowHidden(row, not (in_time and in_product and in_status and in_alarm))
        self._update_summary()

    def _reset_filter(self) -> None:
        self.start_edit.setDateTime(QDateTime.currentDateTime().addDays(-3))
        self.end_edit.setDateTime(QDateTime.currentDateTime())
        self.product_combo.setCurrentText("全部")
        self.status_combo.setCurrentText("全部")
        self.alarm_combo.setCurrentText("全部")
        self._apply_filter()

    def _update_summary(self) -> None:
        total = self.result_table.rowCount()
        finished = 0
        alarms = 0
        for row in range(total):
            if self.result_table.isRowHidden(row):
                continue
            if self.result_table.item(row, 3).text() == "已完成":
                finished += 1
            if self.result_table.item(row, 6).text():
                alarms += 1
        self.summary_label.setText(f"汇总：总数 {total}，完成 {finished}，报警 {alarms}")
        self.set_result(f"检测结果：当前显示 {total} 条记录，报警 {alarms} 条")

    def _show_detail(self) -> None:
        row = self.result_table.currentRow()
        if row < 0:
            self.detail_edit.clear()
            return
        values = [self.result_table.item(row, col).text() for col in range(self.result_table.columnCount())]
        self.detail_edit.setPlainText(
            f"时间：{values[0]}\n产品：{values[1]}\n批次：{values[2]}\n"
            f"状态：{values[3]}\n结果：{values[4]}\n提示：{values[5]}\n报警：{values[6] or '无'}"
        )

    def _export_placeholder(self) -> None:
        self.set_tip("操作提示：导出 CSV 为占位功能，可在此接入 pandas/openpyxl 或文件服务。")

    def _save_config(self) -> None:
        self.config_service.save_page_config(
            "result_query",
            {
                "start": self.start_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                "end": self.end_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                "product": self.product_combo.currentText(),
                "status": self.status_combo.currentText(),
                "alarm": self.alarm_combo.currentText(),
            },
        )
        self.set_tip("操作提示：查询条件已保存到 config/result_query.yaml。")

    def auto_save_config(self) -> None:
        self._save_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].ResultQueryPage))
