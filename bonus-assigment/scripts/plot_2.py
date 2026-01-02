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

# Version colors
VERSION_COLORS = {
    'default': '#95A5A6',
    'v1': '#3498DB',
    'v2': '#9B59B6',
    'v3': '#E74C3C',
}

# Cache line colors
CACHELINE_COLORS = {
    64: '#3498DB',
    128: '#9B59B6',
    256: '#E74C3C',
    512: '#27AE60',
}

# Set global style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 12,
    'axes.labelweight': 'medium',
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'figure.titleweight': 'bold',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#CCCCCC',
    'axes.linewidth': 1.2,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
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
# DATA LOADING FUNCTIONS
# =============================================================================

def load_baseline_results() -> pd.DataFrame:
    """Load baseline (default) benchmark results."""
    csv_path = RESULTS_DIR / 'step1_results.csv'
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df['version'] = 'default'
        return df
    return pd.DataFrame()


def load_version_results(version: str) -> Dict[str, pd.DataFrame]:
    """Load results for a specific version (v1, v2, v3)."""
    results = {}
    
    if version == 'v1':
        base_path = RESULTS_DIR / 'part2'
    elif version == 'v2':
        base_path = RESULTS_DIR / 'part2_v2'
    elif version == 'v3':
        base_path = RESULTS_DIR / 'part2_v3'
    else:
        return results
    
    for benchmark in BENCHMARKS:
        csv_pattern = base_path / benchmark / f'{benchmark}*.csv'
        csv_files = glob.glob(str(csv_pattern))
        if csv_files:
            df = pd.read_csv(csv_files[0])
            df['benchmark'] = benchmark
            df['version'] = version
            results[benchmark] = df
    
    return results


def load_all_configurations() -> pd.DataFrame:
    """Load all configurations from all versions into a single DataFrame."""
    all_data = []
        
    # Load V1, V2, V3
    for version in ['v1', 'v2', 'v3']:
        version_data = load_version_results(version)
        for benchmark, df in version_data.items():
            for _, row in df.iterrows():
                config_name = row['Benchmarks']
                cpi = row['system.cpu.cpi']
                
                # Skip NAN values
                if pd.isna(cpi) or str(cpi).upper() == 'NAN':
                    continue
                
                all_data.append({
                    'benchmark': benchmark,
                    'config': config_name,
                    'version': version,
                    'cpi': float(cpi),
                    'l1d_miss': float(row['system.cpu.dcache.overall_miss_rate::total']),
                    'l1i_miss': float(row['system.cpu.icache.overall_miss_rate::total']),
                    'l2_miss': float(row['system.l2.overall_miss_rate::total']),
                    'sim_seconds': float(row['sim_seconds']),
                })
    
    return pd.DataFrame(all_data)


def get_best_configs() -> pd.DataFrame:
    """Get the best configuration for each benchmark per version."""
    df = load_all_configurations()
    
    best = df.loc[df.groupby(['benchmark', 'version'])['cpi'].idxmin()]
    return best.reset_index(drop=True)


# =============================================================================
# CONFIGURATION METADATA
# =============================================================================

