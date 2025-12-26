# Vector Addition (VADD) - Vitis HLS Kernel Example

This directory contains a complete Vitis application demonstrating **hardware-accelerated vector addition** on Xilinx FPGAs. It serves as a foundational example for understanding the Vitis development flow.

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Architecture](#architecture)
4. [Kernel Code (hw_src/vadd.cpp)](#kernel-code-hw_srcvaddcpp)
5. [Host Application (sw_src/host.cpp)](#host-application-sw_srchostcpp)
6. [Utility Files](#utility-files)
7. [Data Flow](#data-flow)
8. [HLS Pragmas Explained](#hls-pragmas-explained)
9. [Building and Running](#building-and-running)
10. [Comparison with Vitis HLS](#comparison-with-vitis-hls)

---

## Overview

**Purpose**: Compute `C[i] = A[i] + B[i]` for i = 0 to DATA_SIZE-1

**Key Concepts Demonstrated**:
- Hardware/Software partitioning (kernel vs host)
- AXI memory interfaces for FPGA ↔ DDR communication
- OpenCL runtime for FPGA programming
- Burst memory transfers for efficiency
- Local buffering for hiding memory latency

---

## Directory Structure

```
vadd/
├── hw_src/                    # Hardware (FPGA) source code
│   └── vadd.cpp               # HLS kernel - synthesized to RTL
│
└── sw_src/                    # Software (CPU) source code
    ├── host.cpp               # Main application - runs on CPU
    ├── xcl2.hpp               # Xilinx OpenCL utility declarations
    ├── xcl2.cpp               # Xilinx OpenCL utility implementations
    ├── event_timer.hpp        # Timing utility declarations
    └── event_timer.cpp        # Timing utility implementations
```

### hw_src/ vs sw_src/

| Directory | Execution Location | Compilation | Purpose |
|-----------|-------------------|-------------|---------|
| `hw_src/` | **FPGA fabric** | Vitis HLS → RTL → Bitstream | Accelerated computation |
| `sw_src/` | **CPU (x86/ARM)** | GCC/Clang | Control, data management, verification |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOST (CPU)                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  host.cpp                                                               │ │
│  │  ├── Allocate aligned memory (source_in1, source_in2, source_hw_results)│ │
│  │  ├── Generate test data                                                 │ │
│  │  ├── Compute software reference                                         │ │
│  │  ├── OpenCL Setup (find device, load xclbin, create kernel)            │ │
│  │  ├── Create cl::Buffer objects                                          │ │
│  │  ├── Set kernel arguments                                               │ │
│  │  ├── enqueueMigrateMemObjects (Host → Device)                          │ │
│  │  ├── enqueueTask (launch kernel)                                        │ │
│  │  ├── enqueueMigrateMemObjects (Device → Host)                          │ │
│  │  └── Verify results                                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    │ PCIe / AXI                              │
│                                    ▼                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                              FPGA DEVICE                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  DDR Memory (Global Memory)                                             │ │
│  │  ├── in1[0..4095]   ← Input vector 1                                   │ │
│  │  ├── in2[0..4095]   ← Input vector 2                                   │ │
│  │  └── out_r[0..4095] ← Output vector                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                          │         │         │                               │
│                          │ AXI-MM  │ AXI-MM  │ AXI-MM (m_axi gmem)          │
│                          ▼         ▼         ▼                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  VADD Kernel (hw_src/vadd.cpp → synthesized to hardware)               │ │
│  │                                                                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │ │
│  │  │ v1_buffer    │  │ v2_buffer    │  │ vout_buffer  │ ← Local BRAM     │ │
│  │  │ [1024]       │  │ [1024]       │  │ [1024]       │                  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │ │
│  │         │                 │                 ▲                           │ │
│  │         └────────────────►│◄────────────────┘                           │ │
│  │                           │                                             │ │
│  │                    ┌──────▼──────┐                                      │ │
│  │                    │   ADDER     │ ← Pipelined (II=1)                   │ │
│  │                    └─────────────┘                                      │ │
│  │                                                                         │ │
│  │  AXI-Lite Control Interface (s_axilite)                                │ │
│  │  ├── Register: in1 pointer                                              │ │
│  │  ├── Register: in2 pointer                                              │ │
│  │  ├── Register: out_r pointer                                            │ │
│  │  ├── Register: size                                                     │ │
│  │  └── Control: start/done/idle                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Kernel Code (hw_src/vadd.cpp)

### Complete Annotated Source

```cpp
#define BUFFER_SIZE 1024    // Local buffer size (elements per burst)
#define DATA_SIZE 4096      // Total elements to process

// TRIPCOUNT hints for HLS latency estimation (not functional)
const unsigned int c_len = DATA_SIZE / BUFFER_SIZE;  // = 4 iterations
const unsigned int c_size = BUFFER_SIZE;              // = 1024 elements

extern "C" {  // ← CRITICAL: Required for Vitis to find the kernel symbol

void vadd(
    const unsigned int *in1,  // Read-Only Vector 1
    const unsigned int *in2,  // Read-Only Vector 2
    unsigned int *out_r,      // Output Result
    int size                  // Size in integer
) {
```

### AXI Interface Pragmas

```cpp
// Memory-Mapped AXI Master interface for DDR access
// All three arrays share the same "gmem" bundle (same memory port)
#pragma HLS INTERFACE m_axi port=in1 offset=slave bundle=gmem
#pragma HLS INTERFACE m_axi port=in2 offset=slave bundle=gmem
#pragma HLS INTERFACE m_axi port=out_r offset=slave bundle=gmem

// AXI-Lite Slave interface for control registers
// The host writes pointers and size through these registers
#pragma HLS INTERFACE s_axilite port=in1 bundle=control
#pragma HLS INTERFACE s_axilite port=in2 bundle=control
#pragma HLS INTERFACE s_axilite port=out_r bundle=control
#pragma HLS INTERFACE s_axilite port=size bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control  // start/done/idle
```

### Local Buffers

```cpp
unsigned int v1_buffer[BUFFER_SIZE];   // 1024 × 4 bytes = 4 KB BRAM
unsigned int v2_buffer[BUFFER_SIZE];   // 1024 × 4 bytes = 4 KB BRAM
unsigned int vout_buffer[BUFFER_SIZE]; // 1024 × 4 bytes = 4 KB BRAM
```

**Why Local Buffers?**
- DDR memory has high latency (~100+ cycles)
- BRAM has 1-cycle access
- Burst transfers hide DDR latency
- Local computation is fast

### Main Processing Loop

```cpp
// Process data in chunks of BUFFER_SIZE
for (int i = 0; i < size; i += BUFFER_SIZE) {
#pragma HLS LOOP_TRIPCOUNT min=c_len max=c_len  // Hint: 4 iterations

    int chunk_size = BUFFER_SIZE;
    if ((i + BUFFER_SIZE) > size)
        chunk_size = size - i;  // Handle last partial chunk

    // STAGE 1: Burst read vector 1
    read1:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS LOOP_TRIPCOUNT min=c_size max=c_size
#pragma HLS PIPELINE II=1  // One element per clock cycle
        v1_buffer[j] = in1[i + j];
    }

    // STAGE 2: Burst read vector 2
    read2:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS LOOP_TRIPCOUNT min=c_size max=c_size
#pragma HLS PIPELINE II=1
        v2_buffer[j] = in2[i + j];
    }

    // STAGE 3: Vector addition (from local buffers)
    vadd:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS LOOP_TRIPCOUNT min=c_size max=c_size
#pragma HLS PIPELINE II=1
        vout_buffer[j] = v1_buffer[j] + v2_buffer[j];
    }

    // STAGE 4: Burst write results
    write:
    for (int j = 0; j < chunk_size; j++) {
#pragma HLS LOOP_TRIPCOUNT min=c_size max=c_size
#pragma HLS PIPELINE II=1
        out_r[i + j] = vout_buffer[j];
    }
}
```

---

## Host Application (sw_src/host.cpp)

### Step-by-Step Execution Flow

#### 1. Parse Command Line
```cpp
if (argc != 2) {
    std::cout << "Usage: " << argv[0] << " <XCLBIN File>" << std::endl;
    return EXIT_FAILURE;
}
std::string binaryFile = argv[1];  // Path to .xclbin file
```

#### 2. Allocate Aligned Memory
```cpp
// aligned_allocator ensures page-aligned memory for efficient DMA
std::vector<int, aligned_allocator<int>> source_in1(DATA_SIZE);
std::vector<int, aligned_allocator<int>> source_in2(DATA_SIZE);
std::vector<int, aligned_allocator<int>> source_hw_results(DATA_SIZE);
std::vector<int, aligned_allocator<int>> source_sw_results(DATA_SIZE);
```

**Why Aligned Memory?**
- DMA transfers are most efficient with page-aligned buffers (4KB boundary)
- Without alignment, the OpenCL runtime must copy data internally
- `aligned_allocator` uses `posix_memalign` (Linux) or `_aligned_malloc` (Windows)

#### 3. Generate Test Data
```cpp
std::generate(source_in1.begin(), source_in1.end(), std::rand);
std::generate(source_in2.begin(), source_in2.end(), std::rand);

for (int i = 0; i < DATA_SIZE; i++) {
    source_sw_results[i] = source_in1[i] + source_in2[i];  // Golden reference
    source_hw_results[i] = 0;  // Clear output buffer
}
```

#### 4. Find Xilinx Device
```cpp
auto devices = xcl::get_xil_devices();  // Returns all Xilinx FPGA devices
```

This function:
1. Queries all OpenCL platforms
2. Finds the "Xilinx" platform
3. Returns all accelerator devices on that platform

#### 5. Load Binary and Create Kernel
```cpp
auto fileBuf = xcl::read_binary_file(binaryFile);
cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};

for (unsigned int i = 0; i < devices.size(); i++) {
    auto device = devices[i];
    
    // Create OpenCL context for this device
    context = cl::Context(device, NULL, NULL, NULL, &err);
    
    // Create command queue with profiling enabled
    q = cl::CommandQueue(context, device, CL_QUEUE_PROFILING_ENABLE, &err);
    
    // Load the xclbin into the FPGA
    cl::Program program(context, {device}, bins, NULL, &err);
    
    if (err == CL_SUCCESS) {
        // Create kernel object
        krnl_vector_add = cl::Kernel(program, "vadd", &err);
        break;
    }
}
```

#### 6. Create Device Buffers
```cpp
cl::Buffer buffer_in1(
    context, 
    CL_MEM_USE_HOST_PTR | CL_MEM_READ_ONLY,  // Flags
    vector_size_bytes,                         // Size
    source_in1.data(),                         // Host pointer
    &err
);
```

**Buffer Flags Explained**:
| Flag | Meaning |
|------|---------|
| `CL_MEM_USE_HOST_PTR` | Use the provided host memory (zero-copy if aligned) |
| `CL_MEM_READ_ONLY` | Kernel will only read this buffer |
| `CL_MEM_WRITE_ONLY` | Kernel will only write this buffer |

#### 7. Set Kernel Arguments
```cpp
krnl_vector_add.setArg(0, buffer_in1);    // Matches: const unsigned int *in1
krnl_vector_add.setArg(1, buffer_in2);    // Matches: const unsigned int *in2
krnl_vector_add.setArg(2, buffer_output); // Matches: unsigned int *out_r
krnl_vector_add.setArg(3, size);          // Matches: int size
```

The argument order **must match** the kernel function signature!

#### 8. Transfer Data to Device
```cpp
q.enqueueMigrateMemObjects(
    {buffer_in1, buffer_in2},  // Which buffers to transfer
    0                           // 0 = from host to device
);
```

This initiates a DMA transfer from host DDR to FPGA DDR.

#### 9. Launch Kernel
```cpp
q.enqueueTask(krnl_vector_add);
```

For HLS kernels, always use `enqueueTask()` (not `enqueueNDRangeKernel`).

#### 10. Transfer Results Back
```cpp
q.enqueueMigrateMemObjects(
    {buffer_output}, 
    CL_MIGRATE_MEM_OBJECT_HOST  // Direction: device to host
);
q.finish();  // Wait for all operations to complete
```

#### 11. Verify Results
```cpp
bool match = true;
for (int i = 0; i < DATA_SIZE; i++) {
    if (source_hw_results[i] != source_sw_results[i]) {
        match = false;
        break;
    }
}
std::cout << "TEST " << (match ? "PASSED" : "FAILED") << std::endl;
```

---

## Utility Files

### xcl2.hpp / xcl2.cpp

**Purpose**: Xilinx OpenCL utility functions

| Function | Purpose |
|----------|---------|
| `xcl::get_xil_devices()` | Find all Xilinx FPGA devices |
| `xcl::read_binary_file()` | Load .xclbin file into memory |
| `xcl::is_emulation()` | Check if running in emulation mode |
| `aligned_allocator<T>` | Page-aligned memory allocator for efficient DMA |
| `OCL_CHECK(err, call)` | Macro for error checking OpenCL calls |

### event_timer.hpp / event_timer.cpp

**Purpose**: Measure execution time of different stages

```cpp
EventTimer et;
et.add("Step Name");   // Start timing
// ... do work ...
et.finish();           // Stop timing

et.print();            // Print all timings
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TIMELINE                                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ HOST CPU        ████ Allocate    ████ Gen Data    ████ Verify                │
│                      Memory            SW Ref                                 │
│                                                                               │
│ PCIe TRANSFER           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓           ▓▓▓▓▓▓▓▓                  │
│                         Host→Device               Device→Host                │
│                                                                               │
│ FPGA KERNEL                          ████████████████                        │
│                                      Burst Read 1                            │
│                                            ████████████████                  │
│                                            Burst Read 2                      │
│                                                  ████████████████            │
│                                                  Compute (VADD)              │
│                                                        ████████████████      │
│                                                        Burst Write           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## HLS Pragmas Explained

### Interface Pragmas

| Pragma | Purpose |
|--------|---------|
| `#pragma HLS INTERFACE m_axi port=X bundle=gmem` | Create AXI Master for memory access |
| `#pragma HLS INTERFACE s_axilite port=X bundle=control` | Create AXI-Lite register for parameter |
| `offset=slave` | Base address comes from the control interface |

### Optimization Pragmas

| Pragma | Purpose | Effect |
|--------|---------|--------|
| `#pragma HLS PIPELINE II=1` | Pipeline the loop | 1 iteration per clock cycle |
| `#pragma HLS LOOP_TRIPCOUNT min=N max=M` | Hint for latency estimation | No hardware effect |

---

## Performance Considerations

1. **Burst Length**: Larger `BUFFER_SIZE` = better DDR efficiency (up to a point)
2. **Pipeline II=1**: Essential for high throughput
3. **Memory Alignment**: Misaligned data causes extra copy operations
4. **Bundle Assignment**: Separate bundles allow parallel memory access

---

## References

- [Vitis Unified Software Platform Documentation](https://docs.xilinx.com/r/en-US/ug1393-vitis-application-acceleration)
- [Vitis HLS User Guide](https://docs.xilinx.com/r/en-US/ug1399-vitis-hls)
- [Xilinx Runtime (XRT) Documentation](https://xilinx.github.io/XRT/)
