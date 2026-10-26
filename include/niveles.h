#ifndef NIVELES_H
#define NIVELES_H

/*
 * Tipos de la logica por cuadro del objeto controlado (manejador de w2C == 1): la memoria de
 * trabajo que ocupa el scratchpad y los registros de las listas de estados y transiciones que
 * el objeto lleva en +0xF8 y +0xFC. Los desplazamientos y anchos salen del ensamblador de
 * func_80020B90.
 */
#include "common.h"
#include "globales.h"
#include "geometria.h"
#include "motor.h"

/*
 * Registro de estado de la lista de +0xF8 del objeto (el estado vigente). El enlace va en +0 y
 * el identificador en +4 (tambien codigo de accion que recibe func_8001D414). s06 es la animacion
 * del estado (se compara con trabajo.i14), s08 sus parametros (el bit 0x8000 impide reiniciarla),
 * w0A la clave de la lista de transiciones, flags0C y flags10 las capacidades del estado, s14 el
 * multiplicador de velocidad y s16 y s18 la amplitud y el paso del salto.
 */
typedef struct RegistroEstado {
    struct RegistroEstado* sig;
    u16 id;
    s16 s06;
    s16 s08;
    u16 w0A;
    u32 flags0C;
    s32 flags10;
    s16 s14;
    s16 s16;
    s16 s18;
} RegistroEstado;

/*
 * Transicion de la lista de +0xFC del objeto: botones exigidos en w6 (0xFFF1 es comodin) y
 * mascara de botones w8, estado siguiente en wA (0xFFF3 no cambia de estado), accion sobre el
 * objeto portado en wC (0xD3 lo suelta), elemento de logica de 8 bytes en +0xE para TestLogicCond
 * y RunLogicAction, modo en w18 (el bit 2 invierte la mascara de m24 y el bit 1 la de m28) y las
 * mascaras que se comparan con los indicadores del portado (m1C), del apoyo (m20), del propio
 * objeto (m24) y de flags18 (m28).
 */
typedef struct Transicion {
    struct Transicion* sig;
    u16 id;
    u16 w6;
    u16 w8;
    u16 wA;
    u16 wC;
    u8 item[8];
    u8 pad16[2];
    u16 w18;
    u8 pad1A[2];
    u32 m1C;
    u32 m20;
    u32 m24;
    u32 m28;
} Transicion;

/*
 * Apoyo hallado por func_80020354: el objeto al que el jugador se agarra en +0 y, en +0xA, la
 * altura relativa que se copia a la traslacion del apoyo.
 */
typedef struct ApoyoHallado {
    Objeto* objeto;
    u8 pad04[6];
    s16 h0A;
} ApoyoHallado;

/* Velocidad local del cuadro: x sin uso, altura en y, avance en z (carga GTE de VXY0 y VZ0). */
typedef struct VelocidadLocal {
    s16 x;
    u16 y;
    u16 z;
    s16 pad06;
} VelocidadLocal;

/*
 * Memoria de trabajo de la logica del jugador en el scratchpad (0x1F800000). Se borra entera al
 * entrar y no sobrevive al cuadro. Los anchos y signos de cada campo (lh, lhu, lw) son los que el
 * ensamblador de func_80020B90 usa; paso se carga como vector de medias palabras en el GTE y
 * func_80017478 lo recibe como SVECTOR. A partir de 0x148 empieza el area de trabajo que reciben
 * las consultas de terreno y de volumen (func_80019474 exige 0x1C8 bytes libres por debajo de
 * 0x1F8003FF).
 */
typedef struct ScratchJugador {
    s16 paso_x;
    u16 paso_y;
    u16 paso_z;
    u16 pad06;
    VelocidadLocal vel;
    u16 ang_x;
    u16 ang_y;
    u16 ang_z;
    u16 pad16;
    Vec3 desp;
    u8 pad24[4];
    Vec3 resp;
    u8 pad34[4];
    VECTOR punto;
    MATRIX m;
    ResultadoBaldosa res;
    u8 pad80[0xA8 - 0x80];
    ApoyoHallado* apoyo_hallado;
    s16 res_peldano;
    u8 padAE[2];
    s32 tmp;
    Objeto* tocado;
    VECTOR rel;
    Objeto* tocado2;
    RegistroEstado* reg;
    Transicion* trans;
    Transicion* cand;
    NodoSecuencia* sec;
    u8 padDC[4];
    u16 paso_vigente;
    u16 estado_sig;
    GsCOORDINATE2* cursor;
    SVECTOR tmp_sv;
    VECTOR tmp_v;
    u32 resp_apoyo[3];
    u8 pad10C[0x12C - 0x10C];
    AcumuladorNodos acum;
} ScratchJugador;

/*
 * Vista del estado principal (0x80010000) con los campos que lee la logica del jugador: botones
 * de los dos mandos, ejes del analogico y la bandera de demostracion. El original los direcciona
 * con un solo lui y desplazamientos, lo que reproduce un puntero a la direccion constante.
 */
typedef struct EstadoMando {
    u8 pad00[0x0A];
    u16 botones_a;
    u16 botones_c;
    u8 pad0E[4];
    u16 eje_x;
    u16 eje_y;
    u8 pad16[0x4F - 0x16];
    u8 demo;
} EstadoMando;
#define MANDO ((EstadoMando*)0x80010000)

/* Transformacion del jugador relativa al apoyo (+0x18C) y la del objeto portado (+0x11C). */
#define APOYO(o) ((ParametrosObjeto*)((u8*)(o) + 0x18C))
#define PORTADO(o) ((ParametrosObjeto*)((u8*)(o) + 0x11C))

#endif
