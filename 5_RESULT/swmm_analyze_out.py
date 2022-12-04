# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 16.06.2022
#
# Mit SWMM-Ergebnisdatei ".out" Diagramme erstellen.
# -----------------------------------------------------------------------------
"""swmm_analyze_out"""
import os, sys, datetime
from swmm_api import read_out_file 
from swmm_api.output_file import VARIABLES, OBJECTS
from mpl_toolkits.axisartist.parasite_axes import HostAxes, ParasiteAxes
import matplotlib, matplotlib.pyplot as plt, matplotlib.dates as mdates
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))

## Funktionen für die Berechnung der Deckelkote
def plot_swmm_variable(outs, node_name, smmw_variable, simulations, legends, colors = None, linestyles = None, line_width = 2.7, node_label = None,
                       fig_size=(14,7), rain_label = "Regen", xmin=None, xmax=None, ymin=None, ymax=None, legend_loc="lower left", legend_bbox=None):
    """Hilfsfunktion zum plotten
    """   
    fig, ax1 = plt.subplots(constrained_layout=True, figsize=fig_size)

    for ii, simulation in enumerate(simulations):
        inflow = outs[simulation].get_part(OBJECTS.NODE, node_name, smmw_variable).to_frame()
        x_values = inflow.index
        y_values = inflow.values
        rain = outs[simulation].get_part(OBJECTS.SYSTEM)['rainfall']
        a_values = rain.index
        b_values = rain.values
        if simulation in colors.keys():
            line_color = colors[simulation]
        else:
            line_color = None
        if simulation in linestyles.keys():
            line_style = linestyles[simulation]
        else:
            line_style='solid'
        ax1.plot(x_values, y_values, label = legends[ii], linewidth = line_width, color = line_color, linestyle = line_style)
        ax1.set_ylabel("Abfluss $[m^3/s]$")
        ax1.set_xlabel("Zeit [dd hh:mm]")
        ax1.legend(loc=legend_loc, bbox_to_anchor=legend_bbox)
        ax1.set_title(node_label)
        ax1.grid(True)
        ax1.tick_params(axis='x', labelrotation = 25)
        ax1.set_xlim([xmin, xmax])
        ax1.set_xlim([ymin, ymax])
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2 = ax1.twinx()
    ax2.plot(a_values, b_values, linewidth = line_width, color='grey', label = rain_label, linestyle='dotted')
    ax2.set_ylabel("Regenintensität [mm/h]")
    ax2.legend(loc='upper right')

    plt.savefig(fig_file, dpi=600, format="png")
    plt.show() 

def plot_rain(outs, line_width = 2.7, fig_size=(14,7), rain_label = "Regen", xmin=None, xmax=None, ymin=None, ymax=None,
             legend_loc="lower left", legend_bbox=None):
    """Hilfsfunktion zum plotten
    """   
    fig, ax1 = plt.subplots(constrained_layout=True, figsize=fig_size)

    rain = outs[simulation].get_part(OBJECTS.SYSTEM)['rainfall']
    a_values = rain.index
    b_values = rain.values
 
    ax1.plot(a_values, b_values, linewidth = line_width, color='blue', label = rain_label, linestyle='dotted')
    ax1.set_ylabel("Regenintensität [mm/h]")
    ax1.set_xlabel("Zeit [dd hh:mm]")
    ax1.legend(loc=legend_loc, bbox_to_anchor=legend_bbox)
    ax1.grid(True)
    ax1.tick_params(axis='x', labelrotation = 25)
    ax1.set_xlim([xmin, xmax])
    ax1.set_xlim([ymin, ymax])
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    plt.savefig(fig_file, dpi=600, format="png")
    plt.show() 


if __name__ == "__main__":
    # matplotlibe Schriftgrösse erhöhen
    matplotlib.rcParams.update({'font.size': 16})
    ## Pfad zu Ordner wo sich die Ordner der unterschiedlichen SWMM-Simulationsergebnissen befinden
    swmm_folder = r'C:\pygisswmm\4_GISSWMM2SWMM' 
    # Pfad zu Ordner in welchem Plots gespeichert werden
    fig_folder = r'C:\pygisswmm\5_RESULT\figures'

    # Durchgeführte Simulationen
    all_simulations = [ "v1"]

    # Dictionary mit allen SWMM out-Dateien erstellen    
    prefix_5yr = "swmm_template_5-yr_"
    outs_5yr =  {}
    for ii, simulation in enumerate(all_simulations):
        out_file = os.path.join(swmm_folder, simulation, prefix_5yr + simulation + ".out")
        outs_5yr[simulation] = read_out_file(out_file)

    ## Plot Options
    line_width = 2.7
    marker_size = 6
    # Dictionaries mit Farbe und Linnienart für jede Simulation
    colors = {"v0":"dimgray", "v1":"tab:blue", "v2":"tab:orange", "v3":"tab:green", "v4":"tab:pink", "v5":"tab:blue", 
              "v6":"tab:orange", "v7":"tab:green", "v8":"tab:pink", "v9":"tab:red", "v10":"tab:cyan", "v11":"tab:olive"}
    linestyles = {"v0":"dashed","v5":"dashed","v6":"dashed","v7":"dashed","v8":"dashed"}

    ## Plot Regen
    fig_size_1 = (14,7)
    rain_label = 'Starkregen, Jährlichkeit = 5 J.'
    fig_name = "starkregen.png" 
    x_min = datetime.datetime(2006, 6, 17, 15, 40, 0)
    x_max = datetime.datetime(2006, 6, 17, 17, 0, 0)
    legend_loc = "upper right"

    fig_file = os.path.join(fig_folder, fig_name)
    plot_rain(outs_5yr, line_width = 4, fig_size = fig_size_1, rain_label = rain_label, 
              xmin = x_min, xmax = x_max, legend_loc = legend_loc)

    # Abfluss Auslaufschacht
    fig_size = (14,7)
    simulations = ["v1"]
    legends = []
    for sim in simulations:
        legends.append("Simulation " + sim)
    node_name = '{A5D5075A-8BCE-47C7-9767-62272B1BE103}'              
    node_label = 'Auslaufschacht'
    rain_label = 'Regen'
    fig_name = "Abfluss_Auslaufschacht.png" 
    smmw_variable = VARIABLES.NODE.TOTAL_INFLOW    
    x_min = datetime.datetime(2006, 6, 17, 15, 40, 0)
    x_max = datetime.datetime(2006, 6, 17, 17, 0, 0)
    legend_loc = "lower left"
    #legend_bbox=(0.8, 0.998)
    legend_bbox = None

    fig_file = os.path.join(fig_folder, fig_name)
    plot_swmm_variable(outs_5yr, node_name, smmw_variable, simulations, legends, colors = colors, linestyles = linestyles,
                       line_width = line_width, node_label = node_label, fig_size = fig_size, rain_label = rain_label, 
                       xmin = x_min, xmax = x_max, legend_loc = legend_loc, legend_bbox = legend_bbox)

    

