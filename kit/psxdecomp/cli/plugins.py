"""Extensiones del proyecto: subcomandos y ganchos declarados en la seccion ``[plugins]``.

Capa de aplicacion de la CLI. Cada referencia del manifiesto tiene la forma ``paquete.modulo:funcion``
y se resuelve con ``importlib`` en el momento de usarla, de modo que el kit nunca depende de ningun
modulo del proyecto consumidor. Los contratos son:

* ``subcomandos``: ``registrar(subparsers, proyecto)`` anade subcomandos al analizador; cada uno fija
  ``manejador=funcion`` con ``set_defaults``, y esa funcion recibe un ``Contexto`` y devuelve el codigo
  de retorno.
* ``antes_de_construir``: ``gancho(proyecto)`` se invoca al empezar ``build``, antes de compilar.
* ``despues_de_verificar``: ``gancho(proyecto, resultado)`` se invoca al terminar ``verify`` con su
  ``ResultadoVerificacion``, coincida o no.

Un gancho que lanza ``ValueError``, ``ProcesoError`` u ``OSError`` hace que la orden termine con el
mismo mensaje de una linea que cualquier otro error esperado. Resolver un modulo exige que este en la
raiz del proyecto: esa carpeta se agrega a ``sys.path`` solo mientras dura la importacion.
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from psxdecomp.cli.contexto import ResultadoVerificacion
from psxdecomp.cli.errores import PluginInvalidoError
from psxdecomp.dominio import Proyecto

if TYPE_CHECKING:
    Subparsers = argparse._SubParsersAction[argparse.ArgumentParser]


@contextmanager
def _raiz_en_ruta(raiz: Path) -> Iterator[None]:
    """Pone la raiz del proyecto al principio de ``sys.path`` mientras dura el bloque."""
    texto = str(raiz)
    agregada = texto not in sys.path
    if agregada:
        sys.path.insert(0, texto)
    try:
        yield
    finally:
        if agregada and texto in sys.path:
            sys.path.remove(texto)


def resolver_referencia(referencia: str, raiz: Path) -> Callable[..., Any]:
    """
    Resuelve una referencia ``modulo:funcion`` del manifiesto a la funcion que nombra.

    Contexto:
        Las usan el registro de subcomandos y los ganchos. El manifiesto ya valido la forma de la
        referencia; aqui se comprueba que el modulo existe y que el nombre es invocable.

    Args:
        referencia (str): Referencia ``paquete.modulo:funcion``.
        raiz (Path): Raiz del proyecto, donde se busca el modulo ademas del camino normal.

    Returns:
        Callable[..., Any]: La funcion referenciada.

    Raises:
        PluginInvalidoError: Si el modulo no se puede importar, falla al cargarse con cualquier
            excepcion (error de sintaxis o de ejecucion de nivel de modulo), o el nombre no existe o no
            es invocable. El mensaje nombra la referencia y, si hubo fallo, solo el tipo de excepcion;
            nunca rutas de la maquina ni la traza.

    Ejemplo:
        registrar = resolver_referencia("paquete.modulo:registrar", Path("."))
    """
    modulo, _, nombre = referencia.partition(":")
    importlib.invalidate_caches()
    with _raiz_en_ruta(raiz):
        try:
            cargado = importlib.import_module(modulo)
        except ImportError:
            raise PluginInvalidoError(
                f"plugin '{referencia}': no se pudo importar el modulo '{modulo}'"
            ) from None
        except Exception as error:
            # Un plugin ajeno puede fallar al cargarse de cualquier manera (sintaxis, codigo de nivel de
            # modulo). Se informa solo el tipo del fallo: su texto suele llevar rutas de la maquina o
            # lineas de codigo del proyecto. Se deja fuera la traza para que la orden termine con el mismo
            # mensaje de una linea que cualquier otro error esperado.
            raise PluginInvalidoError(
                f"plugin '{referencia}': el modulo '{modulo}' fallo al cargarse ({type(error).__name__})"
            ) from None
    funcion = getattr(cargado, nombre, None)
    if not callable(funcion):
        raise PluginInvalidoError(f"plugin '{referencia}': '{nombre}' no existe o no es invocable")
    return funcion  # type: ignore[no-any-return]  # callable() no estrecha a un Callable tipado


def registrar_subcomandos(subparsers: Subparsers, proyecto: Proyecto) -> None:
    """
    Deja que cada plugin de ``subcomandos`` anada los suyos al analizador.

    Contexto:
        Se invoca al construir el analizador, despues de los subcomandos comunes. Un plugin que repite
        el nombre de un subcomando existente es un error, no una sustitucion silenciosa.

    Args:
        subparsers (Subparsers): Registro de subcomandos del analizador.
        proyecto (Proyecto): Manifiesto del proyecto; se pasa tal cual a cada plugin.

    Raises:
        PluginInvalidoError: Si un plugin no se puede cargar, repite un subcomando o no fija un manejador.

    Ejemplo:
        registrar_subcomandos(parser.add_subparsers(dest="orden"), proyecto)
    """
    for referencia in proyecto.plugins.subcomandos:
        registrar = resolver_referencia(referencia, proyecto.raiz)
        antes = set(subparsers.choices)
        try:
            registrar(subparsers, proyecto)
        except argparse.ArgumentError as error:
            raise PluginInvalidoError(f"plugin '{referencia}': {error.message}") from None
        for nombre in set(subparsers.choices) - antes:
            if subparsers.choices[nombre].get_default("manejador") is None:
                raise PluginInvalidoError(
                    f"plugin '{referencia}': el subcomando '{nombre}' no fija un manejador"
                )


def ejecutar_antes_de_construir(proyecto: Proyecto) -> None:
    """
    Invoca los ganchos ``antes_de_construir`` en el orden declarado.

    Contexto:
        ``build`` los llama antes de compilar; ``split`` ya dejo el ensamblador y el script del enlazador.

    Args:
        proyecto (Proyecto): Manifiesto del proyecto.

    Raises:
        PluginInvalidoError: Si un gancho no se puede cargar.

    Ejemplo:
        ejecutar_antes_de_construir(proyecto)
    """
    for referencia in proyecto.plugins.antes_de_construir:
        resolver_referencia(referencia, proyecto.raiz)(proyecto)


def ejecutar_despues_de_verificar(proyecto: Proyecto, resultado: ResultadoVerificacion) -> None:
    """
    Invoca los ganchos ``despues_de_verificar`` en el orden declarado.

    Contexto:
        ``verify`` los llama con su resultado, tambien cuando las huellas no coinciden o el ejecutable
        reconstruido no existe; el codigo de retorno de ``verify`` depende solo de ese resultado, salvo
        que un gancho falle con un error esperado.

    Args:
        proyecto (Proyecto): Manifiesto del proyecto.
        resultado (ResultadoVerificacion): Resultado de la verificacion.

    Raises:
        PluginInvalidoError: Si un gancho no se puede cargar.

    Ejemplo:
        ejecutar_despues_de_verificar(proyecto, ResultadoVerificacion(True, "OK"))
    """
    for referencia in proyecto.plugins.despues_de_verificar:
        resolver_referencia(referencia, proyecto.raiz)(proyecto, resultado)


_PATRON_NOMBRE_SUBSISTEMA = re.compile(r"^[^\x00-\x1f|`]{1,64}$")


def resolver_agrupador_de_subsistemas(proyecto: Proyecto) -> Callable[[str], str] | None:
    """
    Resuelve el gancho ``entrada_progreso`` a la regla que agrupa los archivos C en subsistemas.

    Contexto:
        La orden ``progreso`` lo usa en lugar del sufijo de ``convenciones.sufijo_subsistema`` cuando el
        manifiesto lo declara. El contrato es ``entrada_progreso(proyecto, archivo)``: recibe la ruta
        relativa de un archivo C y devuelve el nombre de su subsistema. El nombre acaba en una tabla
        Markdown, por eso se admite solo texto de 1 a 64 caracteres sin controles, barras verticales
        ni comillas invertidas.

    Args:
        proyecto (Proyecto): Manifiesto del proyecto.

    Returns:
        Callable[[str], str] | None: La regla, o ``None`` si el manifiesto no declara el gancho.

    Raises:
        PluginInvalidoError: Si el gancho no se puede cargar (al resolverlo) o, al aplicarlo, devuelve algo
            que no es un nombre admitido.

    Ejemplo:
        agrupador = resolver_agrupador_de_subsistemas(proyecto)
    """
    referencia = proyecto.plugins.entrada_progreso
    if referencia is None:
        return None
    gancho = resolver_referencia(referencia, proyecto.raiz)

    def agrupar(archivo: str) -> str:
        nombre = gancho(proyecto, archivo)
        if not isinstance(nombre, str) or _PATRON_NOMBRE_SUBSISTEMA.fullmatch(nombre) is None:
            raise PluginInvalidoError(
                f"plugin '{referencia}': debe devolver el nombre del subsistema como texto de 1 a 64 "
                "caracteres sin barras verticales ni comillas invertidas"
            )
        return nombre

    return agrupar
