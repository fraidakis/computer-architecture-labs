#!/usr/bin/env python3
"""
Cost Function & Cost/Performance Analysis Script
=================================================
Physically-based additive cost function that reflects actual cache architecture.

The cost model separates cache into three components:
- Data Array: Stores actual cache data (scales with capacity and cell type)
- Tag Array: Stores address tags (scales as 1/CL - larger lines = fewer tags)
- Logic Overhead: Comparators, MUX, LRU (scales with associativity)

Part 3 of the Computer Architecture Bonus Assignment.

References:
- Intel Skylake Die Analysis (WikiChip) - 8T vs 6T cell area ratios
- ISSCC Papers (2015-2020) - SRAM cell scaling
- Hennessy & Patterson 6th Ed., Chapter 2 - Tag overhead calculations
"""

import os
import warnings
from pathlib import Path
from typing import Dict, List, Tuple
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import seaborn as sns

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION & STYLING
# =============================================================================

COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'accent1': '#F18F01',
    'accent2': '#C73E1D',
    'success': '#27AE60',
    'warning': '#F39C12',
    'dark': '#2C3E50',
}

BENCHMARK_COLORS = {
    'specbzip': '#2E86AB',
    'spechmmer': '#A23B72',
    'specmcf': '#F18F01',
    'specsjeng': '#C73E1D',
    'speclibm': '#27AE60',
}

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'figure.facecolor': '#FAFBFC',
    'axes.facecolor': '#FFFFFF',
})

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / 'plots' / 'task3'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# PHYSICALLY-BASED ADDITIVE COST MODEL
# =============================================================================
# C_total = C_data + C_tag + C_logic
#
# C_data = S_L1 × γ_L1 + S_L2 × γ_L2
# C_tag  = Σ (S_i / CL) × (T_w + σ) × γ_i
# C_logic = C_tag × δ × W
#
# Combined: C = (S_L1 × γ_L1 + S_L2 × γ_L2) + Σ (S_i/CL × (T_w + σ) × γ_i × (1 + δ × W_i))

COST_PARAMS = {
    'GAMMA_L1': 2.0,          # L1 cell density factor (8T SRAM ~2× larger than 6T)
    'GAMMA_L2': 1.0,          # L2 baseline (6T SRAM)
    'ADDR_WIDTH': 32,         # Address width in bits
    'DELTA': 0.05,            # Logic overhead per way (~5% per way on tag+logic)
}

# =============================================================================
# CONFIGURATION DATA
# =============================================================================

DEFAULT_CONFIG = {
    'name': 'Default',
    'L1i_size_KB': 32,
    'L1d_size_KB': 64,
    'L2_size_KB': 2048,
    'L1i_assoc': 2,
    'L1d_assoc': 2,
    'L2_assoc': 8,
    'cacheline_B': 64,
}

OPTIMAL_CONFIGS = {
    'spechmmer': {
        'name': 'spechmmer-opt',
        'L1i_size_KB': 64,
        'L1d_size_KB': 64,  # Reduced from 128KB
        'L2_size_KB': 512,
        'L1i_assoc': 2,
        'L1d_assoc': 2,     # Reduced from 8-way
        'L2_assoc': 4,
        'cacheline_B': 256,
        'cpi': 1.177,
    },
    'specmcf': {
        'name': 'specmcf-opt',
        'L1i_size_KB': 32,  # Keep default
        'L1d_size_KB': 64,  # Keep default
        'L2_size_KB': 2048, # Keep default
        'L1i_assoc': 2,     # Keep default
        'L1d_assoc': 2,     # Keep default
        'L2_assoc': 8,      # Keep default
        'cacheline_B': 512, # Only change: larger cacheline
        'cpi': 1.105,
    },
    'specbzip': {
        'name': 'specbzip-opt',
        'L1i_size_KB': 32,
        'L1d_size_KB': 128,
        'L2_size_KB': 4096,
        'L1i_assoc': 2,
        'L1d_assoc': 16,
        'L2_assoc': 16,
        'cacheline_B': 256,
        'cpi': 1.589,
    },
    'speclibm': {
        'name': 'speclibm-opt',
        'L1i_size_KB': 16,
        'L1d_size_KB': 16,
        'L2_size_KB': 128,
        'L1i_assoc': 1,
        'L1d_assoc': 2,
        'L2_assoc': 1,
        'cacheline_B': 2048,
        'cpi': 1.496,
    },
    'specsjeng': {
        'name': 'specsjeng-opt',
        'L1i_size_KB': 16,  # Reduced from 32KB
        'L1d_size_KB': 128,
        'L2_size_KB': 512,  # MAJOR: Reduced from 2MB to 512KB!
        'L1i_assoc': 2,
        'L1d_assoc': 4,
        'L2_assoc': 2,      # Reduced from 8-way
        'cacheline_B': 2048,
        'cpi': 3.072,
    },
}

