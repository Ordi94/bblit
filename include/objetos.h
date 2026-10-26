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
    u8 visible;                  /* +0xB4 resultado de la prueba de visibilidad */
    u8 padB5[3];
} Ayuda;

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
    u8 pad3E[0x74 - 0x3E];
    void* p74;                   /* +0x74 descriptor del modelo */
    Ayuda* ayudas;               /* +0x78 lista de ayudantes */
    GsCOORDINATE2 coord;         /* +0x7C */
    GsCOORD2PARAM param;         /* +0xCC */
    u8 padF4[0x1F4 - 0xF4];
} ObjetoEscena;

NodoLista* AllocListNode(u8* base, s32 paso, s32 total);
void InitListPool(u8* base, s32 paso, s32 total);
NodoLista* RemoveListNode(NodoLista* cab, NodoLista* nodo);
NodoLista* ClearList(NodoLista* cab);
NodoLista* AppendListNode(NodoLista* cab, NodoLista* nodo);

#endif
