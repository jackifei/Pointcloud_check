from __future__ import annotations

import numpy as np


def extract_sub_point_cloud(points, xy, tol: float = 1.0) -> np.ndarray:
    """根据二维有效区域的 XY 坐标，从原始点云中提取对应的子点云。

    参数
    ----
    points : (N, >=3) array_like
        原始三维点云，前两列分别为 X、Y。
    xy : (M, 2) array_like
        有效区域的 XY 坐标数组。
    tol : float
        XY 匹配容差，默认 1.0（适合整数像素/网格坐标）。

    返回
    ----
    (K, 3) numpy.ndarray
        去重后提取出的子点云。
    """
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("points 形状应为 (N, >=3)")
    if points.shape[0] == 0:
        return np.empty((0, 3), dtype=np.float64)

    xy = np.asarray(xy, dtype=np.float64)
    if xy.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    if xy.ndim == 1:
        xy = xy.reshape(1, -1)
    if xy.shape[1] < 2:
        raise ValueError("xy 至少需要两列 (x, y)")

    # 量化到整数网格，做高效的排序 + 二分查找匹配。
    pcol = np.rint(points[:, 0] / tol).astype(np.int64)
    prow = np.rint(points[:, 1] / tol).astype(np.int64)
    qcol = np.rint(xy[:, 0] / tol).astype(np.int64)
    qrow = np.rint(xy[:, 1] / tol).astype(np.int64)

    cmin = int(pcol.min())
    rmin = int(prow.min())
    rspan = int(prow.max() - prow.min()) + 1
    pkey = (pcol - cmin) * rspan + (prow - rmin)

    order = np.argsort(pkey, kind="stable")
    sorted_keys = pkey[order]
    uniq_keys, uniq_first = np.unique(sorted_keys, return_index=True)

    qkey = (qcol - cmin) * rspan + (qrow - rmin)
    pos = np.searchsorted(uniq_keys, qkey)
    hit = pos < len(uniq_keys)
    safe = np.clip(pos, 0, len(uniq_keys) - 1)
    hit = hit & (uniq_keys[safe] == qkey)
    if not np.any(hit):
        return np.empty((0, 3), dtype=np.float64)

    selected = order[uniq_first[safe[hit]]]
    selected = np.unique(selected)
    return points[selected, :3]
