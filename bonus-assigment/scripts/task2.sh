#!/bin/bash
# Description: Part 2 - Design Exploration: Test configurations from README.md analysis
# Tests configurations reported in README.md lines 325-516
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
RESULTS_DIR="$PROJECT_ROOT/results/"
CONFIG_DIR="$PROJECT_ROOT/config/"

# Benchmark Definitions: "Name|Binary|Args"
BENCHMARKS=(
    "specbzip|$BENCH_DIR/401.bzip2/src/specbzip|$BENCH_DIR/401.bzip2/data/input.program 10"
    "specmcf|$BENCH_DIR/429.mcf/src/specmcf|$BENCH_DIR/429.mcf/data/inp.in"
    "spechmmer|$BENCH_DIR/456.hmmer/src/spechmmer|--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm"
    "specsjeng|$BENCH_DIR/458.sjeng/src/specsjeng|$BENCH_DIR/458.sjeng/data/test.txt"
    "speclibm|$BENCH_DIR/470.lbm/src/speclibm|20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of"
)

# =============================================================================
# TEST CONFIGURATIONS
# Format: "config_name|l1i_size|l1d_size|l2_size|l1i_assoc|l1d_assoc|l2_assoc|cacheline"
# Constraints: L1 total ≤ 256KB, L2 ≤ 4MB
# =============================================================================

# --- spechmmer: Compute-bound, excellent data locality ---
# Optimization: Near-optimal with default, investment provides negligible returns
CONFIGS_spechmmer=(
    "baseline|32kB|32kB|512kB|2|2|4|64"           # Minimal viable config
    "+L1d|32kB|64kB|512kB|2|2|4|64"               # Double L1d
    "+L1d=128|32kB|128kB|512kB|2|8|4|64"          # Max L1d + higher assoc
    "+128B|32kB|128kB|512kB|2|8|4|128"            # Double cacheline
    "+256B|32kB|128kB|512kB|2|8|4|256"            # 4× cacheline
    "+L1i|64kB|128kB|512kB|2|8|4|256"             # Double L1i (BEST: 1.177)
)

# --- specmcf: Instruction-Bound with Pointer-Chasing ---
# Optimization: Counter-intuitive - instruction-bound benefits most from data-side (larger cacheline)
CONFIGS_specmcf=(
    "baseline|64kB|32kB|512kB|2|2|4|64"           # Larger L1i baseline
    "+assoc|64kB|64kB|512kB|2|4|4|64"             # Double L1d + 4-way
    "balanced|64kB|64kB|2MB|4|4|8|64"             # Balanced config
    "+128B|64kB|64kB|2MB|4|4|8|128"               # 2× cacheline - BREAKTHROUGH!
    "+L2|64kB|64kB|4MB|4|4|16|128"                # 128B + max L2
    "+256B,L1i=2way|64kB|64kB|2MB|2|4|8|256"      # 4× cacheline
    "+512B|64kB|64kB|2MB|4|4|8|512"               # 8× cacheline (BEST: 1.105)
)

# --- specbzip: Data-Centric Streaming ---
# Optimization: Layered optimizations - each cache level contributes
CONFIGS_specbzip=(
    "baseline|32kB|64kB|1MB|2|2|4|64"             # Starting point
    "+L2only|32kB|64kB|2MB|2|2|8|64"              # Double L2
    "+L1d|32kB|128kB|2MB|2|4|8|64"                # Max L1d + 4-way
    "+128B|32kB|128kB|2MB|2|4|8|128"              # 2× cacheline
    "+256B|32kB|128kB|2MB|2|4|8|256"              # 4× cacheline
    "+256B,L2=4M|32kB|128kB|4MB|2|4|16|256"       # Max L2 + 256B
    "+assoc|32kB|128kB|4MB|2|8|16|256"            # 8-way L1d
    "+L1d,16way|32kB|128kB|4MB|2|16|16|256"       # 16-way L1d (BEST: 1.589)
)

# --- speclibm: Severely Memory-Bound Streaming ---
# Optimization: Cacheline size is ONLY factor that matters
CONFIGS_speclibm=(
    "cfg1|32kB|64kB|2MB|2|2|8|64"                 # Baseline
    "+128B|32kB|64kB|2MB|2|2|8|128"               # 2× cacheline (-26% CPI)
    "+256B|32kB|64kB|2MB|2|2|8|256"               # 4× cacheline (-23%)
    "+512B|32kB|64kB|2MB|2|2|8|512"               # 8× cacheline (-14%)
    "+1024B|32kB|64kB|2MB|2|2|8|1024"             # 16× cacheline (-10%)
    "+2048B|32kB|64kB|2MB|2|2|8|2048"             # 32× cacheline (BEST: 1.496)
    "+MicroL2-Direct|32kB|32kB|256kB|1|2|1|2048"  # Minimal L2 + direct-mapped
    "+NanoL2128k|16kB|32kB|128kB|1|2|1|2048"      # Extreme reduction
    "+PicoL1d16k|16kB|16kB|128kB|1|2|1|2048"      # Minimal everything
)

# --- specsjeng: Severely Memory-Bound with Random Access ---
# Optimization: Maximize cacheline to 2048B, additional L1d provides marginal gains
CONFIGS_specsjeng=(
    "cfg1|32kB|64kB|2MB|2|2|8|64"                 # Baseline (10.271 CPI)
    "+128B|32kB|64kB|2MB|2|2|8|128"               # 2× cacheline (-34% CPI)
    "+256B|32kB|64kB|2MB|2|2|8|256"               # 4× cacheline (-24%)
    "+512B|32kB|64kB|2MB|2|2|8|512"               # 8× cacheline (-24%)
    "+1024B|32kB|64kB|2MB|2|2|8|1024"             # 16× cacheline (-17%)
    "+2048B|32kB|64kB|2MB|2|2|8|2048"             # 32× cacheline
    "+L1d128kB|32kB|128kB|2MB|2|2|8|2048"         # Double L1d (-0.3%)
    "+L1d4way|32kB|128kB|2MB|2|4|8|2048"          # 4-way L1d (BEST: 3.072)
    "+PicoL2512k|16kB|128kB|512kB|2|4|2|2048"     # Minimal L2 - proves L2 size irrelevant
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
echo "Part 2: Design Exploration - README.md Configs"
echo "=============================================="
echo ""
echo "Testing configurations from README.md analysis"
echo ""
echo "Results Structure:"
echo "  results/"
echo "  ├── specbzip/     (8 configs)"
echo "  ├── spechmmer/    (6 configs)"
echo "  ├── speclibm/     (9 configs)"
echo "  ├── specmcf/      (7 configs)"
echo "  └── specsjeng/    (9 configs)"
echo ""

# --- Command Generation ---
CMD_FILE="/tmp/part2_best_commands.txt"
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
    RESULTS_CSV="$RESULTS_DIR/${name}_results.csv"
    
    # Get config array for this benchmark
    config_var="CONFIGS_$name[@]"
    
    echo "[Benchmarks]" > "$INI_FILE"
    for config in "${!config_var}"; do
        IFS='|' read -r cfg_name rest <<< "$config"
        echo "$BENCH_RESULTS/$cfg_name" >> "$INI_FILE"
    done
    
    cat >> "$INI_FILE" <<EOF

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
echo "  results/specbzip_results.csv"
echo "  results/spechmmer_results.csv"
echo "  results/speclibm_results.csv"
echo "  results/specmcf_results.csv"
echo "  results/specsjeng_results.csv"
echo ""
