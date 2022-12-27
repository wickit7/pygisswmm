# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 26.06.2021
#
# Das Abwasserkataster, welches im Datenmodell SIA405 vorliegt, wird in einen vereinfachten
# GIS-Datensatz bestehend aus Knoten und Haltungen konvertiert. Dieser Datensatz wird als Grundlage  
# für die weitere Prozessierung mit den folgenden pygisswmm-Skripten benötigt. Die Input-
# Feature-Klassen werden gefiltert und es wird ein Attributmapping durchgeführt.
# Die Input-Parameter werden in einer JSON-Datei angegeben, die als Eingabe dem Skript
# übergeben wird. Die Output-Datensätze werden überschrieben. 
# -----------------------------------------------------------------------------
"""sia2gisswmm"""
import os, sys, time, json
import arcpy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))
import logging_functions as lf

def copy_with_fields(in_fc, out_fc, dict_fields, type_mapping = {}, where = '', overwrite = True):
    """Eine Feature-Klasse mit einer Auswahl von bestimmten Felder kopieren.  
    OID- und Geometry-Felder werden alle beibehalten.

    Required:
        in_fc -- Bezeichnung der Input Feature-Klasse (z. B. "AWK_ABWASSERKNOTEN")
        out_fc -- Bezeichnung der Output Feature-Klasse (z. B. "link")
        dict_fields -- Dictionary mit der Bezeichnung der Eingabe- und Ausgabefeldern "in_field:out_field"
                    die gemappt werden sollen (z. B. "FUNKTIONHYDRAULISCH":"SWMM_TYPE")
        
    Optional:
        type_mapping -- Dictionary "out_field:out_type" für Output Felder deren Typ geändert werden soll
        where -- Where-Clause um Daten zu filtern
        overwrite -- "True" falls angegebene Output Feature-Klasse überschrieben werden soll, andernfalls "False"

    Return:
        out_fc -- Output Feature-Klasse oder None
    """
    logger.info(f'Feld-Mapping von Layer "{in_fc}" durchführen')

    # Falls die Output Feature-Klasse bereits vorhanden ist wird sie gelöscht
    if arcpy.Exists(out_fc):
        if overwrite:
            logger.info(f'Vorhande Feature-Klasse {out_fc} wird gelöscht')
            arcpy.management.Delete(out_fc)
        else:
            logger.warning(f'Vorhande Feature-Klasse {out_fc} wurde nicht überschrieben. '
                           f'Parameter "overwrite" muss "True" sein!')
            return out_fc

    # Field-Mapping initialisieren
    fmap = arcpy.FieldMappings()
    fmap.addTable(in_fc)

    # Liste mit allen Felder
    flds = fmap.fieldMappings
    fnames = {f.getInputFieldName(0) for f in flds}

    # Prüfen ob alle Felder vorhanden sind
    for in_field in dict_fields:
        if in_field not in fnames:
            logger.warning(f'Das Feld {in_field} in FC {in_fc} ist nicht vorhanden')

    # Field-Mapping breinigen
    for fld in flds:
        name_orig = fld.getInputFieldName(0)
        if name_orig in dict_fields.keys():
            # Ausgabefeld
            of = fld.outputField
            change = False
            # Feld umbennenen falls 'in_field' nicht gleich 'out_field'
            if name_orig != dict_fields[name_orig]:
                of.name = dict_fields[name_orig]
                of.aliasName = dict_fields[name_orig]
                change = True
            # Feldtyp ändern 
            if dict_fields[name_orig] in type_mapping:
                of.type = type_mapping[dict_fields[name_orig]]
                if type_mapping[dict_fields[name_orig]] == "Text":
                    of.length = 128
                change = True            
            if change:
                fld.outputField = of
                fmap.replaceFieldMap(fmap.findFieldMapIndex(name_orig), fld)
        else:
            # Feld entfernen falls nicht in 'dict_fields'
            try:
                fmap.removeFieldMap(fmap.findFieldMapIndex(name_orig))
            except Exception:
                e = sys.exc_info()[1]
                logger.warning(f'Das Feld "{name_orig}" konnte nicht gelöscht '
                                f'werden: {e.args[0]}')

    # Pfad und Name der Output Feature-Klasse 
    path, name = os.path.split(out_fc)

    # Werte hinzufügen
    try:
        logger.info(f'Layer "{in_fc}" nach Feature-Klasse "{name}" konvertieren')
        # Layer nach Feature-Klasse kovertieren 
        arcpy.conversion.FeatureClassToFeatureClass(in_fc, path, name, where, fmap)

        return out_fc

    except Exception:
        e = sys.exc_info()[1]
        logger.error(f'Layer "{in_fc}" konnte nicht nach Feature-Klasse "{name}" '
                     f'konvertiert werden: {e.args[0]}')
        return None


