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

extern void func_80037CF8(s32* origen, s32* destino);

/* Pozos de objetos y plantillas de la escena. */
extern Objeto* D_80069504;
extern s16 D_8006955C;
extern u8* D_8006968C;
extern Objeto* D_8006AB70[47];

/* Rutinas de ayudantes y de dibujo que usan varios archivos de este subsistema. */
Ayuda* func_800363D4(void);
void func_80037580(s32* m);

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
EntradaId* func_80036164(s32 id);
Objeto* func_80036734(s16 id, s32* pos, u16* ang);
void func_80037048(Objeto* lista);
void func_80037184(Objeto* lista);
void func_80037FB8(NodoLista* n);
void func_80037FE8(void* lista);
void func_800399C8(Objeto* lista);

/* Rutina del overlay que dibuja un modelo: recibe un Ayuda (escena) o un ModeloDibujo (menus). */
s32 func_80010258(void* modelo, s32 cursor, void* estado, void* vista);

/* Rutina en ensamblador que proyecta los vertices de un Ayuda o de un ModeloDibujo. */
s32 func_8003BDD0(void* modelo);
extern s32 func_8003760C(GsCOORDINATE2* c, MATRIX* m, void* aux);

#endif
