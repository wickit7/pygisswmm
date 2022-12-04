# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 19.11.2021
#
# Erstellung Topologie: Leitungen werden bei Einlaufknoten (Schnittpunkt von zwei Haltungen) 
# aufgetrennt um eine Knoten-Haltung-Knoten Topologie zu erhalten. Die Bezeichnung von 
# getrennten Haltungen wird mit einem Postfix (ID+"_Nr") ergänzt/nummeriert.
#
# Deckelkote: Für die Knoten werden fehlende Deckelkoten aus einem Höhenmodell extrahiert.
#
# Interpolation Sohlenkote: Für einen Knoten ohne Sohlenkote werden alle oberliegenden und 
# unterliegenden Stränge verfolgt bis jeweils zu einem Knoten mit einer Sohlenkote. 
# Anschliessend wird stellvertretend für alle oberliegenden und unterliegenden Knoten durch 
# Mittelung je einen Surrogat-Knoten (stellvertretender Knoten) erstellt. Zwischen  dem oberliegenden 
# und unterliegenden Surrogat-Knoten wird anschliessend das  Gefälle  berechnet und daraus die Sohlenkote 
# des aktuellen Knotens berechnet. Falls Sohlenkoten nur bei oberliegenden oder unterliegenden Knoten 
# bekannt sind, werden die Stränge, die einen Knoten mit Sohlenkote aufweisen, bis zu einem 
# zweiten Knoten mit bekannter Sohlenkote verfolgt. Danach wird das mittlere Gefälle dieser Stränge 
# berechnet. Aufgrund des mittleren Gefälles wird ausgehend vom Surrogat-Knoten die Sohlenkote des 
# aktuellen Knotens berechnet. Bei der Interpolation wird zunächst nur das primäre Netz (PAA) 
# berücksichtigt, da das primäre Netz entlang einem konstanteren Gefälle verläuft (z. B. entlang Strasse) 
# und die Daten oft genauer sind als im sekundären Netz (SAA). In einem zweiten Schritt werden die 
# Sohlenkoten des sekundärenNetzes mithilfe des gesamten Netzes interpoliert. Die Sohlenkote der Einläufe 
# werden jeweils als letztes berechnet. Dies gewährleistet, dass bei Einläufen keine Gefällsänderung auftritt.
# Nachdem die Sohlenkote von allen Schächten bekannt ist wird das Gefälle der Haltungen berechnet. 
#
# Die Input-Parameter werden in einer JSON-Datei angegeben, die als Eingabe dem Skript übergeben wird.
#  -----------------------------------------------------------------------------
"""gisswmm_upd"""
import os, sys, time, json
import arcpy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '0_BasicFunctions'))
import logging_functions as lf
import basic_functions as bf

## Funktionen für die Berechnung der Deckelkote
def main_shaftheight(in_node, node_dk, dhm_workspace, in_dhm, tag):
    """Input-Daten aufbereiten und Funktionen für die Berechnung der Deckelkote aufrufen

    Required:
        in_node -- Name der Input Feature-Klasse mit den Knoten (Schächten)
        node_dk -- Bezeichnung von Input Feld mit Deckelkote
        dhm_workspace -- Pfad zu arcpy Workspace mit DHM (.gdb)
        in_dhm -- Name des DHM-Rasters
    Optional:
        tag -- Text für tag-Feld welcher bei Schächten mit berechneter Deckelkote hinzugefügt wird
    """   
    # Feature-Klasse zu Layer konvertieren
    logger.info(f'Feature-Klasse zu Layer konvertieren')
    in_node_lyr = 'in_node_lyr'
    arcpy.management.MakeFeatureLayer(in_node, in_node_lyr)

    # Pfad des Input Höhenmodells (Raster)
    in_dhm_path = os.path.join(dhm_workspace, in_dhm)

    # Name von neuen Feld mit den extrahierten Rasterwerten
    node_dk_dhm  = node_dk.lower() + "_dhm" 

    # Prüfen ob Felder vorhanden sind
    fnames =  [field.name for field in arcpy.ListFields(in_node)]
    node_tag = "tag"
    if node_dk_dhm in fnames:
        logger.info(f'Vorhandenes Feld Deckelkote berechnet löschen')
        arcpy.management.DeleteField(in_node, node_dk_dhm)
    if node_tag not in fnames:
        logger.info(f'tag-Feld erstellen')
        arcpy.AddField_management(in_node, node_tag, "TEXT", field_length=40)

    # Werte aus Raster extrahieren 
    logger.info(f'Werte aus Höhenmodell extrahieren')
    # ArcGIS env setting "preserveGlobalIds=True" bei dieser Funktion nicht vorhanden, deshalb GlobalID zu Textfeld konvertieren
    arcpy.sa.ExtractMultiValuesToPoints(in_node_lyr, [[in_dhm_path, node_dk_dhm]], 'NONE')

    # Attributbezogene Selektion (Schächte ohne Deckelkote)
    logger.info(f'Attributbezogene Selektion durchführen')
    arcpy.management.MakeFeatureLayer(in_node, in_node_lyr)
    where = '"' + node_dk + '"' + " IS NULL" 
    arcpy.management.SelectLayerByAttribute(in_node_lyr, 'NEW_SELECTION', where, 'NON_INVERT')
    # Deckelkote berechnen
    logger.info(f'Fehlende Deckelkoten abfüllen')
    expression_dk = "!"+node_dk_dhm+"!"
    arcpy.management.CalculateField(in_node_lyr, node_dk, expression_dk, "PYTHON3")    
    logger.info(f'Tag abfüllen')
    bf.append_text(in_node_lyr, node_tag, tag)

