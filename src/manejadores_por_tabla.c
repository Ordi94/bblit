#include "common.h"

/*
 * Doce manejadores de 32 bytes que la tabla de punteros de 0x8005E35C alcanza por
 * indireccion. Cada uno delega en LogicaObjetoMovil con una mascara de bits distinta y deja
 * intacto el primer argumento (la entidad), que el despachador ya dejo en $a0.
 */
extern void LogicaObjetoMovil(void* entidad, s32 mascara);

void func_80026118(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x2);
}

void func_80026138(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x1);
}

void func_80026158(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x80);
}

void func_80026178(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x4);
}

void func_80026198(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x8);
}

void func_800261B8(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x10);
}

void func_800261D8(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x20);
}

void func_800261F8(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x22);
}

void func_80026218(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x40);
}

void func_80026238(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x100);
}

void func_80026258(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x200);
}

void func_80026278(void* entidad)
{
    LogicaObjetoMovil(entidad, 0x400);
}
