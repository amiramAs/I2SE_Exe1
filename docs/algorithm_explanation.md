# 3D to 2D Planar Reslicing Algorithm

## 1. Overview
The algorithm extracts 2D cross-sectional slices from a 3D volumetric discrete grid $M$ (e.g., `.nrrd`) based on spatial coordinates:
* **3-Point Mode**: Isosceles triangle defined by apex $a \in \mathbb{R}^3$ and base vertices $b, c \in \mathbb{R}^3$.
* **4-Point Mode**: Isosceles trapezoid defined by top-base $a_1, a_2 \in \mathbb{R}^3$ and bottom-base $b, c \in \mathbb{R}^3$.

Output canvas $E$ has dimensions $\lceil D_{ab} \rceil \times \lceil D_{bc} \rceil$ (Height $\times$ Width). Each horizontal scanline is centered on the canvas to preserve bilateral symmetry.

```
       3-Point (Triangle)                     4-Point (Trapezoid)
               a                                    a1 ─── a2   (Top Base)
              / \                                   /       \
             /   \  v(ac)                          /         \
     v(ab)  /  y  \                               /     y     \
           /       \                             /             \
          b ─────── c                           b ───────────── c
            (Base)                                (Bottom Base)
```

---

## 2. Validation & Error Handling

### 2.1 CSV Row Ingestion Rules
* **Row Format**: The first column specifies the point count $N \in \{3, 4\}$, followed by sequential 3D coordinates $(x, y, z)$ for each vertex:
  * **3 Points**: `3, x1, y1, z1, x2, y2, z2, x3, y3, z3` (Total 10 columns: $a, b, c$).
  * **4 Points**: `4, x1, y1, z1, x2, y2, z2, x3, y3, z3, x4, y4, z4` (Total 13 columns: $a_1, a_2, b, c$).
* **Empty Lines**: Any empty or whitespace-only lines in the CSV are silently skipped without generating an error frame.
* **Token Count & Point Identifier**:
  * The first value must parse as integer `3` or `4`.
  * For $N=3$, the row must contain exactly 10 values.
  * For $N=4$, the row must contain exactly 13 values.
  * Any other count or unsupported point identifier raises an error.

### 2.2 Error Fallback Frames
When geometric or parsing validation fails, processing for that frame halts and the algorithm yields a **black fallback image displaying the error text**, matching the **dimensions of the last successfully generated frame** (or $500 \times 500$ if the failure occurs on the first frame):

1. **Malformed CSV Data**: Non-numeric or missing coordinate values.
   * *Message*: `"ERROR: Malformed CSV line - invalid numerical coordinates"`
2. **Invalid Point Count or Token Count**: Row does not start with 3 or 4, or does not match expected length (10 or 13 values).
   * *Message*: `"ERROR: Invalid CSV format - expected 3 (10 values) or 4 (13 values)"`
3. **Degenerate Geometry / Zero Distance (Division by 0)**: Coincident vertices where $D_{ab} < \epsilon$ or $D_{bc} < \epsilon$.
   * *Message*: `"ERROR: Degenerate geometry - zero distance between vertices"`
4. **Collinear Vertices**: All points lie along a single linear segment ($\|(b-a) \times (c-a)\| < \epsilon$), spanning zero 2D area.
   * *Message*: `"ERROR: Collinear vertices - cannot construct a 2D slicing plane"`
5. **Non-Isosceles Geometry**: Lateral legs are unequal ($|\text{dist}(a_1, b) - \text{dist}(a_2, c)| > \epsilon$).
   * *Message*: `"ERROR: Non-isosceles geometry - leg lengths must be equal"`
6. **Non-Parallel Trapezoid Bases (4-Point Mode)**: Top base $(a_2 - a_1)$ is not parallel to bottom base $(c - b)$ within angular tolerance.
   * *Message*: `"ERROR: Non-parallel trapezoid bases - top and bottom must be parallel"`

### 2.3 Non-Error Edge Case: Completely Out-of-Bounds Slicing
If a geometrically valid plane lies entirely outside the 3D volume boundaries (e.g. far negative or positive coordinates), this is **not an error**. The algorithm outputs a valid, blank frame filled entirely with `0` (black) **without any error text**.

---

## 3. Algorithm Steps & Centering Mathematics

1. **Dimensions**:
   * Height: $H = \lceil \text{dist}(a_1, b) \rceil$ (where $a_1 = a$ for triangles).
   * Width: $W = \lceil \text{dist}(b, c) \rceil$.
   * Allocate output matrix $E$ of size $W \times H$, initialized to zeros.

2. **Leg Stepping Vectors**:
   * Unit step vectors: $\vec{v}_{ab} = \frac{b - a_1}{H}$ and $\vec{v}_{ac} = \frac{c - a_2}{H}$.

3. **Vertical Loop ($y = 0 \dots H-1$)**:
   * Current scanline endpoints: $a_1$ and $a_2$.
   * Scanline width: $d_{12} = \text{dist}(a_1, a_2)$.
   * Scanline unit vector: $\vec{dp} = \frac{a_2 - a_1}{d_{12}}$ (if $d_{12} > 0$, else $\vec{0}$).

