from __future__ import annotations

from copy import deepcopy
from math import cos, radians, sin, sqrt

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


def normalize_roi(roi: dict) -> dict:
    """把旧版 x/y/w/h 或新版 center 数据统一为圆形/旋转矩形结构。"""
    if not isinstance(roi, dict):
        roi = {}
    name = str(roi.get("name", ""))
    shape = roi.get("shape")

    if shape == "circle":
        cx = float(roi.get("cx", roi.get("x", 0)))
        cy = float(roi.get("cy", roi.get("y", 0)))
        radius = float(roi.get("radius", float(roi.get("w", 80)) / 2.0))
        return {
            "name": name,
            "shape": "circle",
            "cx": cx,
            "cy": cy,
            "radius": max(1.0, radius),
        }

    if "cx" in roi and "cy" in roi:
        cx = float(roi["cx"])
        cy = float(roi["cy"])
    else:
        x = float(roi.get("x", 0))
        y = float(roi.get("y", 0))
        w = float(roi.get("w", 100))
        h = float(roi.get("h", 100))
        cx = x + w / 2.0
        cy = y + h / 2.0

    w = float(roi.get("w", 100))
    h = float(roi.get("h", 100))
    angle = float(roi.get("angle", 0))
    return {
        "name": name,
        "shape": "rect",
        "cx": cx,
        "cy": cy,
        "w": max(1.0, w),
        "h": max(1.0, h),
        "angle": angle,
    }


