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
- [Part 2: Design Exploration](#part-2-design-exploration--performance-optimization)
  - [Benchmark Characterization](#benchmark-characterization-summary)
  - [Optimal Cache Configurations](#optimal-cache-configurations)
  - [Running Optimized Benchmarks](#running-optimized-benchmarks)

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

#### CPU Configuration

| Parameter | Value |
|-----------|-------|
| **CPU Type** | MinorCPU (in-order pipeline) |
| **Max Instructions** | 100,000,000 |
| **Execute Commit Limit** | 2 instructions/cycle |
| **Execute Issue Limit** | 2 instructions/cycle |
| **Decode Input Width** | 2 |
| **Branch Predictor** | TournamentBP (8192 entries) |

---

### Question 2: Baseline Performance Metrics

The following metrics were extracted from `stats.txt` for each SPEC CPU2006 benchmark (simulated for 100 million instructions).

| Benchmark | Sim Time (s) | Instructions | CPI | L1d Miss Rate | L1i Miss Rate | L2 Miss Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **401.bzip2** | 0.0840 | 100M | 1.68 | 1.48% | 0.008% | 28.22% |
| **429.mcf** | 0.0647 | 100M | 1.29 | 0.21% | 2.36% | 5.51% |
| **456.hmmer** | 0.0594 | 100M | 1.19 | 0.16% | 0.022% | 7.82% |
| **458.sjeng** | 0.5135 | 100M | **10.27** | **12.18%** | 0.002% | **99.99%** |
| **470.lbm** | 0.1747 | 100M | 3.49 | 6.10% | 0.009% | **99.99%** |

#### Performance Visualization

![CPI vs Simulation Time](plots/task1/cpi_simtime_dual_axis.png)
*Figure 1: Comparison of CPI (left axis) and Simulation Time (right axis) across benchmarks.*

![Cache Miss Rate Heatmap](plots/task1/cache_miss_heatmap.png)
*Figure 2: Cache Miss Rates across L1 Data, L1 Instruction, and L2 caches. Green indicates low miss rates (good locality), red indicates high miss rates (memory-bound).*

---

#### Key Observations

The simulation results highlight a **massive disparity in performance**, driven almost entirely by the **Memory Wall**, the speed gap between the CPU and off-chip RAM.

**From the Visualizations:**
- The **CPI vs Simulation Time** plot shows direct correlation (fixed 100M instructions), with the **Ideal CPI = 1** line revealing performance gaps
- The **Cache Miss Heatmap** reveals two distinct patterns: green (excellent locality) vs red (memory-bound)
- **L2 miss rate** is the strongest predictor of poor CPI performance

#### Behavioral Classification

| Cluster | Benchmarks | Pattern | Key Insight |
|---------|------------|---------|-------------|
| **Locality** | hmmer, mcf | Near-ideal CPI (≈1.2) | Working set fits in L1/L2 - CPU rarely waits for memory |
| **Mixed** | bzip2 | Moderate CPI (≈1.7) | Compression dictionary slightly exceeds L2 capacity |
| **Streaming** | lbm | Poor CPI (≈3.5) | Sequential access - L1 filters 94% but L2 is 100% miss |
| **Thrashing** | sjeng | Severe CPI (>10) | Random access + 100% L2 miss - CPU stalls on memory |

#### Detailed Benchmark Analysis

##### 1. The "Locality" Cluster (hmmer, mcf)

**hmmer** (Best performer, CPI = 1.188)
- Hidden Markov Model computations with excellent data locality
- All cache miss rates below 8% — working set fits entirely in cache hierarchy
- **Bottleneck:** None. Pipeline remains full.

**mcf** (CPI = 1.294)
- Graph-based combinatorial optimization
- Highest L1i miss rate (2.36%) indicates complex branching control flow
- **Bottleneck:** Branch prediction. Complex control flow confuses the fetch unit.
- *Note:* While mcf is typically memory-bound in full runs, this 100M instruction slice represents a compute-heavy phase.

##### 2. The "Mixed" Workload (bzip2)

**bzip2** (CPI = 1.680)
- Data compression with streaming access patterns
- 28% L2 miss rate shows compression dictionary slightly exceeds L2 capacity
- **Bottleneck:** L2 Capacity. Frequent but not constant memory trips.

##### 3. The "Streaming" Workload (lbm)

**lbm** (CPI = 3.494)
- Lattice Boltzmann fluid dynamics simulation with large array operations
- **L1 Miss (6.1%):** Manageable — hardware prefetcher helps with sequential data
- **L2 Miss (99.99%):** Catastrophic — dataset far exceeds L2 capacity
- **Bottleneck:** Memory Bandwidth. L2 becomes a "pass-through" buffer; performance limited by RAM throughput.

##### 4. The "Thrashing" Anomaly (sjeng)

**sjeng** (Worst performer, CPI = 10.271)
- Chess engine with complex data structures (game trees, hash tables)
- **L1 Miss (12.18%):** Highest in suite — random tree traversals defeat spatial locality
- **L2 Miss (99.99%):** Effectively 100%
- **The Compound Effect:** High L1 misses + 100% L2 misses = massive volume of DRAM requests. Memory bandwidth saturates, and DRAM latency dominates execution time.
- **Bottleneck:** Memory Latency. CPU stalls on almost every memory instruction.

#### Architectural Bottleneck Summary

| Benchmark | Classification | Primary Bottleneck |
|-----------|----------------|-------------------|
| **hmmer** | Compute-Bound | None — excellent locality keeps pipeline full |
| **mcf** | Compute/Branch-Bound | Branch prediction (2.36% L1i miss rate) |
| **bzip2** | Mixed | L2 capacity (28% miss rate) |
| **lbm** | Bandwidth-Bound | L2 capacity & memory bandwidth (99.99% L2 miss) |
| **sjeng** | Latency-Bound | Memory latency — stalling on nearly every access |

---

### Question 3: Frequency Scaling (1GHz vs 4GHz)

#### Clock Configuration Analysis

Three configurations were tested using `--cpu-clock` parameter:

| Configuration | `system.clk_domain.clock` | `cpu_clk_domain.clock` | CPU Frequency |
| :--- | :---: | :---: | :---: |
| **1 GHz Test** | 1000 ps (1 GHz) | 1000 ps | **1 GHz** |
| **Default** | 1000 ps (1 GHz) | 500 ps | **2 GHz** |
| **4 GHz Test** | 1000 ps (1 GHz) | 250 ps | **4 GHz** |

> **Key Finding:** The `system.clk_domain` remains constant at 1 GHz across all tests, while only `cpu_clk_domain` changes with the `--cpu-clock` parameter.

---

#### What Gets Clocked at Each Frequency?

| Clock Domain | Components | Affected by `--cpu-clock`? |
| :--- | :--- | :---: |
| **CPU Clock** | CPU pipeline, L1 caches, L2 cache, TLBs, L1-to-L2 bus | ✅ Yes |
| **System Clock** | Memory controller, memory bus, DRAM timings | ❌ No (fixed at 1 GHz) |

**Why This Separation?**
1. **Memory Technology Limits** — DRAM speeds are constrained by physical properties (capacitor charge/discharge times)
2. **Realistic Modeling** — In real systems, memory cannot scale with CPU frequency
3. **Power Constraints** — Memory runs at lower frequencies to manage power dissipation

> **💡 If we added another processor:**
> - If it uses `cpu_clk_domain` → Same frequency as `--cpu-clock` parameter
> - If it has its own clock domain → Requires explicit configuration

---

#### Frequency Scaling Results

**Simulation Time (seconds):**

| Benchmark | 1 GHz | 2 GHz (Default) | 4 GHz | Speedup (1→4 GHz) | Ideal |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **401.bzip2** | 0.1610 | 0.0840 | 0.0457 | **3.52×** | 4× |
| **429.mcf** | 0.1273 | 0.0647 | 0.0333 | **3.82×** | 4× |
| **456.hmmer** | 0.1185 | 0.0594 | 0.0298 | **3.98×** | 4× |
| **458.sjeng** | 0.7041 | 0.5135 | 0.4175 | **1.69×** | 4× |
| **470.lbm** | 0.2623 | 0.1747 | 0.1327 | **1.98×** | 4× |

**CPI (Cycles Per Instruction):**

| Benchmark | 1 GHz | 2 GHz (Default) | 4 GHz | CPI Increase |
| :--- | :---: | :---: | :---: | :---: |
| **401.bzip2** | 1.61 | 1.68 | 1.83 | +13.5% |
| **429.mcf** | 1.27 | 1.29 | 1.33 | +4.8% |
| **456.hmmer** | 1.19 | 1.19 | 1.19 | +0.7% |
| **458.sjeng** | 7.04 | 10.27 | **16.70** | **+137%** |
| **470.lbm** | 2.62 | 3.49 | **5.31** | **+102%** |

> **Note:** Cache miss rates (L1d, L1i, L2) remain **unchanged** across all frequencies. They depend on memory access patterns, not clock speed.

#### Scaling Efficiency Visualization

![Scaling Efficiency vs Cache Miss Rate](plots/task1/scaling_vs_cache_miss.png)
*Figure 3: Strong negative correlation ($\rho = -0.99$) between L2 miss rate and frequency scaling efficiency. Higher cache misses = worse scaling.*

> **Key Insight:** L2 miss rate is the **single best predictor** of frequency scaling efficiency. Benchmarks with <30% L2 miss rate achieve >85% scaling efficiency.

---

#### Is There Perfect Scaling?

**No.** The analysis reveals a clear dichotomy between workload types:

| Category | Benchmarks | Actual Speedup | Scaling Efficiency | L2 Miss Rate |
| :--- | :--- | :---: | :---: | :---: |
| 🟢 **Compute-Bound** | hmmer, mcf, bzip2 | 3.5×–4.0× | 88%–100% | 5%–28% |
| 🔴 **Memory-Bound** | sjeng, lbm | 1.7×–2.0× | 42%–50% | ~100% |

**Why No Perfect Scaling?**

1. **Memory Latency is Fixed** — DRAM access time (e.g., ~50 ns) doesn't scale with CPU frequency
   - At 1 GHz: 50 ns = 50 CPU cycles of waiting
   - At 4 GHz: 50 ns = **200 CPU cycles** of waiting (4× more stalls)

2. **Amdahl's Law** — Memory-bound portions cannot benefit from faster CPU
   - If 50% of execution is memory-bound, maximum speedup is 2× regardless of CPU frequency

---

### Question 4: Memory Technology Impact

#### Experiment Setup

Benchmarks were re-run with upgraded memory to evaluate the impact of faster DRAM:

| Memory Technology | DDR3_1600_x64 (Baseline) | DDR3_2133_x64 (Upgraded) |
|-------------------|--------------------------|--------------------------|
| **Memory Clock** | 800 MHz | 1066 MHz |
| **Peak Bandwidth** | 12.8 GB/s | 17.0 GB/s |
| **Improvement** | — | **+33% bandwidth** |

> **Note:** The memory controller remains clocked at the system frequency (1 GHz), while the DRAM operates at its native speed. The bandwidth improvement comes from faster memory transactions.

---

#### DDR3_2133 Benchmark Results

| Benchmark | Sim Time (s) | CPI | L2 Miss Rate | Improvement |
|-----------|--------------|-----|--------------|-------------|
| **401.bzip2** | 0.083597 | 1.6719 | 28.22% | **0.48%** |
| **429.mcf** | 0.064545 | 1.2909 | 5.51% | **0.24%** |
| **456.hmmer** | 0.059383 | 1.1877 | 7.82% | **0.02%** |
| **458.sjeng** | 0.493128 | 9.8626 | 99.99% | **3.97%** |
| **470.lbm** | 0.171529 | 3.4306 | 99.99% | **1.81%** |

![Memory Upgrade Benefit](plots/task1/memory_improvement_vs_l2miss.png)
*Figure 4: Memory upgrade benefit correlates positively with L2 miss rate.*

> **Expected Behavior Confirmed:** Cache miss rates remain **identical** between memory technologies — miss rates depend on access patterns and cache hierarchy design, not memory speed.

---

#### Performance Improvement Analysis

##### Improvement vs. L2 Miss Rate Correlation

| Benchmark | L2 Miss Rate | CPI Improvement | Classification |
|-----------|--------------|-----------------|----------------|
| **hmmer** | 7.82% | 0.02% | 🟢 Compute-bound |
| **mcf** | 5.51% | 0.24% | 🟢 Compute-bound |
| **bzip2** | 28.22% | 0.48% | 🟡 Mixed |
| **lbm** | 99.99% | 1.81% | 🔴 Memory-bound |
| **sjeng** | 99.99% | 3.97% | 🔴 Severely Memory-bound |

##### Why sjeng Benefits More Than lbm (Both Have 99.99% L2 Miss Rate)?

Despite identical L2 miss rates, **sjeng gains 2× more** from faster memory than lbm because of **L1d miss rate differences**: sjeng has 12.18% L1d miss rate vs lbm's 6.10%, meaning sjeng generates **2× more memory requests** that can benefit from faster DRAM.

**Key Insight:** The **volume of memory traffic** (driven by L1 miss rate) determines memory upgrade benefit when L2 miss rates are equal.

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
