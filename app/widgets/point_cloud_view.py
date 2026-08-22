from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from PyQt6 import sip
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QMatrix4x4, QPainter, QPen, QPixmap, QSurfaceFormat
from PyQt6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLFunctions_2_0,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLVersionFunctionsFactory,
    QOpenGLVersionProfile,
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget


# OpenGL 常量（避免额外依赖，使用标准枚举值）
GL_FLOAT = 0x1406
GL_POINTS = 0x0000
GL_LINES = 0x0001
GL_TRIANGLES = 0x0004
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303


_POINT_VERT = """
#version 120
attribute vec3 aPos;
attribute vec3 aColor;
uniform mat4 uMVP;
varying vec3 vColor;
void main() {
    gl_Position = uMVP * vec4(aPos, 1.0);
    vColor = aColor;
}
"""

_POINT_FRAG = """
#version 120
varying vec3 vColor;
void main() {
    gl_FragColor = vec4(vColor, 1.0);
}
"""

_PLANE_VERT = """
#version 120
attribute vec3 aPos;
uniform mat4 uMVP;
void main() {
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

_PLANE_FRAG = """
#version 120
uniform vec4 uColor;
void main() {
    gl_FragColor = uColor;
}
"""


def _perspective(fovy_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    return np.array(
        [
            [f / aspect, 0.0, 0.0, 0.0],
            [0.0, f, 0.0, 0.0],
            [0.0, 0.0, (far + near) / (near - far), (2.0 * far * near) / (near - far)],
            [0.0, 0.0, -1.0, 0.0],
        ],
        dtype=np.float64,
    )


def _look_at(eye, center, up) -> np.ndarray:
    eye = np.asarray(eye, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    forward = center - eye
    forward = forward / np.linalg.norm(forward)
    side = np.cross(forward, up)
    side = side / np.linalg.norm(side)
    real_up = np.cross(side, forward)
    return np.array(
        [
            [side[0], side[1], side[2], -np.dot(side, eye)],
            [real_up[0], real_up[1], real_up[2], -np.dot(real_up, eye)],
            [-forward[0], -forward[1], -forward[2], np.dot(forward, eye)],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _jet(t: np.ndarray) -> np.ndarray:
    """把 [0,1] 映射为近似 jet 伪彩色。"""
    t = np.clip(t, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * t - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * t - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * t - 1.0), 0.0, 1.0)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    color = QColor(hex_color)
    return (color.redF(), color.greenF(), color.blueF(), alpha)


def _to_qmatrix(matrix: np.ndarray) -> QMatrix4x4:
    return QMatrix4x4(*matrix.flatten().tolist())


class PointCloudView(QOpenGLWidget):
    """基于 QOpenGLWidget 自绘的三维点云控件。

    能力：
    - 旋转 / 平移 / 缩放
    - 高度伪彩（无颜色时按 Z 轴着色）
    - 划区框选点云
    - 半透明拟合平面显示
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(240, 180)

        # 请求 OpenGL 2.1 兼容上下文，保证 GLSL 120 与基础 VBO 可用。
        fmt = QSurfaceFormat()
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(0)
        self.setFormat(fmt)

        self._points: np.ndarray | None = None
        self._colors: np.ndarray | None = None
        self._selection_mask: np.ndarray | None = None
        self._plane: dict | None = None

        self._gl_ready = False
        self._points_dirty = False
        self._plane_dirty = False

        self._yaw = 0.0
        self._pitch = 0.0
        self._dist = 1.0
        self._pan = np.zeros(3, dtype=np.float64)
        self._bbox_center = np.zeros(3, dtype=np.float64)
        self._bbox_diag = 1.0

        self._selection_enabled = False
        self._selecting = False
        self._rotating = False
        self._panning = False
        self._sel_start = QPointF()
        self._sel_current = QPointF()
        self._last_pos = QPointF()

        self._point_program: QOpenGLShaderProgram | None = None
        self._plane_program: QOpenGLShaderProgram | None = None
        self._point_vbo: QOpenGLBuffer | None = None
        self._plane_vbo: QOpenGLBuffer | None = None
        self._gl = None
        self._point_count = 0
        self._plane_vertex_count = 0
        self._show_axes = True
        self._axis_vbo: QOpenGLBuffer | None = None
        self._axis_dirty = True
        self._axis_vertex_count = 0
        self._axis_length = 1.0
        self._grab_mvp: np.ndarray | None = None
        self._grab_width = 0
        self._grab_height = 0

    # ------------------------------------------------------------------ 公共接口

    def set_point_cloud(self, pcd) -> None:
        if pcd is None:
            self.clear()
            return

        points = np.asarray(pcd.points, dtype=np.float64)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3:
            self.clear()
            return
        points = points[:, :3]

        colors = np.asarray(pcd.colors, dtype=np.float64)
        if (
            colors.ndim == 2
            and colors.shape[0] == points.shape[0]
            and colors.shape[1] >= 3
        ):
            vertex_colors = np.clip(colors[:, :3], 0.0, 1.0).astype(np.float32)
        else:
            z = points[:, 2]
            z_min, z_max = float(z.min()), float(z.max())
            if z_max - z_min < 1e-9:
                vertex_colors = _jet(np.full(z.shape, 0.5))
            else:
                vertex_colors = _jet((z - z_min) / (z_max - z_min))

        self._points = points
        self._colors = vertex_colors
        self._selection_mask = np.zeros(points.shape[0], dtype=bool)
        self._plane = None
        self._points_dirty = True
        self._plane_dirty = True

        lower = points.min(axis=0)
        upper = points.max(axis=0)
        self._bbox_center = (lower + upper) / 2.0
        self._bbox_diag = float(np.linalg.norm(upper - lower)) or 1.0
        self._dist = max(self._bbox_diag * 2.5, 1e-3)
        self._pan = np.zeros(3, dtype=np.float64)
        self._axis_length = max(self._bbox_diag * 0.5, 1e-3)
        self._axis_dirty = True
        self.update()

    def clear(self) -> None:
        self._points = None
        self._colors = None
        self._selection_mask = None
        self._plane = None
        self._points_dirty = True
        self._plane_dirty = True
        self.update()

    def has_cloud(self) -> bool:
        return self._points is not None and len(self._points) > 0

    def selected_points(self) -> np.ndarray:
        if self._points is None or self._selection_mask is None:
            return np.zeros((0, 3), dtype=np.float64)
        return self._points[self._selection_mask]

    def points(self) -> np.ndarray:
        """返回当前点云的三维坐标数组 (N, 3)。"""
        if self._points is None:
            return np.zeros((0, 3), dtype=np.float64)
        return self._points

    def project_points_to_image(self) -> np.ndarray:
        """把当前点云投影到二维图像坐标，返回 (N, 2) 像素坐标。

        该投影优先使用最近一次 grab() 截取画面时的 MVP 与视口尺寸，
        因此可用于在右侧二维 ROI 画布上做多边形框选。
        """
        if self._points is None or len(self._points) == 0:
            return np.zeros((0, 2), dtype=np.float64)
        if self._grab_mvp is not None:
            mvp = self._grab_mvp
            width = self._grab_width if self._grab_width > 0 else self.width()
            height = self._grab_height if self._grab_height > 0 else self.height()
        else:
            mvp = self._current_mvp()
            width = self.width()
            height = self.height()
        homogeneous = np.hstack(
            [self._points, np.ones((len(self._points), 1), dtype=np.float64)]
        )
        clip = homogeneous @ mvp.T
        w = clip[:, 3:4]
        w = np.where(np.abs(w) < 1e-9, 1e-9, w)
        ndc = clip[:, :3] / w
        x = (ndc[:, 0] * 0.5 + 0.5) * width
        y = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * height
        return np.column_stack([x, y])
    def set_selection_enabled(self, enabled: bool) -> None:
        self._selection_enabled = bool(enabled)
        if not self._selection_enabled:
            self._selecting = False
        self.setCursor(
            Qt.CursorShape.CrossCursor if self._selection_enabled else Qt.CursorShape.ArrowCursor
        )

    def clear_selection(self) -> None:
        if self._points is not None:
            self._selection_mask = np.zeros(len(self._points), dtype=bool)
        self._selecting = False
        self.update()

    def set_fitted_plane(self, center, normal, size: float, color: str) -> None:
        center = np.asarray(center, dtype=np.float64).reshape(3)
        normal = np.asarray(normal, dtype=np.float64).reshape(3)
        normal_len = float(np.linalg.norm(normal))
        if normal_len < 1e-9:
            return
        self._plane = {
            "center": center,
            "normal": normal / normal_len,
            "size": float(size),
            "color": color,
        }
        self._plane_dirty = True
        self.update()

    def clear_fitted_plane(self) -> None:
        self._plane = None
        self._plane_dirty = True
        self.update()

    def set_front_view(self) -> None:
        """切换到正视图（沿 Z 轴看 XY 平面）。"""
        self._set_view(0.0, 0.0)

    def set_side_view(self) -> None:
        """切换到侧视图（沿 X 轴看 YZ 平面）。"""
        self._set_view(math.pi / 2.0, 0.0)

    def set_top_view(self) -> None:
        """切换到俯视图（沿 Y 轴向下看 XZ 平面）。"""
        self._set_view(0.0, -math.pi / 2.0)

    def set_axes_visible(self, visible: bool) -> None:
        """显示或隐藏世界坐标系。"""
        self._show_axes = bool(visible)
        self.update()

    def _set_view(self, yaw: float, pitch: float) -> None:
        self._yaw = yaw
        self._pitch = pitch
        self._pan = np.zeros(3, dtype=np.float64)
        self._dist = max(self._bbox_diag * 2.5, 1e-3)
        self.update()

    def grab(self) -> QPixmap:
        """返回当前三维画面的截图，用于 ROI 画布投影。"""
        if self._gl_ready:
            self._grab_mvp = self._current_mvp()
            image = self.grabFramebuffer()
            if image is not None and not image.isNull():
                self._grab_width = image.width()
                self._grab_height = image.height()
                return QPixmap.fromImage(image)
        return super().grab()

    # ------------------------------------------------------------------ OpenGL 生命周期

    def initializeGL(self) -> None:
        context = self.context()

        profile = QOpenGLVersionProfile()
        profile.setVersion(2, 1)
        profile.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        self._gl = QOpenGLVersionFunctionsFactory.get(profile, context)
        if self._gl is None:
            fallback = QOpenGLFunctions_2_0()
            fallback.initializeOpenGLFunctions()
            self._gl = fallback

        self._point_program = self._make_program(_POINT_VERT, _POINT_FRAG, ("aPos", "aColor"))
        self._plane_program = self._make_program(_PLANE_VERT, _PLANE_FRAG, ("aPos",))

        self._point_vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self._point_vbo.create()
        self._plane_vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self._plane_vbo.create()
        self._axis_vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self._axis_vbo.create()

        self._gl.glClearColor(0.086, 0.086, 0.090, 1.0)
        self._gl.glEnable(GL_DEPTH_TEST)
        self._gl.glEnable(GL_BLEND)
        self._gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._gl.glPointSize(2.0)

        self._gl_ready = True
        self._points_dirty = True
        self._plane_dirty = True
        self._log_gl_debug()

    def _make_program(self, vertex_src: str, fragment_src: str, attributes: tuple[str, ...]) -> QOpenGLShaderProgram:
        program = QOpenGLShaderProgram(self)
        program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vertex_src)
        program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragment_src)
        for index, name in enumerate(attributes):
            program.bindAttributeLocation(name, index)
        if not program.link():
            self._write_debug(f"shader link failed: {program.log()}")
        return program

    def resizeGL(self, width: int, height: int) -> None:
        if self._gl is not None:
            self._gl.glViewport(0, 0, max(1, width), max(1, height))

    def paintGL(self) -> None:
        if not self._gl_ready:
            return

        self._gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        mvp = self._current_mvp()

        if self.has_cloud():
            self._upload_points_if_needed()
            self._draw_points(mvp)

        if self._plane is not None:
            self._upload_plane_if_needed()
            self._draw_plane(mvp)

        if self._show_axes:
            self._draw_axes(mvp)

        if self._selecting:
            self._paint_selection_overlay()

    # ------------------------------------------------------------------ 渲染细节

    def _current_mvp(self) -> np.ndarray:
        width = max(1, self.width())
        height = max(1, self.height())
        # near/far 必须跟随相机距离与点云尺寸动态缩放，否则大点云会被裁剪平面裁掉。
        near = max(self._dist * 0.05, self._bbox_diag * 1e-4, 1e-4)
        far = max(self._dist * 100.0, self._bbox_diag * 10.0, 1.0)
        projection = _perspective(45.0, width / height, near, far)
        return projection @ self._view_matrix()

    def _log_gl_debug(self) -> None:
        try:
            version = self._gl.glGetString(0x1F02)  # GL_VERSION
            renderer = self._gl.glGetString(0x1F01)  # GL_RENDERER
            if isinstance(version, bytes):
                version = version.decode("utf-8", errors="replace")
            if isinstance(renderer, bytes):
                renderer = renderer.decode("utf-8", errors="replace")
            log_path = Path(__file__).resolve().parents[2] / "log" / "opengl_debug.txt"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                f"GL_VERSION={version}\nGL_RENDERER={renderer}\n",
                encoding="utf-8",
            )
        except Exception:
            pass

    def _write_debug(self, message: str) -> None:
        try:
            log_path = Path(__file__).resolve().parents[2] / "log" / "opengl_debug.txt"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except Exception:
            pass

    def _rotation(self) -> np.ndarray:
        cy, sy = math.cos(self._yaw), math.sin(self._yaw)
        cp, sp = math.cos(self._pitch), math.sin(self._pitch)
        ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float64)
        rx = np.array([[1.0, 0.0, 0.0], [0.0, cp, -sp], [0.0, sp, cp]], dtype=np.float64)
        return ry @ rx

    def _view_matrix(self) -> np.ndarray:
        rotation = self._rotation()
        target = self._bbox_center + self._pan
        eye = target + rotation @ np.array([0.0, 0.0, self._dist])
        up = rotation @ np.array([0.0, 1.0, 0.0])
        return _look_at(eye, target, up)

    def _upload_points_if_needed(self) -> None:
        if not self._points_dirty:
            return
        self._points_dirty = False
        if self._points is None or self._colors is None or len(self._points) == 0:
            self._point_count = 0
            return
        vertex_data = np.hstack([self._points, self._colors]).astype(np.float32)
        self._upload_vbo(self._point_vbo, vertex_data)
        self._point_count = len(self._points)

    def _draw_points(self, mvp: np.ndarray) -> None:
        if self._point_count == 0 or self._point_program is None or self._point_vbo is None:
            return
        program = self._point_program
        program.bind()
        program.setUniformValue("uMVP", _to_qmatrix(mvp))
        self._point_vbo.bind()
        stride = 6 * 4
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, stride)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 3 * 4, 3, stride)
        self._gl.glDrawArrays(GL_POINTS, 0, self._point_count)
        program.disableAttributeArray(1)
        program.disableAttributeArray(0)
        self._point_vbo.release()
        program.release()

    def _upload_plane_if_needed(self) -> None:
        if not self._plane_dirty:
            return
        self._plane_dirty = False
        if self._plane is None:
            self._plane_vertex_count = 0
            return
        vertex_data = self._plane_vertices().astype(np.float32)
        self._upload_vbo(self._plane_vbo, vertex_data)
        self._plane_vertex_count = vertex_data.shape[0]

    def _upload_vbo(self, vbo: QOpenGLBuffer, data: np.ndarray) -> None:
        """把 float32 数组写入 VBO。

        注意：PyQt6 的 QOpenGLBuffer.allocate() 需要 sip.voidptr 指针，
        不能直接传 bytes，否则数据不会真正上传到 GPU。
        """
        data = np.ascontiguousarray(data, dtype=np.float32)
        ptr = sip.voidptr(data.ctypes.data)
        vbo.bind()
        vbo.allocate(ptr, data.nbytes)
        vbo.release()

    def _plane_vertices(self) -> np.ndarray:
        center = self._plane["center"]
        normal = self._plane["normal"]
        size = self._plane["size"]
        ref = np.array([0.0, 0.0, 1.0]) if abs(normal[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(normal, ref)
        u = u / np.linalg.norm(u)
        v = np.cross(normal, u)
        half = size / 2.0
        c0 = center + u * half + v * half
        c1 = center - u * half + v * half
        c2 = center - u * half - v * half
        c3 = center + u * half - v * half
        return np.array([c0, c1, c2, c0, c2, c3], dtype=np.float64)

    def _draw_plane(self, mvp: np.ndarray) -> None:
        if self._plane_vertex_count == 0 or self._plane_program is None or self._plane_vbo is None:
            return
        program = self._plane_program
        program.bind()
        program.setUniformValue("uMVP", _to_qmatrix(mvp))
        rgba = _hex_to_rgba(self._plane["color"], alpha=0.35)
        program.setUniformValue("uColor", rgba[0], rgba[1], rgba[2], rgba[3])
        self._gl.glDepthMask(False)
        self._plane_vbo.bind()
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, 3 * 4)
        self._gl.glDrawArrays(GL_TRIANGLES, 0, self._plane_vertex_count)
        program.disableAttributeArray(0)
        self._plane_vbo.release()
        self._gl.glDepthMask(True)
        program.release()

    def _upload_axes(self) -> None:
        self._axis_dirty = False
        length = self._axis_length
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [length, 0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, length, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, length, 0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        self._upload_vbo(self._axis_vbo, data)
        self._axis_vertex_count = 6

    def _draw_axes(self, mvp: np.ndarray) -> None:
        if self._axis_vbo is None:
            return
        if self._axis_dirty:
            self._upload_axes()
        if self._axis_vertex_count == 0 or self._point_program is None:
            return

        program = self._point_program
        program.bind()
        program.setUniformValue("uMVP", _to_qmatrix(mvp))
        self._gl.glDisable(GL_DEPTH_TEST)
        self._axis_vbo.bind()
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, 6 * 4)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 3 * 4, 3, 6 * 4)
        self._gl.glLineWidth(2.0)
        self._gl.glDrawArrays(GL_LINES, 0, self._axis_vertex_count)
        program.disableAttributeArray(1)
        program.disableAttributeArray(0)
        self._axis_vbo.release()
        self._gl.glEnable(GL_DEPTH_TEST)
        program.release()

    def _paint_selection_overlay(self) -> None:
        rect = QRectF(self._sel_start, self._sel_current).normalized()
        painter = QPainter(self)
        pen = QPen(QColor("#4ec9b0"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor(78, 201, 176, 40))
        painter.drawRect(rect)
        painter.end()

    # ------------------------------------------------------------------ 交互

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        if self._selection_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            self._sel_start = pos
            self._sel_current = pos
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._rotating = True
            self._last_pos = pos
        elif event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = True
            self._last_pos = pos
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._selecting:
            self._sel_current = pos
            self.update()
        elif self._rotating:
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            self._yaw -= dx * 0.01
            self._pitch -= dy * 0.01
            limit = math.pi / 2.0 - 0.01
            self._pitch = max(-limit, min(limit, self._pitch))
            self._last_pos = pos
            self.update()
        elif self._panning:
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            rotation = self._rotation()
            right = rotation @ np.array([1.0, 0.0, 0.0])
            up = rotation @ np.array([0.0, 1.0, 0.0])
            world_per_pixel = (
                2.0
                * self._dist
                * math.tan(math.radians(45.0) / 2.0)
                / max(1, self.height())
            )
            self._pan -= right * (dx * world_per_pixel)
            self._pan += up * (dy * world_per_pixel)
            self._last_pos = pos
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._selecting and event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
            self._apply_selection()
        if event.button() == Qt.MouseButton.LeftButton:
            self._rotating = False
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 0.9 if delta > 0 else 1.1
        self._dist = max(
            self._bbox_diag * 0.01,
            min(self._bbox_diag * 100.0, self._dist * factor),
        )
        self.update()
        event.accept()

    def _apply_selection(self) -> None:
        if self._points is None or len(self._points) == 0:
            return
        rect = QRectF(self._sel_start, self._sel_current).normalized()
        if rect.width() < 3 or rect.height() < 3:
            return

        mvp = self._current_mvp()
        points = self._points
        homogeneous = np.hstack([points, np.ones((len(points), 1), dtype=np.float64)])
        clip = homogeneous @ mvp.T
        w = clip[:, 3:4]
        w = np.where(np.abs(w) < 1e-9, 1e-9, w)
        ndc = clip[:, :3] / w

        x = (ndc[:, 0] * 0.5 + 0.5) * self.width()
        y = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * self.height()

        self._selection_mask = (
            (w[:, 0] > 0)
            & (ndc[:, 2] >= -1.0)
            & (ndc[:, 2] <= 1.0)
            & (x >= rect.left())
            & (x <= rect.right())
            & (y >= rect.top())
            & (y <= rect.bottom())
        )
        self.update()
