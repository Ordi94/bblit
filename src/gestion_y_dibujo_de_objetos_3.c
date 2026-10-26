#include "common.h"
#include "objetos.h"

/*
 * Memoria de trabajo del dibujo de la lista de escena en el scratchpad (0x1F800000): las tres
 * listas de ordenacion del buffer activo en +0x18, +0x1C y +0x20, el objeto en curso en +0x34
 * y, en +0x04 y +0x38, las dos areas que func_80010258 (rutina del codigo superpuesto) recibe.
 */
typedef struct EscritorioDibujo {
    u8 pad00[0x04];
    u8 area1[0x06];
    s16 s0A;
    s16 s0C;
    u8 pad0E[0x12 - 0x0E];
    s16 s12;
    u8 pad14[0x18 - 0x14];
    GsOT_TAG* ot0;
    GsOT_TAG* ot1;
    GsOT_TAG* ot2;
    u8 pad24[0x34 - 0x24];
    Objeto* actual;
} EscritorioDibujo;

/* Entrada de la tabla D_8006B668 que lee el codigo superpuesto: dos medias palabras y un valor. */
typedef struct EntradaPunto {
    s16 x;
    s16 y;
    s32 z;
} EntradaPunto;

extern s32 D_80076188;
extern u16 D_8005E948[];
extern EntradaPunto D_8006B668[];

/*
 * Dibuja la lista de escena 'lista' (enlazada por +0x00): para cada objeto activo fija el
 * parametro de color segun su identificador, prepara la matriz de cada ayudante con
 * func_80037580 y func_8003BDD0 y, si el objeto es el del identificador 0x1EC, copia ocho
 * puntos de la tabla D_8005E948 a D_8006B668. Despues entrega cada ayudante a func_80010258,
 * que escribe sus primitivas en el buffer D_80076188. Las listas de ordenacion del buffer
 * activo se dejan en el scratchpad.
 */
void func_800399C8(Objeto* lista)
{
    EscritorioDibujo* sp;
    Ayuda* a;
    s32 i;
    s16 hay;
    u16* src;
    EntradaPunto* dst;
    void* area2;

    sp = (EscritorioDibujo*)0x1F800000;
    area2 = (void*)0x1F800038;
    sp->actual = lista;
    sp->ot0 = D_8006AE20[D_8006967C].org;
    sp->ot1 = D_8006AE60[D_8006967C].org;
    sp->ot2 = D_8006AEA0[D_8006967C].org;
    sp->s0C = 0;
    sp->s12 = 0x3FFF;
    /*
     * Pone a cero los registros de traslacion $5 y $6 del GTE (TRX y TRY) y deja TRZ como esta:
     * gte_ldtr escribiria tambien $7 (TRZ), y el original no lo toca. Ninguna macro cubre una
     * escritura aislada de dos registros de traslacion, por eso se emiten las dos ctc2.
     */
    __asm__ volatile ("ctc2 $0, $5");
    __asm__ volatile ("ctc2 $0, $6");
    if (lista != 0) {
        do {
            if (!(sp->actual->flags04 & 2)) {
                sp->actual = sp->actual->siguiente;
            } else {
                hay = 0;
                if (sp->actual->w1C == 0x1ED) {
                    sp->s0A = 0x1F4;
                } else {
                    sp->s0A = 0x118;
                }
                for (a = sp->actual->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                    if (a->flags8 & 6) {
                        hay = 1;
                        if (sp->actual->w1C == 0x1EC) {
                            src = D_8005E948;
                            dst = D_8006B668;
                            for (i = 0; i < 8; i++) {
                                dst->x = src[0];
                                dst->y = src[1];
                                dst->z = 0xC8;
                                src += 2;
                                dst++;
                            }
                            break;
                        }
                        func_80037580((s32*)&a->m94);
                        func_8003BDD0(a);
                    }
                }
                if (hay != 0) {
                    for (a = sp->actual->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                        if (a->flags8 & 6) {
                            D_80076188 = func_80010258(a, D_80076188, sp->area1, area2);
                        }
                    }
                }
                sp->actual = sp->actual->siguiente;
            }
        } while (sp->actual != 0);
    }
}
