#!/bin/bash
# Description: Part 2 V3 - Final Design Exploration based on V2 results
# V3 configurations from versions.md analysis

# --- Configuration ---
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

MAX_PARALLEL=$(nproc)
MAX_PARALLEL=$((MAX_PARALLEL - 1))

GEM5_DIR="/home/arch/Desktop/gem5"
GEM5_BIN="./build/ARM/gem5.opt"
BENCH_DIR="$PROJECT_ROOT/benchmarks/spec_cpu2006"

RESULTS_DIR="$PROJECT_ROOT/results/part2_v3"
CONFIG_DIR="$PROJECT_ROOT/results/config"

# Benchmark Definitions
BENCHMARKS=(
    "specbzip|$BENCH_DIR/401.bzip2/src/specbzip|$BENCH_DIR/401.bzip2/data/input.program 10"
    "specmcf|$BENCH_DIR/429.mcf/src/specmcf|$BENCH_DIR/429.mcf/data/inp.in"
    "spechmmer|$BENCH_DIR/456.hmmer/src/spechmmer|--fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 $BENCH_DIR/456.hmmer/data/bombesin.hmm"
    "specsjeng|$BENCH_DIR/458.sjeng/src/specsjeng|$BENCH_DIR/458.sjeng/data/test.txt"
    "speclibm|$BENCH_DIR/470.lbm/src/speclibm|20 $BENCH_DIR/470.lbm/data/lbm.in 0 1 $BENCH_DIR/470.lbm/data/100_100_130_cf_a.of"
)

# =============================================================================
# V3 CONFIGURATIONS - From versions.md Analysis
# Format: "config_name|l1i_size|l1d_size|l2_size|l1i_assoc|l1d_assoc|l2_assoc|cacheline"
# NOTE: gem5 uses FIXED latency (L1=2, L2=20 cycles) regardless of size
#       Only benefit of size changes is miss rate reduction
# =============================================================================

# --- specbzip V3: Best was v10 (L1i=64kB, L1d=128kB, L2=4MB, line=256B) CPI=1.591 ---
# Focus: Test larger L1d (160-192kB) with winning 256B cacheline
CONFIGS_specbzip=(
    "v3-01|64kB|160kB|4MB|2|8|16|256"    # Max L1d within constraint (64+160=224<256)
    "v3-02|32kB|192kB|4MB|2|8|16|256"    # Push L1d to limit (32+192=224)
    "v3-03|64kB|128kB|4MB|4|8|16|256"    # Higher L1i assoc (4-way)
)

# --- spechmmer V3: Best was v10 (CPI=1.179) ---
# Focus: Miss rate reduction (gem5 has fixed latency)
CONFIGS_spechmmer=(
    "v3-01|64kB|128kB|512kB|2|4|4|256"   # Larger L1d to reduce miss rate
    "v3-02|128kB|64kB|512kB|4|2|4|256"   # Larger L1i with higher assoc
    "v3-03|64kB|64kB|512kB|4|4|8|256"    # Higher assoc across all levels
)

# --- specmcf V3: Best was v09 (128B cacheline) CPI=1.122 ---
# Focus: 128B cacheline + higher associativities (most promising unexplored area)
CONFIGS_specmcf=(
    "v3-01|64kB|128kB|2MB|4|4|8|128"     # Larger L1d with winning 128B line
    "v3-02|128kB|64kB|2MB|8|4|8|128"     # Max L1i assoc (8-way) + 128B line
    "v3-03|64kB|64kB|2MB|4|4|16|128"     # Higher L2 assoc with 128B line
    "v3-04|64kB|64kB|2MB|8|8|8|128"      # All max assoc + 128B line
    "v3-05|64kB|64kB|4MB|4|4|8|128"      # Larger L2 + 128B line
)

# --- specsjeng V3: Best was v04 (L1d=128kB, line=256B) CPI=5.171 ---
# Focus: Test larger L1d (160kB) - 192kB returned NAN in V2
CONFIGS_specsjeng=(
    "v3-01|32kB|192kB|4MB|4|8|16|256"    # Max L1d (192kB) + high assoc
    "v3-02|64kB|128kB|4MB|8|8|16|256"    # Max all assoc
    "v3-03|64kB|160kB|4MB|4|8|16|256"    # Larger L1d (160kB) - should work
)

