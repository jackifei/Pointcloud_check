from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

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