# Input-Daten aufbereiten und Funktionen aufrufen
def main(in_node, in_link, boundary_workspace, in_boundary, gisswmm_workspace, out_node, 
         out_link, mapping_link, mapping_node, default_values_link, default_values_node, sim_nr):

    ## Feature-Klassen kopiern mit Schemaanpassung
    logger.info(f'Feature-Klassen zu Layer konvertieren')
    # Feature-Klasse zu Layer konvertieren
    arcpy.management.MakeFeatureLayer(in_link, 'in_link_lyr')
    arcpy.management.MakeFeatureLayer(in_node, 'in_node_lyr')

    # Pfad zu Input Gebietsgrenze (Untersuchungsgebiet)
    in_boundary = os.path.join(boundary_workspace, in_boundary)

    logger.info(f'Räumliche Selektion durchführen')
    # Räumliche Selektion (nur Daten innerhalb Gebietsgrenze verwenden)
    arcpy.management.SelectLayerByLocation('in_link_lyr', 'intersect', in_boundary)
    arcpy.management.SelectLayerByLocation('in_node_lyr', 'intersect', in_boundary)

    logger.info(f'Datenschema Haltung anpassen (Link-Mapping)')
    where_link = ''
    cnt = 0
    value_mapping_link = {}
    type_mapping_link = {}
    for lm in mapping_link:
        # Where-Clause basierend auf dictionaries
        if "where" in lm:
            # Annahme: In der Where-Clause immer nur das aktuelle Feld (in_field) enthalten
            where = lm.pop("where").replace(lm['in_field'], '"'+lm['in_field'] + '"')
            if cnt == 0:
                # Klammer um Where-Clause
                where_link = f'({where})'
                cnt = 1
            else:
                # Where-Clauses für die unterschiedlichen Felder mit AND verbinden
                where_link = f'{where_link} AND ({where})'
        if "mapping" in lm:
            # Mapping (Werte gemäss mapping zuweisen)
            mapping = lm.pop("mapping")
            value_mapping_link.update({lm['out_field']:mapping})
        if "out_type" in lm:
            # Typ von Output-Feld anpassen
            out_type = lm.pop("out_type")
            type_mapping_link.update({lm['out_field']:out_type})

    logger.info(f'Datenschema Knoten anpassen (Node-Mapping)')
    where_node = ''
    cnt = 0
    value_mapping_node = {}
    type_mapping_node = {}
    for lm in mapping_node:
        # Where-Clause basierend auf dictionaries
        if "where" in lm:
            where = lm.pop("where").replace(lm['in_field'], '"'+lm['in_field'] + '"')
            if cnt == 0:
                # Klammer um Where-Clause
                where_node = f'({where})'
                cnt = 1
            else:
                # Where-Clauses für die untschiedlichen Felder mit AND verbinden
                where_node = f'{where_node} AND ({where})'
        if "mapping" in lm:
            # Mapping (Werte gemäss mapping zuweisen)
            mapping = lm.pop("mapping")
            value_mapping_node.update({lm['out_field']:mapping})
        if "out_type" in lm:
            # Typ von Output-Feld anpassen
            out_type = lm.pop("out_type")
            type_mapping_node.update({lm['out_field']:out_type})
    
    # Prüfen ob gdb bereits existiert
    if not arcpy.Exists(gisswmm_workspace):
        gisswmm_workspace_path, gisswmm_workspace_name = os.path.split(gisswmm_workspace)
        arcpy.management.CreateFileGDB(gisswmm_workspace_path, gisswmm_workspace_name)
    
    # Output Feature-Dataset erstellen
    out_dataset_path = os.path.join(gisswmm_workspace, sim_nr)
    if arcpy.Exists(out_dataset_path):
        if overwrite:
            logger.info(f'Vorhandes Feature-Dataset {sim_nr} wird gelöscht')
            arcpy.management.Delete(sim_nr)
        else:
            logger.warning(f'Vorhandes Feature-Dataset {sim_nr} wurde nicht überschrieben. '
                           f'"overwrite" muss "True" sein!')
    arcpy.management.CreateFeatureDataset(gisswmm_workspace, sim_nr)

    # Namen der Output Feature-Klassen
    out_link_name = out_link + "_" + sim_nr
    out_node_name = out_node + "_" + sim_nr

    # Pfad der Output Feature-Klassen
    out_link_path = os.path.join(out_dataset_path, out_link_name)
    out_node_path = os.path.join(out_dataset_path, out_node_name)

    logger.info(f'Output Feature-Klassen erstellen')
    # field-mapping dictionaries erstellen (Input Feld: Output Feld)
    mapping_link_fields = {map["in_field"]:map["out_field"] for map in mapping_link}
    mapping_node_fields = {map["in_field"]:map["out_field"] for map in mapping_node}

    # Output Feature-Klassen mit einer Auswahl von definierten Feldern erstellen
    out_link = copy_with_fields('in_link_lyr', out_link_path, mapping_link_fields,
                                type_mapping_link, where_link, overwrite)
    out_node= copy_with_fields('in_node_lyr', out_node_path, mapping_node_fields,
                                type_mapping_node, where_node, overwrite)

    ## Werte in Link aktualisieren gemäss mapping
    if value_mapping_link:
            update_link_fields = list(value_mapping_link.keys())
            with arcpy.da.UpdateCursor(out_link, update_link_fields) as ucursor:
                for urow in ucursor:
                    for ii, val in enumerate(urow):
                        try:
                            urow[ii] = value_mapping_link[update_link_fields[ii]][str(urow[ii])]
                        except KeyError:
                            if val == "None":
                                urow[ii] = value_mapping_link[update_link_fields[ii]]["None"]
                            else:
                                arcpy.AddWarning(f'Feld "{update_link_fields[ii]}": Für den Wert "{val}" '
                                                 'ist kein Mapping angegeben! Der Wert wird auf "None" gesetzt')
                                urow[ii] = None
                    ucursor.updateRow(urow)

    ## Werte in Node aktualisieren gemäss mapping
    if value_mapping_node:
            update_node_fields = list(value_mapping_node.keys())
            with arcpy.da.UpdateCursor(out_node, update_node_fields) as ucursor:
                for urow in ucursor:
                    for ii, val in enumerate(urow):
                        try:
                            urow[ii] = value_mapping_node[update_node_fields[ii]][str(urow[ii])]
                        except KeyError:
                            arcpy.AddWarning(f'Feld "{update_node_fields[ii]}": Für den Wert "{val}" '
                                              'ist kein Mapping angegeben! Der Wert wird auf "None" gesetzt')
                            urow[ii] = None
                    ucursor.updateRow(urow)
                    
    ## Zusätzliche Attribute zu Link hinzufügen die für die Applikation SWMM benötigt werden
    arcpy.management.AddField(out_link, "Length", "FLOAT")
    arcpy.management.AddField(out_link, "Geom1", "FLOAT")
    arcpy.management.AddField(out_link, "Geom2", "FLOAT")
    arcpy.management.AddField(out_link, "Geom3", "FLOAT")
    arcpy.management.AddField(out_link, "Geom4", "FLOAT")
    arcpy.management.AddField(out_link, "Barrels", "SHORT")
    arcpy.management.AddField(out_link, "InOffset", "FLOAT")
    arcpy.management.AddField(out_link, "OutOffset", "FLOAT")
    arcpy.management.AddField(out_link, "InitFlow", "FLOAT")
    arcpy.management.AddField(out_link, "MaxFlow", "FLOAT")
    arcpy.management.AddField(out_link, "coords", "TEXT", field_length=10000)

    # Felder berechnen
    with arcpy.da.UpdateCursor(out_link, ["Shape_Length", "Length", "SHAPE@", "coords","LICHTE_HOEHE","BREITE",
                               "Geom1","Geom2","Geom3","Geom4","Barrels"]) as ucursor:
        for urow in ucursor:
            # Länge berechnen
            urow[1] = urow[0]
            coords = []
            for part in urow[2]:
                for pnt in part:
                    coords.append((pnt.X,pnt.Y))
            # Koordinaten von Geometrie als Text in Feld speichern
            urow[3] = str(coords)
            # Höhe und Breite Kanal: Einheit [mm] zu [m] konvertieren
            urow[6] = float(urow[4])/1000.0
            urow[7] = float(urow[5])/1000.0
            # Standartwerte für die SWWM-Felder "Geom3","Geom4","Barrels"
            urow[8] = 0
            urow[9] = 0
            urow[10] = 1

            ucursor.updateRow(urow)

    # Standartwerte für Link (Haltungen) abfüllen
    default_link_fields = list(default_values_link.keys())
    with arcpy.da.UpdateCursor(out_link, default_link_fields) as ucursor:
        for urow in ucursor:
            for ii, val in enumerate(urow):
                if not val:
                    urow[ii] = default_values_link[default_link_fields[ii]]
            ucursor.updateRow(urow)

    ## Zusätzliche Attribute zu Node hinzufügen die für die Applikation SWMM benötigt werden
    arcpy.management.AddField(out_node, "coords", "TEXT", field_length=128)
    arcpy.management.AddField(out_node, "InitDepth", "FLOAT")
    arcpy.management.AddField(out_node, "SurchargeDepth", "FLOAT")
    arcpy.management.AddField(out_node, "PondedArea", "FLOAT")

    # Felder berechnen
    with arcpy.da.UpdateCursor(out_node, ["SHAPE@", "coords"]) as ucursor:
        for urow in ucursor:
            coords = []
            for pnt in urow[0]:
                coords.append((pnt.X,pnt.Y))
            # Koordinaten von Geometrie als Text in Feld speichern
            urow[1] = str(coords)
            ucursor.updateRow(urow)

    # Standartwerte für Node (Knoten) abfüllen
    default_node_fields = list(default_values_node.keys())
    with arcpy.da.UpdateCursor(out_node, default_node_fields) as ucursor:
        for urow in ucursor:
            for ii, val in enumerate(urow):
                if not val:
                    urow[ii] = default_values_node[default_node_fields[ii]]             
            ucursor.updateRow(urow)


