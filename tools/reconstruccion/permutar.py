"""Permutador: busca la forma de C que hace coincidir una funcion ``NON_MATCHING``.

``python tools/build.py permutar <funcion>`` parte del C vigente de la funcion, genera variantes con
mutaciones que conservan su significado (``permutar_mutaciones``), mide cada una con la misma
cadena y la misma puntuacion que ``diff`` (``permutar_evaluacion``) en varios hilos y avanza por
escalada con reinicios aleatorios. Solo el compilador real decide en cada paso.

Nunca modifica ``src/``. El resultado es ``build/permutar/<funcion>/mejor.c``, un candidato que una
persona aplica despues de leerlo.
"""

from __future__ import annotations

import hashlib
import random
import time
from collections import Counter
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from tools.reconstruccion import permutar_analisis as an
from tools.reconstruccion import permutar_c as c
from tools.reconstruccion import permutar_estado as est
from tools.reconstruccion import permutar_mutaciones as mut
from tools.reconstruccion.compilacion import HerramientasCompilacion
from tools.reconstruccion.diff import carpeta_de_trabajo, validar_funcion
from tools.reconstruccion.fuentes_c import MAX_BYTES_FUENTE
from tools.reconstruccion.infraestructura import Ejecutor
from tools.reconstruccion.permutar_evaluacion import (
    ObjetivoMedicion,
    ResultadoEvaluacion,
    evaluar,
    preparar_medicion,
)

MINUTOS_POR_OMISION = 10.0
MAX_PROCESOS = 16
MAX_ITERACIONES = 1_000_000
MAX_MINUTOS = 24 * 60.0
LIMITE_RONDAS_SIN_MEJORA = 12
RONDAS_VACIAS_MAXIMAS = 5
INTENTOS_POR_VARIANTE = 8
CANTIDADES_DE_MUTACIONES = (1, 2, 3)
PESOS_DE_CANTIDAD = (0.55, 0.30, 0.15)
SIN_LIMITE_DE_BYTES = 1 << 62
RONDAS_POR_AVISO = 25
Evaluador = Callable[[str, int], ResultadoEvaluacion]
"""Mide una variante: recibe su texto y el umbral bajo el que se comparan los bytes enlazados."""


@dataclass(frozen=True)
class Opciones:
    """Parametros de una busqueda.

    Attributes:
        iteraciones: Variantes a medir como maximo, o ``None`` si solo manda el tiempo.
        minutos: Duracion maxima de esta sesion en minutos, o ``None`` si solo mandan las iteraciones.
        procesos: Mediciones simultaneas.
        semilla: Semilla aleatoria, o ``None`` para elegir una.
        reanudar: Continuar la busqueda guardada en ``build/permutar/<funcion>/``.
    """

    iteraciones: int | None = None
    minutos: float | None = None
    procesos: int = 1
    semilla: int | None = None
    reanudar: bool = False


@dataclass
class Resumen:
    """Resultado de una busqueda.

    Attributes:
        funcion: Funcion permutada.
        semilla: Semilla usada.
        procesos: Mediciones simultaneas.
        iteraciones: Variantes medidas o descartadas en esta sesion.
        puntuacion_partida: Puntuacion del C original.
        puntuacion_mejor: Mejor puntuacion hallada.
        candidato: Ruta de ``mejor.c``.
        segundos: Duracion de esta sesion.
        descartadas: Variantes descartadas por motivo.
        interrumpida: Si la busqueda se interrumpio con Ctrl+C.
    """

    funcion: str
    semilla: int
    procesos: int
    iteraciones: int
    puntuacion_partida: int
    puntuacion_mejor: int
    candidato: Path
    segundos: float
    descartadas: Counter[str] = field(default_factory=Counter)
    interrumpida: bool = False

    @property
    def codigo_de_salida(self) -> int:
        """0 si llego a puntuacion 0, 1 si mejoro sin cerrar y 2 si no mejoro."""
        if self.puntuacion_mejor == 0:
            return 0
        return 1 if self.puntuacion_mejor < self.puntuacion_partida else 2


