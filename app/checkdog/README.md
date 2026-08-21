# checkdog 说明

该目录负责软件授权、机器绑定和到期控制，独立于业务页面代码。

核心文件：

- `license_manager.py`：授权管理核心

授权数据默认保存：

- 开发环境：项目根目录 `license_data.json`
- 打包环境：`SOP.exe` 同级目录 `license_data.json`

授权工具入口：

```powershell
python license_tool.py
```
