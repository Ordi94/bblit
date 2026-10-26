#ifndef NIVELES_H
#define NIVELES_H

/*
 * Tipos de los manejadores de objeto de la logica de niveles (tabla D_8005E35C, indexada por
 * Objeto.w2C). El objeto de escena vive en globales.h y los registros de animacion en motor.h.
 */
#include "common.h"
#include "globales.h"
#include "motor.h"

/*
 * Nodo de la lista de disparadores del objeto (Objeto.apoyos, +0xFC): los registros de condicion y de
 * accion del interprete de eventos estan dentro del nodo, en +0x10, y se pasan por direccion a
 * TestLogicCond y RunLogicAction. El byte +0x10 elige la condicion y el +0x13 la accion; flags
 * decide que efectos acompanan al disparo. Cada campo cita la funcion cuyo ensamblador fija su
 * desplazamiento y su ancho.
 */
typedef struct NodoDisparador {
    struct NodoDisparador* sig;     /* func_8002D03C: lw 0x8002D568 */
    u16 id;                         /* func_8002D03C: lhu 0x8002D27C, grupo del fotograma */
    u16 desplazamiento;             /* func_8002D03C: lhu 0x8002D28C, posicion en la lista de secuencias */
    u8 pad08[8];
    u8 cond;                        /* func_8002D03C: lbu 0x8002D368, registro de condicion */
    u8 pad11[2];
    u8 accion;                      /* func_8002D03C: lbu 0x8002D38C, registro de accion */
    u8 pad14[4];
    s32 flags;                      /* func_8002D03C: lw 0x8002D298; el bit 31 pide animar al jugador */
    u32 p1C;                        /* func_8002D03C: lw, umbral de azar o valor de estado */
    s32 p20;                        /* func_8002D03C: lw, umbral de azar o identificador */
} NodoDisparador;

/*
 * Memoria de trabajo del recorrido de disparadores, en el scratchpad (0x1F800000): el original
 * guarda aqui sus variables, de modo que cada acceso es un lw / sw contra una base constante y
 * el estado sobrevive a las llamadas.
 */
typedef struct TrabajoDisparo {
    Objeto* buscado;                /* +0x00: objeto hallado por identificador */
    u8 pad04[4];
    RegistroAnim* fotograma;        /* +0x08 */
    NodoDisparador* cabeza;         /* +0x0C */
    NodoDisparador* nodo;           /* +0x10 */
    NodoSecuencia* secuencia;       /* +0x14 */
    u8 pad18[4];
    u16 paso;                       /* +0x1C */
    u16 destino;                    /* +0x1E */
    s32 flags;                      /* +0x20 */
    s32 resultado;                  /* +0x24 */
    s32 previo;                     /* +0x28 */
    u8 area[0x40];                  /* +0x2C: area que reciben func_8001D0FC y func_8001E720 */
} TrabajoDisparo;

#define TRABAJO_DISPARO ((TrabajoDisparo*)0x1F800000)

extern s32 BugsRand(void);
extern s32 TestLogicCond(void* o, void* registro);
extern void RunLogicAction(void* o, void* registro);
extern s32 func_8003F06C(void* o, s32 id, s32 modo, s32 voz);
/* El original pasa el area de trabajo como cuarto argumento aunque la rutina solo declara tres. */
extern void func_8001E528(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern void func_8001E600(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern u32 func_80045C4C(u32 a0, void* a1, Objeto* a2);
extern u32 func_80045498(Objeto* objeto, void* guion, BloqueTrabajo* bloque);
extern void func_8001F268(Objeto* o, BloqueTrabajo* b, u32 anim, u32 params, void* area);
extern void func_8001D0FC(Objeto* o, s32 id, void* area);
extern s32 func_8001E720(Objeto* o, BloqueTrabajo* b, u32 anim, u32 params, void* area);

#endif
