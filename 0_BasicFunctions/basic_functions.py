
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 12.11.2021
#
# Funktionen die in mehreren pygisswmm-Skripts verwendet werden.
# -----------------------------------------------------------------------------
"""basic_functions"""
import sys
import arcpy
import logging_functions as lf


def append_text(in_fc, in_field, text, separator = ";"):
    """ Text einem bestehenden Feld einer Feature-Klasse hinzufügen

    Required:
        in_fc -- Input Feature-Klasse oder Layer
        in_field -- Input tag-Feld
        text -- Text
    Optional:
        separator -- Seperator mit welchem der neue Text hinzugefügt wird
    """
    expression_tag = "addTag(" + "!"+in_field+"!," + '"'+text+'"'+ ")"
    codeblock = """def addTag(old, new):
        if old:
            return old + separator + new
        else:
            return new"""
    arcpy.management.CalculateField(in_fc, in_field, expression_tag, "PYTHON3", codeblock)


def add_field(in_table, field_name, field_type, **kwargs):
    """Feld zu einer Tabelle oder Feature-Klasse hinzufügen

    Required:
        in_table -- Name der Tabelle oder Feature-Klasse
        field_name -- Name des Feldes
        field_type -- Feldtyp

    Optional:
        **kwargs -- Zusätzliche Parameter für arcpy.management.AddField (siehe Dokumentation Esri)
    """

    # Feld hinzufügen
    try:
        arcpy.management.AddField(in_table = in_table, field_name = field_name,
                                field_type = field_type, **kwargs)
    except Exception:
        e = sys.exc_info()[1]
        print(f'Fehler beim erstellen des Feldes "{field_name}": {e.args[0]}')




