# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 16.06.2022
#
# Die SWMM-Ergebnisdateien ".rpt" wir zu Excel-Dateien konvertiert, die anschliessend 
# in ArcGIS Pro zu den GIS-Datensätzen (node, link, subcatchment) angehängt werden können, 
# um die Ergebnisse in Karten zu präsentieren.
# -----------------------------------------------------------------------------
"""swmm_rpt2excel"""
import os, sys, json
from swmm_api import read_rpt_file 
import matplotlib.pyplot as plt, matplotlib.dates as mdates
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))

def print_dict(obj):
    print(json.dumps(obj, indent=4))
    
# Pfad zu Ordner wo sich die Ordner der unterschiedlichen SWMM-Simulationsergebnissen befinden
swmm_folder = r'C:\pygisswmm\4_GISSWMM2SWMM' 

all_simulations = ["v1"]

# Liste mit SWMM rpt-Dateien
rpts = []
for ii, simulation in enumerate(all_simulations):
    dataframe = {}
    rpt_file = os.path.join(swmm_folder, simulation, "swmm_template_5-yr_" + simulation + ".rpt")
    rpts.append(read_rpt_file(rpt_file))
    dataframe["link_flow_summary"] = rpts[ii].link_flow_summary
    dataframe["node_depth_summary"] = rpts[ii].node_depth_summary
    #dataframe["node_flooding_summary"] = rpts[ii].node_flooding_summary
    #dataframe["node_inflow_summary"] = rpts[ii].node_inflow_summary
    dataframe["subcatchment_runoff_summary"] = rpts[ii].subcatchment_runoff_summary
    for key, df in dataframe.items():
        try:
            out_file = os.path.join(swmm_folder, simulation, "swmm_template_5-yr_" + simulation + "_" + key + ".xlsx")
            df.to_excel(out_file, key)
        except:
            continue


