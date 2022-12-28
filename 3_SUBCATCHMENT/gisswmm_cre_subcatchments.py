# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 25.03.2022
#
# Teileinzugsgebiete für Knoten (Schächte) erstellen:
# Es kann zwischen vier unterschiedlichen Methoden gewählt werden. Die topographischen Einzugsgebiete werden bei allen 
# Methoden verwendet und deshalb zuerst berechnet. Um den Wasserlauf über Oberflächen mittels GIS-Analysen zu modellieren, 
# werden die Senken des Höhenmodells gefüllt. Anschliessend wird die Fliessrichtung für jede Rasterzelle mit dem D8-Fliessmodell 
# berechnet (Jenson & Domingue, 1988). Basierend auf dem Raster mit der Fliessrichtung wird anschliessend die Abflussakkumulation
# berechnet (Jenson & Domingue, 1988). Basierend auf dem Raster der Abflussakkumulation wird anschliessend jedem Knoten, ausgenommen 
# Einlaufknoten wo kein Wasser einfliessen kann, ein Abflusspunkt mit maximaler Abflussakkumulation innerhalb einer bestimmten 
# Fangtoleranz zugewiesen. Das heisst, ein Knoten verschiebt seine Position innerhalb von 2m zum Ort mit höchster Abflussakkumulation. 
# Ausgehend von diesen Abflusspunkten wird für jeden Knoten das topographische Einzugsgebiet, basierend auf dem Fliessrichtungsraster, 
# bestimmt. 
#
# Methode 1 - Parzellen als Teileinzugsgebiete:
# Bei dieser Methode werden die Parzellen (Liegenschaften) der amtlichen Vermessung als Teileinzugsgebietsflächen 
# für die hydrodynamische Simulation verwendet. Die berechneten topographischen Teileinzugsgebiete (Abbildung 10) werden bei 
# dieser Methode verwendet, um den Parzellen einen Knoten zuzuweisen, in welchen das Oberflächenwasser der Parzelle entwässert.
# Dazu werden die Parzellen mit den topographischen Teileinzugsgebieten räumlich verschnitten und anschliessend wird der Knoten 
# mit dem grössten topographischen Teileinzugsgenbiet innerhalb der Parzelle als Entwässerungsknoten festgelegt. 
# Als Teileinzugsgebietsfläche, welche für die Berechnung der Teileinzugsgebietsparameter verwendet wird, wird die Summe der 
# innerhalb der Parzelle liegenden topographischen Teileinzugsgebiete verwendet. 
#
# Methode 2 - Parzellen unterteilt in Flächen mit homogener Bodenbedeckung:
# Bei dieser Methode werden die Parzellen mit der Bodenbedeckung räumlich verschnitten. Das Ergebnis sind Teileinzugsgebiete 
# mit homogener Bodenbedeckung. Anschliessend wird für jedes dieser Teileinzugsgebiete der Knoten mit dem grössten topographischen 
# Teileinzugsgenbiet als Entwässerungsknoten festgelegt. Als Teileinzugsgebietsfläche wird wiederum die Summe der innerhalb der 
# homogenen Teilparzellenflächen liegenden topographischen Teileinzugsgebiete verwendet.
#
# Methode 3 – Topographische Teileinzugsgebiete
# Bei dieser Methode entsprechen die Teileinzugsgebiete den topographischen Einzugsgebieten. Die topographischen Teileinzugsgebiete 
# entwässern ihr Oberflächenwasser in die Knoten von denen aus sie berechnet wurden. Das heisst, dass es für jeden Knoten ein zugehöriges 
# Teileinzugsgebiet gibt, mit Ausnahme der Einlaufknoten wo kein Oberflächenwasser einfliessen kann.
#
# Methode 4 - Topographische Teileinzugsgebiete unterteilt in Flächen mit homogener Bodenbedeckung
# Bei dieser Methode werden die topographischen Teileinzugsgebiete mit der Bodenbedeckung räumlich verschnitten. Das Ergebnis sind 
# topographische Teileinzugsgebiete unterteilt in Flächen mit homogener Bodenbedeckung (Abbildung 11), welche jeweils in den gleiche 
# Knoten entwässern.
#
#
# Anschliessend werden die Teileinzugsgebiete gemäss den Spezifikationen des SWMM-Modells (2.10 Hydrodynamische Simulation mit SWMM) 
# parametrisiert. 
# -----------------------------------------------------------------------------
"""gisswmm_cre_subcatchments"""
import os, sys, time, json, math
import arcpy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))
import logging_functions as lf

def del_small_polygons(in_feature, min_area):
    """Polygone der Feature-Klasse "in_feature", welche eine geringere Fläche als "min_area" aufweisen, werden gelöscht.

    Required:
        in_fc -- Input Feature-Klasse
        min_area -- Minimale Fläche
    """
    # Polygone mit geringer Fläche löschen (überbleibsel von clip-Funktion)
    with arcpy.da.UpdateCursor(in_feature, ["Shape_Area"]) as dcursor:
        for drow in dcursor:
            if drow[0] <= min_area:  
                dcursor.deleteRow()

