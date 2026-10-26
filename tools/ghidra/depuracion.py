"""Depuracion de candidatos a funcion contra las instrucciones reales del ejecutable.

Ghidra etiqueta como funcion puntos de entrada secundarios de las librerias (destinos de salto
dentro de una rutina) y el descubrimiento por prologo puede partir una funcion. Emitirlos como
simbolos hace que el desensamblador deje de tratar como codigo la region que sigue, asi que se
filtran aqui, con reglas puras sobre las palabras del segmento.
"""

from collections.abc import Collection
from dataclasses import dataclass, replace
from typing import Final

from tools.ghidra.dominio import (
    ALINEACION_FUNCION,
    DIRECCION_BASE,
    DIRECCION_ENTRADA,
    DIRECCION_FIN,
    FIN_CODIGO,
    TAMANO_MINIMO_FUNCION,
    Funcion,
    asignar_nombres,
)
from tools.ghidra.ejecutable import instruccion_valida, palabra_en
from tools.ghidra.zonas import FIN_JUEGO, INICIO_JUEGO


@dataclass(frozen=True, slots=True)
class Depuracion:
    """Resultado de filtrar los candidatos a funcion contra el codigo real.

    Contexto:
        Lo produce ``depurar_funciones`` y lo consume ``construir_simbolos``; el comando
        ``simbolos`` imprime los conteos.

    Attributes:
        funciones (list[Funcion]): Funciones validas, con el tamano ampliado si absorbieron fragmentos.
        fusionadas (list[int]): Direcciones de fragmentos absorbidos por la funcion anterior.
        descartadas (list[int]): Direcciones de candidatos que no son una funcion completa y de un
            tramo final de codigo sin salto (el codigo no se emite y queda registrado).
        huerfanos (list[tuple[int, int]]): Direccion y tamano de tramos de codigo de menos de 8
            bytes, sin salto, que preceden a una funcion con nombre oficial: no pueden ser una
            funcion ni unirse a ella (el nombre pertenece a su direccion), asi que no se emiten.
        rescatadas (list[int]): Inicios de codigo que ningun candidato cubria y que se anaden.
    """

    funciones: list[Funcion]
    fusionadas: list[int]
    descartadas: list[int]
    rescatadas: list[int]
    huerfanos: list[tuple[int, int]]


def es_terminador(instruccion: int) -> bool:
    """
    Indica si una instruccion MIPS cierra el flujo de una funcion.

    Contexto:
        Una funcion termina en un salto incondicional: ``jr`` (incluido ``jr ra``) o ``j``.

    Args:
        instruccion (int): Palabra de 32 bits.

    Returns:
        bool: Verdadero para ``jr rs`` y ``j destino``.

    Ejemplo:
        es_terminador(0x03E00008)  # True (jr ra)
    """
    es_salto = instruccion >> 26 == 2
    es_jr = instruccion & 0xFC1FFFFF == 0x08
    return es_salto or es_jr


def es_transferencia(instruccion: int) -> bool:
    """
    Indica si una instruccion MIPS siempre desvia el flujo y nunca sigue a la siguiente.

    Contexto:
        Una funcion puede cerrar con un salto de retorno (``jr``, ``j``) o con un salto
        incondicional hacia atras (un bucle final: ``b`` es ``beq zero,zero``). Una rama
        condicional (``bne``, ``blez``...) no cierra nada: si no se toma, el flujo cae en la
        instruccion siguiente, que pertenece a la misma funcion. ``jal``, ``jalr`` y las ramas
        con enlace vuelven y tampoco cuentan.

    Args:
        instruccion (int): Palabra de 32 bits.

    Returns:
        bool: Verdadero para ``jr``, ``j`` y las ramas que se toman siempre: ``beq`` y
            ``beql`` con ambos registros iguales, ``bgez`` y ``bgezl`` sobre ``zero``.

    Ejemplo:
        es_transferencia(0x1000FFFE)  # True (b hacia atras)
    """
    if es_terminador(instruccion):
        return True
    operacion = instruccion >> 26
    rs = (instruccion >> 21) & 0x1F
    rt = (instruccion >> 16) & 0x1F
    if operacion in (4, 0x14):
        return rs == rt
    return operacion == 1 and rs == 0 and rt in (1, 3)


