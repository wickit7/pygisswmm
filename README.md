# pygisswmm
Automatische Erstellung eines SWMM-Modells aus einem Abwasserkataster (sia 405). Die Skripte wurden im Zusammenhang mit der UNIGIS Masterarbeit "Effekt der Einzugsgebietsmodellierung auf die Abflusssimulation im urbanen Gebiet" erstellt.

## Methodik
Die folgende Abbildung gibt einen Überblick über die wichtigsten Inputdaten, Arbeitsschritte und Ergebnisse. Die Prozesse wurden mittels der Programmiersprache Python (Rossum & Drake, 2009) automatisiert. Die hydrodynamische Simulation wird mit der Open Source Software [Stormwater Managment Model (SWMM)](https://www.epa.gov/water-research/storm-water-management-model-swmm) der US Environmental Protection Agency (EPA) durchgeführt (Rossman, 2015). Die GIS-Analysen erfolgen mit dem Softwareprodukt ArcGIS unter Verwendung der Python-Bibliothek [arcpy, v. 2.9](https://pro.arcgis.com/de/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm). Für die Schnittstelle zum Simulationsprogramm SWMM werden die Python-Bibliotheken [swmmio, v. 0.4.9](https://github.com/aerispaha/swmmio) (Erispaha & Brown, 2018) und [swmm_api, v. 0.2.0.18.3](https://gitlab.com/markuspichler/swmm_api) (Pichler, 2022) verwendet. Weitere Informationen sind im PDF der Masterarbeit zu finden.

<img  src="https://user-images.githubusercontent.com/45633047/205504102-8909d633-ce2b-4543-8006-7da86f31b50b.png" width=70% height=70%>

## Erstellung virutelle Umgebung für Python
Als Grundlage wurde die virutelle Python-Umgebung von ArcGIS Pro 2.9.4 in eine neue virutelle Python-Umgebung kopiert, indem in der Python Command Prompt folgender Befehl ausgeführt wurde:

> conda create --name arcgispro-py3-swmm --clone arcgispro-py3
> activate arcgispro-py3-swmm

Die Umgebung enthält unter anderem die Python-Bibliothek arcpy (v. 2.9).

Zusätzlich werden die Python-Bibliotheken «swmmio» und «swmm_api» benötigt:

> pip install swmmio==0.4.9
> pip install swmm_api==0.2.0.18.3

Die vorhandenen JSON- und Batch-Dateien wurden für die Testdaten (data\INPUT.gdb) erstellt. Diese Dateien müssen für die eigenen Daten jeweils entsprechend angepasst werden.

## Ausführung Skripte
Es wurden mehrere Python-Skripte erstellt, die nacheinander ausgeführt werden. Die Skripte werden im Folgenden kurz beschrieben.

### [0_BasicFunctions](0_BasicFunctions/)
Eine Sammlung an Funktionen, die in den folgenden Python-Skripten importiert und angewendet werden.

### [1_SIA2GISSWMM](1_SIA2GISSWMM/)
#### [sia2gisswmm.py](1_SIA2GISSWMM/sia2gisswmm.py)
Das Abwasserkataster (sia405) in einen vereinfachten GIS-Datensatz konvertieren, welcher als Grundlage für die Weiterverarbeitung verwendet wird. 
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder |Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/1_SIA2GISSWMM/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation (Szenario). Das Esri Feature-Dataset im Workspace "gisswmm _workspace" erhält diese Bezeichnung. Zudem wird die Bezeichnung den Feature-Klassen ("out_node", "out_link") und der Log-Datei als Postfix hinzugefügt. | "v1" |
| lk_workspace |Der Pfad zum arcpy Workspace, welcher das zu konvertierende Abwasserkataster (SIA405) enthält. | "C:/pygisswmm/data/INPUT.gdb" |
| in_node | Der Name der Input Feature-Klasse mit den Abwasserknoten (Schächte) im Workspace "lk_workspace". | "AWK_ABWASSERKNOTEN" |
| in_link | Der Name der Input Feature-Klasse mit den Haltungen (Leitungen) im Workspace "lk_workspace". | "AWK_HALTUNG" |
| boundary_workspace | Der Pfad zum arcpy Workspace, welcher die Input Feature-Klasse mit der Begrenzungsfläche des Untersuchungsgebietes enthält. | "C:/pygisswmm/data/INPUT.gdb" |
| in_boundary | Der Name der Feature-Klasse mit der Input Begrenzungsfläche im Workspace "boundary_workspace". | "BEGRENZUNG" |
| gisswmm_workspace | Der Pfad zum Output arcpy Workspace, in dem die Output Feature-Klassen ("out_node", "out_link") gespeichert werden sollen.| "C:/pygisswmm/data/GISSWMM.gdb" |
| out_node | Der Name der Output Feature-Klasse mit den konvertierten Abwasserknoten (dieser Name wird im Skript noch mit dem Postfix "_sim_nr" ergänzt). | "node" |
| out_link | Der Name der Output Feature-Klasse mit den konvertierten Haltungen (dieser Name wird im Skript noch mit dem Postfix "_sim_nr" ergänzt). | "link" |
| overwrite | Die arcpy Umgebungseinstellung "overwirte" | "True" |
| mapping_link <br />  - in_field <br />  - out_field <br />  - where <br />  - out_type <br /> -mapping | Eine Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_link" (Abwasserkataster) zur Output Feature-Klasse "out_link" (gisswmm). | siehe in [Beispiel Json-Datei](1_SIA2GISSWMM/sia2gisswmm_v1.json) |
| mapping_node <br />  - in_field <br />  - out_field <br />  - where <br />  - out_type <br /> -mapping | Eine Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_node" (Abwasserkataster) zur Output Feature-Klasse "out_node" (gisswmm). | siehe in [Beispiel Json-Datei](1_SIA2GISSWMM/sia2gisswmm_v1.json)|
| default_values_link <br />  - InOffset <br />  - SurchargeDepth <br />  - InitFlow <br />  - MaxFlow | Eine Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerten für die Output Feature-Klasse "out_link".| "default_values_link": <br /> {"InOffset":"0", "OutOffset":"0", "InitFlow":"0", "MaxFlow":"0"} |
| default_values_node <br />  - InitDepth <br />  - SurchargeDepth <br />  - PondedArea | Eine Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerten für die Output Feature-Klasse "out_node".| "default_values_node": <br /> {"InitDepth":"0","SurchargeDepth":"0","PondedArea":"0"}	|

### [2_GISSWMM](2_GISSWMM/)
#### [gisswmm_upd.py](2_GISSWMM/gisswmm_upd.py)
Den vereinfachten GIS-Datensatz aktualisieren:
- Erstellung Netzwerktopologie: Haltungen werden bei den Einlaufknoten aufgetrennt, um eine strikte Knoten-Haltung-Knoten Topologie zu erhalten. 
- Ermittlung Deckelkote: Für Knoten ohne gemessene Deckelkote (Höhe des Schachtdeckels m ü. M.), wird die Höhe aus einem Höhenmodell (DHM) extrahiert.
- Interpolation Sohlenkote: Für Knoten ohne gemessene Sohlenkote (Höhe der Schachtsohle m ü. M.), wird die Höhe mit einem Algorithmus berechnet. 
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/2_GISSWMM/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace" hat diese Bezeichnung und die enthaltenen Feature-Klassen haben diese Bezeichnung als Postfix. | "v1" |
| overwrite | Die arcpy Umgebungseinstellung "overwirte". | "TRUE" |
| dhm_workspace | Der Pfad zum arcpy Workspace mit dem Höhenmodell (DHM). | "C:/pygisswmm/data/INPUT.gdb" |
| in_dhm | Der Name des DHM-Rasters im Workspace "dhm_workspace". | "DHM" |
| gisswmm_workspace | Der Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node" und "in_link" gespeichert sind. | "C:/pygisswmm/data/GISSWMM.gdb" |
| in_node | Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!) im Workspace "gisswmm_workspace". | "node" |
| node_id | Die Bezeichnung vom ID-Feld in der Feature-Klasse "in_node". | "Name" |
| node_dk | Die Bezeichnung vom Feld mit der Deckelkote in der Feature-Klasse "in_node". | "ELev" |
| node_sk | Die Bezeichnung vom Feld mit der Sohlenkote in der Feature-Klasse "in_node". | "InvertElev" |
| tag_dk | Den Wert für das tag-Feld, um zu kennzeichnen, welche Deckelkoten mit dem DHM berechnet wurden. | "dk_dhm" |
| tag_sk | Den Wert für das tag-Feld, um zu kennzeichnen, welche Sohlenkoten durch Interpolation ermittelt wurden. | "sk_ip" |
| node_to_link | Der Name des Feldes in der Feature-Klasse "in_node", das die ID des Schachts enthält, auf dem sich der Einlaufschacht befindet. | "NodeToLink" |
| node_type | Die Bezeichnung vom Feld mit dem Schachttyp in der Feature-Klasse "in_node". | "SWMM_TYPE" |
| type_inlet | Den Wert im Feld Schachttyp ("node_type"), welcher dem Einlaufschacht entspricht. | "INLET" |
| min_depth | Eine minimale Schachttiefe (m), die nicht unterschritten werden darf. | "0.1" |
| mean_depth | Eine Schachttiefe (m), die verwendet wird, falls die Sohlenkote nicht interpoliert werden konnte. Dieser Fall tritt nur auf, falls entlang eines Haltungsstranges keine einzige Sohlenkote bekannt ist. | "1.5" |
| in_link | Die Bezeichnung vom ID-Feld in der Feature-Klasse "in_link". | "Name" |
| link_from | Die Bezeichnung vom Feld mit der ID vom Bis-Schacht in der Feature-Klasse "in_link". | "OutletNode" |
| link_length | Die Bezeichnung vom Feld mit der Haltungslänge in der Feature-Klasse "in_link". | "Length" |
| mean_slope | Ein mittleres Gefälle für die Berechnung der Sohlenkote. Dieses Gefälle wird nur verwendet, falls entlang eines Haltungstranges nur eine einzige Sohlenkote vorhanden ist. | 0.05 |

