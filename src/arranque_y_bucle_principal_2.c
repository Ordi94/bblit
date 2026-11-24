#include "common.h"
#include "globales.h"
#include "arranque.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBGS.H"
#include "objetos.h"
#include "menus.h"
#include "geometria.h"

extern s32 D_80069638;

extern u16 D_800694F0;
extern s32 D_8006CF68[];

extern s32 SetRCnt(u32 canal, u16 destino, s32 modo);
extern s32 StartRCnt(u32 canal);
extern s32 VSyncCallback(void (*funcion)());
extern void srand(u32 semilla);
extern void func_80044D44(void);
extern void func_80044E58(void);
extern void ConstruirRegistrosArchivo(void);
extern s32 CargarContenedor(s16 nivel, u8* destino);
extern void func_8003DF84(void);
extern void func_8003E9E8(void);
extern void SondearTarjeta();
extern void func_80015E94(void);
extern void func_80015F38(void);
extern void func_80040240(void);
extern void func_8003E88C(void);
extern void func_8003FC88(void);
extern void func_8003E948(void);
extern void func_8003FD60(void);
extern void func_8003E094(void);
extern void func_8003E068(void);
extern void func_800445E8(s16 nivel);
extern s32 BugsRand(void);
extern s32 VSync(s32 modo);
extern void SetDispMask(s32 mascara);
extern void func_800443CC(void);
extern void func_8004443C(s32 nivel);
extern void func_80044588(s32 nivel);
extern void func_8004048C(void);
extern void func_80015EC0(void);
extern void func_80015FC8(s32 segundos, u16 mascara);
extern void func_80016044(void);
extern void func_800160A8(void);
extern void func_8003E3C0(void);
extern void func_8003F3F0(s16 indice);
extern void func_800353B0(Objeto* a);
extern void func_8001020C(s32 a);

void func_80015EC0(void)
{
    EstadoPrincipal* e;
    s32 i;
    u8* p;

    i = 0xFF;
    p = (u8*)0x800100FF;
    do {
        p[0x40] = 0;
        p--;
        i--;
    } while (i >= 0);
    e = ESTADO_PRINCIPAL;
    e->r[0x01] = 6;
    e->r[0x02] = 6;
    e->r[0x00] = 3;
    e->r[0xA5] = 0x80;
    e->r[0xA6] = 0x50;
    D_80069594 = 0x50;
    e->r[BANCO_VIBRACION] = 1;
    e->mando.f16 = 0;
    e->mando.f18 = 0xFF;
    e->mando.centro_x = 0x7F;
    e->mando.f1C = 0;
    e->mando.f1E = 0xFF;
    e->mando.centro_y = 0x7F;
}

void func_80015F38(void)
{
    EstadoPrincipal* e;
    u8 a;
    u8 b;
    u8 c;
    u8 d;
    u8 f;
    u8 g;

    e = ESTADO_PRINCIPAL;
    a = e->r[0x10];
    b = e->r[BANCO_CONFIG];
    c = e->r[0xA5];
    d = e->r[0xA6];
    f = e->r[BANCO_VIBRACION];
    g = e->r[0xA8];
    func_80015EC0();
    e->r[0x10] = a;
    e->r[BANCO_CONFIG] = b;
    e->r[0xA5] = c;
    e->r[0xA6] = d;
    D_80069594 = d;
    e->r[BANCO_VIBRACION] = f;
    e->r[0xA8] = g;
}

void func_80015FC8(s32 segundos, u16 mascara)
{
    s32 i;

    for (i = 0; i < segundos * 0x3C; i++) {
        VSync(0);
        func_8004048C();
        if (ESTADO_PRINCIPAL->mando.botones_a & mascara) {
            break;
        }
    }
}

void func_80016044(void)
{
    RECT r;
    s32 i;

    i = 0;
    r.x = 0;
    r.y = 0;
    r.w = 0x200;
    r.h = 0x200;
    do {
        VSync(0);
        MoveImage(&r, 0x200, 0);
        DrawSync(0);
        i++;
    } while (i < 2);
}

