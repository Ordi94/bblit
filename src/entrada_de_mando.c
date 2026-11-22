#include "common.h"
#include "globales.h"
#include "arranque.h"
#include "psyq/TYPES.H"
#include "psyq/LIBPAD.H"
#include "psyq/LIBETC.H"
extern void MemCardStart(void);

/*
 * Lectura del mando (libpad). Las funciones func_8003FFA0, func_80040240, func_80040430 y
 * func_8004048C escriben variables de la zona 0x80069xxx en forma simbolica (sb $0,D_xxx,
 * que el ensamblador expande con $at), como el original, solo con un umbral de datos
 * pequenos mayor que cero (-G8) para este archivo. Con el -G0 por omision de
 * config/opciones_compilacion.toml conservan el ensamblador (NON_MATCHING). Con -G8 el
 * compilador emite los cuerpos en C despues de todo el ensamblador incluido, de modo que
 * el archivo solo admite mezcla si las funciones en C son las ultimas en direcciones.
 *
 * Las constantes de 0x8001xxxx se direccionan por direccion absoluta (ver EstadoPrincipal en arranque.h): la
 * comparacion con el original difiere solo en la forma de la direccion (simbolo frente a
 * numero), los bytes son los mismos.
 */

/* Entrada de 16 bytes de la tabla de configuraciones de botones (8 mascaras de 16 bits). */
typedef struct EntradaTabla {
    u16 v[8];
} EntradaTabla;
extern EntradaTabla D_8005EE38[];

/* Acceso a la zona 0x80069xxx con el ancho que usa el original. */
extern u8 D_8006957C;
extern u8 D_800695E0;
extern u8 D_8006965C;
extern u8 D_8006965D;

extern void func_8005A21C(s32 modo);

/* Estado auxiliar del mando (zona 0x80069xxx y bufer de la BIOS). */
extern u16 D_800695EA;
extern s16 D_80069672;
extern u8 D_8006CFF1;
extern u8 D_8006CFF2;
extern u8 D_8006CFF3;
extern u8 D_8006CFF6;
extern u8 D_8006CFF7;

/* Registro absoluto del eje Y: lo escribe el original por direccion, sin base compartida. */
#define W14 (*(s16*)0x80010014)

extern void func_80040430(s8* contador, u16 mascara);

/*
 * Arranque del mando: borra el estado de vibracion y de repeticion, inicia la tarjeta de
 * memoria y el controlador directo, y espera hasta 30 cuadros a que el mando 0 este estable
 * (PadStateStable); si admite el modo extendido lo fija en analogico (hasta 5 intentos).
 * Puntuacion 25 con -G8: solo cambia la forma de las direcciones 0x8001000A..0x80010010
 * (simbolo en el objetivo, numero en el candidato); los bytes son los del original. Con el
 * -G0 por omision las escrituras a 0x80069xxx usan un registro general en lugar de $at.
 */
void func_8003FFA0(void)
{
    s32 i;
    s32 estable;

    estable = 6;
    D_8006957C = 0;
    D_800695E0 = 0;
    D_80069658 = 0;
    D_80069659 = 0;
    D_8006965A = 0;
    D_8006965B = 0;
    D_8006965C = 0;
    D_8006965D = 0;
    D_8006965E = 0;
    ESTADO_PRINCIPAL->mando.botones_a = 0;
    ESTADO_PRINCIPAL->mando.botones_e = 0;
    ESTADO_PRINCIPAL->mando.botones_c = 0;
    ESTADO_PRINCIPAL->mando.botones = 0;
    func_8005A21C(1);
    i = 0;
    MemCardStart();
    PadInitDirect(&D_8006CFF0, &D_8006D038);
    PadStartCom();
    do {
        if (PadGetState(0) == estable) {
            break;
        }
        VSync(0);
        i++;
    } while (i < 30);
    if (PadInfoMode(0, 2, 0) != 0) {
        i = 0;
        do {
            while (PadGetState(0) != 6) {
            }
        } while (PadSetMainMode(0, 1, 2) == 0 && ++i < 5);
    }
}

/*
 * No coincide en el diff (70 con g = 8 y con -G0), aunque los bytes son los del original (build y verify
 * OK con este cuerpo): el objetivo usa los simbolos D_80010026..D_8001003C y D_80010051 y el candidato
 * direcciones numericas con un lui compartido. Con un extern por dato el compilador emite un lui por
 * simbolo (2435).
 * Carga la configuracion de botones: fija las mascaras de las cuatro direcciones y copia a
 * la tabla de salida los ocho valores de la configuracion elegida (16 bytes por entrada).
 */
