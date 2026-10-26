#include "common.h"
#include "globales.h"

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", BugsRand);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032894);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032A24);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032B2C);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800330AC);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80033358);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80034E7C);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_8003502C);

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800351B4);

#ifdef NON_MATCHING
/*
 * Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron, avanza siete secuencias
 * de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una
 * ejecuta su caso con un switch de siete entradas. El archivo se compila con -G8
 * (config/opciones_compilacion.toml). Puntuacion 600: la tabla de saltos, los destinos de los
 * casos, el reparto de registros del estado y la forma simbolica de D_80069662 coinciden;
 * difieren la posicion del almacen en 0x104($gp) (el original no lo coloca en el hueco de
 * retardo), las constantes 0x47 y 1, que el original carga antes del bucle, y el orden de los
 * incrementos de los punteros del bucle.
 */
typedef struct Secuencia {
    s16 caso;
    s16 paso;
    s16 teclas[10];
} Secuencia;

typedef struct EstadoPrincipal {
    s32 modo;
    u8 pad04[0x41 - 0x04];
    u8 f41;
    u8 pad42;
    u8 f43;
    u8 pad44;
    u8 f45;
    u8 pad46;
    u8 f47;
    u8 f48;
    u8 pad49[0x64 - 0x49];
    u8 f64;
    u8 pad65[0x13C - 0x65];
    u8 f13C;
} EstadoPrincipal;

extern Secuencia D_8005E768[];
#define PRINCIPAL ((EstadoPrincipal*)0x80010000)

void func_80035244(void)
{
    s32 i;
    Secuencia* e;
    s32 estado;

    estado = D_80010010;
    estado &= 0xFFF6;
    if (*(s16*)(base_gp + 0x104) != estado) {
        *(s16*)(base_gp + 0x104) = estado;
        if (estado != 0) {
            e = D_8005E768;
            for (i = 0; i < 7; i++, e++) {
                if (e->teclas[e->paso] == estado) {
                    e->paso = e->paso + 1;
                    if (e->teclas[e->paso] == 0) {
                        switch (e->caso) {
                        case 0:
                            PRINCIPAL->f64 |= 1;
                            break;
                        case 1:
                            PRINCIPAL->f43 = 0x63;
                            PRINCIPAL->f64 |= 2;
                            break;
                        case 2:
                            PRINCIPAL->f48 |= 0x1F;
                            PRINCIPAL->f64 |= 4;
                            break;
                        case 3:
                            PRINCIPAL->f41 = 6;
                            PRINCIPAL->f64 |= 8;
                            break;
                        case 4:
                            PRINCIPAL->f48 |= 0x80;
                            PRINCIPAL->f64 |= 0x10;
                            break;
                        case 5:
                            PRINCIPAL->f47 = 0x4D;
                            PRINCIPAL->f13C = 1;
                            PRINCIPAL->f45 = 0x7C;
                        case 6:
                            PRINCIPAL->modo = 0x47;
                            D_80069662 = 1;
                            break;
                        }
                    }
                } else {
                    e->paso = 0;
                }
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80035244);
#endif

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800353B0);
