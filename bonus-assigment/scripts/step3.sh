#!/bin/bash
# Description: Run benchmarks at 1GHz and 4GHz frequencies and parse results.

# --- Configuration ---
# Get the folder where this script lives (to find read_results.sh later)
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Calculate max parallel jobs (Total Cores - 1)
MAX_PARALLEL=$(nproc)
MAX_PARALLEL=$((MAX_PARALLEL - 1))

GEM5_DIR="/home/arch/Desktop/gem5"
GEM5_BIN="./build/ARM/gem5.opt"
BENCH_DIR="$PROJECT_ROOT/benchmarks/spec_cpu2006"

# 1. Parent Results Directory
RESULTS_DIR="$PROJECT_ROOT/results"

# 2. Logs Directory (Shared for frequency tests)
LOG_DIR="$RESULTS_DIR/logs"

# 3. Config Directory (Stores the .ini file)
CONFIG_DIR="$RESULTS_DIR/config"

# Define Benchmarks: "Output_Name|Binary_Path|Args"
# Note: Output_Name will be suffixed with frequency later (e.g., specbzip becomes 1GHz/specbzip)
BENCHMARKS=(
    "specbzip|$BENCH_DIR/401.bzip2/src/specbzip|$BENCH_DIR/401.bzip2/data/input.program 10"
    "specmcf|$BENCH_DIR/429.mcf/src/specmcf|$BENCH_DIR/429.mcf/data/inp.in"
    "spechmmer|$BENCH_DIR/456.hmmer/src/spechmmer|--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm"
    "specsjeng|$BENCH_DIR/458.sjeng/src/specsjeng|$BENCH_DIR/458.sjeng/data/test.txt"
    "speclibm|$BENCH_DIR/470.lbm/src/speclibm|20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of"
)

FREQUENCIES=("1GHz" "4GHz")

GEM5_OPTS_BASE=(
    "configs/example/se.py"
    "--cpu-type=MinorCPU"
    "--caches"
    "--l2cache"
    "-I 100000000"
)

# Create all necessary directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

# --- Command Generation ---

CMD_FILE="/tmp/step3_commands.txt"
trap "rm -f $CMD_FILE" EXIT
> "$CMD_FILE"

echo "Generating commands..."

# Loop through frequencies and benchmarks
for freq in "${FREQUENCIES[@]}"; do
    for bench in "${BENCHMARKS[@]}"; do
        IFS='|' read -r name bin args <<< "$bench"
        
        # Define output directory for this specific run
        RUN_DIR="$RESULTS_DIR/$freq/$name"
        mkdir -p "$RUN_DIR" # Ensure directory exists
        
        # Add frequency option
        OPTS=("${GEM5_OPTS_BASE[@]}" "--cpu-clock=$freq")
        
        # Write to command file
        # Using a unique log name including frequency
        echo "$GEM5_BIN ${OPTS[*]} -d $RUN_DIR -c $bin -o \"$args\" > $LOG_DIR/${name}_${freq}.log 2>&1" >> "$CMD_FILE"
    done
done

# --- Execution ---

echo "Starting Step 3 benchmarks (1GHz & 4GHz)..."
echo "Configuration: $MAX_PARALLEL jobs in parallel"
echo ""

cd "$GEM5_DIR" || exit 1

# Run in parallel
parallel -j "$MAX_PARALLEL" --bar --joblog "$LOG_DIR/step3_jobs.log" < "$CMD_FILE"
EXIT_STATUS=$?

echo ""
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ All benchmarks completed successfully!"
else
    echo "⚠️  WARNING: Some benchmarks returned errors. Check logs in $LOG_DIR."
fi

# --- Results Collection ---

INI_FILE="$CONFIG_DIR/conf_step3.ini"
RESULTS_CSV="$RESULTS_DIR/step3_results.csv"

echo "Generating results configuration at $INI_FILE..."

# Start the INI file
echo "[Benchmarks]" > "$INI_FILE"

# Loop again to add benchmarks to INI file
for freq in "${FREQUENCIES[@]}"; do
    for bench in "${BENCHMARKS[@]}"; do
        IFS='|' read -r name bin args <<< "$bench"
        echo "$RESULTS_DIR/$freq/$name" >> "$INI_FILE"
    done
done

# Append the rest of the configuration
cat >> "$INI_FILE" << EOF

[Parameters]
sim_seconds
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