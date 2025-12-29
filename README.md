<p align="center">
  <h1 align="center">🖥️ Computer Architecture Labs</h1>
  <p align="center">
    <strong>Hardware Acceleration & High-Level Synthesis</strong>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Xilinx%20FPGA-FF6C00?style=for-the-badge&logo=xilinx&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/Tools-Vitis%20HLS%20%7C%20Vitis%20IDE-2196F3?style=for-the-badge" alt="Tools">
  <img src="https://img.shields.io/badge/Language-C%2FC%2B%2B-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white" alt="Language">
  <img src="https://img.shields.io/badge/Year-2025-4CAF50?style=for-the-badge" alt="Year">
</p>

<p align="center">
  <strong>Author:</strong> Fraidakis Ioannis<br>
  <strong>Institution:</strong> Aristotle University of Thessaloniki
</p>

---

## 📖 About

This repository contains laboratory assignments for a **Computer Architecture** course, focusing on **hardware acceleration**, **FPGA design**, and **high-level synthesis (HLS)**. The labs progressively explore image processing algorithms accelerated on Xilinx FPGAs.

---

## 📂 Repository Structure

```
computer-architecture-labs/
├── 📁 lab-1/           # Image Processing with Vitis HLS
├── 📁 lab-2/           # Image Processing Accelerator with Vitis IDE
└── 📄 README.md        # This file
```

---

## Labs Overview

<table>
<tr>
<td width="50%">

### Lab 1: Image Difference

**Tool:** Xilinx Vitis HLS

Implements a posterized image difference algorithm with both baseline (software) and accelerated (FPGA) versions.

**Key Concepts:**
- ✅ Pixel-wise absolute difference
- ✅ Three-level posterization
- ✅ Memory-mapped AXI interfaces
- ✅ Pipeline optimization for FPGA

<p align="center">
  <a href="./lab-1/"><strong>→ Go to Lab 1</strong></a>
</p>

</td>
<td width="50%">

### Lab 2: Image Processing Accelerator

**Tool:** Xilinx Vitis Unified IDE

Extends Lab 1 by adding a 3×3 Laplacian-based sharpening filter with three HLS architectural variants.

**Key Concepts:**
- ✅ Three-stage image pipeline
- ✅ Line buffer & sliding window
- ✅ HLS Dataflow streaming
- ✅ 512-bit AXI burst transfers

<p align="center">
  <a href="./lab-2/"><strong>→ Go to Lab 2</strong></a>
</p>

</td>
</tr>
</table>

---

## ⚙️ Prerequisites

| Lab | Tools Required | Description |
|:---:|----------------|-------------|
| **Lab 1** | Xilinx Vitis HLS | High-level synthesis and C simulation |
| **Lab 2** | Xilinx Vitis Unified IDE | Hardware emulation and FPGA deployment |

**Common Requirements:**
- GCC compiler with C/C++ support
- Basic understanding of image processing
- Target FPGA device (e.g., Alveo U200)

---

## 🛠️ Development Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/fraidakis/computer-architecture-labs.git
cd computer-architecture-labs
```

### 2️⃣ Navigate to a Lab

```bash
cd lab-1   # For HLS-based development
cd lab-2   # For Vitis IDE-based development
```

### 3️⃣ Follow Lab-Specific Instructions

Each lab contains detailed README documentation with step-by-step build and run instructions.

---

## 📚 Documentation

Each lab includes comprehensive documentation:

- **Assignment Specifications** - Original lab requirements
- **Technical Reports** - Detailed analysis and results
- **Code Comments** - Inline documentation and explanations

---

<p align="center">
  <strong>Course:</strong> Computer Architecture<br>
  <strong>Institution:</strong> Aristotle University of Thessaloniki<br>
  <strong>Semester:</strong> Fall 2025
</p>

