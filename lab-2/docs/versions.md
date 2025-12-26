# HLS Kernel Versions Comparison

This document compares the evolution of the HLS image processing kernel from baseline through three optimization levels.

## Overview

| Version | Architecture | Data Storage | Filter Strategy | Key Feature |
|---------|-------------|--------------|-----------------|-------------|
| **V1** | Sequential 3-stage | 2D BRAM arrays | Pixel-by-pixel | Array partitioning |
| **V2** | Sequential 3-stage | 512-bit chunk arrays | Line buffers + sliding window | 64 px/cycle in filter |
| **V3** | **Dataflow pipeline** | **HLS streams** | Line buffers + sliding window | Overlapped execution |

---

## Version Evolution

### V1 - Array Partitioning

**Architecture**: 2D BRAM arrays with **cyclic partitioning** for parallel access.

```cpp
static pixel_t C_tmp[HEIGHT][PADDED_WIDTH];
static pixel_t C_filt[HEIGHT][PADDED_WIDTH];

#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=3 dim=1   // 3 rows for filter
#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=64 dim=2  // 64 cols per chunk
#pragma HLS ARRAY_PARTITION variable=C_filt cyclic factor=64 dim=2
```

**Stages**:
1. **Posterize**: Unpack 512-bit → 64 pixels → posterize → store to 2D array
2. **Filter**: Pixel-by-pixel with II=1 pipelining
3. **Pack**: Read 64 pixels → pack to 512-bit → write to DDR

---

### V2 - Line Buffer + Sliding Window

**Architecture**: Operates directly on **512-bit chunks** with line buffers.

```cpp
static uint512_t C_tmp[TOTAL_CHUNKS];   // Chunk-level storage
static uint512_t C_filt[TOTAL_CHUNKS];

uint512_t lb[2][CHUNKS_PER_ROW];        // 2 line buffers
#pragma HLS ARRAY_PARTITION variable=lb complete dim=1

uint512_t win[3][3];                    // 3x3 chunk window
#pragma HLS ARRAY_PARTITION variable=win complete dim=0
```

**Improvements over V1**:
| Aspect | V1 | V2 |
|--------|----|----|
| Intermediate format | 2D pixel arrays | 512-bit chunk arrays |
| Filter processing | 1 pixel/cycle | **64 pixels/cycle** |
| Memory efficiency | O(H × W) per buffer | O(TOTAL_CHUNKS) |
| Filter data structure | Random access | Sliding window |

**Key Innovation**: The filter stage processes entire 512-bit chunks, computing 64 convolutions in parallel:
```cpp
// Extended loop for pipeline flush
const int LOOP_LIMIT = TOTAL_CHUNKS + CHUNKS_PER_ROW + 1;

Filter_Loop:
for (int iter = 0; iter < LOOP_LIMIT; iter++) {
    // Shift window, update from line buffers
    // Compute 64 filter outputs in parallel
}
```

**Cross-Chunk Neighbor Access**:
```cpp
// West neighbor at chunk boundary
if (k > 0) val -= win[1][1].range((k-1)*8+7, (k-1)*8);
else       val -= win[1][0].range(511, 504);  // From left chunk

// East neighbor at chunk boundary  
if (k < 63) val -= win[1][1].range((k+1)*8+7, (k+1)*8);
else        val -= win[1][2].range(7, 0);     // From right chunk
```

---

### V3 - Dataflow Streaming

**Architecture**: **Full dataflow pipeline** with HLS streams connecting modular stages.

```cpp
#include <hls_stream.h>

static hls::stream<uint512_t> stream_post("s_post");
static hls::stream<uint512_t> stream_filt("s_filt");

#pragma HLS STREAM variable=stream_post depth=16
#pragma HLS STREAM variable=stream_filt depth=16
#pragma HLS DATAFLOW

compute_diff_wide(A, B, stream_post);
apply_filter_wide(stream_post, stream_filt);
write_result_wide(stream_filt, C);
```

**Improvements over V2**:
| Aspect | V2 | V3 |
|--------|----|----|
| Stage execution | Sequential | **Overlapped (concurrent)** |
| Inter-stage comm | BRAM arrays | HLS streams (FIFOs) |
| Total latency | 3× TOTAL_CHUNKS | **~1× TOTAL_CHUNKS** |
| Code structure | Monolithic | Modular functions |

**Modular Stage Functions**:
- `compute_diff_wide()` — Stage 1: Difference + posterize
- `apply_filter_wide()` — Stage 2: Sharpen filter with line buffers
- `write_result_wide()` — Stage 3: Memory write

**Performance**:
- **Throughput**: 64 pixels per clock cycle
- **Latency**: ~1,050 cycles for 256×256 image (theoretical minimum: 1024)

---

## Optimization Summary

| Optimization | V1→V2 | V2→V3 |
|--------------|-------|-------|
| **Goal** | Chunk-level parallelism | Overlap stages |
| **Technique** | Line buffers + sliding window | Dataflow + streams |
| **Filter throughput** | 64 px/cycle | 64 px/cycle (concurrent) |

---

## Common Elements

All HLS-optimized versions (V1, V2, V3) share:
- **Interface**: 512-bit AXI master (`m_axi`) with bundles `gmemA`, `gmemB`, `gmemC`
- **Control**: AXI-Lite (`s_axilite`) via `bundle=control`
- **Algorithm**: 3-stage (posterize → sharpen → output)
- **Sharpen kernel**: `[0 -1 0; -1 5 -1; 0 -1 0]`
- **Border policy**: Output border pixels set to 0
- **Helper functions**: `posterize()` and `clip_u8()` (inlined)
