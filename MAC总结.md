# 项目分析与功能总结（MAC总结）

> 本文档基于对当前代码的完整分析编写，用于快速建立项目认知，
> 并作为后续「项目针对性升级」的参考底稿。如与实际代码有出入，以代码为准。

---

## 1. 项目概览

这是一个基于 **Python 3.12 + PyQt6** 的工业视觉检测软件框架（单检测工位），
主窗口标题为 **“单检测工位框架”**，程序内部名称为 `single_check Demo`。

覆盖场景：

- 相机管理（USB 相机已真实接入 OpenCV，GIGE 相机为预留）
- 运行看板（实时 OK/NG、日/周/月产量、合格率、ROI 叠加显示）
- 模板编辑（产品模板、ROI、检测参数、模型配置、其他参数）
- 硬件配置（串口 + ModbusTCP 16 路输入/16 路输出）
- 结果查询（按时间/产品/状态/报警筛选检测记录）
- MES 对接（报文类型勾选 + 自定义报文模板）
- 日志（按天写入文件）、系统参数、人员管理
- 软件授权（机器码绑定 + 密钥激活 + 到期锁定）

**当前阶段定位**：UI 与交互框架已搭建完成；USB 相机采集、配置读写、
生产计数、日志落盘为真实逻辑；GIGE 相机、ModbusTCP、串口、MES、数据库、
检测算法、流程引擎等仍为 demo / “插入点”占位。

---

## 2. 技术栈与运行环境

| 项目 | 内容 |
| --- | --- |
| 语言 | Python 3.12 |
| GUI 框架 | PyQt6 >= 6.6 |
| 配置解析 | PyYAML >= 6.0 |
| 相机采集 | opencv-python >= 4.8 |
| 打包 | PyInstaller（多套 spec） |
| 主要平台 | Windows（代码含 `CAP_DSHOW` 等 Windows 专用参数） |

依赖文件：`requirements.txt`

```text
PyQt6>=6.6.0
PyYAML>=6.0
opencv-python>=4.8
```

运行：

```bash
python main.py
```

单页面独立调试（每个页面文件底部都带有 `__main__` 入口）：

```bash
python app/pages/camera_page.py
python app/pages/run_dashboard_page.py
```

授权码生成工具：

```bash
python license_tool.py
```

---

## 3. 目录结构与职责

```text
single_check/
├─ main.py                          # 程序入口（创建 QApplication + 主窗口）
├─ requirements.txt                 # 依赖
├─ README.md                        # 项目说明（运行/打包/已实现功能）
├─ PROJECT_ARCHITECTURE.md          # 架构说明与扩展位置
├─ MAC总结.md                       # 本文档
├─ 总结文档.md                       # 历史总结文档（内容较早，部分已过时）
├─ 打包注释.md                       # PyInstaller 参数说明
├─ main.spec / SOP.spec / SOP_APP.spec  # PyInstaller 打包配置
├─ MyAppLog.ico                     # 应用图标
├─ license_tool.py                  # 授权码生成工具（GUI）
├─ license_data.json                # 授权数据（当前为已激活示例）
├─ config/                          # 页面参数 YAML 配置（6 个 yaml）
├─ flow/                            # 流程模板（按模板名分目录）
│  ├─ README.md
│  ├─ 默认产品A/ 产品B/ 123/ 333/ 3333/ 999/
├─ log/                             # 按天运行日志 log/YYYYMMDD.txt（CSV 格式）
├─ checknum/                        # 生产计数状态与清零历史
├─ algorithms/                      # 检测算法（仅占位，无实现）
├─ drivers/                         # 硬件/外部系统驱动
│  ├─ camera/                       # USB 相机驱动（OpenCV，已实现）
│  ├─ io/                           # Modbus/IO 驱动（仅 README）
│  └─ mes/                          # MES 驱动（仅 README）
├─ app/                             # 应用主体
│  ├─ main_window.py                # 主窗口、导航、页面注册、信号联动
│  ├─ status_bar.py                 # 底部 VSCode 风格状态栏
│  ├─ help_dialog.py                # 帮助 + 软件激活对话框
│  ├─ standalone.py                 # 单页面独立运行工具
│  ├─ theme.py                      # 全局暗黑主题 QSS
│  ├─ checkdog/                     # 授权模块（独立于业务代码）
│  ├─ pages/                        # 9 个功能页面
│  ├─ widgets/                      # 可复用 UI 组件
│  └─ services/                     # 配置/看板/日志/计数服务
├─ ui/                              # Qt Designer 基础 .ui 文件
└─ oriui/                           # 贴近暗黑效果的 .ui 文件
```