DEFAULT_CPIS = {
    'spechmmer': 1.188,
    'specmcf': 1.294,
    'specbzip': 1.680,
    'speclibm': 3.494,
    'specsjeng': 10.271,
}


# =============================================================================
# ADDITIVE COST FUNCTION IMPLEMENTATION
# =============================================================================

def calculate_tag_width(cache_size_kb: int, cacheline_b: int, assoc: int) -> int:
    """
    Calculate tag width for a cache.
    T_w = Address_width - log2(CL) - log2(Sets)
    """
    p = COST_PARAMS
    cache_size_b = cache_size_kb * 1024  # Convert to bytes
    num_lines = cache_size_b // cacheline_b
    num_sets = num_lines // assoc if assoc > 0 else num_lines
    
    offset_bits = int(math.log2(cacheline_b)) if cacheline_b > 0 else 0
    index_bits = int(math.log2(num_sets)) if num_sets > 1 else 0
    tag_width = p['ADDR_WIDTH'] - offset_bits - index_bits
    
    return max(tag_width, 1)  # At least 1 bit for tag


def calculate_status_bits(assoc: int) -> int:
    """
    Calculate status bits per cache line.
    σ = valid(1) + dirty(1) + LRU(log2(W)) ≈ 2 + log2(W)
    """
    lru_bits = int(math.ceil(math.log2(assoc))) if assoc > 1 else 0
    return 2 + lru_bits


def calculate_cost(config: Dict) -> float:
    """
    Calculate hardware cost using ADDITIVE physical model.
    
    Formula: C_total = C_data + C_tag_and_logic
    
    C_data = S_L1 × γ_L1 + S_L2 × γ_L2
    C_tag_and_logic = Σ (S_i / CL) × (T_w + σ) × γ_i × (1 + δ × W_i)
    
    Where:
    - γ_L1 = 2.0: L1 cell density factor (8T SRAM ~2× larger than 6T)
    - γ_L2 = 1.0: L2 baseline (6T SRAM)
    - T_w: Tag width in bits
    - σ: Status bits (valid + dirty + LRU)
    - δ = 0.05: Logic overhead per way
    """
    p = COST_PARAMS
    
    # L1 sizes
    l1i_kb = config['L1i_size_KB']
    l1d_kb = config['L1d_size_KB']
    l1_total_kb = l1i_kb + l1d_kb
    l2_kb = config['L2_size_KB']
    cl = config['cacheline_B']
    
    # Data Array Cost: C_data = S_L1 × γ_L1 + S_L2 × γ_L2
    c_data = (l1_total_kb * p['GAMMA_L1']) + (l2_kb * p['GAMMA_L2'])
    
    # Tag & Logic Overhead for L1i
    l1i_tag_w = calculate_tag_width(l1i_kb, cl, config['L1i_assoc'])
    l1i_status = calculate_status_bits(config['L1i_assoc'])
    l1i_num_lines = (l1i_kb * 1024) / cl
    l1i_overhead = l1i_num_lines * (l1i_tag_w + l1i_status) * p['GAMMA_L1'] * (1 + p['DELTA'] * config['L1i_assoc'])
    # Scale down to KB-equivalent units (divide by 8*1024 to convert bits to KB)
    l1i_overhead = l1i_overhead / (8 * 1024)
    
    # Tag & Logic Overhead for L1d
    l1d_tag_w = calculate_tag_width(l1d_kb, cl, config['L1d_assoc'])
    l1d_status = calculate_status_bits(config['L1d_assoc'])
    l1d_num_lines = (l1d_kb * 1024) / cl
    l1d_overhead = l1d_num_lines * (l1d_tag_w + l1d_status) * p['GAMMA_L1'] * (1 + p['DELTA'] * config['L1d_assoc'])
    l1d_overhead = l1d_overhead / (8 * 1024)
    
    # Tag & Logic Overhead for L2
    l2_tag_w = calculate_tag_width(l2_kb, cl, config['L2_assoc'])
    l2_status = calculate_status_bits(config['L2_assoc'])
    l2_num_lines = (l2_kb * 1024) / cl
    l2_overhead = l2_num_lines * (l2_tag_w + l2_status) * p['GAMMA_L2'] * (1 + p['DELTA'] * config['L2_assoc'])
    l2_overhead = l2_overhead / (8 * 1024)
    
    # Total tag/logic overhead
    c_tag_logic = l1i_overhead + l1d_overhead + l2_overhead
    
    # Total cost (additive)
    total = c_data + c_tag_logic
    
    return round(total, 1)