## Funktionen für die Erstellung der Haltung-Knoten-Haltung Topologie
def main_topology(in_node, node_id, node_to_link, node_type, type_inlet, in_link, link_id, link_from, 
                  link_to, link_length, delete = True):
    """Input-Daten aufbereiten und Funktionen für die Erstellung der Topologie aufrufen

    Required:
        in_node -- Name der Input Feature-Klasse mit den Schächten
        node_id -- Bezeichnung von ID-Feld der Schächte
        node_to_link -- Bezeichnung von Feld mit ID der Haltung auf welcher der Einlaufschacht liegt
        node_type -- Bezeichnung vom Feld in welchem der Schachttyp angegeben wird
        type_inlet -- Wert von Schachttyp ('node_type') der dem Einlaufschacht entspricht
        in_link -- Name der Feature-Klasse mit den Haltungen
        link_id -- Bezeichnung von ID-Feld der Haltungen
        link_from -- Bezeichnung von Feld mit ID von Von-Schacht
        link_to -- Bezeichnung von Feld mit ID von Bis-Schacht
        link_length -- Bezeichnung von Feld mit Haltungslänge

    Optional:
        delete -- Falls True werden Schächte und Haltungen gelöscht, die nicht am Netz angeschlossen sind.
                  Ebenfalls werden Einlausschächte ohne zugehörige Haltungen gelöscht. 
    """   
    logger.info('Haltungen mit selben Von- und Bis-Schacht aktualisieren')
    where_link = ('"' + link_from + '"' +" = " + '"' + link_to + '"')   
    with arcpy.da.UpdateCursor(in_link, [link_id, link_from, link_to], where_link) as ucursor:
        for urow in ucursor:
            logger.warning(f'Haltung mit ID {urow[0]} hat den selben Von- und Bis-Schacht! Von-Schacht wird auf Null gesetzt')
            urow[1] = None
            ucursor.updateRow(urow)

    # Haltungen löschen die keinen vorhandenen Von- oder Bis-Schacht aufweisen
    if delete:
        node_id_list = [row[0] for row in arcpy.da.SearchCursor(in_node, node_id)]
        logger.info('Haltungen ohne Von- oder Bis-Schacht löschen')
        where_link = ('"' + link_from + '"' +" NOT IN " + str(node_id_list).replace("[","(").replace("]",")") + " OR " + 
                    '"' + link_to + '"' +" NOT IN " + str(node_id_list).replace("[","(").replace("]",")"))
        cnt = 0
        with arcpy.da.UpdateCursor(in_link, link_id, where_link) as dcursor:
            for drow in dcursor:
                logger.warning(f'Haltung mit ID {drow[0]} wird gelöscht')
                dcursor.deleteRow() 
                cnt += 1 
        logger.info(f'{cnt} Haltungen ohne Von- oder Bis-Schacht wurden gelöscht')

    # Listen mit Von- und Bis-Schächten
    logger.info('Listen mit Von- und Bis-Schächten erstellen')
    link_from_list = []
    link_to_list = []
    with arcpy.da.SearchCursor(in_link, [link_from, link_to]) as cursor:
        for row in cursor:
            link_from_list.append(row[0])
            link_to_list.append(row[1])

    # Schächte die weder ein Von- noch ein Bis-Schacht sind löschen
    if delete:
        logger.info('Schächte die weder Von- noch Bis-Schacht einer Haltung sind löschen')
        where_node = ('"' + node_id + '"' +" NOT IN " + str(link_from_list).replace("[","(").replace("]",")") + " AND " +
                    '"' + node_id + '"' +" NOT IN " + str(link_to_list).replace("[","(").replace("]",")") )
        cnt = 0
        with arcpy.da.UpdateCursor(in_node, node_id, where_node) as dcursor:
            for drow in dcursor:
                logger.warning(f'Schacht mit ID {drow[0]} wird gelöscht')
                dcursor.deleteRow()
                cnt += 1
        logger.info(f'{cnt} Schächte ohne zugehehörige Haltungen wurden gelöscht')

        # Einlaufschächte ohne zugehörige Haltung löschen
        logger.info('Einlaufschächte ohne Von-Schacht löschen')
        where_node = ('"' + node_type + '"' + " = "+ "'" + type_inlet + "'"+ " AND " + 
                    '"' + node_id + '"' +" NOT IN " + str(link_to_list).replace("[","(").replace("]",")") )
        cnt = 0
        with arcpy.da.UpdateCursor(in_node, node_id, where_node) as dcursor:
            for drow in dcursor:
                logger.warning(f'Einlaufschacht mit ID {drow[0]} wird gelöscht')
                dcursor.deleteRow()
                cnt += 1
        logger.info(f'{cnt} Einlaufschächte ohne Von-Schacht wurden gelöscht')

    # Einflaufschächte die eine zugehörige Haltung aufweisen und die referenzierte Einlauf-Haltung noch nicht getrennt ist
    logger.info('Layer mit relevanten Einlaufschächten erstellen')
    where_node = ('"' + node_type + '"' + " = " + "'"+ type_inlet + "'" + " AND " + 
                '"' + node_id + '"' +" NOT IN " + str(link_from_list).replace("[","(").replace("]",")") + " AND " +
                '"' + node_id + '"' +" IN " + str(link_to_list).replace("[","(").replace("]",")") )
    in_node_lyr = 'in_node_lyr'
    arcpy.management.MakeFeatureLayer(in_node, in_node_lyr, where_node)

    # Liste mit ID's der Schächte und ID's der Haltungen in welche die Schächte übergehen
    logger.info('Liste mit den IDs der relevanten Schächte und Haltungen erstellen')
    node_id_list = []
    node_to_link_list = []
    with arcpy.da.SearchCursor(in_node_lyr, [node_id, node_to_link]) as cursor:
        for row in cursor:
            node_id_list.append(row[0])
            node_to_link_list.append(row[1])

    logger.info('Durch alle relevanten Schächte iterieren')
    cnt_deleted = 0
    cnt_updated = 0
    for ii, nid in enumerate(node_id_list):
            # Spezifischer Schacht auswählen
            logger.info(f'Haltungen mit Schacht {nid} trennen')
            where_node = '"' + node_id + '"' +" = " + f"'{nid}'"  
            arcpy.management.MakeFeatureLayer(in_node, in_node_lyr, where_node)
            
            # Haltungen auswählen, welche möglicherweise getrennt werden müssen 
            # ("LIKE" da ID evtl. bereits mit postifix "_u" oder "_l" aktualisiert wurde)
            where_link = '"' + link_id + '"'+" LIKE " + f"'{node_to_link_list[ii]}%'"
            in_link_lyr = 'in_link_lyr'
            arcpy.management.MakeFeatureLayer(in_link, in_link_lyr, where_link)

            # Haltungen mit dem spezifischen Schacht splitten 
            link_splited = "link_splited"
            arcpy.management.SplitLineAtPoint(in_link_lyr, in_node_lyr, link_splited, "0.1 Meters")

            # Feature-Layer von getrennten Haltungen erstellen
            link_splited_lyr = "link_splited_lyr"
            arcpy.management.MakeFeatureLayer(link_splited, link_splited_lyr)
            # Die zwei Haltungen auswählen, welche tatsächlich betroffen sind (da evtl. mehrere Enläufe pro Haltung)
            arcpy.management.SelectLayerByLocation(link_splited_lyr, "INTERSECT", in_node_lyr, "0.1 Meters", 
                                                    "SUBSET_SELECTION", "NOT_INVERT")

            # ObjectIDs der betroffenen Haltungen
            link_objectid_list = [row[0] for row in arcpy.da.SearchCursor(link_splited_lyr, "OBJECTID")]
            
            if len(link_objectid_list) == 0:
                # Einlaufschacht auf keiner Haltung -> löschen
                logger.info('Schacht befindet sich auf keiner Haltung')
                with arcpy.da.UpdateCursor(in_node, node_id, where_node) as dcursor:
                    for drow in dcursor:
                        logger.warning(f'Schacht mit ID {drow[0]} wird gelöscht')
                        dcursor.deleteRow()
                        cnt_deleted += 1
                continue
            elif len(link_objectid_list) < 2:
                # Trennen nicht notwendig
                logger.info('Schacht liegt nur auf einer Haltung, keine Aktualisierung notwendig')
                continue

            # Bis Schacht auswählen um die Reihenfolge (Fliessrichtung) herauszufinden
            node_to = [row[0] for row in arcpy.da.SearchCursor(link_splited_lyr, link_to)][0]
            # Layer mit Bis-Schacht erstellen
            where_node = '"' + node_id + '"' +" = " + f"'{node_to}'"  
            arcpy.management.MakeFeatureLayer(in_node, in_node_lyr, where_node)
            # Haltung auswählen die bei Bis-Schacht liegt
            arcpy.management.SelectLayerByLocation(link_splited_lyr, "INTERSECT", in_node_lyr, "0.1 Meters", 
                                                    "SUBSET_SELECTION", "NOT_INVERT")
            link_objectid_lower = [row[0] for row in arcpy.da.SearchCursor(link_splited_lyr, "OBJECTID")][0]

            for objectid in link_objectid_list:
                if objectid != link_objectid_lower:
                    link_objectid_upper = objectid
            
            # Erneut Haltungen auswählen, welche aktualisiert werden müssen
            where_link = '"' + "OBJECTID" + '"'+" IN " + str(link_objectid_list).replace("[","(").replace("]",")")
            in_link_lyr = 'in_link_lyr'
            arcpy.management.MakeFeatureLayer(link_splited, in_link_lyr, where_link)
            # Originale 'link_id'
            link_id_orig = [row[0] for row in arcpy.da.SearchCursor(in_link_lyr, link_id)][0]

            logger.info('Die zwei neuen Haltungen aktualiseren')
            # Die zwei neuen Haltungen aktualiseren
            with arcpy.da.UpdateCursor(in_link_lyr, ["OBJECTID", link_id, link_from, link_to, link_length, "SHAPE@LENGTH"]) as ucursor:
                for urow in ucursor:
                    if urow[0] == link_objectid_lower:
                        # Link id anpassen
                        urow[1] = urow[1] + "_l"
                        # Von-Schacht anpassen
                        urow[2] = nid
                        # Länge anpassen
                        urow[4] = urow[5]
                        
                    elif urow[0] == link_objectid_upper:
                        # Link id anpassen
                        urow[1] = urow[1] + "_u"
                        # Von-Schacht anpassen
                        urow[3] = nid
                        # Länge anpassen
                        urow[4] = urow[5]
                    
                    else:
                        logger.warning(f'Trennung bei Schacht {nid} führte unerwartet zu mehr als zwei neuen Haltungen!')

                    ucursor.updateRow(urow)
                    cnt_updated += 1

            logger.info(f'Ursprüngliche Haltung {link_id_orig} löschen')
            # Ursprüngliche Haltung löschen
            where_link = '"' + link_id + '"'+" = " + f"'{link_id_orig}'"
            with arcpy.da.UpdateCursor(in_link, link_id, where_link) as dcursor:
                for urow in dcursor:
                    dcursor.deleteRow()
            
            # Neue Haltungen hinzufügen
            logger.info('Neue Haltungen hinzufügen')
            arcpy.management.Append(in_link_lyr, in_link, 'NO_TEST')
            
            # Temporäre Feature Klasse mit getrennten Haltungen löschen
            logger.info('Temporäre Feature-Klasse mit getrennten Haltungen löschen')
            arcpy.management.Delete(link_splited)

    logger.info(f'{cnt_deleted} Schächte wurden gelöscht')
    logger.info(f'Bei {cnt_updated} Einlaufschächten wurde die Haltung getrennt')

    # Aktualisierte Listen mit Von- und Bis-Schächten
    logger.info('Listen mit aktualisierten Von- und Bis-Schächten erstellen')
    link_from_list = []
    link_to_list = []
    with arcpy.da.SearchCursor(in_link, [link_from, link_to, link_id]) as cursor:
        for row in cursor:
            link_from_list.append(row[0])
            link_to_list.append(row[1])
    
    # Feld 'OutfallType' (Auslaufschacht) hinzufügen
    outfall_type = "OutfallType"
    arcpy.management.AddField(in_node, outfall_type, "TEXT", field_length=128)

    # Auslaufschächte definieren
    logger.info('Auslaufschächte definieren')
    cnt = 0
    with arcpy.da.UpdateCursor(in_node, [node_id, node_type, outfall_type]) as ucursor:
        for urow in ucursor:
            if urow[0] not in link_from_list:
                urow[1] = "OUTFALL"
                # Annahme Typ = FREE
                urow[2] = "FREE"
                cnt += 1
                ucursor.updateRow(urow)

    logger.info(f'{cnt} Schächte wurden als Auslaufschächte definiert')


