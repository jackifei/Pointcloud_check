from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
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


class HardwareConfigPage(BasePage):
    """硬件配置页：串口开关 + ModbusTCP IO 控制 demo。"""

    SERIAL_FIXED_PARAMS = {
        "波特率": "115200",
        "数据位": "8",
        "停止位": "1",
        "校验位": "无",
    }

    MODBUS_IP = "192.168.1.100"
    MODBUS_PORT = 502

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "硬件配置",
            "串口参数在代码中固定；ModbusTCP 控制 16 路输入状态与 16 路输出开关。",
            parent,
        )
        self.input_indicators: list[QLabel] = []
        self.output_buttons: list[QPushButton] = []
        self.serial_opened = False
        self.modbus_connected = False
        self.config_service = ConfigService()
        self._build_ui()
        self._load_config()
        self.set_result("检测结果：硬件未连接")

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        serial_group = self._build_serial_group()
        serial_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(serial_group)

        io_group = self._build_io_group()
        io_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(io_group)
        layout.addStretch(1)

        scroll.setWidget(container)
        self.add_to_content(scroll, stretch=1)

    def _build_serial_group(self) -> QGroupBox:
        group = QGroupBox("串口设置")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("串口"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"])
        layout.addWidget(self.port_combo)

        self.serial_button = QPushButton("打开串口")
        self.serial_button.setCheckable(True)
        layout.addWidget(self.serial_button)

        layout.addWidget(QLabel("波特率"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        layout.addWidget(self.baud_combo)

        layout.addWidget(QLabel("数据位"))
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["8", "7", "6", "5"])
        layout.addWidget(self.data_bits_combo)

        layout.addWidget(QLabel("停止位"))
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        layout.addWidget(self.stop_bits_combo)

        layout.addWidget(QLabel("校验位"))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["无", "奇校验", "偶校验"])
        layout.addWidget(self.parity_combo)

        self.save_config_button = QPushButton("保存硬件配置")
        layout.addWidget(self.save_config_button)
        layout.addStretch(1)

        # 插入点：接入真实串口库时，将固定参数替换为实际串口对象配置。
        self.serial_button.clicked.connect(self._toggle_serial)
        self.save_config_button.clicked.connect(self._save_config)
        return group

    def _build_io_group(self) -> QGroupBox:
        group = QGroupBox("IO 控制（ModbusTCP）")
        layout = QVBoxLayout(group)

        modbus_row = QHBoxLayout()
        modbus_row.addWidget(QLabel("ModbusTCP 地址"))
        self.ip_edit = QLineEdit(self.MODBUS_IP)
        self.ip_edit.setMaximumWidth(180)
        modbus_row.addWidget(self.ip_edit)
        modbus_row.addWidget(QLabel("端口"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.MODBUS_PORT)
        modbus_row.addWidget(self.port_spin)
        self.modbus_button = QPushButton("连接 ModbusTCP")
        self.modbus_button.setCheckable(True)
        modbus_row.addWidget(self.modbus_button)
        modbus_row.addStretch(1)
        layout.addLayout(modbus_row)

        io_columns = QHBoxLayout()
        input_group = self._build_input_group()
        output_group = self._build_output_group()
        input_group.setMaximumWidth(780)
        output_group.setMaximumWidth(780)
        input_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        output_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        io_columns.addWidget(input_group)
        io_columns.addWidget(output_group)
        io_columns.addStretch(1)
        io_columns.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addLayout(io_columns)

        self.modbus_button.clicked.connect(self._toggle_modbus)
        self._set_output_buttons_enabled(False)
        return group

    def _build_input_group(self) -> QGroupBox:
        group = QGroupBox("输入状态（16 路）")
        grid = QGridLayout(group)
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)
        for index in range(16):
            indicator = QLabel("●")
            indicator.setObjectName("ioIndicator")
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            indicator.setFixedSize(28, 28)
            indicator.setProperty("state", "off")
            self._apply_indicator_state(indicator, False)
            name = QLabel(f"IN{index + 1:02d}")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row = index // 8
            group_index = index % 8
            grid.addWidget(indicator, row, group_index * 2)
            grid.addWidget(name, row, group_index * 2 + 1)
            self.input_indicators.append(indicator)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("输出控制（16 路）")
        grid = QGridLayout(group)
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)
        for index in range(16):
            button = QPushButton(f"OUT{index + 1:02d}")
            button.setCheckable(True)
            button.setMinimumHeight(36)
            row = index // 8
            column = index % 8
            grid.addWidget(button, row, column)
            button.clicked.connect(lambda checked, i=index: self._toggle_output(i, checked))
            self.output_buttons.append(button)
        return group

    def _toggle_serial(self, checked: bool) -> None:
        self.serial_opened = checked
        self.serial_button.setText("关闭串口" if checked else "打开串口")
        self.set_result(
            f"检测结果：串口 {self.port_combo.currentText()} "
            f"{'已打开' if checked else '已关闭'}"
        )

    def _toggle_modbus(self, checked: bool) -> None:
        self.modbus_connected = checked
        self.modbus_button.setText("断开 ModbusTCP" if checked else "连接 ModbusTCP")
        self.set_result(
            "检测结果：ModbusTCP "
            f"{self.ip_edit.text()}:{self.port_spin.value()} "
            f"{'已连接' if checked else '未连接'}"
        )
        self._set_output_buttons_enabled(checked)

    def _set_output_buttons_enabled(self, enabled: bool) -> None:
        for button in self.output_buttons:
            button.setEnabled(enabled)

    def _toggle_output(self, index: int, checked: bool) -> None:
        # 插入点：在此处写入 ModbusTCP 线圈寄存器，例如写 0x0000+index。
        self.set_tip(f"操作提示：输出 OUT{index + 1:02d} 已{'置位' if checked else '复位'}")

    def _save_config(self) -> None:
        self.config_service.save_page_config(
            "hardware",
            {
                "serial_port": self.port_combo.currentText(),
                "baud_rate": self.baud_combo.currentText(),
                "data_bits": self.data_bits_combo.currentText(),
                "stop_bits": self.stop_bits_combo.currentText(),
                "parity": self.parity_combo.currentText(),
                "modbus_ip": self.ip_edit.text(),
                "modbus_port": self.port_spin.value(),
            },
        )
        self.set_tip("操作提示：硬件配置已保存到 config/hardware.yaml。")

    def _load_config(self) -> None:
        data = self.config_service.load_page_config("hardware")
        if not data:
            return
        self.port_combo.setCurrentText(str(data.get("serial_port", self.port_combo.currentText())))
        self.baud_combo.setCurrentText(str(data.get("baud_rate", self.baud_combo.currentText())))
        self.data_bits_combo.setCurrentText(str(data.get("data_bits", self.data_bits_combo.currentText())))
        self.stop_bits_combo.setCurrentText(str(data.get("stop_bits", self.stop_bits_combo.currentText())))
        self.parity_combo.setCurrentText(str(data.get("parity", self.parity_combo.currentText())))
        self.ip_edit.setText(str(data.get("modbus_ip", self.ip_edit.text())))
        self.port_spin.setValue(int(data.get("modbus_port", self.port_spin.value())))

    def auto_save_config(self) -> None:
        self._save_config()

    @staticmethod
    def _apply_indicator_state(indicator: QLabel, on: bool) -> None:
        color = "#4ec9b0" if on else "#444444"
        indicator.setStyleSheet(
            f"background-color: {color}; border: 1px solid #666666; border-radius: 14px;"
        )


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].HardwareConfigPage))
