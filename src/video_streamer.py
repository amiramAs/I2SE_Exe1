"""
Zero Disk I/O video streaming engine: pipes raw frames directly into ffmpeg stdin.
"""
from __future__ import annotations
import shutil
import subprocess
import numpy as np


def get_ffmpeg_executable() -> str:
    """Finds ffmpeg executable on system PATH or falls back to bundled imageio-ffmpeg."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def pad_to_dimension(frame: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Symmetrically pads a 2D frame with zeros to match target dimensions."""
    h, w = frame.shape[:2]
    if h == target_h and w == target_w:
        return frame

    padded = np.zeros((target_h, target_w), dtype=np.uint8)
    y_start = max(0, (target_h - h) // 2)
    x_start = max(0, (target_w - w) // 2)

    crop_h = min(h, target_h)
    crop_w = min(w, target_w)

    padded[y_start : y_start + crop_h, x_start : x_start + crop_w] = frame[:crop_h, :crop_w]
    return padded


def export_frames_to_mp4(
    frames: list[np.ndarray],
    output_path: str,
    fps: float = 10.0,
    frame_duration: float = 0.1,
) -> None:
    """
    Encodes a list of 2D numpy arrays into an MP4 video file using direct stdin streaming.
    By default, each frame is displayed for 0.1 seconds (10 FPS).
    Ensures zero intermediate disk I/O.
    """
    if not frames:
        raise ValueError("Cannot export empty frame list to MP4")

    effective_fps = (1.0 / frame_duration) if frame_duration > 0 else fps

    # Determine uniform target dimensions (max width and max height across frames)
    # Ensure dimensions are even numbers (required by H.264 yuv420p)
    max_h = max(f.shape[0] for f in frames)
    max_w = max(f.shape[1] for f in frames)

    target_h = max_h if max_h % 2 == 0 else max_h + 1
    target_w = max_w if max_w % 2 == 0 else max_w + 1

    ffmpeg_bin = get_ffmpeg_executable()

    # ffmpeg command: read raw 8-bit grayscale from stdin, output H.264 MP4
    # -framerate sets each input frame duration to 0.1s (10 FPS)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{target_w}x{target_h}",
        "-pix_fmt", "gray",
        "-framerate", str(effective_fps),
        "-i", "-",  # Read from stdin
        "-r", str(effective_fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        output_path,
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for frame in frames:
        if frame.dtype != np.uint8:
            if frame.max() > 0:
                f8 = (frame / frame.max() * 255).astype(np.uint8)
            else:
                f8 = frame.astype(np.uint8)
        else:
            f8 = frame

        padded = pad_to_dimension(f8, target_h, target_w)
        process.stdin.write(padded.tobytes())

    _, stderr_data = process.communicate()

    if process.returncode != 0:
        err_msg = stderr_data.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg encoding failed with exit code {process.returncode}:\n{err_msg}")
