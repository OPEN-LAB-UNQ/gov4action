"""Texto seguro para CSV abiertos en una planilla; no modifica los datos guardados."""


def celda_csv(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value
