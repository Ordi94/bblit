#ifndef GLOBALES_H
#define GLOBALES_H

#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBGS.H"

/*
 * Objeto de escena. Solo se declaran los campos que el codigo traducido usa; los huecos son
 * relleno. D_80069698 (el objeto controlado) y la lista de D_80069518 apuntan a esta estructura.
 * Los calculos de volumen de la colision la ven como ObjetoVolumen (geometria.h): ambas vistas
 * coinciden en los angulos de +0xDC y la posicion de +0xE4.
 */
typedef struct Objeto {
    struct Objeto* siguiente;
    u8 pad04[0x14 - 0x04];
    u32 flags14;
    u32 flags18;
    u16 w1C;
    s16 s1E;
    u8 pad20[2];
    u16 w22;
    u8 pad24[2];
    u16 w26;
    u16 w28;
    u8 pad2A[0x2C - 0x2A];
    u16 w2C;
    u8 pad2E[0x38 - 0x2E];
    u16 w38;
    u8 pad3A[2];
    u16 w3C;
    u8 pad3E[0x6C - 0x3E];
    struct Objeto* p6C;
    struct Objeto* p70;
    u8 pad74[0xC0 - 0x74];
    struct Objeto* pC0;
    s32 iC4;
    u8 padC8[0xDC - 0xC8];
    u16 wDC;
    u16 wDE;
    u16 wE0;
    u8 padE2[0xE4 - 0xE2];
    s32 xE4;
    s32 yE8;
    s32 zEC;
    u8 padF0[0x158 - 0xF0];
    s32 i158;
    u32 flags15C;
    u8 pad160[0x17C - 0x160];
    u16 w17C;
    u16 w17E;
    u16* p180;
    u8 pad184[0x192 - 0x184];
    u16 w192;
    u8 pad194[2];
    u16 w196;
} Objeto;

/*
 * Estado de la camara y de la escena en 0x8006D928. Los primeros 0x20 bytes son un GsRVIEW2 del
 * SDK (punto de vista, punto de mira, rz y coordenada padre): GsSetRefView2L recibe la
 * direccion de la estructura entera. Detras vienen los indicadores y los parametros de
 * seguimiento que mueven los eventos de camara.
 */
typedef struct EstadoCamara {
    s32 vpx;
    s32 vpy;
    s32 vpz;
    s32 x;
    s32 y;
    s32 z;
    s32 rz;
    GsCOORDINATE2* super;
    u8 pad20[0x80 - 0x20];
    u16 flags80;
    u8 pad82[0x86 - 0x82];
    s16 s86;
    s16 s88;
    s16 s8A;
} EstadoCamara;

/*
 * Variables globales que mas de un archivo del juego declara. Una sola declaracion por simbolo:
 * el tipo sale del ensamblador original (el ancho de la instruccion de carga y de almacen) y
 * cambiarlo cambia el codigo generado, asi que no se retoca sin repetir diff y verify.
 *
 * Un dato nuevo que dos archivos compartan se declara aqui, no en cada .c; un dato que solo usa
 * un archivo sigue declarandose en ese archivo.
 */

/*
 * D_80069662: estado de la maquina de `main` y de los menus. El ensamblador lo compara con lh en
 * todas partes y solo lo incrementa cargando con lhu; declarado u16, `main` sube de 1025 a 2025.
 */
extern s16 D_80069662;

/*
 * $gp: el registro que el arranque del juego fija en 0x80069320. Recurso transitorio para
 * acceder a datos pequenos por desplazamiento en las funciones que lo usaban antes de que el
 * build soportara -G8 por archivo; el codigo nuevo define el dato como variable pequena (sin
 * extern, ver docs/DESCOMPILACION.md) y deja que maspsx lo reescriba a $gp.
 */
register u8* base_gp __asm__("$28");

/* --- Estado del bucle principal y de la presentacion de cuadros ------------------------- */

