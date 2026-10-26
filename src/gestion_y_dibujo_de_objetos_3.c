#include "common.h"
#include "objetos.h"

extern u16 D_8005E948[];

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
    EscenaDibujo* sp;
    Ayuda* a;
    s32 i;
    s16 hay;
    u16* src;
    EntradaPunto* dst;
    void* area2;

    sp = ESCENA_DIBUJO;
    area2 = (void*)0x1F800038;
    sp->objeto = lista;
    sp->ot0 = (u32*)D_8006AE20[D_8006967C].org;
    sp->ot1 = (u32*)D_8006AE60[D_8006967C].org;
    sp->ot2 = (u32*)D_8006AEA0[D_8006967C].org;
    sp->estado.w8 = 0;
    sp->estado.w0E = 0x3FFF;
    /*
     * Pone a cero los registros de traslacion $5 y $6 del GTE (TRX y TRY) y deja TRZ como esta:
     * gte_ldtr escribiria tambien $7 (TRZ), y el original no lo toca. Ninguna macro cubre una
     * escritura aislada de dos registros de traslacion, por eso se emiten las dos ctc2.
     */
    __asm__ volatile ("ctc2 $0, $5");
    __asm__ volatile ("ctc2 $0, $6");
    if (lista != 0) {
        do {
            if (!(sp->objeto->flags04 & 2)) {
                sp->objeto = sp->objeto->siguiente;
            } else {
                hay = 0;
                if (sp->objeto->w1C == 0x1ED) {
                    sp->estado.s6 = 0x1F4;
                } else {
                    sp->estado.s6 = 0x118;
                }
                for (a = sp->objeto->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                    if (a->flags8 & 6) {
                        hay = 1;
                        if (sp->objeto->w1C == 0x1EC) {
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
                    for (a = sp->objeto->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                        if (a->flags8 & 6) {
                            D_80076188 = func_80010258(a, D_80076188, &sp->estado, area2);
                        }
                    }
                }
                sp->objeto = sp->objeto->siguiente;
            }
        } while (sp->objeto != 0);
    }
}