def validar_opciones(opciones: Opciones) -> Opciones:
    """
    Comprueba los limites de una busqueda y aplica el tiempo por omision si no hay ninguno.

    Contexto:
        Una busqueda nunca corre sin limite: si no se da ni ``--iteraciones`` ni ``--minutos``, dura
        ``MINUTOS_POR_OMISION``.

    Args:
        opciones (Opciones): Opciones pedidas.

    Returns:
        Opciones: Las mismas, con ``minutos`` fijado si faltaba todo limite.

    Raises:
        ValueError: Si algun valor esta fuera de rango.

    Ejemplo:
        opciones = validar_opciones(Opciones(procesos=4))
    """
    if opciones.iteraciones is not None and not 1 <= opciones.iteraciones <= MAX_ITERACIONES:
        raise ValueError(f"--iteraciones debe estar entre 1 y {MAX_ITERACIONES}")
    if opciones.minutos is not None and not 0 < opciones.minutos <= MAX_MINUTOS:
        raise ValueError(f"--minutos debe ser mayor que 0 y no pasar de {int(MAX_MINUTOS)}")
    if not 1 <= opciones.procesos <= MAX_PROCESOS:
        raise ValueError(f"--procesos debe estar entre 1 y {MAX_PROCESOS}")
    if opciones.semilla is not None and opciones.semilla < 0:
        raise ValueError("--semilla no puede ser negativa")
    if opciones.iteraciones is None and opciones.minutos is None:
        return Opciones(None, MINUTOS_POR_OMISION, opciones.procesos, opciones.semilla, opciones.reanudar)
    return opciones


def leer_cabeceras(raiz: Path) -> list[str]:
    """
    Lee el texto de las cabeceras de ``include/`` para reunir los tipos de los campos.

    Contexto:
        La inferencia de tipos del permutador se apoya en las estructuras que declaran.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        list[str]: Texto de cada cabecera ``.h`` (las que pasan del tamano permitido se omiten).

    Ejemplo:
        textos = leer_cabeceras(Path("."))
    """
    carpeta = raiz / "include"
    if not carpeta.is_dir():
        return []
    rutas = sorted(p for p in carpeta.rglob("*") if p.is_file() and p.suffix.lower() == ".h")
    return [
        ruta.read_text(encoding="utf-8", errors="replace")
        for ruta in rutas
        if ruta.stat().st_size <= MAX_BYTES_FUENTE
    ]


@dataclass
class _Variante:
    """Variante generada en una ronda."""

    texto: str
    arbol: c.Funcion
    mutaciones: list[str]
    resultado: ResultadoEvaluacion | None = None