## Funktionen für die Interpolation der Sohlenkote
def _update_current_branch(node_dict, branch, link_ref, link_node, max_nr):
    """Hilfsfunktion der Funktion _update_current_branches
    
    Verfolgt einen spezifischen Kanalnetz-Strang um einen Schritt.

    Return:
        Aktuallisierter Strang
    """
    # Aktuelle Länge des Stranges
    current_length = branch['length']
    branchs = []
    # prüfen ob der Schacht oberhalb bzw. unterhalb Haltungen hat
    if len(node_dict[branch['node_id']][link_ref])>0:
        # Durch oberliegende bzw. unterliegende Haltungen iterieren
        for ii, link in enumerate(node_dict[branch['node_id']][link_ref]):
            new_branch = branch.copy()
            new_branch['length'] = current_length + link['link_length']
            # Strang mit oberhalb bzw. unterhalb liegenden Schacht aktualisieren
            new_branch['node_id'] = link[link_node]         
            # Prüfen ob der neue Schacht eine Sohlenkote aufweist
            try:
                if node_dict[link[link_node]]['node_sk']:
                    # Sohlenkote aktualisieren
                    new_branch['sk'] = node_dict[link[link_node]]['node_sk']
                    # Strang wird nicht mehr weiterverfolgt
                    new_branch['finished'] = True
            except KeyError:
                logger.warning(f'Schacht mit ID {link[link_node]} ist nicht vorhanden.'
                               f' Verfolgung des Stranges wird abgebrochen')
                new_branch['finished'] = True
            if ii == 0:
                # Erster Strang ist Fortsetzung des aktuellen Stranges
                # Strang Nummer aktualisieren falls zusätzliche Stränge dazukommen
                branch_up_nr = max_nr
            else:
                new_branch['nr'] = branch_up_nr
                # Strang Nummer aktualisieren falls zusätzliche Stränge dazukommen
                branch_up_nr += 1     
            # Strang hinzufügen
            branchs.append(new_branch)
    else:
        # Ende des Stranges erreicht falls oberhalb bzw. unterhalb keine Haltungen mehr vorhanden sind.
        branch['finished'] = True
        branchs.append(branch)

    return branchs