class RoiCanvas(QWidget):
    """ROI 画布。

    支持图像显示、滚轮缩放、右键拖动平移、红色十字线；
    ROI 支持圆形和旋转矩形，使用轮廓线绘制（无填充），
    支持点击选中、拖动圆心/矩形中心进行移动。
    """

    selection_changed = pyqtSignal(int)
    add_requested = pyqtSignal(float, float)

    CENTER_HIT_RADIUS = 10.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("roiCanvas")
        self.setMinimumSize(320, 200)
        self.setMouseTracking(True)
        self.rois: list[dict] = []
        self.selected_index = -1
        self._pixmap: QPixmap | None = None
        self._dragging = False
        self._panning = False
        self._last_pan_pos = QPointF(0.0, 0.0)
        self._zoom = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._show_crosshair = True
        self.selected_color = "#39ff14"
        self.unselected_color = "#3c8f7a"

    def set_rois(self, rois: list[dict]) -> None:
        self.rois = [normalize_roi(roi) for roi in (rois or [])]
        self.selected_index = -1
        self.update()

    def get_rois(self) -> list[dict]:
        return deepcopy(self.rois)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def pixmap(self) -> QPixmap | None:
        return self._pixmap

    def set_selected_color(self, color: str) -> None:
        self.selected_color = color
        self.update()

    def set_crosshair_visible(self, visible: bool) -> None:
        self._show_crosshair = visible
        self.update()

    def crosshair_visible(self) -> bool:
        return self._show_crosshair

    def _image_rect(self) -> QRectF:
        if self._pixmap is None or self._pixmap.isNull():
            return QRectF()
        image_w = self._pixmap.width()
        image_h = self._pixmap.height()
        if image_w <= 0 or image_h <= 0:
            return QRectF()
        w = image_w * self._zoom
        h = image_h * self._zoom
        return QRectF(
            (self.width() - w) / 2.0 + self._pan_offset.x(),
            (self.height() - h) / 2.0 + self._pan_offset.y(),
            w,
            h,
        )

    def _scale(self) -> float:
        if self._pixmap is None or self._pixmap.width() <= 0:
            return 1.0
        return self._zoom

    def _widget_to_image(self, point: QPointF) -> QPointF:
        rect = self._image_rect()
        if self._pixmap is None or self._pixmap.isNull() or rect.isNull():
            return QPointF(point)
        return QPointF(
            (point.x() - rect.left()) / rect.width() * self._pixmap.width(),
            (point.y() - rect.top()) / rect.height() * self._pixmap.height(),
        )

    def _image_to_widget(self, point: QPointF) -> QPointF:
        rect = self._image_rect()
        if self._pixmap is None or self._pixmap.isNull() or rect.isNull():
            return QPointF(point)
        return QPointF(
            rect.left() + point.x() / self._pixmap.width() * rect.width(),
            rect.top() + point.y() / self._pixmap.height() * rect.height(),
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))

        image_rect = self._image_rect()
        if self._pixmap is not None and not self._pixmap.isNull() and not image_rect.isNull():
            painter.drawPixmap(image_rect.toRect(), self._pixmap)
        else:
            painter.setPen(QColor("#555555"))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        if self._show_crosshair:
            self._draw_crosshair(painter, image_rect)

        for index, roi in enumerate(self.rois):
            self._draw_roi(painter, roi, selected=(index == self.selected_index))

    def _draw_crosshair(self, painter: QPainter, image_rect: QRectF) -> None:
        if image_rect.isNull():
            center = self.rect().center()
            left = 0.0
            right = float(self.width())
            top = 0.0
            bottom = float(self.height())
        else:
            center = image_rect.center()
            left = image_rect.left()
            right = image_rect.right()
            top = image_rect.top()
            bottom = image_rect.bottom()

        pen = QPen(QColor("#ff0000"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(int(center.x()), int(top), int(center.x()), int(bottom))
        painter.drawLine(int(left), int(center.y()), int(right), int(center.y()))

    def _draw_roi(self, painter: QPainter, roi: dict, selected: bool) -> None:
        color = QColor(self.selected_color if selected else self.unselected_color)
        pen = QPen(color)
        pen.setWidth(3 if selected else 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if roi["shape"] == "circle":
            center = self._image_to_widget(QPointF(roi["cx"], roi["cy"]))
            radius = roi["radius"] * self._scale()
            painter.drawEllipse(center, radius, radius)
            painter.drawText(center + QPointF(radius + 3.0, 0.0), roi.get("name", ""))
            self._draw_center_handle(painter, center)
            return

        center = self._image_to_widget(QPointF(roi["cx"], roi["cy"]))
        w = roi["w"] * self._scale()
        h = roi["h"] * self._scale()
        painter.save()
        painter.translate(center)
        painter.rotate(roi["angle"])
        painter.drawRect(QRectF(-w / 2.0, -h / 2.0, w, h))
        painter.restore()
        painter.drawText(center + QPointF(-w / 2.0, -h / 2.0 - 6.0), roi.get("name", ""))
        self._draw_center_handle(painter, center)

    def _draw_center_handle(self, painter: QPainter, center: QPointF) -> None:
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, 3.5, 3.5)

    def _contains(self, roi: dict, image_point: QPointF) -> bool:
        if roi["shape"] == "circle":
            distance = sqrt((image_point.x() - roi["cx"]) ** 2 + (image_point.y() - roi["cy"]) ** 2)
            return distance <= roi["radius"]

        dx = image_point.x() - roi["cx"]
        dy = image_point.y() - roi["cy"]
        angle = radians(-roi["angle"])
        local_x = dx * cos(angle) - dy * sin(angle)
        local_y = dx * sin(angle) + dy * cos(angle)
        return abs(local_x) <= roi["w"] / 2.0 and abs(local_y) <= roi["h"] / 2.0

    def _near_center(self, roi: dict, widget_point: QPointF) -> bool:
        center = self._image_to_widget(QPointF(roi["cx"], roi["cy"]))
        distance = sqrt((widget_point.x() - center.x()) ** 2 + (widget_point.y() - center.y()) ** 2)
        return distance <= self.CENTER_HIT_RADIUS

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        widget_point = event.position()
        image_point = self._widget_to_image(widget_point)

        for index in range(len(self.rois) - 1, -1, -1):
            if self._near_center(self.rois[index], widget_point):
                self.selected_index = index
                self._dragging = True
                self.update()
                self.selection_changed.emit(index)
                return

        for index in range(len(self.rois) - 1, -1, -1):
            if self._contains(self.rois[index], image_point):
                self.selected_index = index
                self._dragging = False
                self.update()
                self.selection_changed.emit(index)
                return

        self.selected_index = -1
        self._dragging = False
        self.update()
        self.selection_changed.emit(-1)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._last_pan_pos
            self._pan_offset += delta
            self._last_pan_pos = event.position()
            self.update()
            return

        if self._dragging and 0 <= self.selected_index < len(self.rois):
            image_point = self._widget_to_image(event.position())
            roi = self.rois[self.selected_index]
            roi["cx"] = image_point.x()
            roi["cy"] = image_point.y()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self.unsetCursor()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom = max(0.1, min(10.0, self._zoom * factor))
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        image_point = self._widget_to_image(event.position())
        self.add_requested.emit(image_point.x(), image_point.y())