# Main module: Input-Daten aufbereiten und Funktionen aufrufen
def main(dhm_workspace, in_dhm, max_slope, parcel_workspace, in_parcel, land_workspace, in_land, mapping_land_imperv, 
         mapping_land_roughness, mapping_land_depression_storage, infiltration, out_raster_workspace, out_raster_prefix, 
         gisswmm_workspace, out_node, node_id, node_type, type_inlet, snap_distance, min_area, method, out_subcatchment, sim_nr):
    """Input-Daten aufbereiten und Funktionen für die Erstellung der Teileinzugsgebiete aufrufen

    Required:
        dhm_workspace -- Pfad zu arcpy Workspace mit DHM (.gdb)
        in_dhm -- Bezeichnung des DHM-Rasters
        max_slope -- Neigungswert mit welchem höhere Werte im Raster ersetzt werden, bevor die mittelere Steigung berechnet wird
        parcel_workspace -- Pfad zu arcpy Workspace mit Parzellen (.gdb)
        in_parcel -- Bezeichnung der Feature-Klasse mit den Parzellen
        land_workspace -- Pfad zu arcpy Workspace mit Bodenbedeckung (.gdb)
        in_land -- Bezeichnung des Bodenbedeckung-Rasters
        mapping_land_imperv -- Dictionary mit Bodenbedeckung als "key" und %imperviousness (Befestigungsgrad) als "value"
        mapping_land_roughness -- Dictionary mit Bodenbedeckung als "key" und roughness (Rauhigkeit) als "value"
        mapping_land_depression_storage -- Dictionary mit Bodenbedeckung als "key" und depression storage (Muldentiefe) als "value"
        infiltration -- Dictionary mit Kennwerten zur Infiltration nach Horton
        out_raster_workspace -- Workspace von Ouput-Rasterdaten
        out_raster_prefix -- Prefix von Output-Rasterdaten
        gisswmm_workspace -- Pfad zu arcpy Workspace GISSWMM (.gdb) mit Schächten und Haltungen und der zu erstellenden Output Feature-Klasse (Teileinzugsgebiete)
        out_node -- Name der Feature-Klasse mit den Schächten (ohne Postfix)
        node_id -- Bezeichnung von ID-Feld der Schächte
        node_type -- Bezeichnung von Feld mit Schachttyp in der Feature-Klasse 'node_id'
        type_inlet -- Wert von Schachttyp ('node_type') welcher Einlaufschacht entspricht
        snap_distance -- Snap distance (Fangtoleranz) für Funktion arcpy.sa.SnapPourPoint. Die Startposition für die Berechnung eines Teileinzugsgebietes 
                         wird innerhalb der Fangtoleranz um den Knoten zum Punkt mit höchster Abflussakkumulation verschoben (m)
        min_area -- Minimale Fläche die ein Teileinzugsgebiet aufweisen soll (m2)
        method -- Methode mit der die Teileinzugsgebiete erstellt werden sollen ('1', '2', '3' oder '4')
        out_subcatchment -- Name der Output Feature-Klasse mit den Teileinzugsgebieten
        sim_nr -- Wird als Postfix für Log-Dateinamen und Feature-Klassen verwendet
    """   
    # Feature Dataset für temporäre Daten erstellen
    temp_dataset_name = "temp"
    temp_dataset_path = os.path.join(gisswmm_workspace, temp_dataset_name)
    if arcpy.Exists(temp_dataset_path):
        logger.info(f'Vorhande Feature-Dataset "{temp_dataset_name}" wird gelöscht')
        arcpy.management.Delete(temp_dataset_name)
    arcpy.management.CreateFeatureDataset(gisswmm_workspace, temp_dataset_name)

    # Ausagbefeature mit Nr. der Simulation ergänzen und Pfad zu Ausgabedataset definieren
    out_subcatchment = out_subcatchment + "_" + sim_nr
    sim_dataset_path = os.path.join(gisswmm_workspace, sim_nr)
    
    # Pfad des Input Höhenmodells (Raster)
    in_dhm_path = os.path.join(dhm_workspace, in_dhm)

    # Senken von DHM füllen
    out_surface_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_fill")
    if arcpy.Exists(out_surface_raster_path):
        logger.info(f'Raster "{out_surface_raster_path}" existiert bereits und wird nicht neu erstellt')
        out_surface_raster = out_surface_raster_path
    else:
        logger.info(f'Raster "{out_surface_raster_path}" erstellen')
        out_surface_raster = arcpy.sa.Fill(in_dhm_path, None)
        out_surface_raster.save(out_surface_raster_path)

    # Fliessrichtung berechnen
    out_flow_direction_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_flowdir")
    if arcpy.Exists(out_flow_direction_raster_path):
        logger.info(f'Raster "{out_flow_direction_raster_path}" existiert bereits und wird nicht neu erstellt')
        out_flow_direction_raster = out_flow_direction_raster_path
    else:
        logger.info(f'Raster "{out_flow_direction_raster_path}" erstellen')
        out_flow_direction_raster = arcpy.sa.FlowDirection(out_surface_raster, "NORMAL", None, "D8")
        out_flow_direction_raster.save(out_flow_direction_raster_path)        

    # Abflussakkumulation berechnen
    out_accumulation_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_flowaccu")
    if arcpy.Exists(out_accumulation_raster_path):
        logger.info(f'Raster "{out_accumulation_raster_path}" existiert bereits und wird nicht neu erstellt')
        out_accumulation_raster = out_accumulation_raster_path
    else:
        logger.info(f'Raster "{out_accumulation_raster_path}" erstellen')
        out_accumulation_raster = arcpy.sa.FlowAccumulation(out_flow_direction_raster, None, "FLOAT", "D8")
        out_accumulation_raster.save(out_accumulation_raster_path)        

    # Layer mit Schächten, für welche ein Teileinzugsgebiet berechnet werden soll (ohne Einlaufschächte), erstellen
    logger.info(f'Layer mit Schächten, für welche ein Teileinzugsgebiet berechnet werden soll, erstellen')
    out_node_lyr = 'out_node_lyr'
    where_node = ('"' + node_type + '"' + " <> " + f"'{type_inlet}'" )

    # Feature Layer mit den Schächten erstellen
    arcpy.management.MakeFeatureLayer(out_node, out_node_lyr, where_node)
 
    # Abflusspunkte zu den Schächten zuordnen (innerhalb snap_distance)
    out_pourpoint_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_pourpoint")
    logger.info(f'Raster "{out_pourpoint_raster_path}" erstellen')
    out_pourpoint_raster = arcpy.sa.SnapPourPoint(out_node_lyr, out_accumulation_raster, snap_distance, "OBJECTID")
    out_pourpoint_raster.save(out_pourpoint_raster_path)        

    # Topographische Teileinzugsgebiete erstellen (Raster)
    out_watershed_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_watershed")
    logger.info(f'Raster "{out_watershed_raster_path}" erstellen')
    out_watershed_raster = arcpy.sa.Watershed(out_flow_direction_raster, out_pourpoint_raster, "Value")
    out_watershed_raster.save(out_watershed_raster_path)        

    # Raster zu Polygon konvertieren
    subcatchment_ras2poly = "subcatchment_ras2poly"
    subcatchment_ras2poly_path = os.path.join(temp_dataset_path, subcatchment_ras2poly)
    logger.info(f'Raster "{out_watershed_raster_path}" zu Polygon {subcatchment_ras2poly} konvertieren')
    arcpy.conversion.RasterToPolygon(out_watershed_raster, subcatchment_ras2poly_path, "SIMPLIFY", "Value", "MULTIPLE_OUTER_PART", None)

    # Field-Mapping initialisieren
    fmap = arcpy.FieldMappings()
    fmap.addTable(subcatchment_ras2poly_path)
    # Liste mit allen Felder erstellen
    flds = fmap.fieldMappings
    fnames = {f.getInputFieldName(0) for f in flds}
    # Unnötige Felder entfernen
    del_fields = ["InPoly_FID", "SimPgnFlag", "MaxSimpTol", "MinSimpTol"]
    for del_field in del_fields:
        if del_field in fnames:
            arcpy.management.DeleteField(subcatchment_ras2poly_path, del_field)

    # Polygongeometrie vereinfachen damit die Geometrieobjekte nicht zu lange werden
    hyd_subcatchment = "hyd_subcatchment"
    hyd_subcatchment_path = os.path.join(temp_dataset_path, hyd_subcatchment)
    algorithm = "POINT_REMOVE"
    tolerance = "1 Meters"
    arcpy.cartography.SimplifyPolygon(subcatchment_ras2poly_path, hyd_subcatchment_path, algorithm, tolerance, "0 SquareMeters", 
                                     "RESOLVE_ERRORS", "KEEP_COLLAPSED_POINTS", None)
    
    # Felder zur Feature-Klasse mit den topograhische Teileinzugsgebieten hinzufügen, die in der Software "SWMM" benötigt werden.
    logger.info(f'Der Featureklasse "{hyd_subcatchment}" Felder hinzufügen')
    arcpy.management.AddField(hyd_subcatchment_path, "Name", "TEXT", field_length=128)
    arcpy.management.AddField(hyd_subcatchment_path, "Raingage", "TEXT", field_length=128)
    arcpy.management.AddField(hyd_subcatchment_path, "Outlet", "TEXT", field_length=128)
    arcpy.management.AddField(hyd_subcatchment_path, "Width", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "PercImperv", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "PercSlope", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "N_Imperv", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "N_Perv", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "S_Imperv", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "S_Perv", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "PctZero", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "Area", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "RouteTo", "TEXT", field_length=128)
    arcpy.management.AddField(hyd_subcatchment_path, "MaxRate", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "MinRate", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "Decay", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "DryTime", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "MaxInfil", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "MaxInfil", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "CurbLength", "FLOAT")
    arcpy.management.AddField(hyd_subcatchment_path, "SnowPack", "TEXT", field_length=128)
    arcpy.management.AddField(hyd_subcatchment_path, "coords", "TEXT", field_length=10000)


    # JOIN node on OBJECTID -> node ID Feld befüllen
    logger.info(f'Schächte und Teileinzugebiete miteinander joinen um den Teileinzugsgebieten die ID des Auslaufschachtes zu übergeben')
    out_subcatchment_node = arcpy.management.AddJoin(hyd_subcatchment_path, "gridcode", out_node, "OBJECTID", "KEEP_ALL", "NO_INDEX_JOIN_FIELDS")
    # Das Feld "Outlet" (Auslaufschacht) mit der ID der Schächte befüllen
    logger.info(f'Feld Outlet berechnen')
    expression = "!"+out_node+"."+node_id+"!"
    arcpy.management.CalculateField(out_subcatchment_node, 'Outlet', expression, "PYTHON3")    
    # Join entfernen
    arcpy.management.RemoveJoin(out_subcatchment_node, out_node)

    # Pfad zur Bodenbedeckung definieren
    in_land_path = os.path.join(land_workspace, in_land)

    ## 'Effektive' Teileinzugsgebiete ("out_subcatchment") erstellen
    # Methode "1": Liegenschaften als Teileinzugsgebiete
    # Methode "2": Liegenschaften zusätzlich mit Bodenbedeckung verschneiden
    # Methode "3": Topographische Teileinzugsgebiete verwenden
    # Methode "2": Topographische Teileinzugsgebiete zusätzlich mit Bodenbedeckung verschneiden
    logger.info(f'Teileinzugsgebiete mit Methode "{method}" erstellen')
    # Feature mit effektiven Teileinzugsgebiet löschen, falls bereits vorhanden
    if arcpy.Exists(out_subcatchment):
        logger.info(f'Bestehendes Feature "{out_subcatchment}" löschen')
        arcpy.management.Delete(out_subcatchment)

    logger.info(f'Feature "{out_subcatchment}" erstellen')
    # Feld "OBJECTID"
    objectid = "OBJECTID"
    # Pfad zu Feature-Klasse mit Liegenschaften (Parzellen) wird nur bei der Methode 1 und 2 benötigt
    if method == "1" or method =="2":
        in_parcel_path = os.path.join(parcel_workspace, in_parcel)
    # Geometrie der effektiven Teileinzugsgebiete definieren (="subcatchment_geom")
    if method == "1":
        # Die Geometrie der effektiven Teileinzugsgebiete entsprechen der Geometrie der Liegenschaften
        subcatchment_geom = in_parcel_path
    elif method == "2":
        # Bodenbedeckung mit Liegenschaften ausschneiden (Extend von Bodenbedeckungsfeature auf Untersuchungsgebiet anpassen)
        clip_land_parcel = "clip_land_parcel"
        clip_land_parcel_path = os.path.join(temp_dataset_path, clip_land_parcel)
        arcpy.analysis.Clip(in_land_path, in_parcel_path, clip_land_parcel_path)
        # Bodenbedeckung mit Liegenschaften verschneiden
        identity_land_parcel = "identity_land_parcel"
        identity_land_parcel_path = os.path.join(temp_dataset_path, identity_land_parcel)
        arcpy.analysis.Identity(clip_land_parcel_path, in_parcel_path, identity_land_parcel_path, "ALL")
        # Polygone mit geringer Fläche löschen
        del_small_polygons(identity_land_parcel_path, min_area)                                   
        # Die Geometrie der effektiven Teileinzugsgebiete entsprechen dem Verschnitt von den Liegenschaften mit der Bodenbedeckung
        subcatchment_geom = identity_land_parcel_path

    elif method == "3":
         # Die Geometrie der effektiven Teileinzugsgebiete entsprechen der Geometrie der topographischen Teileinzugsgebiete
        subcatchment_geom = hyd_subcatchment_path
    elif method == "4":
            # Bodenbedeckung mit topographischen Teileinzugsgebieten ausschneiden
            clip_land_hyd_subcatchment = "clip_land_hyd_subcatchment"
            clip_land_hyd_subcatchment_path = os.path.join(temp_dataset_path, clip_land_hyd_subcatchment)
            arcpy.analysis.Clip(in_land_path, hyd_subcatchment_path, clip_land_hyd_subcatchment_path)
            # Bodenbedeckung mit Teileinzugsgebieten verschneiden
            identity_land_hyd_subcatchment = "identity_land_hyd_subcatchment"
            identity_land_hyd_subcatchment_path = os.path.join(temp_dataset_path, identity_land_hyd_subcatchment)
            arcpy.analysis.Identity(clip_land_hyd_subcatchment_path, hyd_subcatchment_path, identity_land_hyd_subcatchment_path, "ALL")
            del_small_polygons(identity_land_hyd_subcatchment_path, min_area)  
            # Die Geometrie der effektiven Teileinzugsgebiete entsprechen dem Verschnitt der topographischen Teileinzugsgebiete mit der Bodenbedeckung
            subcatchment_geom = identity_land_hyd_subcatchment_path
    else:
        logger.error(f'Eingabeparameter "Methode" muss "1", "2", "3" oder "4" sein!')

    # Informationen aus topographischen Teileinzugsebieten extrahieren (="subcatchment_geom_hyd")
    if method == "1" or method == "2":
        # Geometrie der effektiven Teileinzugsgebiete mit topographischen Teileinzugsgbieten ausschneiden
        clip_geom_hyd_subcatchment = "clip_geom_hyd_subcatchment"
        clip_geom_hyd_subcatchment_path = os.path.join(temp_dataset_path, clip_geom_hyd_subcatchment)
        arcpy.analysis.Clip(subcatchment_geom, hyd_subcatchment_path, clip_geom_hyd_subcatchment_path)
        # Geometrie der effektiven Teileinzugsgebiete mit topographischen Teileinzugsgbieten verschneiden
        identity_geom_hyd_subcatchment = "identity_geom_hyd_subcatchment"
        identity_geom_hyd_subcatchment_path = os.path.join(temp_dataset_path, identity_geom_hyd_subcatchment)
        arcpy.analysis.Identity(clip_geom_hyd_subcatchment_path, hyd_subcatchment_path, identity_geom_hyd_subcatchment_path, "ALL")     
        # Polygone mit geringer Fläche löschen
        del_small_polygons(identity_geom_hyd_subcatchment_path, min_area)  
        subcatchment_geom_hyd = identity_geom_hyd_subcatchment_path
    else: 
        # Bei der Methode "3" und "4" sind die Informationen der topographischen Teileinzugsgebiete bereits vorhanden
        subcatchment_geom_hyd = subcatchment_geom

    # Informationen aus Bodenbedeckung extrahieren (="subcatchment_geom_hyd_land")
    if method == "1" or method == "3":
        ## Kennwerte in Abhängigkeit von Bodenbedeckung bestimmen
        clip_subcatchment_geom_hyd_land = "clip_subcatchment_geom_hyd_land"
        clip_subcatchment_geom_hyd_land_path = os.path.join(temp_dataset_path, clip_subcatchment_geom_hyd_land)
        # Bodenbedeckung mit subcatchment ausschneiden
        arcpy.analysis.Clip(in_land_path, subcatchment_geom_hyd, clip_subcatchment_geom_hyd_land_path)
        # Bodenbedeckung mit subcatchment verschneiden
        identitiy_subcatchment_geom_hyd_land = "identitiy_subcatchment_geom_hyd_land"
        identitiy_subcatchment_geom_hyd_land_path = os.path.join(temp_dataset_path, identitiy_subcatchment_geom_hyd_land)
        arcpy.analysis.Identity(clip_subcatchment_geom_hyd_land_path, subcatchment_geom_hyd, identitiy_subcatchment_geom_hyd_land_path, "ALL")
        # Polygone mit geringer Fläche löschen
        del_small_polygons(identitiy_subcatchment_geom_hyd_land_path, min_area)      
        subcatchment_geom_hyd_land = identitiy_subcatchment_geom_hyd_land_path
    else:
        # Bei der Methode "2" und "4" sind die Informationen aus der Bodenbedeckung bereits vorhanden
        subcatchment_geom_hyd_land = subcatchment_geom_hyd

    # Ausgabe Feature-Klasse mit effektiven Teileinzugsgebieten (out_subcatchment) erstellen
    arcpy.management.CreateFeatureclass(sim_dataset_path, out_subcatchment, template = hyd_subcatchment_path)

    # Felder der Ausgabefeature-Klasse 
    out_subcatchment_fields = ["SHAPE@", "Name", "Outlet", "PercImperv", "N_Imperv", "N_Perv", "S_Imperv", "S_Perv", "PctZero", "Raingage", "Area",
                               "RouteTo", "MaxRate","MinRate","Decay","DryTime","MaxInfil", "CurbLength", "coords"]
    # Insert-Cursor initialisieren
    cursor = arcpy.da.InsertCursor(out_subcatchment, out_subcatchment_fields)

    # Felder für "subcatchment_geom" cursor je nach Methode anpassen
    if method == "1":
        subcatchment_geom_fields = ["SHAPE@", objectid]
    elif method == "2":
        # Bei Methode 2 ist zusätzlich das Feld der Bodenbedeckungsart vorhaden
        # "Shape_Length" wird nur angegeben damit Indices mit Methode 4 übereinstimmen
        subcatchment_geom_fields = ["SHAPE@", objectid, "Shape_Length", "Shape_Area", mapping_land_imperv['in_field'] ] 
    elif method == "3":
        # Bei der Methode 3 ist zusätzlich das Feld "Outlet"  vorhanden
        subcatchment_geom_fields = ["SHAPE@", objectid, "Outlet", "Shape_Area"]
    elif method == "4":
        # Bei der Methode 4 ist zusätzlich ist das Feld "Outlet" und das Feld der Bodenbedeckungsart vorhanden
        subcatchment_geom_fields = ["SHAPE@", objectid, "Outlet", "Shape_Area", mapping_land_imperv['in_field']]

    # Durch alle Geometrien iterieren und effektive Teileinzugsgebiete erstellen
    with arcpy.da.SearchCursor(subcatchment_geom, subcatchment_geom_fields) as gcursor:
            for grow in gcursor:
                # Name der effektiven Teileinzugsgebiete = "s" + OBJECTID von subcatchment_geom
                shape = grow[0]
                name =  "s" + str(grow[1])
                ## Auslaufschacht ("Outlet") für jedes Teieinzugsgebiete bestimmen
                if method == "1" or method == "2":
                    # Bei der Methode 1 und 2 müssen die topographischen Informationen aus "subcatchment_geom_hyd" extrahiert werden
                    subcatchment_geom_hyd_lyr = arcpy.management.SelectLayerByLocation(subcatchment_geom_hyd, "WITHIN", grow[0], "", "NEW_SELECTION")
                    # Grösste Teileinzugsgebietseinheiten innerhalb des effektiven Teileinzugsgebiets 
                    max_area = 0
                    # Fläche effektives Teileinzugsgebiet initialisieren
                    sum_area = 0
                    # Auslaufschacht der grössten Teileinzugsgebietseinheiten innerhalb des effektiven Teileinzugsgebiets
                    outlet = None
                    # Durch alle topographischen Teileinzugsgebietseinheiten innerhalb des effektiven Teileinzugsgebiets iterieren 
                    with arcpy.da.SearchCursor(subcatchment_geom_hyd_lyr, ["Shape_Area", "Outlet"]) as scursor:
                        for srow in scursor:
                            # Fläche effektives aktualisieren
                            sum_area += srow[0]
                            if srow[0] > max_area and srow[1] is not None:
                                if len(srow[1])>0:
                                    # Für "outlet" den Wert des topographischen Teileinzugsgebietes mit der grössten Fläche innerhalb des effektiven Teileinzugsgebietes übernehmen
                                    max_area = srow[0]    
                                    outlet = srow[1]

                else:
                    # Fläche effektives Teileinzugsgebiet
                    sum_area = grow[3]
                    # Bei der Methode 3 und 4 ist die Information bereits in "subcatchment_geom" enthalten
                    outlet = grow[2]
                
                ## Kennwerte in Abhängigkeit der Bodenbedeckung extrahieren
                if method == "1" or method == "3":
                    # Bei der Methode 1 und 3 müssen die Kennwerte aus "subcatchment_geom_hyd_land" extrahiert werden                
                    subcatchment_geom_hyd_land_lyr = arcpy.management.SelectLayerByLocation(subcatchment_geom_hyd_land, "WITHIN", grow[0], "", "NEW_SELECTION")
                    # Gesamtfläche effektives Teileinzugsgebiet
                    sum_area_land = 0
                    # Summe "Imperv*Area" Werte pro effektives Teileinzugsgebiet
                    sum_imperv_area = 0
                    # Summe "Roughness*AreaImperv" Werte pro effektives Teileinzugsgebiet
                    sum_roughness_imperv_area = 0
                    # Summe "Roughness*AreaPerv" Werte pro effektives Teileinzugsgebiet
                    sum_roughness_perv_area = 0
                    # Summe "DepressionStorage*AreaImperv" Werte pro effektives Teileinzugsgebiet
                    sum_ds_imperv_area = 0
                    # Summe "DepressionStorage*AreaPerv" Werte pro effektives Teileinzugsgebiet
                    sum_ds_perv_area = 0    
                    # Werte extrahieren
                    with arcpy.da.SearchCursor(subcatchment_geom_hyd_land_lyr, ["Shape_Area", mapping_land_imperv['in_field']]) as scursor:
                        for row in scursor:
                            # Prüfen ob bereits ein Wert vorhanden
                            imperv = float(mapping_land_imperv['mapping'][str(row[1])])
                            roughness = float(mapping_land_roughness['mapping'][str(row[1])])
                            depression_storage = float(mapping_land_depression_storage['mapping'][str(row[1])])
                            sum_area_land += row[0]
                            sum_imperv_area += row[0] * imperv * 0.01
                            # Prüfen ob Imperv oder Perv
                            sum_roughness_imperv_area += row[0] * imperv * 0.01 * roughness
                            sum_ds_imperv_area += row[0] * imperv * 0.01 * depression_storage  
                            sum_roughness_perv_area += row[0] * (1-imperv*0.01) * roughness
                            sum_ds_perv_area += row[0]*(1-imperv*0.01) * depression_storage            

                    # Kennwerte berechnen
                    if sum_area_land>0:
                        PercImperv = sum_imperv_area / sum_area_land *100
                        if sum_imperv_area < sum_area_land:
                            N_Perv = sum_roughness_perv_area / (sum_area_land-sum_imperv_area)
                            S_Perv = sum_ds_perv_area / (sum_area_land-sum_imperv_area)
                        else:
                            N_Perv = 0
                            S_Perv =0
                        if sum_imperv_area>0:
                            N_Imperv = sum_roughness_imperv_area / sum_imperv_area
                            S_Imperv = sum_ds_imperv_area / sum_imperv_area
                        else:
                            N_Imperv = 0
                            S_Imperv = 0

                    else:
                        PercImperv = 0
                        N_Imperv = 0
                        N_Perv = 0
                        S_Imperv = 0
                        S_Perv = 0
                else:
                    # Bei der Methode 2 und 4 sind die Informationen zur Bodenbedeckung bereits in subcatchment_geom enthalten 
                    imperv = float(mapping_land_imperv['mapping'][str(grow[4])])
                    roughness = float(mapping_land_roughness['mapping'][str(grow[4])])
                    depression_storage = float(mapping_land_depression_storage['mapping'][str(grow[4])])
                    sum_area_land = grow[3]
                    sum_imperv_area = grow[3] * imperv * 0.01
                    PercImperv = imperv

                    if sum_area_land>0:
                        N_Imperv = roughness
                        N_Perv = roughness
                        S_Imperv = depression_storage
                        S_Perv = depression_storage            
                    else:
                        N_Imperv = 0
                        N_Perv = 0
                        S_Imperv = 0
                        S_Perv = 0 

                
                ## Restliche Kennwerte bestimmen
                # Annahme für %Zero-Imperv 
                PctZero = 25
                # Annahme nur eine Regenstation "RainGage" vorhanden (mögliche Erweiterung: Punktfeature als Input)
                Raingage = "RainGage"
                # m2 -> ha
                Area = sum_area/10000
                RouteTo = "OUTLET"
                MaxRate = infiltration["max_rate"]
                MinRate = infiltration["min_rate"]
                Decay = infiltration["decay"]
                DryTime = infiltration["dry_time"]
                MaxInfil = infiltration["max_infil"]
                CurbLength = 0 # Standardwert für curb length
                coords = []
                for part in shape:
                    for pnt in part:
                        if pnt:
                            coords.append((pnt.X,pnt.Y))
                coords = str(coords)

                # Teileinzugsgebiet nur hinzufügen falls outlet vorhanden
                if outlet:
                    cursor.insertRow([shape, name, outlet, PercImperv, N_Imperv, N_Perv, S_Imperv, S_Perv, PctZero, Raingage, Area,RouteTo, MaxRate,MinRate,Decay,DryTime,MaxInfil, CurbLength, coords])                                                                   

    del cursor

    ## Gebietsweite berechnen
    logger.info(f'Gebietsweite pro subcatchment berechnen')
    with arcpy.da.UpdateCursor(out_subcatchment, ["Shape_Area","Width"]) as ucursor:
        for urow in ucursor:
            urow[1] = math.sqrt(urow[0])
            ucursor.updateRow(urow)
    
    ## Steigung (Terraingefälle) berechnen
    out_slope_raster_path = os.path.join(out_raster_workspace, out_raster_prefix + "_slope")
    if arcpy.Exists(out_slope_raster_path):
        logger.info(f'Raster {out_slope_raster_path} existiert bereits und wird nicht neu erstellt')
        out_slope_raster = out_slope_raster_path
    else:
        logger.info(f'Raster {out_slope_raster_path} erstellen')
        out_slope_raster = arcpy.sa.Slope(out_surface_raster, "PERCENT_RISE", "", "PLANAR", )

    ## Extreme Steigungswerte entfernen damit alle Steigungen kleiner als 'max_slop'
    out_slope_raster_smooth_path = os.path.join(out_raster_workspace, out_raster_prefix + "_slope_max"+str(max_slope))        
    if arcpy.Exists(out_slope_raster_smooth_path):
        logger.info(f'Raster {out_slope_raster_smooth_path} existiert bereits und wird nicht neu erstellt')
        out_slope_raster_smooth = out_slope_raster_smooth_path
    else:
        logger.info(f'Raster {out_slope_raster_smooth_path} erstellen')
        # Extremwerte entfernen
        out_slope_raster_smooth = arcpy.sa.Con(out_slope_raster, out_slope_raster, max_slope, f"Value < {max_slope}")
        out_slope_raster_smooth.save(out_slope_raster_smooth_path)
        
    # Mittlere Steigung pro Teileinzugsgebiet berechnen
    logger.info(f'Mittlere Steigung (Terraingefälle) pro Einzugsgebiet berechnen')
    arcpy.sa.ZonalStatisticsAsTable(out_subcatchment, "Outlet", out_slope_raster_smooth, "slope_table", "DATA", "MEAN")

    # Tabelle mit Neigungswerte (slope_table) mit Teileinzugsgebieten (out_subcatchment) joinen
    logger.info(f'Join slope table zu subcatchment um Neigung pro Einzugsgebiet zu berechnen')
    out_subcatchment_slope = arcpy.management.AddJoin(out_subcatchment, "Outlet", "slope_table", "Outlet", "KEEP_ALL", "NO_INDEX_JOIN_FIELDS")
   
    # Attribut Slope berechnen
    logger.info(f'Feld PercSlope berechnen')
    expression = "!slope_table.MEAN!"
    arcpy.management.CalculateField(out_subcatchment_slope, 'PercSlope', expression, "PYTHON3")
    # Remove Join
    arcpy.management.RemoveJoin(out_subcatchment_slope, "slope_table")

    # Field-Mapping initialisieren
    fmap = arcpy.FieldMappings()
    fmap.addTable(out_subcatchment)
    # Liste mit allen Felder erstellen
    flds = fmap.fieldMappings
    fnames = {f.getInputFieldName(0) for f in flds}
    ## Unnötige Felder löschen
    for del_field in del_fields:
        if del_field in fnames:
            arcpy.management.DeleteField(out_subcatchment, del_field)

    # Temporäre Datensätze wieder löschen
    if arcpy.Exists("slope_table"):
        arcpy.management.Delete("slope_table") 


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
            # Die Methode mit welcher die Teileinzugsgebiete erstellt werden sollen ("1", "2", "3" oder "4")
            method  = data["subcatchment_method"]
            # Eine Distanz (m), die als Fangtoleranz für die Funktion "arcpy.sa.SnapPourPoint" verwendet wird. Die Funktion verschiebt die Knoten innerhalb dieser 
            # Distanz an die Position mit der grössten Abflussakkumulation, bevor die topographischen Teileinzugsgebiete von dieser Postion aus berechnet werden.
            snap_distance  = data["snap_distance"]
            # Eine minimale Fläche, die ein Teileinzugsgebiet aufweisen soll (m2).
            min_area  = float(data["min_area"])
            # Ein Dictionary mit der Art der Bodenbedeckung als "key" und "%imperviousness" als "value".
            mapping_land_imperv = data["mapping_land_imperv"]
            # Ein Dictionary mit der Art der Bodenbedeckung als "key" und "roughness" als "value".
            mapping_land_roughness = data["mapping_land_roughness"]
            # Ein Dictionary mit der Art der Bodenbedeckung als "key" und "depression storage" als "value".
            mapping_land_depression_storage = data["mapping_land_depression_storage"]
            # Ein Dictionary mit den Kennwerten zur Infiltration nach Horton (max_rate, min_rate, decay, dry_time, max_infil). 
            infiltration = data["infiltration"]
            # Der Pfad zum arcpy Workspace GISSWMM (.gdb) mit den Schächten (out_node), Haltungen (out_link) 
            # und der zu erstelltenden Output Feature-Klasse mit den Teileinzugsgebieten (out_subcatchment).
            gisswmm_workspace = data["gisswmm_workspace"]
            # Die arcpy Umgebungseinstellung "overwrite".
            if "overwrite" in data:
                overwrite = data["overwrite"]
            else: 
                overwrite = "True"
            # Der Name der Output Feature-Klasse mit den Teileinzugsgebieten (ohne Postfix "_sim_nr"!). 
            out_subcatchment = data["out_subcatchment"]
            # Der Name der Feature-Klasse mit den Schächten  (ohne Postfix '_sim_nr'!).
            out_node = data["out_node"]
            # Die Bezeichnung vom ID-Feld in der Feature-Klasse "out_node".
            node_id = data["node_id"]
            # Die Bezeichnung vom Feld mit dem Schachttyp in der Feature-Klasse "out_node". 
            node_type = data["node_type"]
            # Der Wert im Feld Schachttyp ("node_type"), welcher dem Einlaufschacht entspricht.
            type_inlet = data["type_inlet"]           
            # Der Pfad zum arcpy Workspace mit dem Höhenmodell (DHM).
            dhm_workspace = data["dhm_workspace"]
            # Der Name des DHM-Rasters im Workspace "dhm_workspace".
            in_dhm = data["in_dhm"]
            # Ein maximales Terraingefälle in %, das ein Teileinzugsgebiet haben soll.
            max_slope = data["max_slope"]   
            # Der Pfad zum arcpy Workspace mit der Bodenbedeckung. 
            land_workspace = data["land_workspace"]
            # Der Name des Bodenbedeckung-Rasters im Workspace "land_workspace".
            in_land = data["in_land"]
            # Der Workspace in welchem Output Rasterdaten gespeichert werden sollen.
            out_raster_workspace = data["out_raster_workspace"]
            # Ein Prefix für die Bezeichnung der Output Rasterdaten.
            if "out_raster_prefix" in data:
                out_raster_prefix = data["out_raster_prefix"]
            else:
                out_raster_prefix = "raster"
            if "parcel_workspace" in data:
                # Der Pfad zum arcpy Workspace mit den Parzellen (Liegenschaften). Wird bei den Methoden (subcatchment_method) "2" und "4" benötigt.
                parcel_workspace = data["parcel_workspace"]
                # Die Bezeichnung der Feature-Klasse mit den Parzellen im Workspace "parcel_workspace". 
                in_parcel = data["in_parcel"]
            else:
                parcel_workspace = None
                in_parcel = None

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
    
    # Bezeichnung der Output Raster-Dateien
    out_raster_prefix = out_raster_prefix + "_" + sim_nr + "_sd" + str(snap_distance).replace(".","_") 

    # Logging initialisieren
    filename = 'gisswmm_cre_subcatchments_' + sim_nr + '.log'
    log = os.path.join(log_folder, filename)
    logger= lf.init_logging(log)
    logger.info('****************************************************************')
    logger.info(f'Start logging: {time.ctime()}')
    start_time = time.time()

    # Aktuelle Workspace definieren
    arcpy.env.workspace = gisswmm_workspace

    postfix = "_" + sim_nr
    if not postfix in out_node:
        out_node = out_node + postfix
    if not arcpy.Exists(out_node):
        err_txt = f'Die angegebene Feature-Klasse {out_node} ist nicht vorhanden!'
        logger.error(err_txt)
        raise ValueError(err_txt)  

    # Koordinatensystem
    spatial_ref = arcpy.Describe(out_node).spatialReference

    # Main module aufrufen
    with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
        main(dhm_workspace, in_dhm, max_slope, parcel_workspace, in_parcel, land_workspace, in_land, mapping_land_imperv, 
             mapping_land_roughness, mapping_land_depression_storage, infiltration, out_raster_workspace, out_raster_prefix, 
             gisswmm_workspace, out_node, node_id, node_type, type_inlet, snap_distance, min_area, method, out_subcatchment, sim_nr)

    # Logging abschliessen
    end_time = time.time()
    i = lf.search_in_file(log, "error")
    logger.info("Skript Laufzeit: " + str(round(end_time - start_time)) + " sec.")
    logger.info(str(i) + " Fehler gefunden. Check Log.")
    endtime = time.ctime()
    logger.info(f'End time: {time.ctime()}')
    logger.info('****************************************************************\n')


