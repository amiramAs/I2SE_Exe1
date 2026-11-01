"""
Black-Box automated test suite for the Planar Reslicing Engine.
Tests are based strictly on the specification in docs/testing_strategy.md.
"""
import pytest
import numpy as np

from src.geometry import are_collinear, is_isosceles, are_bases_parallel
from src.csv_parser import parse_csv_line
from src.reslicer import reslice_plane
from src.volume_io import VolumeData
from src.error_renderer import make_error_frame


@pytest.fixture
def synthetic_volume():
    """Creates a deterministic synthetic 3D volume (100x100x100) for fast testing."""
    data = np.zeros((100, 100, 100), dtype=np.uint8)
    # Fill an inner box [20:80, 20:80, 20:80] with intensity 200
    data[20:80, 20:80, 20:80] = 200
    return VolumeData(data)


def test_tc01_valid_3point_triangle(synthetic_volume):
    """TC-01: Valid 3-point isosceles triangle entirely within volume."""
    # Apex at (50, 50, 20), base vertices at (40, 50, 40) and (60, 50, 40)
    # dist(a, b) = sqrt(100 + 400) = sqrt(500) ~= 22.36 -> H = 22
    # dist(b, c) = 20 -> W = 20
    a = np.array([50.0, 50.0, 20.0])
    b = np.array([40.0, 50.0, 40.0])
    c = np.array([60.0, 50.0, 40.0])

    frame = reslice_plane(synthetic_volume, [a, b, c])
    assert frame.shape[0] > 0
    assert frame.shape[1] > 0
    # Inside the filled cube, voxels should be 200
    assert np.any(frame == 200)


def test_tc02_valid_4point_trapezoid(synthetic_volume):
    """TC-02: Valid 4-point isosceles trapezoid with parallel bases."""
    # Top base: (45, 50, 30) to (55, 50, 30), length = 10
    # Bottom base: (40, 50, 50) to (60, 50, 50), length = 20
    # Left leg: (45, 50, 30) to (40, 50, 50), length = sqrt(25 + 400) = sqrt(425)
    # Right leg: (55, 50, 30) to (60, 50, 50), length = sqrt(25 + 400) = sqrt(425)
    a1 = np.array([45.0, 50.0, 30.0])
    a2 = np.array([55.0, 50.0, 30.0])
    b = np.array([40.0, 50.0, 50.0])
    c = np.array([60.0, 50.0, 50.0])

    frame = reslice_plane(synthetic_volume, [a1, a2, b, c])
    assert frame.shape[0] == int(round(np.linalg.norm(b - a1)))
    assert frame.shape[1] == 20
    assert np.any(frame == 200)


def test_tc03_completely_out_of_bounds(synthetic_volume):
    """TC-03: Valid geometry entirely outside 3D volume produces a frame of zeros without error."""
    a = np.array([1000.0, 1000.0, 1000.0])
    b = np.array([1000.0, 1010.0, 1000.0])
    c = np.array([1010.0, 1010.0, 1000.0])

    # Leg lengths: dist(a,b)=10, dist(a,c)=sqrt(100+100)=14.14 -> adjust to be isosceles
    # Apex at (1000, 1000, 1000), base at (990, 1010, 1000) and (1010, 1010, 1000)
    b = np.array([990.0, 1010.0, 1000.0])
    c = np.array([1010.0, 1010.0, 1000.0])

    frame = reslice_plane(synthetic_volume, [a, b, c])
    assert frame.shape[0] > 0
    assert frame.shape[1] > 0
    # Entire frame must be zero (black background zero-padding)
    assert np.all(frame == 0)


def test_tc04_empty_line_skipped():
    """TC-04: Empty lines and whitespace rows are silently skipped."""
    assert parse_csv_line("").is_skipped is True
    assert parse_csv_line("   \n").is_skipped is True
    assert parse_csv_line("\t\r\n").is_skipped is True


def test_tc05_malformed_csv_line():
    """TC-05: Non-numeric strings in coordinate entries flag a malformed error."""
    rec = parse_csv_line("3, 10, 20, foo, 40, 50, 60, 70, 80, 90")
    assert rec.is_error is True
    assert "Malformed CSV line" in rec.error_message


