from __future__ import annotations

import numpy as np


def fit_plane_least_squares(points) -> dict:
    """使用最小二乘法对点云拟合平面，输出平面方程 ax + by + cz + d = 0。

    返回字典包含：
    - normal / a / b / c / d：平面方程系数与单位法向量
    - center：拟合点云的质心
    - rms：点到平面的均方根误差
    - point_count：参与拟合的点数
    - equation：可读的平面方程字符串
    """
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("points 形状应为 (N, >=3)")
    if points.shape[0] < 3:
        raise ValueError("至少需要 3 个点进行平面拟合")

    xyz = points[:, :3]
    centroid = xyz.mean(axis=0)
    centered = xyz - centroid

    # 最小二乘平面法向量为最小奇异值对应的右奇异向量。
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    normal = vh[-1].astype(np.float64)
    normal /= np.linalg.norm(normal)
    if normal[2] < 0:
        normal = -normal

    d = -float(normal @ centroid)
    residuals = centered @ normal
    rms = float(np.sqrt(np.mean(residuals ** 2)))

    a, b, c = (float(value) for value in normal)
    return {
        "normal": normal,
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "center": centroid,
        "rms": rms,
        "point_count": int(xyz.shape[0]),
        "equation": f"{a:.6f}x + {b:.6f}y + {c:.6f}z + {d:.6f} = 0",
    }
