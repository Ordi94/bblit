"""Punto de entrada ``python tools/build.py {split,build,verify,clean}``.

Al ejecutarse como script, Python solo agrega ``tools/`` al camino de busqueda; para poder
importar el paquete ``tools`` se agrega la raiz del repositorio antes de importar la logica.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tools.reconstruccion.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
