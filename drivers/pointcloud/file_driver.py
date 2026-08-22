from __future__ import annotations

from pathlib import Path

from .base import PointCloudDeviceDriver
from .io import read_point_cloud


SUPPORTED_SUFFIXES = (".ply", ".pcd", ".xyz", ".xyzrgb", ".pts")


class FilePointCloudDriver(PointCloudDeviceDriver):
    """把 data/pointclouds/ 目录下的点云文件当作“设备”。

    enumerate_devices() 返回该目录（含子目录）中的 .ply/.pcd/.xyz/.pts 文件；
    open(device_id) 按文件路径加载点云；capture() 返回当前点云。
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parents[2] / "data" / "pointclouds"
        self.data_dir = Path(data_dir)
        self._pcd = None
        self._device_id: str | None = None

    def _iter_files(self):
        if not self.data_dir.exists():
            return
        for path in sorted(self.data_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                yield path

    def enumerate_devices(self) -> list[dict]:
        devices: list[dict] = []
        for path in self._iter_files():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            devices.append(
                {
                    "id": str(path),
                    "name": path.name,
                    "path": str(path),
                    "size": size,
                }
            )
        return devices

    def open(self, device_id: str) -> bool:
        self.close()
        path = Path(device_id)
        if not path.exists() or not path.is_file():
            return False
        pcd = read_point_cloud(path)
        if pcd is None or len(pcd.points) == 0:
            return False
        self._pcd = pcd
        self._device_id = str(path)
        return True

    def close(self) -> None:
        self._pcd = None
        self._device_id = None

    def is_opened(self) -> bool:
        return self._pcd is not None and len(self._pcd.points) > 0

    def capture(self):
        if not self.is_opened():
            return None
        return self._pcd

    def set_parameter(self, key: str, value) -> None:
        # 文件设备没有真实采集参数，保留接口以兼容真实 3D 相机驱动。
        return None
