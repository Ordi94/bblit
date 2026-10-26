#ifndef OBJETOS_H
#define OBJETOS_H

#include "common.h"
#include "globales.h"

/*
 * Cabecera comun de un nodo de pozo: el pozo es un arreglo de nodos de tamano fijo y el
 * primer par de palabras de cada nodo es el enlace (siguiente) y la marca de libre (bit 0
 * activo). Las listas de objetos y las de ayudantes usan esta cabecera; el pozo la
 * administra con AllocListNode, InitListPool, AppendListNode, RemoveListNode y ClearList.
 */
typedef struct NodoLista {
    struct NodoLista* siguiente;
    u32 libre;
} NodoLista;

/*
 * Entrada de la tabla de identificadores D_800695D4 (0x58 bytes): 'id' en +0x0C y la marca de
 * libre en +0x04.
 */
typedef struct EntradaId {
    NodoLista cab;
    s32 w8;
    s32 id;
    u8 pad10[0x58 - 0x10];
} EntradaId;

/* Entrada de la tabla D_8006B668 que lee el codigo superpuesto: dos medias palabras y un valor. */
typedef struct EntradaPunto {
    s16 x;
    s16 y;
    s32 z;
} EntradaPunto;

/*
 * Ayudante de un objeto (0xB8 bytes, pozo D_8006964C): un nodo de jerarquia con su propio
 * GsCOORDINATE2 y sus parametros de transformacion. 'clave' lo identifica dentro de la lista
 * del objeto dueno (func_800361CC lo busca por ella). Los campos citan la rutina que los usa.
 */
typedef struct Ayuda {
    NodoLista cab;               /* +0x00 enlace y marca de libre (func_800363D4) */
    u16 flags8;                  /* +0x08 estado (func_80036474, func_80037048) */
    u8 pad0A[2];
    s32 wC;                      /* +0x0C inicializado a 0x80000000 (func_800363D4) */
    GsCOORDINATE2* pcoord;       /* +0x10 apunta a 'coord' (func_800363D4) */
    s32 w14;                     /* +0x14 */
    s32 clave;                   /* +0x18 clave de busqueda (func_80036474) */
    GsCOORDINATE2 coord;         /* +0x1C */
    GsCOORD2PARAM param;         /* +0x6C */
    MATRIX m94;                  /* +0x94 copia de la matriz de vista (func_80037048) */
    s8 visible;                  /* +0xB4 resultado de la prueba de visibilidad */
    u8 padB5[3];
} Ayuda;

/*
 * Memoria de trabajo de las rutinas de recorrido y dibujo de la lista de escena: vive en el
 * scratchpad (0x1F800000), asi que cada acceso es un unico lw/sw contra una base constante.
 * 'actual' es el objeto en curso, 'previo' el ultimo enlazado en la lista de dibujo, 'm' la
 * matriz de vista del ayudante en prueba, 'pos' la posicion original del objeto (se restaura
 * tras reflejarlo) y 'aux' el area de salida de la prueba de visibilidad.
 */
typedef struct Escritorio {
    Objeto* actual;        /* +0x00 */
    Objeto* previo;        /* +0x04 */
    MATRIX m;                    /* +0x08 */
    VECTOR pos;                  /* +0x28 */
    u8 aux[0x20];                /* +0x38 */
} Escritorio;

#define ESCRITORIO ((Escritorio*)0x1F800000)

extern s32 func_8003760C(GsCOORDINATE2* c, MATRIX* m, void* aux);
extern void func_80037CF8(s32* origen, s32* destino);

/* Pozos de objetos y plantillas de la escena. */
extern Objeto* D_80069504;
extern s16 D_8006955C;
extern u8* D_8006968C;
extern Objeto* D_8006AB70[47];

/*
 * Entidad que transforma func_8001CE64: el nodo de jerarquia por el que sube (+0x00), el vector
 * local de entrada (+0x04) y el acumulador de la posicion transformada (+0x0C). func_8001CE64
 * lee de ella con lw 0x0 (nodo), lh 0x4/0x6/0x8 (v) y lw 0xC/0x10/0x14 (acc); el nodo es un
 * GsCOORDINATE2 (la matriz en +0x04 y el padre en +0x48).
 */
typedef struct EntidadTransformada {
    GsCOORDINATE2* nodo;
    SVECTOR v;
    VECTOR acc;
} EntidadTransformada;

/* Rutinas de ayudantes y de dibujo que usan varios archivos de este subsistema. */
Ayuda* func_800363D4(void);
void func_80037580(s32* m);
void func_8003BDD0(Ayuda* a);
s32 func_80010258(Ayuda* a, s32 prim, void* area1, void* area2);
void func_8001CE64(EntidadTransformada* e);

NodoLista* AllocListNode(u8* base, s32 paso, s32 total);
void InitListPool(u8* base, s32 paso, s32 total);
NodoLista* RemoveListNode(NodoLista* cab, NodoLista* nodo);
NodoLista* ClearList(NodoLista* cab);
NodoLista* AppendListNode(NodoLista* cab, NodoLista* nodo);

/* Pozos de la escena compartidos por varios archivos. */

/* D_800695D4: accesos del ensamblador: sw x1, lw x4 */
extern EntradaId* D_800695D4;

/* D_8006964C: accesos del ensamblador: sw x1, lw x3 */
extern Ayuda* D_8006964C;

/* D_8006B668 */
extern EntradaPunto D_8006B668[];

#endif
