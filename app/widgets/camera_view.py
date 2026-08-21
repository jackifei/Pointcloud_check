from __future__ import annotations

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class CameraViewWidget(QWidget):
    """运行看板相机画面显示区。

    支持显示真实图像，并在图像上叠加 ROI 框；未接入图像时显示占位提示。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraView")
        self.setMinimumSize(520, 360)
        self.rois: list[tuple[int, int, int, int]] = []
        self.status_text = "等待相机画面"
        self._pixmap: QPixmap | None = None

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def set_rois(self, rois: list[tuple[int, int, int, int]]) -> None:
        self.rois = rois
        self.update()

    def set_status_text(self, text: str) -> None:
        self.status_text = text
        self.update()

    def _image_rect(self) -> QRectF:
        if self._pixmap is None or self._pixmap.isNull():
            return QRectF()
        image_w = self._pixmap.width()
        image_h = self._pixmap.height()
        if image_w <= 0 or image_h <= 0:
            return QRectF()
        scale = min(self.width() / image_w, self.height() / image_h)
        w = image_w * scale
        h = image_h * scale
        return QRectF((self.width() - w) / 2.0, (self.height() - h) / 2.0, w, h)

    def _scale(self) -> float:
        if self._pixmap is None or self._pixmap.width() <= 0:
            return 1.0
        rect = self._image_rect()
        return rect.width() / self._pixmap.width() if rect.width() > 0 else 1.0

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))

        image_rect = self._image_rect()
        if self._pixmap is not None and not self._pixmap.isNull() and not image_rect.isNull():
            painter.drawPixmap(image_rect.toRect(), self._pixmap)
        else:
            painter.setPen(QColor("#9d9d9d"))
            painter.setFont(QFont("Microsoft YaHei", 13))
            painter.drawText(
                self.rect().adjusted(12, 12, -12, -12),
                Qt.AlignmentFlag.AlignCenter,
                self.status_text,
            )

        # 画中心十字线，模拟相机取景辅助线。
        center = self.rect().center()
        pen = QPen(QColor("#3c3c3c"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(center.x(), 0, center.x(), self.height())
        painter.drawLine(0, center.y(), self.width(), center.y())

        scale = self._scale()
        offset = image_rect.topLeft() if not image_rect.isNull() else QPointF(0.0, 0.0)
        roi_pen = QPen(QColor("#4ec9b0"))
        roi_pen.setWidth(2)
        painter.setPen(roi_pen)
        for index, (x, y, width, height) in enumerate(self.rois):
            if not image_rect.isNull():
                rx = offset.x() + x * scale
                ry = offset.y() + y * scale
                rw = width * scale
                rh = height * scale
            else:
                rx, ry, rw, rh = x, y, width, height
            painter.drawRect(QRect(int(rx), int(ry), int(rw), int(rh)))
            painter.drawText(int(rx) + 4, int(ry) + 16, f"ROI-{index + 1}")
