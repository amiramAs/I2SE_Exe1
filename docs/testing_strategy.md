# Black-Box Testing Strategy & Test Plan

## 1. Overview & Testing Philosophy

This document defines the **Black-Box Testing Strategy** for the 3D to 2D Volumetric Reslicing Engine. 

Under the black-box methodology, the system is evaluated strictly against its functional specification without relying on knowledge of internal implementation details. The test suite verifies that for every defined input state, the system produces the exact expected geometric, visual, and error handling outputs.

The strategy applies two formal specification-based testing techniques:
1. **Equivalence Partitioning (EP)**: Dividing input domains into classes of valid and invalid values where all members of a class are treated equivalently by the engine.
2. **Boundary Value Analysis (BVA)**: Focusing test cases on the extreme edges of input ranges where faults most frequently occur.

---

## 2. Equivalence Classes

### 2.1 Input Domain Partitioning

| Partition ID | Class Name | Description | Expected Output / Behavior |
| :--- | :--- | :--- | :--- |
| **EP-V1** | Valid 3-Point Triangle | Starts with `3` followed by 9 coordinates (10 tokens total), forming an isosceles triangle within $M$. | Output frame of size $\lceil D_{bc} \rceil \times \lceil D_{ab} \rceil$ with valid sampled pixel intensities. |
| **EP-V2** | Valid 4-Point Trapezoid | Starts with `4` followed by 12 coordinates (13 tokens total), forming an isosceles trapezoid with parallel bases within $M$. | Output frame of size $\lceil D_{bc} \rceil \times \lceil D_{ab} \rceil$ with valid centered pixel intensities. |
| **EP-V3** | Valid Completely Out-of-Bounds | Valid geometric coordinates located entirely outside $M$ (e.g. $z > 1000$). | Valid frame of size $W \times H$ filled entirely with zeros (`0`), **no error text**. |
| **EP-V4** | Empty Lines in CSV | Empty lines, blank spaces, or newline characters between valid rows. | **Silently skipped**; no frame or error is generated; process continues to next row. |
| **EP-I1** | Malformed CSV (Non-numeric) | CSV row containing non-numeric strings or unparseable tokens. | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I2** | Invalid Point / Token Count | Row starting with $N \notin \{3, 4\}$, or total tokens $\neq 1 + 3N$ (e.g. 7, 10, or 15 values). | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I3** | Degenerate / Coincident Points | Points with distance $< \text{EPS}$ ($\text{EPS} = 0.001$, $D_{ab} < 0.001$ or $D_{bc} < 0.001$). | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I4** | Collinear Vertices | Vertices all lying on a single straight line in 3D space (cross product norm $\le \text{EPS} = 0.001$). | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I5** | Non-Isosceles Geometry | Shape where lateral leg lengths differ beyond tolerance ($|D_{ab} - D_{ac}| > \text{EPS} = 0.001$). | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I6** | Non-Parallel Trapezoid Bases | 4-point shape where top base vector is not parallel to bottom base vector ($\|\hat{u}_{\text{top}} \times \hat{u}_{\text{bot}}\| > \text{EPS} = 0.001$). | Black error frame with dimensions of the last valid frame, labeled with error message. |
| **EP-I7** | First-Frame Error Fallback | An error occurring on the very first record of the CSV file. | Black error frame with default dimensions $500 \times 500$, labeled with error message. |

---

## 3. Boundary Value Analysis (BVA)

1. **Scanline Apex (Minimum $d_{12}$)**:
   * **Test**: At $y=0$ for a triangle, $d_{12} = 0$.
   * **Verification**: Probe samples single point at apex; centering offset evaluates to $x = \text{round}(W / 2)$; no zero-division or index crash occurs.
2. **Scanline Base (Maximum $d_{12}$)**:
   * **Test**: At $y=H-1$, $d_{12} \approx D_{bc}$.
   * **Verification**: Scanline spans from $x = 0$ to $x = W - 1$, exactly occupying the canvas width without exceeding array bounds ($x < W$).
3. **Volume Clamping Boundaries**:
   * **Test**: Sampling at exact coordinates $p = 0.0$ vs $p = -0.01$, and $p = \text{dim} - 1.0$ vs $p = \text{dim} + 0.01$.
   * **Verification**: Discrete integer rounding maps continuous coordinates to boundary indices safely, switching to zero-padding immediately outside limits.
4. **Distance & Geometric Tolerance Threshold ($\text{EPS} = 0.001$)**:
   * **Test**: Shapes where $|D_{ab} - D_{ac}| \le \text{EPS}$ ($\text{EPS} = 0.001$, accepted as valid isosceles) vs $|D_{ab} - D_{ac}| > \text{EPS}$ (rejected as non-isosceles).
5. **Throughput & Latency Performance Boundary ($\ge 100\text{ FPS}$)**:
   * **Test**: Slicing oblique planes across a full-scale $500 \times 500 \times 500$ 3D volume.
   * **Verification**: Average rendering rate must meet or exceed $100\text{ FPS}$ ($\le 10\text{ ms}$ per frame).

---

## 4. Test Case Specification Table

