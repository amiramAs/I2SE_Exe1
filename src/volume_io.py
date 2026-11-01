"""
Module for loading and managing 3D volumetric datasets (.nrrd) in contiguous memory.
"""
from __future__ import annotations
import os
import nrrd
import numpy as np


class VolumeData:
    """Encapsulates a 3D volumetric array stored contiguously in memory."""

    def __init__(self, data: np.ndarray, header: dict | None = None):
        if data.ndim != 3:
            raise ValueError(f"Expected 3D volume grid, got array of shape {data.shape} ({data.ndim}D)")

        # Ensure contiguous memory layout for maximum CPU cache locality (SRS Section 3)
        self.array: np.ndarray = np.ascontiguousarray(data)
        self.flat_array: np.ndarray = self.array.ravel()
        self.header: dict = header or {}
        self.shape: tuple[int, int, int] = self.array.shape
        self.dtype = self.array.dtype
        self.stride_x: int = self.shape[1] * self.shape[2]
        self.stride_y: int = self.shape[2]

    @classmethod
    def from_file(cls, file_path: str) -> VolumeData:
        """Loads a 3D .nrrd file from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NRRD volume file not found: {file_path}")

        data, header = nrrd.read(file_path)
        return cls(data, header)

    def sample_nearest(self, x: int, y: int, z: int) -> int | float:
        """Returns voxel intensity at (x, y, z) or 0 if out of bounds."""
        dx, dy, dz = self.shape
        if 0 <= x < dx and 0 <= y < dy and 0 <= z < dz:
            return self.array[x, y, z]
        return 0
