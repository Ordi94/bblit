#include "common.h"
#include "globales.h"
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
 * Las constantes de 0x8001xxxx se direccionan por direccion absoluta (ver Mando): la
 * comparacion con el original difiere solo en la forma de la direccion (simbolo frente a
 * numero), los bytes son los mismos.
 */

/*
 * Estado del mando en RAM fija. Los programas del juego direccionan esta zona por direccion
 * absoluta (0x80010000), no por simbolo, por eso el compilador comparte un solo lui entre
 * todos sus campos. Mando empieza en 0x80010008 (func_80040158 recibe esa direccion) y los
 * campos sin nombre propio se llaman por su desplazamiento: el codigo solo revela el ancho
 * de cada acceso. Entre parentesis, la direccion absoluta.
 */
typedef struct Mando {
    u16 w00;
    u16 w02;                /* (0x8001000A) */
    u16 botones;            /* (0x8001000C) botones del cuadro */
    u16 w06;                /* (0x8001000E) */
    u16 w08;                /* (0x80010010) */
    u16 w0A;                /* (0x80010012) eje X del analogico */
    u16 w0C;                /* (0x80010014) eje Y del analogico */
    u8 pad0E[0x12 - 0x0E];
    u16 w12;                /* (0x8001001A) centro X */
    u8 pad14[0x18 - 0x14];
    u16 w18;                /* (0x80010020) centro Y */
    u16 w1A;                /* (0x80010022) */
    u16 w1C;                /* (0x80010024) */
    u16 direcciones[4];     /* (0x80010026) mascaras de las cuatro direcciones */
    u16 mapa[8];            /* (0x8001002E) mascara de salida por boton fisico */
    u16 w36;                /* (0x8001003E) */
    u8 pad38[0x47 - 0x38];
    u8 w47;                 /* (0x8001004F) reproduccion de demo activa */
    u8 pad48;
    u8 conf;                /* (0x80010051) indice de la tabla de configuracion */
    u8 pad4A[0x6E - 0x4A];
    u8 w6E;                 /* (0x80010076) */
    u8 pad6F[0xDF - 0x6F];
    u8 w_e7;                /* (0x800100E7) banderas (bits 7 y 0 habilitan la vibracion) */
} Mando;

typedef struct EstadoGlobal {
    u32 estado;
    u32 pad4;
    Mando mando;
} EstadoGlobal;

#define G ((EstadoGlobal*)0x80010000)

/* Entrada de 16 bytes de la tabla de configuraciones de botones (8 mascaras de 16 bits). */
typedef struct EntradaTabla {
    u16 v[8];
} EntradaTabla;
extern EntradaTabla D_8005EE38[];

/* Acceso a la zona 0x80069xxx con el ancho que usa el original. */
extern u8 D_8006957C;
extern u8 D_800695E0;
extern u8 D_80069658;
extern u8 D_8006965C;
extern u8 D_8006965D;
extern u8 D_8006CFF0[];
extern u8 D_8006D038[];

extern void func_8005A21C(s32 modo);

/* Estado auxiliar del mando (zona 0x80069xxx y bufer de la BIOS). */
extern u8 D_8006AA7C;
extern u16 D_800695EA;
extern s16 D_80069672;
extern s16 D_8006952C;
extern u8 D_8006CFF1;
extern u8 D_8006CFF2;
extern u8 D_8006CFF3;
extern u8 D_8006CFF6;
extern u8 D_8006CFF7;

/* Entidad en curso (D_80069698): solo se lee su palabra de banderas en +0x14. */
typedef struct EntidadActual {
    u8 pad0[0x14];
    u32 banderas;
} EntidadActual;
extern EntidadActual* D_80069698;

/*
 * Solo la usa el cuerpo de func_80040240 bajo NON_MATCHING; la declaracion no emite codigo ni datos,
 * asi que es inocua en la compilacion normal. Esta para que el intento compile con diff.
 * $gp = 0x80069320: PadSetActAlign recibe el bloque de $gp + 0x10. func_80040240 difiere del
 * original en una sola cosa: el original calcula $gp + 0x10 antes de cargar el argumento 0
 * (que ocupa el hueco de retardo de la llamada) y el compilador, con la variable de registro,
 * lo calcula despues.
 */

