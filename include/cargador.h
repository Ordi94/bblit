#ifndef CARGADOR_H
#define CARGADOR_H

#include "common.h"

/*
 * Entrada de la tabla de sectores de la imagen (D_8005EE78, 113 entradas): posicion y tamano en
 * bytes del archivo cuyo identificador de nivel es el indice. ConstruirRegistrosArchivo la recorre al arrancar.
 */
typedef struct EntradaSector {
    u32 sector;
    u32 tamano;
} EntradaSector;

/*
 * Registro de 16 bytes por archivo (D_8005F200), construido a partir de EntradaSector.
 * +4 lo lee la pantalla de carga (archivo de la pantalla asociada); +6 lo deja en 1
 * ConstruirRegistrosArchivo y +8 copia el tamano. Los cuatro bytes de +0xC son la posicion de CD
 * en minuto, segundo y cuadro (CdlLOC) que CargarContenedor pasa a la lectura.
 */
typedef struct RegistroArchivo {
    s32 pad0;
    s16 pantalla;
    s16 habilitado;
    u32 tamano;
    u8 posicion[4];
} RegistroArchivo;

extern RegistroArchivo D_8005F200[];

/*
 * Entrada de la cabecera del contenedor de niveles: tipo de seccion, tamano real y tamano
 * alineado a sectores. La cabecera ocupa el primer sector del archivo y CargarContenedor la copia
 * a la pila (hasta diez entradas) tras comprobar su suma de control.
 */
typedef struct EntradaSeccion {
    s32 tipo;
    u32 tamano;
    u32 alineado;
} EntradaSeccion;

/*
 * Nodos de las tres listas de un contenedor ya cargado (ResolverReferenciasContenedor). Todos empiezan con el
 * enlace al siguiente nodo (+0) y un identificador de 16 bits (+4); el resto de los campos son
 * los que esa rutina convierte de identificador a desplazamiento.
 * NodoA mide 0x10 bytes: cinco referencias de 16 bits a NodoB desde +6 (0xFFF0 cierra la serie).
 */
typedef struct NodoA {
    struct NodoA* sig;
    u16 id;
    u16 ref[5];
} NodoA;

/* NodoB: referencia a NodoC en +0xA y desplazamiento ya convertido en +0x1E. */
typedef struct NodoB {
    struct NodoB* sig;
    u16 id;
    u8 pad6[4];
    u16 refC;
    u8 padC[0x12];
    s16 desplazamiento;
} NodoB;

/*
 * NodoC mide 0x24 bytes (la resta de punteros entre nodos divide entre ese tamano): referencia
 * a NodoA en +6 y, con la bandera 0x20 de +0x18, dos referencias mas en +0x1C y +0x20.
 */
typedef struct NodoC {
    struct NodoC* sig;
    u16 id;
    u16 refA;
    u8 pad8[0x10];
    u32 banderas;
    u32 refA1;
    u32 refA2;
} NodoC;

/* Contenedor cargado: clase en +0x2C y las cabezas de las tres listas en +0xF4, +0xF8 y +0xFC. */
typedef struct ContenedorCarga {
    u8 pad0[0x2C];
    u16 clase;
    u8 pad2E[0xF4 - 0x2E];
    NodoA* listaA;
    NodoB* listaB;
    NodoC* listaC;
} ContenedorCarga;

/* Area de contexto del descompresor en el scratchpad (la tabla de longitudes empieza en +0x38). */
typedef struct ContextoDescompresion {
    u32 retorno;
    u32 retorno_lectura;
    u32 guardados[9];
    u32 anillo_inicio;
    u32 anillo_fin;
    u16 umbral;
    u16 parametros;
    u16 longitudes[128];
} ContextoDescompresion;
s32 SumaControl(s8* datos, s32 n);
s32 func_80044664(u8* entrada, u8* salida, ContextoDescompresion* contexto);

#endif
