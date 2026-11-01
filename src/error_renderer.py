"""
Module for rendering error fallback frames with descriptive text overlays using Pillow.
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def make_error_frame(message: str, frame_dims: tuple[int, int] = (500, 500)) -> np.ndarray:
    """
    Generates a black image of shape (height, width) with white error message text.

    Args:
        message: The error description string.
        frame_dims: Tuple of (height, width). Defaults to (500, 500).

    Returns:
        np.ndarray: 2D uint8 image array with overlaid error message.
    """
    h, w = frame_dims
    h = max(int(h), 50)
    w = max(int(w), 50)

    # Create grayscale Pillow image (mode 'L')
    img = Image.new("L", (w, h), color=0)
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    # Word wrap text to fit within canvas margins
    max_line_width = max(w - 40, 20)
    words = message.split()
    lines: list[str] = []
    current_line: list[str] = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_w = bbox[2] - bbox[0]
        if text_w > max_line_width and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))

    # Calculate vertical spacing
    line_spacing = 18
    total_height = len(lines) * line_spacing
    start_y = max(10, (h - total_height) // 2)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = max(10, (w - text_w) // 2)
        text_y = start_y + i * line_spacing
        if text_y < h - 5:
            draw.text((text_x, text_y), line, fill=255, font=font)

    return np.array(img, dtype=np.uint8)