void func_800400C0(void)
{
    EntradaTabla* t;

    ESTADO_PRINCIPAL->mando.direcciones[0] = 0x8000;
    ESTADO_PRINCIPAL->mando.direcciones[1] = 0x2000;
    ESTADO_PRINCIPAL->mando.direcciones[2] = 0x1000;
    ESTADO_PRINCIPAL->mando.direcciones[3] = 0x4000;
    t = &D_8005EE38[ESTADO_PRINCIPAL->r[BANCO_CONFIG]];
    ESTADO_PRINCIPAL->mando.mapa[0] = t->v[0];
    ESTADO_PRINCIPAL->mando.mapa[1] = t->v[1];
    ESTADO_PRINCIPAL->mando.mapa[2] = t->v[2];
    ESTADO_PRINCIPAL->mando.mapa[3] = t->v[3];
    ESTADO_PRINCIPAL->mando.mapa[4] = t->v[4];
    ESTADO_PRINCIPAL->mando.mapa[5] = t->v[5];
    ESTADO_PRINCIPAL->mando.mapa[6] = t->v[6];
    ESTADO_PRINCIPAL->mando.mapa[7] = t->v[7];
}

/*
 * Reasigna los botones fisicos del cuadro a los logicos segun la tabla de configuracion:
 * cada bit bajo (el byte alto, direcciones y sistema, pasa sin tocar) se sustituye por la
 * mascara de salida del boton correspondiente. No actua mientras D_8006AA7C este activa.
 */
void func_80040158(Mando* m)
{
    u32 b;
    u32 r;

    if (D_8006AA7C == 0) {
        b = m->botones_c;
        r = 0;
        if (b & 0x10) {
            r = m->mapa[2];
        }
        if (b & 0x40) {
            r |= m->mapa[3];
        }
        if (b & 0x80) {
            r |= m->mapa[0];
        }
        if (b & 0x20) {
            r |= m->mapa[1];
        }
        if (b & 4) {
            r |= m->mapa[4];
        }
        if (b & 8) {
            r |= m->mapa[6];
        }
        if (b & 1) {
            r |= m->mapa[5];
        }
        if (b & 2) {
            r |= m->mapa[7];
        }
        m->botones_c = (b & 0xFF00) | r;
    }
}

/* Bloque de alineacion de vibracion: dato pequeno que el original direcciona como 0x10($gp). */
u8 D_80069330[8];

/*
 * El original calcula el bloque de alineacion con `addiu a1,gp,0x10`. maspsx reescribe esa direccion a
 * $gp desde la version 2.80 de ASPSX (gp_allow_la); con la 2.79 salian `lui` + `addiu`. Coincide en
 * bytes; la puntuacion 25 que queda es solo la forma simbolica de 0x800100E7 y de D_80069330.
 *
 * Vibracion del mando: mientras el mando 0 anuncia el modo extendido (PadInfoMode 1 = 7 y
 * PadInfoMode 2 distinto de cero) descuenta los dos temporizadores de pulso (D_80069659 el
 * pequeno, D_8006965A el grande) y fija los motores D_8006965C/D_8006965D si el estado
 * global lo permite (bits 7 y 0 de 0x800100E7); si no, borra todo. Al reconectarse (estado
 * 1) o mientras falte la alineacion, reenvia la vibracion con PadSetAct y PadSetActAlign.
 */