void func_800160A8(void)
{
    SetDispMask(0);
    func_800443CC();
    SetDefDispEnv(&D_8006CF78, 0x200, 0, 0x200, 0x1E0);
    D_8006CF78.isrgb24 = 0;
    do {
    } while (PutDispEnv(&D_8006CF78) == 0);
    SetDispMask(1);
}

void func_80016118(void)
{
    EstadoPrincipal* e;

    func_800160A8();
    e = ESTADO_PRINCIPAL;
    e->nivel = 0x4E;
    func_8004443C(0x4E);
    e->nivel = 0x4F;
    func_80044588(0x4F);
    func_80015FC8(3, 0);
    func_80016044();
    e->nivel = 0x50;
    func_80044588(0x50);
    func_80015FC8(3, 0);
    func_80016044();
    e->nivel = 2;
    func_80015FC8(2, 0);
}

void func_800161A8(void)
{
    EstadoPrincipal* e;

    func_800160A8();
    e = ESTADO_PRINCIPAL;
    e->nivel = 0x6D;
    e->r[BANCO_DEMO] = 0;
    func_8004443C(0x6D);
    func_80016044();
    func_80015FC8(0x1E, 0x140);
    e->nivel = 0x6E;
    func_80044588(0x6E);
    func_80016044();
    func_80015FC8(0x14, 0x140);
}

/*
 * Actualiza un cuadro: contadores de tiempo, lectura de mandos, logica y ordenacion de primitivas.
 * La ordenacion corre con la pila en el bloque de memoria rapida (scratchpad): la pila se guarda en
 * 0x1F8003FC, se cambia a esa zona y se restaura al terminar. Las dos secuencias son ensamblador
 * porque el compilador no tiene forma de mover el puntero de pila.
 *
 */
void func_80016218(void)
{
    D_80069534 += 1;
    D_80069694 = D_80069510 - D_80069638;
    D_80069638 = D_80069510;
    func_8004048C();
    func_800353B0(D_80069518);
    __asm__ volatile ("move $8, %0\n\t"
                      "sw $29, 0($8)\n\t"
                      "addiu $8, $8, -4\n\t"
                      "move $29, $8"
                      : : "r"(0x1F8003FC) : "$8");
    /* 0x80016288: lui a0,%hi(D_8006D928) ; jal GsSetRefView2L ; addiu a0,a0,%lo(D_8006D928): se pasa la base de la estructura, que empieza por un GsRVIEW2. */
    GsSetRefView2L((GsRVIEW2*)&D_8006D928);
    GsClearOt(0, 0, &D_8006AE20[D_8006967C]);
    GsClearOt(0, 0, &D_8006AE60[D_8006967C]);
    GsClearOt(0, 0, &D_8006AEA0[D_8006967C]);
    func_80037048(D_80069630);
    D_8006AD40[D_8006967C] = D_80076188;
    func_800399C8(D_80069508);
    func_8003B5AC(D_80069630);
    DibujarSombras(D_8006AD80);
    func_80045150(D_800694B8);
    DibujarListaReflejada(D_80069630);
    if (D_800694D8 != 0) {
        func_8001020C(0x1C40);
        func_8003B5AC(D_800694D8);
        func_8001020C(0x1840);
    }
    __asm__ volatile ("addiu $29, $29, 4\n\t"
                      "lw $29, 0($29)\n\t"
                      "nop");
}

void func_800163E4(void)
{
    func_8003E3C0();
    func_8003F3F0(D_8006967C);
}

