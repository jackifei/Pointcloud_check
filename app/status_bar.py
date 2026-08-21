from __future__ import annotations

from PyQt6.QtCore import QDateTime, QTimer
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    """VSCode-style bottom status bar."""

    COLORS = {
        "ok": "#d8f5e6",
        "warn": "#fff1cc",
        "error": "#ffd6d6",
        "info": "#ffffff",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(28)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 0, 8, 0)
        root.setSpacing(6)

        self.left_layout = QHBoxLayout()
        self.left_layout.setSpacing(6)
        self.right_layout = QHBoxLayout()
        self.right_layout.setSpacing(6)

        root.addLayout(self.left_layout)
        root.addStretch(1)
        root.addLayout(self.right_layout)

        self._items: dict[str, QLabel] = {}

        # 左侧状态项：用于系统就绪、硬件连接、相机连接和当前页面。
        self.add_item("ready", "就绪", kind="ok")
        self.add_item("fps", "FPS: --")
        self.add_item("image_size", "图像: --")
        self.add_item("hardware", "硬件: 未连接", kind="warn")
        # 相机状态更新示例：
        # self.set_status("camera", "相机: 已连接 GIGE-CAM-01", kind="ok")
        self.add_item("camera", "相机: 未连接", kind="warn")
        self.add_item("page", "界面: 相机管理")

        # 插入点：新增全局状态项时，在这里继续调用 add_item 即可。

        self.add_item("user", "用户: 管理员", side="right")
        self.add_item("template", "模板: 默认产品A", side="right")
        self.add_item("clock", "", side="right")

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

    def add_item(
        self,
        key: str,
        text: str,
        *,
        side: str = "left",
        kind: str = "info",
    ) -> QLabel:
        label = QLabel(text)
        label.setObjectName("statusText")
        self._set_color(label, kind)

        layout = self.right_layout if side == "right" else self.left_layout
        layout.addWidget(label)
        self._items[key] = label
        return label

    def set_status(self, key: str, text: str, kind: str = "info") -> None:
        """更新状态项。

        kind 可选 info / ok / warn / error。
        例如相机连接成功：set_status("camera", "相机: 已连接", "ok")
        """
        if key not in self._items:
            self.add_item(key, text, kind=kind)
            return
        self._items[key].setText(text)
        self._set_color(self._items[key], kind)

    def show_message(self, message: str, timeout_ms: int = 5000) -> None:
        self.set_status("ready", message, kind="info")
        QTimer.singleShot(timeout_ms, lambda: self.set_status("ready", "就绪", kind="ok"))

    def _set_color(self, label: QLabel, kind: str) -> None:
        color = self.COLORS.get(kind, self.COLORS["info"])
        label.setStyleSheet(f"color: {color};")

    def _update_clock(self) -> None:
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.set_status("clock", now)
