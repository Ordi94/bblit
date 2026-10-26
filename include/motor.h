#ifndef MOTOR_H
#define MOTOR_H

/*
 * Tipos auxiliares del movimiento, la animacion de matrices y los eventos de zona. El objeto de
 * escena y el estado de la camara viven en globales.h (Objeto, EstadoCamara).
 */
#include "common.h"
#include "globales.h"
#include "geometria.h"

extern MATRIX* TransMatrix(MATRIX* m, VECTOR* v);

/*
 * Mueve un punto contra el terreno y los volumenes solidos (rutina de colision y terreno): recibe
 * la posicion a corregir, el desplazamiento deseado (se sustituye por el realizado), los
 * parametros de la zona y el area de trabajo de la consulta.
 */
extern void func_80019474(void* pos, void* desplazamiento, void* zona, void* trabajo);

/*
 * Desplazamiento que un objeto pretende hacer en un cuadro (x en +0, altura en +4, z en +8).
 * Las rutinas de movimiento lo sustituyen por el desplazamiento permitido.
 */
typedef struct Movimiento {
    s32 x;
    s32 dy;
    s32 z;
} Movimiento;

/*
 * La orden de movimiento de un objeto es el resultado de la consulta de baldosa
 * (ResultadoBaldosa, geometria.h): +2 banderas del terreno (8 y 1 = rampa y salto, bits 4, 8 y
 * 0x10 piden tipos de movimiento), +6 pendiente absoluta, +8 tipo y +0xA grupo. La altura del
 * techo en +0xC cae en el hueco que geometria.h deja sin nombre.
 */
#define ORDEN_TECHO(r) (*(s32*)((u8*)(r) + 0xC))

/*
 * Area de trabajo del movimiento de un objeto: copia de la posicion de partida en +0, posicion
 * de trabajo (desplazamiento realizado) en +0xC y +0x14, altura en +0x10, copias de 16 bits del
 * desplazamiento en +0x18 y +0x1A, grupo de la baldosa en +0x1C y el area de la consulta de
 * colision en +0x20.
 */
typedef struct TrabajoMov {
    s32 x;
    s32 y;
    s32 z;
    s32 dx;
    s32 y10;
    s32 dz;
    s16 h18;
    s16 h1A;
    u16 w1C;
    u8 pad1E[0x20 - 0x1E];
    u8 consulta[0x40];
} TrabajoMov;

/*
 * Misma area de trabajo vista por la rutina de seguimiento del suelo: punto consultado en +0, el
 * resultado de la baldosa (ResultadoBaldosa) en +0x10 y el area de la consulta (TrabajoBaldosa)
 * en +0x28. El llamador reserva una sola area y cada rutina la reinterpreta.
 */
typedef struct TrabajoSuelo {
    s32 x;
    s32 y;
    s32 z;
    u8 pad0C[4];
    ResultadoBaldosa res;
    TrabajoBaldosa tb;
} TrabajoSuelo;

extern int rsin(int angulo);

/* Coloca la camara detras de una posicion (movimiento_y_objetos_de_escena_2.c). */
extern void func_8001CC68(VECTOR* p);

/* Consulta de baldosa de colision_y_terreno.c (la definicion vive alli). */
extern void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w);

/*
 * Registro de un fotograma dentro del bloque de animacion: desplazamiento de la secuencia en +6
 * y banderas en +8 (el bit 0x40 marca los fotogramas que conservan el estado del salto).
 */
typedef struct RegistroAnim {
    u8 pad00[6];
    u16 w06;
    u16 w08;
    u8 pad0A[2];
    u32 w0C;
} RegistroAnim;

/*
 * Nodo de la lista de secuencias de un objeto: siguiente en +0, identificador en +4 y
 * desplazamiento del registro dentro del bloque de animacion en +6.
 */
typedef struct NodoSecuencia {
    struct NodoSecuencia* sig;
    u16 id;
    u16 desplazamiento;
    u16 w08;
    u16 w0A;
    u16 pad0C[2];
    u32 w10;
} NodoSecuencia;

/* Nodo de la lista de saltos (peldanos) de un objeto: siguiente en +0 y altura de destino en +0x10. */
typedef struct NodoPeldano {
    struct NodoPeldano* sig;
    u8 pad04[0x10 - 0x04];
    s32 w10;
} NodoPeldano;

/* Rutinas de movimiento de movimiento_y_objetos_de_escena.c que se llaman entre si. */
extern void func_8001C424(Objeto* o, Movimiento* m, ResultadoBaldosa* r);
extern void func_8001C6CC(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);
extern void func_8001C998(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);

/*
 * Macro de lectura del GTE del juego: guarda MAC3 (registro 27 de datos) en la palabra de p
 * pasando por los temporales fijos $8 y $9. El original la escribio como ensamblador en linea
 * con los mismos temporales que las macros vectoriales de geometria.h.
 */
#define MOTOR_GUARDAR_MAC3(p)     __asm__ volatile ("move $9, %0
	mfc2 $8, $27
	nop
	sw $8, 0($9)"                       : : "r"(p) : "$8", "$9", "memory")

#endif
