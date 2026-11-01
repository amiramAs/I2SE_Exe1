"""
End-to-End CLI Demo tests for Ex0.py based on Section 5 of docs/testing_strategy.md.
"""
import os
import sys
import subprocess
import pytest


PYTHON_EXE = sys.executable


def test_cli_01_full_e2e_run(tmp_path):
    """TC-CLI-01: Run Ex0.py on valid NRRD and CSV, assert exit code 0 and non-empty MP4."""
    output_mp4 = str(tmp_path / "test_out.mp4")
    cmd = [PYTHON_EXE, "Ex0.py", "data/onion.nrrd", "data/sample_trajectory.csv", output_mp4]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.exists(output_mp4)
    assert os.path.getsize(output_mp4) > 1000  # Non-trivial MP4 file size


def test_cli_02_insufficient_arguments():
    """TC-CLI-02: Run Ex0.py with missing arguments, assert non-zero exit and usage syntax."""
    cmd = [PYTHON_EXE, "Ex0.py", "data/onion.nrrd"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Usage: python Ex0.py" in result.stderr


def test_cli_03_missing_volume_file(tmp_path):
    """TC-CLI-03: Run Ex0.py with missing NRRD file, assert graceful error exit."""
    output_mp4 = str(tmp_path / "test_out.mp4")
    cmd = [PYTHON_EXE, "Ex0.py", "non_existent.nrrd", "data/sample_trajectory.csv", output_mp4]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "not found" in result.stderr


def test_cli_04_missing_csv_file(tmp_path):
    """TC-CLI-04: Run Ex0.py with missing CSV file, assert graceful error exit."""
    output_mp4 = str(tmp_path / "test_out.mp4")
    cmd = [PYTHON_EXE, "Ex0.py", "data/onion.nrrd", "non_existent.csv", output_mp4]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "not found" in result.stderr


def test_cli_05_mixed_sequence_and_empty_line(tmp_path):
    """TC-CLI-06: CSV with empty line between rows preserves frame output without crashing."""
    custom_csv = str(tmp_path / "custom.csv")
    with open(custom_csv, "w", encoding="utf-8") as f:
        f.write("Number of points,x1,y1,z1,x2,y2,z2,x3,y3,z3\n")
        f.write("3, 100,100,50, 50,100,100, 150,100,100\n")
        f.write("\n")  # Empty line to be skipped
        f.write("3, 10,20,foo,40,50,60,70,80,90\n")  # Malformed line (produces error frame)

    output_mp4 = str(tmp_path / "custom.mp4")
    cmd = [PYTHON_EXE, "Ex0.py", "data/onion.nrrd", custom_csv, output_mp4]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.exists(output_mp4)
    assert os.path.getsize(output_mp4) > 500
