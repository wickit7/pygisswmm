# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 25.03.2022
#
# GIS-Daten in die Template SWMM-Eingabedatei (.inp) importieren:
# Für die Simulation eines Modells benötigt es eine SWMM-Input-Datei. Dabei handelt es sich um ein strukturiertes 
# Textformat (.inp) mit allen Angaben (Berechnungsoptionen, Niederschlagsganglinie, Knoten, Haltungen, Teileinzugsgebiete u. a.) 
# die für die Simulation benötigt werden. Es wird eine SWMM-Input-Datei benötigt, in welcher Berechnungsoptionen und die 
# Niederschlagsganglinie enthalten ist. Das Skript importiert die GIS-Datensätze Knoten, Haltungen und Teileinzugsgebiete 
# in die Template-Dateie, um eine vollständige Datei für die Simulation zu generieren. Anschliessend werden die erstellten Modelle mit 
# der Software SWMM ausgeführt (aktuell im Skirpt auskommentiert -> Simulation besser in SWMM-Software ausführen).
#
# Die SWMM-Objekte EVAPORATION, RAINGAGES, MAP, REPORT, STORAGE, DWF, CURVES, ORIFICES, WEIRS, LOSSES, TIMESERIES, 
# TAGS, SYMBOLS, LABELS sind noch nicht berücksichtigt und müssten bei Bedarf in der SWMM-Software erstellt werden.
# Bei den SWMM-Objekten OUTFALLS und PUMPS werden nicht alle Felder berücksichtigt.
# -----------------------------------------------------------------------------
"""gisswmm2swmm"""
import os, sys, time, json, shutil, re
import arcpy
import swmmio
from swmm_api import swmm5_run
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))
import logging_functions as lf

def coords_to_list(coords):
    """Konvertiert einen String mit Koordinaten zu einer Liste aus Koordinatenpaaren

    Required:
        coords -- String mit Koordinaten nach folgendem Schema: '[(x,y),(x,y),...]' z. B. '[(2664547.6, 1210716.7), (2664545.4, 1210718.5)]'

    Return:
        coords_list -- Liste mit Koordinatenpaar-Listen [x,y]
    """
    # Eckige Klammern entfernen
    coords = coords.replace("[","").replace("]","")
    # String bei Klammern und Komma auftrennen
    cs = re.split('\(|\)|,', coords)
    coords_list = []
    idx = 0
    xy_check = "x" 
    for val in cs:
        if val in ["(",",",")",""," "]:
            continue
        else:
            if xy_check == "x":
                coords_list.append([float(val)])
                xy_check = "y"
            elif xy_check == "y":
                coords_list[idx].append(float(val))
                xy_check = "x"
                idx += 1

    return coords_list