#### [copy_from_vx_to_vy.py](2_GISSWMM/copy_from_vx_to_vy.py)
Mit diesem Skript können Haltungen (link) und Knoten (node) von einem Dataset (Simulation) in ein neues Dataset kopiert werden.
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/2_GISSWMM/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace" hat diese Bezeichnung und die enthaltenen Feature-Klassen haben diese Bezeichnung als Postfix. | "v1" |
| gisswmm_workspace | Der Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node" und "in_link" gespeichert sind. | "C:/pygisswmm/data/GISSWMM.gdb" |
| from_sim_nr | Die Bezeichnung des Datasets im Workspace "gisswmm_workspace" (Bezeichnung der Simulation), welches kopiert werden soll. | "v1" |
| to_sim_nrs | Eine Liste mit Datasets (Simulationen), die erstellt werden sollen. | ["v2", "v3", "v4"] |
| in_link | Der Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!). | "link" |
| in_node | Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!) im Workspace "gisswmm_workspace". | "node" |
| overwrite | Die arcpy Umgebungseinstellung "overwirte". | "TRUE" |

### [3_SUBCATCHMENT](3_SUBCATCHMENT/)
#### [gisswmm_cre_subcatchments.py](3_SUBCATCHMENT/gisswmm_cre_subcatchments.py)
Die Teileinzugsgebiete mit einer der folgenden vier Methoden erstellen:
 1. Parzellen als Teileinzugsgebiete 
 2. Parzellen unterteilt in Flächen mit homogener Bodenbedeckung
 3. Topographische Einzugsgebiete als Teileinzugsgebiete
 4. Topographische Einzugsgebite untrteilt in Flächen mit homogener Bodenbedeckung