4. **Horizontal Centering Formula & Pixel Rounding**:
   * Each scanline of width $d_{12}$ is centered inside canvas width $W = D_{bc}$:
     $$x = \text{round}\left(\frac{D_{bc} - d_{12}}{2}\right) + x_1, \quad x_1 \in [0, \lfloor d_{12} \rfloor]$$
   * At apex ($d_{12} \approx 0$), $x = \text{round}(W / 2)$ (centered top).
   * At base ($d_{12} = D_{bc}$), $x$ spans $[0, W-1]$.
   * Safety guard: Pixel column is clamped to canvas limits: $0 \le x < W$.

5. **3D Sampling & Out-of-Bounds (Zero-Padding)**:
   * Continuous coordinate: $p = a_1 + x_1 \cdot \vec{dp}$.
   * Discrete voxel: $(i, j, k) = (\text{round}(p_x), \text{round}(p_y), \text{round}(p_z))$.
   * If $(i, j, k)$ is within volume $M$, $E[x, y] = M[i, j, k]$; otherwise $E[x, y] = 0$.
   * Advance leg boundaries: $a_1 \leftarrow a_1 + \vec{v}_{ab}$, $a_2 \leftarrow a_2 + \vec{v}_{ac}$.

---

## 4. Pseudo-Code

```python
def reslice_plane(M, raw_line, last_frame_dims=(500, 500)):
    # 0. Skip empty lines
    line = raw_line.strip()
    if not line:
        return None  # Silently skip

    # 1. Parse & validate token count
    tokens = [t.strip() for t in line.split(',') if t.strip()]
    if not tokens:
        return None

    try:
        point_count = int(tokens[0])
    except ValueError:
        return make_error_frame("ERROR: Malformed CSV line - invalid numerical coordinates", last_frame_dims)

    if point_count not in (3, 4):
        return make_error_frame("ERROR: Invalid CSV format - expected 3 (10 values) or 4 (13 values)", last_frame_dims)

    expected_len = 10 if point_count == 3 else 13
    if len(tokens) != expected_len:
        return make_error_frame("ERROR: Invalid CSV format - expected 3 (10 values) or 4 (13 values)", last_frame_dims)

    try:
        coords = [float(v) for v in tokens[1:]]
    except ValueError:
        return make_error_frame("ERROR: Malformed CSV line - invalid numerical coordinates", last_frame_dims)

    # 2. Extract points
    if point_count == 3:
        a = array(coords[0:3])
        b = array(coords[3:6])
        c = array(coords[6:9])
        a1, a2 = copy(a), copy(a)
    else:  # point_count == 4
        a1 = array(coords[0:3])
        a2 = array(coords[3:6])
        b = array(coords[6:9])
        c = array(coords[9:12])

        # Validate parallel bases for trapezoid
        top_base = a2 - a1
        bottom_base = c - b
        if norm(cross(top_base, bottom_base)) > EPSILON * norm(top_base) * norm(bottom_base):
            return make_error_frame("ERROR: Non-parallel trapezoid bases - top and bottom must be parallel", last_frame_dims)

    # 3. Geometric validations
    if are_collinear([a1, a2, b, c] if len(coords) == 12 else [a, b, c]):
        return make_error_frame("ERROR: Collinear vertices - cannot construct a 2D slicing plane", last_frame_dims)

    Dab = dist(a1, b)
    Dac = dist(a2, c)
    Dbc = dist(b, c)

    # Prevent division by zero
    if Dab < EPSILON or Dbc < EPSILON:
        return make_error_frame("ERROR: Degenerate geometry - zero distance between vertices", last_frame_dims)

    # Validate isosceles property
    if abs(Dab - Dac) > EPSILON:
        return make_error_frame("ERROR: Non-isosceles geometry - leg lengths must be equal", last_frame_dims)

    # 4. Canvas & stepping initialization
    H, W = int(round(Dab)), int(round(Dbc))
    E = zeros((W, H), dtype=M.dtype)

    v_ab = (b - a1) / Dab
    v_ac = (c - a2) / Dab
    curr_a1, curr_a2 = copy(a1), copy(a2)

    # 5. Outer Vertical Loop (y from 0 to H-1)
    for y in range(H):
        d12 = dist(curr_a1, curr_a2)
        dp = (curr_a2 - curr_a1) / d12 if d12 > EPSILON else zeros(3)
        p = copy(curr_a1)
        scanline_len = int(round(d12))
        x_offset = int(round((W - scanline_len) / 2.0))

        # 6. Inner Horizontal Loop (x1 across scanline)
        for x1 in range(scanline_len + 1):
            x = x_offset + x1
            if 0 <= x < W:
                ix, iy, iz = int(round(p[0])), int(round(p[1])), int(round(p[2]))
                if 0 <= ix < M.shape[0] and 0 <= iy < M.shape[1] and 0 <= iz < M.shape[2]:
                    E[x, y] = M[ix, iy, iz]
                else:
                    E[x, y] = 0  # Out-of-bounds zero padding
            p = p + dp

        curr_a1 += v_ab
        curr_a2 += v_ac

    return E
```
