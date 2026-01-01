#!/bin/bash
# Description: Part 2 - Design Exploration: Run multiple cache configurations per benchmark
# Each benchmark gets its own results folder with separate CSV output

# --- Configuration ---
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Calculate max parallel jobs (Total Cores - 1)
MAX_PARALLEL=$(nproc)
MAX_PARALLEL=$((MAX_PARALLEL - 1))

GEM5_DIR="/home/arch/Desktop/gem5"
GEM5_BIN="./build/ARM/gem5.opt"
BENCH_DIR="$PROJECT_ROOT/benchmarks/spec_cpu2006"

# Results Directories - Separate folder per benchmark
RESULTS_DIR="$PROJECT_ROOT/results/part2"
CONFIG_DIR="$PROJECT_ROOT/results/config"

# Benchmark Definitions: "Name|Binary|Args"
BENCHMARKS=(
    "specbzip|$BENCH_DIR/401.bzip2/src/specbzip|$BENCH_DIR/401.bzip2/data/input.program 10"
    "specmcf|$BENCH_DIR/429.mcf/src/specmcf|$BENCH_DIR/429.mcf/data/inp.in"
    "spechmmer|$BENCH_DIR/456.hmmer/src/spechmmer|--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm"
    "specsjeng|$BENCH_DIR/458.sjeng/src/specsjeng|$BENCH_DIR/458.sjeng/data/test.txt"
    "speclibm|$BENCH_DIR/470.lbm/src/speclibm|20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of"
)

# =============================================================================
# TEST CONFIGURATIONS PER BENCHMARK
# Format: "config_name|l1i_size|l1d_size|l2_size|l1i_assoc|l1d_assoc|l2_assoc|cacheline"
# Constraints: L1 total ≤ 256KB, L2 ≤ 4MB
# =============================================================================

# --- spechmmer: Compute-bound, low miss rates ---
CONFIGS_spechmmer=(
    "cfg1|32kB|32kB|512kB|2|2|4|64"
    "cfg2|32kB|64kB|1MB|2|2|8|64"
    "cfg3|64kB|64kB|512kB|2|2|4|128"
    "cfg4|32kB|32kB|2MB|2|2|8|64"
)

# --- specmcf: High L1i miss rate (2.36%) ---
CONFIGS_specmcf=(
    "cfg1|64kB|32kB|512kB|2|2|4|64"
    "cfg2|128kB|32kB|512kB|4|2|4|64"
    "cfg3|128kB|64kB|1MB|4|2|8|64"
    "cfg4|64kB|64kB|2MB|4|4|8|64"
    "cfg5|128kB|32kB|1MB|8|2|8|64"
)

# --- specbzip: Data-centric, 28% L2 miss ---
CONFIGS_specbzip=(
    "cfg1|32kB|64kB|1MB|2|2|4|64"
    "cfg2|32kB|128kB|2MB|2|4|8|64"
    "cfg3|32kB|128kB|4MB|2|4|8|128"
    "cfg4|64kB|128kB|4MB|2|4|8|64"
    "cfg5|32kB|128kB|4MB|2|8|16|256"
)

# --- speclibm: Memory-bound, 99.99% L2 miss ---
CONFIGS_speclibm=(
    "cfg1|32kB|64kB|2MB|2|2|8|64"
    "cfg2|32kB|128kB|2MB|2|4|8|128"
    "cfg3|32kB|128kB|4MB|2|4|8|256"
    "cfg4|64kB|64kB|4MB|2|4|16|256"
    "cfg5|32kB|128kB|4MB|2|8|8|128"
)

# --- specsjeng: Severely memory-bound ---
CONFIGS_specsjeng=(
    "cfg1|32kB|64kB|2MB|2|2|8|64"
    "cfg2|64kB|64kB|2MB|4|4|8|128"
    "cfg3|64kB|64kB|4MB|4|4|16|128"
    "cfg4|64kB|128kB|4MB|2|4|8|256"
    "cfg5|64kB|64kB|4MB|4|4|16|256"
)

GEM5_SCRIPT="configs/example/se.py"
BASE_OPTS=(
    "--cpu-type=MinorCPU"
    "--caches"
    "--l2cache"
    "-I 100000000"
)

# --- Safety Checks ---
if ! command -v parallel &> /dev/null; then
    echo "Error: GNU parallel is not installed."
    exit 1
fi
[ ! -d "$GEM5_DIR" ] && { echo "Error: gem5 directory not found at $GEM5_DIR"; exit 1; }