### 目录职责速查

| 目录 | 职责 |
| --- | --- |
| `app/pages` | 各功能页面，统一继承 `BasePage` |
| `app/widgets` | 相机图像、ROI 画布、ROI 编辑弹窗、统计卡片 |
| `app/services` | 配置读写、看板模拟数据、日志文件、生产计数 |
| `app/checkdog` | 软件授权、机器绑定、到期控制（独立模块） |
| `drivers` | 相机、IO、MES 硬件/外部系统驱动 |
| `algorithms` | 检测算法（预留扩展位） |
| `config` | 页面参数 YAML（`config/<页面名>.yaml`） |
| `flow` | 产品模板（`flow/<模板名>/template.yaml` + 4 个子目录） |
| `log` | 按天日志，CSV 逗号分隔 |
| `checknum` | 计数状态 JSON + 清零历史 TXT |
| `ui` / `oriui` | Qt Designer 设计参考文件 |

---

## 4. 启动流程

1. `main.py` 创建 `QApplication`，设置应用名 `single_check Demo`、组织名 `single_check`。
2. 应用全局暗黑主题 `APP_STYLESHEET`（来自 `app/theme.py`）。
3. 创建并显示 `MainWindow`（标题“单检测工位框架”，默认 1440x860）。
4. `MainWindow` 初始化：底部状态栏、授权管理器 `LicenseManager`、页面栈 `QStackedWidget`、顶部导航栏。
5. 默认激活第一个页面（相机管理）。
6. 授权检查：已到期则启动 30 分钟宽限定时器，到期锁定页面栈并要求重新激活。

---

## 5. 主窗口（app/main_window.py）

### 5.1 顶部导航

- 左侧“WS”应用标题。
- 9 个互斥导航按钮（`QButtonGroup`），对应 9 个页面。
- 右侧全局操作提示标签 + “帮助”按钮。
- 页面 `tip_changed` 信号同步到导航栏右侧的全局提示（节省页面空间）。

### 5.2 页面注册表 `NAV_ITEMS`

```python
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
```

**新增页面方法**：在 `app/pages/` 创建类继承 `BasePage` → 在 `app/pages/__init__.py` 导出 → 在 `NAV_ITEMS` 注册。

### 5.3 底部状态栏（app/status_bar.py）

- 左侧：`ready`、`fps`、`image_size`、`hardware`、`camera`、`page`。
- 右侧：`user`、`template`、`clock`，以及主窗口动态注册的 `dashboard_runtime`、
  `dashboard_shift`、`dashboard_cycle`、`dashboard_device`。
- 状态颜色：`info` / `ok` / `warn` / `error`。
- 更新接口：`status_bar.set_status(key, text, kind)`。

### 5.4 跨页面信号联动

| 信号 | 作用 |
| --- | --- |
| `CameraPage.camera_metrics_changed` | 更新状态栏 FPS、图像尺寸 |
| `CameraPage.image_changed` | 广播图像给运行看板、模板编辑 ROI 画布 |
| `RunDashboardPage.dashboard_full_status_changed` | 更新状态栏运行时长/当班产量/节拍/设备状态 |
| `RunDashboardPage.template_changed` | 更新状态栏当前模板 |
| 页面 `tip_changed` | 更新导航栏右侧全局提示 |

