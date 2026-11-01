"""
CSV trajectory file parser with validation, header detection, and error diagnostics.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class ParsedRecord:
    is_skipped: bool = False
    is_error: bool = False
    error_message: str | None = None
    point_count: int = 0
    points: list[np.ndarray] | None = None
    raw_line: str = ""
    line_number: int = 0


def parse_csv_line(line: str, line_number: int = 0) -> ParsedRecord:
    """
    Parses a single line from the CSV trajectory file.

    Rules:
    - Empty or whitespace-only lines are skipped.
    - If ALL non-empty tokens are non-numeric strings, it is treated as a Header line and skipped.
    - If some tokens are numeric and others are invalid non-numeric strings, a Malformed error is flagged.
    - First column must indicate point count N in (3, 4).
    - Trailing empty commas are stripped.
    - Exactly 10 tokens for 3 points, exactly 13 tokens for 4 points.
    """
    raw_stripped = line.strip()
    if not raw_stripped:
        return ParsedRecord(is_skipped=True, raw_line=line, line_number=line_number)

    # Split by comma
    tokens = [t.strip() for t in raw_stripped.split(',')]

    # Strip empty tokens from the right (e.g. trailing commas ',,,')
    while tokens and tokens[-1] == '':
        tokens.pop()

    if not tokens:
        return ParsedRecord(is_skipped=True, raw_line=line, line_number=line_number)

    # Check if ALL cells are non-numeric strings -> Header row
    all_non_numeric = True
    any_numeric = False
    for t in tokens:
        try:
            float(t)
            all_non_numeric = False
            any_numeric = True
        except ValueError:
            pass

    if all_non_numeric:
        # Identified as header row -> silently skip
        return ParsedRecord(is_skipped=True, raw_line=line, line_number=line_number)

    # If we have a mix of non-numeric tokens that cannot be converted to floats
    # Check if any token fails float conversion
    try:
        numeric_vals = [float(t) for t in tokens]
    except ValueError:
        return ParsedRecord(
            is_error=True,
            error_message="ERROR: Malformed CSV line - invalid numerical coordinates",
            raw_line=line,
            line_number=line_number,
        )

    # First value is point count (3 or 4)
    point_count_raw = numeric_vals[0]
    if not point_count_raw.is_integer() or int(point_count_raw) not in (3, 4):
        return ParsedRecord(
            is_error=True,
            error_message="ERROR: Invalid CSV format - expected 3 (10 values) or 4 (13 values)",
            raw_line=line,
            line_number=line_number,
        )

    point_count = int(point_count_raw)
    expected_len = 1 + (point_count * 3)

    if len(numeric_vals) != expected_len:
        return ParsedRecord(
            is_error=True,
            error_message="ERROR: Invalid CSV format - expected 3 (10 values) or 4 (13 values)",
            raw_line=line,
            line_number=line_number,
        )

    coords = numeric_vals[1:]
    points: list[np.ndarray] = []
    for i in range(point_count):
        pt = np.array(coords[i * 3 : (i + 1) * 3], dtype=np.float64)
        points.append(pt)

    return ParsedRecord(
        is_skipped=False,
        is_error=False,
        point_count=point_count,
        points=points,
        raw_line=line,
        line_number=line_number,
    )


def parse_csv_file(file_path: str) -> list[ParsedRecord]:
    """Reads and parses an entire CSV file into a list of ParsedRecords."""
    records: list[ParsedRecord] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, start=1):
            record = parse_csv_line(line, line_number=idx)
            if not record.is_skipped:
                records.append(record)
    return records