def _cierra(segmento: bytes, inicio: int, fin: int) -> bool:
    """
    Comprueba que el tramo ``[inicio, fin)`` acabe como una funcion completa.

    Su ultima instruccion real (antes de la ranura de retardo) debe ser una transferencia de
    control y el tramo debe contener una salida real: un ``jr`` o un ``j``. Mirar solo la
    existencia de un salto aceptaria fragmentos que contienen un retorno en medio.
    """
    ultima = min(fin, DIRECCION_FIN) - TAMANO_MINIMO_FUNCION
    if ultima < inicio or not es_transferencia(palabra_en(segmento, ultima)):
        return False
    return any(
        es_terminador(palabra_en(segmento, direccion))
        for direccion in range(inicio, ultima + 1, ALINEACION_FUNCION)
    )


def _cuerpo_termina(segmento: bytes, funcion: Funcion) -> bool:
    """Comprueba que el cuerpo de la funcion cierre como una funcion completa."""
    return _cierra(segmento, funcion.direccion, funcion.direccion + funcion.tamano)


def _anterior_termina(segmento: bytes, previa: Funcion, frontera: int) -> bool:
    """Comprueba que la funcion previa, hasta la frontera, cierre como una funcion completa."""
    return _cierra(segmento, previa.direccion, frontera)


def _prolongar(segmento: bytes, funcion: Funcion, limite: int) -> Funcion:
    """
    Alarga el cuerpo hasta el primer cierre valido antes del siguiente candidato.

    Ghidra corta el cuerpo de las funciones con tabla de saltos en el ultimo destino que
    encuentra, y el epilogo queda fuera. Si el tramo hasta el limite no cierra, se devuelve
    la funcion sin cambios.
    """
    for fin in range(
        funcion.direccion + funcion.tamano + ALINEACION_FUNCION, min(limite, DIRECCION_FIN) + 1, 4
    ):
        if _cierra(segmento, funcion.direccion, fin):
            return replace(funcion, tamano=fin - funcion.direccion)
    return funcion


def _recortar_solapes(funciones: list[Funcion]) -> list[Funcion]:
    """Recorta cada funcion al inicio de la siguiente: dos funciones nunca comparten bytes."""
    ordenadas = sorted(funciones, key=lambda f: f.direccion)
    limites = [f.direccion for f in ordenadas[1:]] + [DIRECCION_FIN] * bool(ordenadas)
    return [
        replace(f, tamano=min(f.tamano, limite - f.direccion))
        for f, limite in zip(ordenadas, limites, strict=True)
    ]


def _primer_no_cero(segmento: bytes, inicio: int, fin: int) -> int | None:
    """Primera direccion del hueco cuya palabra no es relleno de ceros."""
    direccion = inicio
    while direccion < fin and palabra_en(segmento, direccion) == 0:
        direccion += ALINEACION_FUNCION
    return direccion if direccion < fin else None


def _completar_huecos(
    validas: list[Funcion], segmento: bytes
) -> tuple[list[Funcion], list[int], list[int], list[tuple[int, int]]]:
    """
    Cubre el codigo que queda entre funciones o lo deja registrado.

    Cada tramo entre funciones (tras saltar el relleno de ceros) acaba en exactamente un
    destino: datos incrustados (primera palabra que no decodifica) y tramos finales sin salto,
    a ``huerfanos``; rutina completa, a una funcion nueva; cabecera de la funcion siguiente, unida
    a ella si no tiene nombre oficial (el nombre pertenece a su direccion) o, si lo tiene, rutina
    propia que continua en ella, salvo que mida menos de 8 bytes, que va a ``huerfanos``.
    """
    completas: list[Funcion] = []
    rescatadas: list[int] = []
    perdidas: list[int] = []
    huerfanos: list[tuple[int, int]] = []
    cursor = DIRECCION_BASE
    for siguiente in [*validas, None]:
        limite = FIN_CODIGO if siguiente is None else siguiente.direccion
        inicio = _primer_no_cero(segmento, cursor, limite) if limite > cursor else None
        actual = siguiente
        if inicio is not None:
            tamano = limite - inicio
            termina = _cierra(segmento, inicio, limite)
            if not instruccion_valida(palabra_en(segmento, inicio), inicio):
                huerfanos.append((inicio, tamano))
            elif siguiente is not None and not termina and not siguiente.nombre_oficial:
                actual = replace(siguiente, direccion=inicio, tamano=siguiente.tamano + tamano)
                rescatadas.append(inicio)
            elif siguiente is None and not termina:
                perdidas.append(inicio)
                huerfanos.append((inicio, tamano))
            elif not termina and tamano < TAMANO_MINIMO_FUNCION:
                huerfanos.append((inicio, tamano))
            else:
                completas.append(_funcion_nueva(inicio, tamano))
                rescatadas.append(inicio)
        if actual is not None:
            completas.append(actual)
            cursor = max(cursor, actual.direccion + actual.tamano)
    return completas, rescatadas, perdidas, huerfanos