### 5.5 授权锁定

- 到期后启动 30 分钟定时器，超时禁用页面栈并弹窗。
- 在“帮助 → 软件激活”输入正确密钥后解锁。

---

## 6. 页面公共基类（app/pages/base_page.py）

所有页面继承 `BasePage`，提供：

- `set_result(text)`：设置“检测结果”文案
- `set_tip(text)`：设置“操作提示”并发出 `tip_changed`
- `current_tip()`：获取当前提示
- `add_to_content(widget, stretch)` / `add_layout_to_content(layout, stretch)`
- `auto_save_config()`：关闭前自动保存配置（各页面覆盖）
- `closeEvent()`：关闭时调用 `auto_save_config()`

---

## 7. 九个功能页面详解

### 7.1 相机管理页（app/pages/camera_page.py）

功能：

- 相机类型：USB 相机 / GIGE 相机
- 驱动选择：DirectShow / Basler Pylon / HIKVISION SDK / GigE Vision
- 枚举相机、打开/关闭、开始/停止预览、拍照
- 打开本地图像
- 相机参数：曝光、增益、帧率、触发模式、像素格式
- 十字线居中
- 配置保存到 `config/camera.yaml`

实现状态：

- USB 相机已通过 `drivers/camera/usb_camera.py` 真实接入 OpenCV（枚举/打开/预览/拍照）。
- GIGE 相机为 demo，需在 `_enumerate_cameras()` / `_toggle_camera()` 的“插入点”接真实 SDK。
- 相机参数目前只保存/回显，尚未真正下发到相机。
- 图像通过 `image_changed` 信号同步给运行看板和模板编辑页。

### 7.2 运行看板页（app/pages/run_dashboard_page.py）

功能：

- 顶部统计卡片：当前模板 + OK / NG / 日 / 周 / 月 / 合格率
- “模拟OK加1”“模拟NG加1”按钮（后续替换为真实检测结果上报）
- 相机画面显示区（接收相机管理页广播图像，叠加中心十字线和 ROI 框）
- 切换模板更新看板数据

实现状态：

- OK/NG、日/周/月计数来自 `ProductionCounterService` 持久化计数，启动时按日/班次判断清零。
- 模板 ROI 与设备展示信息（运行时长/当班产量/节拍/设备状态）仍为内置演示数据
  （`DashboardService.TEMPLATES` 只有“默认产品A”“产品B”）。
- 底部状态栏展示运行时长、当班产量、平均节拍、设备状态。

### 7.3 模板编辑页（app/pages/flow_page.py）

功能：

- 左侧模板面板：
  - 顶部“模板名称”下拉框用于切换当前模板
  - “产品模板”列表用于选中后复制/删除
  - 新建 / 复制 / 删除 / 保存当前模板
- 右侧四个配置区：
  - **ROI Config**：`RoiCanvas` 画布，显示相机广播图像，滚轮缩放、右键平移、
    红色十字线开关；弹窗 `RoiEditorDialog` 支持圆形、旋转矩形创建编辑
  - **Detection Config**：置信度、检测数量、备用参数 1~3、启用项 1~5、功能选择 1~5
  - **Model Config**：加载/释放模型文件（仅记录路径）
  - **Other Config**：10 行三列自定义参数表（参数名称/参数值）
- 保存时写入 `flow/<模板名>/template.yaml`，并同步拆分为四个子目录：
  `ROI Config/roi.yaml`、`Detection Config/detection.yaml`、
  `Model Config/model.yaml`、`Other Config/other.yaml`

实现状态：

- 模板增删改查、ROI 编辑、参数持久化均为真实逻辑。
- 模型加载只记录文件路径，未接入推理引擎。
- 旧模板中的 `labels`、`steps`、`use_gesture`、`gesture` 字段当前版本已不使用，加载时忽略。