/*
 * Tipos de las variables de control: `pausa` es s8, `ocioso` y `demo` son s16 y el contador de cuadros
 * D_80069676 es volatile u16. `pausa` va en 8 bits porque el original emite `move s4,zero` para el
 * cero de `ocioso`: con `pausa` de 16 bits el volcado de `cc1` da `(set (reg:HI 20) (const_int 0))`
 * tras la asignacion global y `(set (reg:HI 20) (reg:HI 21))` tras la segunda planificacion, es decir
 * `move s4,s5` (puntuacion 200 frente a 0). Se supone, sin verificar, que la sustitucion la hace la
 * propagacion de valores posterior a la recarga y que solo copia entre registros del mismo modo; con
 * `pausa` de 8 bits con signo el cero de cada variable queda en su `move` desde zero y la prueba de
 * `pausa` sigue siendo `move v0,s5` (con 8 bits sin signo cada una de las dos pruebas lleva
 * `andi v0,s5,0xff`).
 *
 * El estado principal y los registros del mando se acceden por su direccion constante, sin variable
 * local de puntero: el ensamblador los muestra con la forma simbolica (`lui s1,%hi(D_80010000)` y
 * `%lo(D_8001004F)(s1)`) y las dos escrituras producen los mismos bytes; con `&D_80010000` como base
 * el `lui` deja de compartirse (un `lui at` por acceso).
 *
 * La envoltura do/while (0) de la lectura del tiempo inicial del cuadro no genera codigo:
 * pondera por un nivel mas la referencia a la tabla de tiempos D_8006CF68 que contiene (de 5 a 6 usos
 * ponderados sobre una vida de 564: prioridad floor_log2(R) * R / L de 2 * 5 / 564 = 0,0177 a
 * 2 * 6 / 564 = 0,0213), que pasa por encima de la constante 3 (6 usos sobre 640: 2 * 6 / 640 = 0,0188)
 * en el orden de global-alloc. Con la envoltura la tabla toma s7 y la constante 3 toma s8, como el
 * original; sin ella la puntuacion es 225 y con ella 0. La forma del fuente original que producia este
 * reparto se desconoce.
 *
 * La envoltura do/while (0) del cuerpo del `if` de la demostracion no genera codigo: pondera por un
 * nivel mas los pseudos del bloque y cambia el orden de local-alloc (`-dl`, bloque 60), que asigna
 * antes la cantidad de mayor floor_log2(R) * R / L (L en instrucciones desde que nace hasta que muere
 * en el orden de la primera planificacion, contadas sobre el volcado; no es la cifra `across` que este
 * imprime, 2 para el pseudo 330, con la que la comparacion no daria el reparto observado. Se supone, sin
 * verificar en el fuente del compilador, que esa es la longitud que compara: con ella salen los registros
 * de los dos casos). El puntero de la pila de botones (pseudo 326) forma una sola
 * cantidad con su ultimo derivado (338, el puntero menos 6, que se calcula cuando 326 muere), y los
 * derivados intermedios (330 y 334) solo viven desde su calculo hasta el almacen en D_800695B0. Sin la
 * envoltura la cantidad del puntero tiene 22 + 4 usos sobre 16 (4 * 26 / 16 = 6,5) y 330 tiene 4 sobre 1
 * (2 * 4 / 1 = 8,0): 330 y 334 toman v0 y el puntero v1. Con ella quedan en 33 + 6 sobre 16
 * (5 * 39 / 16 = 12,19) y 6 sobre 1 (2 * 6 / 1 = 12,0): el puntero se asigna antes y toma v0 (`lw v0`
 * en 0x80016B50) y 330, 334 y el primer valor toman v1 (`lhu v1,0(v0)` en 0x80016B58), como el
 * original. La secuencia de instrucciones, el orden de `regs to allocate` y las disposiciones de
 * global-alloc no cambian. La envoltura abarca todo el cuerpo: limitada a las cuatro lecturas, la carga
 * de D_80069662 queda tras el ultimo almacen en D_800695B0 (el original la adelanta, `lh a0` en
 * 0x80016B9C) y la puntuacion es 940. Sin la envoltura la puntuacion es 310 y con ella 0. La forma del
 * fuente original que producia este reparto se desconoce.
 *
 * Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta
 * del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la
 * pausa y la maquina de estados D_80069662 (el estado 0x16 en adelante recarga el contenido).
 * Con el mando ocioso unos 900 cuadros entra en el ciclo de demostracion.
 */