def calculate_cost_breakdown(config: Dict) -> Dict[str, float]:
    """Get detailed cost breakdown for visualization."""
    p = COST_PARAMS
    
    l1i_kb = config['L1i_size_KB']
    l1d_kb = config['L1d_size_KB']
    l1_total_kb = l1i_kb + l1d_kb
    l2_kb = config['L2_size_KB']
    cl = config['cacheline_B']
    
    # Data Array Cost
    c_data_l1 = l1_total_kb * p['GAMMA_L1']
    c_data_l2 = l2_kb * p['GAMMA_L2']
    c_data = c_data_l1 + c_data_l2
    
    # Tag & Logic Overhead (simplified calculation for display)
    total_kb = l1_total_kb + l2_kb
    avg_ways = (config['L1i_assoc'] + config['L1d_assoc'] + config['L2_assoc']) / 3
    
    # Simplified tag overhead using proxy formula: S_total × (A_w / CL) × (1 + δ × W̄)
    tag_overhead = total_kb * (p['ADDR_WIDTH'] / cl) * (1 + p['DELTA'] * avg_ways)
    
    total = c_data + tag_overhead
    
    return {
        'c_data_l1': c_data_l1,
        'c_data_l2': c_data_l2,
        'c_data': c_data,
        'tag_overhead': tag_overhead,
        'avg_ways': avg_ways,
        'cacheline': cl,
        'total': total,
    }


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_all_configs() -> pd.DataFrame:
    """Analyze cost and performance for all configurations."""
    results = []
    
    for bench, default_cpi in DEFAULT_CPIS.items():
        default_cost = calculate_cost(DEFAULT_CONFIG)
        results.append({
            'benchmark': bench,
            'config_type': 'Default',
            'cpi': default_cpi,
            'cost': default_cost,
            'cost_performance': default_cpi * default_cost,
            'L1_total_KB': DEFAULT_CONFIG['L1i_size_KB'] + DEFAULT_CONFIG['L1d_size_KB'],
            'L2_KB': DEFAULT_CONFIG['L2_size_KB'],
            'cacheline_B': DEFAULT_CONFIG['cacheline_B'],
        })
    
    for bench, config in OPTIMAL_CONFIGS.items():
        opt_cost = calculate_cost(config)
        results.append({
            'benchmark': bench,
            'config_type': 'Optimized',
            'cpi': config['cpi'],
            'cost': opt_cost,
            'cost_performance': config['cpi'] * opt_cost,
            'L1_total_KB': config['L1i_size_KB'] + config['L1d_size_KB'],
            'L2_KB': config['L2_size_KB'],
            'cacheline_B': config['cacheline_B'],
        })
    
    return pd.DataFrame(results)


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_cost_performance_tradeoff():
    """Plot cost vs CPI with iso-cost-performance curves."""
    print("📊 Generating Cost vs Performance Trade-off Plot...")
    
    df = analyze_all_configs()
    
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor('#FAFBFC')
    ax.set_facecolor('#FFFFFF')
    
    # Custom label offsets for each benchmark (x_offset, y_offset)
    LABEL_OFFSETS = {
        'specsjeng': (-53, 5),    # Left
        'speclibm': (-5, -25),    # Top-left
        'spechmmer': (-5, -25),   # Down
        'specmcf': (15, -18),     # Down-right
        'specbzip': (12, 12),      # Default
    }
    
    for bench in OPTIMAL_CONFIGS.keys():
        # Skip mcf as requested
        if bench == 'specmcf':
            continue
        bench_df = df[df['benchmark'] == bench]
        color = BENCHMARK_COLORS[bench]
        
        default = bench_df[bench_df['config_type'] == 'Default'].iloc[0]
        optimized = bench_df[bench_df['config_type'] == 'Optimized'].iloc[0]
        
        # Arrow from default to optimized
        ax.annotate('', xy=(optimized['cost'], optimized['cpi']),
                   xytext=(default['cost'], default['cpi']),
                   arrowprops=dict(arrowstyle='->', color=color, lw=2.5, alpha=0.7))
        
        # Default (hollow circle)
        ax.scatter(default['cost'], default['cpi'], s=280, 
                  facecolors='white', edgecolors=color, linewidths=3, 
                  zorder=5, marker='o')
        
        # Optimized (filled star)
        ax.scatter(optimized['cost'], optimized['cpi'], s=400, 
                  c=color, edgecolors='white', linewidths=2.5, 
                  zorder=6, marker='*')
        
        # Label with custom position
        offset = LABEL_OFFSETS.get(bench, (12, 8))
        ax.annotate(bench.replace('spec', '').upper(),
                   (optimized['cost'], optimized['cpi']),
                   xytext=offset, textcoords='offset points',
                   fontsize=12, fontweight='bold', color='#2C3E50',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                            edgecolor=color, linewidth=2, alpha=0.95))
    
    # Iso-cost-performance curves (CPI × Cost = constant)
    max_cost = df['cost'].max() * 1.3
    costs = np.linspace(50, max_cost, 100)
    for cp_value in [500, 2000, 5000, 15000]:
        cpis = cp_value / costs
        valid = (cpis <= 12) & (cpis >= 0.5)
        if valid.any():
            ax.plot(costs[valid], cpis[valid], '--', color='#BDC3C7', 
                   alpha=0.6, linewidth=1.5)
            idx = len(cpis[valid]) // 3
            if idx < len(costs[valid]):
                label_text = f'{cp_value}' if cp_value < 1000 else f'{cp_value//1000}k'
                ax.text(costs[valid][idx], cpis[valid][idx], 
                       f'CPI×Cost={label_text}', fontsize=9, color='#7F8C8D',
                       rotation=-30, ha='center', va='bottom', style='italic')
    
    # Enhanced Legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='white',
                  markeredgecolor='#2C3E50', markersize=14, markeredgewidth=2.5,
                  label='Default Configuration'),
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='#2C3E50',
                  markeredgecolor='white', markersize=18, markeredgewidth=2,
                  label='Optimized Configuration'),
    ]
    legend = ax.legend(handles=legend_elements, loc='upper right', fontsize=12,
             framealpha=0.95, edgecolor='#CCCCCC', fancybox=True, shadow=True)
    legend.get_frame().set_linewidth(1.5)
    
    # Enhanced axis labels
    ax.set_xlabel('Hardware Cost (Area Cost Units)', fontsize=15, 
                 fontweight='bold', color='#2C3E50', labelpad=12)
    ax.set_ylabel('CPI (Cycles Per Instruction)', fontsize=15, 
                 fontweight='bold', color='#2C3E50', labelpad=12)
    
    # Enhanced title
    ax.set_title('Cost vs Performance Trade-off\n' + 
                r'$C = (S_{L1} \cdot \gamma_{L1} + S_{L2} \cdot \gamma_{L2}) + \sum \frac{S_i}{CL}(T_w + \sigma)$', 
                fontsize=17, fontweight='bold', color='#1A252F', pad=20)
    
    # Enhanced grid and spines
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.8, color='#B0B0B0')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['left'].set_color('#555555')
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['bottom'].set_color('#555555')
    
    # Enhanced tick labels
    ax.tick_params(axis='both', which='major', labelsize=11, colors='#333333')
    
    ax.set_xlim(0, max_cost)
    ax.set_ylim(0, 12)
    
    plt.tight_layout(pad=2.0)
    output_path = OUTPUT_DIR / 'cost_performance_tradeoff.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#FAFBFC')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


