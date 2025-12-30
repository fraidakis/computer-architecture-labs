#!/bin/bash

# 1. Create the results directory first
mkdir -p /mnt/hgfs/bonus-assigment/results/

# --- Benchmark 1: BZIP2 ---
echo "Compiling and Running BZIP2..."
cd /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/401.bzip2/src/ && make && \
cd ~/Desktop/gem5 && \
./build/ARM/gem5.opt -d /mnt/hgfs/bonus-assigment/results/specbzip configs/example/se.py --cpu-type=MinorCPU --caches --l2cache \
-c /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/401.bzip2/src/specbzip \
-o "/mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/401.bzip2/data/input.program 10" -I 100000000 && \

# --- Benchmark 2: MCF ---
echo "Compiling and Running MCF..."
cd /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/429.mcf/src/ && make && \
cd ~/Desktop/gem5 && \
./build/ARM/gem5.opt -d /mnt/hgfs/bonus-assigment/results/specmcf configs/example/se.py --cpu-type=MinorCPU --caches --l2cache \
-c /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/429.mcf/src/specmcf \
-o "/mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/429.mcf/data/inp.in" -I 100000000 && \

# --- Benchmark 3: HMMER ---
echo "Compiling and Running HMMER..."
cd /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/456.hmmer/src/ && make && \
cd ~/Desktop/gem5 && \
./build/ARM/gem5.opt -d /mnt/hgfs/bonus-assigment/results/spechmmer configs/example/se.py --cpu-type=MinorCPU --caches --l2cache \
-c /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/456.hmmer/src/spechmmer \
-o "--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/456.hmmer/data/bombesin.hmm" -I 100000000 && \

# --- Benchmark 4: SJENG ---
echo "Compiling and Running SJENG..."
cd /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/458.sjeng/src/ && make && \
cd ~/Desktop/gem5 && \
./build/ARM/gem5.opt -d /mnt/hgfs/bonus-assigment/results/specsjeng configs/example/se.py --cpu-type=MinorCPU --caches --l2cache \
-c /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/458.sjeng/src/specsjeng \
-o "/mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/458.sjeng/data/test.txt" -I 100000000 && \

# --- Benchmark 5: LBM ---
echo "Compiling and Running LBM..."
cd /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/470.lbm/src/ && make && \
cd ~/Desktop/gem5 && \
./build/ARM/gem5.opt -d /mnt/hgfs/bonus-assigment/results/speclibm configs/example/se.py --cpu-type=MinorCPU --caches --l2cache \
-c /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/470.lbm/src/speclibm \
-o "20 /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/470.lbm/data/lbm.in 0 1 /mnt/hgfs/bonus-assigment/benchmark/spec_cpu2006/470.lbm/data/100_100_130_cf_a.of" -I 100000000 && \

echo "All benchmarks completed successfully!"

# ----------------------------------------------------------------------- #

bash read_results.sh conf_script.ini
