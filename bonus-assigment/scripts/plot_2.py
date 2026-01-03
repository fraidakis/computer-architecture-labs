#!/usr/bin/env python3
"""
Benchmark Results Visualization Script
=======================================
Professional plotting for gem5 SPEC benchmark results.

Generates:
1. Configuration Scatter Plot (L1d size vs CPI)
2. Per-benchmark CPI Progression Curves

Author: Auto-generated
Date: 2025-12-31
"""

import os
import glob
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION & STYLING
# =============================================================================

# Professional color palette (inspired by modern data viz)
COLORS = {
    'primary': '#2E86AB',      # Deep blue
    'secondary': '#A23B72',    # Magenta
    'accent1': '#F18F01',      # Orange
    'accent2': '#C73E1D',      # Red
    'accent3': '#3B1F2B',      # Dark purple
    'success': '#2ECC71',      # Green
    'warning': '#F39C12',      # Yellow
    'dark': '#2C3E50',         # Dark slate
    'light': '#ECF0F1',        # Light gray
    'white': '#FFFFFF',
}

# Benchmark-specific colors
BENCHMARK_COLORS = {
    'specbzip': '#2E86AB',
    'spechmmer': '#A23B72',
    'specmcf': '#F18F01',
    'specsjeng': '#C73E1D',
    'speclibm': '#27AE60',
}



# Set global style - Premium modern aesthetic
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.labelsize': 13,
    'axes.labelweight': 'semibold',
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'legend.framealpha': 0.95,
    'legend.edgecolor': '#E0E0E0',
    'figure.titlesize': 18,
    'figure.titleweight': 'bold',
    'figure.facecolor': '#FAFBFC',
    'axes.facecolor': '#FFFFFF',
    'axes.edgecolor': '#D0D0D0',
    'axes.linewidth': 1.5,
    'grid.alpha': 0.25,
    'grid.linestyle': '-',
    'grid.linewidth': 0.8,
})

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_DIR / 'results'
OUTPUT_DIR = PROJECT_DIR / 'plots' / 'task2'

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARKS = ['specbzip', 'spechmmer', 'specmcf', 'specsjeng', 'speclibm']


# =============================================================================




# =============================================================================
# PLOT 2: PER-BENCHMARK CPI PROGRESSION CURVE
# =============================================================================