def _update_current_branches(node_dict, branchs, link_ref, link_node):
    """Hilfsfunktion der Funktion get_interpolated_sk
    
    Verfolgt alle Kanalnetz-Stränge (branchs) um einen Schritt.

    Return:
        Aktuallisierte Stränge
    """
    new_branchs = branchs.copy()
    for branch in branchs:
        if branch['finished']:
            branchs_updated = [branch]
        else:
            branchs_updated = _update_current_branch(node_dict, branch, link_ref, link_node, len(new_branchs))
        for branch_updated in branchs_updated:
            if branch_updated['nr']<len(branchs):
                new_branchs[branch_updated['nr']]=branch_updated
            else:
                new_branchs.append(branch_updated)
    return new_branchs


def  _create_surrogat(branchs):
    """Hilfsfunktion der Funktion get_interpolated_sk

    Required:
        branchs: Liste mit den Dictionaries von alle Strängen für die ein Surrgat-Schacht
                 erstellt werden soll.
    Return:
        Dictionary mit Sohlenkote des Surrogat-Schachtes, mittlerer Haltungslänge und minimaler 
        und maximaler Sohlenkote des Stranges
    """
    tot_length = 0
    sk_norm = 0
    sum_weights = 0
    nr = 0
    sk_min = None
    sk_max = None
    # Gesamtlänge  und längengenormte Sohlenkote berechnen
    for branch in branchs:
        if branch['sk']:
            tot_length += branch['length']
            sk_norm += branch['sk']/branch['length']
            sum_weights += 1/branch['length']
            if nr>0:
                sk_min = min(sk_min, branch['sk'])
                sk_max = max(sk_max, branch['sk'])
            else:
                sk_max = branch['sk']
                sk_min = branch['sk']
            nr += 1      
    if nr>0:
        # Längengewichtete Sohlenkote berechnen
        sk = sk_norm/sum_weights
        # Durchschnittliche Länge berechnen
        length = tot_length/nr
        return {"sk":sk, "length":length, "sk_min": sk_min, "sk_max": sk_max}
    else:
        return None