/*
 * Anillo de tres buffers de dibujo: indice mostrado (0 a 2). Las comparaciones cargan con lh;
 * solo los incrementos de `main` usan lhu + sh.
 */
extern s16 D_8006967C;

/*
 * Diferencia de marcas de tiempo entre cuadros (D_80069510 - D_80069638): lw y sw de 32 bits,
 * restada con signo.
 */
extern s32 D_80069694;

/*
 * Banco de registros de 8 bits que manejan los eventos y la pausa (lbu en la pausa, sb en la
 * tarjeta de memoria).
 */
extern u8 D_8006AA70[];

/* Pantalla activa. SetDefDispEnv y PutDispEnv lo rellenan y activan: es un DISPENV del SDK. */
extern DISPENV D_8006CF78;

/*
 * Marcas de tiempo del anillo de dibujo: D_80069694 = D_80069510 - D_80069638. Todos los
 * accesos son lw / sw de 32 bits y la resta se interpreta con signo.
 */
extern s32 D_80069510;

/* Tiempo por buffer de dibujo (tres palabras): lw / sw sin extension. */
extern s32 D_8006AD40[];

/*
 * Cuadros pendientes de presentar. El retorno de llamada de VSync la modifica mientras el bucle
 * principal la lee, y el original recarga con lhu en cada espera: debe ser volatile.
 */
extern vu16 D_80069676;

/*
 * Contadores de vibracion del mando. `sb` los pone a cero en `main`, y su direccion se pasa a
 * func_80040430, que los lee con lb (prueba de cero) y lbu (decremento): el parametro es s8*.
 */
extern s8 D_800695A0;
extern s8 D_80069595;
extern s8 D_8006963C;

/* --- Punteros a objetos y a datos cargados -------------------------------------------- */

/*
 * D_80069698: objeto controlado (el protagonista). Se carga con lw en mas de 160 sitios y se
 * indexa por +0x14 (flags14), +0x18 (flags18), +0xDE (angulo) y +0xE4..+0xEC (posicion).
 */
extern Objeto* D_80069698;

/*
 * D_80069518: cabeza de la lista de objetos de escena (enlace en +0). func_800353B0 la recibe
 * como argumento y los eventos la recorren con ->siguiente; lw / sw de 32 bits.
 */
extern Objeto* D_80069518;

/*
 * D_80069630: cabeza de la lista de objetos solidos que recorren las consultas de volumen
 * (enlace en +0x10, ver ObjetoVolumen en geometria.h). El arranque solo la pasa a otras rutinas.
 */
struct ObjetoVolumen;
extern struct ObjetoVolumen* D_80069630;

/*
 * D_800694FC: puntero al bloque de zonas de colision del nivel. Se guarda con sw al cargar el
 * archivo y se pasa tal cual a func_80019364(void*); no se indexa ni se desplaza.
 */
extern void* D_800694FC;

/* --- Camara y listas de ordenacion -------------------------------------------------- */

extern EstadoCamara D_8006D928;

/*
 * Tres listas de ordenacion por buffer de dibujo (D_8006AE20, D_8006AE60, D_8006AEA0), cada una
 * un arreglo de tres GsOT: entradas de 0x14 bytes con el puntero a la lista en +0x10 (GsOT.tag).
 * El arranque las limpia con GsClearOt, que recibe un GsOT*, y func_80040B8C envia cada
 * lista con DrawOTag.
 */
extern GsOT D_8006AE20[];
extern GsOT D_8006AE60[];
extern GsOT D_8006AEA0[];

/* --- Banderas de un byte -------------------------------------------------------------- */

/* Botones del cuadro en el estado principal (0x80010010): lhu en los eventos y la camara, sh en el mando. */
extern u16 D_80010010;

/* Banderas de `main`, de los eventos y de los menus: se escriben con sb y se leen con lbu. */
extern u8 D_800694E0;
extern u8 D_800694E1;
extern u8 D_800694E8;
extern u8 D_80069594;
extern u8 D_800695DC;
extern u8 D_80069659;

