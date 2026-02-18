#!/usr/bin/env python3
"""
Question 2: Baseline Performance Metrics Visualization
Creates charts for SPEC CPU2006 benchmark baseline analysis.
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Create output directory
output_dir = Path(__file__).parent.parent / "plots" / "task1"
output_dir.mkdir(parents=True, exist_ok=True)

# Baseline data from Question 2
benchmarks = ['bzip2', 'mcf', 'hmmer', 'sjeng', 'lbm']
sim_times = [0.0840, 0.0647, 0.0594, 0.5135, 0.1747]
cpi = [1.680, 1.294, 1.188, 10.271, 3.494]
l1d_miss = [1.48, 0.21, 0.16, 12.18, 6.10]
l1i_miss = [0.008, 2.36, 0.022, 0.002, 0.009]
l2_miss = [28.22, 5.51, 7.82, 99.99, 99.99]

# Color palette
colors = {
    'primary': '#2563eb',
    'secondary': '#7c3aed',
    'accent': '#059669',
    'warning': '#d97706',
    'danger': '#dc2626',
    'l1d': '#3b82f6',
    'l1i': '#8b5cf6',
    'l2': '#ef4444'
}

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titleweight'] = 'bold'

# =============================================================================
# Option 1: Dual Y-Axis Bar Chart (CPI + Sim Time)
# =============================================================================
fig, ax1 = plt.subplots(figsize=(12, 6))

x = np.arange(len(benchmarks))
width = 0.35

# CPI bars on left y-axis
bars1 = ax1.bar(x - width/2, cpi, width, label='CPI', color=colors['primary'], edgecolor='white', linewidth=1.5)
ax1.set_xlabel('Benchmark', fontsize=12, fontweight='bold')
ax1.set_ylabel('CPI (Cycles Per Instruction)', fontsize=12, fontweight='bold', color=colors['primary'])
ax1.tick_params(axis='y', labelcolor=colors['primary'])
ax1.set_xticks(x)
ax1.set_xticklabels(benchmarks)

# Add CPI value labels
for bar, val in zip(bars1, cpi):
    height = bar.get_height()
    ax1.annotate(f'{val:.2f}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontweight='bold', fontsize=10, color=colors['primary'])

# Sim time bars on right y-axis
ax2 = ax1.twinx()
bars2 = ax2.bar(x + width/2, sim_times, width, label='Sim Time', color=colors['secondary'], edgecolor='white', linewidth=1.5)
ax2.set_ylabel('Simulation Time (seconds)', fontsize=12, fontweight='bold', color=colors['secondary'])
ax2.tick_params(axis='y', labelcolor=colors['secondary'])

# Add sim time value labels
for bar, val in zip(bars2, sim_times):
    height = bar.get_height()
    ax2.annotate(f'{val:.3f}s',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontweight='bold', fontsize=10, color=colors['secondary'])

# Synchronize Y-axis scales so grid lines align
cpi_max = max(cpi) * 1.15
sim_max = max(sim_times) * 1.15
ax1.set_ylim(0, cpi_max)
ax2.set_ylim(0, sim_max)

# Add ideal CPI reference line
ideal_line = ax1.axhline(y=1, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label='Ideal CPI = 1')

# Sync tick locations
num_ticks = 6
cpi_ticks = np.linspace(0, cpi_max, num_ticks)
sim_ticks = np.linspace(0, sim_max, num_ticks)
ax1.set_yticks(cpi_ticks)
ax2.set_yticks(sim_ticks)
ax1.set_yticklabels([f'{t:.1f}' for t in cpi_ticks])
ax2.set_yticklabels([f'{t:.2f}s' for t in sim_ticks])

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

ax1.set_title('CPI vs Simulation Time — Dual Axis View', fontsize=14, fontweight='bold', pad=15)

ax1.grid(False)
ax2.grid(False)

plt.tight_layout()
plt.savefig(output_dir / 'cpi_simtime_dual_axis.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"✓ Created: cpi_simtime_dual_axis.png")


# =============================================================================
# Figure 3: Cache Miss Heatmap
# =============================================================================
fig, ax = plt.subplots(figsize=(8, 6))

miss_data = np.array([l1i_miss, l1d_miss, l2_miss]).T
cache_levels = ['L1 Instruction', 'L1 Data', 'L2']

import matplotlib.colors as mcolors
norm = mcolors.LogNorm(vmin=0.001, vmax=100)

im = ax.imshow(miss_data, cmap='RdYlGn_r', aspect='auto', norm=norm)

cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('Miss Rate (%)', fontsize=11, fontweight='bold')

ax.set_xticks(np.arange(len(cache_levels)))
ax.set_yticks(np.arange(len(benchmarks)))
ax.set_xticklabels(cache_levels, fontsize=11)
ax.set_yticklabels(benchmarks, fontsize=11)

for i in range(len(benchmarks)):
    for j in range(len(cache_levels)):
        val = miss_data[i, j]
        text_color = 'white' if val > 10 else 'black'
        ax.text(j, i, f'{val:.2f}%', ha='center', va='center', 
                color=text_color, fontsize=10, fontweight='bold')

ax.set_title('Cache Miss Rate Heatmap', fontsize=14, fontweight='bold', pad=15)
ax.grid(False)

for i in range(len(benchmarks) + 1):
    ax.axhline(y=i - 0.5, color='white', linewidth=2)
for j in range(len(cache_levels) + 1):
    ax.axvline(x=j - 0.5, color='white', linewidth=2)

plt.tight_layout()
plt.savefig(output_dir / 'cache_miss_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"✓ Created: cache_miss_heatmap.png")

# =============================================================================
# Question 3: Frequency Scaling Visualizations
# =============================================================================

cpi_1ghz = [1.61, 1.27, 1.19, 7.04, 2.62]
cpi_2ghz = [1.68, 1.29, 1.19, 10.27, 3.49]
cpi_4ghz = [1.83, 1.33, 1.19, 16.70, 5.31]

sim_1ghz = [0.1610, 0.1273, 0.1185, 0.7041, 0.2623]
sim_4ghz = [0.0457, 0.0333, 0.0298, 0.4175, 0.1327]

speedup_1_to_4 = [s1/s4 for s1, s4 in zip(sim_1ghz, sim_4ghz)]
scaling_efficiency = [s/4.0 * 100 for s in speedup_1_to_4]

correlation = np.corrcoef(l2_miss, scaling_efficiency)[0, 1]
print(f"Correlation between L2 Miss Rate and Scaling Efficiency: {correlation:.4f}")

# =============================================================================
# Figure 4: Scaling Efficiency vs L2 Miss Rate (Premium Light Theme)
# =============================================================================
fig, ax = plt.subplots(figsize=(12, 8))

# Clean light background
ax.set_facecolor('#fafbfc')
fig.patch.set_facecolor('white')

from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap

# Compute-bound zone (left, visible green)
compute_zone = Rectangle((0, 35), 35, 75, linewidth=0, 
                          facecolor='#10b981', alpha=0.15)
ax.add_patch(compute_zone)

# Memory-bound zone (right, visible red)
memory_zone = Rectangle((35, 35), 80, 75, linewidth=0, 
                         facecolor='#ef4444', alpha=0.15)
ax.add_patch(memory_zone)

# Zone labels
ax.text(17.5, 107, 'COMPUTE-BOUND', fontsize=9, fontweight='bold', 
        ha='center', va='bottom', color='#059669', alpha=0.9)
ax.text(70, 107, 'MEMORY-BOUND', fontsize=9, fontweight='bold', 
        ha='center', va='bottom', color='#dc2626', alpha=0.9)

# Vertical divider
ax.axvline(x=35, color='#cbd5e1', linestyle='--', linewidth=1.5, alpha=0.7)

# Bubble sizes
bubble_sizes = [c * 45 for c in cpi_4ghz]

# Custom colormap (red to green)
custom_cmap = LinearSegmentedColormap.from_list('efficiency', 
    ['#dc2626', '#f59e0b', '#22c55e', '#059669'], N=256)

# Glow effect (shadow layer)
ax.scatter(l2_miss, scaling_efficiency, s=[s * 1.6 for s in bubble_sizes], 
           c=scaling_efficiency, cmap=custom_cmap, alpha=0.12, 
           vmin=40, vmax=100, zorder=1)

# Main bubbles with white edge
scatter = ax.scatter(l2_miss, scaling_efficiency, s=bubble_sizes, 
                     c=scaling_efficiency, cmap=custom_cmap, alpha=0.9, 
                     edgecolors='white', linewidths=2.5, vmin=40, vmax=100, zorder=2)

# Benchmark labels
label_configs = {
    'bzip2': {'offset': (14, 10), 'ha': 'left'},
    'mcf': {'offset': (-12, -12), 'ha': 'right'},
    'hmmer': {'offset': (12, 12), 'ha': 'left'},
    'sjeng': {'offset': (-22, -12), 'ha': 'right'},
    'lbm': {'offset': (-14, 14), 'ha': 'right'}
}

for i, benchmark in enumerate(benchmarks):
    config = label_configs.get(benchmark, {'offset': (8, 8), 'ha': 'left'})
    eff_val = scaling_efficiency[i]
    
    # Color based on efficiency
    if eff_val >= 85:
        label_color = '#047857'
        bg_color = '#d1fae5'
        edge_color = '#10b981'
    elif eff_val >= 60:
        label_color = '#b45309'
        bg_color = '#fef3c7'
        edge_color = '#f59e0b'
    else:
        label_color = '#b91c1c'
        bg_color = '#fee2e2'
        edge_color = '#ef4444'
    
    ax.annotate(f'{benchmark}\n{eff_val:.0f}%', (l2_miss[i], scaling_efficiency[i]),
                xytext=config['offset'], textcoords='offset points',
                fontsize=10, fontweight='bold', ha=config['ha'], va='center',
                color=label_color,
                bbox=dict(boxstyle='round,pad=0.4', facecolor=bg_color, 
                         alpha=0.95, edgecolor=edge_color, linewidth=1.5),
                zorder=3)

# Trend line
z = np.polyfit(l2_miss, scaling_efficiency, 1)
p = np.poly1d(z)
x_line = np.linspace(-5, 115, 200)
y_line = p(x_line)

# Trend line with shadow
ax.plot(x_line, y_line, '-', color='#8b5cf6', linewidth=5, alpha=0.15, zorder=0)
ax.plot(x_line, y_line, '--', color='#7c3aed', linewidth=2.5, alpha=0.85, 
        label=f'Trend (ρ = {correlation:.2f})', zorder=1)

# Ideal scaling line
ax.axhline(y=100, color='#0ea5e9', linestyle='--', linewidth=2, alpha=0.7, 
           label='Ideal 100% Scaling', zorder=1)

# Colorbar
cbar = plt.colorbar(scatter, ax=ax, shrink=0.75, pad=0.02)
cbar.set_label('Scaling Efficiency (%)', fontsize=11, fontweight='bold')
cbar.outline.set_linewidth(0.5)

# Axis labels
ax.set_xlabel('L2 Cache Miss Rate (%)', fontsize=13, fontweight='bold', labelpad=12)
ax.set_ylabel('Scaling Efficiency (1GHz → 4GHz)', fontsize=13, fontweight='bold', labelpad=12)
ax.set_title('Frequency Scaling Efficiency vs Cache Miss Rate', 
             fontsize=16, fontweight='bold', pad=20, color='#1e293b')

# Subtitle (moved down slightly)
ax.text(0.5, 1.015, f'Strong negative correlation (ρ = {correlation:.2f}) · Bubble size ∝ CPI at 4 GHz',
        transform=ax.transAxes, fontsize=10, ha='center', va='top', 
        color='#64748b', fontstyle='italic')

ax.set_xlim(-5, 115)
ax.set_ylim(35, 112)

# Styling
ax.tick_params(axis='both', labelsize=10, colors='#334155')
ax.spines['bottom'].set_color('#e2e8f0')
ax.spines['left'].set_color('#e2e8f0')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Subtle grid
ax.grid(True, linestyle='--', alpha=0.3, color='#cbd5e1')

# Legend
legend = ax.legend(loc='lower left', fontsize=10, framealpha=0.95, 
                   facecolor='white', edgecolor='#e2e8f0')

plt.tight_layout()
plt.savefig(output_dir / 'scaling_vs_cache_miss.png', dpi=200, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.close()
print(f"✓ Created: scaling_vs_cache_miss.png")

# =============================================================================
# Question 4: Memory Technology Impact - Improvement vs Effective DRAM Miss Rate
# =============================================================================

# Data: DDR3_1600 (Baseline) vs DDR3_2133 (Upgraded) - sorted by effective miss rate
benchmarks_mem = ['hmmer', 'mcf', 'bzip2', 'lbm', 'sjeng']
cpi_1600 = [1.1879, 1.2940, 1.6800, 3.4938, 10.2705]
cpi_2133 = [1.1877, 1.2909, 1.6719, 3.4306, 9.8626]
l2_miss_mem = [7.82, 5.51, 28.22, 99.99, 99.99]
l1d_miss_mem = [0.16, 0.21, 1.48, 6.10, 12.18]

# Combined metric: effective DRAM miss rate = L1d_miss × L2_miss / 100
# This captures the fraction of instructions that actually reach main memory
effective_miss = [l1d * l2 / 100 for l1d, l2 in zip(l1d_miss_mem, l2_miss_mem)]

# Calculate improvements (sim time improvement = CPI improvement since instructions are fixed)
improvement = [(old - new) / old * 100 for old, new in zip(cpi_1600, cpi_2133)]

fig, ax = plt.subplots(figsize=(12, 8))

ax.set_facecolor('#fafbfc')
fig.patch.set_facecolor('white')

# Use log scale for x-axis to spread out the compute-bound benchmarks
ax.set_xscale('log')

# Background zones (in log space: 0.005–0.5 compute, 0.5–15 memory)
compute_zone = Rectangle((0.005, -0.5), 0.495, 5.8, linewidth=0, 
                          facecolor=colors['accent'], alpha=0.12)
ax.add_patch(compute_zone)
memory_zone = Rectangle((0.5, -0.5), 14.5, 5.8, linewidth=0, 
                         facecolor=colors['danger'], alpha=0.12)
ax.add_patch(memory_zone)

# Zone labels
ax.text(0.07, 4.3, 'COMPUTE-BOUND', fontsize=10, fontweight='bold', 
        ha='center', color=colors['accent'], alpha=0.8)
ax.text(4.0, 4.3, 'MEMORY-BOUND', fontsize=10, fontweight='bold', 
        ha='center', color=colors['danger'], alpha=0.8)

# Divider line
ax.axvline(x=0.5, color='#cbd5e1', linestyle='--', linewidth=1.5, alpha=0.7)

# Custom colormap
custom_cmap = LinearSegmentedColormap.from_list('improvement', 
    ['#94a3b8', '#f59e0b', '#ef4444', '#dc2626'], N=256)

# Fixed bubble size
bubble_sizes = [400] * len(benchmarks_mem)

# Shadow layer
ax.scatter(effective_miss, improvement, s=[s * 1.5 for s in bubble_sizes], 
           c=improvement, cmap=custom_cmap, alpha=0.12, 
           vmin=0, vmax=4.5, zorder=1)

# Main bubbles
scatter = ax.scatter(effective_miss, improvement, s=bubble_sizes, 
                     c=improvement, cmap=custom_cmap, alpha=0.9, 
                     edgecolors='white', linewidths=2.5, 
                     vmin=0, vmax=4.5, zorder=2)

# Label configurations adjusted for log-scale x-axis
label_configs_mem = {
    'hmmer': {'offset': (15, -12), 'ha': 'left'},
    'mcf': {'offset': (-15, 14), 'ha': 'right'},
    'bzip2': {'offset': (-18, 16), 'ha': 'right'},
    'lbm': {'offset': (-24, 17), 'ha': 'right'},
    'sjeng': {'offset': (-28, -16), 'ha': 'right'}
}

for i, benchmark in enumerate(benchmarks_mem):
    config = label_configs_mem.get(benchmark, {'offset': (10, 10), 'ha': 'left'})
    imp_val = improvement[i]
    
    # Color based on improvement
    if imp_val < 0.3:
        label_color = '#047857'
        bg_color = '#d1fae5'
        edge_color = '#10b981'
    elif imp_val < 1.5:
        label_color = '#b45309'
        bg_color = '#fef3c7'
        edge_color = '#f59e0b'
    else:
        label_color = '#b91c1c'
        bg_color = '#fee2e2'
        edge_color = '#ef4444'
    
    # Annotation: benchmark name and improvement
    ax.annotate(f'{benchmark}\n{imp_val:.2f}%', 
                (effective_miss[i], improvement[i]),
                xytext=config['offset'], textcoords='offset points',
                fontsize=10, fontweight='bold', ha=config['ha'], va='center',
                multialignment='center',
                color=label_color,
                bbox=dict(boxstyle='round,pad=0.4', facecolor=bg_color, 
                         alpha=0.95, edgecolor=edge_color, linewidth=1.5),
                zorder=3)

# Trend line with R² value (fit in linear space, curves naturally on log axis)
z = np.polyfit(effective_miss, improvement, 1)
p = np.poly1d(z)
x_line = np.logspace(np.log10(0.005), np.log10(20), 200)
y_line = p(x_line)

# R² calculation (linear space)
correlation_mem = np.corrcoef(effective_miss, improvement)[0, 1]
r_squared = correlation_mem ** 2

# Trend line
ax.plot(x_line, y_line, '-', color='#8b5cf6', linewidth=4, alpha=0.15, zorder=0)
ax.plot(x_line, y_line, '--', color='#7c3aed', linewidth=2.5, alpha=0.85, 
        label=f'Trend (R² = {r_squared:.2f}, ρ = {correlation_mem:.2f})', zorder=1)



# Labels and title
ax.set_xlabel('Effective DRAM Miss Rate  (L1d Miss × L2 Miss / 100)', fontsize=13, fontweight='bold', labelpad=12)
ax.set_ylabel('Simulation Time Improvement from Memory Upgrade (%)', fontsize=13, fontweight='bold', labelpad=12)
ax.set_title('Memory Upgrade Benefit: DDR3_1600 → DDR3_2133 (+33% Bandwidth)', 
             fontsize=16, fontweight='bold', pad=30, color='#1e293b')

# Subtitle
ax.text(0.5, 1.03, f'Strong correlation (ρ = {correlation_mem:.2f}) · X-axis combines L1d & L2 miss rates',
        transform=ax.transAxes, fontsize=10, ha='center', va='top', 
        color='#64748b', fontstyle='italic')

ax.set_xlim(0.005, 20)
ax.set_ylim(-0.3, 4.8)

# Styling
ax.tick_params(axis='both', labelsize=10, colors='#334155')
ax.spines['bottom'].set_color('#e2e8f0')
ax.spines['left'].set_color('#e2e8f0')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, linestyle='--', alpha=0.3, color='#cbd5e1')

# Legend
ax.legend(loc='upper left', fontsize=10, framealpha=0.95, 
          facecolor='white', edgecolor='#e2e8f0')

plt.tight_layout()
plt.savefig(output_dir / 'memory_improvement_vs_effective_miss.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"✓ Created: memory_improvement_vs_effective_miss.png")

print(f"\n✅ All plots saved to: {output_dir.resolve()}")
