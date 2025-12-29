<p align="center">
  <h1 align="center">Lab 1: Image Difference with Hardware Acceleration</h1>
  <p align="center">
    <strong>Posterized Image Difference Algorithm using Xilinx Vitis HLS</strong>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Tool-Vitis%20HLS-FF6C00?style=flat-square&logo=xilinx&logoColor=white" alt="Vitis HLS">
  <img src="https://img.shields.io/badge/Language-C%2FC%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white" alt="C/C++">
  <img src="https://img.shields.io/badge/Interface-AXI-2196F3?style=flat-square" alt="AXI">
  <img src="https://img.shields.io/badge/Parallelism-64%20px%2Fcycle-4CAF50?style=flat-square" alt="Parallelism">
</p>

---

## 📋 Overview

This lab implements a hardware-accelerated **image difference algorithm** that compares two grayscale images and produces a posterized difference visualization with three levels:

| Difference Value | Output | Visual |
|:---------------:|:------:|:------:|
| D < 32 | **0** | ⬛ Black |
| 32 ≤ D < 96 | **128** | 🔲 Gray |
| D ≥ 96 | **255** | ⬜ White |

---

## 📁 Directory Structure

```
lab-1/
├── docs/
│   ├── assigment-description-lab-1.pdf  # Assignment specification
│   └── report.pdf                       # Technical report
├── i
│   └── image_defines.h                  # Common definitions and types
├── s
│   ├── image_diff_baseline.c            # Software baseline implementation
│   ├── image_diff_accelarated.cpp       # HLS-optimized FPGA implementation
│   └── tb_image_diff.c                  # Testbench for verification
└── README.md                            # This file
```

---

## Implementation Details

### Key Components

<table>
<tr>
<td width="33%">

#### 1️⃣ Baseline
**`image_diff_baseline.c`**

- Pure C implementation
- Sequential pixel processing
- Reference for verification

</td>
<td width="33%">

#### 2️⃣ Accelerated
**`image_diff_accelarated.cpp`**

- HLS-optimized for FPGA
- **64 pixels** in parallel
- AXI memory interfaces

</td>
<td width="33%">

#### 3️⃣ Testbench
**`tb_image_diff.c`**

- Random image generation
- HW vs SW comparison
- Statistical analysis

</td>
</tr>
</table>

### Algorithm

```
For each pixel (i,j):
  1. D = |A[i,j] - B[i,j]|           // Absolute difference
  2. Apply posterization:
     - If D < 32:     C[i,j] = 0      // Black
     - If 32 ≤ D < 96: C[i,j] = 128   // Gray
     - If D ≥ 96:     C[i,j] = 255    // White
```

---

## Building with Vitis HLS

### Step 1: Create New Project

1. **Launch Vitis HLS** → Select workspace directory
2. **File → New Project**
   - **Project name:** `image_diff_hls`
   - **Location:** Your `lab-1` directory
3. Click **Next**

### Step 2: Add Design Files

| Action | File | Setting |
|--------|------|---------|
| Add File | `src/image_diff_accelarated.cpp` | **Top Function:** `IMAGE_DIFF_POSTERIZE` |

### Step 3: Add Testbench Files

| Action | File |
|--------|------|
| Add File | `src/tb_image_diff.c` |

### Step 4: Configure Solution

| Setting | Value |
|---------|-------|
| **Solution name** | `solution1` |
| **Clock Period** | `10` ns (100 MHz) |
| **Part** | Your target device (e.g., `xcvu9p-flga2104-2-i`) |

### Step 5: Configure Include Paths

1. Right-click on source files → **Properties**
2. Under **C/C++ Build → Settings**
3. Add include path: `../inc`

### Step 6: Run Simulation & Synthesis

| Step | Action | Shortcut |
|------|--------|----------|
| 1️⃣ | **Run C Simulation** | Verify "Test Passed" |
| 2️⃣ | **Run C Synthesis** | `Ctrl+R` |
| 3️⃣ | **Run C/RTL Co-simulation** | Optional |
| 4️⃣ | **Export RTL** | IP Catalog format |

---

## 📊 Viewing Results

### Synthesis Report Navigation

```
solution1/
└── syn/
    └── report/
        └── IMAGE_DIFF_POSTERIZE_csynth.rpt
```

### Key Metrics to Check

| Metric | Description |
|--------|-------------|
| **Timing** | Clock constraint satisfaction |
| **Latency** | Min/Max/Avg cycles |
| **Interval** | Throughput (cycles between calls) |
| **Loop Analysis** | II achieved for each loop |

### Additional Views

- **Resource Utilization** - BRAM, DSP, FF, LUT usage
- **Interface Summary** - AXI interface details
- **Schedule Viewer** - Cycle-by-cycle execution (Analysis Perspective)
- **Waveform Viewer** - Signal transitions (after co-simulation)

---

## Performance Characteristics

<table>
<tr>
<th width="50%">Baseline (Software)</th>
<th width="50%">Accelerated (Hardware)</th>
</tr>
<tr>
<td>

- **Processing**: 1 pixel/iteration
- **Memory Access**: Random pattern
- **Platform**: CPU
- **Iterations**: ~65,536

</td>
<td>

- **Processing**: 64 pixels/cycle
- **Memory Access**: 512-bit bursts
- **Platform**: FPGA
- **Iterations**: ~1,024

</td>
</tr>
</table>

### 📈 Expected Speedup

For a **256×256 image** (65,536 pixels):

| Version | Iterations | Theoretical Speedup |
|---------|------------|:------------------:|
| Baseline | 65,536 | 1× |
| Accelerated | 1,024 | **64×** |

---

## Testing

The testbench performs comprehensive validation:

```
1. Input Generation   → Random 256×256 images with controlled noise
2. Dual Execution     → Runs both SW and HW implementations
3. Validation         → Pixel-by-pixel comparison
4. Statistics         → Reports distribution of posterized values
```

### ✅ Expected Output

```
Starting Testbench for IMAGE_DIFF_POSTERIZE...
Image Size: 256x256 (65536 pixels)
Thresholds: THRESH_LOW=32, THRESH_HIGH=96

--- Validation Results ---
*** Test Passed ***

--- Statistics ---
Black Pixels (0):   22145
Gray Pixels (128):  28934
White Pixels (255): 14457
Total Pixels:       65536
```

---

## HLS Optimization Techniques

| Technique | Pragma | Effect |
|-----------|--------|--------|
| **Pipeline** | `#pragma HLS PIPELINE II=1` | Overlapped loop execution, 1 cycle/iteration |
| **Unroll** | `#pragma HLS UNROLL` | 64 parallel processing units |
| **Wide Data** | `uint512_t` | 512-bit bus, 64 pixels/access |
| **AXI Bundles** | `gmemA`, `gmemB`, `gmemC` | Concurrent memory access |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| 📄 [Assignment Specification](docs/assigment-description-lab-1.pdf) | Original lab requirements |
| 📝 [Detailed Report](docs/report.pdf) | Full technical analysis and results |

---

<p align="center">
  <strong>Next Steps:</strong> Proceed to <a href="../lab-2/">Lab 2</a> to deploy on Vitis IDE with advanced dataflow architectures.
</p>
