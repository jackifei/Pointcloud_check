from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class BasePage(QWidget):
    """页面公共外壳。

    顶部不再显示页面名称，而是显示当前页面的检测结果/状态和操作提示。
    具体页面可通过 set_result / set_tip 动态更新。
    """

    tip_changed = pyqtSignal(str)

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        # title/subtitle 仅作为内部标识或默认提示，不再直接展示页面标题。
        self.page_name = title
        self._tip_text = subtitle or "操作提示：--"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        outer.addLayout(self.content_layout, 1)

        self._result_text = "检测结果：--"

    def set_result(self, text: str) -> None:
        self._result_text = text

    def set_tip(self, text: str) -> None:
        self._tip_text = text
        self.tip_changed.emit(text)

    def current_tip(self) -> str:
        return self._tip_text

    def add_to_content(self, widget: QWidget, stretch: int = 0) -> None:
        self.content_layout.addWidget(widget, stretch)

    def add_layout_to_content(self, layout: QVBoxLayout, stretch: int = 0) -> None:
        self.content_layout.addLayout(layout, stretch)

    def auto_save_config(self) -> None:
        """页面关闭前自动保存配置。

        具体页面可覆盖此方法，把当前配置写入 config 或 flow 目录。
        """
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.auto_save_config()
        super().closeEvent(event)

    # 插入点：可增加统一的页面暂停/恢复、定时刷新、权限控制等公共动作。