def plot_cost_efficiency():
    """Plot cost-performance product comparison."""
    print("📊 Generating Cost Efficiency Plot...")
    
    df = analyze_all_configs()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('#FAFBFC')
    ax.set_facecolor('#FFFFFF')
    
    benchmarks = list(OPTIMAL_CONFIGS.keys())
    x = np.arange(len(benchmarks))
    width = 0.35
    
    default_cp = []
    optimized_cp = []
    
    for bench in benchmarks:
        bench_df = df[df['benchmark'] == bench]
        default_cp.append(bench_df[bench_df['config_type'] == 'Default']['cost_performance'].values[0])
        optimized_cp.append(bench_df[bench_df['config_type'] == 'Optimized']['cost_performance'].values[0])
    
    bars1 = ax.bar(x - width/2, default_cp, width, label='Default',
                  color='#95A5A6', edgecolor='white', linewidth=2)
    bars2 = ax.bar(x + width/2, optimized_cp, width, label='Optimized',
                  color=[BENCHMARK_COLORS[b] for b in benchmarks],
                  edgecolor='white', linewidth=2)
    
    # Value labels
    for bar, val in zip(bars1, default_cp):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 800,
               f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=9,
               fontweight='bold', color='#7F8C8D')
    
    for bar, val in zip(bars2, optimized_cp):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 800,
               f'{val/1000:.1f}k', ha='center', va='bottom', fontsize=9,
               fontweight='bold', color='#2C3E50')
    
    # Improvement badges - moved closer to bars
    for i, (d, o) in enumerate(zip(default_cp, optimized_cp)):
        improvement = (d - o) / d * 100
        color = '#27AE60' if improvement > 0 else '#E74C3C'
        symbol = '▼' if improvement > 0 else '▲'
        ax.annotate(f'{symbol} {abs(improvement):.0f}%',
                   xy=(i, max(d, o) + 2500),
                   ha='center', fontsize=10, fontweight='bold', color='white',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=color,
                            edgecolor='white', linewidth=1.5, alpha=0.95))
    
    ax.set_ylabel('Cost × CPI (Lower = Better)', fontsize=13, 
                 fontweight='bold', color='#2C3E50')
    ax.set_xlabel('Benchmark', fontsize=13, fontweight='bold', color='#2C3E50')
    ax.set_title('Cost-Efficiency Comparison\n(Additive Physical Cost Model)', 
                fontsize=16, fontweight='bold', color='#2C3E50', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace('spec', '').upper() for b in benchmarks],
                       fontsize=12, fontweight='bold')
    
    # Legend removed as requested
    ax.grid(True, axis='y', alpha=0.15)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    ax.set_ylim(0, max(default_cp) * 1.20)
    
    plt.tight_layout(pad=2.0)
    output_path = OUTPUT_DIR / 'cost_efficiency.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#FAFBFC')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


