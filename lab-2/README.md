# Lab 2: Image Processing Accelerator with Sharpening Filter

**Author:** Fraidakis Ioannis  
**Institution:** Aristotle University of Thessaloniki  
**Date:** December 2025

---

## 📋 Overview

This lab extends the previous work by adding a **3×3 Laplacian-based sharpening filter** to the image processing pipeline. The accelerator performs three operations in sequence:

1. **Absolute Difference**: `D[i][j] = |A[i][j] - B[i][j]|`
2. **Posterization**: Map D to discrete levels (0, 128, or 255)
3. **Sharpen Filter**: Apply a 3×3 Laplacian convolution kernel

Three architectural implementations (V1, V2, V3) explore optimization strategies for throughput and resource utilization.

---

## 🎯 Objectives

- Implement FPGA-based image processing with convolution filters
- Compare sequential vs dataflow streaming architectures
- Analyze HLS optimization pragmas (PIPELINE, DATAFLOW, ARRAY_PARTITION)
- Understand memory bandwidth bottlenecks and burst transfers

---

## 📁 Directory Structure

```
lab-2/
├── docs/                    # Documentation
│   ├── report.tex           # Detailed technical report (LaTeX)
│   ├── report.pdf           # Compiled report
│   └── assets/              # Images and figures
├── inc/                     # Header files
├── src_hw/                  # Hardware accelerator implementations
│   ├── accelerated_v1.cpp   # V1: Sequential with 2D buffers
│   ├── accelerated_v2.cpp   # V2: Sequential with line buffers
│   └── accelerated_v3.cpp   # V3: Dataflow streaming
├── src_sw/                  # Software components
│   ├── host.cpp             # OpenCL host application
│   ├── hls_tb.cpp           # HLS testbench
│   └── xcl2.*               # Xilinx OpenCL utilities
└── README.md                # This file
```

---

## 🔧 Implementation Versions

### Version 1: Sequential Three-Stage Pipeline
- **File:** `src_hw/accelerated_v1.cpp`
- Uses 2D local BRAM buffers with full-frame buffering
- Filter stage processes **1 pixel/cycle** (bottleneck)
- HLS Latency: ~67,632 cycles

### Version 2: Sequential with Line Buffers  
- **File:** `src_hw/accelerated_v2.cpp`
- Sliding window approach with line buffers
- All stages process **64 pixels/cycle**
- HLS Latency: ~3,104 cycles (**21× faster** than V1)

### Version 3: Dataflow Streaming Architecture
- **File:** `src_hw/accelerated_v3.cpp`
- `#pragma HLS DATAFLOW` for concurrent stage execution
- Stages connected via `hls::stream<uint512_t>`
- HLS Latency: ~1,049 cycles (**64× faster** than V1)

---

## 📊 Performance Summary

| Metric              | V1        | V2        | V3        |
|---------------------|-----------|-----------|-----------|
| HLS Latency (cycles)| 67,632    | 3,104     | 1,049     |
| CU Time (µs @ 300MHz)| 230      | 15        | 5         |
| BRAM_18K            | 256       | 30        | 0         |
| Throughput          | 1 px/cyc  | 64 px/cyc | 64 px/cyc |

---

## 🚀 Getting Started

### Prerequisites

- Xilinx Vitis HLS
- Xilinx Vitis Unified IDE
- Alveo U200 or compatible FPGA board (for hardware execution)

### Building & Running

1. **Launch Vitis IDE:**
   - Open Vitis IDE (write `vitis` in the terminal)
   - Select a workspace directory

2. **Create New Application Project:**
   - Click **File → New → Application Project**
   - Configure project name and platform (eg `lab-2` and `Alveo U200`)

3. **Add Host Files:**
   - Navigate to `host/src` in your project
   - Add all files from `src_sw/`:
     - `host.cpp` (main host application)
     - `xcl2.cpp` and `xcl2.hpp` (OpenCL utilities)
     - `event_timer.cpp` and `event_timer.hpp`

4. **Add Kernel Files:**
   - Navigate to `kernel/src` in your project
   - Add your chosen accelerator version from `src_hw/`:
     - `accelerated_v1.cpp` (Sequential with 2D buffers)
     - `accelerated_v2.cpp` (Line buffers) 
     - `accelerated_v3.cpp` (Dataflow streaming)

5. **Configure Kernel:**
   - Open the `.prj` file of kernel directory
   - Set the accelerated kernel configuration
   - Ensure top function is `IMAGE_DIFF_POSTERIZE`

6. **Build and Run:**
   - Select **Emulation-HW** as target
   - Click **Build** to compile host and synthesize kernel
   - Click **Run** to execute hardware emulation

> 📘 For more detailed step-by-step instructions, see the [Vitis IDE Tutorial](docs/vitis-ide-tutorial.pdf).

---

**Previous**: [Lab 1](../lab-1/)
