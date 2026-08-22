# 算法目录

## pointcloud/

点云预处理算法（基于 Open3D）：

- `voxel_downsample`：体素降采样
- `remove_outliers`：统计离群点去除
- `estimate_normals`：法线估算
- `height_projection`：高度投影图

后续的检测/测量算法可在 `algorithms/pointcloud/` 下继续新增模块，
供模板编辑页“单次执行”和运行看板正式检测流程调用。

## 兼容接口

如需 2D 图像检测，可保留统一接口：

```python
class DetectionAlgorithm:
    def load_model(self, model_path: str) -> None: ...
    def detect(self, image, rois: list[dict], params: dict) -> list[dict]: ...
```