Bei der Methode 1 und 2 werden die topographischen Einzugsgebiete verwendet, um den Entwässerungsknoten der Teileinzugsgebiete (Parzellen) zu bestimmen.
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/3_SUBCATCHMENT/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace " hat diese Bezeichnung und die enthaltenen Feature-Klassen haben diese Bezeichnung als Postfix. | "v1" |
| method | Die Methode mit welcher die Teileinzugsgebiete erstellt werden sollen ("1", "2", "3" oder "4"). | "3" |
| snap_distance | Eine Distanz (m), die als Fangtoleranz für die Funktion arcpy.sa.SnapPourPoint verwendet wird. Die Funktion verschiebt die Knoten innerhalb dieser Distanz an die Position mit der grössten Abflussakkumulation, bevor die topographischen Teileinzugsgebiete von dieser Postion aus berechnet werden. | "1" |
| min_area | Eine minimale Fläche, die ein Teileinzugsgebiet aufweisen soll (m2). | "1" |
| mapping_land_imperv <br />  - in_field <br /> - mapping | Ein Dictionary mit der Art der Bodenbedeckung als "key" und "%imperviousness" als "value". | "mapping_land_imperv": <br /> {"in_field": "ART", "mapping": {"0":"100","1":"100",....,"24":"0", "25":"0"}} |
| mapping_land_roughness <br />  - in_field <br /> - mapping | Ein Dictionary mit der Art der Bodenbedeckung als "key" und "roughness" als "value". | "mapping_land_roughness":<br /> {"in_field": "ART", "mapping": {"0":"0.01","1":"0.01",...,"24":"0.2", "25":"0.2"}} |
| mapping_land_depression_storage <br />  - in_field <br /> - mapping | Ein Dictionary mit der Art der Bodenbedeckung als "key" und "depression storage" als "value". | 
"mapping_land_depression_storage": <br /> {"in_field": "ART", "mapping": {"0":"0.05",..., "25":"0.3"}} |
| Infiltration <br />  - max_rate <br /> - min_rate <br /> - decay <br /> - dry_time <br /> - max_infil| Ein Dictionary mit den Kennwerten zur Infiltration nach Horton. | "infiltration": <br /> {"max_rate":"3", "min_rate":"0.5", "decay":"4", "dry_time":"7", "max_infil":"0"} |
| gisswmm_workspace | Der Pfad zum Output arcpy Workspace, in dem die Feature-Klasse "in_node" gespeichert ist und "out_subcatchment" gespeichert werden soll. | "C:/pygisswmm/data/GISSWMM.gdb" |
| overwrite | Die arcpy Umgebunseinstellung "overwirte". | "TRUE" |
| out_subcatchment | Der Name der Output Feature-Klasse mit den Teileinzugsgebieten (ohne Postfix "_sim_nr"!). | "subcatchment" |
| in_node | Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!). | "node" |
| node_id | Die Bezeichnung vom ID-Feld in der Feature-Klasse "in_node". | "Name" |
| node_type | Die Bezeichnung vom Feld mit dem Schachttyp in der Feature-Klasse "in_node". | "SWMM_TYPE" |
| type_inlet | Der Wert vom Schachttyp ("node_type"), welcher dem Einlaufschacht entspricht. | "INLET" |
| dhm_workspace | Der Pfad zum arcpy Workspace mit dem Höhenmodell (DHM). | "C:/pygisswmm/data/INPUT.gdb" |
| in_dhm | Der Name des DHM-Rasters im Workspace "dhm_workspace". | "DHM" |
| max_slope | Ein maximales Gefälle in %, das ein Teileinzugsgebiet haben soll. | "60" |
| land_workspace | Der Pfad zum arcpy Workspace mit der Bodenbedeckung. | "C:/pygisswmm/data/INPUT.gdb" |
| in_land | Der Name des Bodenbedeckung-Rasters im Workspace "land_workspace". | "BODENBEDECKUNG" |
| out_raster_workspace | Der Workspace in welchem Output Rasterdaten gespeichert werden sollen. | "C:/pygissmm/data/Default.gdb" |
| out_raster_prefix | Ein Prefix für die Bezeichnung der Output Rasterdaten. | "testdata" |
| parcel_workspace | Der Pfad zum arcpy Workspace mit den Parzellen (Liegenschaften)| "C:/pygisswmm/data/INPUT.gdb" |
| in_parcel | Die Bezeichnung der Feature-Klasse mit den Parzellen im Workspace "parcel_workspace". | "LIEGENSCHAFTEN" |
| parcel_id | Die Bezeichnung vom ID-Feld in der Feature-Klasse "in_parcel".  | "NUMMER" |


