#ifndef EVENTOS_H
#define EVENTOS_H

#include "common.h"
#include "globales.h"
#include "arranque.h"

/*
 * Tipos compartidos del interprete de eventos.
 *
 * Las rutinas de condicion reciben (objeto, registro de condicion) y devuelven 0 o 1; las de
 * accion reciben (objeto, registro de accion) y no devuelven nada. El primer byte del registro
 * de condicion (offset 0) elige la rutina y el del registro de accion esta en el offset 3.
 */

/* Registro de accion: el codigo de operacion esta en el byte 3; w4 y w6 son los operandos. */
typedef struct Accion {
    u8 pad00[4];
    u8 b4;
    u8 pad5;
    u16 w6;
} Accion;
#define ACC_W4(a) (*(u16*)&(a)->b4)

/*
 * Rutinas del interprete de eventos que llaman la logica de niveles, el movimiento y la
 * animacion. TestLogicCond y RunLogicAction son manuscritas: despachan por el byte de operacion
 * del registro (a1) y no leen el objeto (a0), que pasa intacto a la rutina elegida. El llamador
 * enmascara el resultado de la condicion con 0xFFFF (andi en 0x8001EC0C), asi que se declara
 * de palabra completa.
 *
 * func_8003F06C (audio_xa_y_spu.c) normaliza id a 16 bits en la propia rutina (sll / sra en
 * 0x8003F0C8) y no devuelve valor. Los llamadores pasan los argumentos sin estrechar (el cuarto
 * es D_8006967C cargado con lh, sin andi), de modo que el prototipo visible para ellos es de
 * palabra completa; la definicion conserva los anchos que la rutina usa y por eso no incluye
 * esta cabecera.
 */
extern s32 TestLogicCond(Objeto* o, void* registro);
extern void RunLogicAction(Objeto* o, void* registro);
extern void func_8003F06C(void* o, s32 id, s32 modo, s32 voz);

#endif
