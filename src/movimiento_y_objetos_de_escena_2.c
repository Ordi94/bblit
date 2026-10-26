#include "common.h"
#include "gte.h"

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001CC68);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001CD84);

/*
 * Acumula la traslacion de cada nodo de la cadena de padres sobre el vector de una entidad:
 * rota el vector con la matriz del nodo en el GTE, suma la traslacion del nodo, recorta el
 * resultado a 16 bits y sube al nodo padre hasta llegar al raiz.
 */
typedef struct Nodo Nodo;
struct Nodo {
    s32 pad0;
    MATRIX mtx;
    u8 pad24[0x48 - 0x24];
    Nodo* padre;
};

typedef struct Entidad {
    Nodo* nodo;
    SVECTOR v;
    VECTOR acc;
} Entidad;

void func_8001CE64(Entidad* e)
{
    e->v.vx = 0;
    e->v.vy = 0;
    e->v.vz = 0;
    if (e->nodo != NULL) {
        do {
            gte_SetRotMatrix(&e->nodo->mtx);
            gte_ldv0(&e->v);
            gte_rtv0();
            gte_stlvnl(&e->acc);
            e->acc.vx += e->nodo->mtx.t[0];
            e->acc.vy += e->nodo->mtx.t[1];
            e->acc.vz += e->nodo->mtx.t[2];
            e->v.vx = e->acc.vx;
            e->v.vy = e->acc.vy;
            e->v.vz = e->acc.vz;
            e->nodo = e->nodo->padre;
        } while (e->nodo != NULL);
    }
}

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001CF50);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001CFCC);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D028);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D0FC);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D31C);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D414);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D588);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D75C);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D994);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001DA14);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001DF28);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001E1A4);
