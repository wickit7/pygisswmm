# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 16.06.2022
#
# Mit SWMM-Ergebnisdatei «.rpt» Diagramme erstellen.
# -----------------------------------------------------------------------------
"""swmm_analyze_rpt"""
import os, sys
from swmm_api import read_rpt_file 
import matplotlib, matplotlib.pyplot as plt, matplotlib.dates as mdates
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))

# matplotlibe Schriftgrösse erhöhen
matplotlib.rcParams.update({'font.size': 16})

# Pfad zu Ordner wo sich die Ordner der unterschiedlichen SWMM-Simulationsergebnissen befinden
swmm_folder = r'C:\pygisswmm\4_GISSWMM2SWMM' 
# Pfad zu Ordner in welchem Plots gespeichert werden
fig_folder = r'C:\pygisswmm\5_RESULT\figures'

## Plot Options
line_width = 2.7
marker_size = 6
# Dictionaries mit Farbe und Linnienart für jede Simulation
colors = {"v0":"dimgray", "v1":"tab:blue", "v2":"tab:orange", "v3":"tab:green", "v4":"tab:pink", "v5":"tab:blue", 
          "v6":"tab:orange", "v7":"tab:green", "v8":"tab:pink", "v9":"tab:red", "v10":"tab:cyan", "v11":"tab:olive"}
linestyles = {"v0":"dashed","v5":"dashed","v6":"dashed","v7":"dashed","v8":"dashed"}

simulations = ["v1"]


fig_size_1 = (14,7)
# Dictionary mit Simulationen und zugehörige runoff summary
dfs = {}
# Liste mit SWMM rpt-Dateien
rpts_5yr = []
for ii, simulation in enumerate(simulations):
    rpt_file = os.path.join(swmm_folder, simulation, "swmm_template_5-yr_" + simulation + ".rpt")
    rpts_5yr.append(read_rpt_file(rpt_file))
    dfs[simulation] = rpts_5yr[ii].subcatchment_runoff_summary

## Abflussbeiwert 5 yr.
fig, ax1 = plt.subplots(constrained_layout=True, figsize=fig_size_1)
plot_label = 'Regeneregnis mit Jährlichkeit = 5 J.'
legends = []
for sim in simulations:
    legends.append("Simulation " + sim)
fig_name = "abflussbeiwert_5yr.png"
fig_file = os.path.join(fig_folder, fig_name)
legend_loc = "upper left"
n_bins = 30
rc_range = [0.9, 1]
for ii, simulation in enumerate(simulations):
    dist = dfs[simulation]["Runoff_Coeff"].tolist()
    if simulation in colors.keys():
        line_color = colors[simulation]
    else:
        line_color = None
    if simulation in linestyles.keys():
        line_style = linestyles[simulation]
    else:
        line_style='solid'
    ax1.hist(dist, bins = n_bins, range = rc_range, histtype="step", density=True, label = legends[ii], 
             linewidth = line_width, color = line_color, linestyle = line_style)

ax1.text(0.92, 204, plot_label, bbox={'facecolor': 'white', 'edgecolor':'grey', 'alpha': 0.5, 'pad': 5})
ax1.legend(loc=legend_loc)
ax1.grid(True)
ax1.set_ylabel("Häufigkeit (normalisiert)")
ax1.set_xlabel("Abflussbeiwert")

plt.savefig(fig_file, dpi=600, format="png")
plt.show() 


