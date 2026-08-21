APP_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

QFrame#navBar {
    background-color: #252526;
    border-bottom: 1px solid #3c3c3c;
}

QLabel#navAppTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
    padding: 0 8px;
}

QLabel#navTip {
    color: #9d9d9d;
    padding: 0 8px;
}

QLabel#navTitle {
    color: #9d9d9d;
    font-size: 11px;
    letter-spacing: 1px;
    padding: 8px 4px;
}

QPushButton#navButton {
    text-align: center;
    padding: 6px 16px;
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    background: transparent;
    color: #cccccc;
}

QPushButton#navButton:hover {
    background-color: #2a2d2e;
    color: #ffffff;
}

QPushButton#navButton:checked {
    background-color: #37373d;
    border-bottom: 3px solid #007acc;
    color: #ffffff;
}

QFrame#pageHeader {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

QLabel#pageResult {
    color: #4ec9b0;
    font-weight: 600;
}

QLabel#pageTip {
    color: #9d9d9d;
    font-size: 12px;
}

QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #dcdcdc;
}

QPushButton {
    background-color: #333333;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 6px 12px;
    color: #d4d4d4;
}

QPushButton:hover {
    background-color: #3c3c3c;
    border-color: #6c6c6c;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:checked {
    background-color: #0e639c;
    border-color: #007acc;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #6a6a6a;
    border-color: #3a3a3a;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 4px 6px;
    selection-background-color: #264f78;
}

QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    selection-background-color: #264f78;
}

QTableWidget,
QTableView,
QTreeWidget {
    background-color: #252526;
    alternate-background-color: #2a2a2b;
    border: 1px solid #3c3c3c;
    gridline-color: #3c3c3c;
}

QTableWidget::item,
QTreeWidget::item {
    padding: 4px;
}

QHeaderView::section {
    background-color: #333333;
    color: #d4d4d4;
    border: none;
    border-right: 1px solid #3c3c3c;
    border-bottom: 1px solid #3c3c3c;
    padding: 6px;
    font-weight: 600;
}

QSplitter::handle {
    background-color: #3c3c3c;
}

QSplitter::handle:horizontal {
    width: 5px;
}

QSplitter::handle:vertical {
    height: 5px;
}

QLabel#imageView {
    background-color: #111111;
    border: 1px dashed #4a4a4a;
    border-radius: 4px;
}

QLabel#ioIndicator {
    font-size: 18px;
}

QFrame#statCard {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
}

QLabel#statCardTitle {
    color: #9d9d9d;
    font-size: 12px;
}

QLabel#statCardValue {
    color: #ffffff;
    font-size: 24px;
    font-weight: 700;
}

QWidget#cameraView {
    background-color: #111111;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

QWidget#roiCanvas {
    background-color: #111111;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

QFrame#statusBar {
    background-color: #007acc;
    color: #ffffff;
}

QFrame#statusBar QLabel {
    background: transparent;
    color: #ffffff;
}

QLabel#statusText {
    color: #ffffff;
    padding: 0 6px;
}

QScrollArea {
    border: none;
}
"""
