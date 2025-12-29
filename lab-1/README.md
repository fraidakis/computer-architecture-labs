# Lab 1: Image Difference with Hardware Acceleration

This lab implements a hardware-accelerated image difference algorithm with posterization using Xilinx High-Level Synthesis (HLS).

## 📋 Overview

The project compares two grayscale images and produces a posterized difference visualization with three levels:
- **Black (0)**: Minimal difference (< 32)
- **Gray (128)**: Moderate difference (32-95)
- **White (255)**: Significant difference (≥ 96)

## 🎯 Objectives

1. Understand pixel-wise image operations
2. Learn HLS optimization techniques for FPGA acceleration
3. Implement memory-mapped AXI interfaces
4. Optimize for throughput using pipelining and unrolling

## 📁 Directory Structure

```
lab-1/
├── docs/
│   └── assigment-description-lab-1.pdf    # Assignment specification
├── inc/
│   └── image_defines.h                     # Common definitions and types
├── src/
│   ├── image_diff_baseline.c               # Software baseline implementation
│   ├── image_diff_accelarated.cpp          # HLS-optimized FPGA implementation
│   └── tb_image_diff.c                     # Testbench for verification
└── README.md                               # This file
```

## 🔧 Implementation Details

### Key Components

#### 1. **Baseline Implementation** (`image_diff_baseline.c`)
- Pure C implementation for reference
- Sequential processing of all pixels
- Used for correctness verification

#### 2. **Accelerated Implementation** (`image_diff_accelarated.cpp`)
- HLS-optimized for FPGA synthesis
- Processes 64 pixels in parallel (512-bit data path)
- Target: 1 cycle per 64-pixel chunk (II=1)
- Uses AXI memory-mapped interfaces

#### 3. **Testbench** (`tb_image_diff.c`)
- Generates random test images (256×256)
- Compares HW vs SW implementations
- Provides statistical analysis of results

### Algorithm

```
For each pixel (i,j):
  1. D = |A[i,j] - B[i,j]|           // Absolute difference
  2. Apply posterization:
     - If D < 32:     C[i,j] = 0      // Black
     - If 32 ≤ D < 96: C[i,j] = 128   // Gray
     - If D ≥ 96:     C[i,j] = 255    // White
```

## 🏗️ Building the Project

### HLS Synthesis (Xilinx Vitis HLS)

1. **Launch Vitis HLS:**
   - Open Vitis HLS application
   - Select a workspace directory (can be anywhere)

2. **Create New Project:**
   - Click **File → New Project**
   - **Project name:** `image_diff_hls`
   - **Location:** Browse to your `lab-1` directory
   - Click **Next**

3. **Add Design Files:**
   - Click **Add Files...**
   - Select `src/image_diff_accelarated.cpp`
   - **Top Function:** Enter `IMAGE_DIFF_POSTERIZE`
   - Click **Next**

4. **Add Testbench Files:**
   - Click **Add Files...**
   - Select `src/tb_image_diff.c`
   - Click **Next**

5. **Solution Configuration:**
   - **Solution name:** `solution1`
   - **Clock Period:** `10` (ns) → 100 MHz
   - **Part Selection:**
     - Click **...** button
     - Search for your target device (e.g., `xcvu9p-flga2104-2-i`)
     - Or select from boards/devices list
   - Click **Finish**

6. **Configure Include Paths:**
   - Right-click on `image_diff_accelarated.cpp` in Explorer
   - Select **Properties**
   - Under **C/C++ Build → Settings**
   - Add include path: `../inc` or absolute path to `inc` directory
   - Repeat for testbench files

7. **Run C Simulation:**
   - Click **Project → Run C Simulation**
   - Or click the ▶️ **Run C Simulation** button in toolbar
   - Verify output shows "Test Passed"

8. **Run C Synthesis:**
   - Click **Solution → Run C Synthesis → Active Solution**
   - Or press **Ctrl+R** (Windows) / **Cmd+R** (Mac)
   - Wait for synthesis to complete
   - Review synthesis report (opens automatically)

