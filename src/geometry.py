"""
Geometric computations and validation for 3D slicing planes.
"""
from __future__ import annotations
import numpy as np


EPSILON = 1e-3


def dist(p1: np.ndarray, p2: np.ndarray) -> float:
    """Calculates Euclidean distance between two 3D points."""
    return float(np.linalg.norm(np.asarray(p2, dtype=np.float64) - np.asarray(p1, dtype=np.float64)))


def unit_vector(p_from: np.ndarray, p_to: np.ndarray, length: float | None = None) -> np.ndarray:
    """Returns normalized unit direction vector from p_from to p_to."""
    diff = np.asarray(p_to, dtype=np.float64) - np.asarray(p_from, dtype=np.float64)
    if length is None:
        length = float(np.linalg.norm(diff))
    if length < 1e-9:
        return np.zeros(3, dtype=np.float64)
    return diff / length


def are_collinear(points: list[np.ndarray], eps: float = EPSILON) -> bool:
    """
    Checks if 3 or 4 points lie along a single linear segment.
    """
    pts = [np.asarray(p, dtype=np.float64) for p in points]
    if len(pts) < 3:
        return True

    # Vector from first point to second point
    v1 = pts[1] - pts[0]
    norm1 = np.linalg.norm(v1)
    if norm1 < eps:
        # First two points are coincident -> test remaining
        return are_collinear(pts[1:], eps)

    u1 = v1 / norm1

    for p in pts[2:]:
        v = p - pts[0]
        norm_v = np.linalg.norm(v)
        if norm_v < eps:
            continue
        cross_prod = np.cross(u1, v / norm_v)
        if np.linalg.norm(cross_prod) > eps:
            return False

    return True


def is_isosceles(a1: np.ndarray, a2: np.ndarray, b: np.ndarray, c: np.ndarray, is_3pt: bool = False, eps: float = 0.5) -> bool:
    """
    Validates if leg lengths are equal within tolerance:
    dist(a1, b) == dist(a2, c)
    """
    dab = dist(a1, b)
    dac = dist(a2, c)
    return abs(dab - dac) <= eps


def are_bases_parallel(a1: np.ndarray, a2: np.ndarray, b: np.ndarray, c: np.ndarray, eps: float = 0.05) -> bool:
    """
    For 4-point trapezoids, checks if top base (a1 -> a2) is parallel to bottom base (b -> c).
    """
    v_top = np.asarray(a2, dtype=np.float64) - np.asarray(a1, dtype=np.float64)
    v_bot = np.asarray(c, dtype=np.float64) - np.asarray(b, dtype=np.float64)

    norm_top = np.linalg.norm(v_top)
    norm_bot = np.linalg.norm(v_bot)

    if norm_top < 1e-7 or norm_bot < 1e-7:
        return False

    u_top = v_top / norm_top
    u_bot = v_bot / norm_bot

    cross_prod = np.cross(u_top, u_bot)
    # Vectors must point in same direction and be parallel
    is_parallel = np.linalg.norm(cross_prod) <= eps
    same_direction = np.dot(u_top, u_bot) > 0

    return bool(is_parallel and same_direction)


def are_coplanar(a1: np.ndarray, a2: np.ndarray, b: np.ndarray, c: np.ndarray, eps: float = 1.0) -> bool:
    """
    Checks if 4 points lie on the same 2D plane in R^3 using scalar triple product.
    """
    p1 = np.asarray(a1, dtype=np.float64)
    p2 = np.asarray(a2, dtype=np.float64)
    p3 = np.asarray(b, dtype=np.float64)
    p4 = np.asarray(c, dtype=np.float64)

    v1 = p2 - p1
    v2 = p3 - p1
    v3 = p4 - p1

    volume = abs(float(np.dot(np.cross(v1, v2), v3)))
    return volume <= eps
