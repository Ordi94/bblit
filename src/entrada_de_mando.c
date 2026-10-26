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

/*
 * Solo la usa el cuerpo de func_80040240 bajo NON_MATCHING; la declaracion no emite codigo ni datos,
 * asi que es inocua en la compilacion normal. Esta para que el intento compile con diff.
 * $gp = 0x80069320: PadSetActAlign recibe el bloque de $gp + 0x10. func_80040240 difiere del
 * original en una sola cosa: el original calcula $gp + 0x10 antes de cargar el argumento 0
 * (que ocupa el hueco de retardo de la llamada) y el compilador, con la variable de registro,
 * lo calcula despues.
 */

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
    PadInitDirect(D_8006CFF0, D_8006D038);
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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 130 con la configuracion versionada (g = 8 del archivo). El original calcula la
 * direccion del bloque de alineacion con `addiu a1,gp,0x10`; maspsx solo la reescribe a $gp desde la
 * version 2.80 de ASPSX (gp_allow_la) y la configuracion versionada fija 2.79, de modo que sale
 * `lui` + `addiu`. Con 2.80 la funcion coincide en bytes (puntuacion 25 por la forma simbolica de
 * 0x800100E7 y de D_80069330) y el ejecutable completo sigue verificando. Variantes: base_gp + 0x10,
 * variable intermedia al principio y al final, conversion a u32, definicion tentativa del dato pequeno.
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
#else
INCLUDE_ASM("asm/nonmatchings/entrada_de_mando", func_80040240);
#endif

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
 * Pendiente: puntuacion 7264 con la configuracion versionada (g = 8 del archivo). El marco de pila del original
 * es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de
 * (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Variantes probadas: 14 (switch con goto, if/else, copias).
 *
 * Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o
 * entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma
 * los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS
 * (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
 * Puntuacion 7264 con -G8 (switch con goto, la formulacion mas cercana): la estructura de
 * saltos y casi todo el cuerpo coinciden; difieren el marco de pila (el original reserva 8
 * bytes mas, 0x28), el reparto de registros de la rama de grabacion, el orden de
 * (D_8006CFF2 ^ 0xFF) << 8 (el original no fusiona el xor con el desplazamiento) y la copia
 * s1 = s2 del valor de los botones de direccion. Probadas: if/else en lugar de switch
 * (12794), orden de declaracion de las copias, copia con la expresion repetida.
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
    s32 bits2;
    s32 hi;
    s32 centro;
    s32 eje;

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
        D_800695B0 = grab + 4;
        id = D_8006CFF1 & 0x7F;
        ESTADO_PRINCIPAL->mando.botones = c;
        if ((id == 0x41 || id == 0x73) && (((D_8006CFF2 ^ 0xFF) << 8) & 0x800) && ESTADO_PRINCIPAL->r[BANCO_DEMO] != 0) {
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
        v = ESTADO_PRINCIPAL->r[BANCO_VIBRACION] & 0x7F;
        goto aplicar;
    case 0x73:
        v = ESTADO_PRINCIPAL->r[BANCO_VIBRACION] | 0x80;
    aplicar:
        ESTADO_PRINCIPAL->r[BANCO_VIBRACION] = v;
        D_80069672 = 0;
        hi = (D_8006CFF2 ^ 0xFF) << 8;
        bits2 = hi;
        a = D_8006CFF3 ^ 0xFF;
        b = a | hi;
        ESTADO_PRINCIPAL->mando.botones_c = a;
        ESTADO_PRINCIPAL->mando.botones = a;
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
            if (bits2 & 0x1000) {
                W14 = 0x7F;
            } else if (bits2 & 0x4000) {
                W14 = -0x80;
            }
            return;
        }
        ESTADO_PRINCIPAL->mando.botones_c = a | (hi & 0xFFF);
        func_80040158(&ESTADO_PRINCIPAL->mando);
        centro = ESTADO_PRINCIPAL->mando.centro_x;
        mascara = ESTADO_PRINCIPAL->mando.botones_c;
        eje = D_8006CFF6 & 0xFF;
        prev = mascara & ~ESTADO_PRINCIPAL->mando.botones_e;
        ESTADO_PRINCIPAL->mando.w3E = prev;
        ESTADO_PRINCIPAL->mando.botones_a = prev;
        if (eje < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x8000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x8000;
            ESTADO_PRINCIPAL->mando.eje_x = (D_8006CFF6 & 0xFF) - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x8000;
        } else if (centro + D_8006952C < eje) {
            ESTADO_PRINCIPAL->mando.botones_a = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.w3E = prev | 0x2000;
            ESTADO_PRINCIPAL->mando.botones_c = mascara | 0x2000;
            ESTADO_PRINCIPAL->mando.eje_x = D_8006CFF6 - centro;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x2000;
        } else {
            ESTADO_PRINCIPAL->mando.eje_x = 0;
        }
        centro = ESTADO_PRINCIPAL->mando.centro_y;
        eje = D_8006CFF7 & 0xFF;
        if (eje < centro - D_8006952C) {
            ESTADO_PRINCIPAL->mando.eje_y = centro - ((D_8006CFF7 & 0xFF) + 1);
            ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a | 0x1000;
            ESTADO_PRINCIPAL->mando.w3E = ESTADO_PRINCIPAL->mando.w3E | 0x1000;
            ESTADO_PRINCIPAL->mando.botones_c = ESTADO_PRINCIPAL->mando.botones_c | 0x1000;
            ESTADO_PRINCIPAL->mando.botones = ESTADO_PRINCIPAL->mando.botones | 0x1000;
        } else if (centro + D_8006952C < eje) {
            ESTADO_PRINCIPAL->mando.eje_y = centro - (D_8006CFF7 + 1);
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
            if (D_8006AA70[0] == 0 && D_8006966A == 0 && (*(u32*)D_8006D9A8 & 0x301) == 1 && ESTADO_PRINCIPAL->r[BANCO_PAUSA] == 0) {
                D_80069672 = 5;
                ESTADO_PRINCIPAL->mando.botones_a = ESTADO_PRINCIPAL->mando.botones_a & 0xF7FF;
            } else if (D_8006AA7C == 0) {
                D_80069672 = 3;
            }
        }
        return;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/entrada_de_mando", func_8004048C);
#endif