def plot_cpi_progression_per_benchmark():
    """Create line charts showing CPI progression (sorted) for each benchmark."""
    print("📊 Generating Per-Benchmark CPI Progression Curves...")
    
    data = load_new_benchmark_results()
    
    for benchmark in ['specsjeng']:  # Only generate for specsjeng
        if benchmark not in data:
            continue

        df = data[benchmark]
        
        # Prepare data: clean and sort
        bench_data = df[['Benchmarks', 'system.cpu.cpi']].copy()
        bench_data = bench_data.rename(columns={'Benchmarks': 'config', 'system.cpu.cpi': 'cpi'})
        bench_data = bench_data.dropna(subset=['cpi'])

        bench_data = bench_data.sort_values('cpi', ascending=False).reset_index(drop=True)
        
        # Create figure with subtle background
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor('#FAFBFC')
        ax.set_facecolor('#FFFFFF')
        
        # Get data
        x = np.arange(len(bench_data))
        cpis = bench_data['cpi'].values
        configs = bench_data['config'].values
        bench_color = BENCHMARK_COLORS.get(benchmark, '#2E86AB')
        
        # Create smooth gradient fill under curve
        ax.fill_between(x, cpis, cpis[-1] * 0.9, alpha=0.08, color=bench_color)
        for i in range(len(x) - 1):
            gradient_alpha = 0.15 - (i / len(x)) * 0.08  # Fade gradient
            ax.fill_between([x[i], x[i+1]], [cpis[i], cpis[i+1]], 
                           alpha=gradient_alpha, color=bench_color)
        
        # Shadow line for depth effect
        ax.plot(x, cpis, '-', linewidth=6, color='#000000', alpha=0.08, zorder=4)
        
        # Main line with gradient-like effect
        ax.plot(x, cpis, '-', linewidth=4, color=bench_color, alpha=0.9, zorder=5,
                solid_capstyle='round', solid_joinstyle='round')
        
        # Outer glow for scatter points
        ax.scatter(x, cpis, c=bench_color, s=180, alpha=0.2, zorder=8)
        # Main scatter points with gradient effect
        ax.scatter(x, cpis, c=bench_color, s=120, edgecolors='white', 
                  linewidth=2.5, zorder=10, alpha=0.95)
        
        # Best point with glow effect
        ax.scatter(x[-1], cpis[-1], c='#1ABC9C', s=500, alpha=0.2, zorder=13)  # Glow
        ax.scatter(x[-1], cpis[-1], c='#1ABC9C', s=350, marker='*', 
                  edgecolors='#FFFFFF', linewidth=2.5, zorder=15, label='Best')
        
        # Worst point with glow effect  
        ax.scatter(x[0], cpis[0], c='#E74C3C', s=350, alpha=0.2, zorder=13)  # Glow
        ax.scatter(x[0], cpis[0], c='#E74C3C', s=220, marker='X', 
                  edgecolors='#FFFFFF', linewidth=2.5, zorder=15, label='Baseline')
        
        # Baseline reference line with style
        baseline_mask = bench_data['config'].astype(str).str.contains('baseline|cfg1', case=False)
        if baseline_mask.any():
            default_cpi = bench_data.loc[baseline_mask, 'cpi'].values[0]
            ax.hlines(y=default_cpi, xmin=x[0]-0.3, xmax=x[-1]+0.3, 
                      colors='#7F8C8D', linestyles='--', linewidth=2.5, alpha=0.6)
            ax.text(x[-1]+0.4, default_cpi, f'Baseline\n{default_cpi:.2f}', 
                   fontsize=10, color='#7F8C8D', va='center', fontweight='bold')
        
        # X-axis labels (config names)
        ax.set_xticks(x)
        # Clean up config names
        clean_configs = [str(c).replace('system.cpu.', '') for c in configs]
        ax.set_xticklabels(clean_configs, rotation=45, ha='right', fontsize=9)
        
        # Calculate improvement
        improvement = ((cpis[0] - cpis[-1]) / cpis[0]) * 100
        
        # Premium annotation boxes
        # Best annotation - ABOVE the line
        ax.annotate(f'✓ Best: {cpis[-1]:.2f}', 
                   xy=(x[-1], cpis[-1]), 
                   xytext=(x[-1] - 1.5, cpis[-1] + (cpis[0] - cpis[-1]) * 0.12),
                   fontsize=12, fontweight='bold', color='white',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='#1ABC9C', 
                            edgecolor='#16A085', linewidth=2, alpha=0.95),
                   arrowprops=dict(arrowstyle='->', color='#1ABC9C', lw=2,
                                  connectionstyle='arc3,rad=-0.2'))
        
        ax.annotate(f'✗ Baseline: {cpis[0]:.2f}', 
                   xy=(x[0], cpis[0]), 
                   xytext=(x[0] + 1.2, cpis[0] + (cpis[0] - cpis[-1]) * 0.12),
                   fontsize=12, fontweight='bold', color='white',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='#E74C3C', 
                            edgecolor='#C0392B', linewidth=2, alpha=0.95),
                   arrowprops=dict(arrowstyle='->', color='#E74C3C', lw=2,
                                  connectionstyle='arc3,rad=-0.2'))
        
        # Styling with premium look
        ax.set_xlabel('Configuration (sorted by CPI: worst → best)', 
                     fontweight='bold', fontsize=13, color='#2C3E50')
        ax.set_ylabel('CPI (Cycles Per Instruction)', fontweight='bold', fontsize=13, color='#2C3E50')
        
        # Title with improvement badge
        ax.set_title(f'{benchmark.replace("spec", "").upper()} — CPI Optimization Journey', 
                    fontsize=16, fontweight='bold', color='#2C3E50', pad=25)
        
        # Add improvement badge as text box
        ax.text(0.98, 0.97, f'▼ {improvement:.1f}%\nImprovement', 
               transform=ax.transAxes, fontsize=11, fontweight='bold',
               va='top', ha='right', color='white',
               bbox=dict(boxstyle='round,pad=0.6', facecolor='#27AE60', 
                        edgecolor='#1E8449', linewidth=2, alpha=0.95))
        
        
        # Premium grid styling
        ax.yaxis.grid(True, linestyle='-', alpha=0.15, linewidth=1, color='#BDC3C7')
        ax.xaxis.grid(True, linestyle='-', alpha=0.08, linewidth=0.5, color='#BDC3C7')
        ax.set_axisbelow(True)
        
        # Clean spines with subtle styling
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color('#D0D0D0')
            ax.spines[spine].set_linewidth(1.5)
        
        # Set y-axis limits with generous padding
        y_range = cpis[0] - cpis[-1]
        ax.set_ylim(cpis[-1] - y_range * 0.15, cpis[0] + y_range * 0.2)
        ax.set_xlim(x[0]-0.7, x[-1]+0.7)

        plt.tight_layout(pad=2.0)
        
        # Save with high quality
        output_path = OUTPUT_DIR / f'{benchmark}_cpi_progression.png'
        plt.savefig(output_path, dpi=200, bbox_inches='tight', 
                   facecolor='#FAFBFC', edgecolor='none')
        plt.close()
        print(f"   ✅ Saved: {output_path}")