### 7.4 硬件配置页（app/pages/hardware_config_page.py）

功能：

- 串口设置：选择串口、打开/关闭，波特率/数据位/停止位/校验位横向排列
- ModbusTCP：IP + 端口 + 连接/断开
- IO 控制：16 路输入状态指示灯 + 16 路输出开关按钮（未连接时禁用）
- 配置保存到 `config/hardware.yaml`

实现状态：串口与 ModbusTCP 均为模拟逻辑，需在“插入点”接入真实串口库 / Modbus 驱动。

### 7.5 结果查询页（app/pages/result_query_page.py）

功能：

- 查询条件：开始/结束时间、产品/模板、完成状态、报警状态
- 查询 / 重置 / 导出 CSV / 保存条件
- 检测记录表：检测时间、产品/模板、批次号、完成状态、检测结果、提示信息、报警信息
- 选中记录后下方详情框显示完整信息；顶部汇总总数/完成数/报警数

实现状态：数据为演示数据（`_append_demo_results`），未接数据库/文件检索；导出 CSV 为占位。

### 7.6 MES 对接页（app/pages/mes_page.py）

功能：

- MES 服务配置：上报地址、API Key
- 测试连接（demo 模拟）
- 勾选上报报文：设备状态 / 检测结果 / 报警信息 / 统计信息 / 操作日志 / 自定义报文
- 自定义报文模板编辑、发送测试报文、重置、保存配置（`config/mes.yaml`）

实现状态：全部为 demo/占位，真实 MES HTTP/WebSocket 客户端需在“插入点”接入。

### 7.7 日志页（app/pages/log_page.py）

功能：

- 级别筛选：全部 / DEBUG / INFO / WARN / ERROR
- 添加测试日志、清空当天日志、导出 CSV、保存筛选（`config/log.yaml`）
- 日志表：时间、级别、来源、消息，级别带颜色
- 仅显示当天日志，界面最多 100 条

实现状态：日志已真实写入 `log/YYYYMMDD.txt`（CSV 逗号分隔）；真实日志源未接。

### 7.8 参数页（app/pages/parameters_page.py）

功能：

- 系统参数：界面语言、日志级别、启用自动保存
- 计数设置：OK/NG 计数方式（日计数 / 班计数），最多 6 个班次时间
- 存储路径：检测结果目录、数据存储目录
- 保存到 `config/system.yaml`

说明：相机参数已迁移到相机管理页，检测参数已迁移到模板编辑页。
班次时间被 `ProductionCounterService` 用于班计数清零判断。

### 7.9 人员管理页（app/pages/personnel_page.py）

功能：

- 人员列表：工号、姓名、角色、权限、状态
- 新增 / 编辑（占位弹窗）、删除（可用）、刷新（恢复演示数据）

实现状态：演示数据，可替换为数据库、LDAP 或权限配置文件。

---

## 8. 服务层（app/services）

| 文件 | 职责 | 关键点 |
| --- | --- | --- |
| `config_service.py` | 统一配置/模板读写 | 页面配置 `config/<页面名>.yaml`；模板 `flow/<模板名>/template.yaml`；打包后根目录指向 exe 同级；`_copy_bundled_runtime_data` 自动复制内置 config/flow |
| `dashboard_service.py` | 看板数据服务 | `DashboardSnapshot` 数据类 + 内置演示 `TEMPLATES`；统计来自 `ProductionCounterService` |
| `log_service.py` | 日志文件服务 | 按天写入 `log/YYYYMMDD.txt`，CSV 格式；`append/load_today/clear_today` |
| `production_counter_service.py` | 生产计数 | OK/NG、日/周/月持久化到 `checknum/counter_state.json`；启动时按日/班次清零；清零前写入 `checknum/check_result_num.txt`；`snapshot()/add_result()` |

### ConfigService 主要接口

