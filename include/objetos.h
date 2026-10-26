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
 * Descriptor del modelo de un objeto (+0x74 del objeto): su segundo puntero lleva los datos
 * del modelo, de los que se leen una bandera de 16 bits en +0x0A (bit 1 = el objeto tiene
 * jerarquia de ayudantes) y un valor inicial de 32 bits en +0x54.
 */
typedef struct DatosModelo {
    u8 pad00[0x0A];
    u16 wA;
    u8 pad0C[0x54 - 0x0C];
    s32 w54;
} DatosModelo;

typedef struct DescModelo {
    u8 pad00[0x08];
    DatosModelo* datos;
} DescModelo;

/*
 * Objeto de escena tal como lo ve la reserva y el dibujo (0x1F4 bytes, pozo D_8006968C). Es la
 * vista completa de la misma memoria que 'Objeto' de globales.h describe para la logica
 * (ambas coinciden en el enlace de +0x00, en las banderas de +0x14/+0x18, en los angulos de
 * +0xDC y en la posicion de +0xE4).
 */
typedef struct ObjetoEscena {
    NodoLista cab;               /* +0x00 enlace de la lista D_80069518 y bits de estado */
    s32 w8;                      /* +0x08 puesto a cero al crear el objeto de la camara */
    s32 wC;                      /* +0x0C idem */
    struct ObjetoEscena* sig10;  /* +0x10 enlace de la lista de objetos solidos */
    u32 flags14;
    u32 flags18;
    u16 w1C;                     /* +0x1C identificador de plantilla */
    s16 s1E;
    s16 s20;
    u16 w22;
    u8 pad24[0x26 - 0x24];
    s16 s26;
    u8 pad28[0x2A - 0x28];
    s16 s2A;
    s16 s2C;
    u8 pad2E[0x3C - 0x2E];
    s16 s3C;
    u8 pad3E[0x70 - 0x3E];
    struct ObjetoEscena* p70;    /* +0x70 objeto asociado (func_8003A3D0) */
    DescModelo* p74;             /* +0x74 descriptor del modelo */
    Ayuda* ayudas;               /* +0x78 lista de ayudantes */
    GsCOORDINATE2 coord;         /* +0x7C */
    GsCOORD2PARAM param;         /* +0xCC */
    u8 padF4[0x1F4 - 0xF4];
} ObjetoEscena;

/*
 * Memoria de trabajo de las rutinas de recorrido y dibujo de la lista de escena: vive en el
 * scratchpad (0x1F800000), asi que cada acceso es un unico lw/sw contra una base constante.
 * 'actual' es el objeto en curso, 'previo' el ultimo enlazado en la lista de dibujo, 'm' la
 * matriz de vista del ayudante en prueba, 'pos' la posicion original del objeto (se restaura
 * tras reflejarlo) y 'aux' el area de salida de la prueba de visibilidad.
 */
typedef struct Escritorio {
    ObjetoEscena* actual;        /* +0x00 */
    ObjetoEscena* previo;        /* +0x04 */
    MATRIX m;                    /* +0x08 */
    VECTOR pos;                  /* +0x28 */
    u8 aux[0x20];                /* +0x38 */
} Escritorio;

#define ESCRITORIO ((Escritorio*)0x1F800000)

extern s32 func_8003760C(GsCOORDINATE2* c, MATRIX* m, void* aux);
extern void func_80037CF8(s32* origen, s32* destino);

/* Pozos de objetos y plantillas de la escena. */
extern ObjetoEscena* D_80069504;
extern s16 D_8006955C;
extern u8* D_8006968C;
extern ObjetoEscena* D_8006AB70[47];

NodoLista* AllocListNode(u8* base, s32 paso, s32 total);
void InitListPool(u8* base, s32 paso, s32 total);
NodoLista* RemoveListNode(NodoLista* cab, NodoLista* nodo);
NodoLista* ClearList(NodoLista* cab);
NodoLista* AppendListNode(NodoLista* cab, NodoLista* nodo);

#endif