### [4_GISSWMM2SWMM](4_GISSWMM2SWMM/)
#### [gisswmm2swmm.py](4_GISSWMM2SWMM/gisswmm2swmm.py)
Die GIS-Datensätze («node», «link», «subcatchment») in die Template SWMM-Inptdatei (.inp) importieren. Die SWMM-Objekte EVAPORATION, RAINGAGES, MAP, REPORT, STORAGE, DWF, CURVES, ORIFICES, WEIRS, LOSSES, TIMESERIES, TAGS, SYMBOLS und LABELS werden noch nicht berücksichtig und müssten bei Bedarf in der SWMM-Software weiterbearbeitet werden. Bei den SWMM-Objekten OUTFALLS und PUMPS werden nicht alle Felder berücksichtigt.
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Der Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/4_GISSWMM2SWMM/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace " hat diese Bezeichnung und die enthaltenen Feature-Klassen haben diese Bezeichnung als Postfix. | "v1" |
| gisswmm_workspace | Der Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node", "in_link" und "in_subcatchment" gespeichert sind. | "C:/pygisswmm/data/GISSWMM.gdb" |
| in_node | Der Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!). | "node" |
| in_link | Der Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!). | "link" |
| in_subcatchment | Der Name der Feature-Klasse mit den Teileinzugsgebieten (ohne Postfix "_sim_nr"!). | "subcatchment" |
| template_swmm_file | Der Pfad zur Template SWMM-Inputdatei (.inp). | --- |

