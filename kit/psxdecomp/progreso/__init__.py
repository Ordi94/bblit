"""Medicion del progreso de la descompilacion y su presentacion.

Capas: ``calculo`` (reglas puras sobre simbolos y estados de funciones), ``documento`` (texto Markdown y
objeto JSON del resultado), ``medicion`` (lectura del disco y escritura del documento y del resumen) y
``readme`` (seccion del README entre marcadores). Ningun modulo conoce un proyecto concreto: zonas de
memoria, rutas, convenciones y comando llegan del manifiesto.
"""