void func_80040240(void)
{
    s32 estado;

    estado = PadGetState(0);
    if (estado == 0) {
        D_8006CFF1 = 0;
        return;
    }
    if (PadInfoMode(0, 1, 0) == 7) {
        if (PadInfoMode(0, 2, 0) != 0) {
            if (D_80069658 != 0) {
                if (D_80069659 != 0) {
                    D_80069659--;
                    if ((ESTADO_PRINCIPAL->r[BANCO_VIBRACION] & 0x80) && (ESTADO_PRINCIPAL->r[BANCO_VIBRACION] & 1)) {
                        D_8006965C = 1;
                    }
                } else {
                    D_8006965C = 0;
                }
                if (D_8006965A != 0) {
                    D_8006965A--;
                    if ((ESTADO_PRINCIPAL->r[BANCO_VIBRACION] & 0x80) && (ESTADO_PRINCIPAL->r[BANCO_VIBRACION] & 1)) {
                        if (D_8006965E != 0) {
                            D_8006965D = D_8006AA70[D_8006965E];
                        } else {
                            D_8006965D = D_8006965B;
                        }
                    } else {
                        D_8006965D = 0;
                    }
                } else {
                    D_8006965D = 0;
                }
            } else {
                D_80069659 = 0;
                D_8006965A = 0;
                D_8006965C = 0;
                D_8006965D = 0;
                D_8006965E = 0;
            }
        }
    } else {
        D_80069659 = 0;
        D_8006965A = 0;
        D_8006965C = 0;
        D_8006965D = 0;
        D_8006965E = 0;
    }
    if (estado == 1) {
        D_80069658 = 0;
    }
    if (D_80069658 == 0) {
        PadSetAct(0, &D_8006965C, 2);
        if (PadSetActAlign(0, D_80069330) != 0) {
            D_80069658 = 1;
        }
    }
}

/*
 * Repeticion automatica de un boton: mientras esta pulsado cuenta hacia atras el contador
 * de retardo; al llegar a cero marca el boton en D_800695EA (botones que disparan este
 * cuadro). Soltarlo rearma el retardo en 2 cuadros. Puntuacion 10 con -G8: solo cambia la
 * forma de la direccion 0x8001000C; con -G0 el almacen a D_800695EA no usa $at.
 */