s32 main(void)
{
    EstadoPrincipal* e0;
    s16 contador;
    s16 ocioso;
    s16 demo;
    s8 pausa;

    func_80044D44();
    func_80044E58();
    func_80015EC0();
    e0 = ESTADO_PRINCIPAL;
    e0->nivel = 2;
    ConstruirRegistrosArchivo();
    func_80016118();
    D_800694F0 = e0->nivel;
    func_8004443C(e0->nivel);
    while (CargarContenedor((s16)ESTADO_PRINCIPAL->nivel, (void*)0x80077000) != 0) {
    }
    pausa = 0;
    ocioso = 0;
    demo = 0x4A;
    func_80019364((void*)D_800694FC);
    DrawSyncCallback(0);
    VSyncCallback(func_80040AF0);
    srand(1);
    D_80069534 = 0;
    D_80069694 = 0;
    D_80069638 = 0;
    D_80069510 = 1;
    D_800695DC = 0;
    D_8006967C += 1;
    func_800353B0(D_80069518);
    SetRCnt(0xF2000000 | 2, 0xFFFF, 0x2000);
    StartRCnt(0xF2000000 | 2);
    func_8003DF84();
    func_8003AA50(1, 0x100);
    for (;;) {
        if (D_8006967C == 3) {
            D_8006967C = 0;
        }
        do {
            func_8003E9E8();
        } while ((s16)D_80069676 == 2);
        /* Envoltura sin codigo: pondera la tabla de tiempos (ver la cabecera). */
        do {
            D_8006CF68[D_8006967C] = VSync(1);
        } while (0);
        func_80016218();
        D_8006CF68[D_8006967C] = VSync(1) - D_8006CF68[D_8006967C];
        if (D_80069662 == 0 && D_8006AA70[3] != 0) {
            SondearTarjeta(1);
        } else {
            func_80015E94();
        }
        if (pausa != 0) {
            if (!(ESTADO_PRINCIPAL->mando.botones_a & 0x800)) {
                pausa = 0;
            }
        } else if (D_8006AA70[0] == 0) {
            if (D_8006AA70[0xC] == 0 && D_80069662 == 0) {
                if ((ESTADO_PRINCIPAL->mando.botones_a & 0x800) && D_8006966A == 0 && (!(D_8006D9A8[0] & 0x300) || (D_8006D9A8[0] & 1)) && ESTADO_PRINCIPAL->r[BANCO_PAUSA] == 0) {
                    contador = 0;
                    func_80037FB8(D_80069508);
                    func_80037FE8(D_80069508);
                    D_8006AA70[0xC] = 1;
                    D_8006AA70[0xD] = 0;
                    D_8006AA70[0xE] = 1;
                    D_8006AA70[0xF] = 0;
                    D_8006AA70[0x10] = 1;
                    D_8006965A = 0;
                    D_80069659 = 0;
                    func_80040240();
                    do {
                        D_8006967C += 1;
                        D_80069676 += 1;
                        if (D_8006967C == 3) {
                            D_8006967C = 0;
                        }
                        do {
                        } while ((s16)D_80069676 == 2);
                        func_80016218();
                        func_800163E4();
                        contador++;
                    } while (contador < 3);
                    D_8006965A = 0;
                    D_80069659 = 0;
                    func_80040240();
                    func_8003E88C();
                    func_8003FC88();
                    if (ESTADO_PRINCIPAL->mando.botones != 0) {
                        for (;;) {
                            func_8004048C();
                            if (ESTADO_PRINCIPAL->mando.botones == 0) {
                                break;
                            }
                        }
                    }
                }
            } else if (D_8006AA70[0xC] == 2) {
                D_8006AA70[0xC] = 0;
                D_8006963C = 0;
                D_80069595 = 0;
                D_800695A0 = 0;
                pausa = 1;
                func_8003E948();
                func_8003FD60();
                D_80069628 = pausa;
                func_80037FB8(D_80069508);
            }
        }
        if (ESTADO_PRINCIPAL->nivel == 0) {
            ocioso++;
            if (ESTADO_PRINCIPAL->r[0x8D] & 2) {
                ocioso = 0;
            }
            if (ocioso >= 0x385) {
                ocioso = 0;
                D_80069662 = 1;
                ESTADO_PRINCIPAL->nivel = demo;
                ESTADO_PRINCIPAL->r[BANCO_DEMO] = 1;
            }
        }
        if (D_80069662 != 0) {
            if (D_80069662 == 1) {
                func_8003E094();
                func_8003AA7C(2, 0x100);
                D_800694E0 = 0;
                D_800694E1 = 0;
                D_800694E8 = 0;
                func_80037FB8(D_80069508);
            } else if (D_80069662 >= 0x16 && ESTADO_PRINCIPAL->nivel >= 0) {
                func_8003E068();
                if (ESTADO_PRINCIPAL->nivel == 0) {
                    ocioso = 0;
                    func_80015F38();
                }
                D_8006965A = 0;
                D_80069659 = 0;
                func_80040240();
                D_800694F0 = ESTADO_PRINCIPAL->nivel;
                func_8004443C(ESTADO_PRINCIPAL->nivel);
                func_800445E8(ESTADO_PRINCIPAL->nivel);
                D_8006965A = 0;
                D_80069659 = 0;
                func_80040240();
                if (ESTADO_PRINCIPAL->r[BANCO_DEMO] == 0) {
                    srand((BugsRand() + VSync(1)) % 300);
                } else {
                    func_80015F38();
                    if (demo == 0x4A) {
                        demo = 0x4B;
                        ESTADO_PRINCIPAL->r[0xB8] = 0x83;
                        ESTADO_PRINCIPAL->r[0xB6] = 0x5D;
                    } else if (demo == 0x4B) {
                        demo = 0x4C;
                        ESTADO_PRINCIPAL->r[0xB8] = 0x85;
                        ESTADO_PRINCIPAL->r[0xB6] = 0x5F;
                    } else if (demo == 0x4C) {
                        demo = 0x4D;
                        ESTADO_PRINCIPAL->r[0xB8] = 0x8C;
                        ESTADO_PRINCIPAL->r[0xB6] = 0x66;
                    } else if (demo == 0x4D) {
                        demo = 0x4A;
                        ESTADO_PRINCIPAL->r[0xB8] = 0xEA;
                        ESTADO_PRINCIPAL->r[0xB6] = 0xEB;
                    }
                    ESTADO_PRINCIPAL->r[BANCO_DEMO] = 1;
                    srand(1);
                }
                D_80069534 = 0;
                D_80069694 = 0;
                D_80069638 = 0;
                D_80069510 = 1;
                D_800695DC = 0;
                D_8006967C += 1;
                func_800353B0(D_80069518);
                func_8003E3C0();
                func_8003AA50(1, 0x100);
                continue;
            }
            D_80069662 += 1;
        }
        if (ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0 && (ESTADO_PRINCIPAL->mando.botones & 0x100)) {
            /* Envoltura sin codigo: pondera el puntero de la pila de botones (ver la cabecera). */
            do {
                ESTADO_PRINCIPAL->mando.botones_a = *D_800695B0--;
                ESTADO_PRINCIPAL->mando.botones_e = *D_800695B0--;
                ESTADO_PRINCIPAL->mando.botones_c = *D_800695B0--;
                ESTADO_PRINCIPAL->mando.botones = *D_800695B0--;
                if (D_80069662 == 0) {
                    D_80069662 = 1;
                    ESTADO_PRINCIPAL->nivel = 0;
                }
            } while (0);
        }
        if (D_8006AA70[0xC] == 0) {
            func_800163E4();
        }
        D_8006967C += 1;
        D_80069676 += 1;
    }
}
