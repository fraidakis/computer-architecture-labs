# V2 Complete Guide: Chunk-Level Sliding Window Architecture

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Stage 2: Filter Loop with Sliding Window](#stage-2-filter-loop-with-sliding-window)
4. [Top-Level Function: IMAGE_DIFF_POSTERIZE](#top-level-function-image_diff_posterize)
5. [Key Takeaways](#key-takeaways)
6. [Filter Loop Deep Dive](#filter-loop-deep-dive)
7. [Step-by-Step Execution Trace](#step-by-step-execution-trace)

---

# Part 1: V2 Architecture Guide

## Overview

**Version 2** implements a **Chunk-Level Sequential** architecture that processes **64 pixels per clock cycle**. Unlike V1 which streams individual pixels, V2:

- **Processes 512-bit chunks** (64 pixels at a time) through processing stages
- Uses **chunk-level line buffers** (2 rows of 512-bit chunks instead of pixel arrays)
- Operates with a **3×3 chunk sliding window** for the filter stage
- Targets **64 pixels per clock cycle (II=1)** throughput

### Key Performance Characteristics

| Metric | V1 (Pixel Streaming) | V2 (Chunk Processing) |
|--------|----------------------|----------------------|
| Processing Width | 1 pixel/cycle | 64 pixels/cycle |
| Data Type | `pixel_t` streams | `uint512_t` chunks |
| Filter Window | 3×3 pixels | 3×3 chunks |
| Stage Execution | Dataflow (overlapped) | Sequential |

---

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DDR Memory     │     │  DDR Memory     │     │  DDR Memory     │
│  (Image A)      │     │  (Image B)      │     │  (Output C)     │
└────────┬────────┘     └────────┬────────┘     └────────▲────────┘
         │ AXI Master            │ AXI Master            │ AXI Master
         │ (gmemA)               │ (gmemB)               │ (gmemC)
         │                       │                       │
         ▼                       ▼                       │
┌────────────────────────────────────────┐               │
│     STAGE 1: Posterize_Loop            │               │
│  ┌───────────────────────────────────┐ │               │
│  │ Read 512-bit A[i], B[i]           │ │               │
│  │ Process 64 pixels in parallel     │ │               │
│  │ Compute |A-B| → Posterize         │ │               │
│  │ Store to C_tmp[i] (uint512_t)     │ │               │
│  └───────────────────────────────────┘ │               │
└──────────────────┬─────────────────────┘               │
                   │ C_tmp[TOTAL_CHUNKS] (BRAM)          │
                   ▼                                     │
┌─────────────────────────────────────────┐              │
│        STAGE 2: Filter_Loop             │              │
│  ┌────────────────────────────────────┐ │              │
│  │ Line Buffers: lb[2][CHUNKS_PER_ROW]│ │              │
│  │ Window: win[3][3] (512-bit chunks) │ │              │
│  │ Process 64 pixels per iteration    │ │              │
│  └────────────────────────────────────┘ │              │
└──────────────────┬──────────────────────┘              │
                   │ C_filt[TOTAL_CHUNKS] (BRAM)         │
                   ▼                                     │
┌────────────────────────────────────────┐               │
│        STAGE 3: Write_Loop             │               │
│  ┌───────────────────────────────────┐ │               │
│  │ Write C_filt[i] to DDR            │─┴───────────────┘
│  │ (512-bit burst writes)            │
│  └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

## Stage 2: Filter Loop with Sliding Window

**Purpose:** Applies a 3×3 sharpening filter using **chunk-level** line buffers and sliding window.

### Local Buffer Declaration

```cpp
static uint512_t C_tmp[TOTAL_CHUNKS];   // Posterized difference
static uint512_t C_filt[TOTAL_CHUNKS];  // Filtered result
```

| Buffer | Contents |
|--------|----------|
| `C_tmp[i]` | 512-bit chunk containing 64 posterized pixels |
| `C_filt[i]` | 512-bit chunk containing 64 filtered pixels |

### Line Buffer Declaration

```cpp
uint512_t lb[2][CHUNKS_PER_ROW];
#pragma HLS ARRAY_PARTITION variable=lb complete dim=1
```

#### What are Chunk-Level Line Buffers?

Instead of storing individual pixels, V2 stores **512-bit chunks**. For a 256-pixel wide image with 64 pixels per chunk:
- `CHUNKS_PER_ROW = 256 / 64 = 4` chunks per row
- Line buffer stores 2 rows × 4 chunks = 8 chunks total

```
          ┌───────────────────────────────────────────────────┐
Row r-2:  │ lb[0][0]   lb[0][1]   lb[0][2]   lb[0][3]         │  ← Oldest row (4 chunks)
          ├───────────────────────────────────────────────────┤
Row r-1:  │ lb[1][0]   lb[1][1]   lb[1][2]   lb[1][3]         │  ← Previous row
          ├───────────────────────────────────────────────────┤
Row r:    │            (incoming chunks)                      │  ← Current row
          └───────────────────────────────────────────────────┘
```

#### `#pragma HLS ARRAY_PARTITION variable=lb complete dim=1`

| Part | Meaning |
|------|---------|
| `ARRAY_PARTITION` | Splits array into separate memory elements |
| `variable=lb` | Applies to the `lb` array |
| `complete` | Fully partition (individual registers) |
| `dim=1` | Partition the first dimension (the 2 rows) |

**Effect:** `lb[0][...]` and `lb[1][...]` become separate memory banks, allowing simultaneous access to both rows of chunks.

### Window Declaration

```cpp
uint512_t win[3][3];
#pragma HLS ARRAY_PARTITION variable=win complete dim=0
```

The 3×3 window holds **512-bit chunks** (not individual pixels):

| Part | Meaning |
|------|---------|
| `dim=0` | Partition ALL dimensions completely |

**Effect:** All 9 chunks become individual registers, enabling parallel access to all 9 × 64 = 576 pixels in a single clock cycle.

### Extended Loop for Pipeline Latency

```cpp
const int LOOP_LIMIT = TOTAL_CHUNKS + CHUNKS_PER_ROW + 1;

Filter_Loop:
for (int iter = 0; iter < LOOP_LIMIT; iter++)
{
    #pragma HLS PIPELINE II=1
```

#### Why `TOTAL_CHUNKS + CHUNKS_PER_ROW + 1` iterations?

The filter has **latency** because we need data from the next row before we can compute the current output:

```
To compute output chunk at:  (row r, chunk c)
We need input chunk at:      (row r+1, chunk c+1)
Latency =                    CHUNKS_PER_ROW + 1 chunks
```

| Phase | Iteration Range | Description |
|-------|-----------------|-------------|
| Fill | [0, CHUNKS_PER_ROW] | Reading first row, filling line buffers |
| Compute | [CHUNKS_PER_ROW+1, TOTAL_CHUNKS-1] | Normal operation |
| Drain | [TOTAL_CHUNKS, TOTAL_CHUNKS+CHUNKS_PER_ROW] | No new input, flush remaining outputs |

### Window Update - Read Phase

```cpp
uint512_t new_chunk = 0;
if (iter < TOTAL_CHUNKS)
{
    new_chunk = C_tmp[iter];
}

// Shift Window Left
for (int r = 0; r < 3; r++) {
#pragma HLS UNROLL
    win[r][0] = win[r][1];
    win[r][1] = win[r][2];
}

// Update Right Column from Line Buffers
int col_idx = iter % CHUNKS_PER_ROW;

if (iter < TOTAL_CHUNKS)
{
    win[0][2] = lb[0][col_idx];  // Oldest row chunk
    win[1][2] = lb[1][col_idx];  // Middle row chunk
    win[2][2] = new_chunk;       // Current row chunk

    // Update Line Buffers (Shift up)
    lb[0][col_idx] = lb[1][col_idx];
    lb[1][col_idx] = new_chunk;
}
```

#### Sliding Window Operation (Chunk-Level)

```
Before:                              After:
┌─────┬─────┬─────┐                          ┌─────┬─────┬─────┐
│ A64 │ B64 │ C64 │  ←shift left──────→      │ B64 │ C64 │ X64 │
├─────┼─────┼─────┤                          ├─────┼─────┼─────┤
│ D64 │ E64 │ F64 │  ←shift left──────→      │ E64 │ F64 │ Y64 │
├─────┼─────┼─────┤                          ├─────┼─────┼─────┤
│ G64 │ H64 │ I64 │  ←shift left──────→      │ H64 │ I64 │ Z64 │
└─────┴─────┴─────┘                          └─────┴─────┴─────┘
              X64 = lb[0][col_idx] (64 pixels)
              Y64 = lb[1][col_idx] (64 pixels)
              Z64 = new_chunk (64 pixels just read)
```

### Window Update - Drain Phase

```cpp
else
{
    // Drain phase: zero padding
    win[0][2] = 0;
    win[1][2] = 0;
    win[2][2] = 0;
}
```

During drain phase, no new chunks are read. The window fills with zeros to flush remaining outputs.

---

## Top-Level Function: IMAGE_DIFF_POSTERIZE

**Purpose:** Top-level synthesis entry point. Declares interfaces and executes stages **sequentially**.

### Interface Pragmas

```cpp
#pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmemA depth=TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmemB depth=TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmemC depth=TOTAL_CHUNKS
#pragma HLS INTERFACE s_axilite port=return bundle=control
```

| Part | Meaning |
|------|---------|
| `m_axi` | AXI4 Master interface for DDR access |
| `bundle=gmemA/B/C` | Separate memory ports for concurrent access |
| `depth=TOTAL_CHUNKS` | Memory depth hint for co-simulation |
| `s_axilite` | AXI4-Lite for control signals |

### Stage Execution

```cpp
// STAGE 1: Posterized absolute difference
Posterize_Loop:
for (int i = 0; i < TOTAL_CHUNKS; i++) { ... }

// STAGE 2: 3×3 sharpen filter with sliding window
Filter_Loop:
for (int iter = 0; iter < LOOP_LIMIT; iter++) { ... }

// STAGE 3: Write output to DDR
Write_Loop:
for (int i = 0; i < TOTAL_CHUNKS; i++) { ... }
```

> **Note:** V2 executes stages **sequentially** (not concurrently). For overlapped execution with dataflow streaming, see **V3** in [versions.md](versions.md).

---

## Key Takeaways

1. **Chunk-level processing** achieves 64 pixels/cycle throughput
2. **512-bit line buffers** enable 3×3 filter with 2 rows of chunks
3. **Sequential stages** with BRAM intermediates (simpler than dataflow)
4. **II=1 pipelining** in all loops for maximum throughput
5. **Separate AXI bundles** maximize memory bandwidth

---

# Part 2: Filter Loop Deep Dive

A detailed explanation of the **chunk-level 2D convolution** implementation with a **3×3 sliding window of 512-bit chunks**.

## What It Computes

The function applies a **sharpen kernel** that only uses the cross neighbors (no diagonals):

```
Filter Kernel (K):
┌────┬────┬────┐
│  0 │ -1 │  0 │
├────┼────┼────┤
│ -1 │  5 │ -1 │
├────┼────┼────┤
│  0 │ -1 │  0 │
└────┴────┴────┘
```

### Formula

For a non-border pixel at position `(r, c)`:

```cpp
out(r, c) = clip( 5 * x(r, c) 
                  - x(r-1, c)    // North
                  - x(r+1, c)    // South
                  - x(r, c-1)    // West
                  - x(r, c+1) )  // East
```

> **Border Policy:** All border pixels are forced to `0`.

---

## Why Line Buffers + Window

### The Sequential Constraint

Chunks are read **one per cycle** from `C_tmp[]` in raster order (row-major). A 3×3 filter on 64-pixel chunks needs access to:

- The **current row** of chunks
- The **previous row** of chunks
- The **row before that** of chunks

Since filter computation requires vertical neighbors, you must store the last two rows of chunks in on-chip memory.

### Memory Layout

```
                    Chunk-Level Line Buffers Storage
     ┌─────────────────────────────────────────────────┐
     │  lb[0][c] = 512-bit chunk from 2 rows ago       │
     │  lb[1][c] = 512-bit chunk from 1 row ago        │
     └─────────────────────────────────────────────────┘
                            │
                            ▼
     ┌─────────────────────────────────────────────────┐
     │         3×3 Sliding Window of Chunks            │
     │  win[row][col] = 9 chunks (576 pixels total)    │
     └─────────────────────────────────────────────────┘
```

| Buffer | Contents |
|--------|----------|
| `lb[0][c]` | 512-bit chunk from **row r-2**, chunk column `c` |
| `lb[1][c]` | 512-bit chunk from **row r-1**, chunk column `c` |
| `win[3][3]` | Current 3×3 chunk neighborhood (9 × 64 = 576 pixels) |

---

## Per-Cycle Update Steps

For each loop iteration `iter` (reading chunk index `iter` where `iter < TOTAL_CHUNKS`):

### Step 1: Read New Chunk

```cpp
uint512_t new_chunk = C_tmp[iter];  // 64 pixels at once
```

### Step 2: Shift Window Left

```cpp
for (int r = 0; r < 3; r++) {
#pragma HLS UNROLL
    win[r][0] = win[r][1];
    win[r][1] = win[r][2];
}
```

```
Before Shift:                  After Shift:
┌────┬────┬────┐                 ┌────┬────┬────┐
│ A64│ B64│ C64│   ──────▶      │ B64│ C64│  ? │
├────┼────┼────┤                 ├────┼────┼────┤
│ D64│ E64│ F64│   ──────▶      │ E64│ F64│  ? │
├────┼────┼────┤                 ├────┼────┼────┤
│ G64│ H64│ I64│   ──────▶      │ H64│ I64│  ? │
└────┴────┴────┘                 └────┴────┴────┘
```

### Step 3: Fill Right Column

```cpp
int col_idx = iter % CHUNKS_PER_ROW;
win[0][2] = lb[0][col_idx];  // Row r-2 chunk
win[1][2] = lb[1][col_idx];  // Row r-1 chunk
win[2][2] = new_chunk;       // Row r chunk (just read)
```

### Step 4: Update Line Buffers (Shift Rows Up)

```cpp
lb[0][col_idx] = lb[1][col_idx];  // Row r-1 becomes "old"
lb[1][col_idx] = new_chunk;       // Current chunk goes to r-1 position
```

This prepares the line buffers for the **next time we visit this chunk column** (i.e., next row).

---

## The Key Indexing: `out_idx = iter - (CHUNKS_PER_ROW + 1)`

### Understanding Output Lag

After reading chunk `iter` at coordinates:
- `r_in = iter / CHUNKS_PER_ROW`
- `c_in = iter % CHUNKS_PER_ROW`

The **center** of the 3×3 window is at:
- Chunk Row: `r_in - 1`
- Chunk Column: `c_in - 1`

This center corresponds to `win[1][1]`.

### Linear Index Derivation

```
out_idx = (r_in - 1) * CHUNKS_PER_ROW + (c_in - 1)
        = (r_in * CHUNKS_PER_ROW + c_in) - (CHUNKS_PER_ROW + 1)
        = iter - (CHUNKS_PER_ROW + 1)
```

The output **lags** the input by exactly `CHUNKS_PER_ROW + 1` chunks.


---

## The Drain Phase

### Why `LOOP_LIMIT = TOTAL_CHUNKS + CHUNKS_PER_ROW + 1`?

Even after reading all `TOTAL_CHUNKS` chunks, the pipeline still **owes outputs** for the last `(CHUNKS_PER_ROW + 1)` centers.

### Behavior During Drain

| Iteration | Action |
|-----------|--------|
| `iter < TOTAL_CHUNKS` | Read from C_tmp, update buffers normally |
| `iter >= TOTAL_CHUNKS` | **No reads** — fill with zeros to flush outputs |

During drain, the tail outputs correspond to **border regions** (last row), and border pixels are forced to `0`.

---

## Comparison: Without Line Buffers

Without line buffers, you'd need random access to the entire image:

```cpp
// This is what V1 does (works but slower at filter stage)
static pixel_t C_tmp[HEIGHT][PADDED_WIDTH];
static pixel_t C_filt[HEIGHT][PADDED_WIDTH];
```

**V1 Approach** (full 2D arrays):
- Requires array partitioning for parallel access
- Filter runs at 1 pixel/cycle

**V2 Approach** (chunk-level line buffers):
- Only 2 × CHUNKS_PER_ROW chunks stored
- Filter runs at **64 pixels/cycle**

---

## Filter Summary

| Concept | V2 Implementation |
|---------|-------------------|
| **Line Buffers** | Store 2 rows of 512-bit chunks (O(CHUNKS_PER_ROW) memory) |
| **Sliding Window** | 3×3 chunk array, shifts horizontally each cycle |
| **Output Lag** | `out_idx = iter - (CHUNKS_PER_ROW + 1)` |
| **Drain Phase** | Extra iterations to flush the pipeline |
| **Border Policy** | All border pixels output as `0` |
| **Parallelism** | 64 pixels processed per iteration |

---

# Part 3: Step-by-Step Execution Trace

> **Note:** This section provides a **pixel-level conceptual trace** to illustrate the sliding window algorithm. In V2, the same principle applies at the **chunk level** (64 pixels at a time), with:
> - `WIDTH` → `CHUNKS_PER_ROW`
> - `IMAGE_SIZE` → `TOTAL_CHUNKS`
> - `pixel_t` → `uint512_t`

## Example Setup: 4×4 Image (Conceptual Pixel-Level Trace)

```
WIDTH = 4, HEIGHT = 4, IMAGE_SIZE = 16
LOOP_LIMIT = IMAGE_SIZE + WIDTH + 1 = 21 iterations (iter = 0 to 20)
```

### Input Image (Pixel Values)

```
        col 0   col 1   col 2   col 3
       ┌───────┬───────┬───────┬───────┐
row 0  │  A(0) │  B(1) │  C(2) │  D(3) │
       ├───────┼───────┼───────┼───────┤
row 1  │  E(4) │  F(5) │  G(6) │  H(7) │
       ├───────┼───────┼───────┼───────┤
row 2  │  I(8) │  J(9) │ K(10) │ L(11) │
       ├───────┼───────┼───────┼───────┤
row 3  │ M(12) │ N(13) │ O(14) │ P(15) │
       └───────┴───────┴───────┴───────┘

Letter(index) — e.g., F(5) means pixel F at index 5
```

### Key Formula Reminder

```
col = i % WIDTH = i % 4
out_idx = i - (WIDTH + 1) = i - 5
Output row = out_idx / 4
Output col = out_idx % 4
```

---

## 💡 Key Concepts to Watch

> **Line Buffer Purpose:** The line buffers store previous rows so we can access neighbors above.
> - `lb[1]` holds the "current-1" row (one row behind current input)
> - `lb[0]` holds the "current-2" row (two rows behind current input)
>

---

## Iteration Trace

### Legend

- `·` = uninitialized/garbage value
- `0` = zero (initial value in line buffers)
- Letters = pixel values from input image

---

## i = 0: Read A (row 0, col 0)

> **FIRST LINE BUFFER INSERTION:** This is the very first pixel being processed.
> Since we're reading row 0, there's no "previous row" data yet — the line buffers
> contain zeros (their initial state). We store pixel A in `lb[1][0]` to make it
> available when we process row 1 later. The "store previous" mechanism:
> - `lb[0][0]` = old `lb[1][0]` = 0 (no previous data exists yet)
> - `lb[1][0]` = A (current pixel, will be "previous" for next row at col 0)

**Input:** `new_pixel = A`, `col = 0 % 4 = 0`

**Window BEFORE (shift left, then fill right column):**
```
[·][·][·]      shift      [·][·][·]      fill       [·][·][0]
[·][·][·]    ────────▶    [·][·][·]    ────────▶   [·][·][0]
[·][·][·]     left        [·][·][·]    right col    [·][·][A]
                                        ↑ lb[0][0]=0  (2 rows ago - nothing)
                                        ↑ lb[1][0]=0  (1 row ago - still nothing before update)
                                        ↑ new_pixel=A (current row)
```

**Line Buffers AFTER update:**
```
lb[0]: [0][0][0][0]   (lb[0][0] = old lb[1][0] = 0)
lb[1]: [A][0][0][0]   (lb[1][0] = A) ← A stored for future use!
```

**Output:** `out_idx = 0 - 5 = -5` → **No output** (out_idx < 0)

---

## i = 1: Read B (row 0, col 1)

**Input:** `new_pixel = B`, `col = 1`

**Window AFTER shift + fill:**
```
[·][0][0]   ← lb[0][1]=0
[·][0][0]   ← lb[1][1]=0 (before update; will become B after)
[·][A][B]   ← new_pixel=B
```

**Line Buffers AFTER:**
```
lb[0]: [0][0][0][0]
lb[1]: [A][B][0][0]   ← Row 0 pixels accumulating
```

**Output:** `out_idx = 1 - 5 = -4` → **No output**

---

## i = 2: Read C (row 0, col 2)

**Input:** `new_pixel = C`, `col = 2`

**Window AFTER:**
```
[0][0][0]   ← lb[0][2]=0
[0][0][0]   ← lb[1][2]=0
[A][B][C]   ← new_pixel=C
```

**Line Buffers AFTER:**
```
lb[0]: [0][0][0][0]
lb[1]: [A][B][C][0]
```

**Output:** `out_idx = 2 - 5 = -3` → **No output**

---

## i = 3: Read D (row 0, col 3)

**Input:** `new_pixel = D`, `col = 3`

**Window AFTER:**
```
[0][0][0]
[0][0][0]
[B][C][D]
```

**Line Buffers AFTER:**
```
lb[0]: [0][0][0][0]
lb[1]: [A][B][C][D]   ← Row 0 complete in lb[1]!
```

**Output:** `out_idx = 3 - 5 = -2` → **No output**

---

## i = 4: Read E (row 1, col 0)


> **FIRST ROW CHANGE!** We're now processing row 1. This is where line buffer
> management becomes crucial. Watch how row 0 data "shifts up":
>
> **What happens at col=0 when changing rows:**
> 1. We read `lb[0][0]` and `lb[1][0]` into window RIGHT column BEFORE updating
> 2. Then we execute: `lb[0][0] = lb[1][0]` (A moves up: lb[1]→lb[0])
> 3. Then we execute: `lb[1][0] = E` (new pixel takes lb[1] position)
>
> **Why this order?** We need the OLD values for the window, then update for future use.
> The line buffers work as a "shift register" across rows at each column position.

**Input:** `new_pixel = E`, `col = 0`

**Window AFTER:**
```
[0][0][0]   ← lb[0][0]=0 (BEFORE update - still zero)
[0][0][A]   ← lb[1][0]=A (BEFORE update - row 0 data!)
[C][D][E]   ← new_pixel=E
```

**Line Buffers AFTER:**
```
lb[0]: [A][0][0][0]   (lb[0][0] = old lb[1][0] = A) ← A moved up!
lb[1]: [E][B][C][D]   (lb[1][0] = E) ← E takes A's old spot
       ↑
       Note: positions 1,2,3 still have row 0 data (B,C,D)
       They'll be updated as we process cols 1,2,3 of row 1
```

**Output:** `out_idx = 4 - 5 = -1` → **No output**

---

## i = 5: Read F (row 1, col 1) ⭐ First Output!


> **FIRST VALID OUTPUT INDEX!** `out_idx = 0` means we can finally write something.
> However, output position (0,0) is a CORNER → BORDER pixel, so result = 0.

**Input:** `new_pixel = F`, `col = 1`

**Window AFTER:**
```
[0][0][0]   ← lb[0][1]=0 (row 0 col 1 was 0s padding before actual data)
[0][A][B]   ← lb[1][1]=B (row 0's B, before F overwrites it)
[D][E][F]   ← new_pixel=F
```

**Line Buffers AFTER:**
```
lb[0]: [A][B][0][0]   ← Notice: col 1 updated! B moved from lb[1] to lb[0]
lb[1]: [E][F][C][D]   ← F stored at col 1
```

**Output:** `out_idx = 5 - 5 = 0` → **Output pixel (0,0) = A's position**
- `row = 0/4 = 0, col = 0%4 = 0` → **BORDER (corner)** → `result = 0`

---

## i = 6: Read G (row 1, col 2)

**Input:** `new_pixel = G`, `col = 2`

**Window AFTER:**
```
[0][0][0]   ← lb[0][2]=0 (still zeros - row 0 data hasn't propagated here yet!)
[A][B][C]   ← lb[1][2]=C (row 0's C)
[E][F][G]   ← new_pixel=G
```

**Line Buffers AFTER:**
```
lb[0]: [A][B][C][0]   ← C propagated up to lb[0]
lb[1]: [E][F][G][D]   ← G stored at col 2
```

**Output:** `out_idx = 6 - 5 = 1` → pixel (0,1) = B's position
- `row = 1/4 = 0, col = 1%4 = 1` → **BORDER** (top row) → `result = 0`

---

## i = 7: Read H (row 1, col 3)

**Input:** `new_pixel = H`, `col = 3`

**Window AFTER:**
```
[0][0][0]   ← lb[0][3]=0 (last position to still have zero!)
[B][C][D]   ← D from row 0
[F][G][H]   ← new_pixel=H
```

**Line Buffers AFTER:**
```
lb[0]: [A][B][C][D]   ← Row 0 now COMPLETE in lb[0]!
lb[1]: [E][F][G][H]   ← Row 1 now COMPLETE in lb[1]!
```

> **Steady state reached!** After processing a complete row, both line buffers
> contain full, contiguous row data. This pattern continues for remaining rows.

**Output:** `out_idx = 7 - 5 = 2` → pixel (0,2) = C's position
- `row = 2/4 = 0, col = 2%4 = 2` → **BORDER** → `result = 0`

---

## i = 8: Read I (row 2, col 0)

> **Second row change!** Now processing row 2. Row 1's E will move to lb[0],
> while I takes lb[1][0]. Watch the line buffer "shift" mechanism again.

**Input:** `new_pixel = I`, `col = 0`

**Window AFTER:**
```
[0][0][A]   ← lb[0][0]=A (row 0 data, before shifting)
[0][D][E]   ← lb[1][0]=E (row 1 data, before update)
[G][H][I]   ← new_pixel=I
```


**Line Buffers AFTER:**
```
lb[0]: [E][B][C][D]   ← E moved up from lb[1] to lb[0] at col 0
lb[1]: [I][F][G][H]   ← I stored at col 0
       ↑
       cols 1,2,3 still have row 1 data (F,G,H)
       They'll update as we process cols 1,2,3 of row 2
```

**Output:** `out_idx = 8 - 5 = 3` → pixel (0,3) = D's position
- `row = 3/4 = 0, col = 3%4 = 3` → **BORDER** → `result = 0`

---

## i = 9: Read J (row 2, col 1)

**Input:** `new_pixel = J`, `col = 1`

**Window AFTER:**
```
[0][A][B]   ← lb[0][1]=B (row 0 data - notice the "lag" - col 1 still has old data!)
[D][E][F]   ← lb[1][1]=F (row 1 data)
[H][I][J]   ← new_pixel=J
```

**Line Buffers AFTER:**
```
lb[0]: [E][F][C][D]   ← F moved up to lb[0] at col 1
lb[1]: [I][J][G][H]   ← J stored at col 1
```

**Output:** `out_idx = 9 - 5 = 4` → pixel (1,0) = E's position
- `row = 4/4 = 1, col = 4%4 = 0` → **BORDER** (left edge) → `result = 0`

> Still outputting border pixels! The output "lags" the input by 5 iterations,
> so we're still processing output positions that touch the image edges.

---

## i = 10: Read K (row 2, col 2) ⭐ First Non-Border Output!


> **🎉 WINDOW BECOMES FULLY VALID FOR FILTER COMPUTATION!**
>
> This is the **first iteration** where:
> 1. `out_idx ≥ 0` (we have a valid output)
> 2. Output pixel (1,1) = F's position is **NOT on any border**
> 3. All 8 neighbors in the window contain **real image data** (not zeros!)

**Input:** `new_pixel = K`, `col = 2`

**Window AFTER:**
```
[A][B][C]   ← lb[0][2]=C (row 0 data - A,B from earlier updates)
[E][F][G]   ← lb[1][2]=G (row 1 data - E,F from earlier updates)
[I][J][K]   ← new_pixel=K
```

**Line Buffers AFTER:**
```
lb[0]: [E][F][G][D]   ← G moved up to lb[0] at col 2
lb[1]: [I][J][K][H]   ← K stored at col 2
```

**Output:** `out_idx = 10 - 5 = 5` → pixel (1,1) = **F's position**
- `row = 5/4 = 1, col = 5%4 = 1` → **NOT BORDER!** (interior pixel)

**Filter Computation:**
```
Window:       [A][B][C]     Kernel:    [ 0][-1][ 0]
              [E][F][G]                [-1][ 5][-1]
              [I][J][K]                [ 0][-1][ 0]

              ↑ Center = F (the pixel being sharpened)
              ↑ Neighbors: B (top), J (bottom), E (left), G (right)

sum = 5*F - B - J - E - G
    = 5×center - top - bottom - left - right

result = clip(sum, 0, 255)
```
---

## i = 11: Read L (row 2, col 3)

**Input:** `new_pixel = L`, `col = 3`

**Window AFTER:**
```
[B][C][D]
[F][G][H]
[J][K][L]
```

**Line Buffers AFTER:**
```
lb[0]: [E][F][G][H]   ← Row 1 complete in lb[0]
lb[1]: [I][J][K][L]   ← Row 2 complete in lb[1]
```

**Output:** `out_idx = 11 - 5 = 6` → pixel (1,2) = **G's position**
- `row = 6/4 = 1, col = 6%4 = 2` → **NOT BORDER!**

**Filter:** `sum = 5*G - C - K - F - H`

---

## i = 12: Read M (row 3, col 0)

**Input:** `new_pixel = M`, `col = 0`

**Window AFTER:**
```
[C][D][E]
[G][H][I]
[K][L][M]
```

**Line Buffers AFTER:**
```
lb[0]: [I][F][G][H]
lb[1]: [M][J][K][L]
```

**Output:** `out_idx = 12 - 5 = 7` → pixel (1,3) = H's position
- `row = 7/4 = 1, col = 7%4 = 3` → **BORDER** (right edge) → `result = 0`

---

## i = 13: Read N (row 3, col 1)

**Input:** `new_pixel = N`, `col = 1`

**Window AFTER:**
```
[D][E][F]
[H][I][J]
[L][M][N]
```

**Line Buffers AFTER:**
```
lb[0]: [I][J][G][H]
lb[1]: [M][N][K][L]
```

**Output:** `out_idx = 13 - 5 = 8` → pixel (2,0) = I's position
- `row = 8/4 = 2, col = 8%4 = 0` → **BORDER** → `result = 0`

---

## i = 14: Read O (row 3, col 2)

**Input:** `new_pixel = O`, `col = 2`

**Window AFTER:**
```
[E][F][G]
[I][J][K]
[M][N][O]
```

**Line Buffers AFTER:**
```
lb[0]: [I][J][K][H]
lb[1]: [M][N][O][L]
```

**Output:** `out_idx = 14 - 5 = 9` → pixel (2,1) = **J's position**
- `row = 9/4 = 2, col = 9%4 = 1` → **NOT BORDER!**

**Filter:** `sum = 5*J - F - N - I - K`

---

## i = 15: Read P (row 3, col 3) — Last Input!

> **LAST INPUT PIXEL!** After this, no more data from the input stream.
> The remaining iterations will "drain" the pipeline to produce final outputs.

**Input:** `new_pixel = P`, `col = 3`

**Window AFTER:**
```
[F][G][H]
[J][K][L]
[N][O][P]
```

**Line Buffers AFTER:**
```
lb[0]: [I][J][K][L]
lb[1]: [M][N][O][P]
```

**Output:** `out_idx = 15 - 5 = 10` → pixel (2,2) = **K's position**
- `row = 10/4 = 2, col = 10%4 = 2` → **NOT BORDER!**

**Filter:** `sum = 5*K - G - O - J - L`

---

## DRAIN PHASE (i = 16 to 20)


> **No more input reads!** We've consumed all 16 pixels, but still need to
> produce 5 more outputs (indices 11-15). The window shifts left each iteration,
> right column fills with garbage/stale data, BUT we don't care:
>
> - For BORDER pixels (which all remaining outputs are), we output 0 anyway
> - The window content doesn't matter for border detection logic
> - This "drain phase" ensures we produce exactly IMAGE_SIZE outputs

No more input reads. Window just shifts left and fills with garbage (but we don't care — only window center matters for valid out_idx).

---

## i = 16: Drain (no read)

**Window shifts only** (right column becomes garbage `·`):
```
[G][H][·]
[K][L][·]
[O][P][·]
```

**Output:** `out_idx = 16 - 5 = 11` → pixel (2,3) = L's position
- `row = 11/4 = 2, col = 11%4 = 3` → **BORDER** → `result = 0`

---

## i = 17: Drain

**Window:**
```
[H][·][·]
[L][·][·]
[P][·][·]
```

**Output:** `out_idx = 17 - 5 = 12` → pixel (3,0) = M's position
- `row = 12/4 = 3, col = 12%4 = 0` → **BORDER** → `result = 0`

---

## i = 18: Drain

**Output:** `out_idx = 18 - 5 = 13` → pixel (3,1) = N's position
- `row = 13/4 = 3, col = 13%4 = 1` → **BORDER** → `result = 0`

---

## i = 19: Drain

**Output:** `out_idx = 19 - 5 = 14` → pixel (3,2) = O's position
- `row = 14/4 = 3, col = 14%4 = 2` → **BORDER** → `result = 0`

---

## i = 20: Drain — Final Iteration!

**Output:** `out_idx = 20 - 5 = 15` → pixel (3,3) = P's position
- `row = 15/4 = 3, col = 15%4 = 3` → **BORDER** → `result = 0`

---

## Summary Table

| i  | Input | col | out_idx | Output Pos | Border? | Window Center | Result |
|----|-------|-----|---------|------------|---------|---------------|--------|
| 0  | A     | 0   | -5      | —          | —       | —             | —      |
| 1  | B     | 1   | -4      | —          | —       | —             | —      |
| 2  | C     | 2   | -3      | —          | —       | —             | —      |
| 3  | D     | 3   | -2      | —          | —       | —             | —      |
| 4  | E     | 0   | -1      | —          | —       | —             | —      |
| 5  | F     | 1   | 0       | (0,0)=A    | ✓       | —             | 0      |
| 6  | G     | 2   | 1       | (0,1)=B    | ✓       | —             | 0      |
| 7  | H     | 3   | 2       | (0,2)=C    | ✓       | —             | 0      |
| 8  | I     | 0   | 3       | (0,3)=D    | ✓       | —             | 0      |
| 9  | J     | 1   | 4       | (1,0)=E    | ✓       | —             | 0      |
| 10 | K     | 2   | 5       | **(1,1)=F**| ✗       | F             | **5F-B-J-E-G** |
| 11 | L     | 3   | 6       | **(1,2)=G**| ✗       | G             | **5G-C-K-F-H** |
| 12 | M     | 0   | 7       | (1,3)=H    | ✓       | —             | 0      |
| 13 | N     | 1   | 8       | (2,0)=I    | ✓       | —             | 0      |
| 14 | O     | 2   | 9       | **(2,1)=J**| ✗       | J             | **5J-F-N-I-K** |
| 15 | P     | 3   | 10      | **(2,2)=K**| ✗       | K             | **5K-G-O-J-L** |
| 16 | —     | —   | 11      | (2,3)=L    | ✓       | —             | 0      |
| 17 | —     | —   | 12      | (3,0)=M    | ✓       | —             | 0      |
| 18 | —     | —   | 13      | (3,1)=N    | ✓       | —             | 0      |
| 19 | —     | —   | 14      | (3,2)=O    | ✓       | —             | 0      |
| 20 | —     | —   | 15      | (3,3)=P    | ✓       | —             | 0      |

> **Pattern recognition:** Notice the interior pixels (✗ in Border column) appear at:
> - i=10,11 (row 1 interiors: F, G)
> - i=14,15 (row 2 interiors: J, K)
>
> In general: interior outputs occur when `out_idx` maps to positions where
> `1 ≤ row ≤ HEIGHT-2` and `1 ≤ col ≤ WIDTH-2`.

---

## Output Image

For a 4×4 image, only the **4 interior pixels** `{F, G, J, K}` at positions `{(1,1), (1,2), (2,1), (2,2)}` get computed filter values. All border pixels are zero:

```
        col 0   col 1         col 2         col 3
       ┌───────┬─────────────┬─────────────┬───────┐
row 0  │   0   │      0      │      0      │   0   │  ← Top border (all zeros)
       ├───────┼─────────────┼─────────────┼───────┤
row 1  │   0   │ 5F-B-J-E-G  │ 5G-C-K-F-H  │   0   │  ← Left/Right borders = 0
       ├───────┼─────────────┼─────────────┼───────┤
row 2  │   0   │ 5J-F-N-I-K  │ 5K-G-O-J-L  │   0   │  ← Interior gets computed!
       ├───────┼─────────────┼─────────────┼───────┤
row 3  │   0   │      0      │      0      │   0   │  ← Bottom border (all zeros)
       └───────┴─────────────┴─────────────┴───────┘
```

> **Why only 4 interior pixels for a 4×4 image?**
> - Interior = (HEIGHT-2) × (WIDTH-2) = 2 × 2 = 4 pixels
> - For a 1920×1080 image: (1080-2) × (1920-2) = 1078 × 1918 = 2,067,404 interior pixels
> - Border pixels are zeroed because the filter would need neighbors outside the image

---