class Busqueda:
    """Escalada con reinicios aleatorios sobre las variantes de una funcion."""

    def __init__(
        self,
        base: c.Funcion,
        tabla: an.TablaTipos,
        evaluador: Evaluador,
        *,
        estado: est.Estado,
        carpeta: Path,
        opciones: Opciones,
        salida: Callable[[str], None],
        reloj: Callable[[], float],
    ) -> None:
        """
        Prepara una busqueda a partir de un estado (nuevo o reanudado).

        Args:
            base (c.Funcion): Arbol del C original.
            tabla (an.TablaTipos): Tipos de campos y globales.
            evaluador (Evaluador): Mide una variante.
            estado (est.Estado): Contadores de partida.
            carpeta (Path): Carpeta de estado en disco.
            opciones (Opciones): Limites y paralelismo.
            salida (Callable[[str], None]): Destino de los avisos de progreso.
            reloj (Callable[[], float]): Reloj monotono en segundos.
        """
        self.base = base
        self.texto_base = c.imprimir_funcion(base)
        self.tabla = tabla
        self.evaluador = evaluador
        self.estado = estado
        self.carpeta = carpeta
        self.opciones = opciones
        self.salida = salida
        self.reloj = reloj
        self.actual = base
        self.texto_actual = self.texto_base
        self.arbol_mejor = base
        self.vistos: set[str] = {self._huella(self.texto_base)}
        self.descartadas: Counter[str] = Counter()
        self.iteraciones_sesion = 0
        self.rondas_vacias = 0
        self.barrido: Iterator[tuple[c.Funcion, str]] | None = None

    @staticmethod
    def _huella(texto: str) -> str:
        """Identifica un texto para no medirlo dos veces."""
        return hashlib.sha1(texto.encode("utf-8"), usedforsecurity=False).hexdigest()

    def adoptar(self, arbol_actual: c.Funcion, arbol_mejor: c.Funcion) -> None:
        """Fija desde donde continua una busqueda reanudada."""
        self.actual = arbol_actual
        self.texto_actual = c.imprimir_funcion(arbol_actual)
        self.arbol_mejor = arbol_mejor
        self.vistos.add(self._huella(self.texto_actual))

    def iniciar_barrido(self) -> None:
        """Recorre primero todos los vecinos de una mutacion del C original (ver ``mutaciones.vecinos``)."""
        self.barrido = mut.vecinos(self.base, self.tabla)

    def _siguiente_vecino(self) -> _Variante | None:
        """Da el proximo vecino no medido del barrido, o ``None`` cuando se agota."""
        for arbol, descripcion in self.barrido or ():
            texto = c.imprimir_funcion(arbol)
            huella = self._huella(texto)
            if huella not in self.vistos:
                self.vistos.add(huella)
                return _Variante(texto, arbol, [descripcion])
        self.barrido = None
        return None

    def _generar(self, indice: int) -> _Variante | None:
        """Genera una variante nueva (primero las del barrido), o ``None`` si no se logra una distinta."""
        if self.barrido is not None:
            vecino = self._siguiente_vecino()
            if vecino is not None:
                return vecino
        for intento in range(INTENTOS_POR_VARIANTE):
            azar = random.Random(f"{self.estado.semilla}-{self.estado.ronda}-{indice}-{intento}")  # noqa: S311
            cantidad = azar.choices(CANTIDADES_DE_MUTACIONES, weights=PESOS_DE_CANTIDAD)[0]
            arbol, aplicadas = mut.mutar(self.actual, self.tabla, azar, cantidad)
            texto = c.imprimir_funcion(arbol)
            huella = self._huella(texto)
            if aplicadas and huella not in self.vistos:
                self.vistos.add(huella)
                return _Variante(texto, arbol, aplicadas)
        return None

    def _medir(self, variantes: list[_Variante], pool: ThreadPoolExecutor) -> None:
        """Aplica el filtro de reglas y mide las variantes permitidas en paralelo."""
        pendientes: list[_Variante] = []
        for variante in variantes:
            if mut.variante_permitida(variante.texto, self.texto_base):
                pendientes.append(variante)
            else:
                variante.resultado = ResultadoEvaluacion(None, "regla")
        umbral = self.estado.puntuacion_actual
        medidas = pool.map(lambda v: self.evaluador(v.texto, umbral), pendientes)
        for variante, resultado in zip(pendientes, medidas, strict=True):
            variante.resultado = resultado

    def _registrar_mejora(self, variante: _Variante, puntuacion: int, posicion: int) -> None:
        """Guarda una variante que mejora el mejor resultado."""
        self.estado.puntuacion_mejor = puntuacion
        self.arbol_mejor = variante.arbol
        est.guardar_mejor(self.carpeta, variante.texto, puntuacion, self.estado.puntuacion_partida)
        iteracion = self.estado.iteraciones + posicion
        est.anadir_registro(self.carpeta, iteracion, puntuacion, variante.mutaciones)
        self.salida(f"iteracion {iteracion}: puntuacion {puntuacion} ({', '.join(variante.mutaciones)})")

    def _avanzar(self, variantes: list[_Variante], azar: random.Random) -> bool:
        """
        Actualiza la escalada con los resultados de una ronda.

        Returns:
            bool: Verdadero si alguna variante coincide con el original.
        """
        medidas = [
            (v, v.resultado.puntuacion)
            for v in variantes
            if v.resultado and v.resultado.puntuacion is not None
        ]
        for variante in variantes:
            if variante.resultado and variante.resultado.puntuacion is None:
                self.descartadas["regla" if variante.resultado.motivo == "regla" else "evaluacion"] += 1
        if not medidas:
            self.estado.rondas_sin_mejora += 1
            return False
        minimo = min(p for _, p in medidas if p is not None)
        mejores = [v for v, p in medidas if p == minimo]
        elegida = azar.choice(mejores)
        if minimo < self.estado.puntuacion_mejor:
            self._registrar_mejora(elegida, minimo, variantes.index(elegida) + 1)
        if minimo < self.estado.puntuacion_actual:
            self.estado.rondas_sin_mejora = 0
        else:
            self.estado.rondas_sin_mejora += 1
        if minimo <= self.estado.puntuacion_actual:
            self.actual, self.texto_actual = elegida.arbol, elegida.texto
            self.estado.puntuacion_actual = minimo
            est.guardar_actual(self.carpeta, elegida.texto)
        return minimo == 0

    def _reiniciar(self, azar: random.Random) -> None:
        """Reinicia la escalada desde el C original o desde el mejor hallado."""
        if azar.random() < 0.5:
            self.actual, self.estado.puntuacion_actual = self.base, self.estado.puntuacion_partida
        else:
            self.actual, self.estado.puntuacion_actual = self.arbol_mejor, self.estado.puntuacion_mejor
        self.texto_actual = c.imprimir_funcion(self.actual)
        self.estado.rondas_sin_mejora = 0
        est.guardar_actual(self.carpeta, self.texto_actual)

    def _limite_alcanzado(self, inicio: float) -> bool:
        """Indica si se agoto el numero de iteraciones o el tiempo de la sesion."""
        if self.opciones.iteraciones is not None and self.iteraciones_sesion >= self.opciones.iteraciones:
            return True
        if self.opciones.minutos is not None:
            return self.reloj() - inicio >= self.opciones.minutos * 60
        return False

    def _tamano_de_ronda(self) -> int:
        """Variantes de la proxima ronda: una por proceso sin pasar del limite de iteraciones."""
        if self.opciones.iteraciones is None:
            return self.opciones.procesos
        return min(self.opciones.procesos, self.opciones.iteraciones - self.iteraciones_sesion)

    def _ronda(self, pool: ThreadPoolExecutor) -> bool:
        """Genera, mide y aplica una ronda. Devuelve verdadero si alguna variante coincide."""
        azar = random.Random(f"{self.estado.semilla}-ronda-{self.estado.ronda}")  # noqa: S311
        tamano = self._tamano_de_ronda()
        generadas = [self._generar(i) for i in range(tamano)]
        variantes = [v for v in generadas if v is not None]
        self.iteraciones_sesion += tamano
        self.rondas_vacias = self.rondas_vacias + 1 if not variantes else 0
        self._medir(variantes, pool)
        coincide = self._avanzar(variantes, azar)
        self.estado.iteraciones += tamano
        self.estado.ronda += 1
        if not coincide and self.estado.rondas_sin_mejora >= LIMITE_RONDAS_SIN_MEJORA:
            self._reiniciar(azar)
        return coincide

    def ejecutar(self) -> Resumen:
        """
        Repite rondas hasta cerrar la funcion o agotar el limite.

        Returns:
            Resumen: Resultado de la sesion; el estado queda guardado en disco tras cada ronda.
        """
        inicio = self.reloj()
        acumulado = self.estado.segundos
        interrumpida = False
        pool = ThreadPoolExecutor(max_workers=self.opciones.procesos)
        try:
            while not self._limite_alcanzado(inicio) and self.rondas_vacias < RONDAS_VACIAS_MAXIMAS:
                coincide = self._ronda(pool)
                self.estado.segundos = acumulado + self.reloj() - inicio
                est.guardar_estado(self.carpeta, self.estado)
                if self.estado.ronda % RONDAS_POR_AVISO == 0:
                    self.salida(f"{self.iteraciones_sesion} variantes, mejor {self.estado.puntuacion_mejor}")
                if coincide:
                    break
        except KeyboardInterrupt:
            interrumpida = True
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
        self.estado.segundos = acumulado + self.reloj() - inicio
        est.guardar_estado(self.carpeta, self.estado)
        return Resumen(
            funcion=self.estado.funcion,
            semilla=self.estado.semilla,
            procesos=self.opciones.procesos,
            iteraciones=self.iteraciones_sesion,
            puntuacion_partida=self.estado.puntuacion_partida,
            puntuacion_mejor=self.estado.puntuacion_mejor,
            candidato=self.carpeta / "mejor.c",
            segundos=self.reloj() - inicio,
            descartadas=self.descartadas,
            interrumpida=interrumpida,
        )