```python
save_page_config(page_name, data) -> Path
load_page_config(page_name) -> dict
save_template(template_name, data) -> Path
load_template(template_name) -> dict
save_template_category(template_name, category, filename, data) -> Path
copy_template(source_name, target_name) -> Path
delete_template(template_name) -> bool
list_templates() -> list[str]
ensure_template_dirs(template_name) -> list[Path]   # 自动迁移旧中文子目录
```

---

## 9. 可复用组件（app/widgets）

| 文件 | 类 | 用途 |
| --- | --- | --- |
| `camera_image_view.py` | `CameraImageView` | 相机图像显示：滚轮缩放、右键拖动平移、十字虚线拖动、双击适配 |
| `camera_view.py` | `CameraViewWidget` | 运行看板画面区：显示图像 + 中心线 + ROI 框叠加 |
| `roi_canvas.py` | `RoiCanvas` | ROI 画布：缩放/平移/十字线，圆形与旋转矩形（无填充轮廓），选中与中心拖拽 |
| `roi_editor.py` | `RoiEditorDialog` | ROI 大图编辑弹窗：形状选择、正/反转按钮、三档旋转倍率、参数表格 |
| `stat_card.py` | `StatCard` | 看板统计卡片 |

ROI 数据结构（`normalize_roi` 统一）：

- 矩形：`{name, shape: rect, cx, cy, w, h, angle}`
- 圆形：`{name, shape: circle, cx, cy, radius}`

---

## 10. 驱动层（drivers）

### 10.1 相机驱动（drivers/camera/usb_camera.py）—— 已实现

- `UsbCameraDriver`：OpenCV 枚举（`CAP_DSHOW`）、打开、关闭、取帧
- `UsbCameraCaptureThread`：QThread 独立采集线程，`frame_ready` 信号回传主线程

### 10.2 IO 驱动（drivers/io/）—— 仅 README

建议接口：

```python
class IODriver:
    def connect(self, ip, port) -> bool: ...
    def disconnect(self) -> None: ...
    def read_inputs(self, count) -> list[bool]: ...
    def write_coil(self, index, value) -> None: ...
```

接入位置：`app/pages/hardware_config_page.py`。

### 10.3 MES 驱动（drivers/mes/）—— 仅 README

建议接口：

```python
class MesDriver:
    def configure(self, url, api_key) -> None: ...
    def test_connection(self) -> bool: ...
    def send(self, message_type, payload) -> bool: ...
```

接入位置：`app/pages/mes_page.py`。

---

## 11. 算法层（algorithms/）—— 预留

建议统一检测接口：

```python
class DetectionAlgorithm:
    def load_model(self, model_path) -> None: ...
    def detect(self, image, rois, params) -> list[dict]: ...
```

接入位置：模板编辑页后续检测流程、运行看板正式检测流程。

---

## 12. 软件授权模块（app/checkdog/）

### LicenseManager（app/checkdog/license_manager.py）

- `machine_code()`：基于 `platform.system() + platform.node() + uuid.getnode()`
  SHA-256 摘要，格式 `XXXX-XXXX-XXXX-XXXX`
- `generate_key(machine_code, start_date, end_date)`：生成动态密钥（HMAC 式签名 + base64）
- `activate(key)`：校验签名、机器码、起止日期，成功保存激活信息
- `is_activated()` / `is_expired()` / `expiry_date()`
- 数据位置：开发环境在项目根目录 `license_data.json`；打包后在 exe 同级目录
- 当前 `license_data.json` 为已激活示例，到期 `2027-08-28`

### license_tool.py

独立 GUI 工具：显示机器码，选择起止日期，生成授权密钥。

### 到期控制（主窗口）

- 启动时已到期 → 30 分钟宽限定时器
- 超时 → 禁用页面栈 + 弹窗提示
- 输入正确密钥 → 解锁并显示到期日期

---

