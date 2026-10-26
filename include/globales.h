#ifndef GLOBALES_H
#define GLOBALES_H

#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBGS.H"

/* Tipos que el objeto referencia; sus campos se definen donde se leen (motor.h, objetos.h, menus.h). */
struct NodoSecuencia;
struct RegistroAnim;
struct Ayuda;
struct ModeloDibujo;

/*
 * Registro de dieciseis bytes de la tabla de fotogramas; solo se lee el u16 de +0xA
 * (func_80044EA8).
 */
typedef struct Fotograma {
    u8 pad00[0x0A];
    u16 h0A;
    u8 pad0C[4];
} Fotograma;

typedef struct TablaFotogramas {
    u8 pad00[0x10];
    Fotograma* fotogramas;
} TablaFotogramas;

/*
 * Definicion de una animacion o de un modelo: la comparten el recorrido de animaciones
 * (func_80044EA8, func_80045C4C: tipo en +0x4E y tabla de fotogramas en +0x54) y la creacion de
 * objetos de escena (func_80037DB4: la bandera 2 de +0x0A indica que el objeto tiene jerarquia de
 * ayudantes y la palabra de +0x54 se copia al ayudante como valor inicial).
 */
typedef struct DefinicionAnimacion {
    u8 pad00[0x0A];
    u16 wA;
    u8 pad0C[0x4E - 0x0C];
    u16 tipo;
    u8 pad50[4];
    TablaFotogramas* tabla;
} DefinicionAnimacion;

/*
 * Nodo de la lista que el objeto lleva en +0x74: enlace al siguiente en +0 y la definicion en +8
 * (func_80044EA8, func_80045C4C recorren la lista; func_80037DB4 solo lee la definicion del primer
 * nodo).
 */
typedef struct NodoAnimacion {
    struct NodoAnimacion* sig;
    u8 pad04[4];
    DefinicionAnimacion* def;
} NodoAnimacion;

/*
 * Giro de un objeto (+0xDC). La logica de los objetos lo lee como tres angulos de 16 bits sin
 * signo (lhu) y las rutinas del SDK y del calculo de volumen como un SVECTOR (lh): la union deja
 * ambas lecturas sin casts sueltos y el ancho de cada acceso lo fija el ensamblador de quien lo
 * usa.
 */
typedef union GiroObjeto {
    SVECTOR rotate;
    struct {
        u16 x;
        u16 y;
        u16 z;
        u16 pad;
    } u;
} GiroObjeto;

/*
 * Transformacion propia del objeto (+0xCC): escala en +0, giro en +0x10 y traslacion en +0x18.
 * Tiene el mismo diseno que GsCOORD2PARAM del SDK, salvo el giro (ver GiroObjeto): el nodo
 * coord.param del objeto apunta aqui, con el cast de PARAMETROS_SDK. func_8001CF50 y
 * func_8001CFCC reconstruyen la matriz del nodo desde ella.
 */
typedef struct ParametrosObjeto {
    VECTOR escala;
    GiroObjeto giro;
    VECTOR trans;
} ParametrosObjeto;

/* Direccion de la transformacion propia de un objeto con el tipo del SDK, para coord.param. */
#define PARAMETROS_SDK(o) ((GsCOORD2PARAM*)&(o)->param)

/*
 * Bloque de trabajo de la animacion del objeto (+0x144 del objeto): estado del fotograma en
 * curso. func_8001CD84 reinicia h02, b08, i14 y flags18 al cambiar de secuencia, func_80020A90
 * lee h0A (altura del peldano) y func_80045C4C guarda en +0x20 la tabla de fotogramas de la
 * animacion elegida; func_80045498 recibe su direccion.
 */
typedef struct BloqueTrabajo {
    u8 pad00[2];
    s16 h02;
    u8 pad04[4];
    u8 b08;
    u8 pad09;
    s16 h0A;
    u8 pad0C[0x14 - 0x0C];
    s32 i14;
    u32 flags18;
    u8 pad1C[4];
    struct Fotograma* fotogramas;
} BloqueTrabajo;

/*
 * Objeto de escena (0x1F4 bytes): D_80069698 (el objeto controlado), la lista de D_80069518 y la
 * lista de objetos solidos de D_80069630 apuntan a esta estructura, que es la unica vista de esa
 * memoria. El tamano sale de la reserva de ranuras: func_8003652C, func_800365D0 y func_80036734
 * piden ranuras de paso 0x1F4 al pozo D_8006968C (AllocListNode). Los dos primeros campos son
 * la cabecera de nodo de pozo (enlace y marca de libre).
 *
 * Solo se declaran los campos que el codigo traducido usa; los huecos son relleno. Cada campo cita
 * una funcion cuyo ensamblador fija su desplazamiento y su ancho.
 */