def _funcion_nueva(direccion: int, tamano: int) -> Funcion:
    """Funcion del juego sin identificar para un hueco de codigo."""
    return Funcion(direccion, f"FUN_{direccion:08x}", tamano, False, "", 0, False, "")


def depurar_funciones(funciones: list[Funcion], segmento: bytes) -> Depuracion:
    """
    Separa las funciones reales de los fragmentos interiores que Ghidra etiqueta como funcion.

    Contexto:
        Las firmas de libreria marcan puntos de entrada secundarios (destinos de salto dentro de
        una rutina) y el descubrimiento por prologo puede partir una funcion. Un candidato
        pegado al final de una funcion que no termina en salto es continuacion de ella: se
        fusiona ampliando su tamano. Un candidato de menos de ``TAMANO_MINIMO_FUNCION`` bytes que
        sigue a una funcion terminada se descarta. Los demas quedan abiertos hasta el final:
        pueden absorber los fragmentos que les siguen, y solo se emiten si su cuerpo definitivo
        contiene un terminador con su ranura de retardo; si no, se descartan junto con lo que
        absorbieron. La unica excepcion es el punto de entrada de la cabecera, cuyo codigo de
        arranque llama a ``main`` y no retorna. Emitir fragmentos como funciones hace que el
        desensamblador deje de tratar como codigo la region que sigue.

    Args:
        funciones (list[Funcion]): Candidatos en cualquier orden.
        segmento (bytes): Segmento cargado, de ``leer_segmento``.

    Returns:
        Depuracion: Funciones validas ordenadas por direccion y las direcciones fusionadas
            y descartadas.

    Raises:
        ValueError: Si hay direcciones duplicadas o el segmento no tiene el tamano esperado.

    Ejemplo:
        limpias = depurar_funciones(funciones, leer_segmento(ruta)).funciones
    """
    asignar_nombres(funciones)
    abiertas: list[Funcion] = []
    absorbidas: dict[int, list[int]] = {}
    descartadas: list[int] = []
    for candidata in sorted(funciones, key=lambda f: f.direccion):
        previa = abiertas[-1] if abiertas else None
        pegada = previa is not None and candidata.direccion <= previa.direccion + previa.tamano
        if previa is not None and pegada and not _anterior_termina(segmento, previa, candidata.direccion):
            fin = max(previa.direccion + previa.tamano, candidata.direccion + candidata.tamano)
            abiertas[-1] = replace(previa, tamano=fin - previa.direccion)
            absorbidas.setdefault(previa.direccion, []).append(candidata.direccion)
        elif candidata.tamano >= TAMANO_MINIMO_FUNCION:
            abiertas.append(candidata)
        else:
            descartadas.append(candidata.direccion)
    validas: list[Funcion] = []
    fusionadas: list[int] = []
    for indice, original in enumerate(abiertas):
        siguiente = abiertas[indice + 1].direccion if indice + 1 < len(abiertas) else DIRECCION_FIN
        recortada = replace(original, tamano=min(original.tamano, siguiente - original.direccion))
        funcion = (
            recortada if _cuerpo_termina(segmento, recortada) else _prolongar(segmento, recortada, siguiente)
        )
        propias = absorbidas.get(funcion.direccion, [])
        if funcion.direccion == DIRECCION_ENTRADA or _cuerpo_termina(segmento, funcion):
            validas.append(funcion)
            fusionadas.extend(propias)
        else:
            descartadas.extend([funcion.direccion, *propias])
    completas, rescatadas, perdidas, huerfanos = _completar_huecos(validas, segmento)
    return Depuracion(
        _recortar_solapes(completas),
        sorted(fusionadas),
        sorted({*descartadas, *perdidas}),
        rescatadas,
        huerfanos,
    )