def get_interpolated_sk(node_dict, id_node, mean_slope = 0.01, mean_depth = 1, min_depth = 0.3):
    """Sohlenkote für einen bestimmten Schacht mit Berücksichtigung der Topologie berechnen.

    Required:
        node_dict -- Dictionary mit den Informationen zu allen Schächten inklusive Informationen
            über die Topolgie. Der Dictionary muss folgendes Schema aufweisen:
            "{ID Schacht: {'node_sk': Sohlenkote, 'node_dk': Deckelkote, 'links_up': [{'link_id': ID Link, 'link_from': 
            ID Von-Schacht, 'link_to': ID Bis-Scacht, 'link_length': Länge der Haltung},...], 
            'links_down': [{'link_id': ID Link, 'link_from': ID Von-Schacht, 'link_to': ID Bis-Schacht, 
            'link_length': Länge der Haltung},...]}". Die ID's der Schächte werden als Key verwendet.
            Bei 'links_up' handelt es sich um eine Liste mit den Haltungen, welche in den Schacht hinein führen.
            Bei 'links_down' handelt es sich um eine Liste mit den Haltungen, welche aus dem Schacht führen.
        id_node -- ID des Schachtes für welchen die Sohlenkote berechnet werden soll.
        mean_slope -- Diese Steigung wird für die Berechnung der Sohlenkote verwendet, falls entlang eines Stranges 
            nur eine einzige Sohlenkote bekannt ist.
        mean_depth -- Diese Schachttife wird für die Berechnung der Sohlenkote verwendet, falls entlang eines Stranges
            keine einzige Sohlenkote bekannt ist.
        min_depth -- Prüft ob die Schachttiefe mindestens diesem Wert entspricht, ansonsten wird die Sohlenkote angepasst

    Return:
        sk -- Berechnete Sohlenkote
    """
    # Deckelkote des Schachtes
    dk = node_dict[id_node]['node_dk']
    # Erster Strang oberhalb des aktuellen Schachtes initialisieren
    branchs_up = [{'nr':0, 'node_id': id_node, 'length':0, 'sk':None,'finished':False}]
    finished_up = False
    while not finished_up:
        # Alle Stränge aktualisieren
        branchs_up = _update_current_branches(node_dict, branchs_up, 'links_up', 'link_from')
        # Kontrollieren ob alle oberliegende Stränge Ende erreicht haben
        finished_up = True
        for branch in branchs_up:
            if not branch['finished']:
                # Falls ein Strang noch nicht fertig is weiter iterieren
                finished_up = False

    # Alle Stränge unterhalb verfolgen
    # Erster Strang unterhalb des aktuellen Schachtes initialisieren
    branchs_down = [{'nr':0, 'node_id': id_node, 'length':0, 'sk':None, 'finished':False}]
    finished_down = False
    while not finished_down:
        branchs_down = _update_current_branches(node_dict, branchs_down, 'links_down', 'link_to')
        # Kontrollieren ob alle unterliegenden Stränge Ende erreicht haben
        finished_down = True
        for branch in branchs_down:
            if not branch['finished']:
                # Falls ein Strang noch nicht fertig is weiter iterieren
                finished_down = False
    
    # Oberhalb liegender Surrogat-Schacht erstellen
    surrogat_up = _create_surrogat(branchs_up)
    # Unterhalb liegender Surrogat-Schacht erstellen
    surrogat_down = _create_surrogat(branchs_down) 

    # Sohlenkote berechnen
    if surrogat_up and surrogat_down:
        sk = surrogat_down['sk'] + (surrogat_up["sk"]-surrogat_down['sk'])/(surrogat_up["length"]+surrogat_down['length'])*surrogat_down['length']
        # Mit folgender Anpassung positive Steigung in Fliessrichtung vermeiden 
        # Annahme: Falls durch folgende Anpassung die postive Steigung vermieden werden kann ist in Realität keine Druckleitung vorhanden
        # Prüfen ob berechnete Sohlenkote tiefer als minimale Sohlenkote oberhalb oder tiefer als maximale Sohlenkote unterhalb ist
        if sk > surrogat_up["sk_min"] or sk < surrogat_down["sk_max"]:
            # Anpassung nur vornehmen falls dadurch Bedingung eingehalten werden kann 
            if surrogat_up["sk_min"] > surrogat_down["sk_max"]:
                # Annahme Sohlenkote liegt zwischen den beiden Extremwerten
                logger.warning(f'Um eine positive Steigung in Fliessrichtung zu verweiden wird beim Schacht mit der ID {id_node} die berechnete'
                               f' Sohlenkote von {sk} auf {(surrogat_up["sk_min"] + surrogat_down["sk_max"])/2} (zwischen Extremwerten) angepasst.')
                sk = (surrogat_up["sk_min"] + surrogat_down["sk_max"])/2
   
    elif surrogat_up:
        # Für jeden oberliegenden Strang einen zweiten Schacht mit sk suchen um mittlere Steigung zu berechnen
        finished_up = False
        for branch in branchs_up:
            # Alle Stränge die einen Schacht mit Sohlenkote haben weiter verfolgen
            if branch["sk"]:
                # Stränge mit aktualiseren damit anschliessend Steigung berechnet werden kann
                branch["finished"]=False
                # Sohlenkote des ersten Schachtes mit Sohlenkote
                branch["sk_first"]=branch["sk"]
                # Sohlenkote des zweiten Schachtes mit Sohlenkote suchen
                branch["sk"]=None
                # Länge zu erstem Schacht mit Sohlenkote 
                branch["length_first"]=branch["length"]
                # Länge von erstem Schacht bis zu zweitem Schacht mit Sohlenkote suchen
                branch["length"]=0
        while not finished_up:    
            branchs_up = _update_current_branches(node_dict, branchs_up, 'links_up', 'link_from')
            # Kontrollieren ob alle oberliegende Stränge Ende erreicht haben
            finished_up = True
            for branch in branchs_up:
                if not branch['finished']:
                    # Falls ein Strang noch nicht fertig ist weiter iterieren
                    finished_up = False
        # Steigung für jeden Strang berechnen
        nr_slope = 0
        slope_sum = 0
        for branch in branchs_up:
            if branch["sk"]:
                branch["slope"] = (branch["sk_first"]-branch["sk"])/branch["length"]
                slope_sum += branch["slope"]
                nr_slope += 1
        if nr_slope>0:
            sk = surrogat_up["sk"] + slope_sum/nr_slope*surrogat_up["length"]
        else:
            # Falls kein zweiter Schacht mit Sohlenkote gefunden wird. Definierte mittlere negative Steigung annehmen.
            sk = surrogat_up["sk"] - mean_slope*surrogat_up["length"]

        # Mit folgender Anpassungen positive Steigung in Fliessrichtung vermeiden 
        # Annahme: Falls durch folgende Anpassung die postive Steigung vermieden werden kann, handelt es sich nicht um eine Druckleitung.
        # Prüfen ob Steigung in Fliessrichtung negativ ist, falls Sohlenkote mit Deckelkote und definierter mittlerer Schachttiefe berechnet wird
        if sk >= surrogat_up["sk_min"]:
            # Anpassung nur vornehmen falls dadurch Bedingung eingehalten werden kann 
            if (dk - mean_depth) < surrogat_up["sk_min"]:
                # Sohlenkote mit defnierter mittlerer Schachttiefe berechnen
                logger.warning(f'Um eine positive Steigung in Fliessrichtung zu verweiden wird beim Schacht mit der ID {id_node} die berechnete'
                               f' Sohlenkote von {sk} auf {dk- mean_depth} (Deckelkote - mean_depth) angepasst.')
                sk = dk - mean_depth

    elif surrogat_down:
        # Für jeden unterliegenden Strang einen zweiten Schacht mit Sohlenkote (sk) suchen um mittlere Steigung berechnen
        finished_down = False
        for branch in branchs_down:
            # Alle Stränge die einen Schacht mit Sohlenkote haben weiter verfolgen
            if branch["sk"]:
                # Stränge mit aktualiseren damit anschliessend Steigung berechnet werden kann
                branch["finished"]=False
                # Sohlenkote des ersten Schachtes mit Sohlenkote
                branch["sk_first"]=branch["sk"]
                # Sohlenkote des zweiten Schachtes mit Sohlenkote suchen
                branch["sk"]=None
                # Länge zu erstem Schacht mit Sohlenkote 
                branch["length_first"]=branch["length"]
                # Länge von erstem Schacht bis zu zweitem Schacht mit Sohlenkote suchen
                branch["length"]=0
        while not finished_down:
            branchs_down = _update_current_branches(node_dict, branchs_down, 'links_down', 'link_to')
            # Kontrollieren ob alle oberliegende Stränge Ende erreicht haben
            finished_down = True
            for branch in branchs_down:
                if not branch['finished']:
                    # Falls ein Strang noch nicht fertig is weiter iterieren
                    finished_down = False
        # Steigung berechnen für jeden Strang
        nr_slope = 0
        slope_sum = 0
        for branch in branchs_down:
            if branch["sk"]:
                branch["slope"] = (branch["sk_first"]-branch["sk"])/branch["length"]
                slope_sum += branch["slope"]
                nr_slope += 1
        if nr_slope>0:
            sk = surrogat_down["sk"] + slope_sum/nr_slope*surrogat_down["length"]
        else:
            # Falls kein zweiter Schacht mit Sohlenkote gefunden wird. Definierte mittlere positive Steigung annehmen.
            sk = surrogat_down["sk"] + mean_slope*surrogat_down["length"]

        # Mit folgender Anpassungen positive Steigung in Fliessrichtung verweiden 
        # Annahme: Falls durch folgende Anpassung die postive Steigung vermieden werden kann ist in Realität keine Druckleitung vorhanden
        # Prüfen ob Steigung in Fliessrichtung negativ ist falls Sohlenkote mit Deckelkote und defnierter mittlerer Schachttiefe berechnet wird
        if sk < surrogat_down["sk_max"]:
            # Anpassung nur vornehmen falls dadurch Bedingung eingehalten werden kann 
            if (dk - mean_depth) > surrogat_down["sk_max"]:
                logger.warning(f'Um eine positive Steigung in Fliessrichtung zu verweiden wird beim Schacht mit der ID {id_node} die berechnete'
                               f' Sohlenkote von {sk} auf {dk- mean_depth} (Deckelkote - mean_depth) angepasst.')
                # Sohlenkote mit defnierter mittlerer Schachttiefe berechnen
                sk = dk - mean_depth

    else:
        # Kein oberliegender oder unterliegender Schacht weist Sohlenkote auf -> mit definierter mittlerer Schachttiefe berechnen
        if dk:
            logger.warning(f'Sohlenkote von Schacht mit ID {id_node} konnte nicht berechnet werden. Es wird eine Schachttiefe von {mean_depth} angenommen.')
            sk = dk - mean_depth
        else:
            logger.warning(f'Sohlenkote von Schacht mit ID {id_node} konnte nicht berechnet werden.')
    
    if sk and dk:
        # Mindesttiefe für Schacht prüfen 
        if dk - sk < min_depth:
            logger.warning(f'Beim Schacht mit der ID {id_node} wurde die Mindesttiefe {min_depth} unterschritten.'
                            f' Die berechnete Sohlenkote {sk} wurde auf {dk- min_depth} angepasst.')
            sk = dk - min_depth
        
    return sk