## 13. 配置与流程数据

### 13.1 config 目录

| 文件 | 内容 |
| --- | --- |
| `camera.yaml` | 相机类型、驱动、曝光、增益、帧率、触发、像素格式 |
| `hardware.yaml` | 串口、波特率、数据位、停止位、校验位、Modbus IP/端口 |
| `mes.yaml` | 上报地址、API Key、选中报文、自定义模板 |
| `system.yaml` | 语言、日志级别、自动保存、结果目录、数据目录、计数方式、班次 |
| `result_query.yaml` | 查询时间、产品、状态、报警筛选 |
| `log.yaml` | 日志级别筛选 |

### 13.2 flow 目录

```text
flow/
├─ 默认产品A/
│  ├─ template.yaml              # 主模板（name/model_file/rois/detection/other_params）
│  ├─ ROI Config/roi.yaml
│  ├─ Detection Config/detection.yaml
│  ├─ Model Config/model.yaml
│  └─ Other Config/other.yaml
├─ 产品B/ ...
├─ 123/      # 历史模板（含旧字段）
├─ 333/ 999/ # 旧模板（含 labels/steps/use_gesture 旧字段）
└─ 3333/     # 新结构模板
```

新模板标准结构：

```yaml
name: 模板名
model_file: ''
rois:
  - name: ROI-1
    shape: rect
    cx: 150
    cy: 120
    w: 200
    h: 150
    angle: 0
detection:
  confidence: 0.5
  detection_count: 20
  spare_1: ''
  spare_2: ''
  spare_3: ''
  enable_1: false
  enable_2: false
  enable_3: false
  enable_4: false
  enable_5: false
  function_1: 功能1
  function_2: 功能2
  function_3: 功能3
  function_4: 功能4
  function_5: 功能5
other_params:
  - name: 参数名
    value: 参数值
```

---

## 14. 打包（PyInstaller）

三个 spec：

| 文件 | 模式 | 特点 |
| --- | --- | --- |
| `main.spec` | 目录模式 | `main`，console，无 datas |
| `SOP.spec` | 单文件模式 | `SOP`，附带 config/flow，windowed |
| `SOP_APP.spec` | 目录模式 | `SOP_APP`，附带 config/flow，windowed，uac_admin，图标 |

README 中的命令：

```powershell
# 单文件 exe
pyinstaller --noconfirm --windowed --onefile --name SOP --add-data "config;config" --add-data "flow;flow" main.py

# 小 exe + 外部配置目录
pyinstaller -D main.py --noconfirm --windowed --icon=MyAppLog.ico --name SOP_APP --uac-admin --add-data "config;config" --add-data "flow;flow"
```

注意：Windows 下 `--add-data` 用分号 `;`，Linux/macOS 用冒号 `:`。
打包后 `ConfigService` 会把内置 `config/`、`flow/` 初始文件复制到 exe 同级目录。

---

## 15. UI 设计文件（ui/ 与 oriui/）

- `ui/`：Qt Designer 基础 `.ui` 文件（每页一份，共 10 个）
- `oriui/`：带暗黑样式预览的 `.ui` 文件
- 当前程序以 `app/pages/*.py` 手写 UI 为准，`.ui` 文件作为设计参考与二次编辑使用
- 修改界面后需同步维护两份 UI 文件

---

## 16. 当前实现状态总览

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 主窗口 / 导航 / 状态栏 | 已实现 | 暗黑主题，9 页面切换 |
| USB 相机采集 | 已实现 | OpenCV 枚举、打开、预览、拍照 |
| GIGE 相机 | Demo | 需接真实 SDK |
| 运行看板 | 部分实现 | 计数真实持久化，模板/设备展示为演示数据 |
| 模板编辑 | 已实现（框架） | 模板/ROI/检测参数/模型/其他参数可编辑保存 |
| 检测算法 | 预留 | `algorithms/` 无实现 |
| 硬件配置（串口/Modbus/IO） | Demo | 全部为模拟逻辑 |
| 结果查询 | Demo | 演示数据，导出占位 |
| MES 对接 | Demo | 需接真实 MES 客户端 |
| 日志 | 已实现（文件） | 按天 CSV 落盘；真实日志源未接 |
| 参数 / 人员管理 | 框架已实现 | 参数可保存，人员为演示数据 |
| 软件授权 | 已实现 | 机器绑定、密钥激活、到期锁定 |

