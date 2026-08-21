# SOP 项目结构与扩展说明

本文档用于说明当前项目的目录结构、主要接口，以及相机驱动、算法、配置等模块的建议扩展位置。

## 1. 当前目录结构

```text
SOP/
├─ main.py
├─ requirements.txt
├─ README.md
├─ PROJECT_ARCHITECTURE.md
├─ config/
│  ├─ README.md
│  ├─ camera.yaml
│  ├─ hardware.yaml
│  ├─ system.yaml
│  ├─ mes.yaml
│  ├─ result_query.yaml
│  └─ log.yaml
├─ flow/
│  ├─ README.md
│  └─ <模板名>/
│     └─ template.yaml
├─ ui/
│  └─ *.ui
├─ oriui/
│  └─ *.ui
├─ drivers/
│  ├─ camera/
│  ├─ io/
│  └─ mes/
├─ algorithms/
└─ app/
   ├─ main_window.py
   ├─ status_bar.py
   ├─ help_dialog.py
   ├─ standalone.py
   ├─ theme.py
   ├─ pages/
   ├─ widgets/
   └─ services/
```

## 2. 目录职责

| 目录 | 职责 |
| --- | --- |
| `app/pages` | 各功能页面，继承 `BasePage` |
| `app/widgets` | 可复用 UI 组件：统计卡片、相机视图、ROI 画布、ROI 编辑弹窗 |
| `app/services` | 页面级服务：配置读写、看板模拟数据 |
| `drivers` | 硬件/外部系统驱动：相机、IO、MES |
| `algorithms` | 检测算法、图像处理算法 |
| `config` | 页面参数 YAML 配置 |
| `flow` | 流程模板配置，以模板名作为顶级目录 |
| `ui` / `oriui` | Qt Designer 基础 UI 文件和暗黑预览 UI 文件 |

## 3. 页面注册方式

新增页面：

1. 在 `app/pages/` 下新建页面类，继承 `BasePage`。
2. 在 `app/pages/__init__.py` 中导出。
3. 在 `app/main_window.py` 的 `NAV_ITEMS` 中注册。

```python
NAV_ITEMS = [
    ("相机管理", CameraPage),
    ("运行看板", RunDashboardPage),
]
```

## 4. 主要页面接口

### BasePage

所有页面继承：

```python
class BasePage(QWidget):
    def set_result(self, text: str) -> None: ...
    def set_tip(self, text: str) -> None: ...
    def auto_save_config(self) -> None: ...
    def closeEvent(self, event) -> None: ...
```

页面关闭时，会调用 `auto_save_config()` 保存配置。

### ConfigService

文件：`app/services/config_service.py`

```python
class ConfigService:
    def save_page_config(page_name: str, data: dict) -> Path: ...
    def load_page_config(page_name: str) -> dict: ...
    def save_template(template_name: str, data: dict) -> Path: ...
    def load_template(template_name: str) -> dict: ...
```

### DashboardService

文件：`app/services/dashboard_service.py`

用于运行看板的模拟数据，后续可替换为数据库或 MES 统计接口。

## 5. 运行看板信号

`RunDashboardPage` 提供：

```python
dashboard_full_status_changed = pyqtSignal(dict)
template_changed = pyqtSignal(str)
```

`MainWindow` 接收这些信号并更新底部状态栏。

## 6. 相机驱动扩展位置

推荐目录：

```text
drivers/camera/
```

建议接口：

```python
class CameraDriver:
    def enumerate_devices(self) -> list[dict]: ...
    def open(self, device_id: str) -> bool: ...
    def close(self) -> None: ...
    def start_preview(self) -> None: ...
    def stop_preview(self) -> None: ...
    def capture(self) -> object: ...
    def get_frame(self) -> object: ...
```

页面接入位置：

- `app/pages/camera_page.py`
- 搜索 `插入点` 注释
- 将 `_enumerate_cameras()`、`_toggle_camera()` 中的 demo 逻辑替换为真实驱动调用

## 7. IO 驱动扩展位置

推荐目录：

```text
drivers/io/
```

建议接口：

```python
class IODriver:
    def connect(self, ip: str, port: int) -> bool: ...
    def disconnect(self) -> None: ...
    def read_inputs(self, count: int) -> list[bool]: ...
    def write_coil(self, index: int, value: bool) -> None: ...
```

页面接入位置：

- `app/pages/hardware_config_page.py`
- 搜索 `插入点`
- 替换 `_toggle_modbus()`、`_toggle_output()` 中的模拟逻辑

## 8. MES 驱动扩展位置

推荐目录：

```text
drivers/mes/
```

建议接口：

```python
class MesDriver:
    def configure(self, url: str, api_key: str) -> None: ...
    def test_connection(self) -> bool: ...
    def send(self, message_type: str, payload: dict) -> bool: ...
```

页面接入位置：

- `app/pages/mes_page.py`
- 搜索 `插入点`

## 9. 算法扩展位置

推荐目录：

```text
algorithms/
```

建议接口：

```python
class DetectionAlgorithm:
    def load_model(self, model_path: str) -> None: ...
    def detect(self, image, rois: list[dict], params: dict) -> list[dict]: ...
```

接入位置：

- `app/pages/flow_page.py` 中的“单次执行”
- 后续正式运行看板检测流程

## 10. 配置与流程数据

- 页面参数：`config/<页面名>.yaml`
- 流程模板：`flow/<模板名>/template.yaml`
- 模板内包含：模型路径、标签、ROI、流程步骤和逐步骤检测参数

## 11. UI 文件

- `ui/`：Qt Designer 基础 UI 文件
- `oriui/`：带暗黑样式预览的 UI 文件

当前程序仍以 Python 手写 UI 为主，`.ui` 文件用于设计参考和后续二次编辑。
