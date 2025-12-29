# Computer Architecture Labs
**Hardware Acceleration and High-Level Synthesis**  
**Author:** Fraidakis Ioannis  
**Institution:** Aristotle University of Thessaloniki  
**Date:** 2025  

This repository contains laboratory assignments for a Computer Architecture course, focusing on hardware acceleration, FPGA design, and high-level synthesis (HLS).

## Repository Structure

```
computer-architecture-labs/
├── lab-1/          # Image Processing with Vitis HLS
├── lab-2/          # Image Processing Accelerator with Vitis IDE
└── README.md       # This file
```

## Getting Started

Each lab is self-contained with its own documentation, source code, and build instructions. Navigate to the respective lab directory to get started.

### Prerequisites

- **For Lab 1:**
  - GCC compiler with C/C++ support
  - Xilinx Vitis HLS (for hardware synthesis)
  - Basic understanding of image processing

## Labs Overview

### Lab 1: Image Difference with Hardware Acceleration (Vitis HLS)

Implements a posterized image difference algorithm with both baseline (software) and accelerated (FPGA) versions using **Xilinx Vitis HLS** for high-level synthesis.

**Key Concepts:**
- Pixel-wise absolute difference
- Three-level posterization
- Memory-mapped AXI interfaces
- Pipeline optimization for FPGA

[→ Go to Lab 1](./lab-1/)

### Lab 2: Image Processing Accelerator with Sharpening Filter (Vitis IDE)

Extends Lab 1 by adding a 3×3 Laplacian-based sharpening filter to the image processing pipeline. Implements three HLS architectural variants using **Xilinx Vitis Unified IDE** for hardware emulation and deployment.

**Key Concepts:**
- Three-stage processing: Difference → Posterization → Sharpen Filter
- Line buffer and sliding window optimization
- HLS Dataflow streaming architecture
- AXI burst transfers with 512-bit memory interfaces

[→ Go to Lab 2](./lab-2/)

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/fraidakis/computer-architecture-labs.git
   cd computer-architecture-labs
   ```

2. **Navigate to a specific lab:**
   ```bash
   cd lab-1
   ```

3. **Follow the lab-specific README for build and run instructions**

---

**Course:** Computer Architecture  
**Institution:** Aristotle University of Thessaloniki  
**Semester:** Fall 2025