def main_slope(in_node, node_id, node_dk, node_sk, tag, node_type, type_inlet, min_depth, 
               mean_depth, in_link, link_id, link_from, link_to, link_length, mean_slope):
    """Input-Daten aufbereiten und Funktionen für die Interpolation der Sohlenkote aufrufen

    Required:
        in_node -- Name der Input Feature-Klasse mit den Schächten
        node_id -- Bezeichnung von ID-Feld der Schächte
        node_dk -- Bezeichnung von Feld mit Deckelkote
        node_sk -- Bezeichnung von Feld mit Sohlenkote
        tag -- Text für tag-Feld um zu kennzeichnen welche Sohlenkoten interpoliert wurden
        node_type -- Bezeichnung vom Feld in welchem der Schachttyp angegeben wird
        type_inlet -- Wert von Schachttyp (node_type) welcher Einlaufschacht entspricht
        min_depth -- Minimale Schachttiefe die nicht unterschritten werden darf. Annahme: Deckelkote genauer als Solhenkote
        mean_depth -- Schachttiefe die verwendet wird falls Sohlenkote nicht interpoliert werden konnte .
                      Dies kommt nur vor falls entlang eines Stranges keine einzige Sohlenkote bekannt ist.
        in_link -- Name der Feature-Klasse mit den Haltungen
        link_id -- Bezeichnung von ID-Feld
        link_from -- Bezeichnung von Feld mit ID von Von-Schacht
        link_to -- Bezeichnung von Feld mit ID von Bis-Schacht
        link_length -- Bezeichnung von Feld mit Haltungslänge
        mean_slope -- Mittlere Steigung für die Berechnung der Sohlenkote. Diese Steigung wird nur verwendet 
                      falls enlang eines Stranges nur eine einzige Sohlenkote vorhanden ist.
    """   

    # Prüfen ob Output-Feld und "tag"-Feld bereits vorhanden sind
    fnames =  [field.name for field in arcpy.ListFields(in_node)]
    node_tag = "tag"
    if node_tag not in fnames:
        logger.info(f'tag-Feld erstellen')
        arcpy.AddField_management(in_node, node_tag, "TEXT", field_length=40)

    ## Sohlenkote interpolieren
    # Liste mit Haltungen erstellen
    logger.info('Liste mit allen Haltungen erstellen')
    link_dict_list = []
    with arcpy.da.SearchCursor(in_link, [link_id, link_from, link_to, link_length]) as cursor:
        for row in cursor:
            # Relevante Werte der Haltungen als Dictionary speichern
            if row[1] == row[2]:
                logger.warning(f'Haltung mit ID {row[0]} hat selben Von- und Bis-Schacht! Von-Schacht wird auf Null gesetzt')
                link_dict_list.append({'link_id':row[0],'link_from':None, 'link_to':row[2], 'link_length':row[3]})
            else:   
                link_dict_list.append({'link_id':row[0],'link_from':row[1], 'link_to':row[2], 'link_length':row[3]})

    logger.info('Dictionary mit allen Schächten mit den zugehörigen Haltungen (gemäss Topologie) erstellen')
    node_dict = {}
    # Dictionary für Schächte mit zugehörigen Haltungen erstellen um iterieren später im Skript zu vereinfachen
    with arcpy.da.SearchCursor(in_node, [node_id, node_sk, node_dk, node_type]) as cursor:
        for row in cursor:
            # Einlaufhaltungen (Haltungen oberhalb Schacht)
            links_up = []
            # Auslaufhaltungen (Haltunen unterhalb Schacht)
            links_down = []
            # Zugehörige Haltungen eruieren
            for link in link_dict_list:
                if link['link_to'] == row[0]:
                    links_up.append(link)
                elif link['link_from'] == row[0]:
                    links_down.append(link)

            # Einlaufschächte kennzeichnen
            if str(row[3]) == type_inlet:
                inlet = 1
            else:
                inlet = 0
            
            # Wert von node_id als key verwenden und zugehörige Informationen innerhalb nested dictionaries speichern
            node_dict[row[0]] = {"node_sk":row[1],
                                 "node_dk":row[2],
                                 "inlet": inlet,
                                 "links_up":links_up,
                                 "links_down":links_down}

    # Dictionary sortieren damit die Sohlenkote von Einlaufschächten als letztes berechnet werden 
    # Nach Ordnung sortieren damit zuerst Sohlentiefe von Schächte ester Ordnung (PAA) berechnet werden
    # Nach Einlaufschächten sortieren damit Sohlenkote dieser Schächte nicht mit "Deckelkote - mean_depth" berechnet wird, da eher tieferliegend als "echte" Schächte
    node_sorted = sorted(node_dict.keys(), key=lambda x: (node_dict[x]['inlet']))

    # Durch alle Schächte iterieren
    logger.info('Durch alle Schächte iterieren und Sohlenkote berechnen falls nicht vorhanden')
    cnt = 0
    for id_node in node_sorted:
        if node_dict[id_node]['node_sk']:
            # Sohlenkote bereits vorhanden
            continue
        else:
            # Sohlenkote interpolieren
            #print(f'Sohlenkote von Schacht {cnt}:{id_node} berechnen')
            node_dict[id_node]['node_sk'] = get_interpolated_sk(node_dict, id_node, mean_slope, mean_depth, min_depth)
            cnt +=1

    logger.info(f'Von {cnt} Schächten Sohlenkote berechnet')

    # Attributbezogene Selektion (nur Schächte ohne Sohlenkote)
    logger.info('Schächte ohne Solhenkote selektieren')
    in_node_lyr = 'in_node_lyr'
    arcpy.management.MakeFeatureLayer(in_node, in_node_lyr)
    where = '"' + node_sk + '"' + " IS NULL" 
    arcpy.management.SelectLayerByAttribute(in_node_lyr, 'NEW_SELECTION', where, 'NON_INVERT')

    # Sohlenkote aktualisieren
    logger.info('Sohlenkote aktualisieren')
    cnt = 0
    with arcpy.da.UpdateCursor(in_node_lyr, [node_id, node_sk, node_tag]) as ucursor:
        for urow in ucursor:
            urow[1] = node_dict[urow[0]]['node_sk']            
            if urow[2]:
                urow[2] = urow[2] + ";"+tag
            else:
                urow[2] = tag
            cnt += 1
            ucursor.updateRow(urow)

    logger.info(f'Von {cnt} Schächten Sohlenkote aktualisiert')

    ## Schachttiefe aktualisieren
    # Feld Schachttiefe ergänzen
    max_depth = "MaxDepth"
    arcpy.management.AddField(in_node, max_depth, "FLOAT")   

    logger.info('Schachttiefe aktualisieren')
    cnt = 0
    with arcpy.da.UpdateCursor(in_node, [node_dk, node_sk, max_depth]) as ucursor:
        for urow in ucursor:
            urow[2] = float(urow[0]-urow[1])     
            ucursor.updateRow(urow)

   ## Steigung berechenen
   # Feld "slope" neu erstellen falls bereits vorhanden 
    fnames = arcpy.ListFields(in_link)
    link_slope = "slope"
    for in_field in fnames:
        if in_field.name == link_slope:
            logger.info(f'Vorhandenes slope-Feld löschen')
            arcpy.management.DeleteField(in_link, in_field.name)
    
    logger.info(f'slope-Feld erstellen')
    arcpy.AddField_management(in_link, link_slope, "FLOAT")

    logger.info(f'Steigung (Gefälle) berechnen und Feldwert abfüllen')
    # where (nur Haltungen mit Von- und Bisschacht)
    where = '"' + link_from + '"' + " IS NOT NULL" + " AND " + '"' + link_to + '"' + " IS NOT NULL"
    cnt = 0
    with arcpy.da.UpdateCursor(in_link, [link_id, link_from, link_to, link_length, link_slope], where) as cursor:
        for row in cursor:
            # get node_sk Wert von Vonschacht
            where_from = '"' + node_id + '"' + " = " + f"'{row[1]}'" 
            with arcpy.da.SearchCursor(in_node, [node_id, node_sk], where_from) as scursor:
                for srow in scursor:
                    sk_from = srow[1]
            # get node_sk Wert von Bisschacht
            where_to = '"' + node_id + '"' + " = " + f"'{row[2]}'" 
            with arcpy.da.SearchCursor(in_node, [node_id, node_sk], where_to) as scursor:
                for srow in scursor:
                    sk_to = srow[1]
            
            # Steigung berechnen
            try:
                slope = (sk_from - sk_to)/row[3]
                row[4] = slope
                cursor.updateRow(row)
                cnt += 1
                if slope < 0: 
                    logger.warning(f'Die Steigung für die Haltung mit ID "{row[0]}" ist negativ.')                  
            except:
                logger.warning(f'Die Steigung für die Haltung mit ID "{row[0]}" konnte aufgrund '
                               f'fehlender Daten nicht berechnet werden.')        

    logger.info(f'Von {cnt} Leitungen Steigung berechnet')
      

