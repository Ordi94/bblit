#include "common.h"
#include "globales.h"
#include "cargador.h"
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
 * Pantalla de carga y arranque de un contenedor. Este archivo se compila con un umbral de datos
 * pequenos mayor que cero (-G8) en config/opciones_compilacion.toml: la maquina de estados de la
 * carga (D_800694A8) es un dato pequeno que el original direcciona como 0x188($gp).
 */

extern u8 D_80010065;

/*
 * Dato pequeno de $gp (+0x188): maquina de estados de la pantalla de carga (0, 2, 4; bit 0 = activa).
 * Es la misma variable que define graficos_y_gte_10.c: ambas son definiciones tentativas (sin extern)
 * y el enlazador funde los simbolos comunes en uno solo. Con -fno-common se duplicaria.
 */
u8 D_800694A8;

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

/*
 * Reinicia el hardware grafico y muestra la pantalla de carga del archivo pedido: apaga
 * los retornos de llamada, limpia la VRAM, carga la imagen asociada y reactiva la pantalla.
 * Para el archivo 3 el numero de pantalla depende de D_80010065 (nivel). La tabla de
 * registros se toma por un puntero local: asi el original calcula la base antes del
 * desplazamiento del indice. Coincide en bytes (3 referencias en forma numerica; el diff puntua 15
 * por la forma simbolica).
 */
void func_8004443C(s32 archivo)
{
    RegistroArchivo* reg;
    RegistroArchivo* tabla;
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
    tabla = D_8005F200;
    reg = &tabla[archivo];
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

/*
 * Carga la pantalla del archivo pedido sin reiniciar la pantalla. La tabla de registros se toma por un puntero
 * local y la maquina de estados de la carga (D_800694A8) pasa a 4 antes de leer el numero de pantalla: asi el
 * original reparte la tabla y el argumento en registros distintos. Coincide en bytes (1 referencia en forma
 * numerica; el diff puntua 5 por la forma simbolica).
 */
void func_80044588(s32 archivo)
{
    RegistroArchivo* reg;
    RegistroArchivo* tabla;

    tabla = D_8005F200;
    reg = &tabla[archivo];
    if (reg->pantalla != 0) {
        D_800694A8 = 4;
        archivo = reg->pantalla;
        while (func_800415A0(archivo, (void*)0x80077000) != 0) {
        }
    }
}

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
