from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..services.dashboard_service import DashboardService, DashboardSnapshot
from ..widgets import CameraViewWidget, StatCard

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
else:
    from .base_page import BasePage


class RunDashboardPage(BasePage):
    """运行看板页面。

    显示相机图像与 ROI，顶部展示 OK/NG、日/周/月统计和 OK 完成率。
    """

    dashboard_full_status_changed = pyqtSignal(dict)
    template_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "运行看板",
            "实时查看当前模板、相机画面和生产统计。",
            parent,
        )
        self.service = DashboardService()
        self.current_template_name = "默认产品A"
        self._build_ui()
        self._load_dashboard(self.current_template_name)

    def _build_ui(self) -> None:
        self.add_to_content(self._build_dashboard_status_group())
        self.add_to_content(self._build_camera_area(), stretch=1)

    def _build_dashboard_status_group(self) -> QGroupBox:
        group = QGroupBox("看板统计")
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)

        stats_row.addWidget(QLabel("当前模板"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(self.service.TEMPLATES.keys()))
        self.template_combo.setStyleSheet(
            "QComboBox { background-color: #123a56; color: #ffffff; border: 2px solid #4ec9b0; border-radius: 4px; padding: 4px 8px; font-weight: 600; }"
        )
        self.template_combo.setMinimumHeight(54)
        self.template_combo.setMaximumHeight(54)
        stats_row.addWidget(self.template_combo)

        self.ok_card = StatCard("OK", "--", compact=True)
        self.ng_card = StatCard("NG", "--", accent="#f48771", compact=True)
        self.today_card = StatCard("日", "--", compact=True)
        self.week_card = StatCard("周", "--", compact=True)
        self.month_card = StatCard("月", "--", compact=True)
        self.rate_card = StatCard("合格率", "--", accent="#dcdcaa", compact=True)
        for card in (
            self.ok_card,
            self.ng_card,
            self.today_card,
            self.week_card,
            self.month_card,
            self.rate_card,
        ):
            stats_row.addWidget(card, 1)

        self.ok_add_button = QPushButton("模拟OK加1")
        self.ng_add_button = QPushButton("模拟NG加1")
        stats_row.addWidget(self.ok_add_button)
        stats_row.addWidget(self.ng_add_button)
        group.setLayout(stats_row)

        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        self.ok_add_button.clicked.connect(self._simulate_ok)
        self.ng_add_button.clicked.connect(self._simulate_ng)
        return group

    def _build_camera_area(self) -> QGroupBox:
        group = QGroupBox("相机图像显示区")
        layout = QVBoxLayout(group)

        self.camera_view = CameraViewWidget()
        layout.addWidget(self.camera_view, 1)

        self.roi_label = QLabel("ROI：--")
        self.roi_label.setObjectName("pageTip")
        layout.addWidget(self.roi_label)
        return group

    def set_image(self, pixmap) -> None:
        """接收相机管理页广播的图像，用于看板同步显示。"""
        self.camera_view.set_pixmap(pixmap)

    def _build_full_status_area(self) -> QGroupBox:
        self.full_status_group = QGroupBox("完整看板状态")
        self.full_status_group.setVisible(True)
        layout = QHBoxLayout(self.full_status_group)

        self.runtime_label = QLabel("运行时长：--")
        self.shift_output_label = QLabel("当班产量：--")
        self.average_cycle_label = QLabel("平均节拍：--")
        self.device_state_label = QLabel("设备状态：--")
        for label in (
            self.runtime_label,
            self.shift_output_label,
            self.average_cycle_label,
            self.device_state_label,
        ):
            layout.addWidget(label)
        layout.addStretch(1)
        return self.full_status_group

    def _on_template_changed(self, name: str) -> None:
        if not name:
            return
        self._load_dashboard(name)

    def _simulate_ok(self) -> None:
        # 插入点：后续把真实检测结果接入时，用 add_result(True/False) 即可。
        self.service.counter.add_result(True)
        self._apply_snapshot(self.service.snapshot(self.current_template_name))

    def _simulate_ng(self) -> None:
        self.service.counter.add_result(False)
        self._apply_snapshot(self.service.snapshot(self.current_template_name))

    def _load_dashboard(self, template_name: str) -> None:
        self.current_template_name = template_name
        self.template_changed.emit(template_name)
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentText(template_name)
        self.template_combo.blockSignals(False)
        self._apply_snapshot(self.service.snapshot(template_name))

    def _apply_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.ok_card.set_value(str(snapshot.ok))
        self.ng_card.set_value(str(snapshot.ng))
        self.today_card.set_value(str(snapshot.today))
        self.week_card.set_value(str(snapshot.week))
        self.month_card.set_value(str(snapshot.month))
        self.rate_card.set_value(f"{snapshot.ok_rate:.1f}%")

        self.camera_view.set_status_text(
            f"当前模板：{snapshot.template_name}    等待相机画面"
        )
        self.camera_view.set_rois(snapshot.rois)
        roi_text = "、".join(f"ROI-{i + 1}" for i in range(len(snapshot.rois))) or "无"
        self.roi_label.setText(f"ROI：{roi_text}")

        self.set_result(
            f"检测结果：OK {snapshot.ok}，NG {snapshot.ng}，"
            f"合格率 {snapshot.ok_rate:.1f}%"
        )
        self.set_tip(
            "操作提示：切换当前模板可更新看板数据。"
        )
        self._emit_full_status(snapshot)

    def _emit_full_status(self, snapshot: DashboardSnapshot | None = None) -> None:
        if snapshot is None:
            self.dashboard_full_status_changed.emit({})
            return
        self.dashboard_full_status_changed.emit(
            {
                "runtime": snapshot.runtime,
                "shift_output": str(snapshot.shift_output),
                "average_cycle": snapshot.average_cycle,
                "device_state": snapshot.device_state,
            }
        )

    def publish_full_status(self) -> None:
        self._emit_full_status(self.service.snapshot(self.current_template_name))

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].RunDashboardPage))
