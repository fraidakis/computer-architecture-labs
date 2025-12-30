#!/bin/bash

# --- Configuration ---
GEM5_DIR=~/Desktop/gem5
BASE_DIR=/mnt/hgfs/bonus-assigment
BENCH_DIR=$BASE_DIR/benchmark/spec_cpu2006
# Ensure base result directories exist
mkdir -p $BASE_DIR/results/1GHz
mkdir -p $BASE_DIR/results/4GHz

echo "=========================================="
echo " STEP 1: COMPILING BENCHMARKS"
echo " (Skipping if already compiled)"
echo "=========================================="

# Compile all benchmarks first (just in case)
cd $BENCH_DIR/401.bzip2/src/ && make
cd $BENCH_DIR/429.mcf/src/ && make
cd $BENCH_DIR/456.hmmer/src/ && make
cd $BENCH_DIR/458.sjeng/src/ && make
cd $BENCH_DIR/470.lbm/src/ && make

echo "Compilation Finished. Starting Parallel Simulations..."

# ==============================================================================
# FUNCTION TO RUN BENCHMARKS IN PARALLEL
# ==============================================================================
run_suite_parallel() {
    FREQ=$1
    OUT_DIR=$BASE_DIR/results/$1
    
    echo "------------------------------------------"
    echo " LAUNCHING ALL $FREQ BENCHMARKS SIMULTANEOUSLY..."
    echo " Logs will be saved in: $OUT_DIR/<benchmark>/run.log"
    echo "------------------------------------------"

    cd $GEM5_DIR

    # 1. BZIP2
    mkdir -p $OUT_DIR/specbzip
    ./build/ARM/gem5.opt -d $OUT_DIR/specbzip configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache --cpu-clock=$FREQ \
    -c $BENCH_DIR/401.bzip2/src/specbzip \
    -o "$BENCH_DIR/401.bzip2/data/input.program 10" -I 100000000 \
    > $OUT_DIR/specbzip/run.log 2>&1 &
    PID1=$!
    echo " -> Launched BZIP2 (PID $PID1)"

    # 2. MCF
    mkdir -p $OUT_DIR/specmcf
    ./build/ARM/gem5.opt -d $OUT_DIR/specmcf configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache --cpu-clock=$FREQ \
    -c $BENCH_DIR/429.mcf/src/specmcf \
    -o "$BENCH_DIR/429.mcf/data/inp.in" -I 100000000 \
    > $OUT_DIR/specmcf/run.log 2>&1 &
    PID2=$!
    echo " -> Launched MCF (PID $PID2)"

    # 3. HMMER
    mkdir -p $OUT_DIR/spechmmer
    ./build/ARM/gem5.opt -d $OUT_DIR/spechmmer configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache --cpu-clock=$FREQ \
    -c $BENCH_DIR/456.hmmer/src/spechmmer \
    -o "--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm" -I 100000000 \
    > $OUT_DIR/spechmmer/run.log 2>&1 &
    PID3=$!
    echo " -> Launched HMMER (PID $PID3)"

    # 4. SJENG
    mkdir -p $OUT_DIR/specsjeng
    ./build/ARM/gem5.opt -d $OUT_DIR/specsjeng configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache --cpu-clock=$FREQ \
    -c $BENCH_DIR/458.sjeng/src/specsjeng \
    -o "$BENCH_DIR/458.sjeng/data/test.txt" -I 100000000 \
    > $OUT_DIR/specsjeng/run.log 2>&1 &
    PID4=$!
    echo " -> Launched SJENG (PID $PID4)"

    # 5. LBM
    mkdir -p $OUT_DIR/speclibm
    ./build/ARM/gem5.opt -d $OUT_DIR/speclibm configs/example/se.py \
    --cpu-type=MinorCPU --caches --l2cache --cpu-clock=$FREQ \
    -c $BENCH_DIR/470.lbm/src/speclibm \
    -o "20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of" -I 100000000 \
    > $OUT_DIR/speclibm/run.log 2>&1 &
    PID5=$!
    echo " -> Launched LBM (PID $PID5)"

    echo "Waiting for all $FREQ jobs to finish..."
    wait
    echo "All $FREQ jobs completed."
}

# ==============================================================================
# EXECUTE
# ==============================================================================

# Run Loop 1: 1GHz (Runs 5 benchmarks at once)
run_suite_parallel "1GHz"

# Run Loop 2: 4GHz (Runs 5 benchmarks at once)
run_suite_parallel "4GHz"

echo "=========================================="
echo " ALL PARALLEL SIMULATIONS COMPLETED"
echo "=========================================="