def print_analysis_table():
    """Print detailed analysis table."""
    print("\n" + "=" * 100)
    print("📋 COST-PERFORMANCE ANALYSIS (Additive Model: C = (L1×γ_L1 + L2×γ_L2) + Tag_overhead)")
    print("=" * 100)
    
    df = analyze_all_configs()
    
    print(f"\n{'Benchmark':<12} {'Config':<10} {'CPI':>8} {'Cost':>10} {'CPI×Cost':>12} {'Δ Efficiency':>14}")
    print("-" * 80)
    
    for bench in OPTIMAL_CONFIGS.keys():
        bench_df = df[df['benchmark'] == bench]
        default = bench_df[bench_df['config_type'] == 'Default'].iloc[0]
        optimized = bench_df[bench_df['config_type'] == 'Optimized'].iloc[0]
        
        efficiency_change = (default['cost_performance'] - optimized['cost_performance']) / default['cost_performance'] * 100
        
        print(f"{bench:<12} {'Default':<10} {default['cpi']:>8.3f} {default['cost']:>10.0f} {default['cost_performance']:>12.0f}")
        print(f"{'':<12} {'Optimized':<10} {optimized['cpi']:>8.3f} {optimized['cost']:>10.0f} {optimized['cost_performance']:>12.0f} {efficiency_change:>+13.1f}%")
        print()
    
    print("=" * 100)
    
    opt_df = df[df['config_type'] == 'Optimized']
    best_idx = opt_df['cost_performance'].idxmin()
    best = opt_df.loc[best_idx]
    
    print(f"\n🏆 BEST COST-EFFICIENCY: {best['benchmark'].replace('spec', '').upper()}")
    print(f"   CPI × Cost = {best['cost_performance']:.0f} (CPI={best['cpi']:.3f}, Cost={best['cost']:.0f})")
    
    return df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Generate all cost analysis outputs."""
    print("=" * 70)
    print("💰 PHYSICALLY-BASED ADDITIVE COST ANALYSIS")
    print("   Model: C = (S_L1 × γ_L1 + S_L2 × γ_L2) + Tag_overhead")
    print("   γ_L1=2.0 (8T SRAM), γ_L2=1.0 (6T), Tag ∝ 1/CL")
    print("=" * 70)
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print()
    
    plot_cost_performance_tradeoff()
    plot_cost_efficiency()
    
    df = print_analysis_table()
    
    print()
    print("=" * 70)
    print("✅ COST ANALYSIS COMPLETE!")
    print(f"📁 Find your plots in: {OUTPUT_DIR}")
    print("=" * 70)
    
    return df


if __name__ == '__main__':
    main()
