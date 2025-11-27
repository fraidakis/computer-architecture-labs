# Computer Architecture Labs

This repository contains laboratory assignments for a Computer Architecture course, focusing on hardware acceleration, FPGA design, and high-level synthesis (HLS).

## 📁 Repository Structure

```
computer-architecture-labs/
├── lab-1/          # Image Processing with HLS
├── lab-2/          # [To be added]
├── lab-3/          # [To be added]
└── README.md       # This file
```

## 🚀 Getting Started

Each lab is self-contained with its own documentation, source code, and build instructions. Navigate to the respective lab directory to get started.

### Prerequisites

- **For Lab 1:**
  - GCC compiler with C/C++ support
  - Xilinx Vitis HLS (for hardware synthesis)
  - Basic understanding of image processing

## 📚 Labs Overview

### Lab 1: Image Difference with Hardware Acceleration

Implements a posterized image difference algorithm with both baseline (software) and accelerated (FPGA) versions using Xilinx HLS.

**Key Concepts:**
- Pixel-wise absolute difference
- Three-level posterization
- Memory-mapped AXI interfaces
- Pipeline optimization for FPGA

[→ Go to Lab 1](./lab-1/)

### Lab 2: [Coming Soon]

*Lab 2 content will be added here*

### Lab 3: [Coming Soon]

*Lab 3 content will be added here*

## 🛠️ Development Setup

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

## 📖 Additional Resources

- [Xilinx Vitis HLS Documentation](https://www.xilinx.com/products/design-tools/vitis/vitis-hls.html)
- [Computer Architecture: A Quantitative Approach](https://www.elsevier.com/books/computer-architecture/hennessy/978-0-12-811905-1)