void func_80040430(s8* contador, u16 mascara)
{
    if (ESTADO_PRINCIPAL->mando.botones_c & (s16)mascara) {
        if (*contador != 0) {
            *contador = (u8)*contador - 1;
            return;
        }
        D_800695EA |= mascara;
        return;
    }
    *contador = 2;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 1540 con la configuracion versionada (g = 8 del archivo): 52 diferencias de operando, 0
 * lineas reordenadas y 267 insertadas o borradas. Reserva de pila: el original reserva 0x28 (`addiu sp`
 * en 0x80040494) y sin la local el marco es 0x20; la cifra medida sin la local es 1614 y con ella 1540. El
 * original no usa 0x10(sp) ni 0x14(sp) y guarda ra, s0, s1 y s2 en 0x24, 0x18, 0x1c y 0x20; el volcado del
 * reparto no deja ningun pseudo sin registro, de modo que se desconoce que local del original desaparecio
 * (en una copia de diagnostico fuera de la rama, una llamada eliminada con seis palabras de argumentos da el
 * mismo marco: se supone, sin verificar, que el compilador no reduce el area de argumentos tras eliminarla).
 *
 * Forma del fuente que baja el residuo: el banco D_8006AA70 se lee por un puntero local (`banco`), que el
 * compilador mantiene en s1 hasta la rama por defecto como el original (el original usa `0xc(s1)` y `0x17(s1)` en
 * el cuerpo y en la rama por defecto); el byte 0xc se lee en `v` ANTES del almacen a D_800695EA, como el original
 * (`lbu v0,0xc(s1)` en 0x80040520 y el almacen en 0x80040528), y la base de `est` se calcula tras las tres
 * llamadas de borrado, donde el original repite `lui s0` (0x80040564). Con la lectura en una local de un solo
 * uso, o sin ella, el compilador vuelve a colocar la carga tras el almacen.
 *
 * Una sola variable (`bits`) guarda los botones de direccion en la rama de grabacion y en la de lectura de la BIOS:
 * el original usa el mismo registro (s1) en las dos (`lhu s1` en 0x80040668 y `move s1,s2` en 0x8004074C), y con dos
 * variables la de la rama de grabacion cae en un temporal y la otra intercambia s1 y s2 con `hi`.
 *
 * El byte de vibracion se modifica con `&= 0x7F` y `|= 0x80` en cada caso, sin variable intermedia: el original
 * hace `lbu`, `andi`/`ori` y un `sb` unico (0x80040724) al que salta el primer caso (`j` en 0x80040710), y la
 * fusion de colas lo reproduce al encontrar el mismo `sb` al final de cada camino; con una variable que guardaba el
 * valor y un almacen tras la etiqueta, el compilador sacaba las lecturas de D_8006CFF2/D_8006CFF3 por encima del
 * `sb` y el valor caia en `v1`.
 *
 * Reparto de a3 y t0 en la rama de los ejes (medido en el volcado `-dg`/`-dl`): el original guarda `botones_c` en t0 y
 * el umbral D_8006952C del eje X en a3 (`lhu t0` en 0x80040834 y `lh a3` en 0x8004083C); aqui es al reves porque `global-alloc` asigna antes la
 * lectura de `botones_c` (pseudo 81: 4 usos, vida 19, prioridad 2 * 4 / 19 = 0,42) que la del umbral (pseudo 236:
 * 3 usos, vida 8, prioridad 1 * 3 / 8 = 0,375) y el primero libre es a3. Con un cuarto uso del umbral la prioridad
 * seria 1,0 y el reparto saldria como el del original, pero sumarlo con `umbral = D_8006952C; umbral--; umbral++;` y
 * usar `umbral` en las cuatro comparaciones emite codigo (la puntuacion sube de 1655 a 2080), de modo que no se
 * aplica; la local sola se funde con la lectura y no cambia la cifra. En la rama por defecto, leer el primer byte del banco por el simbolo en lugar
 * de por `banco` no comparte el `lui` de s2: el compilador repite el `lui` en ese bloque (el volcado `-ds` deja
 * dos instrucciones `high` del mismo pseudo, una por bloque).
 *
 * Queda: el `lui` de D_8006AA70 en s2 con el puntero en s1 (el original lo conserva en s2 para la lectura
 * `%lo(D_8006AA70)(s2)` de la rama por defecto; aqui el `lui` va a v0); la lectura del identificador D_8006CFF1 en
 * la rama de grabacion, que sale antes del almacen del tercer registro del cuadro cuando en el original sale
 * despues; el almacen de `lo` en el campo de botones (0x10) que el original conserva antes del almacen de
 * `lo | hi` (0x80040760 y 0x80040768) y que aqui desaparece entre `.cse` y `.combine` (se supone, sin verificar,
 * que lo borra el analisis de vida al ver dos almacenes seguidos a la misma direccion); y la forma simbolica de
 * los campos de 0x80010000.
 *
 * El xor del byte invertido se hace sobre una local de 32 bits (cf2, cf3, cfd): con el byte
 * leido directamente el analizador de tipos del front end estrecha el xor a un byte (sale
 * `nor` + `andi 0xff`, y el combinador lo funde con el desplazamiento: `sll` y `xori 0xff00`),
 * mientras que el original hace `xori 0xff` sin mascara y luego `sll 8`.
 *
 * Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o
 * entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma
 * los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS
 * (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
 * Se usa un switch con goto (la formulacion mas cercana): la estructura de saltos y casi todo el cuerpo
 * coinciden; difieren el reparto de registros de la rama de grabacion y la copia s1 = s2 del valor de los
 * botones de direccion (en el original va antes del `or`, 0x2c0). Sin bajada: if/else en lugar de switch,
 * orden de declaracion de las copias, copia con la expresion repetida.
 */
void func_8004048C(void)
{
    u16 prev;
    u16 mascara;
    u16 a;
    u16 b;
    u16 c;
    u16* grab;
    u32 id;
    u32 v;
    s32 bits;
    s32 hi;
    s32 centro;
    s32 eje;
    s32 lo;
    u32 cf2;
    u32 cf3;
    u32 cfd;
    /* Lecturas sin centrar de los ejes X e Y del mando: el original lee cada una una sola vez (0x80040830 y 0x800408E4). */
    u32 eje_x_crudo;
    u32 eje_y_crudo;
    u32 eje_y_mas_uno;
    EstadoPrincipal* est;
    u8* banco;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[2];

    if (D_80069662 == 0 && (D_80069698 == 0 || (D_80069698->flags14 & 0x01000000) == 0)) {
        goto normal;
    }
    if (D_8006AA7C == 0) {
        ESTADO_PRINCIPAL->mando.w3E = 0;
        ESTADO_PRINCIPAL->mando.botones = 0;
        ESTADO_PRINCIPAL->mando.botones_c = 0;
        ESTADO_PRINCIPAL->mando.botones_e = 0;
        ESTADO_PRINCIPAL->mando.botones_a = 0;
        ESTADO_PRINCIPAL->mando.eje_y = 0;
        ESTADO_PRINCIPAL->mando.eje_x = 0;
        if (ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
            D_8006965A = 0;
            D_80069659 = 0;
        }
        func_80040240();
        return;
    }
normal:
    banco = D_8006AA70;
    /* banco[0xC] es el mismo byte que D_8006AA7C (0x8006AA70 + 0xC). */
    v = banco[0xC];
    D_800695EA = 0;
    if (v == 0) {
        func_80040430(&D_800695A0, 0x40);
        func_80040430(&D_80069595, 0x80);
        func_80040430(&D_8006963C, 4);
    }
    est = ESTADO_PRINCIPAL;
    prev = ESTADO_PRINCIPAL->mando.botones_c;
    ESTADO_PRINCIPAL->mando.botones_c = 0;
    ESTADO_PRINCIPAL->mando.botones_e = prev;
    ESTADO_PRINCIPAL->mando.botones_e = prev & D_800695EA;
    if (ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
        /* banco[0x17] es el mismo byte que D_8006AA87[0] (0x8006AA70 + 0x17). */
        if (banco[0x17] != 0 && banco[0x17] != 4) {
            ESTADO_PRINCIPAL->mando.botones = 0;
            ESTADO_PRINCIPAL->mando.botones_c = 0;
            ESTADO_PRINCIPAL->mando.botones_e = 0;
            ESTADO_PRINCIPAL->mando.botones_a = 0;
            return;
        }
        grab = D_800695B0;
        a = grab[0];
        ESTADO_PRINCIPAL->mando.w3E = a;
        ESTADO_PRINCIPAL->mando.botones_a = a;
        ESTADO_PRINCIPAL->mando.botones_e = grab[1];
        b = grab[2];
        ESTADO_PRINCIPAL->mando.botones_c = b;
        c = grab[3];
        id = D_8006CFF1 & 0x7F;
        D_800695B0 = grab + 4;
        ESTADO_PRINCIPAL->mando.botones = c;
        /* La lectura de D_8006CFF2 va dentro de la condicion: sacarla antes del `if` la carga siempre y sube la cifra (6644 a 6964). */
        if ((id == 0x41 || id == 0x73) && ((cfd = D_8006CFF2, ((cfd ^ 0xFF) << 8) & 0x800)) && ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
            ESTADO_PRINCIPAL->mando.botones_a = a | 0x100;
            ESTADO_PRINCIPAL->mando.botones_c = b | 0x100;
            ESTADO_PRINCIPAL->mando.botones = c | 0x100;
        }
        bits = ESTADO_PRINCIPAL->mando.botones_a;
        ESTADO_PRINCIPAL->mando.eje_x = 0;
        ESTADO_PRINCIPAL->mando.eje_y = 0;
        if (bits & 0x8000) {
            ESTADO_PRINCIPAL->mando.eje_x = -0x80;
        } else if (bits & 0x2000) {
            ESTADO_PRINCIPAL->mando.eje_x = 0x7F;
        }
        if (bits & 0x1000) {
            W14 = 0x7F;
        } else if (bits & 0x4000) {
            W14 = -0x80;
        }
        D_8006965A = 0;
        D_80069659 = 0;
        func_80040240();
        return;
    }
    func_80040240();
    switch (D_8006CFF1 & 0x7F) {
    case 0x41:
        est->r[BANCO_VIBRACION] &= 0x7F;
        goto aplicar;
    case 0x73:
        est->r[BANCO_VIBRACION] |= 0x80;
    aplicar:
        cf2 = D_8006CFF2;
        hi = (cf2 ^ 0xFF) << 8;
        bits = hi;
        cf3 = D_8006CFF3;
        lo = cf3 ^ 0xFF;
        b = lo | hi;
        ESTADO_PRINCIPAL->mando.botones_c = lo;
        ESTADO_PRINCIPAL->mando.botones = lo;
        /* El original lo almacena antes de la `xori` de la mascara (`sh zero` en 0x80040738); escrito ahi la cifra
           es 1655 y tras los dos primeros almacenes de `botones` 1560: el planificador lo adelanta solo. */
        D_80069672 = 0;
        ESTADO_PRINCIPAL->mando.botones = b;
        if ((hi & 0xF000) != 0 || (D_8006CFF1 & 0x7F) == 0x41) {
            ESTADO_PRINCIPAL->mando.botones_c = b;
            func_80040158(&ESTADO_PRINCIPAL->mando);
            ESTADO_PRINCIPAL->mando.eje_x = 0;
            ESTADO_PRINCIPAL->mando.eje_y = 0;
            ESTADO_PRINCIPAL->mando.w22 = 0;
            ESTADO_PRINCIPAL->mando.w24 = 0;
            prev = ESTADO_PRINCIPAL->mando.botones_c & ~ESTADO_PRINCIPAL->mando.botones_e;
            ESTADO_PRINCIPAL->mando.w3E = prev;
            ESTADO_PRINCIPAL->mando.botones_a = prev;
            if (hi & 0x8000) {
                ESTADO_PRINCIPAL->mando.eje_x = -0x80;
            } else if (hi & 0x2000) {
                ESTADO_PRINCIPAL->mando.eje_x = 0x7F;
            }
            if (bits & 0x1000) {
                W14 = 0x7F;
            } else if (bits & 0x4000) {
                W14 = -0x80;
            }
            return;
        }
        ESTADO_PRINCIPAL->mando.botones_c = lo | (hi & 0xFFF);
        func_80040158(&ESTADO_PRINCIPAL->mando);
        centro = ESTADO_PRINCIPAL->mando.centro_x;
        mascara = ESTADO_PRINCIPAL->mando.botones_c;
        /* Cada eje se lee una sola vez (0x80040830 y 0x800408E4) y las ramas reutilizan el valor tras los almacenes;
           la conversion a u8 en las ramas conserva el `andi 0xff` del original (0x80040880 y 0x80040908). */
        eje_x_crudo = D_8006CFF6;
        eje = eje_x_crudo & 0xFF;
        prev = mascara & ~ESTADO_PRINCIPAL->mando.botones_e;
        ESTADO_PRINCIPAL->mando.w3E = prev;
        ESTADO_PRINCIPAL->mando.botones_a = prev;
        if (eje < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x8000;
            ESTADO_PRINCIPAL->mando.eje_x = (u8)eje_x_crudo - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x8000;
        } else if (centro + D_8006952C < eje) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x2000;
            ESTADO_PRINCIPAL->mando.eje_x = eje_x_crudo - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x2000;
        } else {
            ESTADO_PRINCIPAL->mando.eje_x = 0;
        }
        centro = ESTADO_PRINCIPAL->mando.centro_y;
        eje_y_crudo = D_8006CFF7;
        eje = eje_y_crudo & 0xFF;
        if (eje < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.eje_y = centro - ((u8)eje_y_crudo + 1);
            ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a | 0x1000;
            ESTADO_PRINCIPAL->mando.w3E = ESTADO_PRINCIPAL->mando.w3E | 0x1000;
            ESTADO_PRINCIPAL->mando.botones_c = ESTADO_PRINCIPAL->mando.botones_c | 0x1000;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x1000;
        } else if (centro + D_8006952C < eje) {
            /* La lectura mas uno va a una local antes de restarla del centro: con la resta en una sola
               expresion la cifra es 1560 y con la local 1540. */
            eje_y_mas_uno = eje_y_crudo + 1;
            ESTADO_PRINCIPAL->mando.eje_y = centro - eje_y_mas_uno;
            ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a | 0x4000;
            ESTADO_PRINCIPAL->mando.w3E = ESTADO_PRINCIPAL->mando.w3E | 0x4000;
            ESTADO_PRINCIPAL->mando.botones_c = ESTADO_PRINCIPAL->mando.botones_c | 0x4000;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x4000;
        } else {
            ESTADO_PRINCIPAL->mando.eje_y = 0;
        }
        return;
    default:
        /* La base del estado se reutiliza aqui (`est`, 0x800409D8): el original no la recalcula. */
        D_80069672 += 1;
        if (D_80069672 == 4) {
            /* banco[0xC] es D_8006AA7C; banco[0] es el primer byte del banco D_8006AA70. */
            if (banco[0xC] == 0) {
                est->mando.botones_a = 0x800;
            }
        } else if (D_80069672 >= 5) {
            /* El original carga D_8006D9A8 entera con lw; globales.h la declara u16[5] por el resto de usos. */
            /* El original emite antes el bloque de la prueba de D_8006AA7C (0x80040A2C) que el de la rearme: la condicion va invertida. */
            if (banco[0] != 0 || D_8006966A != 0 || (*(u32*)D_8006D9A8 & 0x301) != 1 || ESTADO_PRINCIPAL->r[BANCO_PAUSA] != 0) {
                if (D_8006AA7C == 0) {
                    D_80069672 = 3;
                }
            } else {
                D_80069672 = 5;
                est->mando.botones_a = est->mando.botones_a & 0xF7FF;
            }
        }
        return;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/entrada_de_mando", func_8004048C);
#endif
