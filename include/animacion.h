#ifndef ANIMACION_H
#define ANIMACION_H

/*
 * Tipos de la animacion de objetos: los registros que el cursor (BloqueTrabajo, globales.h)
 * referencia, el area de trabajo con que se aplica un cuadro y los tipos de pista del flujo de
 * un cuadro. El cursor y la definicion de animacion viven en globales.h porque el objeto de
 * escena los contiene.
 */
#include "common.h"
#include "motor.h"
#include "objetos.h"

/*
 * Sonido de un cuadro (4 bytes): identificador en +0 y cuadro en el que suena en +1
 * (func_8001E720: lbu 0 y lbu 1 de cada entrada; el avance de la lista es de 4 bytes).
 */
typedef struct RegistroSonido {
    u8 id;
    u8 cuadro;
    u8 pad02[2];
} RegistroSonido;

/*
 * Evento de un cuadro (0xE bytes): plantilla del objeto hijo en +0 (lh para crear el hijo, lhu
 * para recordarla en el agarre), banderas en +2 y cuadro en el que se dispara en +4. Desde +6
 * hay un registro de condicion y accion del interprete de eventos: func_8001E720 pasa su
 * direccion a TestLogicCond y a RunLogicAction.
 */
typedef struct RegistroEvento {
    u16 id;
    u16 banderas;
    u16 cuadro;
    u8 cond[8];
} RegistroEvento;

/*
 * Par de bytes por cuadro de una animacion: el segundo es la duracion en ticks
 * (func_8001E720: lbu 1 del par indexado por el cuadro; el indice se multiplica por 2).
 */
typedef struct ParCuadro {
    u8 pad00;
    u8 ticks;
} ParCuadro;

/* Banderas de RegistroEvento.banderas que func_8001E720 interpreta. */
#define EVENTO_HIJO_ACOPLADO 0x0001
#define EVENTO_HIJO_SUELTO 0x0002
#define EVENTO_AGARRA 0x0004
#define EVENTO_SUELTA 0x0008
#define EVENTO_COLOCA 0x0100
#define EVENTO_HIJO_CON_GIRO 0x0400
#define EVENTO_LIBERA_HIJO 0x0040
#define EVENTO_AGARRE_SIN_DESFASE 0x0080
#define EVENTO_SIN_SUSTITUIR 0x8000

/* Bits del estado del cursor (BloqueTrabajo.flags18) que func_8001E720 maneja. */
#define ANIM_UNA_PASADA 0x0002
#define ANIM_EN_BUCLE 0x0001
#define ANIM_PAUSA 0x0010
#define ANIM_VUELTA 0x0080
#define ANIM_TERMINADA 0x0100
#define ANIM_EN_CURSO 0x0200
#define ANIM_HIJO_VIVO 0x0800
#define ANIM_RECIEN_INICIADA 0x1000
#define ANIM_ULTIMO_CUADRO 0x2000

/*
 * Tipos de pista del flujo de un cuadro (la palabra de la pista & 0xF0000, func_8003690C).
 */
#define PISTA_MASCARA 0x00000
#define PISTA_POSE 0x10000
#define PISTA_SPRITE 0x20000
#define PISTA_PADRE 0x30000
#define PISTA_CAMPO32 0x60000
#define PISTA_AYUDANTE 0x80000
#define PISTA_CAJA 0x90000
#define PISTA_POSICION 0xA0000

/*
 * Vista de un ayudante (Ayuda, objetos.h) a partir de +0x0C: palabra de estado, puntero a su
 * GsCOORDINATE2 (Ayuda.pcoord, +0x10) y valor asociado (Ayuda.w14, +0x14). func_8003690C
 * mantiene viva la direccion Ayuda + 0xC entre una pista y la siguiente (las pistas sin ayudante
 * reutilizan la anterior), de modo que esos tres campos se alcanzan con un puntero propio.
 */
typedef struct NucleoAyuda {
    s32 w0;
    GsCOORDINATE2* pcoord;
    s32 w8;
} NucleoAyuda;

/*
 * Area de trabajo con que func_8003690C aplica un cuadro (en el scratchpad del llamador; 0x78
 * bytes mas un puntero por ayudante). Cada campo cita el acceso que fija su desplazamiento.
 */
typedef struct AreaCuadro {
    union {
        u32 w;
        struct {
            u16 bajo;
            u16 alto;
        } h;
    } cab;                  /* +0x00: primera palabra del cuadro (sw); su mitad alta es el numero de pistas (lhu +2) */
    u32 banderas;           /* +0x04: palabra de la pista & 0xF00000 (sw) */
    u32 tam;                /* +0x08: palabra de la pista >> 24, en palabras (sw / lw) */
    MATRIX* m;              /* +0x0C: matriz del nodo del ayudante en curso (sw; argumento de RotMatrix, ScaleMatrix y TransMatrix) */
    NucleoAyuda* aux;       /* +0x10: cuerpo (Ayuda + 0xC) del ayudante padre en la pista de vinculo (sw / lw) */
    VECTOR acc;             /* +0x14: traslacion acumulada de la cadena de nodos (swc2 x3 y lw / sw) */
    SVECTOR v;              /* +0x24: vector que rota el GTE (lwc2 0 y 1; sh zero) */
    u32 n;                  /* +0x2C: cuadro de sprite pedido (sw / lw) */
    u32 tipo;               /* +0x30: palabra de la pista & 0xF0000 (sw / lw) */
    u8 pad34[4];
    u32 idx;                /* +0x38: pista en curso (sw / lw) */
    u32 npistas;            /* +0x3C: numero de pistas (sw / lw) */
    u32 palabra2;           /* +0x40: segunda palabra de la cabecera del cuadro (sw) */
    GsCOORDINATE2* nodo;    /* +0x44: nodo en curso de la cadena (sw / lw) */
    u8 pad48[0x68 - 0x48];
    Ayuda** tabla;          /* +0x68: tabla de ayudantes por indice, a partir de +0x78 (sw / lw) */
    s16 modo;               /* +0x6C: 1 busca el ayudante por clave, 0 por indice (sh / lh) */
    u8 pad6E[2];
    Ayuda* p70;             /* +0x70: cursor de la busqueda del padre (sw / lw) */
    u8 pad74[4];
    Ayuda* ayudas[1];       /* +0x78: ayudantes del objeto; el 0 queda sin uso y se llena desde el 1 (sw desde +0x7C) */
} AreaCuadro;

