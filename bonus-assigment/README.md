# 🖥️ gem5 Processor Simulation & Performance Analysis

<div align="center">

![gem5](https://img.shields.io/badge/gem5-Simulator-blue?style=for-the-badge)
![SPEC CPU2006](https://img.shields.io/badge/SPEC-CPU2006-green?style=for-the-badge)
![ARM](https://img.shields.io/badge/Architecture-ARM-red?style=for-the-badge)

**A comprehensive analysis of processor performance using gem5 simulation and SPEC CPU2006 benchmarks**

> *Computer Architecture Lab - Bonus Assignment*
</div>

---

## 📑 Table of Contents

- [Part 1: Baseline Analysis \& Frequency Scaling](#part-1-baseline-analysis--frequency-scaling)
  - [Question 1: System Parameters](#question-1-system-parameters)
  - [Question 2: Baseline Performance Metrics](#question-2-baseline-performance-metrics)
  - [Question 3: Frequency Scaling](#question-3-frequency-scaling-1ghz-vs-4ghz)
  - [Question 4: Memory Technology Impact](#question-4-memory-technology-impact)

---

## Part 1: Baseline Analysis & Frequency Scaling

### Question 1: System Parameters

The following system parameters were extracted from the gem5 configuration files (`config.ini`):

#### Cache Configuration

| Component | Size | Associativity | Block Size | Latency |
|-----------|------|---------------|------------|---------|
| **L1 Instruction Cache** | 32 KB | 2-way | 64 bytes | 2 cycles |
| **L1 Data Cache** | 64 KB | 2-way | 64 bytes | 2 cycles |
| **L2 Cache** | 2 MB | 8-way | 64 bytes | 20 cycles |

#### Memory Subsystem

| Parameter | Value |
|-----------|-------|
| **Main Memory Type** | DDR3_1600_x64 |
| **Memory Capacity** | 512 MB |
| **Memory Clock Period (tCK)** | 1250 ps (800 MHz) |
| **CAS Latency (tCL)** | 13.75 ns |
| **RAS to CAS Delay (tRCD)** | 13.75 ns |
| **Bank Count** | 8 banks per rank |
| **Ranks per Channel** | 2 |

#### Clock Domains

| Clock Domain | Period | Frequency |
|--------------|--------|-----------|
| **System Clock** (`system.clk_domain`) | 1000 ps | 1 GHz |
| **CPU Clock** (`system.cpu_clk_domain`) | 500 ps | 2 GHz |

---

### Question 2: Baseline Performance Metrics

The following metrics were extracted from `stats.txt` for each SPEC CPU2006 benchmark (100M instructions):

| Benchmark | Sim Time (s) | Instructions | CPI | L1d Miss Rate | L1i Miss Rate | L2 Miss Rate |
|-----------|-------------|--------------|-----|---------------|---------------|--------------|
| **401.bzip2** | 0.0840 | 100M | 1.680 | 1.48% | 0.008% | 28.22% |
| **429.mcf** | 0.0647 | 100M | 1.294 | 0.21% | 2.36% | 5.51% |
| **456.hmmer** | 0.0594 | 100M | 1.188 | 0.16% | 0.022% | 7.82% |
| **458.sjeng** | 0.5135 | 100M | 10.271 | 12.18% | 0.002% | 99.99% |
| **470.lbm** | 0.1747 | 100M | 3.494 | 6.10% | 0.009% | 99.99% |

#### Key Observations

1. **bzip2** has moderate L1d miss rate (1.48%) but significant L2 miss rate (28%)
   - Data compression involves streaming through large datasets

2. **mcf** has high L1i miss rate (2.36%) but low overall miss rates
   - Graph-based algorithms with irregular instruction patterns

3. **hmmer** achieves the best CPI (1.188), closest to ideal IPC of 1.0
   - Very low cache miss rates across all levels
   - Excellent data locality and predictable access patterns

4. **sjeng** shows extremely poor performance (CPI = 10.271)
   - Nearly 100% L2 miss rate indicates working set far exceeds cache capacity
   - Memory-bound workload with severe cache thrashing

5. **lbm** exhibits memory-bound behavior (CPI = 3.494)
   - 99.99% L2 miss rate indicates streaming access patterns
   - Lattice Boltzmann Method involves large array operations

---

### Question 3: Frequency Scaling (1GHz vs 4GHz)

#### Clock Configuration Analysis

Three configurations were tested with different CPU clock frequencies:

| Configuration | `system.clk_domain` | `cpu_clk_domain` | CPU Frequency |
|--------------|---------------------|------------------|---------------|
| **Default** | 1000 ps | 500 ps | **2 GHz** |
| **1 GHz Test** | 1000 ps | 1000 ps | **1 GHz** |
| **4 GHz Test** | 1000 ps | 250 ps | **4 GHz** |

#### What Gets Clocked at Each Frequency?

**CPU Clock Domain (affected by `--cpu-clock`):**
- CPU pipeline stages (fetch, decode, execute, memory, writeback)
- L1 Instruction and Data caches
- L2 Cache
- TLBs and table walkers
- L1-to-L2 bus (`tol2bus`)

**System Clock Domain (remains constant at 1 GHz):**
- Memory controller (DRAM)
- Memory bus (`membus`)
- All DRAM timing parameters

#### 💡 Why This Separation?

The separation exists because:
1. **Memory technology limitations** — DRAM speeds are constrained by physical properties (capacitor charge/discharge times)
2. **Realistic modeling** — In real systems, DRAM cannot scale with CPU frequency
3. **Power/thermal constraints** — Memory runs at lower frequencies to manage power

> **❓ If we added another processor, its frequency would be determined by which clock domain it belongs to:**
> - Using `cpu_clk_domain` → Same frequency as the --cpu-clock parameter
> - Using its own domain → Would require explicit configuration

#### Frequency Scaling Results

##### Simulation Time (seconds)

| Benchmark | 1 GHz | 2 GHz (Default) | 4 GHz | Speedup (1→4 GHz) |
|-----------|-------|-----------------|-------|-------------------|
| **401.bzip2** | 0.1610 | 0.0840 | 0.0457 | 3.52× |
| **429.mcf** | 0.1273 | 0.0647 | 0.0333 | 3.82× |
| **456.hmmer** | 0.1185 | 0.0594 | 0.0298 | 3.98× |
| **458.sjeng** | 0.7041 | 0.5135 | 0.4175 | 1.69× |
| **470.lbm** | 0.2623 | 0.1747 | 0.1327 | 1.98× |

##### CPI (Cycles Per Instruction)

| Benchmark | 1 GHz | 2 GHz (Default) | 4 GHz | Change (1→4 GHz) |
|-----------|-------|-----------------|-------|------------------|
| **401.bzip2** | 1.610 | 1.680 | 1.828 | +13.5% |
| **429.mcf** | 1.273 | 1.294 | 1.334 | +4.8% |
| **456.hmmer** | 1.185 | 1.188 | 1.193 | +0.7% |
| **458.sjeng** | 7.041 | 10.271 | 16.701 | +137% |
| **470.lbm** | 2.623 | 3.494 | 5.307 | +102% |

> **Note:** Cache miss rates (L1d, L1i, L2) remain unchanged across all frequencies, as they depend on memory access patterns rather than clock speed.

##### Key Insights

The scaling is **NOT perfect** due to:

1. **Memory Bottleneck** — Memory latency remains constant regardless of CPU speed
   - At 4 GHz, the CPU experiences more "wait cycles" for memory operations
   - The ratio of memory latency to CPU cycle time increases 4×

2. **Amdahl's Law** — Memory-bound portions don't scale with CPU frequency
   
3. **Cache Miss Penalty** — Fixed memory latency means:
   - At 1 GHz: 50 ns DRAM latency = 50 CPU cycles
   - At 4 GHz: 50 ns DRAM latency = 200 CPU cycles (4× more stalls)

**Benchmark Classification:**
- **Compute-bound** (hmmer, mcf): Near-ideal 4× speedup, minimal CPI increase
- **Memory-bound** (sjeng, lbm): Poor scaling (~2× speedup), CPI more than doubles

---

### Question 4: Memory Technology Impact

#### Experiment Setup

Two benchmarks were re-run with upgraded memory:
- **Original**: DDR3_1600_x64 (tCK = 1250 ps, 800 MHz)
- **Upgraded**: DDR3_2133_x64 (tCK = 938 ps, 1066 MHz)

| Aspect | DDR3_1600 | DDR3_2133 | Change |
|--------|-----------|-----------|--------|
| **Memory Clock** | 800 MHz | 1066 MHz | +33% |
| **Peak Bandwidth** | 12.8 GB/s | 17.0 GB/s | +33% |

#### Benchmark Results

| Benchmark | Memory | Sim Time (s) | CPI | Improvement |
|-----------|--------|--------------|-----|-------------|
| **456.hmmer** | DDR3_1600 | 0.059395 | 1.1879 | — |
| **456.hmmer** | DDR3_2133 | 0.059383 | 1.1877 | **0.02%** |
| **458.sjeng** | DDR3_1600 | 0.513526 | 10.2705 | — |
| **458.sjeng** | DDR3_2133 | 0.493128 | 9.8626 | **4.0%** |

> **Note:** Cache miss rates remain identical between DDR3_1600 and DDR3_2133, as expected.

#### Analysis

The results confirm the expected behavior:

1. **hmmer (compute-bound, 7.8% L2 miss rate)**: 
   - Negligible improvement (0.02%)
   - Excellent cache behavior means few main memory accesses
   - Faster memory provides almost no benefit

2. **sjeng (memory-bound, 99.99% L2 miss rate)**:
   - Measurable improvement (4.0%)
   - Nearly every L2 access results in a main memory fetch
   - Higher bandwidth reduces memory stall cycles

**Key Insight:** Memory upgrade impact scales with L2 miss rate:
- **Low L2 miss rate** → Minimal benefit (compute-bound)
- **High L2 miss rate** → Significant benefit (memory-bound)

---

## 📁 Repository Structure

```
bonus-assignment/
├── 📂 results/
│   ├── 📂 default/          # Baseline runs (2 GHz CPU)
│   │   ├── specbzip/
│   │   ├── spechmmer/
│   │   ├── specmcf/
│   │   ├── specsjeng/
│   │   └── speclibm/
│   ├── 📂 1GHz/              # 1 GHz CPU frequency tests
│   ├── 📂 4GHz/              # 4 GHz CPU frequency tests
│   └── 📂 memory_test/       # DDR3_2133 memory tests
├── 📂 shared/
│   └── final.md              # Assignment specification
└── 📜 README.md              # This file
```

---

## 🔧 Tools & Technologies

| Tool | Purpose |
|------|---------|
| **gem5** | Full-system architectural simulator |
| **SPEC CPU2006** | Industry-standard benchmark suite |
| **MinorCPU** | In-order pipeline model in gem5 |
| **GNU Parallel** | Parallel benchmark execution |

---

<div align="center">

**Computer Architecture Lab - Bonus Assignment**

*Performance analysis through simulation enables us to understand the complex interplay between processor microarchitecture and memory hierarchy design decisions.*

</div>
