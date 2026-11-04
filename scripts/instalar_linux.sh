#!/usr/bin/env bash
# Prepara una maquina Debian 13 para reconstruir y permutar funciones del juego.
#
# Instala Wine (los compiladores del SDK son ejecutables Win32), Python con venv y las dependencias
# de las herramientas, descarga los binutils MIPS nativos que usa el toolchain de Windows (GNU
# binutils 2.40 de mipsel-none-elf, build de Linux de PSn00bSDK) y crea el entorno virtual del
# repositorio. Los binutils de Debian (mipsel-linux-gnu-) NO sirven: alinean las secciones a 16
# bytes en lugar de 4 y el ejecutable deja de coincidir byte a byte.
# Es idempotente: se puede repetir sin efectos secundarios.
#
# Uso (como root o con sudo disponible):
#   bash scripts/instalar_linux.sh
#
# Variables opcionales:
#   BBLIT_OMITIR_APT=1     no instala paquetes del sistema
#   BBLIT_BINUTILS_DIR     destino de los binutils (por omision $HOME/.local/mipsel-none-elf)
#
# Las herramientas que instala `pip install -r requirements.txt` (el kit psxdecomp incluido) leen las
# variables BBLIT_* o sus equivalentes PSXDECOMP_* (esta ultima manda si ambas estan definidas).
set -eo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINUTILS_DIR="${BBLIT_BINUTILS_DIR:-$HOME/.local/mipsel-none-elf}"
BINUTILS_URL="https://github.com/Lameguy64/PSn00bSDK/releases/download/v0.24/gcc-mipsel-none-elf-12.3.0-linux.zip"
BINUTILS_SHA256="228f031a25cf2687d8845fd1421f625bafc211fa27da428e458e80d030a726f8"

if [[ "${BBLIT_OMITIR_APT:-0}" != "1" ]]; then
    SUDO=""
    if [[ "$(id -u)" -ne 0 ]]; then
        SUDO="sudo"
    fi
    export DEBIAN_FRONTEND=noninteractive
    $SUDO dpkg --add-architecture i386
    $SUDO apt-get update -qq
    $SUDO apt-get install -y --no-install-recommends \
        wine wine32:i386 \
        python3 python3-venv python3-pip \
        git ca-certificates curl unzip
fi

if [[ ! -x "$BINUTILS_DIR/bin/mipsel-none-elf-as" ]]; then
    TEMPORAL="$(mktemp -d)"
    trap 'rm -rf "$TEMPORAL"' EXIT
    curl -fsSL -o "$TEMPORAL/binutils.zip" "$BINUTILS_URL"
    echo "$BINUTILS_SHA256  $TEMPORAL/binutils.zip" | sha256sum -c --quiet -
    mkdir -p "$BINUTILS_DIR"
    unzip -q -o "$TEMPORAL/binutils.zip" -d "$BINUTILS_DIR" \
        "bin/mipsel-none-elf-as" "bin/mipsel-none-elf-ld" "bin/mipsel-none-elf-objcopy" \
        "bin/mipsel-none-elf-objdump" "bin/mipsel-none-elf-nm" "bin/mipsel-none-elf-readelf"
    chmod +x "$BINUTILS_DIR"/bin/*
fi

cd "$RAIZ"
python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

# Crea el prefijo de Wine una sola vez, sin ventanas ni mensajes de depuracion.
export WINEDEBUG=-all
wine wineboot --init >/dev/null 2>&1 || true

cat <<EOF
Instalacion terminada en ${RAIZ}.
Defina antes de usar las herramientas:
  export PATH="${BINUTILS_DIR}/bin:\$PATH"
  export BBLIT_TOOLCHAIN=<carpeta con psyq-4.4, maspsx y asm-differ>
  export BBLIT_DISC=<ruta al .bin del disco>      # tambien vale PSXDECOMP_TOOLCHAIN / PSXDECOMP_DISC
  export PYTHONUTF8=1
Despues:  .venv/bin/python tools/build.py split && .venv/bin/python tools/build.py build
EOF
