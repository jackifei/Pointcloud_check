from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService


class MesPage(BasePage):
    """MES 对接页。

    左侧勾选需要上报的报文类型，右侧可编辑/预留自定义报文模板。
    """

    DEFAULT_MESSAGES = [
        "设备状态",
        "检测结果",
        "报警信息",
        "统计信息",
        "操作日志",
        "自定义报文",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "MES对接",
            "选择需要发送给 MES 的报文内容，并预留自定义报文模板。",
            parent,
        )
        self.config_service = ConfigService()
        self._build_ui()
        self.set_result("检测结果：MES 未发送测试")
        self.set_tip("操作提示：勾选需要上报的报文，并配置自定义模板。")

    def _build_ui(self) -> None:
        connection_group = QGroupBox("MES 服务配置")
        form = QFormLayout(connection_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.url_edit = QLineEdit("http://mes.example.com/api/report")
        self.api_key_edit = QLineEdit("demo-api-key")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("上报地址", self.url_edit)
        form.addRow("API Key", self.api_key_edit)

        connection_buttons = QHBoxLayout()
        connection_buttons.addStretch(1)
        test_connection_button = QPushButton("测试连接")
        connection_buttons.addWidget(test_connection_button)
        button_container = QWidget()
        button_container.setLayout(connection_buttons)
        form.addRow("", button_container)

        self.add_to_content(connection_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        splitter.addWidget(self._build_message_selection())
        splitter.addWidget(self._build_custom_area())
        splitter.setSizes([420, 700])
        self.add_to_content(splitter, stretch=1)

        test_connection_button.clicked.connect(self._test_connection)

    def _build_message_selection(self) -> QGroupBox:
        group = QGroupBox("选择上报报文")
        layout = QVBoxLayout(group)

        hint = QLabel("勾选后，对应报文会在实际 MES 模块中排队发送。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.message_list = QListWidget()
        for text in self.DEFAULT_MESSAGES:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if text in {"设备状态", "检测结果", "报警信息"} else Qt.CheckState.Unchecked)
            self.message_list.addItem(item)
        layout.addWidget(self.message_list, 1)
        return group

    def _build_custom_area(self) -> QGroupBox:
        group = QGroupBox("自定义报文模板")
        layout = QVBoxLayout(group)

        self.template_edit = QPlainTextEdit()
        self.template_edit.setPlaceholderText(
            '示例：\n'
            '{\n'
            '  "device_id": "SOP-001",\n'
            '  "product": "默认产品A",\n'
            '  "result": "OK"\n'
            '}'
        )
        layout.addWidget(self.template_edit, 1)

        buttons = QHBoxLayout()
        save_button = QPushButton("保存配置")
        send_test_button = QPushButton("发送测试报文")
        reset_button = QPushButton("重置模板")
        buttons.addWidget(save_button)
        buttons.addWidget(send_test_button)
        buttons.addWidget(reset_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status_edit = QPlainTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMaximumHeight(130)
        layout.addWidget(self.status_edit)

        save_button.clicked.connect(self._save_config)
        send_test_button.clicked.connect(self._send_test)
        reset_button.clicked.connect(self._reset_template)
        return group

    def _selected_messages(self) -> list[str]:
        selected = []
        for index in range(self.message_list.count()):
            item = self.message_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _save_config(self) -> None:
        selected = self._selected_messages()
        self.config_service.save_page_config(
            "mes",
            {
                "url": self.url_edit.text(),
                "api_key": self.api_key_edit.text(),
                "selected_messages": selected,
                "custom_template": self.template_edit.toPlainText(),
            },
        )
        self._append_status(f"配置已保存到 config/mes.yaml。已勾选：{', '.join(selected) or '无'}")

    def _send_test(self) -> None:
        # 插入点：在此处调用实际 MES HTTP/WebSocket 客户端发送模板内容。
        self._append_status("测试报文已准备，等待真实 MES 客户端接入后发送。")

    def _reset_template(self) -> None:
        self.template_edit.clear()
        self._append_status("自定义报文模板已清空。")

    def _test_connection(self) -> None:
        self._append_status(f"测试连接：{self.url_edit.text()}（demo 模拟成功）")

    def _append_status(self, text: str) -> None:
        self.status_edit.appendPlainText(text)

    def auto_save_config(self) -> None:
        self._save_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].MesPage))