### [5_RESULT](5_RESULT/)
Die Skripte zur Analyse der Simulationsergebnisse wurden spezifisch für die Beispielsimulation erstellt und müssen bei der Verwendung für eine andere Simulation angepasst werden. Die Eingabeparameter werden nicht über eine JSON-Datei übergeben.

#### [swmm_analyze_inp.py](5_RESULT/swmm_analyze_inp.py)
Diagramme mit Informationen aus der SWMM-Inputdatei erstellen (z. B. Flächenverteilung).

#### [swmm_analyze_out.py](5_RESULT/swmm_analyze_out.py)
Diagramme mit Informationen aus der SWMM-Outputdatei «.out» erstellen (z. B. Abfluss über die Simulationszeit bei einem bestimmten Knoten).

#### [swmm_analyze_rpt.py](5_RESULT/swmm_analyze_rpt.py)
Diagramme mit Informationen aus der SWMM-Outputdatei ".rpt" erstellen (z. B. Verteilung Abflussbeiwert).

#### [swmm_rpt2excel.py](5_RESULT/swmm_rpt2excel.py)
Die SWMM-Outputdateien ".rpt" werden zu Excel-Dateien konvertiert, die anschliessend in ArcGIS Pro zu den GIS-Datensätzen ("node", "link", "subcatchment") angehängt werden können, um die Ergebnisse in Karten zu präsentieren.

[Beispieldiagramme](5_RESULT/figures/)

## Referenzen
- Erispaha, A. S., & Brown, C. (2018). Automating Model Builds for Sequence Optimization of Flood Mitigation Investment Phases. Journal of Water Management Modeling.
- Pichler, M. (2022). swmm-api: API for reading, manipulating and running SWMM-Projects with python. In (Version 0.2.0.18.3) Zenodo. https://doi.org/10.5281/zenodo.5862141
- Rossman, L. A. (2015). Storm water management model user's manual, version 5.1. National Risk Management Research Laboratory, Office of Research and and Development. 
- Rossum & Drake (2009). Python 3 Reference Manual