| Test Case ID | Category | Input Data / Precondition | Expected Output / Assertion |
| :--- | :--- | :--- | :--- |
| **TC-01** | EP-V1 | `3, 0,0,0, 0,10,0, 10,10,0` (Triangle, $D_{ab}=10, D_{bc}=10$) | Frame shape $(10, 10)$, non-zero pixels inside triangle, zero outside. |
| **TC-02** | EP-V2 | `4, 2,0,0, 8,0,0, 0,10,0, 10,10,0` (Trapezoid, parallel bases) | Frame shape $(10, 10)$, symmetrically centered slice. |
| **TC-03** | EP-V3 | `3, 1000,1000,1000, 1000,1010,1000, 1010,1010,1000` | Frame shape $(10, 10)$, array is all zeros (`np.all(E == 0)`), no error text. |
| **TC-04** | EP-V4 | Valid row followed by `\n` (empty line) and another valid row | Exactly 2 video frames generated; empty row skipped without error. |
| **TC-05** | EP-I1 | `"3, 10, 20, foo, 40, 50, 60, 70, 80, 90"` | Black frame, shape matching previous frame, text: `"ERROR: Malformed CSV line..."`. |
| **TC-06** | EP-I2 | `"5, 1, 2, 3, 4, 5, 6, 7"` (Invalid point count 5 and 8 values) | Black frame, shape matching previous frame, text: `"ERROR: Invalid CSV format..."`. |
| **TC-07** | EP-I3 | `3, 5,5,5, 5,5,5, 10,10,10` ($a=b \implies D_{ab}=0 < \text{EPS}$) | Black frame, shape matching previous frame, text: `"ERROR: Degenerate geometry..."`. |
| **TC-08** | EP-I4 | `3, 0,0,0, 5,5,5, 10,10,10` (Collinear points) | Black frame, shape matching previous frame, text: `"ERROR: Collinear vertices..."`. |
| **TC-09** | EP-I5 | `3, 0,0,0, 0,10,0, 15,20,0` ($|D_{ab} - D_{ac}| > \text{EPS}$) | Black frame, shape matching previous frame, text: `"ERROR: Non-isosceles geometry..."`. |
| **TC-10** | EP-I6 | `4, 0,0,0, 5,0,0, 0,10,0, 5,15,0` (Non-parallel bases) | Black frame, shape matching previous frame, text: `"ERROR: Non-parallel trapezoid bases..."`. |
| **TC-11** | EP-I7 | First CSV row has malformed text (no prior frame exists) | Error frame generated with dimensions exactly $(500, 500)$. |
| **TC-12** | BVA | Continuous coordinates with decimal fractions (e.g. `12.6, 44.4`) | Correct nearest-integer rounding, no index out of bounds ($0 \le x < W$). |
| **TC-13** | BVA (`EPS`) | Isosceles leg difference within $\text{EPS} = 0.001$ vs exceeding $\text{EPS} = 0.001$ | Accepted (`True`) when $|D_{ab} - D_{ac}| \le 0.001$; rejected (`False`) when $> 0.001$. |
| **TC-14** | Performance | Rendering 30 oblique slices ($559 \times 500$) across a $500 \times 500 \times 500$ volume | Measured throughput $\ge 100\text{ FPS}$ ($\le 10\text{ ms}$ per frame). |

---

---

## 5. End-to-End CLI Demo Verification (`Ex0.py`)

In accordance with course requirements, the application must provide an executable CLI demo entry point:
```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```
* `<file.nrrd>`: 3D volumetric data file in NRRD format.
* `<file.csv>`: Sequence of 3-point or 4-point slice definitions.
* `<file.mp4>`: Output video file containing a frame for each plane coordinate in the CSV (in exact list order).

### 5.1 CLI Integration Test Cases

| Test ID | Category | CLI Invocation & Conditions | Expected Output / Assertion |
| :--- | :--- | :--- | :--- |
| **TC-CLI-01** | Full E2E Flow | `python Ex0.py data/onion.nrrd trajectory.csv output.mp4` | Exit code `0`; `output.mp4` created; frame count equals valid CSV rows. |
| **TC-CLI-02** | Argument Count | `python Ex0.py data/onion.nrrd` (Missing CSV and MP4) | Exit code $\ne 0$; descriptive usage syntax printed to `stderr`. |
| **TC-CLI-03** | Missing Volume | `python Ex0.py non_existent.nrrd file.csv output.mp4` | Exit code $\ne 0$; clean error message (no unhandled stack trace). |
| **TC-CLI-04** | Missing CSV | `python Ex0.py data/onion.nrrd non_existent.csv output.mp4` | Exit code $\ne 0$; clean error message. |
| **TC-CLI-05** | Video Validity | Verify generated `.mp4` using `cv2.VideoCapture` / `ffprobe` | Valid H.264 video header, non-zero file size, correct FPS and duration. |
| **TC-CLI-06** | Frame Sequence | CSV with mixed valid slices and error lines | Output video preserves exact 1:1 order (valid slices + error frames). |

---

## 6. Test Execution & Reporting

All test cases are implemented using the `pytest` automated framework:
* **Engine Tests**: `tests/test_reslicing_blackbox.py` (Fast, in-memory synthetic volumes and $500^3$ performance benchmarks for TC-01 to TC-14).
* **CLI Demo Tests**: `tests/test_demo_cli.py` (Subprocess invocations testing `Ex0.py` for TC-CLI-01 to TC-CLI-06).
* All tests run in continuous integration without requiring GUI display or interactive user intervention.