def formatear_resumen(resumen: Resumen, raiz: Path) -> str:
    """
    Da el texto con que ``permutar`` cierra su salida.

    Contexto:
        Muestra iteraciones, puntuaciones, ruta del candidato y tiempo.

    Args:
        resumen (Resumen): Resultado de la busqueda.
        raiz (Path): Raiz del repositorio (la ruta del candidato se muestra relativa a ella).

    Returns:
        str: Lineas de resumen.

    Ejemplo:
        print(formatear_resumen(resumen, Path(".")))
    """
    if resumen.puntuacion_mejor == 0:
        veredicto = "coincide con el original"
    elif resumen.puntuacion_mejor < resumen.puntuacion_partida:
        veredicto = "mejora sin cerrar"
    else:
        veredicto = "sin mejora"
    descartadas = ", ".join(
        f"{motivo} {cantidad}" for motivo, cantidad in sorted(resumen.descartadas.items())
    )
    lineas = [
        f"{resumen.funcion}: {resumen.iteraciones} iteraciones en {resumen.segundos / 60:.1f} min "
        f"({resumen.procesos} procesos, semilla {resumen.semilla})",
        f"puntuacion de partida {resumen.puntuacion_partida}, mejor {resumen.puntuacion_mejor} ({veredicto})",
        f"candidato: {resumen.candidato.relative_to(raiz).as_posix()}",
        f"descartadas: {descartadas or 'ninguna'}",
    ]
    if resumen.interrumpida:
        lineas.append("busqueda interrumpida: reanude con --reanudar")
    return "\n".join(lineas)