# Create base directories
mkdir -p "$RESULTS_DIR" "$CONFIG_DIR"

# Create separate directory for each benchmark
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    mkdir -p "$RESULTS_DIR/$name"
    mkdir -p "$RESULTS_DIR/$name/logs"
done

echo "=============================================="
echo "Part 2: Design Exploration - Multiple Configs"
echo "=============================================="
echo ""
echo "Results Structure:"
echo "  results/part2/"
echo "  ├── specbzip/     (5 configs)"
echo "  ├── spechmmer/    (4 configs)"
echo "  ├── speclibm/     (5 configs)"
echo "  ├── specmcf/      (5 configs)"
echo "  └── specsjeng/    (5 configs)"
echo ""

# --- Command Generation ---
CMD_FILE="/tmp/part2_exploration_commands.txt"
trap "rm -f $CMD_FILE" EXIT
> "$CMD_FILE"

echo "Generating benchmark commands..."
echo ""

# Function to generate commands and INI for a benchmark
run_benchmark() {
    local bench_name=$1
    local bin=$2
    local args=$3
    shift 3
    local configs=("$@")
    
    local BENCH_RESULTS="$RESULTS_DIR/$bench_name"
    local LOG_DIR="$BENCH_RESULTS/logs"
    
    echo "  $bench_name: ${#configs[@]} configurations"
    
    for config in "${configs[@]}"; do
        IFS='|' read -r cfg_name l1i_size l1d_size l2_size l1i_assoc l1d_assoc l2_assoc cacheline <<< "$config"
        
        OUTPUT_DIR="$BENCH_RESULTS/$cfg_name"
        
        CACHE_OPTS=(
            "--l1i_size=$l1i_size"
            "--l1d_size=$l1d_size"
            "--l2_size=$l2_size"
            "--l1i_assoc=$l1i_assoc"
            "--l1d_assoc=$l1d_assoc"
            "--l2_assoc=$l2_assoc"
            "--cacheline_size=$cacheline"
        )
        
        echo "    $cfg_name: L1i=$l1i_size L1d=$l1d_size L2=$l2_size line=$cacheline"
        echo "$GEM5_BIN -d $OUTPUT_DIR $GEM5_SCRIPT ${BASE_OPTS[*]} ${CACHE_OPTS[*]} -c $bin -o \"$args\" > $LOG_DIR/${cfg_name}.log 2>&1" >> "$CMD_FILE"
    done
}

# Generate commands for each benchmark
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    
    # Get the config array for this benchmark
    config_var="CONFIGS_$name[@]"
    run_benchmark "$name" "$bin" "$args" "${!config_var}"
done

TOTAL_CMDS=$(wc -l < "$CMD_FILE")
echo ""
echo "Total configurations to run: $TOTAL_CMDS"
echo ""

# --- Execution ---
echo "Starting design exploration benchmarks..."
echo "Configuration: $MAX_PARALLEL jobs in parallel"
echo ""

cd "$GEM5_DIR" || exit 1

parallel -j "$MAX_PARALLEL" --joblog "$RESULTS_DIR/jobs.log" < "$CMD_FILE"
EXIT_STATUS=$?

echo ""
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ All benchmark configurations completed successfully!"
else
    echo "⚠️  WARNING: Some benchmarks returned errors. Check logs."
fi

# --- Results Collection (Separate CSV per benchmark) ---
echo ""
echo "Extracting results per benchmark..."

for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    
    BENCH_RESULTS="$RESULTS_DIR/$name"
    INI_FILE="$CONFIG_DIR/conf_${name}.ini"
    RESULTS_CSV="$BENCH_RESULTS/${name}_results.csv"
    
    # Get config array for this benchmark
    config_var="CONFIGS_$name[@]"
    
    echo "[Benchmarks]" > "$INI_FILE"
    for config in "${!config_var}"; do
        IFS='|' read -r cfg_name rest <<< "$config"
        echo "$BENCH_RESULTS/$cfg_name" >> "$INI_FILE"
    done
    
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
    
    echo "  Extracting $name results..."
    bash "$SCRIPT_DIR/read_results.sh" "$INI_FILE"
done

echo ""
echo "=============================================="
echo "Done! Results saved to:"
echo "=============================================="
echo ""
echo "  results/part2/specbzip/specbzip_results.csv"
echo "  results/part2/spechmmer/spechmmer_results.csv"
echo "  results/part2/speclibm/speclibm_results.csv"
echo "  results/part2/specmcf/specmcf_results.csv"
echo "  results/part2/specsjeng/specsjeng_results.csv"
echo ""
