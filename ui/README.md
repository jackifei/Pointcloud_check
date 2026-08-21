# UI 文件说明

本目录中的 `.ui` 文件是每个页面的 Qt Designer 基线文件，供二次编辑使用。

包含页面：相机管理、运行看板、流程编辑、硬件配置、结果查询、MES 对接、日志、参数、人员管理和主窗口。

使用方式：

1. 用 Qt Designer 打开对应 `.ui` 文件。
2. 调整布局或控件属性后保存。
3. 可使用 PyQt6 自带的 `pyuic6` 生成 Python 代码，再与当前手写页面逻辑合并：

```powershell
python -m PyQt6.uic.pyuic ui\camera_page.ui -o ui\camera_page_ui.py
```

当前程序仍以 `app/pages/*.py` 手写 UI 为主，`.ui` 文件用于设计和交接参考。
