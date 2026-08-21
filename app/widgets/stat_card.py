from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class StatCard(QFrame):
    """看板统计卡片。

    用于显示 OK、NG、日/周/月统计、OK 完成率等关键指标。
    """

    def __init__(
        self,
        title: str,
        value: str = "--",
        accent: str = "#4ec9b0",
        compact: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")

        layout = QHBoxLayout(self) if compact else QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statCardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statCardValue")
        self.value_label.setStyleSheet(f"color: {accent};")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if compact:
            self.value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.value_label.setMinimumWidth(54)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        if compact:
            layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
