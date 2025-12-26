# Wide Vector Addition (WIDE_VADD) - Advanced Vitis HLS Kernel Example

This document explains the `wide_vadd/` example directory in detail.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Differences from Basic VADD](#key-differences-from-basic-vadd)
3. [Directory Structure](#directory-structure)
4. [Architecture](#architecture)
5. [Kernel Code (hw_src/vadd.cpp)](#kernel-code-hw_srcvaddcpp)
6. [Host Application (sw_src/host.cpp)](#host-application-sw_srchostcpp)
7. [Wide Memory Access Explained](#wide-memory-access-explained)
8. [HLS Pragmas and Optimizations](#hls-pragmas-and-optimizations)
9. [Performance Analysis](#performance-analysis)
10. [Building and Running](#building-and-running)

---

## Overview

**Purpose**: Compute `C[i] = A[i] + B[i]` for i = 0 to DATA_SIZE-1

**Optimization Focus**: **16× throughput improvement** through wide (512-bit) memory interfaces

**Key Concepts Demonstrated**:
- Wide memory access using `ap_uint<512>` datatype
- Processing 16 integers per memory transaction
- Separate memory bundles for parallel access
- DATAFLOW pragma for overlapping stages
- HLS streams for efficient data movement

---

## Key Differences from Basic VADD

| Feature | Basic VADD | Wide VADD |
|---------|------------|-----------|
| **Data Width** | 32 bits (1 int) | **512 bits (16 ints)** |
| **Elements per Transfer** | 1 | **16** |
| **Memory Bundles** | Single (`gmem`) | **Separate (`gmem`, `gmem1`, `gmem2`)** |
| **DATA_SIZE** | 4,096 | **16,384** |
| **Loop Optimization** | PIPELINE only | **DATAFLOW + streaming** |
| **Throughput** | 1 elem/cycle | **16 elems/cycle** |

---

## Directory Structure

```
wide_vadd/
├── hw_src/                    # Hardware (FPGA) source code
│   └── vadd.cpp               # Optimized kernel with 512-bit interfaces
│
└── sw_src/                    # Software (CPU) source code
    ├── host.cpp               # Host application
    ├── xcl2.hpp               # Xilinx OpenCL utilities (header)
    ├── xcl2.cpp               # Xilinx OpenCL utilities (source)
    ├── event_timer.hpp        # Timing utilities (header)
    └── event_timer.cpp        # Timing utilities (source)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              HOST (CPU)                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  host.cpp                                                                    ││
│  │  ├── Allocate 16,384 × 4 bytes = 64 KB per vector                           ││
│  │  ├── Data pattern: A[i] = i, B[i] = i²                                      ││
│  │  ├── Expected result: C[i] = i + i²                                         ││
│  │  └── OpenCL flow (same as basic vadd)                                       ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                    │                                             │
│                                    │ PCIe / AXI                                  │
│                                    ▼                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              FPGA DEVICE                                         │
│                                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  │
│  │ DDR Bank 0           │  │ DDR Bank 1           │  │ DDR Bank 2           │  │
│  │ in1[0..16383]        │  │ in2[0..16383]        │  │ out[0..16383]        │  │
│  │                      │  │                      │  │                      │  │
│  │ Bundle: gmem         │  │ Bundle: gmem1        │  │ Bundle: gmem2        │  │
│  └──────────┬───────────┘  └──────────┬───────────┘  └──────────▲───────────┘  │
│             │                         │                         │              │
│             │ 512-bit AXI             │ 512-bit AXI             │ 512-bit AXI  │
│             ▼                         ▼                         │              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                         VADD Kernel (wide_vadd.cpp)                         ││
│  │                                                                              ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐││
│  │  │                         DATAFLOW Region                                  │││
│  │  │                                                                          │││
│  │  │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐              │││
│  │  │  │ v1_local    │      │ v2_local    │      │ result_local│              │││
│  │  │  │ [64]        │─────►│ [64]        │─────►│ [64]        │              │││
│  │  │  │ 512-bit     │      │ 512-bit     │      │             │              │││
│  │  │  │ HLS Streams │      │ HLS Streams │      │             │              │││
│  │  │  └─────────────┘      └─────────────┘      └─────────────┘              │││
│  │  │        │                    │                    │                       │││
│  │  │        ▼                    ▼                    ▼                       │││
│  │  │  ┌───────────────────────────────────────────────────────────────────┐  │││
│  │  │  │              ADDER (16 parallel 32-bit additions)                  │  │││
│  │  │  │                                                                    │  │││
│  │  │  │   [31:0] + [31:0]     → [31:0]     (Element 0)                    │  │││
│  │  │  │   [63:32] + [63:32]   → [63:32]    (Element 1)                    │  │││
│  │  │  │   ...                                                              │  │││
│  │  │  │   [511:480] + [511:480] → [511:480] (Element 15)                  │  │││
│  │  │  │                                                                    │  │││
│  │  │  │   #pragma HLS UNROLL  (16 adders instantiated in parallel)        │  │││
│  │  │  └───────────────────────────────────────────────────────────────────┘  │││
│  │  │                                                                          │││
│  │  └─────────────────────────────────────────────────────────────────────────┘││
│  │                                                                              ││
│  │  AXI-Lite Control (s_axilite bundle=control)                                ││
│  │  ├── Register: in1 pointer   (64-bit address)                               ││
│  │  ├── Register: in2 pointer   (64-bit address)                               ││
│  │  ├── Register: out pointer   (64-bit address)                               ││
│  │  ├── Register: size          (32-bit integer)                               ││
│  │  └── Control: start/done/idle                                               ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Kernel Code (hw_src/vadd.cpp)

### Type Definitions

```cpp
#include <ap_int.h>  // Xilinx arbitrary precision types

#define BUFFER_SIZE 64                          // Chunks per burst
#define DATAWIDTH 512                           // Bits per memory access
#define VECTOR_SIZE (DATAWIDTH / 32)            // = 16 integers per access

typedef ap_uint<DATAWIDTH> uint512_dt;          // 512-bit wide datatype
```

**Why 512 bits?**
- DDR4 memory bus width is typically 512 bits
- Matches the physical memory interface
- Maximizes bandwidth utilization

### Interface Pragmas (Critical Difference!)

```cpp
extern "C" {
void vadd(
    const uint512_dt *in1,   // 512-bit wide input 1
    const uint512_dt *in2,   // 512-bit wide input 2
    uint512_dt *out,         // 512-bit wide output
    int size                 // Size in 32-bit INTEGERS (not chunks)
) {
// SEPARATE memory ports for parallel access!
#pragma HLS INTERFACE m_axi port=in1 bundle=gmem   // ← Bank 0
#pragma HLS INTERFACE m_axi port=in2 bundle=gmem1  // ← Bank 1 (DIFFERENT!)
#pragma HLS INTERFACE m_axi port=out bundle=gmem2  // ← Bank 2 (DIFFERENT!)

// Control interface
#pragma HLS INTERFACE s_axilite port=in1 bundle=control
#pragma HLS INTERFACE s_axilite port=in2 bundle=control
#pragma HLS INTERFACE s_axilite port=out bundle=control
#pragma HLS INTERFACE s_axilite port=size bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
```

**Key Insight**: Using separate bundles (`gmem`, `gmem1`, `gmem2`) enables:
- **Parallel memory access** - read in1 and in2 simultaneously
- **Higher bandwidth** - no contention on memory ports
- **Better DDR utilization** - can map to different DDR banks

### Local Buffers with Streaming

```cpp
uint512_dt v1_local[BUFFER_SIZE];      // 64 × 64 bytes = 4 KB
uint512_dt v2_local[BUFFER_SIZE];
uint512_dt result_local[BUFFER_SIZE];

// Convert to HLS streams for DATAFLOW
#pragma HLS stream variable=v1_local depth=64
#pragma HLS stream variable=v2_local depth=64
```

**Streams vs Arrays**:
| Aspect | Array | Stream |
|--------|-------|--------|
| Access | Random | Sequential (FIFO) |
| Reuse | Yes | No (consumed once) |
| DATAFLOW | Limited | Full support |
| Overlap | Difficult | Natural |

### Size Calculation

```cpp
// Input 'size' is in 32-bit integers
// Convert to number of 512-bit chunks
int size_in16 = (size - 1) / VECTOR_SIZE + 1;  // Ceiling division

// Example: size = 16384 integers
// size_in16 = (16384 - 1) / 16 + 1 = 1024 chunks
```

### DATAFLOW Optimization

```cpp
for (int i = 0; i < size_in16; i += BUFFER_SIZE) {
#pragma HLS DATAFLOW

    // These operations OVERLAP in execution:
    
    // Stage 1: Read both inputs (parallel due to separate bundles)
    v1_rd:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS pipeline
        v1_local[j] = in1[i + j];
        v2_local[j] = in2[i + j];  // Same loop, concurrent reads!
    }

    // Stage 2: Compute (overlaps with reads of next chunk)
    add:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS pipeline
        uint512_dt tmpV1 = v1_local[j];
        uint512_dt tmpV2 = v2_local[j];
        uint512_dt tmpOut = 0;

        // Process all 16 integers in parallel
        for (int vector = 0; vector < VECTOR_SIZE; vector++) {
#pragma HLS UNROLL
            ap_uint<32> tmp1 = tmpV1.range(32*(vector+1)-1, vector*32);
            ap_uint<32> tmp2 = tmpV2.range(32*(vector+1)-1, vector*32);
            tmpOut.range(32*(vector+1)-1, vector*32) = tmp1 + tmp2;
        }
        
        out[i + j] = tmpOut;  // Direct write to output
    }
}
```

### Bit Range Access Explained

```
512-bit word: uint512_dt
┌───────────────────────────────────────────────────────────────────────────────┐
│ [511:480] │ [479:448] │ ... │ [95:64] │ [63:32] │ [31:0] │
│    int15  │    int14  │ ... │   int2  │   int1  │  int0  │
└───────────────────────────────────────────────────────────────────────────────┘

Access pattern:
  tmpV1.range(31, 0)     → int0  (bits 0-31)
  tmpV1.range(63, 32)    → int1  (bits 32-63)
  tmpV1.range(95, 64)    → int2  (bits 64-95)
  ...
  tmpV1.range(511, 480)  → int15 (bits 480-511)

General formula:
  tmpV1.range(32*(i+1)-1, i*32)  → int[i]
```

---

## Host Application (sw_src/host.cpp)

### Key Differences from Basic VADD

#### 1. Larger Data Size
```cpp
#define DATA_SIZE 16384  // 4× larger than basic vadd
```

#### 2. Different Test Pattern
```cpp
for (int i = 0; i < DATA_SIZE; i++) {
    source_in1[i] = i;          // A[i] = i
    source_in2[i] = i * i;      // B[i] = i²
    source_sw_results[i] = 0;
    source_hw_results[i] = 0;
}

// Expected result: C[i] = i + i²
for (int i = 0; i < DATA_SIZE; i++) {
    source_sw_results[i] = source_in1[i] + source_in2[i];
}
```

#### 3. Same OpenCL Flow
The host-side OpenCL code is nearly identical to basic vadd because:
- The wide memory access is transparent to the host
- Host always deals with individual integers
- FPGA handles the packing/unpacking internally

---

## Wide Memory Access Explained

### Memory Hierarchy

```
                    ┌─────────────────────────┐
                    │      Host CPU Memory    │
                    │    (source_in1, etc.)   │
                    └───────────┬─────────────┘
                                │ PCIe DMA
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                        FPGA DDR Memory                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Logical view (host sees):                                   │ │
│  │  int array[16384] = {0, 1, 2, 3, 4, 5, ..., 16383}          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                │                                  │
│                                │ (same data, different view)      │
│                                ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Physical view (kernel sees):                                │ │
│  │  uint512_dt chunks[1024]                                     │ │
│  │                                                              │ │
│  │  chunk[0] = { 0,  1,  2,  3,  4,  5,  6,  7,                │ │
│  │               8,  9, 10, 11, 12, 13, 14, 15 }               │ │
│  │  chunk[1] = {16, 17, 18, 19, 20, 21, 22, 23,                │ │
│  │              24, 25, 26, 27, 28, 29, 30, 31 }               │ │
│  │  ...                                                         │ │
│  │  chunk[1023] = {16368, 16369, ..., 16383}                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### Bandwidth Calculation

| Metric | Basic VADD | Wide VADD |
|--------|------------|-----------|
| Data per read | 4 bytes | 64 bytes |
| Reads per cycle | 1 | 1 |
| Elements per cycle | 1 | 16 |
| **Speedup** | 1× | **16×** |

Assuming 300 MHz kernel clock:
- Basic: 300M × 4 bytes = 1.2 GB/s
- Wide: 300M × 64 bytes = 19.2 GB/s

---

## HLS Pragmas and Optimizations

### Interface Pragmas

| Pragma | Purpose | Effect |
|--------|---------|--------|
| `bundle=gmem` | Assign to memory port 0 | in1 reads from port 0 |
| `bundle=gmem1` | Assign to memory port 1 | in2 reads from port 1 (parallel!) |
| `bundle=gmem2` | Assign to memory port 2 | out writes to port 2 (no conflict) |

### Optimization Pragmas

| Pragma | Purpose | Effect |
|--------|---------|--------|
| `#pragma HLS DATAFLOW` | Overlap loop iterations | Pipelined execution |
| `#pragma HLS stream variable=X depth=64` | Convert array to FIFO | Enable DATAFLOW |
| `#pragma HLS pipeline` | Pipeline loop body | II=1 target |
| `#pragma HLS UNROLL` | Expand inner loop | 16 parallel adders |
| `#pragma HLS LOOP_TRIPCOUNT` | Latency estimation hint | No hardware effect |

### Execution Timeline with DATAFLOW

```
Without DATAFLOW:
│ Read Chunk 0 │ Compute Chunk 0 │ Read Chunk 1 │ Compute Chunk 1 │ ...
└──────────────┴─────────────────┴──────────────┴─────────────────┘

With DATAFLOW:
│ Read Chunk 0 │ Read Chunk 1    │ Read Chunk 2    │ Read Chunk 3    │
               │ Compute Chunk 0 │ Compute Chunk 1 │ Compute Chunk 2 │
└──────────────┴─────────────────┴─────────────────┴─────────────────┘
                  ↑ Overlapped!
```

---

## Performance Analysis

### Resource Utilization Comparison

| Resource | Basic VADD | Wide VADD | Notes |
|----------|------------|-----------|-------|
| LUTs | ~1,000 | ~2,500 | More logic for wide data |
| FFs | ~1,500 | ~4,000 | Pipeline registers |
| BRAM | 3 | 6 | Larger buffers |
| DSP | 0 | 0 | Integer addition |

### Latency Breakdown

For 16,384 integers (1,024 chunks of 16):

| Stage | Basic VADD | Wide VADD |
|-------|------------|-----------|
| Read input 1 | 16,384 cycles | 1,024 cycles |
| Read input 2 | 16,384 cycles | 1,024 cycles (parallel!) |
| Compute | 16,384 cycles | 1,024 cycles |
| Write output | 16,384 cycles | 1,024 cycles |
| **Total** | **65,536 cycles** | **~2,000 cycles** |

**Speedup: ~32×** (due to parallelism + overlap)

---

## Building and Running

### 1. Software Emulation
```bash
cd wide_vadd

# Compile kernel
v++ -c -t sw_emu \
    --platform xilinx_u200_gen3x16_xdma_2_202110_1 \
    -k vadd \
    -o vadd.xo \
    hw_src/vadd.cpp

# Link kernel
v++ -l -t sw_emu \
    --platform xilinx_u200_gen3x16_xdma_2_202110_1 \
    -o vadd.xclbin \
    vadd.xo

# Compile host
g++ -o host \
    sw_src/host.cpp sw_src/xcl2.cpp sw_src/event_timer.cpp \
    -I$XILINX_XRT/include \
    -L$XILINX_XRT/lib \
    -lOpenCL -lxrt_coreutil

# Run
export XCL_EMULATION_MODE=sw_emu
./host vadd.xclbin
```

### 2. Hardware Emulation
```bash
v++ -c -t hw_emu ... (same as above with -t hw_emu)
v++ -l -t hw_emu ...
export XCL_EMULATION_MODE=hw_emu
./host vadd.xclbin
```

### 3. Hardware Build
```bash
v++ -c -t hw ... (same as above with -t hw)
v++ -l -t hw ...   # WARNING: Takes 2-6 hours!
unset XCL_EMULATION_MODE
./host vadd.xclbin
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Data mismatch | Endianness or bit ordering | Use `range()` correctly |
| Lower than expected bandwidth | Memory contention | Use separate bundles |
| DATAFLOW not applied | Arrays not converted to streams | Add `#pragma HLS stream` |
| Routing failure | Too many memory ports | Reduce bundle count |

---

## Key Takeaways

1. **Wide data types** (`ap_uint<512>`) maximize memory bandwidth
2. **Separate memory bundles** enable parallel access
3. **DATAFLOW** overlaps read/compute/write stages
4. **UNROLL** creates parallel hardware for inner loops
5. **Streams** are essential for DATAFLOW to work correctly

---

## Next Steps

To apply these optimizations to your own kernels:

1. **Identify the bottleneck** (usually memory bandwidth)
2. **Pack data** into 512-bit words using `ap_uint<512>`
3. **Use separate bundles** for independent data paths
4. **Apply DATAFLOW** at the outer loop level
5. **Pipeline inner loops** with II=1
6. **UNROLL** the element processing loop

---

## References

- [Vitis HLS Optimization Guide](https://docs.xilinx.com/r/en-US/ug1399-vitis-hls)
- [UG1393: Vitis Application Acceleration](https://docs.xilinx.com/r/en-US/ug1393-vitis-application-acceleration)
- [UG1076: AXI Reference Guide](https://docs.xilinx.com/r/en-US/ug1076-axi-reference-guide)
