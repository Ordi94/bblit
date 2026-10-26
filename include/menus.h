#ifndef MENUS_H
#define MENUS_H

/*
 * Tipos del dibujo de escena que comparten las rutinas de menus_e_interfaz.c: contexto de
 * dibujo, objetos y modelos que recorre, primitivas que emite. Cada campo es un desplazamiento
 * que el ensamblador original lee o escribe; los huecos son relleno.
 */
#include "common.h"
#include "globales.h"

/* Entrada de D_8006A940: sala o modelo visible con su bandera (12 bytes por entrada). */
typedef struct EntradaVisible {
    s16 modelo;
    u16 bandera;
    u8 pad04[8];
} EntradaVisible;

/*
 * Entrada de la lista de dibujo de modelos (D_8006A940, 12 bytes por entrada) y argumento de
 * func_8003B26C: indice del modelo, nivel de profundidad y grupo. Los accesos de func_8003B26C
 * leen los dos ultimos campos como bytes (lbu).
 */
typedef struct PedidoModelo {
    s16 modelo;
    s16 profundidad;
    u16 grupo;
} PedidoModelo;

/*
 * Modelo de la tabla D_8006B568 y elemento de las cadenas de dibujo de func_8003C014: enlace al
 * siguiente en +0, banderas en +8 y +0xC, geometria en +0x10, un byte de visibilidad en +0xB4 y
 * un byte de estado en +0xB5.
 */
typedef struct ModeloDibujo {
    struct ModeloDibujo* siguiente;
    u8 pad04[4];
    u16 banderas;
    u8 pad0A[2];
    u32 modo;
    void* geometria;
    u8 pad14[0xB4 - 0x14];
    s8 visible;
    u8 estado;
} ModeloDibujo;

/*
 * Objeto de escena visto por las rutinas de dibujo (la misma memoria que Objeto): banderas en +4,
 * +8 y +0xC, identificadores en +0x26..+0x3E, el nodo de jerarquia empotrado en +0x7C, un
 * contador en +0xC4, la profundidad en +0xD4 y la posicion en +0xE4..+0xEC.
 */
typedef struct ObjetoEscena {
    u8 pad00[0x04];
    u32 flags04;
    u32 flags08;
    u32 flags0C;
    u8 pad10[0x26 - 0x10];
    u16 w26;
    u16 w28;
    u8 pad2A[2];
    u16 w2C;
    u8 pad2E[0x3C - 0x2E];
    u16 w3C;
    u16 w3E;
    u8 pad40[0x7C - 0x40];
    u8 nodo[4];
    u8 pad80[0xC4 - 0x80];
    s32 iC4;
    u8 padC8[0xD4 - 0xC8];
    s32 iD4;
    u8 padD8[0xE4 - 0xD8];
    s32 xE4;
    s32 yE8;
    s32 zEC;
} ObjetoEscena;

/* Pila de func_8003AF8C para func_8001CE64: puntero al nodo, vector de entrada y acumulador (E-07). */
typedef struct PilaNodo {
    void* nodo;
    SVECTOR v;
    VECTOR acc;
} PilaNodo;

/* Resultado de func_8001DF28: color base del sprite proyectado y desplazamiento de su textura. */
typedef struct ColorYDesplazamiento {
    u32 color;
    s32 desplazamiento;
} ColorYDesplazamiento;

/*
 * Sprite de cuatro vertices que func_8003AF8C emite como POLY_FT4: +8 banderas (bit 4 = fijo),
 * +0xC..+0x28 las ocho palabras de vertices y coordenadas de textura, +0x2C = semitransparente.
 */
typedef struct SpriteDibujo {
    u8 pad00[0x08];
    u16 banderas;
    u8 pad0A[2];
    u32 palabras[8];
    u32 semitransparente;
} SpriteDibujo;

/* Vista que reciben las rutinas de dibujo: +4 desplazamiento, +0xC y +0xE limites de profundidad. */
typedef struct VistaDibujo {
    u8 pad00[0x04];
    s16 s4;
    u8 pad06[0x0C - 0x06];
    u16 w0C;
    u16 w0E;
} VistaDibujo;


/* Vertice de la caja que func_8003DD70 prueba contra la pantalla: x en +8, y en +0xA, 12 bytes. */
typedef struct VerticeCaja {
    u8 pad00[8];
    s16 x;
    s16 y;
} VerticeCaja;

