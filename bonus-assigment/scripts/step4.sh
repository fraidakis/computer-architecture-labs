#!/bin/bash

# --- Configuration ---
GEM5_DIR=~/Desktop/gem5
BASE_DIR=/mnt/hgfs/bonus-assigment
BENCH_DIR=$BASE_DIR/benchmark/spec_cpu2006
RESULTS_DIR=$BASE_DIR/results/memory_test

# Create result directory
mkdir -p $RESULTS_DIR

cd $GEM5_DIR

echo "=========================================================="
echo " TEST 1: The 'BEST' Case (Memory Hungry) -> SJENG"
echo " (Your data showed this had CPI=10.27 and L2 Miss=99%)"
echo "=========================================================="

# Run SJENG with FASTER RAM (DDR3_2133)
./build/ARM/gem5.opt -d $RESULTS_DIR/specsjeng_2133 configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache \
    --mem-type=DDR3_2133_8x8 \
    -c $BENCH_DIR/458.sjeng/src/specsjeng \
    -o "$BENCH_DIR/458.sjeng/data/test.txt" -I 100000000

echo "Finished SJENG. Check stats for improvement."

echo "=========================================================="
echo " TEST 2: The 'WORST' Case (Cache Friendly) -> HMMER"
echo " (Your data showed this had CPI=1.18, barely using RAM)"
echo "=========================================================="

# Run HMMER with FASTER RAM (DDR3_2133)
./build/ARM/gem5.opt -d $RESULTS_DIR/spechmmer_2133 configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache \
    --mem-type=DDR3_2133_8x8 \
    -c $BENCH_DIR/456.hmmer/src/spechmmer \
    -o "--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm" -I 100000000

echo "Finished HMMER. Expect little to no change."
echo "All tests complete. Results in: $RESULTS_DIR"