# Main module: Input-Daten aufbereiten und Funktionen aufrufen
def main(out_node, out_link, out_subcatchment, template_swmm_file, sim_nr):
    """Input-Daten aufbereiten und Funktionen für die Konvertierung der GIS Feature-Klassen (node, link, subcatchment)
    in das SWMM-Datenformat (.inp) aufrufen.

    Required:
        out_node -- Name der Feature-Klasse mit den Schächten (ohne Postfix)
        out_link -- Name der Feature-Klasse mit den Haltungen (ohne Postfix)
        out_subcatchment -- Name der Feature-Klasse mit den Teileinzugsgebieten (ohne Postfix)
        template_swmm_file -- Template .inp-Datei die alle Angaben ausser der Bauwerke enthält
        sim_nr -- Wird als Postfix für Log-Dateinamen und Feature-Klassen verwendet
    """
    # Pfad zur Output SWMM-Datei
    in_path, in_name = os.path.split(template_swmm_file)
    out_path = os.path.join(in_path, sim_nr)
    out_name = in_name.split(".inp")[0] + "_" + sim_nr + '.inp'

    # Ordner mit SWMM-Dateien erstellen
    if not os.path.isdir(out_path):
        os.mkdir(out_path)

    swmm_out_file = os.path.join(out_path, out_name)

    # swmmio Objekt erstellen
    mymodel = swmmio.Model(template_swmm_file)

    ## Nodes hinzufügen (STORAGE, DWF,.. noch nicht berücksichtigt)
    # Dataframes laden
    junctions = mymodel.inp.junctions
    outfalls = mymodel.inp.outfalls
    coordinates = mymodel.inp.coordinates
    # Name dataframe index (swmmio)
    junctions.index.name = "Name"
    coordinates.index.name = "Name"
    outfalls.index.name = "Name"
    # GISSWMM-Felder definieren  (erstes Feld -> Index, zweites Feld -> Typ)
    node_fields_gis = ["Name", "SWMM_TYPE", "InvertElev", "InitDepth", "MaxDepth", "SurchargeDepth", "PondedArea", "OutfallType", "coords", "tag"]
    # Mapping GISSWMM-Feld:swmmio-Feld für junction
    junction_fields = {"InvertElev":"InvertElev", "MaxDepth":"MaxDepth", "InitDepth":"InitDepth", "SurchargeDepth":"SurchargeDepth", "PondedArea":"PondedArea"}
    # Mapping GISSWMM-Feld:swmmio-Feld für outfall    
    outfall_fields = {"InvertElev":"InvertElev", "OutfallType":"OutfallType"}
    # Daten aus GIS-Datensatz extrahieren
    with arcpy.da.SearchCursor(out_node, node_fields_gis) as cursor:
        for row in cursor:
            for ii, val in enumerate(row):
                in_field = node_fields_gis[ii]
                if row[1] in ["INLET", "JUNCTION"] and  in_field in list(junction_fields.keys()):
                    junctions.loc[row[0], junction_fields[in_field]]= val
                elif row[1] == "OUTFALL" and  in_field in list(outfall_fields.keys()):
                    outfalls.loc[row[0], outfall_fields[in_field]] = val
                elif in_field == "coords":
                    coordinates.loc[row[0]] = coords_to_list(val)[0]
                #elif in_field == "tag":
    # Modell aktualisieren
    mymodel.inp.junctions = junctions
    mymodel.inp.outfalls = outfalls
    mymodel.inp.coordinates = coordinates

    ## Links hinzufügen (ORIFICES, WEIRS, LOSSES noch nicht berücksichtigt)
    conduits = mymodel.inp.conduits
    pumps = mymodel.inp.pumps
    xsections = mymodel.inp.xsections
    vertices = mymodel.inp.vertices
    # Name dataframe index (swmmio)
    conduits.index.name = "Name"
    pumps.index.name = "Name"
    xsections.index.name = "Link"
    vertices.index.name = "Link"
    # GISSWMM-Felder definieren  (erstes Feld -> Index, zweites Feld -> Typ)
    link_fields_gis = ["Name", "SWMM_TYPE", "InletNode", "OutletNode", "Length", "Roughness", "InOffset", "OutOffset", 
                       "InitFlow", "MaxFlow", "ShapeType", "Geom1", "Geom2", "Geom3" , "Geom4", "Barrels", "coords"]
    # Mapping GISSWMM-Feld:swmmio-Feld für conduit (muss evtl. je nach SWMM-Version angepasst werden)
    conduit_fields = {"InletNode":"InletNode", "OutletNode":"OutletNode", "Length":"Length",  "Roughness":"Roughness", 
                      "InOffset": "InOffset", "OutOffset":"OutOffset", "InitFlow":"InitFlow", "MaxFlow":"MaxFlow"}
    # Mapping GISSWMM-Feld:swmmio-Feld für pump
    pump_fields = {"InletNode":"InletNode", "OutletNode":"OutletNode"} #  PumpCurve, InitStatus, StartupDepth, ShutoffDepth nicht berücksichtigt
    # Mapping GISSWMM-Feld:swmmio-Feld für xsection
    xsections_fields = {"ShapeType":"Shape", "Geom1":"Geom1", "Geom2":"Geom2", "Geom3":"Geom3", "Geom4":"Geom4", "Barrels":"Barrels"} # Geom3, Geom4, Barrels nicht berücksichtigt
    # Daten aus GIS-Datensatz extrahieren
    with arcpy.da.SearchCursor(out_link, link_fields_gis) as cursor:
        for row in cursor:
            for ii, val in enumerate(row):
                in_field = link_fields_gis[ii]
                if row[1] == "CONDUIT" and  in_field in list(conduit_fields.keys()):
                    conduits.loc[row[0], conduit_fields[in_field]] = val
                elif row[1] == "PUMP" and  in_field in list(pump_fields.keys()):
                    pumps.loc[row[0], pump_fields[in_field]] = val
                elif in_field in list(xsections_fields.keys()):
                    xsections.loc[row[0], xsections_fields[in_field]] = val
                elif in_field == "coords":
                    coords_list = coords_to_list(val)
                    for coords in coords_list:
                        # temp dataframe
                        df = pd.DataFrame({"X":coords[0],"Y":coords[1]},  index = [row[0]] )
                        df.index.name = "Link"
                        vertices = vertices.append(df)
                #elif in_field == "tag":

    # Modell aktualisieren
    mymodel.inp.conduits = conduits
    mymodel.inp.pumps = pumps
    mymodel.inp.xsections = xsections
    mymodel.inp.vertices = vertices

    ## Subcatchment hinzufügen
    subcatchments = mymodel.inp.subcatchments
    subareas = mymodel.inp.subareas
    infiltration = mymodel.inp.infiltration
    polygons = mymodel.inp.polygons

    # Name dataframe index (swmmio)
    subcatchments.index.name = "Name"
    subareas.index.name = "Subcatchment"
    subareas.index.name = "Subcatchment"
    polygons.index.name = "Subcatchment"

    # GISSWMM-Felder definieren  (erstes Feld -> Index, zweites Feld -> Typ)
    subcatchments_fields_gis = ["Name", "Raingage", "Outlet", "Area", "PercImperv", "Width", "PercSlope", "N_Imperv", 
                                "N_Perv", "S_Imperv", "S_Perv", "PctZero", "RouteTo", "CurbLength", "SnowPack",
                                "MaxRate", "MinRate", "Decay", "DryTime", "MaxInfil", "coords"]
    # Mapping GISSWMM-Feld:swmmio-Feld für conduit (muss evtl. je nach SWMM-Version angepasst werden)
    subcatchments_fields = {"Raingage":"Raingage", "Outlet":"Outlet", "Area":"Area",  "PercImperv":"PercImperv", 
                            "Width": "Width", "PercSlope":"PercSlope", "CurbLength":"CurbLength", "SnowPack":"SnowPack"}
    subareas_fields = {"N_Imperv":"N-Imperv", "N_Perv":"N-Perv", "S_Imperv":"S-Imperv", "S_Perv":"S-Perv", 
                       "PctZero":"PctZero", "RouteTo": "RouteTo"}
    infiltration_fields = {"MaxRate":"MaxRate", "MinRate":"MinRate", "Decay":"Decay", "DryTime":"DryTime", "MaxInfil":"MaxInfil"}                      

    # Daten aus GIS-Datensatz extrahieren
    with arcpy.da.SearchCursor(out_subcatchment, subcatchments_fields_gis) as cursor:
        for row in cursor:
            for ii, val in enumerate(row):
                in_field = subcatchments_fields_gis[ii]
                if in_field in list(subcatchments_fields.keys()):
                    subcatchments.loc[row[0], subcatchments_fields[in_field]] = val
                elif in_field in list(subareas_fields.keys()):
                    subareas.loc[row[0], subareas_fields[in_field]] = val
                elif in_field in list(infiltration_fields.keys()):
                    infiltration.loc[row[0], infiltration_fields[in_field]] = val      
                elif in_field == "coords":
                    coords_list = coords_to_list(val)
                    for coords in coords_list:
                        # temp dataframe
                        df = pd.DataFrame({"X":coords[0],"Y":coords[1]},  index = [row[0]] )
                        df.index.name = "Subcatchment"
                        polygons = polygons.append(df)

    # Modell aktualisieren
    mymodel.inp.subcatchments = subcatchments
    mymodel.inp.subareas = subareas
    mymodel.inp.infiltration = infiltration
    mymodel.inp.polygons = polygons

    ## save model to new file
    mymodel.inp.save(swmm_out_file)

    ## run model
    #swmm5_run(swmm_out_file)


