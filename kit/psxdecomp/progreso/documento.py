"""Presentacion del progreso: objeto JSON y documento Markdown, sin entrada ni salida.

Capa de presentacion. Recibe el ``Progreso`` ya calculado y devuelve texto o estructuras; escribirlos
en disco corresponde a ``medicion``. Los nombres de macro, carpetas y comando que aparecen en el texto
salen del manifiesto del proyecto, de modo que el kit no escribe ninguno a mano.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from psxdecomp.dominio import Convenciones, Rutas
from psxdecomp.progreso.calculo import Progreso, ResumenZona


def a_json(progreso: Progreso) -> dict[str, Any]:
    """
    Convierte el progreso al objeto que se guarda en ``build/progreso.json``.

    Contexto:
        Las claves van en camelCase, como el resto de JSON del proyecto.

    Args:
        progreso (Progreso): Resultado del medidor.

    Returns:
        dict[str, Any]: Objeto serializable con ``json.dumps``.

    Ejemplo:
        texto = json.dumps(a_json(progreso))
    """

    def zona(resumen: ResumenZona) -> dict[str, int]:
        return {"funciones": resumen.funciones, "bytes": resumen.bytes}

    return {
        "totales": {
            "arranque": zona(progreso.arranque),
            "juego": zona(progreso.juego),
            "librerias": zona(progreso.librerias),
            "funciones": progreso.funciones_totales,
        },
        "descompiladas": {
            "juego": zona(progreso.c_juego),
            "librerias": zona(progreso.c_librerias),
            "funciones": progreso.funciones_en_c,
            "porcentajeBytesJuego": progreso.porcentaje_bytes_juego,
        },
        "noCoincidentes": list(progreso.no_coincidentes),
        "motivosNoCoincidentes": dict(progreso.motivos),
        "archivos": [
            {
                "archivo": a.archivo,
                "funcionesC": a.c,
                "noCoincidentes": a.no_coincidentes,
                "ensamblador": a.ensamblador,
                "bytesC": a.bytes_c,
                "bytesTotal": a.bytes_total,
            }
            for a in progreso.archivos
        ],
        "subsistemas": [
            {
                "subsistema": s.nombre,
                "archivos": s.archivos,
                "funcionesC": s.c,
                "noCoincidentes": s.no_coincidentes,
                "ensamblador": s.ensamblador,
                "bytesC": s.bytes_c,
                "bytesTotal": s.bytes_total,
            }
            for s in progreso.subsistemas
        ],
        "manuscritas": [{"funcion": n, "bytes": b} for n, b in progreso.manuscritas],
        "sinComentario": [{"archivo": a, "funcion": f} for a, f in progreso.sin_comentario],
        "auxiliares": list(progreso.auxiliares),
        "sinSimbolo": list(progreso.sin_simbolo),
        "coherencia": {
            "glabelEnAsm": progreso.glabel_en_asm,
            "funcionesEnC": progreso.funciones_en_c,
            "funcionesTotales": progreso.funciones_totales,
            "coincide": progreso.coherente,
        },
    }


def _vineta(nombre: str, motivos: Mapping[str, str]) -> str:
    """Linea de lista de una funcion pendiente, con su motivo si lo tiene."""
    motivo = motivos.get(nombre)
    return f"- `{nombre}`: {motivo}" if motivo else f"- `{nombre}`"


def a_markdown(progreso: Progreso, *, comando: str, rutas: Rutas, convenciones: Convenciones) -> str:
    """
    Genera el contenido del documento de progreso (``rutas.documento_progreso``).

    Contexto:
        El texto es determinista (sin fechas) para que regenerarlo sin cambios no ensucie el
        historial.

    Args:
        progreso (Progreso): Resultado del medidor.
        comando (str): Comando con el que el proyecto invoca al kit (``identidad.comando``).
        rutas (Rutas): Carpetas del proyecto; el texto nombra la de fuentes y la del ensamblador.
        convenciones (Convenciones): Macros del proyecto; el texto nombra las dos.

    Returns:
        str: Documento en Markdown, terminado en salto de linea.

    Ejemplo:
        texto = a_markdown(progreso, comando="python -m psxdecomp.cli", rutas=rutas, convenciones=conv)
    """
    no_coincidente = convenciones.macro_no_coincidente
    lineas = [
        "# Progreso de la descompilación",
        "",
        f"Generado por `{comando} progreso`; no se edita a mano. Los conteos salen del",
        f"texto de `{rutas.fuentes}/*.c` (una función cuenta como descompilada solo si está definida en C "
        "en la",
        "construcción normal) y de la tabla de símbolos.",
        "",
        "## Resumen",
        "",
        "| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |",
        "|---|---:|---:|---:|---:|",
        f"| Arranque | {progreso.arranque.funciones} | {progreso.arranque.bytes} | 0 | 0 |",
        f"| Código del juego | {progreso.juego.funciones} | {progreso.juego.bytes} | "
        f"{progreso.c_juego.funciones} | {progreso.c_juego.bytes} |",
        f"| Librerías Sony | {progreso.librerias.funciones} | {progreso.librerias.bytes} | "
        f"{progreso.c_librerias.funciones} | {progreso.c_librerias.bytes} |",
        "",
        f"Bytes de código del juego descompilados: {progreso.c_juego.bytes} de {progreso.juego.bytes} "
        f"({progreso.porcentaje_bytes_juego:.2f} %).",
        f"Funciones marcadas `{no_coincidente}`: {len(progreso.no_coincidentes)}.",
    ]
    if progreso.coherente is None:
        lineas.append("Coherencia con el ensamblador: no medida (ejecute `split`).")
    else:
        estado = "correcta" if progreso.coherente else "ROTA"
        lineas.append(
            f"Coherencia con el ensamblador: {estado} ({progreso.glabel_en_asm} `glabel` en `{rutas.asm}/` + "
            f"{progreso.funciones_en_c} en C = {(progreso.glabel_en_asm or 0) + progreso.funciones_en_c}; "
            f"la tabla declara {progreso.funciones_totales})."
        )
    lineas += [
        "",
        "## Por subsistema",
        "",
        f"| Subsistema | Archivos | En C | `{no_coincidente}` | En ensamblador | "
        "Bytes en C | Bytes totales |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *(
            f"| {s.nombre} | {s.archivos} | {s.c} | {s.no_coincidentes} | {s.ensamblador} | "
            f"{s.bytes_c} | {s.bytes_total} |"
            for s in progreso.subsistemas
        ),
        "",
        "## Por archivo",
        "",
        f"| Archivo | En C | `{no_coincidente}` | En ensamblador | Bytes en C | Bytes totales |",
        "|---|---:|---:|---:|---:|---:|",
        *(
            f"| `{a.archivo}` | {a.c} | {a.no_coincidentes} | {a.ensamblador} | "
            f"{a.bytes_c} | {a.bytes_total} |"
            for a in progreso.archivos
        ),
        "",
        f"## Funciones `{no_coincidente}`",
        "",
        *(_vineta(nombre, dict(progreso.motivos)) for nombre in progreso.no_coincidentes),
    ]
    if not progreso.no_coincidentes:
        lineas.append("Ninguna.")
    lineas += ["", "## Rutinas manuscritas (siguen en ensamblador por diseño)", ""]
    lineas += [f"- `{nombre}` ({tamano} bytes)" for nombre, tamano in progreso.manuscritas]
    if not progreso.manuscritas:
        lineas.append("Ninguna.")
    if progreso.sin_comentario:
        lineas += [
            "",
            f"## `{convenciones.macro_ensamblador}` sin comentario en archivos con funciones en C",
            "",
        ]
        lineas += [f"- `{nombre}` (`{archivo}`)" for archivo, nombre in progreso.sin_comentario]
    if progreso.auxiliares:
        lineas += ["", "## Ayudantes definidos en C (no figuran en la tabla)", ""]
        lineas += [f"- `{nombre}`" for nombre in progreso.auxiliares]
    if progreso.sin_simbolo:
        lineas += ["", "## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)", ""]
        lineas += [f"- `{nombre}`" for nombre in progreso.sin_simbolo]
    return "\n".join(lineas) + "\n"