# Daten einlesen 
# Logginig initialisieren
if __name__ == "__main__":
    # Globale Variabel für logging
    global loggerf
    ### Input JSON-Datei ###
    # Falls Übergabe mittels Batch-Datei, JSON-Datei als Parameter übergeben:
    paramFile = arcpy.GetParameterAsText(0)
    # Falls Skript direkt ausgeführt wird, JSON-Datei hier angeben:
    if len(paramFile) == 0:
        paramFile = os.path.join(os.path.dirname(__file__), '..', 'settings_v1.json')

    if paramFile:
        # Einlesen der json-Datei
        with open(paramFile, encoding='utf-8') as f:
            data = json.load(f)
            # Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll.	
            log_folder = data["log_folder"]
            # Die Bezeichnung der aktuellen Simulation (Szenario). Das Esri Feature-Dataset im Workspace 
            # "gisswmm _workspace" erhält diese Bezeichnung. Zudem wird die Bezeichnung den Feature-Klassen 
            # ("out_node", "out_link") und der Log-Datei als Postfix hinzugefügt.	
            sim_nr = data["sim_nr"]
            # Der Pfad zum arcpy Workspace (.gdb, .sde), welcher das zu konvertierende Abwasserkataster (SIA405) enthält.	
            lk_workspace = data["lk_workspace"]
            # Der Name der Input Feature-Klasse mit den Abwasserknoten (Schächte) im Workspace "lk_workspace".	
            in_node = data["in_node"]
            # Der Name der Input Feature-Klasse mit den Haltungen (Leitungen) im Workspace "lk_workspace".	
            in_link = data["in_link"]
            # Der Pfad zum arcpy Workspace, welcher die Input Feature-Klasse mit der Begrenzungsfläche des Untersuchungsgebietes enthält.	
            boundary_workspace = data["boundary_workspace"]
            # Der Name der Feature-Klasse mit der Input Begrenzungsfläche im Workspace "boundary_workspace".	
            in_boundary = data["in_boundary"]
            # Der Pfad zum Output arcpy Workspace, in dem die Output Feature-Klassen ("out_node", "out_link") gespeichert werden sollen.	
            gisswmm_workspace = data["gisswmm_workspace"]
            # Der Name der Output Feature-Klasse mit den konvertierten Abwasserknoten (dieser Name wird im Skript noch mit dem Postfix "_sim_nr" ergänzt).	
            out_node = data["out_node"]
            # Der Name der Output Feature-Klasse mit den konvertierten Haltungen (dieser Name wird im Skript noch mit dem Postfix "_sim_nr" ergänzt).	
            out_link = data["out_link"]
            # Die arcpy Umgebungseinstellung "overwrite".
            if "overwrite" in data:
                overwrite = data["overwrite"]
            else: 
                overwrite = "True"
            # Eine Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_link" (Abwasserkataster) zur Output Feature-Klasse "out_link" (gisswmm).	
            mapping_link = data["mapping_link"]
            # Eine Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_node" (Abwasserkataster) zur Output Feature-Klasse "out_node" (gisswmm).	
            mapping_node = data["mapping_node"]
            # Eine Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerten für die Output Feature-Klasse "out_link".	
            default_values_link = data["default_values_link"]
            # Eine Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerten für die Output Feature-Klasse "out_node".	
            default_values_node = data["default_values_node"]     
    else:
        raise ValueError('keine json-Datei mit den Parametern angegeben')

    # Prüfen ob Logfolder existiert
    if not os.path.isdir(log_folder):
        raise ValueError(f'Logfolder "{log_folder}" existiert nicht!')

    # overwrite str -> bool
    if overwrite == 'True':
        overwrite = True
    else:
        overwrite = False

    # Logging initialisieren
    filename = 'sia2gisswmm_' + sim_nr + '.log'
    log = os.path.join(log_folder, filename)
    logger = lf.init_logging(log)
    logger.info('****************************************************************')
    logger.info(f'Start logging: {time.ctime()}')
    start_time = time.time()

    # Aktueller Workspace definieren
    arcpy.env.workspace = lk_workspace
    # Koordinatensystem 
    spatial_ref = arcpy.Describe(in_node).spatialReference

    # Main module aufrufen
    with arcpy.EnvManager(workspace = lk_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
            main(in_node, in_link, boundary_workspace, in_boundary, gisswmm_workspace, out_node, 
                 out_link, mapping_link, mapping_node, default_values_link, default_values_node, sim_nr)

    # Logging abschliessen
    end_time = time.time()
    i = lf.search_in_file(log, "error")
    logger.info("Skript Laufzeit: " + str(round(end_time - start_time)) + " sec.")
    logger.info(str(i) + " Fehler gefunden. Check Log.")
    endtime = time.ctime()
    logger.info(f'End time: {time.ctime()}')
    logger.info('****************************************************************\n')

