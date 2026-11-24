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
typedef struct {
    u8 valor;
} ByteBufferMando;
extern ByteBufferMando D_8006CFF1;
extern ByteBufferMando D_8006CFF2;
extern ByteBufferMando D_8006CFF3;
extern ByteBufferMando D_8006CFF6;
extern ByteBufferMando D_8006CFF7;

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
 * mascara de salida del boton correspondiente. No actua mientras D_8006AA70[0xC] sea distinto de cero.
 */
void func_80040158(Mando* m)
{
    u32 b;
    u32 r;

    if (D_8006AA70[0xC] == 0) {
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
        D_8006CFF1.valor = 0;
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

/*
 * Reserva de pila: el original reserva 0x28 (`addiu sp` en 0x80040494) y sin la local el marco es 0x20; la cifra
 * medida sin la local es 619 y con ella 0. El original no usa 0x10(sp) ni 0x14(sp).
 *
 * El despacho por el identificador del mando es un `switch` en el que 0x41 y 0x73 comparten cuerpo y el cuerpo
 * vuelve a probar el identificador para apagar o encender el bit de vibracion. Con las dos etiquetas seguidas, la
 * primera pasada de saltos convierte el salto incondicional hacia la rama por defecto en un `bne` hacia ella (el
 * volcado `-dr` tiene dos saltos `eq` y uno incondicional; `-dj`, un `eq` y un `ne`). La eliminacion de
 * subexpresiones solo prolonga su camino por saltos condicionales, de modo que asi llega a la rama por defecto y
 * comparte con ella el `lui` de D_8006AA70, que queda en s2 para la lectura `%lo(D_8006AA70)(s2)` (0x800409E4);
 * despues resuelve la prueba repetida y el despacho final es el del original (`beq`, `beq` y `j`, 0x800406F0 a
 * 0x80040704). Con un cuerpo por caso y un salto del primero a la cola comun la cifra es 1350.
 *
 * Los bytes del bufer de la BIOS (D_8006CFF1, D_8006CFF2, D_8006CFF3, D_8006CFF6 y D_8006CFF7) se declaran como
 * estructuras de un solo campo y se leen por ese campo: con bytes sueltos el planificador sube la lectura del
 * identificador (D_8006CFF1) por encima de los almacenes a los campos del estado (el original la deja tras el
 * almacen de 0x8001000C, 0x80040664) y como miembro de estructura la deja detras de ellos. Se declaran uno por
 * uno y no como una sola estructura desde D_8006CFF1: el original los nombra por separado. Se supone, sin
 * verificar, que la diferencia de planificacion es la marca de miembro de estructura de la direccion de memoria.
 *
 * Dos almacenes seguidos al mismo campo estan en el original: a botones_e (0x8004057C y 0x80040588) y, en la rama
 * de lectura de la BIOS, a botones (0x80040760 y 0x80040768). En esa rama D_80069672 se pone a cero despues de los
 * dos primeros almacenes, aunque el original lo almacena antes de la `xori` de la mascara (`sh zero` en
 * 0x80040738): el planificador lo adelanta, y escrito junto a la lectura de D_8006CFF2 el compilador elimina el
 * primer almacen a botones.
 *
 * El banco D_8006AA70 se lee siempre por su nombre; el puntero que el original mantiene en s1 (`0xc(s1)` y
 * `0x17(s1)`) lo crea el compilador. El byte 0xc es el que globales.h declara tambien como D_8006AA7C: aqui se
 * nombra solo como elemento del arreglo sin tamano. En la cola de la rama por defecto el original deja en el hueco
 * de retardo de las cuatro bifurcaciones del bloque de la prueba (0x800409EC, 0x80040A00, 0x80040A18 y
 * 0x80040A28) el `lui` de esa direccion: con el escalar (u8 de un byte, dentro del umbral -G8) el compilador emite
 * la lectura como una sola instruccion de macro, el `lui` lo crea el ensamblador y no puede ocupar un hueco; con el
 * arreglo sin tamano el `lui` es una instruccion propia. Con el escalar en la ultima prueba la cifra es 1100.
 *
 * En la rama de arriba del eje Y la resta de `eje_y` va despues del almacen a botones_a. El original conserva el
 * `andi 0xff` del byte antes de la suma (0x80040908) y la resta es la primera instruccion del bloque; mientras no
 * haya un almacen entre la lectura del byte y la suma, el combinador pliega el `andi` sobre el registro del byte
 * (`addiu` con el byte sin extender). Con el almacen delante el `andi` se conserva, y el planificador deja la resta
 * antes de los almacenes como el original. Con la resta primero la cifra es 650. En el eje X los almacenes a w3E y
 * botones_a ya quedan entre la lectura y la rama de la izquierda.
 *
 * El byte crudo de los dos ejes vive en una sola local de 8 bits (`eje_crudo`) y todas las ramas la usan por su
 * nombre: el original lee cada eje una vez (0x80040830 y 0x800408E4), compara una copia enmascarada (a2) y repite
 * `andi 0xff` sobre la lectura en las ramas de la izquierda y de arriba (0x80040880 y 0x80040908), mientras que las
 * ramas de la derecha y de abajo usan el registro del byte (v1) sin extender. Con una local de 8 bits compartida
 * el reparto de registros de los ejes coincide con el original (crudo v1, `centro` a1, copia enmascarada a2, umbral
 * a3 y `botones_c` t0) y el planificador deja la lectura del eje X la primera del bloque. Se supone, sin verificar,
 * que el `andi` de las ramas derecha y abajo lo elimina la limpieza posterior a la asignacion de registros al
 * quedar la copia en el mismo registro que el byte.
 *
 * Una sola variable (`bits`) guarda los botones de direccion en la rama de grabacion y en la de lectura de la BIOS:
 * el original usa el mismo registro (s1) en las dos (`lhu s1` en 0x80040668 y `move s1,s2` en 0x8004074C).
 *
 * El byte de vibracion se modifica con `&= 0x7F` y `|= 0x80`, sin variable intermedia: el original hace `lbu`,
 * `andi`/`ori` y un `sb` unico (0x80040724) al que salta la primera rama (`j` en 0x80040710).
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
 */
void func_8004048C(void)
{
    u16 prev;
    u16 mascara;
    u16 a;
    u16 b;
    u16 c;
    u32 id;
    s32 bits;
    s32 hi;
    s32 centro;
    u16* grab;
    s32 lo;
    u32 cf2;
    u32 cf3;
    u32 cfd;
    /* Lectura sin centrar de cada eje del mando, de 8 bits y compartida por los dos ejes: el original lee cada una
     * una sola vez (0x80040830 y 0x800408E4). */
    u8 eje_crudo;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[2];

    if (D_80069662 == 0 && (D_80069698 == 0 || (D_80069698->flags14 & 0x01000000) == 0)) {
        goto normal;
    }
    if (D_8006AA70[0xC] == 0) {
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
    D_800695EA = 0;
    if (D_8006AA70[0xC] == 0) {
        func_80040430(&D_800695A0, 0x40);
        func_80040430(&D_80069595, 0x80);
        func_80040430(&D_8006963C, 4);
    }
    prev = ESTADO_PRINCIPAL->mando.botones_c;
    ESTADO_PRINCIPAL->mando.botones_c = 0;
    ESTADO_PRINCIPAL->mando.botones_e = prev;
    ESTADO_PRINCIPAL->mando.botones_e = prev & D_800695EA;
    if (ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
        if (D_8006AA70[0x17] != 0 && D_8006AA70[0x17] != 4) {
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
        id = D_8006CFF1.valor & 0x7F;
        D_800695B0 = grab + 4;
        ESTADO_PRINCIPAL->mando.botones = c;
        /* La lectura de D_8006CFF2 va dentro de la condicion: sacarla antes del `if` la carga siempre y la cifra
         * sube mucho. */
        if ((id == 0x41 || id == 0x73) && ((cfd = D_8006CFF2.valor, ((cfd ^ 0xFF) << 8) & 0x800)) &&
            ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
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
    switch (D_8006CFF1.valor & 0x7F) {
    case 0x41:
    case 0x73:
        if ((D_8006CFF1.valor & 0x7F) == 0x41) {
            ESTADO_PRINCIPAL->r[BANCO_VIBRACION] &= 0x7F;
        } else {
            ESTADO_PRINCIPAL->r[BANCO_VIBRACION] |= 0x80;
        }
        cf2 = D_8006CFF2.valor;
        hi = (cf2 ^ 0xFF) << 8;
        bits = hi;
        cf3 = D_8006CFF3.valor;
        lo = cf3 ^ 0xFF;
        b = lo | hi;
        ESTADO_PRINCIPAL->mando.botones_c = lo;
        ESTADO_PRINCIPAL->mando.botones = lo;
        /* Va despues de los dos primeros almacenes aunque el original lo emite antes (0x80040738): ver la cabecera. */
        D_80069672 = 0;
        ESTADO_PRINCIPAL->mando.botones = b;
        if ((hi & 0xF000) != 0 || (D_8006CFF1.valor & 0x7F) == 0x41) {
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
        /* Cada eje se lee una sola vez (0x80040830 y 0x800408E4) en la misma local de 8 bits y las ramas la usan por su
           nombre: el `andi 0xff` de la izquierda y de arriba (0x80040880 y 0x80040908) sale por ser de 8 bits (en una
           de 32 el combinador da por redundante la conversion tras `lbu`). */
        eje_crudo = D_8006CFF6.valor;
        prev = mascara & ~ESTADO_PRINCIPAL->mando.botones_e;
        ESTADO_PRINCIPAL->mando.w3E = prev;
        ESTADO_PRINCIPAL->mando.botones_a = prev;
        if (eje_crudo < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x8000;
            ESTADO_PRINCIPAL->mando.eje_x = eje_crudo - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x8000;
        } else if (centro + D_8006952C < eje_crudo) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x2000;
            ESTADO_PRINCIPAL->mando.eje_x = eje_crudo - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x2000;
        } else {
            ESTADO_PRINCIPAL->mando.eje_x = 0;
        }
        eje_crudo = D_8006CFF7.valor;
        centro = ESTADO_PRINCIPAL->mando.centro_y;
        if (eje_crudo < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a | 0x1000;
            ESTADO_PRINCIPAL->mando.eje_y = centro - (eje_crudo + 1);
            ESTADO_PRINCIPAL->mando.w3E = ESTADO_PRINCIPAL->mando.w3E | 0x1000;
            ESTADO_PRINCIPAL->mando.botones_c = ESTADO_PRINCIPAL->mando.botones_c | 0x1000;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x1000;
        } else if (eje_crudo > centro + D_8006952C) {
            ESTADO_PRINCIPAL->mando.eje_y = centro - (eje_crudo + 1);
            ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a | 0x4000;
            ESTADO_PRINCIPAL->mando.w3E = ESTADO_PRINCIPAL->mando.w3E | 0x4000;
            ESTADO_PRINCIPAL->mando.botones_c = ESTADO_PRINCIPAL->mando.botones_c | 0x4000;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x4000;
        } else {
            ESTADO_PRINCIPAL->mando.eje_y = 0;
        }
        return;
    default:
        D_80069672 += 1;
        if (D_80069672 == 4) {
            if (D_8006AA70[0xC] == 0) {
                ESTADO_PRINCIPAL->mando.botones_a = 0x800;
            }
        } else if (D_80069672 >= 5) {
            /* El original carga D_8006D9A8 entera con lw; globales.h la declara u16[5] por el resto de usos. */
            /* El original emite antes el bloque de la prueba de D_8006AA70[0xC] (0x80040A2C) que el del rearme: la
               condicion va invertida. */
            if (D_8006AA70[0] != 0 || D_8006966A != 0 || (*(u32*)D_8006D9A8 & 0x301) != 1 || ESTADO_PRINCIPAL->r[BANCO_PAUSA] != 0) {
                if (D_8006AA70[0xC] == 0) {
                    D_80069672 = 3;
                }
            } else {
                D_80069672 = 5;
                ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a & 0xF7FF;
            }
        }
        return;
    }
}
