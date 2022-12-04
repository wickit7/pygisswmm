# pygisswmm
Automatische Erstellung eines SWMM-Modells aus einem Abwasserkataster (sia 405). Die Skripte wurden in Zusammenhang mit der UNIGIS Masterarbeit "Effekt der Einzugsgebietsmodellierung auf die Abflusssimulation im urbanen Gebiet" erstellt.

## Methodik
Die folgende Abbildung gibt einen Überblick über die wichtigsten Inputdaten, Arbeitsschritte und Ergebnisse. Die Prozesse wurden mittels der Programmiersprache Python (Rossum & Drake, 2009) automatisiert. Die hydrodynamische Simulation wird mit der Open Source Software [Stormwater Managment Model (SWMM)](https://www.epa.gov/water-research/storm-water-management-model-swmm) der US Environmental Protection Agency (EPA) durchgeführt (Rossman, 2015). Die GIS-Analysen erfolgen mit dem Softwareprodukt ArcGIS unter Verwendung der Python-Bibliothek [arcpy, v. 2.9](https://pro.arcgis.com/de/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm). Für die Schnittstelle zum Simulationsprogramm SWMM werden die Python-Bibliotheken [swmmio, v. 0.4.9](https://github.com/aerispaha/swmmio) (Erispaha & Brown, 2018) und [swmm_api, v. 0.2.0.18.3](https://gitlab.com/markuspichler/swmm_api) (Pichler, 2022) verwendet. Weitere Informationen sind im PDF der Masterarbeit zu finden.

<img  src="https://user-images.githubusercontent.com/45633047/205504102-8909d633-ce2b-4543-8006-7da86f31b50b.png" width=70% height=70%>

## Erstellung Python-Environment
Als Grundlage wurde die Python-Environment von ArcGIS Pro 2.9.4 in eine neue Python-Environment kopiert, indem in der Python Command Prompt folgender Befehl ausgeführt wurde:

> conda create --name arcgispro-py3-swmm --clone arcgispro-py3
> activate arcgispro-py3-swmm

Die Environment enthält unter anderem das Python-Package arcpy (v. 2.9).

Zusätzlich werden die Python-Packages «swmmio» und «swmm_api» benötigt:

> pip install swmmio==0.4.9
> pip install swmm_api==0.2.0.18.3

Die vorhandenen JSON- und Batch-Dateien wurden für die Testdaten (data\INPUT.gdb) erstellt. Diese Dateien müssen für die eigenen Daten entsprechend angepasst werden.


## Ausführung Skripte
Es wurden mehrere Skripte erstellt, die nacheinander ausgeführt werden. Im Folgenden werden die Skripte kurz beschrieben.

### [0_BasicFunctions](0_BasicFunctions/)
Eine Sammlung an Funktionen die in den folgenden Python-Skripten importiert und angewendet werden.


### [1_SIA2GISSWMM](1_SIA2GISSWMM/)
#### [sia2gisswmm.py](1_SIA2GISSWMM/sia2gisswmm.py)
Das Abwasserkataster (sia405) in einen vereinfachten GIS-Datensatz konvertieren, welcher als Grundlage für die Weiterverarbeitung verwendet wird. Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/1_SIA2GISSWMM/Logs" |
| sim_nr | Die Bezeichnung der aktuellen Simulation (Szenario). Das Esri Feature-Dataset im Workspace " gisswmm _workspace" erhält diese Bezeichnung. Zudem wird die Bezeichnung den Feature-Klassen ("out_node", "out_link") und der Log-Datei als Postfix hinzugefügt. | "v1" |
| lk_workspace | Pfad zum arcpy Workspace, der das zu konvertierende Abwasserkataster (SIA405) enthält. | "C:/pygisswmm/data/INPUT.gdb" |
| in_node | Name der Input Feature-Klasse mit den Abwasserknoten (Schächte) im Workspace "lk_workspace". | "AWK_ABWASSERKNOTEN" |
| in_link | Name der Input Feature-Klasse mit den Haltungen (Leitungen) Workspace "lk_workspace". | "AWK_HALTUNG" |
| boundary_workspace | Pfad zum arcpy Workspace, der die Input Feature-Klasse mit der Begrenzungsfläche des Untersuchungsgebietes enthält. | "C:/pygisswmm/data/INPUT.gdb" |
| in_boundary | Name der Feature-Klasse mit der Input Begrenzungsfläche im Workspace "boundary_workspace". | "BEGRENZUNG" |
| gisswmm_workspace |Pfad zum Output arcpy Workspace, in dem die Output Feature-Klassen ("out_node", "out_link") gespeichert werden sollen.| "C:/pygisswmm/data/GISSWMM.gdb" |
| out_node | Name der Output Feature-Klasse mit den konvertierten Abwasserknoten (dieser Name wird im Skript noch mit dem Postfix "sim_nr" ergänzt). | "node" |
| in_boundary | Name der Feature-Klasse mit der Input Begrenzungsfläche im Workspace "boundary_workspace". | "BEGRENZUNG" |
| out_link | Name der Ausgabe Feature-Klasse mit den konvertierten Haltungen (dieser Name wird im Skript noch mit dem Postfix "sim_nr" ergänzt). | "link" |
| overwrite | Die arcpy Workspace-Einstellung "overwirte" | "True" |
| mapping_link <br />  - in_field <br />  - out_field <br />  - where <br />  - out_type <br /> -mapping | Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_link" (Abwasserkataster) zur Output Feature-Klasse "out_link" (gisswmm). | ![image](https://user-images.githubusercontent.com/45633047/205503673-33d1ec2d-6575-4c13-8984-afbd85b2e7a8.png) |
| mapping_node <br />  - in_field <br />  - out_field <br />  - where <br />  - out_type <br /> -mapping | Liste mit Dictionaries für das Mapping von der Input Feature-Klasse "in_node" (Abwasserkataster) zur Output Feature-Klasse "out_node" (gisswmm). | ![image](https://user-images.githubusercontent.com/45633047/205505157-d31d14e0-8d68-4f46-8175-4dc1bba7155e.png) |
| default_values_link <br />  - InOffset <br />  - SurchargeDepth <br />  - InitFlow <br />  - MaxFlow | Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerte für die Output Feature-Klasse "out_link".| ![image](https://user-images.githubusercontent.com/45633047/205505226-cb84ae6a-fc96-4dba-8203-79a9e7470200.png) |
| default_values_node <br />  - InitDepth <br />  - SurchargeDepth <br />  - PondedArea <br /> | Liste mit Dictionaries für das Mapping von zusätzlichen Output Feldern inklusive Standardwerte für die Output Feature-Klasse "out_node".| ![image](https://user-images.githubusercontent.com/45633047/205505287-f1abcfce-bc19-48ed-85c3-96798a5aa70a.png)|

### [2_GISSWMM](2_GISSWMM/)
#### [gisswmm_upd.py](2_GISSWMM/gisswmm_upd.py)
- Erstellung Netzwerktopologie: Haltungen werden bei Einlaufknoten aufgetrennt um eine strikte Knoten-Haltung-Knoten Topologie zu erhalten. 
- Ermittlung Deckelkote: Für Knoten ohne gemessene Deckelkote (Höhe des Schachtdeckels m ü. M.), wird die Höhe aus einem Höhenmodell (DHM) extrahiert.
- Interpolation Sohlenkote: Für Knoten ohne gemessene Sohlenkote (Höhe der Schachtsohle m ü. M.), wird die Höhe mit einem Algorithmus berechnet. 
Dem Skript wird eine JSON-Datei mit den folgenden Parametern übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/2_GISSWMM/Logs" |
| sim_nr | Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace " hat diese Bezeichnung und die enthaltenen Feature-Klasse haben diese Bezeichnung als Postfix. | «v1» |
| overwrite | Die arcpy Workspace-Einstellung "overwirte". | "TRUE" |
| dhm_workspace | Pfad zum arcpy Workspace mit dem Höhenmodell (DHM). | "C:/pygisswmm/data/INPUT.gdb" |
| in_dhm | Name des DHM-Rasters im Workspace "dhm_workspace". | "DHM" |
| gisswmm_workspace | Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node" und "out_link" gespeichert sind. | "C:/pygisswmm/data/GISSWMM.gdb" |
| in_node | Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!) im Workspace "gisswmm_workspace". | "node" |
| node_id | Bezeichnung vom ID-Feld der Feature-Klasse "in_node". | "Name" |
| node_dk | Bezeichnung vom Feld mit der Deckelkote der Feature-Klasse "in_node". | "ELev" |
| node_sk | Bezeichnung vom Feld mit der Sohlenkote der Feature-Klasse "in_node". | "InvertElev" |
| tag_dk | Wert für tag-Feld, um zu kennzeichnen, welche Deckelkoten mit DHM berechnet wurden. | "dk_dhm" |
| tag_sk | Wert für tag-Feld, um zu kennzeichnen, welche Sohlenkoten interpoliert wurden. | "sk_ip" |
| node_to_link | Bezeichnung vom Feld in der Feature-Klasse "in_node"., mit der ID von der Haltung, auf welcher der Einlaufschacht liegt. | "NodeToLink" |
| node_type | Bezeichnung vom Feld mit dem Schachttyp, in der Feature-Klasse "in_node". | "SWMM_TYPE" |
| type_inlet | Wert im Feld Schachttyp ("node_type"), welcher dem Einlaufschacht entspricht. | "INLET" |
| min_depth | Minimale Schachttiefe (m), die nicht unterschritten werden darf. Annahme: Deckelkote genauer als Sohlenkote. | "0.1" |
| mean_depth | Schachttiefe (m) die verwendet wird, falls die Sohlenkote nicht interpoliert werden konnte. Dies kommt nur vor, falls entlang eines Haltungsstranges keine einzige Sohlenkote bekannt ist. | "1.5" |
| in_link | Bezeichnung vom ID-Feld in der Feature-Klasse "in_link". | "Name" |
| link_from | Bezeichnung vom Feld mit der ID vom Bis-Schacht in der Feature-Klasse "in_link". | "OutletNode" |
| link_length | Bezeichnung vom Feld mit der Haltungslänge in der Feature-Klasse "in_link". | "Length" |
| mean_slope | Mittleres Gefälle für die Berechnung der Sohlenkote. Dieses Gefälle wird nur verwendet, falls entlang eines Haltungstranges nur eine einzige Sohlenkote vorhanden ist. | 0.05 |

#### [copy_from_vx_to_vy.py](2_GISSWMM/copy_from_vx_to_vy.py)
Mit diesem Skript können Haltungen (link) und Knoten (node) von einem Dataset (Simulation) in ein neues Dataset kopiert werden. Dem Skript wird eine JSON-Datei mit folgenden Parameter übergeben:

| Parameter | Beschreibung | Beispiel |
| --- | --- | --- |
| log_folder | Pfad zum Ordner, in dem die log-Datei gespeichert werden soll. | "C:/pygisswmm/2_GISSWMM/Logs" |
| sim_nr | Bezeichnung der aktuellen Simulation. Das Feature-Dataset in "gisswmm_workspace " hat diese Bezeichnung und die enthaltenen Feature-Klasse haben diese Bezeichnung als Postfix. | «v1» |
| gisswmm_workspace | Pfad zum Output arcpy Workspace, in dem die Feature-Klassen "in_node" und "out_link" gespeichert sind. | "C:/pygisswmm/data/GISSWMM.gdb" |
| from_sim_nr | Bezeichnung des Datasets im Workspace "gisswmm_workspace" (Bezeichnung der Simulation), welches kopiert werden soll. | "v1" |
| to_sim_nrs | Liste mit Datasets (Simulationen), die erstellt werden sollen. | ["v2", "v3", "v4"] |
| in_link | Name der Feature-Klasse mit den Haltungen (ohne Postfix "_sim_nr"!). | "link" |
| in_node | Name der Feature-Klasse mit den Knoten (ohne Postfix "_sim_nr"!) im Workspace "gisswmm_workspace". | "node" |
| overwrite | Die arcpy Workspace-Einstellung "overwirte". | "TRUE" |

## Referenzen
- Erispaha, A. S., & Brown, C. (2018). Automating Model Builds for Sequence Optimization of Flood Mitigation Investment Phases. Journal of Water Management Modeling.
- Pichler, M. (2022). swmm-api: API for reading, manipulating and running SWMM-Projects with python. In (Version 0.2.0.18.3) Zenodo. https://doi.org/10.5281/zenodo.5862141
- Rossman, L. A. (2015). Storm water management model user's manual, version 5.1. National Risk Management Research Laboratory, Office of Research and and Development. 
- Rossum & Drake (2009). Python 3 Reference Manual



