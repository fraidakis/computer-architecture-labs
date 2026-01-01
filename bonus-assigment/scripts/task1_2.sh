#!/bin/bash
# Description: Run baseline benchmarks (bzip, mcf, hmmer, sjeng, lbm) and parse results.

# --- Configuration ---
# Calculate max parallel jobs (Total Cores - 1)
MAX_PARALLEL=$(nproc)
MAX_PARALLEL=$((MAX_PARALLEL - 1))

GEM5_DIR="/home/arch/Desktop/gem5"
GEM5_BIN="./build/ARM/gem5.opt"
BENCH_DIR="/mnt/hgfs/bonus-assigment/benchmarks/spec_cpu2006"

# 1. Parent Results Directory (Stores the final CSV)
RESULTS_DIR="/mnt/hgfs/bonus-assigment/results"

# 2. Benchmark Output Directory (Stores bulky gem5 output folders & logs)
BENCH_OUTPUT_DIR="$RESULTS_DIR/default"
LOG_DIR="$BENCH_OUTPUT_DIR/logs"

# 3. Config Directory (Stores the .ini file)
CONFIG_DIR="$RESULTS_DIR/config"

# Get the folder where this script lives (to find read_results.sh later)
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Define Benchmarks: "Output_Name|Binary_Path|Args"
BENCHMARKS=(
    "specbzip|$BENCH_DIR/401.bzip2/src/specbzip|$BENCH_DIR/401.bzip2/data/input.program 10"
    "specmcf|$BENCH_DIR/429.mcf/src/specmcf|$BENCH_DIR/429.mcf/data/inp.in"
    "spechmmer|$BENCH_DIR/456.hmmer/src/spechmmer|--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm"
    "specsjeng|$BENCH_DIR/458.sjeng/src/specsjeng|$BENCH_DIR/458.sjeng/data/test.txt"
    "speclibm|$BENCH_DIR/470.lbm/src/speclibm|20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of"
)

GEM5_SCRIPT="configs/example/se.py"
GEM5_OPTS=(
    "--cpu-type=MinorCPU"
    "--caches"
    "--l2cache"
    "-I 100000000"
)

# Create all necessary directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$BENCH_OUTPUT_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

# --- Command Generation ---

CMD_FILE="/tmp/step1_commands.txt"
trap "rm -f $CMD_FILE" EXIT
> "$CMD_FILE"

echo "Generating commands..."

# Loop through our array to generate commands
for bench in "${BENCHMARKS[@]}"; do
    # Split the string by '|' delimiter
    IFS='|' read -r name bin args <<< "$bench"
    
    # Write to command file
    # OUTPUT goes to BENCH_OUTPUT_DIR (results/default/specbzip)
    # LOGS go to LOG_DIR (results/default/logs/specbzip.log)
    echo "$GEM5_BIN -d $BENCH_OUTPUT_DIR/$name $GEM5_SCRIPT ${GEM5_OPTS[*]} -c $bin -o \"$args\" > $LOG_DIR/${name}.log 2>&1" >> "$CMD_FILE"
done

# --- Execution ---

echo "Starting Step 1 benchmarks..."
echo "Output Directory: $BENCH_OUTPUT_DIR"
echo "Configuration: $MAX_PARALLEL jobs in parallel"
echo ""

cd "$GEM5_DIR" || exit 1

# Run in parallel
parallel -j "$MAX_PARALLEL" --joblog "$LOG_DIR/step1_jobs.log" < "$CMD_FILE"
EXIT_STATUS=$?

echo ""
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ All benchmarks completed successfully!"
else
    echo "⚠️  WARNING: Some benchmarks returned errors. Check logs in $LOG_DIR."
fi

# --- Results Collection ---

INI_FILE="$CONFIG_DIR/conf_step1.ini"
RESULTS_CSV="$RESULTS_DIR/step1_results.csv"

echo "Generating results configuration at $INI_FILE..."

# Start the INI file
echo "[Benchmarks]" > "$INI_FILE"

# Loop again to add benchmarks to INI file
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    # Point INI to the specific benchmark output folder
    echo "$BENCH_OUTPUT_DIR/$name" >> "$INI_FILE"
done

# Append the rest of the configuration
cat >> "$INI_FILE" << EOF

[Parameters]
sim_seconds
sim_insts
system.clk_domain.clock
system.cpu.cpi
system.cpu.dcache.overall_miss_rate::total
system.cpu.icache.overall_miss_rate::total
system.l2.overall_miss_rate::total
host_mem_usage

[Output]
$RESULTS_CSV
EOF

echo "Extracting results to CSV..."
bash "$SCRIPT_DIR/read_results.sh" "$INI_FILE"

echo "Done. Results saved to $RESULTS_CSV"