def _medir_partida(objetivo: ObjetivoMedicion, texto_original: str, texto_reescrito: str) -> int:
    """Mide el C original y su reescritura; deben dar la misma puntuacion."""
    original = evaluar(objetivo, texto_original, comprobar_bytes_bajo=SIN_LIMITE_DE_BYTES)
    if original.puntuacion is None:
        raise ValueError(f"el C vigente de la funcion no se puede medir: {original.motivo}")
    reescrito = evaluar(objetivo, texto_reescrito, comprobar_bytes_bajo=SIN_LIMITE_DE_BYTES)
    if reescrito.puntuacion != original.puntuacion:
        raise ValueError(
            "la reescritura del C de la funcion no reproduce su puntuacion "
            f"({original.puntuacion} frente a {reescrito.puntuacion}): no se puede permutar sin riesgo"
        )
    return original.puntuacion


def permutar_funcion(
    raiz: Path,
    funcion: str,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
    *,
    opciones: Opciones,
    salida: Callable[[str], None] = print,
    reloj: Callable[[], float] = time.monotonic,
) -> Resumen:
    """
    Busca una forma de C que haga coincidir una funcion.

    Contexto:
        Implementa ``permutar``. Mide el C vigente, lo reescribe a un arbol, ejecuta la escalada y deja
        el candidato en ``build/permutar/<funcion>/mejor.c``. No escribe en ``src/``.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        opciones (Opciones): Limites, paralelismo, semilla y reanudacion.
        salida (Callable[[str], None], opcional): Destino de los avisos de progreso.
        reloj (Callable[[], float], opcional): Reloj monotono en segundos.

    Returns:
        Resumen: Resultado de la busqueda.

    Raises:
        ValueError: Si las opciones o el nombre no son validos, la funcion no tiene C que permutar, su C
            usa algo que el analizador no soporta, la reescritura no reproduce su puntuacion o no hay
            estado que reanudar.
        FuncionSinCError: Si la funcion sigue solo en ``INCLUDE_ASM``.
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si falla el ensamblado del objetivo.

    Ejemplo:
        resumen = permutar_funcion(Path("."), "f", h, script, ejecutar, opciones=Opciones(minutos=10))
    """
    validar_funcion(funcion)
    opciones = validar_opciones(opciones)
    carpeta = est.carpeta_de(raiz, funcion)
    with carpeta_de_trabajo(raiz, f"permutar-{funcion}-objetivo") as trabajo:
        objetivo = preparar_medicion(raiz, funcion, herramientas, script_diff, ejecutar, carpeta=trabajo)
        texto_original = objetivo.texto_archivo[objetivo.inicio : objetivo.fin]
        tabla = an.construir_tabla([*leer_cabeceras(raiz), objetivo.texto_archivo])
        base = c.analizar_funcion(texto_original, funcion, tabla.nombres_de_tipo)
        texto_base = c.imprimir_funcion(base)

        def evaluador(texto: str, umbral: int) -> ResultadoEvaluacion:
            return evaluar(objetivo, texto, comprobar_bytes_bajo=umbral)

        if opciones.reanudar:
            busqueda = _reanudar(
                carpeta,
                funcion,
                base,
                tabla=tabla,
                evaluador=evaluador,
                opciones=opciones,
                salida=salida,
                reloj=reloj,
            )
        else:
            partida = _medir_partida(objetivo, texto_original, texto_base)
            semilla = (
                opciones.semilla if opciones.semilla is not None else random.SystemRandom().randrange(1 << 31)
            )
            est.reiniciar(carpeta)
            estado = est.Estado(funcion, objetivo.archivo, semilla, partida, partida, partida)
            est.guardar_mejor(carpeta, texto_base, partida, partida)
            est.guardar_actual(carpeta, texto_base)
            est.guardar_estado(carpeta, estado)
            busqueda = Busqueda(
                base,
                tabla,
                evaluador,
                estado=estado,
                carpeta=carpeta,
                opciones=opciones,
                salida=salida,
                reloj=reloj,
            )
            busqueda.iniciar_barrido()
        if busqueda.estado.puntuacion_mejor == 0:
            return _resumen_cerrado(busqueda, opciones)
        return busqueda.ejecutar()


