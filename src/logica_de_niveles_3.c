#include "common.h"
#include "globales.h"
#include "arranque.h"

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026298);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026FEC);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002BA80);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002C1DC);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002CB8C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002CEC4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D03C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D68C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EA9C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EAA4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F018);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F510);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F614);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F6B4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F968);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F970);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 60 con la configuracion versionada (g = 0 del archivo). Los dos bytes se
 * leen y escriben con un unico lui y la copia del valor leido queda en el hueco del primer salto,
 * como el original; difiere solo el reparto de registros: el original deja el resultado de la
 * suma en a2 y GCC lo deja en v1 (los papeles de v1 y a2 estan invertidos).
 *
 * Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el
 * bajo y D_8001013C el alto: r[7] y r[0xFC] del banco del estado principal de 0x80010000). El operando se
 * trunca a un byte dentro de la rutina (andi 0xFF en 0x8002F9AC y 0x8002F9DC) y los llamadores
 * le pasan el valor de 16 bits sin truncar (lhu): por eso el parametro es s32 y el truncamiento
 * un cast. Declarado u8, cada llamador recorta el argumento con lbu.
 */
void func_8002F990(s32 a0, s32 a1)
{
    EstadoPrincipal* e;
    u32 reg;
    u32 res;
    u32 alto;

    e = ESTADO_PRINCIPAL;
    reg = e->r[7] | (e->r[0xFC] << 8);
    res = reg;
    if (a1 == 0) {
        res = (u8)a0 + reg;
    }
    if (a1 == 1) {
        res = reg + 1;
    }
    if (a1 == 2) {
        res = reg - 1;
    }
    if (a1 == 3) {
        res = reg - (u8)a0;
    }
    alto = res & 0xFFFF;
    e->r[7] = res;
    e->r[0xFC] = alto >> 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F990);
#endif
