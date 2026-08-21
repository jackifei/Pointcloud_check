# config 目录

程序运行时会将各页面配置保存到此目录，文件名对应页面或功能：

- camera.yaml
- hardware.yaml
- system.yaml
- mes.yaml
- result_query.yaml
- log.yaml

这些文件由 `app/services/config_service.py` 统一读写。
