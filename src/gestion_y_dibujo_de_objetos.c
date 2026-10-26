#include "common.h"

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_80036164);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800361CC);

/* Ranura de una reserva: 'marca' con el bit 0 activo indica que esta libre. */
typedef struct Ranura {
    s32 dato;
    u32 marca;
} Ranura;

/* Devuelve la primera ranura libre, la ocupa (borra la marca) y avanza por la reserva de 'paso' en 'paso'. */
Ranura* AllocListNode(u8* base, s32 paso, s32 total)
{
    u8* p;
    u8* fin;

    p = base;
    fin = p + total;
    while (p < fin) {
        if (((Ranura*)p)->marca & 1) {
            ((Ranura*)p)->marca = 0;
            ((Ranura*)p)->dato = 0;
            return (Ranura*)p;
        }
        p = base + paso;
        base = p;
    }
    return 0;
}

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", InitListPool);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", RemoveListNode);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", ClearList);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", AppendListNode);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800363D4);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_80036474);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800364E0);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_8003652C);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800365D0);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_80036734);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800368E8);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_8003690C);
