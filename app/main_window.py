from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .help_dialog import HelpDialog
from .checkdog.license_manager import LicenseManager
from .pages import (
    CameraPage,
    FlowPage,
    HardwareConfigPage,
    LogPage,
    MesPage,
    ParametersPage,
    PersonnelPage,
    ResultQueryPage,
    RunDashboardPage,
)
from .status_bar import StatusBar


NAV_ITEMS = [
    ("相机管理", CameraPage),
    ("运行看板", RunDashboardPage),
    ("模板编辑", FlowPage),
    ("硬件配置", HardwareConfigPage),
    ("结果查询", ResultQueryPage),
    ("MES对接", MesPage),
    ("日志", LogPage),
    ("参数", ParametersPage),
    ("人员管理", PersonnelPage),
]

# 新增页面时：在 app/pages 下创建页面类，并在此列表中注册即可。


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("单检测工位框架")
        self.resize(1440, 860)
        self.setMinimumSize(1100, 700)

        self.status_bar = StatusBar()
        self.license_manager = LicenseManager()
        for key in ("dashboard_runtime", "dashboard_shift", "dashboard_cycle", "dashboard_device"):
            self.status_bar.add_item(key, "", side="right")
        self.stack = QStackedWidget()
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.help_dialog: HelpDialog | None = None
        self.global_tip_label: QLabel | None = None

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_pages()
        nav_bar = self._build_nav_bar()

        root.addWidget(nav_bar)
        root.addWidget(self.stack, 1)
        root.addWidget(self.status_bar)

        self.setCentralWidget(central)
        self._set_active_page(0)
        self._setup_license()

    def _build_pages(self) -> None:
        self.pages: list[QWidget] = []
        self.camera_page: CameraPage | None = None
        self.dashboard_page: RunDashboardPage | None = None
        self.flow_page: FlowPage | None = None
        for _, page_class in NAV_ITEMS:
            page = page_class()
            self.pages.append(page)
            self.stack.addWidget(page)
            # 将各页面顶部提示同步到主窗口导航栏右侧，减少页面内占用。
            page.tip_changed.connect(self._on_page_tip_changed)
            if isinstance(page, CameraPage):
                self.camera_page = page
                page.camera_metrics_changed.connect(self._on_camera_metrics_changed)
            if isinstance(page, RunDashboardPage):
                self.dashboard_page = page
                page.dashboard_full_status_changed.connect(self._on_dashboard_full_status_changed)
                page.template_changed.connect(self._on_dashboard_template_changed)
                page.publish_full_status()
                self._on_dashboard_template_changed(page.current_template_name)
            if isinstance(page, FlowPage):
                self.flow_page = page

        if self.camera_page is not None and self.dashboard_page is not None:
            self.camera_page.image_changed.connect(self.dashboard_page.set_image)
        if self.camera_page is not None and self.flow_page is not None:
            self.camera_page.image_changed.connect(self.flow_page.set_roi_image)

    def _build_nav_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("navBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(2)

        app_title = QLabel("WS")
        app_title.setObjectName("navAppTitle")
        layout.addWidget(app_title)
        layout.addSpacing(12)

        for index, (label, _) in enumerate(NAV_ITEMS):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setMinimumHeight(34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.button_group.addButton(button, index)
            layout.addWidget(button)

        # 插入点：需要全局快捷操作/菜单时，可在这里继续添加工具栏按钮或 QMenu。

        layout.addStretch(1)

        self.global_tip_label = QLabel("操作提示：--")
        self.global_tip_label.setObjectName("navTip")
        self.global_tip_label.setWordWrap(False)
        layout.addWidget(self.global_tip_label)

        self.help_button = QPushButton("帮助")
        self.help_button.setObjectName("helpButton")
        self.help_button.clicked.connect(self._show_help)
        layout.addWidget(self.help_button)

        self.button_group.buttonClicked.connect(self._on_nav_clicked)
        return bar

    def _on_nav_clicked(self, button: QPushButton) -> None:
        index = self.button_group.id(button)
        if index >= 0:
            self._set_active_page(index)

    def _set_active_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        buttons = self.button_group.buttons()
        if 0 <= index < len(buttons):
            buttons[index].setChecked(True)

        page_title = NAV_ITEMS[index][0]
        self.status_bar.set_status("page", f"界面: {page_title}")
        if self.global_tip_label is not None:
            self.global_tip_label.setText(self.pages[index].current_tip())
        # 插入点：页面切换时可在此广播事件，例如暂停其他页面的定时刷新。

    def _on_page_tip_changed(self, tip: str) -> None:
        if self.global_tip_label is not None:
            self.global_tip_label.setText(tip)

    def _on_dashboard_full_status_changed(self, data: dict) -> None:
        self.status_bar.set_status(
            "dashboard_runtime",
            f"运行时长：{data.get('runtime', '')}" if data.get("runtime") else "",
        )
        self.status_bar.set_status(
            "dashboard_shift",
            f"当班产量：{data.get('shift_output', '')}" if data.get("shift_output") else "",
        )
        self.status_bar.set_status(
            "dashboard_cycle",
            f"平均节拍：{data.get('average_cycle', '')}" if data.get("average_cycle") else "",
        )
        self.status_bar.set_status(
            "dashboard_device",
            f"设备状态：{data.get('device_state', '')}" if data.get("device_state") else "",
        )

    def _on_dashboard_template_changed(self, template_name: str) -> None:
        self.status_bar.set_status("template", f"模板: {template_name}")

    def _on_camera_metrics_changed(self, data: dict) -> None:
        fps = data.get("fps", "--")
        image_size = data.get("image_size", "--")
        self.status_bar.set_status("fps", f"FPS: {fps}")
        self.status_bar.set_status("image_size", f"图像: {image_size}")

    def _show_help(self) -> None:
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self)
            self.help_dialog.license_activated.connect(self._on_license_activated)
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        # 关闭主窗口前，依次保存所有页面的当前配置。
        for page in self.pages:
            page.auto_save_config()
        super().closeEvent(event)

    def _setup_license(self) -> None:
        self.license_grace_timer = QTimer(self)
        self.license_grace_timer.setInterval(30 * 60 * 1000)
        self.license_grace_timer.timeout.connect(self._block_expired_license)
        if self.license_manager.is_expired():
            self.license_grace_timer.start()
            self.status_bar.set_status("ready", "授权已到期", kind="warn")

    def _block_expired_license(self) -> None:
        self.stack.setEnabled(False)
        self.license_grace_timer.stop()
        QMessageBox.warning(
            self,
            "授权已到期",
            "软件授权已到期，当前操作已锁定。\n请打开“帮助 -> 软件激活”输入新密钥。",
        )

    def _on_license_activated(self, expiry_date: str) -> None:
        self.stack.setEnabled(True)
        self.license_grace_timer.stop()
        self.status_bar.set_status("ready", f"授权到期：{expiry_date}", kind="ok")
