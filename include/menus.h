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
    struct ObjetoEscena* sig;
    u32 flags14;
    u32 flags18;
    u8 pad1C[0x26 - 0x1C];
    u16 w26;
    u16 w28;
    u8 pad2A[2];
    u16 w2C;
    u8 pad2E[0x3A - 0x2E];
    u16 w3A;
    u16 w3C;
    u16 w3E;
    u8 pad40[0x48 - 0x40];
    u16 h48;
    u16 h4A;
    u16 h4C;
    u8 pad4E[2];
    u16 h50;
    u16 h52;
    u16 h54;
    u8 pad56[0x70 - 0x56];
    struct ObjetoEscena* p70;
    u8 pad74[4];
    struct ModeloDibujo* modelos;
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
#define GEO_GUARDAR_W_T4(p) \
    __asm__ volatile ("move $8, %0\n\tsw $12, 0($8)\n\tsw $13, 4($8)\n\tsw $14, 8($8)" \
                      : : "r"(p) : "$8", "memory")

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

/* Vistas de palabra del vertice de trabajo: x e y empaquetados, coordenadas de textura y color con codigo. */
#define VERT_XY(v) (*(u32*)&(v)->x)
#define VERT_UV(v) (*(u16*)&(v)->u)
#define VERT_COLOR(v) (*(u32*)&(v)->r)

/* Copia de 12 bytes sin alineacion (struct de bytes): el compilador la hace con lwl/lwr y swl/swr. */
typedef struct Copia12 {
    u8 b[12];
} Copia12;

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
 * Definicion de un poligono de la cola de dibujo. Los 20 valores de 16 bits se leen como indices
 * de vertice (con signo) o como coordenadas de textura y clut (sin signo) segun el tipo; los
 * desplazamientos concretos de cada tipo estan en func_8003C1C8.
 */
typedef union PoligonoDef {
    s16 s[20];
    u16 u[20];
} PoligonoDef;

/* Vertice proyectado de la tabla del objeto: x e y empaquetados en una palabra, z aparte (8 bytes). */
typedef struct VerticeObjeto {
    u32 xy;
    u16 z;
    u16 pad06;
} VerticeObjeto;

/*
 * Entrada de la cola de poligonos D_8006D1C8 (0x1C bytes) que llena el dibujador de modelos y
 * consume func_8003C1C8: tipo de poligono, bandera, definicion, tabla de vertices del objeto y
 * los colores de cada vertice. El byte alto del primer color es el codigo de primitiva.
 */
typedef struct EntradaCola {
    u16 tipo;
    u16 w2;
    PoligonoDef* def;
    VerticeObjeto* tabla;
    u8 rgb0[3];
    s8 codigo;
    u32 color1;
    u32 color2;
    u32 color3;
} EntradaCola;

/* Cuadrilatero de color por vertice (POLY_G4, 0x24 bytes). */
typedef struct PoligonoG4 {
    u32 tag;
    u32 c0;
    u32 xy0;
    u32 c1;
    u32 xy1;
    u32 c2;
    u32 xy2;
    u32 c3;
    u32 xy3;
} PoligonoG4;

/* Cuadrilatero con textura y color plano (POLY_FT4, 0x28 bytes). */
typedef struct PoligonoFT4 {
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
    u32 xy3;
    u16 uv3;
    u16 pad26;
} PoligonoFT4;

/* Cuadrilatero con textura y color por vertice (POLY_GT4, 0x34 bytes). */
typedef struct PoligonoGT4 {
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
    u32 c3;
    u32 xy3;
    u16 uv3;
    u16 pad32;
} PoligonoGT4;

/*
 * Estado que se pasa al dibujador de modelos del overlay (func_80010204/func_80010258): los
 * primeros bytes de la escena. +0..+2: bytes de estado (func_8003B26C y func_8003B354);
 * +4 (s4): profundidad del objeto (func_8003AF8C) y, en func_8003C014, desplazamiento de la
 * entidad; +6 (s6): desplazamiento de profundidad; +8 (w8): nivel del fundido de pantalla;
 * +0xC/+0xE (w0C, w0E) y +0x10/+0x12: limites de profundidad del modelo.
 */
typedef struct EstadoDibujo {
    u8 b0;
    u8 b1;
    u8 b2;
    u8 pad03;
    s16 s4;
    s16 s6;
    u16 w8;
    u8 pad0A[2];
    u16 w0C;
    u16 w0E;
    u16 w10;
    u16 w12;
} EstadoDibujo;

/*
 * Escena en curso, en el scratchpad (0x1F800000, 0x38 bytes): estado del dibujador en +4, las
 * bases de las tres listas de ordenacion en +0x18/+0x1C/+0x20, punteros a los contadores del
 * cuadro en +0x24/+0x28, inicio y limite del buffer de primitivas en +0x2C/+0x30 (func_8003AE08,
 * func_8003AF8C) y el objeto en curso en +0x34.
 */
typedef struct EscenaDibujo {
    u8 pad00[4];
    EstadoDibujo estado;
    u32* ot0;
    u32* ot1;
    u32* ot2;
    u16* cuenta_a;
    u16* cuenta_b;
    s32 inicio;
    s32 limite;
    ObjetoEscena* objeto;
} EscenaDibujo;

/*
 * Vista de dibujo (tercer argumento de las rutinas de modelos y contexto de la cola de poligonos).
 * +0: tipo de primitiva (8 y 12 sin textura, 16 y 20 con
 * textura y color plano, 24 y 28 con textura y color por vertice); +0x10: registro de banderas del
 * GTE (negativo si el poligono se descarta); +0x18: cursor de la primitiva siguiente; +0x1C,
 * +0x20 y +0x24: bases de las tres listas de ordenacion, de resolucion decreciente; +0x28:
 * entrada elegida; +0x2C: plantilla de poligono con textura y color por vertice (POLY_GT4, 0x34 bytes) donde
 * func_8003CA5C deja las coordenadas proyectadas y de la que copia los tres formatos de
 * primitiva; su clut (+0x3A) y su pagina de textura (+0x46) los fija func_8003DA4C; +0x60: cuatro
 * vertices de trabajo.
 */
typedef struct VistaDibujo {
    s8 tipo;
    s8 b1;
    s8 b2;
    u8 pad03;
    s16 s4;
    s16 s6;
    s16 w8;
    u8 pad0A[2];
    s32 indice;
    s32 bandera;
    s32 bandera2;
    s32 cursor;
    u32* ot0;
    u32* ot1;
    u32* ot2;
    u32* destino;
    PoligonoGT4 plantilla;
    Vertice12 trabajo[4];
} VistaDibujo;

/*
 * El cursor se vuelve a leer de memoria tras escribirlo: el original compara el valor recien
 * guardado con el limite del buffer sin reutilizar el registro.
 */
#define CURSOR_RELEIDO(c) (*(volatile s32*)&(c)->cursor)

#endif