@dataclass(frozen=True, slots=True)
class Refinamiento:
    """Resultado de aplicar a las funciones depuradas lo que revelan las tablas de punteros.

    Contexto:
        Lo produce ``refinar_con_tablas`` y lo consumen el comando ``simbolos`` (para escribir la
        tabla) y el informe de funciones nuevas.

    Attributes:
        funciones (list[Funcion]): Funciones tras partir los bloques madre y fusionar las continuaciones.
        nuevas (list[tuple[int, int]]): Pares ``(direccion, madre)`` de cada funcion creada al partir.
        fusionadas (list[tuple[int, int]]): Pares ``(absorbida, principal)`` de continuaciones fundidas.
        por_retorno (list[tuple[int, int]]): Pares ``(direccion, madre)`` de rutinas separadas porque
            la anterior termina con un retorno completo y nada cruza ese punto.
        conflictos (list[tuple[int, str]]): Destinos que no se aplicaron y la razon.
    """

    funciones: list[Funcion]
    nuevas: list[tuple[int, int]]
    fusionadas: list[tuple[int, int]]
    por_retorno: list[tuple[int, int]]
    conflictos: list[tuple[int, str]]


def _destinos_de_llamada(segmento: bytes) -> set[int]:
    """Destinos de todos los ``jal`` del codigo: direcciones que alguien llama como funcion."""
    destinos: set[int] = set()
    for direccion in range(DIRECCION_BASE, FIN_CODIGO, ALINEACION_FUNCION):
        palabra = palabra_en(segmento, direccion)
        if palabra >> 26 == 3:
            destinos.add((direccion & 0xF0000000) | ((palabra & 0x03FFFFFF) << 2))
    return destinos


def _salta_dentro(segmento: bytes, origen: Funcion, destino: Funcion) -> bool:
    """Indica si el cuerpo de ``origen`` bifurca a una direccion interior de ``destino``.

    Una rama condicional que sale de la funcion, o un ``j`` hacia el interior de otra (no a su
    inicio, que seria una llamada de cola), solo los emite un compilador dentro de una funcion.
    """
    fin = destino.direccion + destino.tamano
    for direccion in range(origen.direccion, origen.direccion + origen.tamano, ALINEACION_FUNCION):
        palabra = palabra_en(segmento, direccion)
        operacion = palabra >> 26
        if operacion in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
            inmediato = palabra & 0xFFFF
            con_signo = inmediato - 0x10000 if inmediato & 0x8000 else inmediato
            objetivo = direccion + 4 + 4 * con_signo
        elif operacion == 2:
            objetivo = (direccion & 0xF0000000) | ((palabra & 0x03FFFFFF) << 2)
            if objetivo == destino.direccion:
                continue
        else:
            continue
        if destino.direccion <= objetivo < fin:
            return True
    return False