# Daten einlesen 
# Logginig initialisieren
if __name__ == "__main__":
    # Globale Variabel für logging
    global logger
    ### Input JSON-Datei ###
    # paramFile = r'...\gisswmm_upd_v1.json'
    paramFile = arcpy.GetParameterAsText(0)

    if paramFile:
        # Einlesen der json-Datei
        with open(paramFile, encoding='utf-8') as f:
            data = json.load(f)
            # Pfad zum Ordner in welchem Log-Datei gespeichert wird
            log_folder = data["log_folder"]
            # Wird als Postfix für Log-Dateinamen verwendet
            sim_nr = data["sim_nr"]
            # arcpy Workspace-Einstellung ('True' oder 'False')
            overwrite = data["overwrite"]
            # Pfad zu arcpy Workspace (.gdb) mit Knoten und Haltungen
            gisswmm_workspace = data["gisswmm_workspace"]
            # Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!)
            in_node = data["in_node"]
            # Bezeichnung von ID-Feld der Feature-Klasse 'in_node'
            node_id = data["node_id"]
            # Bezeichnung von Feld in Feature-Klasse 'in_node', mit der ID von der Haltung, auf welcher der Einlaufschacht liegt
            node_to_link = data["node_to_link"]
            # Bezeichnung vom Feld in welchem der Schachttyp angegeben wird (in Feature-Klasse 'in_node')
            node_type = data["node_type"]
            # Wert von Schachttyp ('node_type'), welcher dem Einlaufschacht entspricht
            type_inlet = data["type_inlet"]
            # Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!)
            in_link = data["in_link"]
            # Bezeichnung von ID-Feld der Feature-Klasse 'in_link'
            link_id = data["link_id"]
            # Bezeichnung von Feld mit ID von Von-Schacht der Feature-Klasse 'in_link'
            link_from = data["link_from"]
            # Bezeichnung von Feld mit ID von Bis-Schacht der Feature-Klasse 'in_link'
            link_to = data["link_to"]
            # Bezeichnung von Feld mit Haltungslänge der Feature-Klasse 'in_link'
            link_length = data["link_length"]
            # link_link_ref = data["link_link_ref"]   
            # Pfad zu arcpy Workspace mit DHM (.gdb)
            dhm_workspace = data["dhm_workspace"]
            # Name des DHM-Rasters
            in_dhm = data["in_dhm"]
            # Bezeichnung von Feld mit Deckelkote der Feature-Klasse 'in_node'
            node_dk = data["node_dk"]
            # Wert für tag-Feld um zu kennzeichnen, welche Deckelkote mit DHM berechnet wurden
            tag = data["tag_dk"]          
            # Bezeichnung von Feld mit Sohlenkote der Feature-Klasse 'in_node'
            node_sk = data["node_sk"]
            # Wert für tag-Feld um zu kennzeichnen, welche Sohlenkoten interpoliert wurden
            tag_sk = data["tag_sk"]
            # Minimale Schachttiefe (m) die nicht unterschritten werden darf. Annahme: Deckelkote genauer als Sohlenkote
            min_depth = float(data["min_depth"])
            # Schachttiefe (m) die verwendet wird, falls Sohlenkote nicht interpoliert werden konnte
            # Dieser Fall tritt nur auf, falls entlang eines Stranges keine einzige Sohlenkote bekannt ist
            mean_depth = float(data["mean_depth"])
            # Mittlere Steigung für die Berechnung der Sohlenkote. Diese Steigung wird nur verwendet, 
            # falls entlang eines Stranges nur eine einzige Sohlenkote vorhanden ist
            mean_slope = float(data["mean_slope"])  

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
    filename = 'gisswmm_upd_' + sim_nr + '.log'
    log = os.path.join(log_folder, filename)
    logger= lf.init_logging(log)
    logger.info('****************************************************************')
    logger.info(f'Start logging: {time.ctime()}')
    start_time = time.time()

    # Aktueller Workspace definieren
    arcpy.env.workspace = gisswmm_workspace
    
    # Prüfen ob Eingabedatensätze vorhanden sind
    postfix = "_" + sim_nr
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

    # Koordinatensystem
    spatial_ref = arcpy.Describe(in_node).spatialReference

    ## Von allen Knoten Deckelkote ermitteln 
    logger.info('Deckelkote berechnen')
    with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
        main_shaftheight(in_node, node_dk, dhm_workspace, in_dhm, tag)

    ## Zunächst nur PAA-Netz berücksichtigen
    count_input = arcpy.GetCount_management(in_node)
    where_clause_paa = "TYP_AA = 1"    
    node_paa = "node_lyr_paa"
    link_paa = "link_lyr_paa"
    arcpy.management.MakeFeatureLayer(in_node, node_paa, where_clause_paa)
    arcpy.management.MakeFeatureLayer(in_link, link_paa, where_clause_paa)
    count_paa = arcpy.GetCount_management(node_paa)

    # Sohlenkote zuerst nur von PAA Netz interpolieren, da üblicherweise präzisere Daten
    
    if int(count_paa[0])<int(count_input[0]):
        with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
            ## Topologie für PAA-Netz erstellen
            logger.info('Topologie von PAA-Netz erstellen')
            main_topology(in_node, node_id, node_to_link, node_type, type_inlet, in_link, link_id, link_from, 
                          link_to, link_length, delete = False)
            ## Sohlenkote für PAA-Netz interpolieren
            logger.info('Sohlenkote von PAA-Netz interpolieren')
            main_slope(node_paa, node_id, node_dk, node_sk, tag_sk, node_type, type_inlet, min_depth, 
                       mean_depth, link_paa, link_id, link_from, link_to, link_length, mean_slope)


    with arcpy.EnvManager(workspace = gisswmm_workspace, outputCoordinateSystem = spatial_ref, overwriteOutput = overwrite):
        ## Topologie für gesamtes Netz erstellen
        logger.info('Topologie für gesamte Netz erstellen')
        main_topology(in_node, node_id, node_to_link, node_type, type_inlet, in_link, link_id, link_from, link_to, link_length)
        ## Sohlenkote für gesamtes Netz interpolieren
        logger.info('Sohlenkote für gesamtes Netz interpolieren')
        main_slope(in_node, node_id, node_dk, node_sk, tag_sk, node_type, type_inlet, min_depth, 
                   mean_depth, in_link, link_id, link_from, link_to, link_length, mean_slope)

    # Logging abschliessen
    end_time = time.time()
    i = lf.search_in_file(log, "error")
    logger.info("Skript Laufzeit: " + str(round(end_time - start_time)) + " sec.")
    logger.info(str(i) + " Fehler gefunden. Check Log.")
    endtime = time.ctime()
    logger.info(f'End time: {time.ctime()}')
    logger.info('****************************************************************\n')

