from __future__ import annotations

import numpy as np
import open3d as o3d


def voxel_downsample(pcd, voxel_size: float):
    """体素降采样。voxel_size <= 0 或点云为空时原样返回。"""
    if pcd is None or len(pcd.points) == 0 or float(voxel_size) <= 0:
        return pcd
    return pcd.voxel_down_sample(float(voxel_size))


def remove_outliers(pcd, nb_neighbors: int = 20, std_ratio: float = 2.0):
    """统计离群点去除。"""
    if pcd is None or len(pcd.points) == 0:
        return pcd
    _, inliers = pcd.remove_statistical_outlier(
        nb_neighbors=int(nb_neighbors),
        std_ratio=float(std_ratio),
    )
    return pcd.select_by_index(inliers)


def estimate_normals(pcd, search_radius: float = 1.0, max_nn: int = 30):
    """估算点云法线。"""
    if pcd is None or len(pcd.points) == 0:
        return pcd
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=float(search_radius),
            max_nn=int(max_nn),
        )
    )
    return pcd


def height_projection(
    pcd,
    width: int = 512,
    height: int = 512,
    axis: str = "z",
    reduction: str = "mean",
) -> np.ndarray:
    """把点云投影到平面，生成高度图（float32，值域 0..1）。

    axis: 使用哪个轴作为高度（"z" 默认投影到 XY 平面）。
    reduction: "mean" 取平均高度，"max" 取最大高度。
    """
    points = np.asarray(pcd.points, dtype=np.float64) if pcd is not None else np.empty((0, 3))
    if points.shape[0] == 0:
        return np.zeros((height, width), dtype=np.float32)

    xyz = points[:, :3]
    if axis == "x":
        u, v, h = xyz[:, 1], xyz[:, 2], xyz[:, 0]
    elif axis == "y":
        u, v, h = xyz[:, 0], xyz[:, 2], xyz[:, 1]
    else:
        u, v, h = xyz[:, 0], xyz[:, 1], xyz[:, 2]

    u_min, u_max = float(u.min()), float(u.max())
    v_min, v_max = float(v.min()), float(v.max())
    if u_max - u_min < 1e-9:
        u_max = u_min + 1e-9
    if v_max - v_min < 1e-9:
        v_max = v_min + 1e-9

    cols = np.clip(((u - u_min) / (u_max - u_min) * (width - 1)).astype(np.int64), 0, width - 1)
    rows = np.clip(((v - v_min) / (v_max - v_min) * (height - 1)).astype(np.int64), 0, height - 1)

    if reduction == "max":
        grid = np.full((height, width), np.nan, dtype=np.float64)
        np.maximum.at(grid, (rows, cols), h)
    else:
        accum = np.zeros((height, width), dtype=np.float64)
        counts = np.zeros((height, width), dtype=np.float64)
        np.add.at(accum, (rows, cols), h)
        np.add.at(counts, (rows, cols), 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            grid = accum / np.where(counts > 0, counts, 1.0)
        grid[counts == 0] = np.nan

    finite = grid[np.isfinite(grid)]
    if finite.size == 0:
        return np.zeros((height, width), dtype=np.float32)

    lo, hi = float(finite.min()), float(finite.max())
    if hi - lo < 1e-9:
        norm = np.where(np.isfinite(grid), 0.5, 0.0)
    else:
        norm = np.where(np.isfinite(grid), (grid - lo) / (hi - lo), 0.0)
    return norm.astype(np.float32)
