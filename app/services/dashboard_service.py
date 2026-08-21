from __future__ import annotations

from dataclasses import dataclass

from .production_counter_service import ProductionCounterService


@dataclass
class DashboardSnapshot:
    template_name: str
    ok: int
    ng: int
    today: int
    week: int
    month: int
    ok_rate: float
    rois: list[tuple[int, int, int, int]]
    runtime: str
    shift_output: int
    average_cycle: str
    device_state: str


class DashboardService:
    """运行看板数据服务。

    OK/NG、日/周/月统计来自持久化计数服务，模板相关的 ROI 与
    设备展示信息仍使用内置演示数据。
    """

    TEMPLATES = {
        "默认产品A": {
            "rois": [(80, 70, 240, 180), (350, 90, 220, 190)],
            "runtime": "08:26:17",
            "shift_output": 342,
            "average_cycle": "2.38 s",
            "device_state": "运行中",
        },
        "产品B": {
            "rois": [(120, 80, 260, 200), (390, 130, 210, 170)],
            "runtime": "05:42:08",
            "shift_output": 251,
            "average_cycle": "2.71 s",
            "device_state": "运行中",
        },
    }

    def __init__(self) -> None:
        self.counter = ProductionCounterService()

    def snapshot(self, template_name: str) -> DashboardSnapshot:
        data = self.TEMPLATES.get(template_name, self.TEMPLATES["默认产品A"])
        counts = self.counter.snapshot()
        return DashboardSnapshot(
            template_name=template_name,
            ok=counts["ok"],
            ng=counts["ng"],
            today=counts["day"],
            week=counts["week"],
            month=counts["month"],
            ok_rate=counts["ok_rate"],
            rois=data["rois"],
            runtime=data["runtime"],
            shift_output=data["shift_output"],
            average_cycle=data["average_cycle"],
            device_state=data["device_state"],
        )

    def refresh(self, template_name: str) -> DashboardSnapshot:
        return self.snapshot(template_name)
