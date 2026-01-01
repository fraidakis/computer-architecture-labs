#!/bin/bash
# Description: Part 2 V2 - Refined Design Exploration based on V1 results
# 10+ configurations per benchmark, exploring around best-performing settings

# --- Configuration ---
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

MAX_PARALLEL=$(nproc)
MAX_PARALLEL=$((MAX_PARALLEL - 1))

GEM5_DIR="/home/arch/Desktop/gem5"
GEM5_BIN="./build/ARM/gem5.opt"
BENCH_DIR="$PROJECT_ROOT/benchmarks/spec_cpu2006"

RESULTS_DIR="$PROJECT_ROOT/results/part2_v2"
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
# V2 CONFIGURATIONS - Based on V1 Results Analysis
# Format: "config_name|l1i_size|l1d_size|l2_size|l1i_assoc|l1d_assoc|l2_assoc|cacheline"
# =============================================================================

# --- specbzip: Best was cfg5 (L1d=128kB, L2=4MB, line=256) CPI=1.591 ---
# Explore: larger cachelines, L1d variations, L2 assoc
CONFIGS_specbzip=(
    # Baseline variations around best config
    "v01|32kB|128kB|4MB|2|4|8|256"       # Best from V1
    "v02|32kB|128kB|4MB|2|8|8|256"       # Higher L1d assoc
    "v03|32kB|128kB|4MB|2|4|16|256"      # Higher L2 assoc
    "v04|32kB|128kB|4MB|2|8|16|256"      # Both higher assoc
    # L1d size variations
    "v05|32kB|64kB|4MB|2|4|8|256"        # Smaller L1d
    "v06|64kB|128kB|4MB|2|4|8|256"       # Larger L1i
    "v07|32kB|192kB|4MB|2|4|8|256"       # Max L1d (192+32=224<256)
    # L2 variations
    "v08|32kB|128kB|2MB|2|4|16|256"      # Smaller L2, higher assoc
    "v09|32kB|128kB|4MB|2|4|8|128"       # Smaller cacheline
    "v10|64kB|128kB|4MB|2|8|16|256"      # All enhanced
    "v11|32kB|128kB|4MB|4|4|8|256"       # Higher L1i assoc
    "v12|32kB|128kB|4MB|2|4|4|256"       # Lower L2 assoc
)

# --- spechmmer: Best was cfg3 (L1d=64kB, line=128) CPI=1.181 ---
# Already near optimal, explore small variations
CONFIGS_spechmmer=(
    # Baseline around best
    "v01|64kB|64kB|512kB|2|2|4|128"      # Best from V1
    "v02|64kB|64kB|512kB|4|4|4|128"      # Higher assoc
    "v03|64kB|64kB|1MB|2|2|8|128"        # Larger L2
    "v04|64kB|64kB|512kB|2|2|8|128"      # Higher L2 assoc only
    # Size variations
    "v05|32kB|64kB|512kB|2|2|4|128"      # Smaller L1i
    "v06|64kB|32kB|512kB|2|2|4|128"      # Smaller L1d
    "v07|64kB|128kB|512kB|2|2|4|128"     # Larger L1d
    "v08|128kB|64kB|512kB|2|2|4|128"     # Larger L1i
    # Cacheline variations
    "v09|64kB|64kB|512kB|2|2|4|64"       # Smaller cacheline
    "v10|64kB|64kB|512kB|2|2|4|256"      # Larger cacheline
    "v11|64kB|64kB|1MB|4|4|8|128"        # All enhanced
    "v12|32kB|32kB|512kB|2|2|4|128"      # Minimal L1
)

# --- specmcf: Best was cfg4 (L1d=64kB, L2=2MB) CPI=1.152 ---
# Explore L1d and L2 balance
CONFIGS_specmcf=(
    # Baseline around best
    "v01|64kB|64kB|2MB|4|4|8|64"         # Best from V1
    "v02|64kB|64kB|2MB|4|4|16|64"        # Higher L2 assoc
    "v03|64kB|64kB|4MB|4|4|8|64"         # Larger L2
    "v04|64kB|64kB|4MB|4|4|16|64"        # Max L2 + high assoc
    # L1 variations
    "v05|128kB|64kB|2MB|4|4|8|64"        # Larger L1i
    "v06|64kB|128kB|2MB|4|4|8|64"        # Larger L1d
    "v07|128kB|64kB|2MB|8|4|8|64"        # Max L1i assoc
    "v08|64kB|64kB|2MB|8|8|8|64"         # Higher all assoc
    # Cacheline variations
    "v09|64kB|64kB|2MB|4|4|8|128"        # Larger cacheline
    "v10|64kB|64kB|2MB|4|4|8|32"         # Smaller cacheline
    "v11|64kB|128kB|4MB|4|4|16|64"       # Max config
    "v12|128kB|64kB|4MB|8|4|16|64"       # Max L1i focus
)