# =============================================================================
# DATA LOADING
# =============================================================================

def load_new_benchmark_results() -> Dict[str, pd.DataFrame]:
    """Load benchmark results from the new structure (results/spec*_results.csv)."""
    data = {}
    for bench in BENCHMARKS:
        csv_path = RESULTS_DIR / f"{bench}_results.csv"
        if csv_path.exists():
            try:
                # Try with on_bad_lines='skip' to handle malformed rows
                df = pd.read_csv(csv_path, on_bad_lines='skip')
                df.columns = df.columns.str.strip()
                data[bench] = df
            except Exception as e:
                print(f"   ⚠️ Warning: Could not load {bench}: {e}")
    return data


# =============================================================================
# PLOT 4: OPTIMIZATION IMPACT (Baseline vs Best)
# =============================================================================

def plot_optimization_impact():
    """Plot baseline vs best CPI with improvement percentages."""
    print("📊 Generating Optimization Impact Plot...")
    
    data = load_new_benchmark_results()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('#FAFBFC')
    ax.set_facecolor('#FFFFFF')
    
    width = 0.38
    
    baseline_cpi = []
    best_cpi = []
    bench_names = []
    
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        df = data[bench]
        bench_names.append(bench)
        
        baseline_mask = df['Benchmarks'].str.contains('baseline|cfg1', case=False, na=False)
        if baseline_mask.any():
            baseline_cpi.append(df.loc[baseline_mask, 'system.cpu.cpi'].values[0])
        else:
            baseline_cpi.append(df['system.cpu.cpi'].max())
        best_cpi.append(df['system.cpu.cpi'].min())
    
    x = np.arange(len(bench_names))
    
    # Shadow bars for depth
    ax.bar(x - width/2 + 0.02, baseline_cpi, width, color='#000000', alpha=0.05)
    ax.bar(x + width/2 + 0.02, best_cpi, width, color='#000000', alpha=0.05)
    
    # Baseline bars with gradient effect
    bars1 = ax.bar(x - width/2, baseline_cpi, width, label='Baseline (Default)', 
                  color='#95A5A6', alpha=0.9, edgecolor='white', linewidth=2.5,
                  zorder=3)
    
    # Best config bars with benchmark colors
    bars2 = ax.bar(x + width/2, best_cpi, width, label='Optimized', 
                  color=[BENCHMARK_COLORS[b] for b in bench_names], alpha=0.9, 
                  edgecolor='white', linewidth=2.5, zorder=3)
    
    # Add value labels on bars
    for bar, val in zip(bars1, baseline_cpi):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
               f'{val:.2f}', ha='center', va='bottom', fontsize=10, 
               fontweight='bold', color='#7F8C8D')
    
    for bar, val in zip(bars2, best_cpi):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
               f'{val:.2f}', ha='center', va='bottom', fontsize=10, 
               fontweight='bold', color='#2C3E50')
    
    ax.set_ylabel('CPI (Cycles Per Instruction)', fontsize=13, fontweight='bold', color='#2C3E50')
    ax.set_xlabel('Benchmark', fontsize=13, fontweight='bold', color='#2C3E50')
    ax.set_title('Optimization Impact: Baseline vs Best Configuration', 
                fontsize=16, fontweight='bold', color='#2C3E50', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace('spec', '').upper() for b in bench_names], 
                       fontsize=12, fontweight='bold')
    
    # Improvement badges - on TOP of bars, consistent green color
    for i, (base, best) in enumerate(zip(baseline_cpi, best_cpi)):
        if base > 0:
            improvement = (base - best) / base * 100
            # Position badge further above the tallest bar (baseline)
            ax.annotate(f'▼ {improvement:.1f}%', 
                       xy=(i, base + 1.0), 
                       ha='center', fontsize=11, fontweight='bold', color='white',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='#27AE60', 
                                edgecolor='white', linewidth=1.5, alpha=0.95))
    
    # Premium styling
    ax.yaxis.grid(True, linestyle='-', alpha=0.15, linewidth=1, color='#BDC3C7')
    ax.set_axisbelow(True)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color('#D0D0D0')
    
    ax.set_ylim(0, max(baseline_cpi) * 1.25)
    
    plt.tight_layout(pad=2.0)
    output_path = OUTPUT_DIR / 'optimization_impact.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#FAFBFC')
    plt.close()
    print(f"   ✅ Saved: {output_path}")



