from __future__ import annotations

from .plane_fit import fit_plane_least_squares
from .sub_cloud import extract_sub_point_cloud


def extract_and_fit_plane(points, xy, tol: float = 1.0) -> dict:
    """对接二维有效区域的 XY 坐标数组，提取子点云并做最小二乘平面拟合。

    返回 fit_plane_least_squares() 的全部字段，并额外包含：
    - sub_points：提取出的子点云
    - sub_point_count：子点云点数
    """
    sub_points = extract_sub_point_cloud(points, xy, tol)
    if sub_points.shape[0] < 3:
        raise ValueError(
            f"提取的子点云点数不足（{sub_points.shape[0]} 点），无法拟合平面"
        )
    result = fit_plane_least_squares(sub_points)
    result["sub_points"] = sub_points
    result["sub_point_count"] = int(sub_points.shape[0])
    return result
