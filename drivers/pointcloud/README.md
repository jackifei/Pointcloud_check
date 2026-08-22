# drivers/pointcloud

点云设备驱动目录。

- `base.py`：`PointCloudDeviceDriver` 统一接口
- `file_driver.py`：`FilePointCloudDriver`，把 `data/pointclouds/` 下的点云文件当作设备

真实 3D 相机（TOF / 结构光 / 激光轮廓仪）接入时，在此目录新增驱动并继承
`PointCloudDeviceDriver`，然后在 `app/pages/pointcloud_device_page.py` 的
“插入点”处替换当前文件设备驱动。