/*
 * Contadores de vibracion de los motores del mando: los eventos y el mando los escriben con sb y
 * func_80040240 los lee con lbu.
 */
extern u8 D_8006965A;
extern u8 D_8006965B;

/*
 * D_8006D9A8: palabra de estado del nivel. Casi todo el codigo la lee con lhu (mascaras 0x300 y
 * 0x1) y la escribe con sh; func_8004048C y func_8001D31C la cargan entera con lw (quien necesite
 * los 32 bits la lee como *(u32*)D_8006D9A8).
 *
 * Se declara como arreglo de cinco u16 (10 bytes) y no como escalar: con el umbral de datos
 * pequenos de 8 bytes (-G8) un escalar se emite en forma simbolica y el original usa lui +
 * desplazamiento, que es lo que produce un objeto mayor que el umbral. Como escalar,
 * func_80032684 sube de 0 a 365 y func_80031FE0 de 20 a 130.
 */
extern u16 D_8006D9A8[5];
extern u8 D_8006965E;

/*
 * D_8006966A: bandera de menu. La leen con lb las rutinas que ya estan en C (func_80031FE0,
 * func_8004048C) y con lbu las que aun no lo estan, que solo la comparan con cero.
 */
extern s8 D_8006966A;

/* Cursor descendente de la demostracion: se carga y se guarda como puntero (lw / sw). */
extern u16* D_800695B0;

/* --- Motor e inicializacion ------------------------------------------------------------- */

/*
 * D_80076188: puntero a la siguiente primitiva libre del anillo de primitivas del motor. Todos
 * los accesos son lw / sw de 32 bits (func_80016218, func_80045150, func_800415A0, func_800399C8);
 * func_80045150 le suma 0x28 por glifo y lo compara con D_8006958C, y func_80016218 lo guarda en
 * D_8006AD40[]. Se declara s32 y no como puntero porque asi lo comparan y lo suman los originales.
 */
extern s32 D_80076188;

/*
 * D_8006B558: vector de tres palabras (x, y, z) del evento de zona. func_8001E1A4 lo rellena con
 * tres sw sobre +0, +4 y +8 desde los campos +0x18, +0x1C y +0x20 de la zona; func_80031650 solo
 * pasa su direccion a func_8001D588.
 */
extern s32 D_8006B558[3];

/*
 * D_80069558: puntero a un u16 (el angulo que func_8001DA14 y func_80020B90 copian a +0x26 del
 * objeto). Se guarda con sw (cero en func_80044A04, el valor leido de 0x1F8000BC en
 * func_80033358) y se desreferencia con lhu 0(reg) en func_8001DA14 y func_80020B90.
 */
extern u16* D_80069558;

/*
 * D_800695D0: numero de entradas de la pila de datos de eventos D_8006B658. Se carga con lhu y se
 * guarda con sh (func_800313D4, func_800353B0); func_80044A04 solo toma su direccion para la
 * tabla de punteros D_8006B2F8[13].
 */
extern u16 D_800695D0;

/*
 * D_80069610: direccion del anillo de primitivas sobre la que espera func_80039CD0. lw / sw de 32
 * bits (func_80039CD0, func_8003DF10, func_80040B8C, func_800415A0); la distancia a otro puntero
 * se calcula con subu y se prueba con bgez, y func_80040B8C la sustituye por D_80069614.
 */
extern u32 D_80069610;

/*
 * D_8006B658: pila de ocho palabras de 16 bits de la que func_800313D4 apila con sh sobre
 * D_800695D0 * 2; func_80044A04 solo toma su direccion para D_8006B2F8[14].
 */
extern u16 D_8006B658[8];

/*
 * D_800694B8: inicio de la tabla de entradas de ocho bytes de glifos (lw en func_80016218,
 * func_80045368 y func_800353B0; sw en func_800415A0). Se pasa como puntero opaco a
 * func_80045150 y func_80045368 lo indexa con (indice << 3) sumando la direccion.
 */
extern void* D_800694B8;

#endif