# --- speclibm V3: Best was v01-v05 (line=256B) CPI=1.989 ---
# Focus: Test larger L1d (160kB) and 512B cacheline
CONFIGS_speclibm=(
    "v3-01|32kB|160kB|4MB|2|4|8|256"     # Larger L1d (160kB)
    "v3-02|64kB|160kB|4MB|2|8|16|256"    # Larger L1d + higher assoc
    "v3-03|32kB|128kB|4MB|2|4|8|512"     # Test 512B cacheline (if supported)
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
[ ! -d "$GEM5_DIR" ] && { echo "Error: gem5 directory not found"; exit 1; }

# Create directories
mkdir -p "$RESULTS_DIR" "$CONFIG_DIR"
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    mkdir -p "$RESULTS_DIR/$name/logs"
done

echo "=============================================="
echo "Part 2 V3: Final Design Exploration"
echo "=============================================="
echo ""
echo "Based on V2 results + gem5 fixed latency analysis"
echo "Focus: Miss rate reduction via L1d size and assoc"
echo ""
echo "Results Structure:"
echo "  results/part2_v3/"
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    config_var="CONFIGS_$name[@]"
    count=$(eval "echo \${#$config_var}")
    echo "  ├── $name/ ($count configs)"
done
echo ""

# --- Command Generation ---
CMD_FILE="/tmp/part2_v3_commands.txt"
trap "rm -f $CMD_FILE" EXIT
> "$CMD_FILE"

echo "Generating commands..."
echo ""

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
        
        echo "    $cfg_name: L1i=$l1i_size L1d=$l1d_size L2=$l2_size assoc=$l1i_assoc/$l1d_assoc/$l2_assoc line=$cacheline"
        echo "$GEM5_BIN -d $OUTPUT_DIR $GEM5_SCRIPT ${BASE_OPTS[*]} ${CACHE_OPTS[*]} -c $bin -o \"$args\" > $LOG_DIR/${cfg_name}.log 2>&1" >> "$CMD_FILE"
    done
}

for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    config_var="CONFIGS_$name[@]"
    run_benchmark "$name" "$bin" "$args" "${!config_var}"
done

TOTAL_CMDS=$(wc -l < "$CMD_FILE")
echo ""
echo "Total configurations: $TOTAL_CMDS"
echo ""

# --- Execution ---
echo "Starting V3 benchmarks ($MAX_PARALLEL parallel jobs)..."
echo ""

cd "$GEM5_DIR" || exit 1
parallel -j "$MAX_PARALLEL" --joblog "$RESULTS_DIR/jobs.log" < "$CMD_FILE"
EXIT_STATUS=$?

echo ""
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ All V3 benchmarks completed!"
else
    echo "⚠️  Some benchmarks had errors. Check logs."
fi

# --- Results Collection ---
echo ""
echo "Extracting results..."

for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    
    BENCH_RESULTS="$RESULTS_DIR/$name"
    INI_FILE="$CONFIG_DIR/conf_${name}_v3.ini"
    RESULTS_CSV="$BENCH_RESULTS/${name}_v3_results.csv"
    
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
    
    echo "  $name -> ${name}_v3_results.csv"
    bash "$SCRIPT_DIR/read_results.sh" "$INI_FILE"
done

echo ""
echo "=============================================="
echo "V3 Complete! Results in results/part2_v3/"
echo "=============================================="
echo ""
echo "Total configs tested: $TOTAL_CMDS"
echo "  specbzip:  3 configs (testing 160-192kB L1d)"
echo "  spechmmer: 3 configs (testing assoc variations)"
echo "  specmcf:   5 configs (testing 128B line + assoc)"
echo "  specsjeng: 3 configs (testing 160-192kB L1d)"
echo "  speclibm:  3 configs (testing 160kB L1d + 512B line)"