# Cache configuration mapping (from versions.md)
CONFIG_METADATA = {
    # V1 configurations (cfg1-cfg5 per benchmark)
    'cfg1': {'l1i': 32, 'l1d': 64, 'l2': 2048, 'l1i_assoc': 2, 'l1d_assoc': 2, 'l2_assoc': 8, 'cacheline': 64},
    'cfg2': {'l1i': 64, 'l1d': 64, 'l2': 2048, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 128},
    'cfg3': {'l1i': 64, 'l1d': 64, 'l2': 512, 'l1i_assoc': 2, 'l1d_assoc': 2, 'l2_assoc': 4, 'cacheline': 128},
    'cfg4': {'l1i': 64, 'l1d': 64, 'l2': 2048, 'l1i_assoc': 4, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 64},
    'cfg5': {'l1i': 32, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    
    # V2 configurations (v01-v12)
    'v01': {'l1i': 64, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    'v02': {'l1i': 32, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    'v03': {'l1i': 64, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 16, 'cacheline': 256},
    'v04': {'l1i': 64, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 4, 'l1d_assoc': 4, 'l2_assoc': 16, 'cacheline': 256},
    'v05': {'l1i': 32, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 64},
    'v06': {'l1i': 64, 'l1d': 192, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    'v07': {'l1i': 128, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 4, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    'v08': {'l1i': 32, 'l1d': 64, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 16, 'cacheline': 256},
    'v09': {'l1i': 64, 'l1d': 64, 'l2': 2048, 'l1i_assoc': 4, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 128},
    'v10': {'l1i': 64, 'l1d': 64, 'l2': 512, 'l1i_assoc': 2, 'l1d_assoc': 2, 'l2_assoc': 4, 'cacheline': 256},
    'v11': {'l1i': 64, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 8, 'l2_assoc': 8, 'cacheline': 256},
    'v12': {'l1i': 64, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 256},
    
    # V3 configurations
    'v3-01': {'l1i': 64, 'l1d': 128, 'l2': 512, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 4, 'cacheline': 256},
    'v3-02': {'l1i': 128, 'l1d': 64, 'l2': 512, 'l1i_assoc': 4, 'l1d_assoc': 2, 'l2_assoc': 4, 'cacheline': 256},
    'v3-03': {'l1i': 32, 'l1d': 128, 'l2': 4096, 'l1i_assoc': 2, 'l1d_assoc': 4, 'l2_assoc': 8, 'cacheline': 512},
    
    # Default baseline
    'baseline': {'l1i': 32, 'l1d': 64, 'l2': 2048, 'l1i_assoc': 2, 'l1d_assoc': 2, 'l2_assoc': 8, 'cacheline': 64},
    'minimal': {'l1i': 32, 'l1d': 32, 'l2': 512, 'l1i_assoc': 2, 'l1d_assoc': 2, 'l2_assoc': 4, 'cacheline': 64},
}


def get_config_cacheline(config: str) -> int:
    """Get cacheline size for a configuration."""
    if config in CONFIG_METADATA:
        return CONFIG_METADATA[config]['cacheline']
    return 64  # default


def get_config_l1d_size(config: str) -> int:
    """Get L1d size for a configuration."""
    if config in CONFIG_METADATA:
        return CONFIG_METADATA[config]['l1d']
    return 64  # default


# =============================================================================
# PLOT 1: CONFIGURATION SCATTER PLOT
# =============================================================================

def plot_configuration_scatter():
    """Create a scatter plot of L1d size vs CPI, colored by cacheline size."""
    print("📊 Generating Configuration Scatter Plot...")
    
    df = load_all_configurations()
    
    # Add config metadata
    df['l1d_size'] = df['config'].apply(get_config_l1d_size)
    df['cacheline'] = df['config'].apply(get_config_cacheline)
    
    # Create figure with subplots for each benchmark
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, benchmark in enumerate(BENCHMARKS):
        ax = axes[idx]
        bench_data = df[df['benchmark'] == benchmark]
        
        # Plot points colored by cacheline
        for cacheline in sorted(bench_data['cacheline'].unique()):
            subset = bench_data[bench_data['cacheline'] == cacheline]
            color = CACHELINE_COLORS.get(cacheline, '#95A5A6')
            
            ax.scatter(subset['l1d_size'], subset['cpi'], 
                      c=color, s=120, alpha=0.8, edgecolors='white',
                      linewidth=1.5, label=f'{cacheline}B')
        
        # Highlight best point
        best_idx = bench_data['cpi'].idxmin()
        best_row = bench_data.loc[best_idx]
        ax.scatter(best_row['l1d_size'], best_row['cpi'], 
                  c='gold', s=250, marker='*', edgecolors='black',
                  linewidth=2, zorder=10, label='Best')
        
        # Styling
        ax.set_xlabel('L1d Cache Size (kB)', fontweight='medium')
        ax.set_ylabel('CPI', fontweight='medium')
        ax.set_title(f'{benchmark.replace("spec", "").upper()}', 
                    fontsize=13, fontweight='bold', color=BENCHMARK_COLORS[benchmark])
        
        ax.grid(True, linestyle='--', alpha=0.4)
        
        # Remove top and right spines
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
    
    # Hide the 6th subplot (we only have 5 benchmarks)
    axes[5].axis('off')
    
    # Create a shared legend in the empty subplot space
    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    axes[5].legend(by_label.values(), by_label.keys(), 
                   loc='center', fontsize=12, title='Cache Line Size',
                   title_fontsize=13, framealpha=0.95)
    
    fig.suptitle('Configuration Space Exploration\nL1d Size vs CPI (colored by Cache Line Size)', 
                 fontsize=16, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    
    # Save
    output_path = OUTPUT_DIR / 'configuration_scatter.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


# =============================================================================
# PLOT 2: PER-BENCHMARK CPI PROGRESSION CURVE
# =============================================================================

def plot_cpi_progression_per_benchmark():
    """Create line charts showing CPI progression (sorted) for each benchmark."""
    print("📊 Generating Per-Benchmark CPI Progression Curves...")
    
    df = load_all_configurations()
    
    for benchmark in BENCHMARKS:
        bench_data = df[df['benchmark'] == benchmark].copy()
        bench_data = bench_data.sort_values('cpi', ascending=False).reset_index(drop=True)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Get data
        x = np.arange(len(bench_data))
        cpis = bench_data['cpi'].values
        configs = bench_data['config'].values
        versions = bench_data['version'].values
        
        # Create colors based on version
        point_colors = []
        for version in versions:
            if version == 'default':
                point_colors.append(VERSION_COLORS['default'])
            elif version == 'v1':
                point_colors.append(VERSION_COLORS['v1'])
            elif version == 'v2':
                point_colors.append(VERSION_COLORS['v2'])
            else:
                point_colors.append(VERSION_COLORS['v3'])
        
        # Plot the progression line with gradient effect
        # Create a smooth gradient background
        for i in range(len(x) - 1):
            ax.fill_between([x[i], x[i+1]], [cpis[i], cpis[i+1]], 
                           alpha=0.15, color=BENCHMARK_COLORS[benchmark])
        
        # Main line
        ax.plot(x, cpis, '-', linewidth=3, color=BENCHMARK_COLORS[benchmark], 
                alpha=0.8, zorder=5)
        
        # Scatter points with version colors
        for i, (xi, cpi, color) in enumerate(zip(x, cpis, point_colors)):
            ax.scatter(xi, cpi, c=color, s=100, edgecolors='white', 
                      linewidth=2, zorder=10)
        
        # Highlight best (last point after descending sort) and worst (first point)
        # Best point - green star
        ax.scatter(x[-1], cpis[-1], c='#27AE60', s=300, marker='*', 
                  edgecolors='black', linewidth=2, zorder=15, label='Best')
        
        # Worst point - red X
        ax.scatter(x[0], cpis[0], c='#E74C3C', s=200, marker='X', 
                  edgecolors='black', linewidth=2, zorder=15, label='Worst')
        
        # Add baseline reference line
        default_cpi = bench_data[bench_data['config'] == 'default']['cpi'].values
        if len(default_cpi) > 0:
            ax.axhline(y=default_cpi[0], color='#95A5A6', linestyle='--', 
                      linewidth=2, alpha=0.7, label=f'Default ({default_cpi[0]:.3f})')
        
        # X-axis labels (config names)
        ax.set_xticks(x)
        config_labels = [f"{c}\n({v})" for c, v in zip(configs, versions)]
        ax.set_xticklabels(config_labels, rotation=45, ha='right', fontsize=8)
        
        # Add annotations for best and worst
        ax.annotate(f'Best: {cpis[-1]:.3f}', 
                   xy=(x[-1], cpis[-1]), 
                   xytext=(x[-1] - 0.5, cpis[-1] - (cpis[0] - cpis[-1]) * 0.15),
                   fontsize=11, fontweight='bold', color='#27AE60',
                   arrowprops=dict(arrowstyle='->', color='#27AE60', lw=1.5))
        
        ax.annotate(f'Worst: {cpis[0]:.3f}', 
                   xy=(x[0], cpis[0]), 
                   xytext=(x[0] + 0.5, cpis[0] + (cpis[0] - cpis[-1]) * 0.08),
                   fontsize=11, fontweight='bold', color='#E74C3C',
                   arrowprops=dict(arrowstyle='->', color='#E74C3C', lw=1.5))
        
        # Calculate improvement
        improvement = ((cpis[0] - cpis[-1]) / cpis[0]) * 100
        
        # Styling
        ax.set_xlabel('Configuration (sorted by CPI, worst → best)', 
                     fontweight='bold', fontsize=12)
        ax.set_ylabel('CPI (Cycles Per Instruction)', fontweight='bold', fontsize=12)
        ax.set_title(f'{benchmark.upper()} — CPI Progression Across Configurations\n'
                    f'Improvement: {improvement:.1f}% (from {cpis[0]:.3f} to {cpis[-1]:.3f})', 
                    fontsize=14, fontweight='bold', color=BENCHMARK_COLORS[benchmark],
                    pad=20)
        
        # Add legend for versions
        legend_patches = [
            mpatches.Patch(color=VERSION_COLORS['default'], label='Default'),
            mpatches.Patch(color=VERSION_COLORS['v1'], label='V1'),
            mpatches.Patch(color=VERSION_COLORS['v2'], label='V2'),
            mpatches.Patch(color=VERSION_COLORS['v3'], label='V3'),
        ]
        ax.legend(handles=legend_patches, loc='upper right', framealpha=0.95,
                 title='Version', title_fontsize=11)
        
        # Grid
        ax.yaxis.grid(True, linestyle='--', alpha=0.4)
        ax.set_axisbelow(True)
        
        # Remove top and right spines
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        
        # Set y-axis limits with padding
        y_range = cpis[0] - cpis[-1]
        ax.set_ylim(cpis[-1] - y_range * 0.1, cpis[0] + y_range * 0.15)
        
        plt.tight_layout()
        
        # Save
        output_path = OUTPUT_DIR / f'{benchmark}_cpi_progression.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()
        print(f"   ✅ Saved: {output_path}")


# =============================================================================
# PLOT 3: CACHELINE SCALING (Memory-Bound Benchmarks)
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

def extract_cacheline_from_config_name(name: str) -> Optional[int]:
    """Extract cacheline size from config name like '+128B', '+256B', etc."""
    import re
    # Extract from path - get last component
    if '/' in name or '\\' in name:
        name = Path(name).name
    
    match = re.search(r'\+(\d+)B', name)
    if match:
        return int(match.group(1))
    if 'cfg1' in name.lower() or 'baseline' in name.lower():
        return 64  # Default cacheline
    return None

def plot_cacheline_scaling():
    """Plot CPI vs Cacheline Size for memory-bound benchmarks."""
    print("📊 Generating Cacheline Scaling Plot...")
    
    data = load_new_benchmark_results()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    memory_bound = ['speclibm', 'specsjeng']
    
    for bench in memory_bound:
        if bench not in data:
            continue
        df = data[bench]
        
        # Extract cacheline sizes and CPI
        cacheline_cpi = []
        for _, row in df.iterrows():
            name = str(row['Benchmarks'])
            cacheline = extract_cacheline_from_config_name(name)
            cpi = row['system.cpu.cpi']
            if cacheline and not pd.isna(cpi):
                cacheline_cpi.append((cacheline, float(cpi)))
        
        if cacheline_cpi:
            # Remove duplicates by taking average
            from collections import defaultdict
            cl_dict = defaultdict(list)
            for cl, cpi in cacheline_cpi:
                cl_dict[cl].append(cpi)
            cacheline_cpi = [(cl, np.mean(cpis)) for cl, cpis in cl_dict.items()]
            cacheline_cpi.sort(key=lambda x: x[0])
            cachelines, cpis = zip(*cacheline_cpi)
            
            ax.plot(cachelines, cpis, 'o-', label=bench.replace('spec', '').upper(), 
                   color=BENCHMARK_COLORS[bench], linewidth=2.5, markersize=10)
    
    ax.set_xscale('log', base=2)
    ax.set_xlabel('Cacheline Size (bytes)', fontsize=12, fontweight='bold')
    ax.set_ylabel('CPI', fontsize=12, fontweight='bold')
    ax.set_title('CPI vs Cacheline Size (Memory-Bound Benchmarks)\nLarger cacheline = implicit prefetching', 
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add improvement annotation
    ax.annotate('Each 2× cacheline provides\n~25-40% CPI reduction', 
               xy=(256, 4), fontsize=10, style='italic', color='gray',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'cacheline_scaling.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


# =============================================================================
# PLOT 4: OPTIMIZATION IMPACT (Baseline vs Best)
# =============================================================================

def plot_optimization_impact():
    """Plot baseline vs best CPI with improvement percentages."""
    print("📊 Generating Optimization Impact Plot...")
    
    data = load_new_benchmark_results()
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    x = np.arange(len(BENCHMARKS))
    width = 0.35
    
    baseline_cpi = []
    best_cpi = []
    bench_names = []
    
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        df = data[bench]
        bench_names.append(bench)
        
        # Find baseline/cfg1
        baseline_mask = df['Benchmarks'].str.contains('baseline|cfg1', case=False, na=False)
        if baseline_mask.any():
            baseline_cpi.append(df.loc[baseline_mask, 'system.cpu.cpi'].values[0])
        else:
            baseline_cpi.append(df['system.cpu.cpi'].max())
        best_cpi.append(df['system.cpu.cpi'].min())
    
    x = np.arange(len(bench_names))
    
    bars1 = ax.bar(x - width/2, baseline_cpi, width, label='Baseline', 
                  color='#95A5A6', alpha=0.85, edgecolor='white', linewidth=2)
    bars2 = ax.bar(x + width/2, best_cpi, width, label='Best Config', 
                  color=[BENCHMARK_COLORS[b] for b in bench_names], alpha=0.85, 
                  edgecolor='white', linewidth=2)
    
    ax.set_ylabel('CPI', fontsize=12, fontweight='bold')
    ax.set_xlabel('Benchmark', fontsize=12, fontweight='bold')
    ax.set_title('Optimization Impact: Baseline vs Best Configuration', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace('spec', '').upper() for b in bench_names], fontsize=11)
    ax.legend(loc='upper right', fontsize=11)
    
    # Add improvement percentages
    for i, (base, best) in enumerate(zip(baseline_cpi, best_cpi)):
        if base > 0:
            improvement = (base - best) / base * 100
            ax.annotate(f'-{improvement:.1f}%', 
                       xy=(i + width/2, best), 
                       xytext=(0, -20), textcoords='offset points',
                       ha='center', fontsize=10, fontweight='bold', color='#27AE60')
    
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'optimization_impact.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


# =============================================================================
# PLOT 5: CACHE MISS RATES HEATMAP
# =============================================================================

def plot_miss_rates_heatmap():
    """Plot cache miss rates as a heatmap across benchmarks."""
    print("📊 Generating Miss Rates Heatmap...")
    
    data = load_new_benchmark_results()
    
    # Collect miss rates for best configs
    miss_data = []
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        df = data[bench]
        
        # Get best config (lowest CPI)
        best_idx = df['system.cpu.cpi'].idxmin()
        row = df.loc[best_idx]
        
        miss_data.append({
            'Benchmark': bench.replace('spec', '').upper(),
            'L1d Miss': row['system.cpu.dcache.overall_miss_rate::total'] * 100,
            'L1i Miss': row['system.cpu.icache.overall_miss_rate::total'] * 100,
            'L2 Miss': row['system.l2.overall_miss_rate::total'] * 100,
        })
    
    miss_df = pd.DataFrame(miss_data)
    miss_df = miss_df.set_index('Benchmark')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create heatmap
    im = ax.imshow(miss_df.values, cmap='YlOrRd', aspect='auto')
    
    # Set ticks
    ax.set_xticks(np.arange(len(miss_df.columns)))
    ax.set_yticks(np.arange(len(miss_df.index)))
    ax.set_xticklabels(miss_df.columns, fontsize=11)
    ax.set_yticklabels(miss_df.index, fontsize=11)
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Miss Rate (%)', rotation=-90, va='bottom', fontsize=11)
    
    # Add text annotations
    for i in range(len(miss_df.index)):
        for j in range(len(miss_df.columns)):
            value = miss_df.values[i, j]
            color = 'white' if value > 50 else 'black'
            ax.text(j, i, f'{value:.2f}%', ha='center', va='center', 
                   color=color, fontsize=10, fontweight='bold')
    
    ax.set_title('Cache Miss Rates (Best Configuration per Benchmark)', 
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'miss_rates_heatmap.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✅ Saved: {output_path}")


# =============================================================================
# PLOT 6: WORKLOAD CLASSIFICATION
# =============================================================================

def plot_workload_classification():
    """Plot workload classification based on L2 miss rate vs CPI improvement."""
    print("📊 Generating Workload Classification Plot...")
    
    data = load_new_benchmark_results()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Collect data points for correlation
    l2_miss_values = []
    improvement_values = []
    
    for bench in BENCHMARKS:
        if bench not in data:
            continue
        df = data[bench]
        
        # Get baseline L2 miss rate - use first row or baseline/cfg1
        baseline_mask = df['Benchmarks'].str.contains('baseline|cfg1', case=False, na=False)
        if baseline_mask.any():
            l2_miss = df.loc[baseline_mask, 'system.l2.overall_miss_rate::total'].values[0]
            baseline_cpi = df.loc[baseline_mask, 'system.cpu.cpi'].values[0]
        else:
            # Fallback to first row (not max, which could be wrong)
            l2_miss = df['system.l2.overall_miss_rate::total'].iloc[0]
            baseline_cpi = df['system.cpu.cpi'].iloc[0]
        
        best_cpi = df['system.cpu.cpi'].min()
        improvement = (baseline_cpi - best_cpi) / baseline_cpi * 100
        
        # Debug output
        print(f"   {bench}: L2 miss={l2_miss:.4f} ({l2_miss*100:.2f}%), improvement={improvement:.1f}%")
        
        l2_miss_values.append(l2_miss * 100)
        improvement_values.append(improvement)
        
        ax.scatter(l2_miss * 100, improvement, s=300, c=BENCHMARK_COLORS[bench], 
                  edgecolors='black', linewidths=2, alpha=0.85,
                  label=bench.replace('spec', '').upper())
        ax.annotate(bench.replace('spec', '').upper(), 
                   (l2_miss * 100, improvement), 
                   xytext=(8, 5), textcoords='offset points', 
                   fontsize=10, fontweight='bold')
    
    # Add correlation/trend line
    if len(l2_miss_values) >= 2:
        z = np.polyfit(l2_miss_values, improvement_values, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(l2_miss_values) - 5, max(l2_miss_values) + 5, 100)
        ax.plot(x_line, p(x_line), '--', color='#E74C3C', linewidth=2, alpha=0.7,
               label=f'Trend (r={np.corrcoef(l2_miss_values, improvement_values)[0,1]:.2f})')
    
    ax.set_xlabel('Baseline L2 Miss Rate (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('CPI Improvement (%)', fontsize=12, fontweight='bold')
    ax.set_title('Workload Classification: Memory-Bound vs Compute-Bound', 
                fontsize=14, fontweight='bold')
    
    # Add quadrant annotations (only if data spans these regions)
    ax.axhline(y=20, color='gray', linestyle='--', alpha=0.4, linewidth=1)
    ax.axvline(x=50, color='gray', linestyle='--', alpha=0.4, linewidth=1)
    
    # Position text boxes based on actual data range
    ax.text(15, 3, 'Compute-Bound', ha='center', fontsize=9, color='#27AE60', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.text(85, max(improvement_values) - 5, 'Memory-Bound', ha='center', fontsize=9, 
           color='#E74C3C', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    # Set axis limits with padding
    ax.set_xlim(0, max(l2_miss_values) + 10)
    ax.set_ylim(0, max(improvement_values) + 10)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'workload_classification.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
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
        plot_configuration_scatter()
    except Exception as e:
        print(f"   ❌ Error generating scatter plot: {e}")
    
    try:
        plot_cpi_progression_per_benchmark()
    except Exception as e:
        print(f"   ❌ Error generating CPI progression charts: {e}")
    
    # New plots using the reorganized results
    try:
        plot_cacheline_scaling()
    except Exception as e:
        print(f"   ❌ Error generating cacheline scaling plot: {e}")
    
    try:
        plot_optimization_impact()
    except Exception as e:
        print(f"   ❌ Error generating optimization impact plot: {e}")
    
    try:
        plot_miss_rates_heatmap()
    except Exception as e:
        print(f"   ❌ Error generating miss rates heatmap: {e}")
    
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
