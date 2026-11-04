"""Punto de entrada ``python tools/build.py <orden>``: la linea de ordenes del kit con el manifiesto.

Al ejecutarse como script, Python solo agrega ``tools/`` al camino de busqueda; para poder
importar el paquete ``tools`` se agrega la raiz del repositorio antes de importar la logica.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from psxdecomp.cli import main  # noqa: E402
from tools.proyecto import PROYECTO, ejecutar_proceso  # noqa: E402

DESCRIPCION = "Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."

if __name__ == "__main__":
    sys.exit(
        main(
            ejecutar=ejecutar_proceso,
            proyecto=PROYECTO,
            prog=PROYECTO.identidad.comando,
            descripcion=DESCRIPCION,
        )
    )