/*
 * Rutinas de interpretacion de eventos que invoca el avance de animacion: la condicion devuelve
 * un valor de 16 bits (el llamador lo enmascara con 0xFFFF).
 */
extern u32 TestLogicCond(Objeto* o, void* registro);
extern void RunLogicAction(Objeto* o, void* registro);

/*
 * Aplica un cuadro de la animacion (gestion_y_dibujo_de_objetos.c) y avanza el cursor
 * (movimiento_y_objetos_de_escena_3.c).
 */
extern void func_8003690C(Objeto* o, BloqueTrabajo* cursor, AreaCuadro* w);
extern u32 func_8001E720(Objeto* o, BloqueTrabajo* c, u32 anim, u32 modo, u8* area);

/*
 * Macros vectoriales del juego que reproducen las instrucciones del original (registros t
 * fijos): cada una copia primero la direccion a $8 con "move" y la lista de registros destruidos
 * contiene exactamente los que su cuerpo escribe, como las de geometria.h.
 *
 * ANIM_CARGAR_H3(p)      t1..t3 = vector de 3 medias palabras con signo en p (lh x3)
 * ANIM_CERO_W3(p)        vector de 3 palabras en p = 0
 * ANIM_CERO_WH(p)        palabra y media palabra de p = 0
 * ANIM_UNOS_W3(p)        vector de 3 palabras en p = 0x1000 (pasa por t4 y se copia a t1..t3)
 * ANIM_DIAGONAL_CERO(p)  elementos de la diagonal de la matriz p = 0 (sw 0, sw 8, sh 0x10)
 */
#define ANIM_CARGAR_H3(p) \
    __asm__ volatile ("move $8, %0\n\tlh $9, 0($8)\n\tlh $10, 2($8)\n\tlh $11, 4($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "memory")
#define ANIM_CERO_W3(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsw $0, 4($8)\n\tsw $0, 8($8)" \
                      : : "r"(p) : "$8", "memory")
#define ANIM_CERO_WH(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsh $0, 4($8)" \
                      : : "r"(p) : "$8", "memory")
#define ANIM_UNOS_W3(p) \
    __asm__ volatile ("move $8, %0\n\taddiu $12, $0, 0x1000\n\tmove $9, $12\n\tmove $10, $12\n\t" \
                      "move $11, $12\n\tsw $9, 0($8)\n\tsw $10, 4($8)\n\tsw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "$12", "memory")
#define ANIM_DIAGONAL_CERO(p) \
    __asm__ volatile ("move $8, %0\n\tmove $9, $0\n\tsw $9, 0($8)\n\tsw $9, 8($8)\n\tsh $9, 16($8)" \
                      : : "r"(p) : "$8", "$9", "memory")


/*
 * Rutinas que invoca el avance de animacion. func_8001E528 recibe el area de trabajo del llamador
 * como cuarto argumento y func_8003F06C recibe el cuadro del anillo sin recortar (lh): se llaman
 * con prototipos de palabra completa para que el llamador no normalice los argumentos.
 */
typedef void (*DibujarSprite)(Objeto*, BloqueTrabajo*, u32, u8*);
typedef void (*SonidoObjeto)(Objeto*, s32, s32, s32);
extern void func_8003502C(Objeto* o);
extern void func_8003F06C(void* objeto, s16 id, u16 modo, u8 clave);
extern s32 func_80018D98(Objeto* a, VECTOR* p, void* area);

/*
 * Tabla activa del cursor (+0x28): coincide con Objeto.tabla (+0x16C) cuando el cursor es
 * Objeto.trabajo (+0x144), y func_8001E720 la escribe a traves del cursor.
 */
#define CURSOR_TABLA(c) (*(TablaFotogramas**)((u8*)(c) + 0x28))

/*
 * Bloque de parametros de agarre del protagonista (Objeto + 0x18C): mismo diseno que
 * ParametrosObjeto; solape con campos de otras clases de objeto (w192, w196, i1A8), por eso se
 * accede por desplazamiento.
 */
#define AGARRE(j) (*(ParametrosObjeto*)((u8*)(j) + 0x18C))

/* Parametros propios de un objeto hijo recien creado (Objeto + 0x11C). */
#define HIJO_PARAM(h) ((u8*)(h) + 0x11C)

#endif
