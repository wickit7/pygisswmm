# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 28.07.2021
#
# Haltungen (link) und Schächte (node) von einem Dataset in andere Datasets kopieren.
# Kann verwendet werden, falls im folgenden für die gleichen Haltungen und Knoten, 
# Teileinzugsgebiete mit unterschiedlicher Methoden berechnet werden sollen. Damit
# vorherige Prozesse nicht nochmals durchgeführt werden müssen
# -----------------------------------------------------------------------------
"""copy_from_vx_to_vy"""
import os, sys, time, json
import arcpy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))
import logging_functions as lf

def main(gisswmm_workspace, overwrite, in_node, in_link, out_node, out_link, to_sim_nrs):
    """Input-Daten aufbereiten und Funktionen aufrufen

    Required:
        gisswmm_workspace -- Pfad zu arcpy Workspace  (z. B. ".gdb") mit Schächten und Haltungen
        overwrite -- "True" falls angegebene Output Feature-Klasse überschrieben werden soll. "False" falls nicht.
        in_node -- Name der Input Feature-Klasse mit den Schächten
        in_link -- Name der Input Feature-Klasse mit den Haltungen
        out_node -- Name der Output Feature-Klasse mit den Schächte
        out_link -- Name der Output Feature-Klasse mit den Haltungen
        to_sim_nrs -- Liste mit Datasets (Simulationsnummern) bei welchen die Haltungen und Schächte hinzugefügt werden sollen
    """   
    for sim_nr in to_sim_nrs:
        # Feature Dataset erstellen
        out_dataset_path = os.path.join(gisswmm_workspace, sim_nr)
        if arcpy.Exists(out_dataset_path):
            if overwrite:
                logger.info(f'Vorhande Feature-Dataset {sim_nr} wird gelöscht')
                arcpy.management.Delete(sim_nr)
            else:
                logger.warning(f'Vorhande Feature-Klasse {sim_nr} wurde nicht überschrieben. '
                            f'"overwrite" muss "True" sein!')
        arcpy.management.CreateFeatureDataset(gisswmm_workspace, sim_nr)

        # Name der Output Datensätze
        out_link_name = out_link + "_" + sim_nr
        out_node_name = out_node + "_" + sim_nr

        # Haltungen kopieren
        try:
            logger.info(f'Feature "{in_link}" nach Feature-Klasse "{out_link_name}" kopieren')
            # copy feature
            arcpy.conversion.FeatureClassToFeatureClass(in_link, out_dataset_path, out_link_name)

        except Exception:
            e = sys.exc_info()[1]
            logger.error(f'Feature "{in_link}" konnte nicht nach Feature-Klasse "{out_link_name}" '
                        f'kopiert werden: {e.args[0]}')

        # Schächte kopieren
        try:
            logger.info(f'Feature "{in_node}" nach Feature-Klasse "{out_node_name}" kopieren')
            # copy feature
            arcpy.conversion.FeatureClassToFeatureClass(in_node, out_dataset_path, out_node_name)

        except Exception:
            e = sys.exc_info()[1]
            logger.error(f'Feature "{in_node}" konnte nicht nach Feature-Klasse "{out_node_name}" '
                        f'kopiert werden: {e.args[0]}')

        logger.info(f'')

# Daten einlesen 
# Logginig initialisieren
if __name__ == "__main__":
    # Globale Variabel für logging
    global logger
    ### Input JSON-Datei ###
    #paramFile = r'...\gisswmm_copy_v5_to_v6_v7_v8.json'
    paramFile = arcpy.GetParameterAsText(0)

    # Falls das Skript mittels einer Batch-Datei ausgeführt wird, wird die JSON-Datei als Parameter übergeben:
    paramFile = arcpy.GetParameterAsText(0)
    # Falls das Skript direkt ausgeführt wird, wird die JSON-Datei hier angeben:
    if len(paramFile) == 0:
        paramFile = "copy_v1_to_v2_v3_v4"

    if paramFile:
        #Einlesen der json-Datei
        with open(paramFile, encoding='utf-8') as f:
            data = json.load(f)
            # Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. 
            log_folder = data["log_folder"]
            # Der Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node" und "in_link" gespeichert sind. 
            gisswmm_workspace = data["gisswmm_workspace"]
            # Die Bezeichnung des Datasets im Workspace "gisswmm_workspace" (Bezeichnung der Simulation), welches kopiert werden soll. 
            from_sim_nr = data["from_sim_nr"]
            #  Eine Liste mit Datasets (Simulationen), die erstellt werden sollen.
            to_sim_nrs = data["to_sim_nrs"]
            # Der Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!).
            in_node = data["out_node"]
            # Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!).
            in_link = data["out_link"]
            # Die arcpy Umgebungseinstellung "overwrite".
            if "overwrite" in data:
                overwrite = data["overwrite"]
            else: 
                overwrite = "True"

    else:
        raise ValueError('keine json-Datei mit den Parametern angegeben')

    # Prüfen ob Logfolder existiert
    if not os.path.isdir(log_folder):
        try:
            os.mkdir(log_folder)
        except:
            raise ValueError(f'Logfolder "{log_folder}" konnte nicht erstellt werden!')

    # overwrite str -> bool
    if overwrite == 'True':
        overwrite = True
    else:
        overwrite = False

    # Logging initialisieren
    filename = 'copy_from_' + from_sim_nr + '.log'
    log = os.path.join(log_folder, filename)
    logger= lf.init_logging(log)
    logger.info('****************************************************************')
    logger.info(f'Start logging: {time.ctime()}')
    start_time = time.time()

    # Aktuelle Workspace definieren
    arcpy.env.workspace = gisswmm_workspace
    
    # Ausgabedatensätze gleiche Bezeichnung wie Eingabedatensätze (ohne Postfix)
    out_node = in_node
    out_link = in_link
    # Prüfen ob Eingabedatensätze vorhanden sind
    postfix = "_" + from_sim_nr
    if not postfix in in_node:
        in_node = in_node + postfix
    if not postfix in in_link:
        in_link = in_link + postfix
    if not arcpy.Exists(in_node):
        err_txt = f'Die angegebene Feature-Klasse {in_node} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)  
    if not arcpy.Exists(in_link):
        err_txt = f'Die angegebene Feature-Klasse {in_link} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)

    spatial_ref = arcpy.Describe(in_node).spatialReference

    # Main module aufrufen
    with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
        main(gisswmm_workspace, overwrite, in_node, in_link, out_node, out_link, to_sim_nrs)

    # Logging abschliessen
    end_time = time.time()
    i = lf.search_in_file(log, "error")
    logger.info("Skript Laufzeit: " + str(round(end_time - start_time)) + " sec.")
    logger.info(str(i) + " Fehler gefunden. Check Log.")
    endtime = time.ctime()
    logger.info(f'End time: {time.ctime()}')
    logger.info('****************************************************************\n')










