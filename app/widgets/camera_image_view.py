from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class CameraImageView(QWidget):
    """相机图像显示控件。

    支持鼠标滚轮缩放图像，并可拖动十字虚线。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraImageView")
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)

        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._cross_ratio = QPointF(0.5, 0.5)
        self._dragging_cross = False
        self._panning = False
        self._last_pan_pos = QPointF(0.0, 0.0)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def clear(self) -> None:
        self._pixmap = None
        self.update()

    def center_cross(self) -> None:
        self._cross_ratio = QPointF(0.5, 0.5)
        self.update()

    def fit_to_view(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        zoom_x = self.width() / self._pixmap.width()
        zoom_y = self.height() / self._pixmap.height()
        self._zoom = max(0.1, min(zoom_x, zoom_y))
        self._pan_offset = QPointF(0.0, 0.0)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))

        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(QColor("#9d9d9d"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "等待相机画面",
            )
            return

        base_w = self._pixmap.width() * self._zoom
        base_h = self._pixmap.height() * self._zoom
        image_rect = QRectF(
            (self.width() - base_w) / 2.0 + self._pan_offset.x(),
            (self.height() - base_h) / 2.0 + self._pan_offset.y(),
            base_w,
            base_h,
        )
        painter.drawPixmap(image_rect.toRect(), self._pixmap)

        cross_x = image_rect.left() + image_rect.width() * self._cross_ratio.x()
        cross_y = image_rect.top() + image_rect.height() * self._cross_ratio.y()

        pen = QPen(QColor("#4ec9b0"))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(
            int(cross_x),
            int(image_rect.top()),
            int(cross_x),
            int(image_rect.bottom()),
        )
        painter.drawLine(
            int(image_rect.left()),
            int(cross_y),
            int(image_rect.right()),
            int(cross_y),
        )

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom = max(0.1, min(10.0, self._zoom * factor))
        self.update()

    def mousePressEvent(self, event) -> None:
        if self._pixmap is None:
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            cross_point = self._cross_image_point()
            distance = (event.position().toPoint() - cross_point).manhattanLength()
            if distance <= 24:
                self._dragging_cross = True

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._last_pan_pos
            self._pan_offset += delta
            self._last_pan_pos = event.position()
            self.update()
            return

        if self._dragging_cross and self._pixmap is not None:
            image_rect = self._image_rect()
            if image_rect.isNull():
                return
            x = (event.position().x() - image_rect.left()) / image_rect.width()
            y = (event.position().y() - image_rect.top()) / image_rect.height()
            self._cross_ratio = QPointF(max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self.unsetCursor()
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_cross = False

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.fit_to_view()

    def _image_rect(self) -> QRectF:
        if self._pixmap is None:
            return QRectF()
        base_w = self._pixmap.width() * self._zoom
        base_h = self._pixmap.height() * self._zoom
        return QRectF(
            (self.width() - base_w) / 2.0 + self._pan_offset.x(),
            (self.height() - base_h) / 2.0 + self._pan_offset.y(),
            base_w,
            base_h,
        )

    def _cross_image_point(self):
        image_rect = self._image_rect()
        return image_rect.topLeft().toPoint() + QPointF(
            image_rect.width() * self._cross_ratio.x(),
            image_rect.height() * self._cross_ratio.y(),
        ).toPoint()