/* Semi-ancho y semi-alto de la ventana de recorte (+4 y +6). */
typedef struct LimitesPantalla {
    u8 pad00[4];
    s16 x;
    s16 y;
} LimitesPantalla;

/*
 * Objeto que func_8003ACA8 usa como camara: el puntero de +0x10 es el sistema de coordenadas
 * (GsCOORDINATE2) cuya matriz mundial se calcula con GsGetLw.
 */
typedef struct ObjetoCamara {
    u8 pad00[0x10];
    GsCOORDINATE2* coord;
} ObjetoCamara;

/*
 * Vector de tres palabras en t4..t6 guardado en memoria: el mismo estilo de macro de vector que
 * geometria.h (los temporales fijos $8 y $12..$14 y la direccion copiada a $8).
 */
#define GEO_GUARDAR_W_T4(p)     __asm__ volatile ("move $8, %0
	sw $12, 0($8)
	sw $13, 4($8)
	sw $14, 8($8)"                       : : "r"(p) : "$8", "memory")

/* Vertice fuente de 12 bytes: posicion en espacio objeto, coordenadas de textura, color y codigo. */
typedef struct Vertice12 {
    s16 x;
    s16 y;
    s16 z;
    u8 u;
    u8 v;
    u8 r;
    u8 g;
    u8 b;
    u8 codigo;
} Vertice12;

/* Triangulo de color por vertice (POLY_G3, 0x1C bytes). */
typedef struct PoligonoG3 {
    u32 tag;
    u32 c0;
    u32 xy0;
    u32 c1;
    u32 xy1;
    u32 c2;
    u32 xy2;
} PoligonoG3;

/* Triangulo con textura y color plano (POLY_FT3, 0x20 bytes). */
typedef struct PoligonoFT3 {
    u32 tag;
    u32 c0;
    u32 xy0;
    u16 uv0;
    u16 clut;
    u32 xy1;
    u16 uv1;
    u16 tpage;
    u32 xy2;
    u16 uv2;
    u16 pad1E;
} PoligonoFT3;

/* Triangulo con textura y color por vertice (POLY_GT3, 0x28 bytes). */
typedef struct PoligonoGT3 {
    u32 tag;
    u32 c0;
    u32 xy0;
    u16 uv0;
    u16 clut;
    u32 c1;
    u32 xy1;
    u16 uv1;
    u16 tpage;
    u32 c2;
    u32 xy2;
    u16 uv2;
    u16 pad26;
} PoligonoGT3;

/*
 * Contexto de dibujo de la escena. +0: tipo de primitiva (8 y 12 sin textura, 16 y 20 con
 * textura plana, el resto con textura y color por vertice: func_8003DA4C); +4..+6: bytes de estado
 * que se pasan al dibujador de modelos (func_8003B26C y func_8003B354); +8: profundidad del
 * objeto (func_8003AF8C) que func_8003D880 resta del indice; +0xA: desplazamiento de
 * profundidad; +0xC: indice de la lista de ordenacion; +0x10: registro de banderas del GTE
 * (negativo si el triangulo se descarta); +0x18: cursor de la primitiva siguiente; +0x1C/+0x20/
 * +0x24: bases de las tres listas de ordenacion, de resolucion decreciente; +0x28: entrada
 * elegida; +0x2C/+0x30: inicio y limite del buffer de primitivas; +0x34: objeto que fija la sala
 * visible; +0x3A y +0x46: clut y pagina de textura de las primitivas texturadas.
 */
typedef struct ContextoDibujo {
    s8 tipo;
    u8 pad01[3];
    u8 b4;
    u8 b5;
    u8 b6;
    u8 pad07;
    s16 profundidad;
    s16 desplazamiento;
    s32 indice;
    s32 bandera;
    u8 pad14[4];
    volatile s32 cursor;
    u32* ot0;
    u32* ot1;
    u32* ot2;
    u32* destino;
    s32 inicio;
    s32 limite;
    ObjetoEscena* objeto;
    u8 pad38[2];
    u16 clut;
    u8 pad3C[0x46 - 0x3C];
    u16 tpage;
} ContextoDibujo;

#endif
