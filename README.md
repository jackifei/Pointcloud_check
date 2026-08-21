# Pointcloud_check

三维点云视觉检测软件框架（PyQt6 + Open3D）。

- 点云设备管理：文件设备（.ply/.pcd）开箱即用，真实 3D 相机按驱动接口接入
- 三维点云显示：自研 QOpenGLWidget 控件，支持旋转/平移/缩放、高度伪彩
- 模板编辑：3D 点云参考 + 2D 投影 ROI 编辑 + 划区平面拟合（RANSAC/最小二乘）
- 运行看板：三维点云实时显示
- 点云处理：Open3D（体素降采样、离群点去除、法线估算、高度投影）

运行：`python main.py`（环境：conda `python312pack`）
