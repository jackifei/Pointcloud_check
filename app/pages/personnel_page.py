from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
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
else:
    from .base_page import BasePage


class PersonnelPage(BasePage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "人员管理",
            "管理系统操作人员及其角色权限。",
            parent,
        )
        self._build_ui()
        self._populate_demo_users()
        self.set_result("检测结果：已加载演示人员数据")
        self.set_tip("操作提示：人员管理可替换为数据库、LDAP 或权限配置。")

    def _build_ui(self) -> None:
        group = QGroupBox("人员列表")
        layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        add_button = QPushButton("新增")
        edit_button = QPushButton("编辑")
        delete_button = QPushButton("删除")
        refresh_button = QPushButton("刷新")
        toolbar.addWidget(add_button)
        toolbar.addWidget(edit_button)
        toolbar.addWidget(delete_button)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["工号", "姓名", "角色", "权限", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.add_to_content(group, stretch=1)

        add_button.clicked.connect(lambda: self._show_placeholder("新增人员"))
        edit_button.clicked.connect(lambda: self._show_placeholder("编辑人员"))
        delete_button.clicked.connect(self._delete_selected)
        refresh_button.clicked.connect(self._populate_demo_users)

    def _populate_demo_users(self) -> None:
        self.table.setRowCount(0)
        users = [
            ("1001", "管理员", "系统管理员", "全部", "启用"),
            ("1002", "张工", "工艺工程师", "模板编辑、参数", "启用"),
            ("1003", "李工", "设备工程师", "硬件配置、日志", "启用"),
            ("1004", "王工", "质检员", "仅查看", "停用"),
        ]
        for user in users:
            self._append_user(user)

    def _append_user(self, user: tuple[str, str, str, str, str]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate(user):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, column, item)

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要删除的人员。")
            return
        name = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        answer = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除人员“{name}”吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.table.removeRow(row)

    def _show_placeholder(self, title: str) -> None:
        QMessageBox.information(self, title, "当前为 demo 框架，实际表单可在此基础上接入。")

    # 插入点：人员数据可替换为数据库、LDAP 或本地权限配置文件。


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].PersonnelPage))
