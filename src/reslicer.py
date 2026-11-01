"""
Core Planar Reslicing Engine: Slices 3D volumetric data into 2D planar frames.
"""
from __future__ import annotations
import numpy as np

from src.geometry import (
    dist,
    unit_vector,
    are_collinear,
    is_isosceles,
    are_bases_parallel,
    are_coplanar,
)
from src.error_renderer import make_error_frame
from src.volume_io import VolumeData


def reslice_plane(
    volume: VolumeData | np.ndarray,
    points: list[np.ndarray],
    last_frame_dims: tuple[int, int] = (500, 500),
) -> np.ndarray:
    """
    Extracts a 2D cross-sectional planar frame from a 3D volume.

    Args:
        volume: VolumeData or 3D numpy array.
        points: List of 3 or 4 points in R^3.
        last_frame_dims: Tuple of (height, width) of the last valid frame.

    Returns:
        np.ndarray: 2D array of shape (height, width) representing the sliced image.
    """
    vol_array = volume.array if isinstance(volume, VolumeData) else np.asarray(volume)
    dx, dy, dz = vol_array.shape

    # 1. Point Count Validation
    if len(points) == 3:
        a = np.asarray(points[0], dtype=np.float64)
        b = np.asarray(points[1], dtype=np.float64)
        c = np.asarray(points[2], dtype=np.float64)
        a1 = a.copy()
        a2 = a.copy()
        is_3pt = True
    elif len(points) == 4:
        a1 = np.asarray(points[0], dtype=np.float64)
        a2 = np.asarray(points[1], dtype=np.float64)
        b = np.asarray(points[2], dtype=np.float64)
        c = np.asarray(points[3], dtype=np.float64)
        is_3pt = False
    else:
        return make_error_frame("ERROR: Invalid coordinate count - expected 3 or 4 points", last_frame_dims)

    # 2. Geometric Validations
    pts_to_check = [a1, a2, b, c] if not is_3pt else [points[0], b, c]

    # Collinear check
    if are_collinear(pts_to_check):
        return make_error_frame("ERROR: Collinear vertices - cannot construct a 2D slicing plane", last_frame_dims)

    dab = dist(a1, b)
    dac = dist(a2, c)
    dbc = dist(b, c)

    # Degenerate distance check (division by zero prevention)
    if dab < 1e-4 or dbc < 1e-4:
        return make_error_frame("ERROR: Degenerate geometry - zero distance between vertices", last_frame_dims)

    # Isosceles check
    if not is_isosceles(a1, a2, b, c, is_3pt=is_3pt):
        return make_error_frame("ERROR: Non-isosceles geometry - leg lengths must be equal", last_frame_dims)

    # For 4 points, check parallel bases and coplanarity
    if not is_3pt:
        if not are_bases_parallel(a1, a2, b, c):
            return make_error_frame("ERROR: Non-parallel trapezoid bases - top and bottom must be parallel", last_frame_dims)
        if not are_coplanar(a1, a2, b, c):
            return make_error_frame("ERROR: Non-coplanar points in 4-point geometry", last_frame_dims)

    # 3. Canvas Dimensions & Vector Initialization
    H = int(round(dab))
    W = int(round(dbc))

    if H <= 0 or W <= 0:
        return make_error_frame("ERROR: Degenerate dimensions - slice height or width is zero", last_frame_dims)

    output_frame = np.zeros((H, W), dtype=vol_array.dtype)

    v_ab = (b - a1) / dab
    v_ac = (c - a2) / dac

    # Cache volume representation and strides
    if isinstance(volume, VolumeData):
        flat_vol = volume.flat_array
        stride_x = volume.stride_x
        stride_y = volume.stride_y
    else:
        flat_vol = np.ascontiguousarray(vol_array).ravel()
        stride_x = dy * dz
        stride_y = dz

    # Full 2D Grid Vectorization (Guarantees >= 100 FPS)
    y_arr = np.arange(H, dtype=np.float64)
    A1 = a1 + y_arr[:, None] * v_ab
    A2 = a2 + y_arr[:, None] * v_ac
    diff = A2 - A1
    d12 = np.linalg.norm(diff, axis=1)

    scanline_len = np.rint(d12).astype(np.int64)
    x_offset = np.rint((W - scanline_len) / 2.0).astype(np.int64)

    d12_safe = np.where(d12 > 1e-7, d12, 1.0)[:, None]
    dp = np.where((d12 > 1e-7)[:, None], diff / d12_safe, 0.0)

    # Compute valid scanline masks across all pixels
    x1_grid = np.arange(W)[None, :] - x_offset[:, None]
    mask = (x1_grid >= 0) & (x1_grid <= scanline_len[:, None])

    y_idx, x_idx = np.where(mask)
    if y_idx.size == 0:
        return output_frame

    x1_vals = x1_grid[y_idx, x_idx]
    probes = A1[y_idx] + x1_vals[:, None] * dp[y_idx]
    indices = np.rint(probes).astype(np.int64)

    ix = indices[:, 0]
    iy = indices[:, 1]
    iz = indices[:, 2]

    in_bounds = (ix >= 0) & (ix < dx) & (iy >= 0) & (iy < dy) & (iz >= 0) & (iz < dz)
    if np.any(in_bounds):
        y_valid = y_idx[in_bounds]
        x_valid = x_idx[in_bounds]
        flat_idx = ix[in_bounds] * stride_x + iy[in_bounds] * stride_y + iz[in_bounds]
        output_frame[y_valid, x_valid] = flat_vol[flat_idx]

    return output_frame

