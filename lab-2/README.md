<p align="center">
  <h1 align="center">Lab 2: Image Processing Accelerator with Sharpening Filter</h1>
  <p align="center">
    <strong>Multi-Stage HLS Pipeline with Dataflow Streaming</strong>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Tool-Vitis%20IDE-FF6C00?style=flat-square&logo=xilinx&logoColor=white" alt="Vitis IDE">
  <img src="https://img.shields.io/badge/Architecture-Dataflow-4CAF50?style=flat-square" alt="Dataflow">
  <img src="https://img.shields.io/badge/Interface-512--bit%20AXI-2196F3?style=flat-square" alt="512-bit AXI">
  <img src="https://img.shields.io/badge/Speedup-64×-E91E63?style=flat-square" alt="Speedup">
</p>

<p align="center">
  <strong>Author:</strong> Fraidakis Ioannis<br>
  <strong>Institution:</strong> Aristotle University of Thessaloniki<br>
  <strong>Date:</strong> December 2025
</p>

---

## 📋 Overview

This lab extends the previous work by adding a **3×3 Laplacian-based sharpening filter** to the image processing pipeline. The accelerator performs three operations in sequence:

1. **Absolute Difference**: `D[i][j] = |A[i][j] - B[i][j]|`
2. **Posterization**: Map D to discrete levels (0, 128, or 255)
3. **Sharpen Filter**: Apply a 3×3 Laplacian convolution kernel

Three architectural implementations (**V1**, **V2**, **V3**) explore optimization strategies for throughput and resource utilization.

---

## Directory Structure

```
lab-2/
├── docs/                          # Documentation
│   ├── assigment-description.pdf  # Assignment specification
│   ├── vitis-ide-tutorial.pdf     # Vitis IDE step-by-step guide
│   ├── report.tex                 # Detailed technical report (LaTeX)
│   ├── report.pdf                 # Compiled report
│   └── assets/                    # Images and figures
├── inc/                           # Header files
├── src_hw/                        # Hardware accelerator implementations
│   ├── accelerated_v1.cpp         # V1: Sequential with 2D buffers
│   ├── accelerated_v2.cpp         # V2: Sequential with line buffers
│   └── accelerated_v3.cpp         # V3: Dataflow streaming
├── src_sw/                        # Software components
│   ├── host.cpp                   # OpenCL host application
│   ├── hls_tb.cpp                 # HLS testbench
│   ├── event_timer.*              # Timing utility 
│   └── xcl2.*                     # Xilinx OpenCL utilities
└── README.md                      # This file
```

---

## Implementation Versions

<table>
<tr>
<th width="33%">🔵 Version 1</th>
<th width="33%">🟢 Version 2</th>
<th width="33%">🟣 Version 3</th>
</tr>
<tr>
<td>

### Sequential Pipeline

**File:** `accelerated_v1.cpp`

- 2D local BRAM buffers
- Full-frame buffering
- **1 pixel/cycle** (bottleneck)
- Latency: ~67,632 cycles

</td>
<td>

### Line Buffers

**File:** `accelerated_v2.cpp`

- Sliding window approach
- Line buffer optimization
- **64 pixels/cycle**
- Latency: ~3,104 cycles

</td>
<td>

### Dataflow Streaming

**File:** `accelerated_v3.cpp`

- `#pragma HLS DATAFLOW`
- `hls::stream<uint512_t>`
- **64 pixels/cycle**
- Latency: ~1,049 cycles

</td>
</tr>
<tr>
<td align="center">⏱️ Baseline</td>
<td align="center">⚡ <strong>21× faster</strong></td>
<td align="center">🚀 <strong>64× faster</strong></td>
</tr>
</table>

---

## 📊 Performance Summary

| Metric                    |    V1     |    V2     |      V3       |
|---------------------------|:---------:|:---------:|:-------------:|
| **HLS Latency** (cycles)  |  67,632   |   3,104   |   **1,049**   |
| **CU Time** (µs @ 300MHz) |    230    |     15    |     **5**     |
| **BRAM_18K**              |    256    |     30    |     **0**     |
| **Throughput**            | 1 px/cyc  | 64 px/cyc | **64 px/cyc** |

> 💡 **V3** achieves the best performance through concurrent stage execution with dataflow streaming.

---

## Getting Started

> 📘 **New to Vitis IDE?** Follow this comprehensive [Vitis IDE Tutorial](docs/vitis-ide-tutorial.pdf) for detailed step-by-step instructions.

### Prerequisites

| Tool | Purpose |
|------|---------|
| **Xilinx Vitis HLS** | HLS synthesis and simulation |
| **Xilinx Vitis  IDE** | Hardware emulation and deployment |
| **Alveo U200** (or compatible) | FPGA execution target |

### Step-by-Step Guide

#### 1️⃣ Launch Vitis IDE

```bash
vitis    # Opens Vitis Unified IDE
```

Select a workspace directory when prompted.

#### 2️⃣ Create New Application Project

1. **File → New → Application Project**
2. Configure:
   - **Project name:** `lab-2`
   - **Platform:** Alveo U200 (or your target)

#### 3️⃣ Add Host Files

Navigate to `host/src` in your project and add from `src_sw/`:

| File | Description |
|------|-------------|
| `host.cpp` | Main host application |
| `xcl2.cpp` + `xcl2.hpp` | OpenCL utilities |
| `event_timer.cpp` + `event_timer.hpp` | Timing utilities |

#### 4️⃣ Add Kernel Files

Navigate to `kernel/src` and add your chosen version from `src_hw/`:

| Option | File | Architecture |
|:------:|------|--------------|
| **A** | `accelerated_v1.cpp` | Sequential with 2D buffers |
| **B** | `accelerated_v2.cpp` | Line buffers |
| **C** | `accelerated_v3.cpp` | Dataflow streaming ⭐ |

#### 5️⃣ Configure Kernel

1. Open the `.prj` file of kernel directory
2. Set top function: `IMAGE_DIFF_POSTERIZE`
3. Configure kernel settings as needed

#### 6️⃣ Build and Run

| Step | Target | Action |
|------|--------|--------|
| 1 | **Emulation-HW** | Select as build target |
| 2 | **Build** | Compile host + synthesize kernel |
| 3 | **Run** | Execute hardware emulation |


---

## Architecture Comparison

### V1: Full-Frame Buffering
```
[Read A,B] → [BRAM 2D] → [Diff] → [Poster] → [Filter 1px] → [Write]
                                                  ↑
                                             BOTTLENECK
```

### V2: Line Buffer + Sliding Window
```
[Read 64px] → [Line Buffer] → [Sliding Window] → [64px/cycle] → [Write]
                                    ↓
                              21× Improvement
```

### V3: Dataflow Streaming
```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Read Stage │═══│ Process Stage│═══│  Write Stage │
│  (streaming) │   │  (parallel)  │   │  (streaming) │
└──────────────┘   └──────────────┘   └──────────────┘
         ↓                ↓                  ↓
        CONCURRENT EXECUTION → 64× Improvement
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| 📄 [Assignment Specification](docs/assigment-description-lab-2-en.pdf.pdf) | Original lab requirements |
| 📝 [Detailed Report](docs/report.pdf) | Full technical analysis and results |

---

<p align="center">
  ⬅️ <strong>Previous:</strong> <a href="../lab-1/">Lab 1</a> - Image Processing with Vitis HLS
</p>

