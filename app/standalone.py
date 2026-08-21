from __future__ import annotations

import sys
from typing import Type

from PyQt6.QtWidgets import QApplication, QWidget

from .theme import APP_STYLESHEET


def run_page(page_class: Type[QWidget]) -> int:
    """以独立窗口运行某个页面，方便单独调试。"""
    app = QApplication(sys.argv)
    app.setApplicationName("SOP Page Debug")
    app.setStyleSheet(APP_STYLESHEET)

    window = page_class()
    window.setWindowTitle(page_class.__name__)
    window.resize(1100, 720)
    window.show()
    return app.exec()


# 插入点：可扩展为命令行解析，例如 python run_page.py camera / flow / dashboard。
