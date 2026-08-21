# 算法目录

建议每个算法模块暴露统一检测接口：

```python
class DetectionAlgorithm:
    def load_model(self, model_path: str) -> None: ...
    def detect(self, image, rois: list[dict], params: dict) -> list[dict]: ...
```

流程编辑页中的“单次执行”和正式检测流程，后续都应调用这里的算法接口。