---

## 17. 升级注意事项与扩展点

1. **新增页面**：继承 `BasePage` → `app/pages/__init__.py` 导出 → `main_window.py` 的 `NAV_ITEMS` 注册。
2. **接入真实硬件/外部系统**：优先在 `drivers/` 对应目录实现统一接口，
   再替换页面中标记 `插入点` 的 demo 逻辑（代码中可搜索 `插入点` 快速定位）。
3. **新增算法**：在 `algorithms/` 实现统一 `detect()` 接口。
4. **配置读写**：通过 `ConfigService.save_page_config / load_page_config`，
   自动落到 `config/<页面名>.yaml`。
5. **流程模板**：通过 `ConfigService.save_template / load_template`，
   落到 `flow/<模板名>/template.yaml`（含四个分类子目录）。
6. **UI 二次设计**：修改界面后需同步 `ui/` 与 `oriui/` 两份 `.ui` 文件。
7. **打包**：新增需打包的数据目录时，同步更新 `.spec` 文件的 `datas`。
8. **授权模块**：逻辑集中在 `app/checkdog/`，业务代码不要混入。
9. **历史遗留**：`flow/123`、`333`、`999` 等旧模板含 `labels/steps/use_gesture/gesture`
   旧字段，当前版本不再使用，加载时会忽略并按新结构补齐。
10. **升级建议**：下一步针对性升级前，建议先明确优先级，例如：
    - 接真实检测算法并打通「相机 → ROI → 模型推理 → OK/NG 计数」主流程
    - 运行看板模板下拉改为读取 `flow/` 真实模板（当前是内置硬编码）
    - 结果查询接入真实记录存储（数据库或本地文件检索）
    - 硬件配置接入真实串口 + ModbusTCP 驱动
    - MES 对接接入真实 HTTP/WebSocket 上报

---

## 18. 快速定位索引

| 想做的事 | 关键文件 |
| --- | --- |
| 主窗口、导航、页面注册 | `app/main_window.py` |
| 全局主题/样式 | `app/theme.py` |
| 底部状态栏 | `app/status_bar.py` |
| 帮助/激活 | `app/help_dialog.py` |
| 相机逻辑 | `app/pages/camera_page.py`、`drivers/camera/usb_camera.py` |
| 运行看板 | `app/pages/run_dashboard_page.py`、`app/services/dashboard_service.py` |
| 模板编辑 | `app/pages/flow_page.py`、`app/widgets/roi_canvas.py`、`app/widgets/roi_editor.py` |
| 硬件/IO | `app/pages/hardware_config_page.py`、`drivers/io/` |
| 结果查询 | `app/pages/result_query_page.py` |
| MES | `app/pages/mes_page.py`、`drivers/mes/` |
| 日志 | `app/pages/log_page.py`、`app/services/log_service.py` |
| 参数 | `app/pages/parameters_page.py` |
| 人员管理 | `app/pages/personnel_page.py` |
| 授权 | `app/checkdog/license_manager.py`、`license_tool.py` |
| 配置读写 | `app/services/config_service.py` |
| 生产计数 | `app/services/production_counter_service.py` |
| 打包配置 | `SOP_APP.spec`、`SOP.spec`、`main.spec` |
| 设计参考 UI | `ui/`、`oriui/` |

---

*分析日期：2026-08-20。本文档可作为后续升级讨论的基线，升级完成后再同步更新。*
