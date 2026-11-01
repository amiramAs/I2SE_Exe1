"""
CLI Demo Entry Point:
Usage: python Ex0.py <file.nrrd> <file.csv> <file.mp4>
"""
from __future__ import annotations
import sys
import os
import numpy as np

from src.volume_io import VolumeData
from src.csv_parser import parse_csv_file
from src.reslicer import reslice_plane
from src.error_renderer import make_error_frame
from src.video_streamer import export_frames_to_mp4


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python Ex0.py <file.nrrd> <file.csv> <file.mp4>", file=sys.stderr)
        return 1

    nrrd_path = sys.argv[1]
    csv_path = sys.argv[2]
    mp4_path = sys.argv[3]

    if not os.path.exists(nrrd_path):
        print(f"ERROR: NRRD volume file not found: {nrrd_path}", file=sys.stderr)
        return 1

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV trajectory file not found: {csv_path}", file=sys.stderr)
        return 1

    print(f"Loading 3D volume from '{nrrd_path}'...")
    try:
        volume = VolumeData.from_file(nrrd_path)
    except Exception as e:
        print(f"ERROR: Failed to load NRRD file: {e}", file=sys.stderr)
        return 1

    print(f"Volume loaded successfully. Dimensions: {volume.shape}, dtype: {volume.dtype}")

    print(f"Parsing CSV trajectory from '{csv_path}'...")
    try:
        records = parse_csv_file(csv_path)
    except Exception as e:
        print(f"ERROR: Failed to parse CSV file: {e}", file=sys.stderr)
        return 1

    print(f"Found {len(records)} trajectory records to process.")

    frames: list[np.ndarray] = []
    last_valid_dims: tuple[int, int] = (500, 500)

    for idx, rec in enumerate(records, start=1):
        if rec.is_error:
            print(f"  Frame {idx}: Handling CSV error '{rec.error_message}'")
            frame = make_error_frame(rec.error_message or "ERROR: Invalid data", last_valid_dims)
        else:
            frame = reslice_plane(volume, rec.points, last_frame_dims=last_valid_dims)
            # Check if frame returned is an error frame
            if hasattr(frame, 'dtype') and frame.dtype == np.uint8 and np.all(frame == 0):
                # Valid blank frame or normal slice
                pass

        # Update last valid dimensions if this was a successful slice
        if not rec.is_error and frame.shape != (500, 500):
            last_valid_dims = (frame.shape[0], frame.shape[1])

        frames.append(frame)

    if not frames:
        print("WARNING: No valid frames generated.", file=sys.stderr)
        return 0

    print(f"Exporting {len(frames)} frames directly to '{mp4_path}' via ffmpeg...")
    try:
        export_frames_to_mp4(frames, mp4_path, fps=10)
        print(f"SUCCESS: Video exported to '{mp4_path}'.")
    except Exception as e:
        print(f"ERROR: Failed to export video: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