# =============================================================================
# PLOT 6: WORKLOAD CLASSIFICATION
# =============================================================================

def plot_workload_classification():
    """Plot workload classification based on L2 miss rate vs CPI improvement."""
    print("📊 Generating Workload Classification Plot...")
    
    data = load_new_benchmark_results()
    
    fig, ax = plt.subplots(figsize=(12, 9))
    fig.patch.set_facecolor('#FAFBFC')
    ax.set_facecolor('#FFFFFF')
    
    # Import Rectangle for background zones
    from matplotlib.patches import Rectangle
    
    l2_miss_values = []
    improvement_values = []
    
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        df = data[bench]
        
        baseline_mask = df['Benchmarks'].str.contains('baseline|cfg1', case=False, na=False)
        if baseline_mask.any():
            l2_miss = df.loc[baseline_mask, 'system.l2.overall_miss_rate::total'].values[0]
            baseline_cpi = df.loc[baseline_mask, 'system.cpu.cpi'].values[0]
        else:
            l2_miss = df['system.l2.overall_miss_rate::total'].iloc[0]
            baseline_cpi = df['system.cpu.cpi'].iloc[0]
        
        best_cpi = df['system.cpu.cpi'].min()
        improvement = (baseline_cpi - best_cpi) / baseline_cpi * 100
        
        print(f"   {bench}: L2 miss={l2_miss:.4f} ({l2_miss*100:.2f}%), improvement={improvement:.1f}%")
        
        l2_miss_values.append(l2_miss * 100)
        improvement_values.append(improvement)
        
        # Outer glow effect
        ax.scatter(l2_miss * 100, improvement, s=600, c=BENCHMARK_COLORS[bench], 
                  alpha=0.15, zorder=3)
        # Main point with premium styling
        ax.scatter(l2_miss * 100, improvement, s=400, c=BENCHMARK_COLORS[bench], 
                  edgecolors='white', linewidths=3, alpha=0.9, zorder=5)
        
        # Premium label
        ax.annotate(bench.replace('spec', '').upper(), 
                   (l2_miss * 100, improvement), 
                   xytext=(12, 8), textcoords='offset points', 
                   fontsize=11, fontweight='bold', color='#2C3E50',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            edgecolor=BENCHMARK_COLORS[bench], linewidth=1.5, alpha=0.9))
    
    # Trend line with confidence band effect
    if len(l2_miss_values) >= 2:
        z = np.polyfit(l2_miss_values, improvement_values, 1)
        p = np.poly1d(z)
        x_line = np.linspace(0, max(l2_miss_values) + 5, 100)
        y_line = p(x_line)
        
        # Confidence band - purple color to distinguish from memory-bound zone
        ax.fill_between(x_line, y_line - 5, y_line + 5, alpha=0.1, color='#8B5CF6')
        ax.plot(x_line, y_line, '-', color='#7C3AED', linewidth=3, alpha=0.8,
               label=f'Trend (ρ = {np.corrcoef(l2_miss_values, improvement_values)[0,1]:.2f})')
    
    ax.set_xlabel('Baseline L2 Miss Rate (%)', fontsize=14, fontweight='bold', color='#2C3E50')
    ax.set_ylabel('CPI Improvement (%)', fontsize=14, fontweight='bold', color='#2C3E50')
    ax.set_title('Workload Classification: Memory-Bound vs Compute-Bound', 
                fontsize=16, fontweight='bold', color='#2C3E50', pad=20)
    
    # Background zone rectangles (like plot_1.py style)
    max_imp = max(improvement_values) + 15
    # Compute-bound zone (left, green)
    compute_zone = Rectangle((0, 0), 50, max_imp, linewidth=0, 
                              facecolor='#10b981', alpha=0.12)
    ax.add_patch(compute_zone)
    
    # Memory-bound zone (right, red)
    memory_zone = Rectangle((50, 0), 60, max_imp, linewidth=0, 
                             facecolor='#ef4444', alpha=0.12)
    ax.add_patch(memory_zone)
    
    # Zone labels at top
    ax.text(25, max_imp - 3, 'COMPUTE-BOUND', fontsize=10, fontweight='bold', 
            ha='center', va='top', color='#059669', alpha=0.85)
    ax.text(80, max_imp - 3, 'MEMORY-BOUND', fontsize=10, fontweight='bold', 
            ha='center', va='top', color='#dc2626', alpha=0.85)
    
    # Divider line
    ax.axvline(x=50, color='#cbd5e1', linestyle='--', linewidth=1.5, alpha=0.7)
    
    # Premium legend and grid
    legend = ax.legend(loc='upper left', fontsize=11, framealpha=0.95,
                      edgecolor='#E0E0E0', fancybox=True, shadow=True)
    ax.grid(True, alpha=0.15, linestyle='-', linewidth=1, color='#BDC3C7')
    ax.set_axisbelow(True)
    
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color('#D0D0D0')
    
    ax.set_xlim(-5, max(l2_miss_values) + 15)
    ax.set_ylim(-5, max(improvement_values) + 15)
    
    plt.tight_layout(pad=2.0)
    output_path = OUTPUT_DIR / 'workload_classification.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#FAFBFC')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Generate all plots."""
    print("=" * 60)
    print("🎨 BENCHMARK RESULTS VISUALIZATION")
    print("=" * 60)
    print(f"📁 Results directory: {RESULTS_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print()
    
    # Verify results directory exists
    if not RESULTS_DIR.exists():
        print("❌ Error: Results directory not found!")
        return
    
    # Generate plots
    try:
        plot_cpi_progression_per_benchmark()
    except Exception as e:
        print(f"   ❌ Error generating CPI progression charts: {e}")
    
    try:
        plot_optimization_impact()
    except Exception as e:
        print(f"   ❌ Error generating optimization impact plot: {e}")
    
    try:
        plot_workload_classification()
    except Exception as e:
        print(f"   ❌ Error generating workload classification plot: {e}")
    
    print()
    print("=" * 60)
    print("✅ ALL PLOTS GENERATED SUCCESSFULLY!")
    print(f"📁 Find your plots in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