# --- specsjeng: Best was cfg4/5 (L1d=128kB, line=256) CPI=5.17 ---
# Cacheline 256B was crucial! Explore around this
CONFIGS_specsjeng=(
    # Baseline around best
    "v01|64kB|128kB|4MB|2|4|8|256"       # Best from V1
    "v02|64kB|128kB|4MB|4|4|8|256"       # Higher L1i assoc
    "v03|64kB|128kB|4MB|2|4|16|256"      # Higher L2 assoc
    "v04|64kB|128kB|4MB|4|4|16|256"      # Both higher assoc
    # L1d variations - key parameter
    "v05|64kB|64kB|4MB|4|4|8|256"        # Smaller L1d
    "v06|32kB|192kB|4MB|2|4|8|256"       # Max L1d (32+192=224<256)
    "v07|64kB|128kB|4MB|2|8|8|256"       # Higher L1d assoc
    "v08|64kB|128kB|4MB|2|8|16|256"      # High L1d + L2 assoc
    # L2 and cacheline variations
    "v09|64kB|128kB|2MB|4|4|16|256"      # Smaller L2
    "v10|32kB|128kB|4MB|2|4|8|256"       # Smaller L1i
    "v11|64kB|128kB|4MB|4|8|16|256"      # Max assoc
    "v12|128kB|64kB|4MB|4|4|16|256"      # Swap L1i/L1d
)

# --- speclibm: Best was cfg3/4 (line=256) CPI=1.989 ---
# Cacheline 256B was crucial! Explore further
CONFIGS_speclibm=(
    # Baseline around best
    "v01|32kB|128kB|4MB|2|4|8|256"       # Best from V1
    "v02|32kB|128kB|4MB|2|8|8|256"       # Higher L1d assoc
    "v03|32kB|128kB|4MB|2|4|16|256"      # Higher L2 assoc
    "v04|32kB|128kB|4MB|2|8|16|256"      # Both higher assoc
    # L1d variations
    "v05|32kB|64kB|4MB|2|4|8|256"        # Smaller L1d
    "v06|32kB|192kB|4MB|2|4|8|256"       # Max L1d
    "v07|64kB|128kB|4MB|2|4|8|256"       # Larger L1i
    "v08|64kB|64kB|4MB|2|4|8|256"        # Balanced L1
    # L2 variations
    "v09|32kB|128kB|2MB|2|4|16|256"      # Smaller L2
    "v10|32kB|128kB|4MB|4|4|8|256"       # Higher L1i assoc
    "v11|64kB|128kB|4MB|4|8|16|256"      # All max assoc
    "v12|32kB|128kB|4MB|2|4|8|128"       # Test smaller cacheline
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
echo "Part 2 V2: Refined Design Exploration"
echo "=============================================="
echo ""
echo "Based on V1 results, exploring 12 configurations per benchmark"
echo ""
echo "Results Structure:"
echo "  results/part2_v2/"
for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    echo "  ├── $name/ (12 configs)"
done
echo ""

# --- Command Generation ---
CMD_FILE="/tmp/part2_v2_commands.txt"
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
echo "Starting V2 benchmarks ($MAX_PARALLEL parallel jobs)..."
echo ""

cd "$GEM5_DIR" || exit 1
parallel -j "$MAX_PARALLEL" --joblog "$RESULTS_DIR/jobs.log" < "$CMD_FILE"
EXIT_STATUS=$?

echo ""
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ All V2 benchmarks completed!"
else
    echo "⚠️  Some benchmarks had errors. Check logs."
fi

# --- Results Collection ---
echo ""
echo "Extracting results..."

for bench in "${BENCHMARKS[@]}"; do
    IFS='|' read -r name bin args <<< "$bench"
    
    BENCH_RESULTS="$RESULTS_DIR/$name"
    INI_FILE="$CONFIG_DIR/conf_${name}_v2.ini"
    RESULTS_CSV="$BENCH_RESULTS/${name}_v2_results.csv"
    
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
    
    echo "  $name -> ${name}_v2_results.csv"
    bash "$SCRIPT_DIR/read_results.sh" "$INI_FILE"
done

echo ""
echo "=============================================="
echo "V2 Complete! Results in results/part2_v2/"
echo "=============================================="
