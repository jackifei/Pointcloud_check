from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .checkdog.license_manager import LicenseManager


HELP_CONTENT = """
<h2>SOP 软件帮助</h2>
<p>本界面是工业视觉/设备控制软件的 UI 框架 demo。</p>
<ul>
  <li>顶部导航栏用于切换功能页面。</li>
  <li>每个页面上方显示检测结果和操作提示。</li>
  <li>模板编辑页可管理产品模板、ROI Config、Detection Config、Model Config 和 Other Config。</li>
  <li>硬件配置页包含串口开关和 ModbusTCP IO 控制。</li>
  <li>结果查询页可按时间范围和状态筛选历史检测记录。</li>
</ul>
<p>实际相机 SDK、Modbus 驱动、MES 接口和数据库请在各页面标记的“插入点”接入。</p>
"""


class HelpDialog(QDialog):
    """帮助与激活对话框。"""

    license_activated = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("帮助与激活")
        self.resize(760, 540)
        self.license_manager = LicenseManager()

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_help_tab(), "帮助内容")
        self.tabs.addTab(self._build_activation_tab(), "软件激活")
        self._refresh_license_display()

    def _build_help_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词，例如：流程、Modbus、结果查询")
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)

        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        self.help_browser.setHtml(HELP_CONTENT)
        layout.addWidget(self.help_browser, 1)

        self.search_edit.textChanged.connect(self._filter_help)
        return page

    def _build_activation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("请输入授权序列号或授权文件内容："))
        self.machine_label = QLabel(f"当前机器码：{self.license_manager.machine_code()}")
        self.machine_label.setWordWrap(True)
        layout.addWidget(self.machine_label)
        self.activation_edit = QLineEdit()
        self.activation_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        layout.addWidget(self.activation_edit)

        buttons = QHBoxLayout()
        self.activate_button = QPushButton("激活")
        self.clear_button = QPushButton("清空")
        buttons.addWidget(self.activate_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.activation_status = QLabel("激活状态：未激活（demo）")
        self.activation_status.setWordWrap(True)
        layout.addWidget(self.activation_status)

        self.expiry_label = QLabel("到期时间：未激活")
        self.expiry_label.setWordWrap(True)
        layout.addWidget(self.expiry_label)
        layout.addStretch(1)

        self.activate_button.clicked.connect(self._activate)
        self.clear_button.clicked.connect(self.activation_edit.clear)
        return page

    def _filter_help(self, keyword: str) -> None:
        keyword = keyword.strip()
        if keyword:
            # 插入点：可替换为完整帮助文档/知识库检索。
            self.help_browser.setPlainText(
                f"搜索关键词：{keyword}\n\n"
                "当前 demo 提供基础帮助内容。可将此区域接入本地帮助文档或在线知识库。"
            )
        else:
            self.help_browser.setHtml(HELP_CONTENT)

    def _activate(self) -> None:
        code = self.activation_edit.text().strip()
        if not code:
            self.activation_status.setText("激活状态：请输入授权码。")
            self.expiry_label.setText("到期时间：未激活")
            return
        ok, message = self.license_manager.activate(code)
        if ok:
            expiry = self.license_manager.expiry_date()
            expiry_text = expiry.isoformat() if expiry else "未知"
            self.activation_status.setText(f"激活状态：已激活，到期日期：{expiry_text}")
            self.expiry_label.setText(f"到期时间：{expiry_text}")
            self.license_activated.emit(expiry_text)
        else:
            self.activation_status.setText(f"激活状态：{message}")
            self.expiry_label.setText("到期时间：未激活")

    def _refresh_license_display(self) -> None:
        if self.license_manager.is_activated():
            expiry = self.license_manager.expiry_date()
            expiry_text = expiry.isoformat() if expiry else "未知"
            self.activation_status.setText(f"激活状态：已激活，到期日期：{expiry_text}")
            self.expiry_label.setText(f"到期时间：{expiry_text}")
        else:
            self.activation_status.setText("激活状态：未激活")
            self.expiry_label.setText("到期时间：未激活")
