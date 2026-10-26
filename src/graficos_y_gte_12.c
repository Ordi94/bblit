#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBETC.H"
#include "psyq/LIBCD.H"

extern s32 func_800415A0(s16 archivo, void* destino);
extern void func_80044A04(void);
extern void func_80019364(void* dato);
extern void func_8003DF84(void);
extern void func_8003E068(void);
extern void func_8003E3C0(void);
extern void func_80040AF0(void);

/*
 * Pantalla de carga y arranque de un contenedor. Las funciones que escriben variables de la
 * zona 0x80069xxx o leen datos pequenos con $gp se emiten como el original solo con un
 * umbral de datos pequenos mayor que cero (-G8) para este archivo; con el -G0 por omision
 * de config/opciones_compilacion.toml conservan el ensamblador (NON_MATCHING). Las dos que
 * usan $gp (func_8004443C y func_80044588) ademas dependen de un simbolo externo pequeno
 * con desplazamiento $gp, que el ensamblador del flujo no reescribe.
 */

/* Registro de 16 bytes por archivo; el campo +4 es el archivo de la pantalla de carga, 0 si no hay. */
typedef struct RegistroArchivo {
    s32 pad0;
    s16 pantalla;
    s16 pad6;
    s32 pad8;
    s32 padC;
} RegistroArchivo;
extern RegistroArchivo D_8005F200[];

extern DISPENV D_8006CF78;
extern void* D_800694FC;
extern u8 D_80010065;

/* Dato pequeno de $gp (+0x188): maquina de estados de la pantalla de carga (0, 2, 4; bit 0 = activa). */
extern u8 D_800694A8;

/* Pone a negro dos veces, con un cuadro de espera, el rectangulo de 512x512 de la VRAM en (512, 0). */
void func_800443CC(void)
{
    RECT r;
    s32 i;

    r.x = 0x200;
    r.y = 0;
    r.w = 0x200;
    r.h = 0x200;
    VSync(0);
    i = 0;
    do {
        ClearImage(&r, 0, 0, 0);
        DrawSync(0);
        VSync(0);
        i++;
    } while (i < 2);
}

#ifdef NON_MATCHING
/*
 * Reinicia el hardware grafico y muestra la pantalla de carga del archivo pedido: apaga
 * los retornos de llamada, limpia la VRAM, carga la imagen asociada y reactiva la pantalla.
 * Para el archivo 3 el numero de pantalla depende de D_80010065 (nivel).
 * Puntuacion 555 con -G8: el cuerpo coincide salvo las cuatro escrituras de 0x188($gp) y
 * el orden de la base de la tabla D_8005F200 frente al indice (el original calcula la base
 * antes del desplazamiento).
 */
void func_8004443C(s32 archivo)
{
    RegistroArchivo* reg;
    DISPENV* env;
    s32 nivel;

    DrawSyncCallback(NULL);
    VSyncCallback(NULL);
    CdReadyCallback(NULL);
    ResetGraph(1);
    DrawSync(0);
    func_80044A04();
    D_800694A8 = 0;
    SetDispMask(0);
    func_800443CC();
    reg = &D_8005F200[archivo];
    if (reg->pantalla != 0) {
        D_800694A8 = 4;
        if (archivo == 3) {
            nivel = D_80010065;
            if (nivel == 1) {
                archivo = 0x68;
            } else if (nivel == 2) {
                archivo = 0x5F;
            } else if (nivel == archivo) { /* el original compara con el propio indice (3) */
                archivo = 0x64;
            } else if (nivel == 4) {
                archivo = 0x54;
            } else if (nivel == 5) {
                archivo = 0x59;
            } else {
                archivo = 1;
            }
        } else {
            archivo = reg->pantalla;
        }
        while (func_800415A0(archivo, (void*)0x80077000) != 0) {
        }
        D_800694A8 = 2;
    }
    env = &D_8006CF78;
    SetDefDispEnv(env, 0x200, 0, 0x200, 0x1E0);
    env->isrgb24 = 0;
    PutDispEnv(env);
    SetDispMask(1);
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_12", func_8004443C);
#endif

#ifdef NON_MATCHING
/*
 * Carga la pantalla del archivo pedido sin reiniciar la pantalla. Puntuacion 290 con -G8:
 * difieren la escritura de 0x188($gp) y que el original conserva el valor leido en dos
 * registros (el de comparacion y el del argumento).
 */
void func_80044588(s32 archivo)
{
    s32 id;

    id = D_8005F200[archivo].pantalla;
    if (id != 0) {
        D_800694A8 = 4;
        while (func_800415A0(id, (void*)0x80077000) != 0) {
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_12", func_80044588);
#endif

#ifdef NON_MATCHING
/*
 * Carga el contenedor pedido, entrega el resultado a func_80019364 y deja armados los
 * retornos de llamada de VSync (func_80040AF0) y de audio y menus. Puntuacion 0 con -G8;
 * con el -G0 por omision la carga de D_800694FC usa otro registro y la funcion pierde un nop.
 */
void func_800445E8(s16 archivo)
{
    func_80044A04();
    while (func_800415A0(archivo, (void*)0x80077000) != 0) {
    }
    func_80019364(D_800694FC);
    DrawSyncCallback(NULL);
    VSyncCallback(func_80040AF0);
    func_8003DF84();
    func_8003E068();
    func_8003E3C0();
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_12", func_800445E8);
#endif
