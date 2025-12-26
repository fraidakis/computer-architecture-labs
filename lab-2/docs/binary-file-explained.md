# The XCLBIN Binary File Explained

This document explains the **binary file (XCLBIN)** used in Vitis FPGA applications — what it is, how it's produced, and how it's used to program Xilinx FPGAs like the Alveo U200.

---

## Table of Contents

1. [What Is the XCLBIN File?](#what-is-the-xclbin-file)
2. [Where Is It Located?](#where-is-it-located)
3. [How Is It Produced?](#how-is-it-produced)
4. [Why Is It Needed?](#why-is-it-needed)
5. [How Does the Host Use It?](#how-does-the-host-use-it)
6. [Platform Matching (Alveo U200)](#platform-matching-alveo-u200)
7. [Quick Reference](#quick-reference)

---

## What Is the XCLBIN File?

The `binaryFile` (passed as `argv[1]` to the host application) is an **XCLBIN file** — the compiled FPGA bitstream plus metadata.
! It is the procedure to build the kernel from SW/HW build, later given to the host application for the SW/HW emulation. !
It's the deployable artifact that contains everything needed to program the FPGA:

| Component | Description |
|-----------|-------------|
| **Bitstream** | The actual FPGA configuration (logic gates, routing, memory mappings) |
| **Metadata** | Kernel names, function arguments, memory interface definitions |
| **Debug info** | Symbols for profiling and debugging tools |
| **Platform info** | Target device family and version information |

### File Format

```
vadd.xclbin
├── Bitstream (.bit)           ← FPGA configuration
├── Kernel metadata (XML)      ← Argument types, names, interfaces
├── Memory topology            ← DDR bank assignments
└── Platform requirements      ← Target device specification
```

---

---

## How Is It Produced?

The XCLBIN is created through a **two-step compilation** using the Vitis `v++` compiler.

### Build Targets Comparison

| Target | Flag | Build Time | Purpose | Output |
|--------|------|------------|---------|--------|
| Software Emulation | `-t sw_emu` | **Seconds** | Functional testing (runs on CPU) | `vadd.xclbin` (stub) |
| Hardware Emulation | `-t hw_emu` | **Minutes** | Cycle-accurate RTL simulation | `vadd.xclbin` (simulation model) |
| Hardware | `-t hw` | **2-6 Hours** | Real FPGA bitstream | `vadd.xclbin` (actual bitstream) |

### Complete Build Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           VITIS BUILD FLOW                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  hw_src/vadd.cpp                                                             │
│       │                                                                      │
│       │  v++ -c (HLS Synthesis)                                              │
│       │  ├── Parse C++ code                                                  │
│       │  ├── Apply HLS pragmas                                               │
│       │  ├── Generate RTL (Verilog/VHDL)                                     │
│       │  └── Package as Xilinx Object                                        │
│       ▼                                                                      │
│  vadd.xo (Xilinx Object)                                                     │
│       │                                                                      │
│       │  v++ -l (Implementation)                                             │
│       │  ├── Synthesis (RTL → Netlist)                                       │
│       │  ├── Place & Route                                                   │
│       │  ├── Timing closure                                                  │
│       │  ├── Bitstream generation                                            │
│       │  └── Package with metadata                                           │
│       ▼                                                                      │
│  vadd.xclbin (Deployable Binary)                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Why Is It Needed?

The XCLBIN serves as the **bridge between software and hardware**:

### Development vs Runtime

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ BUILD TIME (Development Machine)                                            │
│                                                                             │
│   vadd.cpp ──v++ -c──► vadd.xo ──v++ -l──► vadd.xclbin                     │
│   (HLS C++)            (Object)            (FPGA Binary)                   │
│                                                                             │
│   This can be done on any machine with Vitis installed                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    │ Deploy to target machine
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RUNTIME (Machine with Alveo U200)                                           │
│                                                                             │
│   1. host.cpp reads vadd.xclbin from disk                                  │
│   2. OpenCL runtime loads it via PCIe to FPGA                              │
│   3. FPGA is configured with the vadd kernel                               │
│   4. Host can now invoke the kernel                                         │
│                                                                             │
│   Only needs: host executable + xclbin + XRT runtime                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How Does the Host Use It?

Here's the complete flow in `host.cpp`:

### Step-by-Step Code Walkthrough

```cpp
// ═══════════════════════════════════════════════════════════════════════════
// STEP 1: Get the binary file path from command line
// ═══════════════════════════════════════════════════════════════════════════
std::string binaryFile = argv[1];  // e.g., "vadd.xclbin"

// ═══════════════════════════════════════════════════════════════════════════
// STEP 2: Read the xclbin file into memory
// ═══════════════════════════════════════════════════════════════════════════
auto fileBuf = xcl::read_binary_file(binaryFile);
// fileBuf is now a std::vector<unsigned char> containing the entire file

// ═══════════════════════════════════════════════════════════════════════════
// STEP 3: Wrap it as an OpenCL binary
// ═══════════════════════════════════════════════════════════════════════════
cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};
// bins is a vector of (pointer, size) pairs - we have just one binary

// ═══════════════════════════════════════════════════════════════════════════
// STEP 4: Find available Xilinx devices
// ═══════════════════════════════════════════════════════════════════════════
auto devices = xcl::get_xil_devices();
// This queries PCIe for all Xilinx accelerator cards

// ═══════════════════════════════════════════════════════════════════════════
// STEP 5: Try to program each device until one succeeds
// ═══════════════════════════════════════════════════════════════════════════
for (unsigned int i = 0; i < devices.size(); i++) {
    auto device = devices[i];
    
    // Create OpenCL context for this device
    context = cl::Context(device, nullptr, nullptr, nullptr, &err);
    
    // Create command queue for sending commands
    q = cl::CommandQueue(context, device, CL_QUEUE_PROFILING_ENABLE, &err);
    
    // ═══════════════════════════════════════════════════════════════════════
    // STEP 6: Load the binary into the FPGA
    // ═══════════════════════════════════════════════════════════════════════
    cl::Program program(context, {device}, bins, nullptr, &err);
    
    if (err == CL_SUCCESS) {
        // Binary was accepted! The FPGA is now programmed.
        
        // ═══════════════════════════════════════════════════════════════════
        // STEP 7: Extract the kernel object for invocation
        // ═══════════════════════════════════════════════════════════════════
        krnl_vector_add = cl::Kernel(program, "vadd", &err);
        // "vadd" must match the extern "C" function name in the kernel
        
        valid_device = true;
        break;  // Found a compatible device!
    }
}
```
### Runtime Matching Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PLATFORM MATCHING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. xcl::get_xil_devices() queries PCIe bus                                │
│     └── Returns: ["xilinx_u200_gen3x16_xdma_2_202110_1", ...]              │
│                                                                             │
│  2. For each device, OpenCL extracts device info:                          │
│     device.getInfo<CL_DEVICE_NAME>()                                        │
│     └── Returns: "xilinx_u200_gen3x16_xdma_2_202110_1"                     │
│                                                                             │
│  3. cl::Program constructor validates binary:                               │
│     ├── Extract target platform from XCLBIN metadata                       │
│     ├── Compare with device platform string                                 │
│     │                                                                       │
│     │   XCLBIN target: "xilinx_u200_gen3x16_xdma_2_202110_1"              │
│     │   Device:        "xilinx_u200_gen3x16_xdma_2_202110_1"              │
│     │                   ✓ MATCH!                                           │
│     │                                                                       │
│     └── If matched: Load bitstream, return CL_SUCCESS                      │
│         If not:     Return CL_INVALID_BINARY                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---