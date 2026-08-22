from __future__ import annotations


class PointCloudDeviceDriver:
    """点云设备统一驱动接口。

    所有 3D 相机 / 文件设备驱动都应继承此类并实现具体逻辑，
    页面层只依赖该接口，便于后续替换为 TOF / 结构光 / 激光轮廓仪等真实 SDK。
    """

    def enumerate_devices(self) -> list[dict]:
        """枚举可用设备，返回列表，每项至少包含 id 与 name。"""
        raise NotImplementedError

    def open(self, device_id: str) -> bool:
        """打开指定设备，成功返回 True。"""
        raise NotImplementedError

    def close(self) -> None:
        """关闭当前设备。"""
        raise NotImplementedError

    def is_opened(self) -> bool:
        """返回设备是否已打开。"""
        raise NotImplementedError

    def capture(self):
        """采集一帧点云，返回 open3d.geometry.PointCloud。"""
        raise NotImplementedError

    def set_parameter(self, key: str, value) -> None:
        """设置设备采集参数（如曝光、增益、采集模式等）。"""
        raise NotImplementedError