def test_tc06_invalid_point_count():
    """TC-06: Invalid leading point count or token length flags format error."""
    rec1 = parse_csv_line("5, 1, 2, 3, 4, 5, 6, 7")
    assert rec1.is_error is True
    assert "Invalid CSV format" in rec1.error_message

    # 3 points but only 5 tokens total
    rec2 = parse_csv_line("3, 1, 2, 3, 4")
    assert rec2.is_error is True
    assert "Invalid CSV format" in rec2.error_message


def test_tc07_degenerate_geometry_zero_distance(synthetic_volume):
    """TC-07: Coincident vertices (division by zero) generate an error frame."""
    a = np.array([5.0, 5.0, 5.0])
    b = np.array([5.0, 5.0, 5.0])  # Same as a -> dist = 0
    c = np.array([10.0, 10.0, 10.0])

    frame = reslice_plane(synthetic_volume, [a, b, c], last_frame_dims=(300, 300))
    assert frame.shape == (300, 300)
    # White text pixels on black background
    assert np.any(frame > 0)


def test_tc08_collinear_vertices(synthetic_volume):
    """TC-08: Vertices lying on a single straight line produce an error frame."""
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([5.0, 5.0, 5.0])
    c = np.array([10.0, 10.0, 10.0])

    assert are_collinear([a, b, c]) is True
    frame = reslice_plane(synthetic_volume, [a, b, c], last_frame_dims=(250, 250))
    assert frame.shape == (250, 250)
    assert np.any(frame > 0)


def test_tc09_non_isosceles_geometry(synthetic_volume):
    """TC-09: Asymmetric leg lengths produce an error frame."""
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([0.0, 10.0, 0.0])   # dab = 10
    c = np.array([15.0, 20.0, 0.0])  # dac = sqrt(225+400) = 25

    assert is_isosceles(a, a, b, c) is False
    frame = reslice_plane(synthetic_volume, [a, b, c], last_frame_dims=(400, 400))
    assert frame.shape == (400, 400)
    assert np.any(frame > 0)


def test_tc10_non_parallel_trapezoid_bases(synthetic_volume):
    """TC-10: 4-point trapezoid with non-parallel bases produces an error frame."""
    a1 = np.array([0.0, 0.0, 0.0])
    a2 = np.array([5.0, 0.0, 0.0])   # top base vector = (5, 0, 0)
    b = np.array([0.0, 10.0, 0.0])
    c = np.array([5.0, 15.0, 0.0])   # bottom base vector = (5, 5, 0) -> not parallel!

    assert are_bases_parallel(a1, a2, b, c) is False
    frame = reslice_plane(synthetic_volume, [a1, a2, b, c], last_frame_dims=(350, 350))
    assert frame.shape == (350, 350)
    assert np.any(frame > 0)


def test_tc11_first_frame_error_fallback():
    """TC-11: First record failure defaults to (500, 500) dimensions."""
    frame = make_error_frame("ERROR: Malformed CSV line", frame_dims=(500, 500))
    assert frame.shape == (500, 500)
    assert np.any(frame > 0)


def test_tc12_decimal_coordinates_and_bounds_rounding(synthetic_volume):
    """TC-12: Decimal fractional coordinates are safely rounded without array index crashes."""
    a = np.array([50.45, 50.12, 20.78])
    b = np.array([39.88, 50.12, 40.23])
    c = np.array([61.02, 50.12, 40.23])

    # Leg lengths:
    # dab = sqrt((39.88-50.45)^2 + (40.23-20.78)^2) = sqrt(111.72 + 378.30) = sqrt(490.02) = 22.13
    # dac = sqrt((61.02-50.45)^2 + (40.23-20.78)^2) = sqrt(111.72 + 378.30) = sqrt(490.02) = 22.13
    frame = reslice_plane(synthetic_volume, [a, b, c])
    assert frame.ndim == 2
    assert frame.shape[0] == int(round(np.linalg.norm(b - a)))
