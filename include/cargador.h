#ifndef CARGADOR_H
#define CARGADOR_H

#include "common.h"

/*
 * Entrada de la tabla de sectores de la imagen (D_8005EE78, 113 entradas): posicion y tamano en
 * bytes del archivo cuyo identificador de nivel es el indice. func_80040EB4 la recorre al arrancar.
 */
typedef struct EntradaSector {
    u32 sector;
    u32 tamano;
} EntradaSector;

/*
 * Registro de 16 bytes por archivo (D_8005F200), construido a partir de EntradaSector.
 * +4 lo lee la pantalla de carga (archivo de la pantalla asociada); +6 lo deja en 1
 * func_80040EB4 y +8 copia el tamano. Los cuatro bytes de +0xC son la posicion de CD
 * en minuto, segundo y cuadro (CdlLOC) que func_800415A0 pasa a la lectura.
 */
typedef struct RegistroArchivo {
    s32 pad0;
    s16 pantalla;
    s16 habilitado;
    u32 tamano;
    u8 posicion[4];
} RegistroArchivo;

/*
 * Entrada de la cabecera del contenedor de niveles: tipo de seccion, tamano real y tamano
 * alineado a sectores. La cabecera ocupa el primer sector del archivo y func_800415A0 la copia
 * a la pila (hasta diez entradas) tras comprobar su suma de control.
 */
typedef struct EntradaSeccion {
    s32 tipo;
    u32 tamano;
    u32 alineado;
} EntradaSeccion;

#endif
