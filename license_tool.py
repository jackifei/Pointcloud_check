from __future__ import annotations

import sys

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QApplication,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.checkdog.license_manager import LicenseManager


class LicenseToolWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SOP 授权码生成工具")
        self.resize(560, 320)
        self.manager = LicenseManager()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.machine_edit = QLineEdit(self.manager.machine_code())
        self.machine_edit.setReadOnly(True)

        self.start_edit = QDateEdit(QDate.currentDate())
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")

        self.end_edit = QDateEdit(QDate.currentDate().addYears(1))
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")

        form.addRow("机器码", self.machine_edit)
        form.addRow("起始日期", self.start_edit)
        form.addRow("停止日期", self.end_edit)
        layout.addLayout(form)

        generate_button = QPushButton("生成密钥")
        layout.addWidget(generate_button)

        self.key_edit = QLineEdit()
        self.key_edit.setReadOnly(True)
        layout.addWidget(QLabel("生成的密钥："))
        layout.addWidget(self.key_edit)

        generate_button.clicked.connect(self._generate)

    def _generate(self) -> None:
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        key = self.manager.generate_key(self.machine_edit.text(), start, end)
        self.key_edit.setText(key)


def main() -> int:
    app = QApplication(sys.argv)
    window = LicenseToolWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
