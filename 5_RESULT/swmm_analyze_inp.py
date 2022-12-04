# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 16.06.2022
#
# Mit SWMM-Inputdatei ".inp" Diagramme erstellen.
# -----------------------------------------------------------------------------
"""swmm_analyze_inp"""
import os, sys, json
from swmm_api import read_inp_file 
import pandas as pd6
from mpl_toolkits.axisartist.parasite_axes import HostAxes, ParasiteAxes
import matplotlib, matplotlib.pyplot as plt, matplotlib.dates as mdates
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))

def print_dict(obj):
    print(json.dumps(obj, indent=4))

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
colors = {"v0":"dimgray", "v1":"tab:blue", "v2":"tab:orange", "v3":"tab:green", "v4":"tab:pink", "v5":"tab:blue", "v6":"tab:orange", "v7":"tab:green", "v8":"tab:pink", "v9":"tab:red", "v10":"tab:cyan", "v11":"tab:olive"}
linestyles = {"v0":"dashed","v5":"dashed","v6":"dashed","v7":"dashed","v8":"dashed"}
#simulations = ["v9", "v11", "v3", "v10"]
simulations = ["v1"]

dfs = {}
inps = []
for ii, simulation in enumerate(simulations):
    inp_file = os.path.join(swmm_folder, simulation, "swmm_template_5-yr_" + simulation + ".inp")
    inps.append(read_inp_file(inp_file))
    dfs[simulation] = inps[ii].SUBCATCHMENTS.frame

fig_size = (14,7)
## Plot 1 - Flächenverteilung
fig, ax1 = plt.subplots(constrained_layout = True, figsize = fig_size)
plot_label = 'Regen'
legends = []
for sim in simulations:
    legends.append("Simulation " + sim)       
fig_name = "flaechenverteilung.png"
fig_file = os.path.join(fig_folder, fig_name)
legend_loc = "upper right"
n_bins = 100
rc_range = [0, 1000]
for ii, simulation in enumerate(simulations):
    dist = dfs[simulation]["Area"].tolist()
    dist = [val*10000 for val in dist]
    if simulation in colors.keys():
        line_color = colors[simulation]
    else:
        line_color = None
    if simulation in linestyles.keys():
        line_style = linestyles[simulation]
    else:
        line_style='solid'
    ax1.hist(dist, bins = n_bins, range = rc_range, histtype="step", density=False, label = legends[ii], 
             linewidth = line_width, color = line_color, linestyle = line_style)

ax1.legend(loc=legend_loc)
ax1.grid(True)
ax1.set_ylabel("Häufigkeit")
ax1.set_xlabel("Fläche $[m^3]$")

plt.savefig(fig_file, dpi=600, format="png")
plt.show() 

