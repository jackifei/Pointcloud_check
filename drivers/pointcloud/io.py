from __future__ import annotations

import os
import shutil
import struct
import tempfile
from pathlib import Path

import numpy as np
import open3d as o3d


def _is_ascii(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def read_point_cloud(path):
    """读取点云文件，返回 open3d.geometry.PointCloud，失败时返回 None。

    open3d 在 Windows 下对非 ASCII（如中文）路径支持不佳，直接读取会抛
    UnicodeDecodeError。此函数会先尝试直接读取，失败时把文件复制到系统
    临时目录下的 ASCII 文件名再读取，从而兼容中文路径。
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None

    try:
        pcd = o3d.io.read_point_cloud(str(path))
    except (UnicodeDecodeError, UnicodeEncodeError):
        pcd = None
    except Exception:
        return None

    if pcd is not None and len(pcd.points) > 0:
        return pcd

    if _is_ascii(path):
        return pcd
    return _read_via_temp_ascii(path, o3d)


def _read_via_temp_ascii(path: Path, o3d):
    fd, tmp_path = tempfile.mkstemp(prefix="pointcloud_", suffix=path.suffix)
    os.close(fd)
    try:
        shutil.copyfile(path, tmp_path)
        return o3d.io.read_point_cloud(tmp_path)
    except Exception:
        return None
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def read_stl_mesh(path):
    """读取 STL 网格模型（二进制或 ASCII 格式），返回 (vertices, faces)。

    vertices: (N, 3) float64 顶点坐标
    faces:    (M, 3) int32 三角形顶点索引

    网格只用于三维显示参考，不参与点云拟合等任何算法计算。
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None

    try:
        data = path.read_bytes()
    except OSError:
        return None

    if len(data) < 84:
        return None

    # 二进制 STL：80 字节文件头 + uint32 三角形数量 + 每三角形 50 字节
    try:
        (triangle_count,) = struct.unpack_from("<I", data, 80)
    except struct.error:
        triangle_count = 0
    expected = 84 + triangle_count * 50
    if triangle_count > 0 and expected <= len(data) <= expected + 4096:
        return _parse_binary_stl(data, triangle_count)

    # 非二进制结构时按 ASCII STL 解析：逐行读取 vertex 关键字
    return _parse_ascii_stl(data)


def _parse_binary_stl(data: bytes, triangle_count: int):
    vertices = []
    faces = []
    offset = 84
    for _ in range(triangle_count):
        # 前 12 字节为面法线，忽略；随后为 3 个顶点坐标
        triangle = struct.unpack_from("<9f", data, offset + 12)
        base = len(vertices)
        vertices.append(triangle[0:3])
        vertices.append(triangle[3:6])
        vertices.append(triangle[6:9])
        faces.append((base, base + 1, base + 2))
        offset += 50
    return (
        np.asarray(vertices, dtype=np.float64),
        np.asarray(faces, dtype=np.int32),
    )


def _parse_ascii_stl(data: bytes):
    text = data.decode("latin-1", errors="replace")
    points = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.lower().startswith("vertex"):
            continue
        parts = line.split()
        if len(parts) < 4:
            return None
        try:
            points.append((float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            return None
    if len(points) == 0 or len(points) % 3 != 0:
        return None
    vertices = np.asarray(points, dtype=np.float64)
    faces = np.arange(len(vertices), dtype=np.int32).reshape(-1, 3)
    return vertices, faces
