# 3D to 2D Planar Reslicing Algorithm

## 1. Overview
The algorithm extracts 2D cross-sectional slices from a 3D volumetric discrete grid $M$ (e.g., `.nrrd`) based on spatial coordinates:
* **3-Point Mode**: Isosceles triangle defined by apex $a$ and base vertices $b, c$.
* **4-Point Mode**: Isosceles trapezoid defined by top-base $a_1, a_2$ and bottom-base $b, c$.

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
Before processing a frame, coordinates are validated. Any failure triggers logging and yields a **black fallback image displaying the error text**, matching the **dimensions of the last successfully generated frame** (or $500 \times 500$ if the failure occurs on the first frame):

1. **Malformed CSV Data**: Non-numeric or missing coordinate values.
   * *Message*: `"ERROR: Malformed CSV line - invalid numerical coordinates"`
2. **Collinear Vertices**: All points lie along a single line ($\|(b-a) \times (c-a)\| < \epsilon$), spanning zero area.
   * *Message*: `"ERROR: Collinear vertices - cannot construct a 2D slicing plane"`
3. **Non-Isosceles Geometry**: Lateral legs are unequal ($|\text{dist}(a_1, b) - \text{dist}(a_2, c)| > \epsilon$).
   * *Message*: `"ERROR: Non-isosceles geometry - leg lengths must be equal"`

---

## 3. Algorithm Steps & Centering Mathematics

1. **Dimensions**:
   * Height: $H = \lceil \text{dist}(a_1, b) \rceil$ (where $a_1 = a$ for triangles).
   * Width: $W = \lceil \text{dist}(b, c) \rceil$.
   * Allocate output matrix $E$ of size $W \times H$, initialized to zeros.

2. **Leg Stepping Vectors**:
   * Unit step vectors: $\vec{v}_{ab} = \frac{b - a_1}{H}$ and $\vec{v}_{ac} = \frac{c - a_2}{H}$.

3. **Vertical Loop ($y = 0 \dots H-1$)**:
   * Endpoints of current scanline: $a_1$ and $a_2$.
   * Scanline width: $d_{12} = \text{dist}(a_1, a_2)$.
   * Scanline unit vector: $\vec{dp} = \frac{a_2 - a_1}{d_{12}}$ (if $d_{12} > 0$, else $\vec{0}$).

4. **Horizontal Centering Formula**:
   * Each scanline of width $d_{12}$ is centered inside canvas width $W = D_{bc}$:
     $$x = \left\lfloor \frac{D_{bc} - d_{12}}{2} \right\rfloor + x_1, \quad x_1 \in [0, \lfloor d_{12} \rfloor]$$
   * At the apex ($d_{12} \approx 0$), $x = W / 2$ (centered top).
   * At the base ($d_{12} = D_{bc}$), $x$ spans $[0, W]$ (full width).

5. **3D Sampling & Out-of-Bounds (Zero-Padding)**:
   * Continuous coordinate: $p = a_1 + x_1 \cdot \vec{dp}$.
   * Discrete voxel: $(i, j, k) = \text{round}(p)$.
   * If $(i, j, k)$ is within volume $M$, $E[x, y] = M[i, j, k]$; otherwise $E[x, y] = 0$.
   * Advance leg boundaries: $a_1 \leftarrow a_1 + \vec{v}_{ab}$, $a_2 \leftarrow a_2 + \vec{v}_{ac}$.

---

## 4. Pseudo-Code

```python
def reslice_plane(M, points, last_frame_dims=(500, 500)):
    # 1. Validation & Error Handling
    try:
        coords = [float(v) for v in points]
    except (ValueError, TypeError):
        return make_error_frame("ERROR: Malformed CSV line - invalid numerical coordinates", last_frame_dims)

    if len(coords) == 3:
        a, b, c = coords
        a1, a2 = copy(a), copy(a)
    elif len(coords) == 4:
        a1, a2, b, c = coords
    else:
        return make_error_frame("ERROR: Invalid point count", last_frame_dims)

    if are_collinear(coords):
        return make_error_frame("ERROR: Collinear vertices - cannot construct a 2D slicing plane", last_frame_dims)

    Dab, Dac, Dbc = dist(a1, b), dist(a2, c), dist(b, c)
    if abs(Dab - Dac) > EPSILON:
        return make_error_frame("ERROR: Non-isosceles geometry - leg lengths must be equal", last_frame_dims)

    # 2. Canvas & Stepping Initialization
    H, W = int(round(Dab)), int(round(Dbc))
    E = zeros((W, H), dtype=M.dtype)

    v_ab = (b - a1) / Dab if Dab > 0 else zeros(3)
    v_ac = (c - a2) / Dab if Dab > 0 else zeros(3)
    curr_a1, curr_a2 = copy(a1), copy(a2)

    # 3. Outer Vertical Loop (y from 0 to H)
    for y in range(H):
        d12 = dist(curr_a1, curr_a2)
        dp = (curr_a2 - curr_a1) / d12 if d12 > EPSILON else zeros(3)
        p = copy(curr_a1)
        scanline_len = int(round(d12))
        x_offset = int((W - scanline_len) // 2)

        # 4. Inner Horizontal Loop (x1 across scanline)
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