9. **Run C/RTL Co-simulation:**
   - Click **Solution → Run C/RTL Cosimulation**
   - Select **RTL:** `Verilog` or `VHDL`
   - Enable **Dump Trace:** `all` (optional, for waveform viewing)
   - Click **OK**

10. **Export RTL (Optional):**
    - Click **Solution → Export RTL**
    - Select format: **IP Catalog** or **System Generator**
    - Click **OK**

### Viewing Results in Vitis HLS GUI

After synthesis completes, you can view various reports:

1. **Synthesis Report:**
   - Navigate to **Explorer** panel
   - Expand **solution1 → syn → report**
   - Double-click `IMAGE_DIFF_POSTERIZE_csynth.rpt`
   - **Key Metrics:**
     - **Timing:** Check if clock constraint is met
     - **Latency:** Min/Max/Avg cycles to complete
     - **Interval:** Throughput (cycles between function calls)
     - **Loop Analysis:** Shows II achieved for each loop

2. **Resource Utilization:**
   - In synthesis report, scroll to **Utilization Estimates**
   - Shows: BRAM, DSP, FF (Flip-Flops), LUT usage
   - Compare with available resources on target device

3. **Interface Summary:**
   - Shows AXI interface details
   - Memory bundles (gmemA, gmemB, gmemC)
   - Control interface (s_axilite)

4. **Schedule Viewer (Analysis Perspective):**
   - Click **Perspective → Analysis** (top-right corner)
   - Shows cycle-by-cycle execution schedule
   - Visualizes pipeline behavior and data dependencies

5. **Waveform Viewer (After Co-simulation):**
   - Double-click on `.wdb` file in **sim/verilog** folder
   - Opens Vivado waveform viewer
   - Inspect signal transitions and timing

## 📊 Performance Characteristics

### Baseline (Software)
- **Processing**: Sequential, 1 pixel per iteration
- **Memory Access**: Random access pattern
- **Target Platform**: CPU

### Accelerated (Hardware)
- **Processing**: 64 pixels per cycle
- **Memory Access**: Burst transfers (512-bit wide)
- **Pipeline II**: 1 (one chunk per cycle)
- **Target Platform**: FPGA (Xilinx UltraScale+)

### Expected Speedup
For a 256×256 image (65,536 pixels):
- **Baseline**: ~65,536 iterations
- **Accelerated**: ~1,024 chunks (64× fewer iterations)
- **Theoretical Speedup**: Up to 64× (with optimal memory bandwidth)

## 🧪 Testing

The testbench (`tb_image_diff.c`) performs:

1. **Input Generation**: Random 256×256 images with controlled noise
2. **Dual Execution**: Runs both SW and HW implementations
3. **Validation**: Compares outputs pixel-by-pixel
4. **Statistics**: Reports distribution of posterized values

### Expected Output

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

## 🔍 HLS Optimization Techniques Used

1. **Pipeline Directive**: `#pragma HLS PIPELINE II=1`
   - Enables overlapped execution of loop iterations
   - Target initiation interval of 1 cycle

2. **Unroll Directive**: `#pragma HLS UNROLL`
   - Fully unrolls the 64-pixel processing loop
   - Creates 64 parallel processing units

3. **Wide Data Types**: `uint512_t` (512-bit)
   - Matches FPGA bus width for efficient transfers
   - Enables 64-pixel parallel processing

4. **AXI Memory-Mapped Interfaces**:
   - Separate bundles for A, B, C (gmemA, gmemB, gmemC)
   - Enables concurrent memory access
   - Optimizes memory bandwidth utilization

## 📚 Documentation

- 📄 [Assignment Specification](docs/assigment-description-lab-1.pdf) - Original lab requirements
- 📝 [Detailed Report](docs/report.pdf) - Full technical analysis and results

---

**Next Steps**: Proceed to [Lab 2](../lab-2/) to deploy on Vitis IDE.