/* Registro absoluto del eje Y: lo escribe el original por direccion, sin base compartida. */
#define W14 (*(u16*)0x80010014)

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
    G->mando.w02 = 0;
    G->mando.w06 = 0;
    G->mando.botones = 0;
    G->mando.w08 = 0;
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

    G->mando.direcciones[0] = 0x8000;
    G->mando.direcciones[1] = 0x2000;
    G->mando.direcciones[2] = 0x1000;
    G->mando.direcciones[3] = 0x4000;
    t = &D_8005EE38[G->mando.conf];
    G->mando.mapa[0] = t->v[0];
    G->mando.mapa[1] = t->v[1];
    G->mando.mapa[2] = t->v[2];
    G->mando.mapa[3] = t->v[3];
    G->mando.mapa[4] = t->v[4];
    G->mando.mapa[5] = t->v[5];
    G->mando.mapa[6] = t->v[6];
    G->mando.mapa[7] = t->v[7];
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
        b = m->botones;
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
        m->botones = (b & 0xFF00) | r;
    }
}

#ifdef NON_MATCHING
/*
 * No coincide: puntuacion 240 (el archivo se compila con g = 8; 3210 con -G0).
 * Vibracion del mando: mientras el mando 0 anuncia el modo extendido (PadInfoMode 1 = 7 y
 * PadInfoMode 2 distinto de cero) descuenta los dos temporizadores de pulso (D_80069659 el
 * pequeno, D_8006965A el grande) y fija los motores D_8006965C/D_8006965D si el estado
 * global lo permite (bits 7 y 0 de 0x800100E7); si no, borra todo. Al reconectarse (estado
 * 1) o mientras falte la alineacion, reenvia la vibracion con PadSetAct y PadSetActAlign.
 * Puntuacion 240 con -G8: difiere solo el orden de las dos ultimas instrucciones antes de
 * PadSetActAlign (el original calcula $gp + 0x10 y deja el argumento 0 en el hueco de
 * retardo; el candidato al reves) y la forma simbolica de 0x800100E7. Probado sin efecto:
 * &base_gp[0x10], variable intermedia al final y al principio, conversion a u32.
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
                    if ((G->mando.w_e7 & 0x80) && (G->mando.w_e7 & 1)) {
                        D_8006965C = 1;
                    }
                } else {
                    D_8006965C = 0;
                }
                if (D_8006965A != 0) {
                    D_8006965A--;
                    if ((G->mando.w_e7 & 0x80) && (G->mando.w_e7 & 1)) {
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
        if (PadSetActAlign(0, base_gp + 0x10) != 0) {
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
    if (G->mando.botones & (s16)mascara) {
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
 * No coincide: puntuacion 7419 (el archivo se compila con g = 8; 10074 con -G0).
 * Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o
 * entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma
 * los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS
 * (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
 * Puntuacion 7419 con -G8 (switch con goto, la formulacion mas cercana): la estructura de
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

    if (D_80069662 == 0 && (D_80069698 == 0 || (D_80069698->banderas & 0x01000000) == 0)) {
        goto normal;
    }
    if (D_8006AA7C == 0) {
        G->mando.w36 = 0;
        G->mando.w08 = 0;
        G->mando.botones = 0;
        G->mando.w06 = 0;
        G->mando.w02 = 0;
        G->mando.w0C = 0;
        G->mando.w0A = 0;
        if (G->mando.w47 != 0) {
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
    prev = G->mando.botones;
    G->mando.botones = 0;
    G->mando.w06 = prev;
    G->mando.w06 = prev & D_800695EA;
    if (G->mando.w47 != 0) {
        if (D_8006AA70[0x17] != 0 && D_8006AA70[0x17] != 4) {
            G->mando.w08 = 0;
            G->mando.botones = 0;
            G->mando.w06 = 0;
            G->mando.w02 = 0;
            return;
        }
        grab = D_800695B0;
        a = grab[0];
        G->mando.w36 = a;
        G->mando.w02 = a;
        G->mando.w06 = grab[1];
        b = grab[2];
        G->mando.botones = b;
        c = grab[3];
        D_800695B0 = grab + 4;
        id = D_8006CFF1 & 0x7F;
        G->mando.w08 = c;
        if ((id == 0x41 || id == 0x73) && (((D_8006CFF2 ^ 0xFF) << 8) & 0x800) && G->mando.w47 != 0) {
            G->mando.w02 = a | 0x100;
            G->mando.botones = b | 0x100;
            G->mando.w08 = c | 0x100;
        }
        bits = G->mando.w02;
        G->mando.w0A = 0;
        G->mando.w0C = 0;
        if (bits & 0x8000) {
            G->mando.w0A = -0x80;
        } else if (bits & 0x2000) {
            G->mando.w0A = 0x7F;
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
        v = G->mando.w_e7 & 0x7F;
        goto aplicar;
    case 0x73:
        v = G->mando.w_e7 | 0x80;
    aplicar:
        G->mando.w_e7 = v;
        D_80069672 = 0;
        hi = (D_8006CFF2 ^ 0xFF) << 8;
        bits2 = hi;
        a = D_8006CFF3 ^ 0xFF;
        b = a | hi;
        G->mando.botones = a;
        G->mando.w08 = a;
        G->mando.w08 = b;
        if ((hi & 0xF000) != 0 || (D_8006CFF1 & 0x7F) == 0x41) {
            G->mando.botones = b;
            func_80040158(&G->mando);
            G->mando.w0A = 0;
            G->mando.w0C = 0;
            G->mando.w1A = 0;
            G->mando.w1C = 0;
            prev = G->mando.botones & ~G->mando.w06;
            G->mando.w36 = prev;
            G->mando.w02 = prev;
            if (hi & 0x8000) {
                G->mando.w0A = -0x80;
            } else if (hi & 0x2000) {
                G->mando.w0A = 0x7F;
            }
            if (bits2 & 0x1000) {
                W14 = 0x7F;
            } else if (bits2 & 0x4000) {
                W14 = -0x80;
            }
            return;
        }
        G->mando.botones = a | (hi & 0xFFF);
        func_80040158(&G->mando);
        centro = (s16)G->mando.w12;
        mascara = G->mando.botones;
        eje = D_8006CFF6 & 0xFF;
        prev = mascara & ~G->mando.w06;
        G->mando.w36 = prev;
        G->mando.w02 = prev;
        if (eje < centro - D_8006952C) {
            G->mando.w02 = prev | 0x8000;
            G->mando.w36 = prev | 0x8000;
            G->mando.botones = mascara | 0x8000;
            G->mando.w0A = (D_8006CFF6 & 0xFF) - centro;
            G->mando.w08 = G->mando.w08 | 0x8000;
        } else if (centro + D_8006952C < eje) {
            G->mando.w02 = prev | 0x2000;
            G->mando.w36 = prev | 0x2000;
            G->mando.botones = mascara | 0x2000;
            G->mando.w0A = D_8006CFF6 - centro;
            G->mando.w08 = G->mando.w08 | 0x2000;
        } else {
            G->mando.w0A = 0;
        }
        centro = (s16)G->mando.w18;
        eje = D_8006CFF7 & 0xFF;
        if (eje < centro - D_8006952C) {
            G->mando.w0C = centro - ((D_8006CFF7 & 0xFF) + 1);
            G->mando.w02 = G->mando.w02 | 0x1000;
            G->mando.w36 = G->mando.w36 | 0x1000;
            G->mando.botones = G->mando.botones | 0x1000;
            G->mando.w08 = G->mando.w08 | 0x1000;
        } else if (centro + D_8006952C < eje) {
            G->mando.w0C = centro - (D_8006CFF7 + 1);
            G->mando.w02 = G->mando.w02 | 0x4000;
            G->mando.w36 = G->mando.w36 | 0x4000;
            G->mando.botones = G->mando.botones | 0x4000;
            G->mando.w08 = G->mando.w08 | 0x4000;
        } else {
            G->mando.w0C = 0;
        }
        return;
    default:
        D_80069672 += 1;
        if (D_80069672 == 4) {
            if (D_8006AA70[0xC] == 0) {
                G->mando.w02 = 0x800;
            }
        } else if (D_80069672 >= 5) {
            /* El original carga D_8006D9A8 entera con lw; globales.h la declara u16[5] por el resto de usos. */
            if (D_8006AA70[0] == 0 && D_8006966A == 0 && (*(u32*)D_8006D9A8 & 0x301) == 1 && G->mando.w6E == 0) {
                D_80069672 = 5;
                G->mando.w02 = G->mando.w02 & 0xF7FF;
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