# Daten einlesen 
# Logginig initialisieren
if __name__ == "__main__":
    # Globale Variabel für logging
    global logger
    # Input JSON-Datei
    # Falls das Skript mittels einer Batch-Datei ausgeführt wird, wird die JSON-Datei als Parameter übergeben:
    paramFile = arcpy.GetParameterAsText(0)
    # Falls das Skript direkt ausgeführt wird, wird die JSON-Datei hier angeben:
    if len(paramFile) == 0:
        paramFile = os.path.join(os.path.dirname(__file__), '..', 'settings_v1.json')


    if paramFile:
        #Einlesen der json-Datei
        with open(paramFile, encoding='utf-8') as f:
            data = json.load(f)
            # Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. 
            log_folder = data["log_folder"]
            # Wird als Postfix für Log-Dateinamen und die SWMM Feature-Klassen (node, link, subcatchment) verwendet.
            sim_nr = data["sim_nr"]
            # Pfad zu arcpy Workspace GISSWMM (.gdb)  mit dem Knoten (out_node), Haltungen (out_link) und Teileinzugsgebieten (out_subcatchment).
            gisswmm_workspace = data["gisswmm_workspace"]
            # Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!).
            out_node = data["out_node"]
            # Der Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!).
            out_link = data["out_link"]
            # Der Name der Feature-Klasse mit den Teileinzugsgebieten (ohne Postfix "_sim_nr"!).
            out_subcatchment = data["out_subcatchment"]
            # Der Pfad zur Template SWMM-Eingabedatei (.inp).
            template_swmm_file = data["template_swmm_file"]
    else:
        raise ValueError('keine json-Datei mit den Parametern angegeben')

    # Prüfen ob Logfolder existiert
    if not os.path.isdir(log_folder):
        try:
            os.mkdir(log_folder)
        except:
            raise ValueError(f'Logfolder "{log_folder}" konnte nicht erstellt werden!')
   
    # Logging initialisieren
    filename = 'gisswmm2swmm_' + sim_nr + "_" + template_swmm_file.split("/")[-1].split(".")[0] + '.log'
    log = os.path.join(log_folder, filename)
    logger= lf.init_logging(log)
    logger.info('****************************************************************')
    logger.info(f'Start logging: {time.ctime()}')
    start_time = time.time()

    # Aktuelle Workspace definieren
    arcpy.env.workspace = gisswmm_workspace

    # Prüfen ob Eingabedatensätze vorhanden sind
    postfix = "_" + sim_nr
    if not postfix in out_node:
        out_node = out_node + postfix
    if not postfix in out_link:
        out_link = out_link + postfix
    if not postfix in out_subcatchment:
        out_subcatchment = out_subcatchment + postfix
    if not arcpy.Exists(out_node):
        err_txt = f'Die angegebene Feature-Klasse {out_node} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)  
    if not arcpy.Exists(out_link):
        err_txt = f'Die angegebene Feature-Klasse {out_link} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)
    if not arcpy.Exists(out_subcatchment):
        err_txt = f'Die angegebene Feature-Klasse {out_subcatchment} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)

    # Koordinatensystem
    spatial_ref = arcpy.Describe(out_node).spatialReference

    # Main module aufrufen
    with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref):
        main(out_node, out_link, out_subcatchment, template_swmm_file, sim_nr)

    # Logging abschliessen
    end_time = time.time()
    i = lf.search_in_file(log, "error")
    logger.info("Skript Laufzeit: " + str(round(end_time - start_time)) + " sec.")
    logger.info(str(i) + " Fehler gefunden. Check Log.")
    endtime = time.ctime()
    logger.info(f'End time: {time.ctime()}')
    logger.info('****************************************************************\n')