typedef struct Objeto {
    struct Objeto* siguiente;
    u32 flags04;            /* func_8001DF28: lw / sw, bit 2 = sprite visible; pozo: bit 0 = libre, bit 1 = en uso (func_800363D4, func_800365D0) */
    u32 flags08;            /* func_8001CF50, func_8001D75C: lw con mascaras 0x200000 y 0x10000000; indicadores de volumen (graficos_y_gte.c) */
    u32 flags0C;            /* func_8001DF28, func_8001E1A4, func_80045C4C: lw / sw */
    struct Objeto* sig10;   /* lista de objetos solidos que recorren las consultas de volumen (D_80069630); func_80036734 enlaza al final */
    u32 flags14;
    u32 flags18;
    u16 w1C;                /* identificador de plantilla */
    /*
     * +0x1E: lectura con tres formas segun quien lo consulte. Los condicionales del interprete de
     * eventos lo comparan con lh (func_80030990) y el dano del golpe lo carga con lhu y con lbu
     * (func_8001D75C). El campo es s16; func_8001D75C usa casts locales comentados.
     */
    s16 s1E;
    s16 s20;                /* radio del volumen: lh en las consultas de graficos_y_gte.c */
    u16 w22;
    u16 w24;                /* func_800353B0 */
    /*
     * +0x26: se copia como u16 (movimiento, interprete, menus) y el calculo de volumen y la sonda de
     * escena lo cargan con lh (etiqueta de grupo, func_8003A3D0); el campo es u16 y esas rutinas usan
     * un cast (s16) local.
     */
    u16 w26;
    u16 w28;
    s16 s2A;                /* tipo del volumen (2 = solido): graficos_y_gte.c; func_8003652C lo pone a 0 y func_800365D0 a 5 */
    u16 w2C;                /* las rutinas de creacion lo escriben con sh y el resto lo lee con lhu */
    u16 w2E;                /* func_800353B0 */
    u32 alcance2;           /* alcance al cuadrado del volumen: graficos_y_gte.c */
    s32 i34;                /* func_8001D75C: sw con w1C del atacante */
    u16 w38;                /* func_8001D75C, func_80031FE0: solo sh; sin lectura que fije el signo */
    u16 w3A;                /* menus_e_interfaz.c */
    u16 w3C;                /* las rutinas de creacion lo escriben con sh y el resto lo lee con lhu */
    u16 w3E;                /* func_800353B0 */
    u8 pad40[0x48 - 0x40];
    SVECTOR min;            /* caja del volumen (+0x48) y mitades de sprite que lee func_8001DF28 con lh */
    SVECTOR max;            /* +0x50 */
    u8 pad58[0x68 - 0x58];
    s32 i68;                /* func_8001D0FC: sw zero */
    struct Objeto* p6C;
    struct Objeto* p70;
    struct NodoAnimacion* lista;   /* func_80044EA8, func_80045C4C: lw, lista de animaciones; func_80037DB4 la usa como descriptor de modelo */
    /*
     * +0x78: la misma palabra se lee como lista de ayudantes (objetos con jerarquia, pozo
     * D_8006964C), como lista de modelos que dibuja func_8003B5AC y como puntero a datos del
     * modelo: func_8001CF50 solo lo compara con cero, func_8001DF28 suma 0xC para llegar a las
     * coordenadas del sprite y func_80020A90 lo recorre como lista de peldanos (NodoPeldano en
     * motor.h).
     */
    union {
        struct Ayuda* ayudas;
        struct ModeloDibujo* modelos;
        void* p;
    } u78;
    GsCOORDINATE2 coord;    /* +0x7C: func_8001CF50, func_8001CFCC, func_8001D0FC; su param y su super son los lw / sw de +0xC0 y +0xC4 */
    ParametrosObjeto param; /* +0xCC: func_8001CF50, func_8001DF28, func_8001E1A4 */
    struct NodoSecuencia* secuencias;   /* func_8001CD84, func_8001D0FC: lw */
    u8* bloque;             /* func_8001CD84: base del bloque de animacion */
    struct NodoSecuencia* apoyos;       /* func_8001D0FC: lw */
    s32 i100;               /* func_8001C424, func_8001C6CC, func_8001C998: lw / sw */
    s16 h104;               /* func_80020210, func_80020240: lh */
    s16 h106;
    s16 h108;               /* func_8001C424, func_8001C998, func_80020210, func_80020240 */
    s16 h10A;               /* func_8001C6CC, func_8001C998, func_80020210, func_80020240 */
    s16 h10C;               /* func_8001C424, func_8001C6CC, func_8001DA14 */
    u16 w10E;               /* func_8001C424: lhu */
    s16 h110;               /* func_8001C6CC: lh */
    s16 h112;               /* func_8001C6CC: lh */
    u8 pad114[0x116 - 0x114];
    s16 h116;               /* func_8001C424: lh */
    u8 pad118[0x13C - 0x118];
    s32 i13C;               /* func_80020A90: sw */
    u8 pad140[0x144 - 0x140];
    BloqueTrabajo trabajo;  /* +0x144, ver BloqueTrabajo */
    u8 pad168[0x16C - 0x168];
    struct TablaFotogramas* tabla;      /* func_80044EA8: sw de la tabla activa */
    u8 pad170[0x17C - 0x170];
    u16 w17C;
    u16 w17E;               /* lhu en func_80030018 y func_80020B90; las demas rutinas solo lo ponen a cero */
    /*
     * +0x180: nodo de la secuencia de animacion en curso (func_8001CD84 lo guarda con sw). El
     * interprete de eventos lo lee como tabla de u16 indexada por w17E (func_80030018) y
     * func_80045C4C lo pasa como guion a func_80045498.
     */
    struct NodoSecuencia* p180;
    struct RegistroAnim* registro184;   /* func_8001CD84, func_8001D75C: lw */
    struct NodoSecuencia* nodo188;      /* func_8001D0FC: sw */
    u8 pad18C[0x192 - 0x18C];
    u16 w192;
    u8 pad194[2];
    u16 w196;
    u8 pad198[0x1A8 - 0x198];
    s32 i1A8;               /* func_80020A90: sw */
    u8 pad1AC[0x1F4 - 0x1AC];
} Objeto;

