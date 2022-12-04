
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# author: Timo Wicki
# date: 29.10.2021
#
# Funktionen für das Logging
# -----------------------------------------------------------------------------
"""logging_functions"""
import logging

def init_logging(file):
    """Initialisiert das Logging

    Required:
        file -- Pfad zur Logdatei
    """
    logger = logging.getLogger('myapp')
    # Logging  für Log-Datei initialisieren
    hdlr = logging.FileHandler(file, mode='w')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    # Logging für Konsole initialisieren
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    logger.setLevel(logging.INFO)

    return logger


def search_in_file(file, text) -> int:
    """In einer Datei nach einem bestimmten String suchen und ermitteln wie oft
    der Text in der Datei vorkommt

    Required:
        file -- Pfad zur Logdatei
        text -- String welcher gesucht werden soll

    Return:
        cnt -- Anzahl des Vorkommens
    """
    cnt = 0
    with open(file) as f:
        for line in f:
            if text in line.lower():
                #logger.info(line)
                cnt=cnt+1
        return cnt