def refinar_con_tablas(
    funciones: list[Funcion],
    segmento: bytes,
    destinos_de_puntero: Collection[int],
    destinos_de_salto: Collection[int],
) -> Refinamiento:
    """
    Parte los bloques que contienen rutinas de tablas de punteros y une las continuaciones.

    Contexto:
        Ademas separa las rutinas pegadas sin tabla (ver ``_partir_por_retornos``). Las rutinas hoja a las
        que se llega por una tabla de punteros a funcion no tienen prologo ni
        ningun ``jal`` que las delate, y la depuracion las deja fundidas en la funcion anterior. Todo
        destino de esas tablas dentro del rango del juego es inicio de funcion. En sentido contrario,
        una funcion que solo existe porque un ``switch`` de la anterior cae justo en su primera
        instruccion, o a la que la anterior bifurca con ramas condicionales, es una continuacion:
        nadie la llama (ni ``jal`` ni tabla de punteros) y se funde.

    Args:
        funciones (list[Funcion]): Funciones depuradas (``Depuracion.funciones``).
        segmento (bytes): Segmento cargado, de ``leer_segmento``.
        destinos_de_puntero (Collection[int]): Destinos de las tablas de punteros a funcion.
        destinos_de_salto (Collection[int]): Destinos de las tablas de ``switch``.

    Returns:
        Refinamiento: Funciones resultantes, las creadas, las fusionadas y los destinos rechazados
        (fuera del rango del juego, desalineados, sin funcion que los contenga o cuya pieza
        anterior no cierra como una funcion completa).

    Raises:
        ValueError: Si el segmento no tiene el tamano esperado.

    Ejemplo:
        refinado = refinar_con_tablas(depuracion.funciones, segmento, destinos, saltos)
    """
    ordenadas = sorted(funciones, key=lambda f: f.direccion)
    conflictos: list[tuple[int, str]] = []
    puntos: dict[int, list[int]] = {}
    inicios = {f.direccion for f in ordenadas}
    for destino in sorted(set(destinos_de_puntero)):
        if destino % ALINEACION_FUNCION:
            conflictos.append((destino, "destino desalineado"))
        elif not INICIO_JUEGO <= destino < FIN_JUEGO:
            conflictos.append((destino, "fuera del rango del juego"))
        elif destino not in inicios:
            madre = next((f for f in ordenadas if f.direccion < destino < f.direccion + f.tamano), None)
            if madre is None:
                conflictos.append((destino, "ninguna funcion lo contiene"))
            else:
                puntos.setdefault(madre.direccion, []).append(destino)
    resultado: list[Funcion] = []
    nuevas: list[tuple[int, int]] = []
    for funcion in ordenadas:
        resultado.extend(_partir(segmento, funcion, puntos.get(funcion.direccion, []), nuevas, conflictos))
    resultado, fusionadas = _fusionar_continuaciones(
        segmento, resultado, _destinos_de_llamada(segmento) | set(destinos_de_puntero), set(destinos_de_salto)
    )
    resultado, por_retorno = _partir_por_retornos(segmento, resultado, set(destinos_de_salto))
    return Refinamiento(resultado, nuevas, fusionadas, por_retorno, sorted(conflictos))


def _partir(
    segmento: bytes,
    funcion: Funcion,
    puntos: list[int],
    nuevas: list[tuple[int, int]],
    conflictos: list[tuple[int, str]],
) -> list[Funcion]:
    """Parte una funcion en los puntos dados, siempre que cada pieza cierre como funcion completa."""
    fin = funcion.direccion + funcion.tamano
    inicio = funcion.direccion
    piezas: list[Funcion] = []
    aceptados: list[int] = []
    for punto in sorted(puntos):
        if _cierra(segmento, inicio, punto) and _cierra(segmento, punto, fin):
            if piezas:
                piezas.append(_funcion_nueva(inicio, punto - inicio))
            else:
                piezas.append(replace(funcion, tamano=punto - inicio))
            inicio = punto
            aceptados.append(punto)
        else:
            conflictos.append((punto, "la pieza anterior o la siguiente no cierra como funcion"))
    if not aceptados:
        return [funcion]
    piezas.append(_funcion_nueva(inicio, fin - inicio))
    nuevas.extend((p, funcion.direccion) for p in aceptados)
    return piezas


def _fusionar_continuaciones(
    segmento: bytes, funciones: list[Funcion], llamadas: set[int], saltos: set[int]
) -> tuple[list[Funcion], list[tuple[int, int]]]:
    """Une cada funcion del juego que es continuacion de la anterior (ver ``refinar_con_tablas``)."""
    resultado: list[Funcion] = []
    fusionadas: list[tuple[int, int]] = []
    for funcion in funciones:
        previa = resultado[-1] if resultado else None
        es_continuacion = (
            previa is not None
            and INICIO_JUEGO <= funcion.direccion < FIN_JUEGO
            and previa.direccion + previa.tamano == funcion.direccion
            and funcion.direccion not in llamadas
            and (funcion.direccion in saltos or _salta_dentro(segmento, previa, funcion))
        )
        if es_continuacion and previa is not None:
            resultado[-1] = replace(previa, tamano=previa.tamano + funcion.tamano)
            fusionadas.append((funcion.direccion, previa.direccion))
        else:
            resultado.append(funcion)
    return resultado, fusionadas