/*
 * Estado de la camara y de la escena en 0x8006D928. Los primeros 0x20 bytes son un GsRVIEW2 del
 * SDK (punto de vista, punto de mira, rz y coordenada padre): GsSetRefView2L recibe la
 * direccion de la estructura entera. Detras vienen los indicadores y los parametros de
 * seguimiento que mueven los eventos de camara. func_8001CC68 escribe el punto de vista en
 * cuatro copias (+0x0, +0x68, +0x94 y +0xB4) y el punto de mira en dos (+0xC y +0xA4).
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
    u8 pad20[0x68 - 0x20];
    s32 c68;                /* func_8001CC68: sw, copia del punto de vista */
    s32 c6C;
    s32 c70;
    u8 pad74[0x80 - 0x74];
    u16 flags80;
    u8 pad82[0x86 - 0x82];
    s16 s86;
    s16 s88;
    s16 s8A;
    s16 h8C;                /* func_8001D588: sh zero */
    s16 h8E;                /* func_8001D588: sh zero */
    u8 pad90[0x94 - 0x90];
    s32 c94;                /* func_8001CC68: sw, copia del punto de vista */
    s32 c98;
    s32 c9C;
    u8 padA0[0xA4 - 0xA0];
    s32 cA4;                /* func_8001CC68: sw, copia del punto de mira */
    s32 cA8;
    s32 cAC;
    u8 padB0[0xB4 - 0xB0];
    s32 cB4;                /* func_8001CC68: sw, copia del punto de vista */
    s32 cB8;
    s32 cBC;
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

/* --- Camara, eventos y tarjeta de memoria ------------------------------------------------ */

/*
 * D_80010076: bandera de un byte del estado principal. El ensamblador la carga con lbu (main,
 * func_8004048C, func_80033358, func_8003B5AC) y la guarda con sb (func_8003B5AC); la tarjeta de
 * memoria la escribe como simbolo (con -G8 cc1 emite `sb $0,D_80010076`), por lo que no se
 * accede por un puntero.
 */
extern u8 D_80010076;

/*
 * D_80069560: objeto de referencia de la camara. Se guarda con sw (0x80036020 en func_800353B0,
 * func_800415A0, func_80044A04 con $zero) y se carga con lw (0x800353F8): se compara y se copia
 * como puntero de objeto y tambien se pone a cero. Se declara void* porque el cargador le asigna
 * un puntero a nodo de lista (func_800415A0); como puntero genera el mismo codigo que como entero
 * en todas las funciones que lo usan.
 */
extern void* D_80069560;

/*
 * D_80069618, D_8006961C, D_80069624: parametros de seguimiento de la camara. Palabras de 32 bits:
 * func_80033358 las carga con lw (0x8003361C, 0x80033624, 0x8003362C) y los eventos las escriben
 * con sw.
 */
extern s32 D_80069618;
extern s32 D_8006961C;
extern s32 D_80069624;

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
 * D_800695D0: numero de entradas de la pila de datos de eventos D_8006B658 (ocho como maximo).
 * func_800353B0 lo pone a cero con sh (0x80036010); func_800313D4 lo carga con lhu y lo guarda con
 * sh; los eventos lo comparan con 8, lo leen y lo incrementan. func_80044A04 solo toma su
 * direccion para la tabla de punteros D_8006B2F8[13]. Es volatile porque el original recarga el
 * valor en cada acceso.
 */
extern vu16 D_800695D0;

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
 * D_800694B8: puntero a datos del nivel y inicio de la tabla de entradas de ocho bytes de glifos.
 * Se guarda con sw (0x80041E70 en func_800415A0) y se carga con lw (0x800353B8 en func_800353B0,
 * 0x80045390 en func_80045368, func_80016218) para pasarlo tal cual; se pasa como puntero opaco a
 * func_80045150 y func_80045368 lo indexa con (indice << 3) sumando la direccion.
 */
extern void* D_800694B8;

#endif