def _reanudar(
    carpeta: Path,
    funcion: str,
    base: c.Funcion,
    *,
    tabla: an.TablaTipos,
    evaluador: Evaluador,
    opciones: Opciones,
    salida: Callable[[str], None],
    reloj: Callable[[], float],
) -> Busqueda:
    """Reconstruye una busqueda guardada."""
    estado = est.cargar_estado(carpeta, funcion)
    actual = c.analizar_funcion(est.cargar_actual(carpeta), funcion, tabla.nombres_de_tipo)
    mejor_texto = (carpeta / "mejor.c").read_text(encoding="utf-8").split("\n", 1)[1].rstrip("\n")
    mejor = c.analizar_funcion(mejor_texto, funcion, tabla.nombres_de_tipo)
    busqueda = Busqueda(
        base, tabla, evaluador, estado=estado, carpeta=carpeta, opciones=opciones, salida=salida, reloj=reloj
    )
    busqueda.adoptar(actual, mejor)
    return busqueda


def _resumen_cerrado(busqueda: Busqueda, opciones: Opciones) -> Resumen:
    """Resumen de una funcion que ya coincide: no hay nada que buscar."""
    return Resumen(
        funcion=busqueda.estado.funcion,
        semilla=busqueda.estado.semilla,
        procesos=opciones.procesos,
        iteraciones=0,
        puntuacion_partida=busqueda.estado.puntuacion_partida,
        puntuacion_mejor=0,
        candidato=busqueda.carpeta / "mejor.c",
        segundos=0.0,
    )