_JR_RA: Final[int] = 0x03E00008
_RAMAS_CONDICIONALES: Final[frozenset[int]] = frozenset({1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17})


def _objetivo_de_salto(direccion: int, palabra: int) -> int | None:
    """Destino de una rama o de un ``j``; ``None`` si la instruccion no bifurca (``jal`` no cuenta)."""
    operacion = palabra >> 26
    if operacion in _RAMAS_CONDICIONALES:
        inmediato = palabra & 0xFFFF
        return direccion + 4 + 4 * (inmediato - 0x10000 if inmediato & 0x8000 else inmediato)
    if operacion == 2:
        return (direccion & 0xF0000000) | ((palabra & 0x03FFFFFF) << 2)
    return None


def _puntos_de_retorno(segmento: bytes, funcion: Funcion, saltos: set[int]) -> list[int]:
    """Puntos de ``funcion`` donde empieza una rutina distinta tras un retorno completo."""
    inicio, fin = funcion.direccion, funcion.direccion + funcion.tamano
    bifurcaciones = [
        (direccion, objetivo)
        for direccion in range(inicio, fin, ALINEACION_FUNCION)
        if (objetivo := _objetivo_de_salto(direccion, palabra_en(segmento, direccion))) is not None
        and inicio <= objetivo < fin
    ]
    internos = sorted(s for s in saltos if inicio <= s < fin)
    puntos: list[int] = []
    for punto in range(inicio + TAMANO_MINIMO_FUNCION, fin - TAMANO_MINIMO_FUNCION + 1, ALINEACION_FUNCION):
        ranura = palabra_en(segmento, punto - 4)
        if palabra_en(segmento, punto - 8) != _JR_RA or _objetivo_de_salto(punto - 4, ranura) is not None:
            continue
        cruza = any((origen < punto) != (objetivo < punto) for origen, objetivo in bifurcaciones)
        con_tabla = bool(internos) and internos[0] <= punto <= internos[-1]
        if not cruza and not con_tabla:
            puntos.append(punto)
    return puntos


def _partir_por_retornos(
    segmento: bytes, funciones: list[Funcion], saltos: set[int]
) -> tuple[list[Funcion], list[tuple[int, int]]]:
    """
    Separa las rutinas que quedaron pegadas tras un ``jr ra`` sin nada que las una.

    Contexto:
        Una funcion de un solo cuerpo no puede tener codigo alcanzable solo despues de su retorno:
        todo lo que sigue a un ``jr ra`` con su ranura es el destino de alguna rama anterior. Si
        ninguna rama ni ``j`` cruza ese punto, ni hay destinos de ``switch`` a ambos lados, el
        codigo posterior solo puede alcanzarse llamandolo: es otra rutina. Las funciones con varios
        retornos legitimos siempre tienen ramas que cruzan el punto.
    """
    resultado: list[Funcion] = []
    separadas: list[tuple[int, int]] = []
    for funcion in funciones:
        piezas = [funcion]
        if INICIO_JUEGO <= funcion.direccion < FIN_JUEGO and funcion.tamano >= 2 * TAMANO_MINIMO_FUNCION:
            inicio, fin = funcion.direccion, funcion.direccion + funcion.tamano
            for punto in _puntos_de_retorno(segmento, funcion, saltos):
                if _cierra(segmento, inicio, punto) and _cierra(segmento, punto, fin):
                    piezas[-1] = replace(piezas[-1], tamano=punto - inicio)
                    piezas.append(_funcion_nueva(punto, fin - punto))
                    separadas.append((punto, funcion.direccion))
                    inicio = punto
        resultado.extend(piezas)
    return resultado, separadas
