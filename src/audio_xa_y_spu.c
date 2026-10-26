#include "common.h"
#include "globales.h"
#include "audio.h"
#include "psyq/LIBCD.H"
#include "psyq/LIBSPU.H"
#include "geometria.h"

/*
 * Audio: musica y voces en streaming XA, efectos por SPU y comprobacion del disco.
 *
 * El archivo se compila con umbral de datos pequenos (-G8, config/opciones_compilacion.toml):
 * el original direcciona el estado de la pista con desplazamiento($gp) y los almacenes a
 * variables de la zona 0x80069xxx son simbolicos (lui $at). Las variables pequenas que usa solo
 * este archivo se definen aqui sin extern para que maspsx las reescriba a $gp.
 */

/*
 * Lista de pistas XA por zona: 40 entradas de 3 bytes (func_8003EC3C las llena). pista_a es la pista
 * que se reproduce al entrar en la zona (func_8003E3C0 la guarda en D_80069501) y pista_b la
 * alternativa que se compara con la pista en curso (func_8003E680 reinicia con ella).
 */
typedef struct Pista {
    u8 zona;
    u8 pista_a;
    u8 pista_b;
} Pista;

/* Estado de la pista XA en curso (zona de datos pequenos, $gp = 0x80069320). */
s32 D_80069440;
CdlLOC D_80069444;
s16 D_80069448;
Pista* D_8006944C;
u32 D_80069450;
u32 D_80069454;
u8 D_80069458;

/* Atributos comunes del SPU: volumen maestro, volumen del CD y mezcla del CD. */
extern SpuCommonAttr D_8006AD08;

extern void func_8003E680(u8 a0, u8* a1);
/*
 * Volumen del CD que recibe CdMix (CdlATV, cuatro bytes). Se declaran como cuatro bytes sueltos y no
 * como CdlATV: el original nombra cada byte (lui at ; sb) y pasa solo la direccion del primero.
 */
extern u8 D_800695CC;
extern u8 D_800695CD;
extern u8 D_800695CE;
extern u8 D_800695CF;
/* Volumen de musica configurado por el jugador (estado principal). */
extern void func_8003DFE4(void);
/* Tablas de posiciones de las pistas XA (sectores) y direcciones de pista en el disco. */
extern u16 D_8005E968[];
extern u16 D_8005E974[];
extern CdlLOC D_8005F8FC[];

/* Modo de CdlSetmode para la musica XA: velocidad doble, ADPCM activo, filtro de canal y pausa automatica (0xCA). */
#define CD_MODO_XA (CdlModeSpeed | CdlModeRT | CdlModeSF | CdlModeAP)

extern void func_8003E034(s32 a0);
extern void func_8003E88C(void);
extern u16 D_8005E9B8[];
extern u16 D_8005EA38[];
extern CdlLOC D_8005F90C[];
extern u8 D_8006AA87[];
extern u8 D_80069501;
extern s16 D_800694CE;
extern u8 D_80069541;
extern u8 D_80069620;
extern void func_8003E068(void);
extern void func_8003E094(void);
extern void func_8003E16C(u8 a0);
extern void func_8003FC88(void);
extern u32 func_8003FC04(void);
extern void func_8003FD60(void);
/* Volumen maestro de los efectos en el estado principal (0x80010000 + 0xE5). */
extern u8 D_800100E5;
/* Banderas de audio del estado principal (0x80010000 + 0xE8): el bit 0 fuerza el mismo volumen en ambos canales. */
extern u8 D_800100E8;
extern s32 BugsRand(void);

/* Tabla de nombres de archivo del disco: el primero es \LEVEL5\MERLIN.BZZ;1 (rodata D_80067EF0). */
typedef struct Lista4 {
    char* nombre[4];
} Lista4;
extern Lista4 D_80067F08;

/*
 * Vista del estado principal (0x80010000) con los dos bytes que lee el audio: el idioma
 * activo en +0x50 y el volumen de la musica en +0xE6. Donde el original comparte un solo lui
 * entre ambos se accede por este puntero constante; donde carga cada uno con su propio lui se
 * usan los simbolos sueltos.
 */
typedef struct EstadoAudio {
    u8 pad00[0x50];
    u8 idioma;
    u8 pad51[0xE6 - 0x51];
    u8 volumen;
} EstadoAudio;

extern Efecto D_8006AEE0[];
extern Pista D_8006AC58[];
extern s16 D_80069568;
extern s16 D_800695D8;
extern s32 func_8003F9C4(u8* a0, u32 a1);
extern u32 func_8003EDA8(Objeto* o, Efecto* e);
extern void func_8003F984(void);

/* Parametros de reverberacion que recibe func_8003ECF8 (profundidad en +8). */
typedef struct ParamReverb {
    u32 mask;
    s32 mode;
    u16 depth;
} ParamReverb;

/* Sonido de la tabla D_80069F28 que se vuelca a una voz del SPU (func_8003FA2C). */
typedef struct Sonido {
    s8 prioridad;
    u8 flags;
    s16 vol_l;
    s16 vol_r;
    s16 s6;
    u16 pitch;
    u16 wA;
    u16 wC;
    s16 pad0E;
    s32 indice;
} Sonido;

/* Pitch de una voz guardado al silenciar el SPU (func_8003FC88) y repuesto por func_8003FD60. */
typedef struct PitchVoz {
    s16 voz;
    u16 pitch;
} PitchVoz;

/* Entrada de 16 bytes de las tablas de sonidos: volumen base en +2 (func_8003FDEC, func_8003FEEC). */
typedef struct ParamSonido {
    u8 prioridad;
    u8 flags;
    s16 vol;
    u8 pad04[12];
} ParamSonido;

extern Sonido D_80069F28[];
extern s8 D_8006B2E0[];
extern s8 D_80069DD0[];
extern s16 D_800694CA;
extern u8 D_800694F6;
extern PitchVoz D_8006D8C8[];
extern u32 D_8006951C;
extern u32 D_800695E4;
extern u8* D_8006966C;
/* LIBSND.H necesita <sys/types.h>, que el SDK incluido no trae: se declara solo lo que se usa. */
extern void SsUtReverbOff(void);
extern void func_8004D860(s32 a0, s32 a1);
extern s32 func_8003FB54(s8 a0);
extern s32 func_8003FA2C(s32 a0, s16 a1);
extern s16 func_8003FDEC(s16 a0, s16 a1, VolVoz a2, u16 a3);
extern void func_8003FEEC(s16 a0, s16 a1, s16 a2, VolVoz a3, u16 a4);

void func_8003DF84(void)
{
    D_8006AD08.mask = 0x2C3;
    D_8006AD08.mvol.left = 0x3FFF;
    D_8006AD08.mvol.right = 0x3FFF;
    D_8006AD08.cd.volume.left = 0x7FFF;
    D_8006AD08.cd.volume.right = 0x7FFF;
    D_8006AD08.cd.mix = 1;
    SpuSetCommonAttr(&D_8006AD08);
    CdReadyCallback(func_8003E680);
    D_80069674 = 0;
    D_80069448 = 0;
}

void func_8003DFE4(void)
{
    u8 v;

    v = D_80069674;
    D_800695CD = 0;
    D_800695CF = 0;
    D_800695CC = v;
    D_800695CE = v;
    CdMix((CdlATV*)&D_800695CC);
}

void func_8003E034(s32 a0)
{
    u8 param[2];

    param[1] = a0;
    param[0] = 1;
    CdControlB(CdlSetfilter, param, 0);
}

void func_8003E068(void)
{
    D_80069674 = 0;
    func_8003DFE4();
    D_80069448 = 1;
}

void func_8003E094(void)
{
    D_80069674 = D_800100E6;
    func_8003DFE4();
    D_80069448 = 2;
}

void func_8003E0C8(void)
{
    D_80069674 += 8;
    if (D_80069674 >= D_800100E6) {
        D_80069674 = D_800100E6;
        D_80069448 = 0x10;
    }
    func_8003DFE4();
}

void func_8003E120(void)
{
    D_80069674 -= 8;
    if ((s8)D_80069674 <= 0) {
        D_80069674 = 0;
        D_80069448 = 0x20;
    }
    func_8003DFE4();
}

void func_8003E16C(u8 track)
{
    s32 i;
    s32 n;
    s32 acc;
    s32 pos;

    if (track >= 2) {
        acc = 0;
        n = (track + 14) / 8;
        for (i = 0; i <= n; i++) {
            D_80069450 = acc;
            acc += D_8005E968[i];
        }
        acc = D_8005E974[track] << 3;
        pos = CdPosToInt(D_8005F8FC);
        D_80069450 = D_80069450 + pos;
        D_80069440 = D_80069450 + acc - 0x20;
        CdIntToPos(D_80069450, &D_80069444);
        CdReadyCallback(func_8003E680);
        D_800694D0 = CD_MODO_XA;
        CdControlB(CdlSetmode, &D_800694D0, 0);
        func_8003E034((track - 2) % 8);
        CdControlB(CdlReadS, (u8*)&D_80069444, 0);
    } else {
        func_8003E88C();
    }
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 70 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere solo el orden de los dos lui iniciales (el original emite la base de la tabla de posiciones antes que la del estado principal). */
void func_8003E298(s32 a0)
{
    EstadoAudio* g;
    s32 i;
    s32 n;
    s32 acc;
    s32 pos;
    u8 vol;

    acc = 0;
    i = 0;
    n = a0 - 2;
    if (n >= 0) {
        for (; i <= n; i++) {
            D_80069450 = acc;
            acc += D_8005E9B8[i];
        }
    }
    acc = *(u16*)((u8*)D_8005EA38 + ((EstadoAudio*)0x80010000)->idioma * 2 + n * 16) << 3;
    g = (EstadoAudio*)0x80010000;
    pos = CdPosToInt(D_8005F90C);
    D_80069450 = D_80069450 + pos;
    D_80069440 = D_80069450 + acc - 0x40;
    CdIntToPos(D_80069450, &D_80069444);
    CdReadyCallback(func_8003E680);
    D_800694D0 = CD_MODO_XA;
    CdControlB(CdlSetmode, &D_800694D0, 0);
    func_8003E034(g->idioma);
    CdControlF(CdlSeekL, (u8*)&D_80069444);
    D_800694C8 = -1;
    D_80069501 = 0;
    D_8006AA87[0] = 2;
    vol = g->volumen;
    g->volumen = 0x50;
    D_80069594 = vol;
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003E298);
#endif

void func_8003E3C0(void)
{
    u16 f;
    s16 i;
    Pista* p;
    Pista* t;
    Objeto* o;
    s16 zona;
    u8 modo;
    u8 a;
    u8 b;

    f = D_80069448;
    if (f & 4) {
        func_8003E068();
    } else if (f & 8) {
        func_8003E094();
    } else if (f & 1) {
        func_8003E0C8();
    } else if (f & 2) {
        func_8003E120();
    }
    if (D_80069448 & 0x30) {
        D_80069448 = 0;
    }
    modo = D_8006AA70[0x17];
    if (modo != 0) {
        if (modo == 1) {
        } else if (modo == 2) {
            CdControlB(CdlNop, &D_800694D0, &D_80069540);
            if (D_80069540 & 2) {
                CdControl(CdlReadS, (u8*)&D_80069444, 0);
                D_8006AA70[0x17] = 4;
            }
        } else if (modo == 8) {
            if (D_80069448 == 0) {
                func_8003E298(D_80069586);
                func_8003E068();
            }
        }
    } else {
        for (i = 0; i < D_800694CE; i++) {
            if (D_8006AC58[i].zona == (s16)D_80069698->w26) {
                break;
            }
        }
        if (i != D_800694CE) {
            o = D_80069698;
            zona = o->w26;
            if (D_800694C8 != (s16)o->w26) {
                t = D_8006AC58;
                p = t + i;
                a = p->pista_a;
                b = p->pista_b;
                if (D_80069501 != (s8)p->pista_a || D_80069501 != (s8)b) {
                    if (D_80069674 == 0) {
                        D_80069501 = a;
                        D_800694C8 = zona;
                        D_8006944C = p;
                        func_8003E16C(a);
                        func_8003E068();
                    } else if (o->flags14 & 0x1000000) {
                        D_80069674 = 0;
                    } else if (D_80069674 == D_800100E6) {
                        func_8003E094();
                    }
                } else {
                    D_800694C8 = zona;
                }
            }
        } else {
            D_80069501 = 0;
            func_8003E16C(0);
        }
    }
}

void func_8003E680(u8 intr, u8* resultado)
{
    CdlLOC loc;
    s32 pos;
    s32 i;

    if (intr == 1) {
        CdControlB(CdlGetlocL, 0, resultado);
        loc.minute = resultado[0];
        loc.second = resultado[1];
        loc.sector = 0;
        pos = CdPosToInt(&loc);
        if (D_8006AA70[0x17] == 4 && pos >= D_80069440) {
            D_80069586 = 0;
            D_80069674 = 0;
            func_8003DFE4();
            D_800695DC = 1;
            D_8006AA70[0x17] = 0;
            D_800100E6 = D_80069594;
        }
        if (D_8006AA87[0] == 0) {
            D_80069586 = 0;
            if (D_800695DC != 0) {
                D_800695DC = 0;
                if (pos >= D_80069440) {
                    for (i = 0; i < D_800694CE; i++) {
                        if (D_8006AC58[i].zona == (s16)D_80069698->w26) {
                            break;
                        }
                    }
                    if (i != D_800694CE) {
                        D_80069501 = D_8006AC58[i].pista_b;
                        func_8003E16C(D_80069501);
                        func_8003E068();
                    } else {
                        D_80069501 = 0;
                        func_8003E16C(0);
                    }
                }
            }
        }
    } else if (intr == 5) {
        CdControlB(CdlNop, &D_800694D0, &D_80069540);
        if (D_80069540 & 0x10) {
            D_80069620 = 1;
            func_8003FC88();
        }
    }
}

void func_8003E88C(void)
{
    CdlLOC loc;
    u8 v;

    if (D_8006955E == 0) {
        do {
            VSync(0);
            CdControlB(CdlPause, 0, 0);
            CdControlB(CdlNop, 0, 0);
        } while (CdStatus() != 2);
        v = D_8006AA70[0xC];
        if (v == 1) {
            D_8006955E = v;
            CdControlB(CdlGetlocL, &D_800694D0, &D_80069540);
            loc.minute = D_80069540;
            loc.second = D_80069541;
            loc.sector = 0;
            D_80069454 = CdPosToInt(&loc);
        }
    }
}

void func_8003E948(void)
{
    CdlLOC loc;

    if (D_8006955E == 1) {
        if (D_80069448 == 0) {
            D_80069594 = D_800100E6;
            D_80069674 = D_800100E6;
            func_8003DFE4();
        }
        CdIntToPos(D_80069454, &loc);
        D_800694D0 = CD_MODO_XA;
        CdControlB(CdlSetmode, &D_800694D0, &D_80069540);
        CdControlB(CdlReadS, (u8*)&loc, 0);
        D_8006955E = 0;
    }
}

void func_8003E9E8(void)
{
    Lista4 files;
    CdlFILE file;

    files = D_80067F08;
    if (D_80069620 != 0) {
        do {
            VSync(0);
            CdControlB(CdlNop, &D_800694D0, &D_80069540);
            if ((D_80069540 & 0x10) == 0) {
                CdDiskReady(0);
                if (CdGetDiskType() == 2) {
                    if (CdSearchFile(&file, files.nombre[0]) != 0) {
                        D_80069620 = 0;
                        if (D_8006AA70[0xC] == 0) {
                            func_8003FD60();
                            func_8003E16C(D_80069501);
                        }
                    }
                }
            }
        } while (D_80069620 != 0);
    }
}

void func_8003EAEC(void)
{
    u32 i;
    u8* p;

    D_80069568 = 0;
    p = (u8*)D_8006AEE0;
    for (i = 0; i < 0x400; i++) {
        *p = 0;
        p++;
    }
    for (i = 0; (s32)i < 0x18; i++) {
        D_8006B378[i].flags = 0;
        D_8006B378[i].efecto = 0;
        D_8006B378[i].objeto = 0;
        D_8006B378[i].id = 0;
    }
}

void func_8003EB48(void)
{
    u32 i;
    u8* p;

    p = (u8*)D_8006AC58;
    D_800694CE = 0;
    D_80069501 = 0;
    for (i = 0; i < 0x78; i++) {
        *p = 0;
        p++;
    }
}

void func_8003EB80(void)
{
}

void func_8003EB88(Efecto* e)
{
    if (D_80069568 == 0x80) {
        for (;;) {
        }
    }
    D_8006AEE0[D_80069568].id = e->id;
    D_8006AEE0[D_80069568].grupo = e->grupo;
    D_8006AEE0[D_80069568].fila = e->fila;
    D_8006AEE0[D_80069568].flags = e->flags;
    D_8006AEE0[D_80069568].cuenta = e->cuenta;
    D_8006AEE0[D_80069568++].azar = e->azar;
}

void func_8003EC3C(u8* e)
{
    if (D_800694CE == 0x28) {
        for (;;) {
        }
    }
    D_8006AC58[D_800694CE].zona = e[0];
    D_8006AC58[D_800694CE].pista_a = e[1];
    D_8006AC58[D_800694CE++].pista_b = e[2];
}

void func_8003ECD4(u8* a0, u32 a1)
{
    D_800695D8 = func_8003F9C4(a0, a1);
}

void func_8003ECF8(ParamReverb* p)
{
    SpuReverbAttr attr;

    attr.mask = p->mask;
    attr.mode = p->mode;
    attr.depth.left = p->depth;
    attr.depth.right = p->depth;
    SpuSetReverbModeParam(&attr);
    SpuSetReverbDepth(&attr);
    SpuReserveReverbWorkArea(1);
    SpuSetReverbVoice(1, 0xFFFFFF);
    SpuSetReverb(1);
}

void func_8003ED6C(void)
{
    func_8003F984();
    D_800695D8 = -1;
}

void func_8003ED94(void)
{
    D_800695D8 = -1;
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 85 con la configuracion versionada (g = 8 del archivo). Las instrucciones y los registros coinciden (el resultado, una union de dos bytes, queda en s2); difiere solo la posicion de un sll (x << 8) respecto al mflo en la rama de angulo positivo. */
u32 func_8003EDA8(Objeto* o, Efecto* e)
{
    s32 d[3];
    s32 w[3];
    s32 pos[3];
    AcumuladorNodos acc;
    VolVoz r;
    s32 x;
    s32 y;
    s32 t;

    if (D_80069458 == 0) {
        return 0;
    }
    if (o == D_80069698 || o == 0) {
        return D_80069458 | (D_80069458 << 8);
    }
    if ((e->flags & 0x100) && o->u78.p != 0 && *(u32*)o->u78.p != 0) {
        acc.nodo = (GsCOORDINATE2*)(*(u32*)o->u78.p + 0x1C);
        func_8001CE64(&acc);
        GEO_CARGAR_W(&acc.acc);
        GEO_GUARDAR_W_T1(pos);
    } else {
        GEO_CARGAR_W(&o->param.trans);
        GEO_GUARDAR_W_T1(pos);
    }
    d[0] = pos[0] - D_8006D928.x;
    d[1] = pos[1] - D_8006D928.y;
    d[2] = pos[2] - D_8006D928.z;
    x = func_80044940(d);
    if (x < 0x1000) {
        d[0] = pos[0] - D_8006D928.vpx;
        d[2] = pos[2] - D_8006D928.vpz;
        w[0] = D_8006D928.x - D_8006D928.vpx;
        w[2] = D_8006D928.z - D_8006D928.vpz;
        y = ratan2(d[0], d[2]);
        y -= ratan2(w[0], w[2]);
        if (y > 0x800) {
            y -= 0x1000;
        }
        if (y < -0x800) {
            y += 0x1000;
        }
        x = 0x7F - ((x << 7) >> 12);
        x = (x * D_80069458) >> 7;
        if (y >= 0) {
            t = x * y;
            if (y > 0x400) {
                y = 0x800 - y;
                t = x * y;
            }
            r.c.der = x;
            y = t >> 10;
            r.c.izq = x - y;
        } else {
            if (y < -0x400) {
                y = -0x800 - y;
            }
            t = x * y;
            y = t >> 10;
            r.c.der = x + y;
            r.c.izq = x;
        }
    } else {
        r.w = 0;
    }
    if (e->flags & 0x200) {
        x = r.c.izq + e->cuenta;
        if (D_80069458 < x) {
            x = D_80069458;
        }
        r.c.izq = x;
        x = r.c.der + e->cuenta;
        if (D_80069458 < x) {
            x = D_80069458;
        }
        r.c.der = x;
    }
    return r.w;
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003EDA8);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 2792 con la configuracion versionada (g = 8 del archivo). El flujo coincide; el original recorre la tabla de efectos con dos punteros que avanzan juntos (entrada y entrada + 4) y aqui la reduccion de fuerza del bucle exterior reparte un tercero para los accesos de +2 y +3, lo que desplaza los registros s. */
void func_8003F06C(void* objeto, s16 id, u16 modo, u8 clave)
{
    Voz* v;
    Efecto* e;
    u8* pf;
    s16 i;
    s16 j;
    u16 libre;

    e = D_8006AEE0;
    D_80069458 = D_800100E5;
    if (modo & 1) {
        v = D_8006B378;
        pf = (u8*)&e->flags;
        for (i = 0; i < 0x18; i++, v++) {
            libre = v->flags & 0x8000;
            if (libre == 0) {
                for (j = 0; j < D_80069568; j++) {
                    if (e->id == id) {
                        break;
                    }
                    e++;
                    pf += 8;
                }
                if (j != D_80069568 && (!(*(u16*)pf & 0x80) || (BugsRand() >> 7) >= pf[3])) {
                    if (*(u16*)pf & 2) {
                        if (D_80069458 < pf[2]) {
                            v->vol.w = D_80069458 + (D_80069458 << 8);
                        } else {
                            v->vol.w = pf[2] + (pf[2] << 8);
                        }
                    } else {
                        v->vol.w = func_8003EDA8(objeto, e);
                    }
                    if (v->vol.w != 0 || (*(u16*)pf & 0x820) == 0x20) {
                        if ((*(u16*)pf & 1) || (D_800100E8 & 1)) {
                            if (v->vol.c.der < v->vol.c.izq) {
                                v->vol.c.der = v->vol.c.izq;
                            } else {
                                v->vol.c.izq = v->vol.c.der;
                            }
                        }
                        v->objeto = objeto;
                        v->efecto = e;
                        v->flags = modo | 0x8000;
                        v->id = clave;
                    }
                }
                return;
            }
        }
    } else if (modo & 2) {
        v = D_8006B378;
        for (i = 0; i < 0x18; i++, v++) {
            if ((*(u32*)&v->flags & 0x8002) == 0x8000 && v->efecto->id == id && v->objeto == objeto) {
                if (!(v->flags & 1)) {
                    v->id = clave;
                    v->flags = 0x8002;
                } else {
                    v->flags = 0;
                }
                break;
            }
        }
        if (i == 0x18) {
            v = D_8006B378;
            for (i = 0; i < 0x18; i++, v++) {
                if ((*(u32*)&v->flags & 0x8002) == 0x8000 && v->efecto->id == id) {
                    if (!(v->flags & 1)) {
                        v->id = clave;
                        v->flags = 0x8002;
                        return;
                    }
                    v->flags = 0;
                }
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003F06C);
#endif

void func_8003F3F0(void)
{
    s32 i;
    Voz* v;
    u16 f;
    Efecto* e;

    D_80069458 = D_800100E5;
    v = D_8006B378;
    for (i = 0; i < 0x18; i++) {
        f = v->flags;
        if (f & 0x8000) {
            e = v->efecto;
            if (f & 4) {
                if (e->flags & 2) {
                    if ((s8)D_80069628 == 1) {
                        if (e->cuenta > D_80069458) {
                            v->vol.w = (D_80069458 << 8) + D_80069458;
                        } else {
                            v->vol.w = (e->cuenta << 8) + e->cuenta;
                        }
                    }
                } else if ((e->flags & 0x20) || (s8)D_80069628 == 1) {
                    v->vol.w = func_8003EDA8(v->objeto, e);
                }
            }
        }
        v++;
    }
    if ((s8)D_80069628 == 1) {
        D_80069628 = 2;
    }
}

void func_8003F528(s16 id)
{
    Voz* v;
    Efecto* e;
    s32 i;
    s32 activas;
    u32 encender;
    u32 apagar;
    u32 m;
    u32 m3;
    s32 vz;
    u16 f;
    u16 fe;
    u8 g;

    apagar = 0;
    activas = func_8003FC04();
    g = D_800100E5;
    D_80069458 = g;
    encender = 0;
    if (g != 0) {
        D_80069458 = g - 1;
    }
    v = D_8006B378;
    for (i = 0; i < 0x18; v++, i++) {
        f = v->flags;
        if (!(f & 0x8000)) {
            continue;
        }
        e = v->efecto;
        if (f & 1) {
            if (v->id != id) {
                continue;
            }
            f &= 0xFFFE;
            v->flags = f;
            if (v->objeto == 0) {
                goto liberar;
            }
            if (e->id != 0xD || !(D_80069698->flags14 & 0x1000000)) {
                v->flags = f | 4;
                v->cuenta = 0;
                v->voz = func_8003FDEC(e->grupo, e->fila, v->vol, e->flags);
            }
            if (v->voz < 0) {
                goto liberar;
            }
            encender |= 1 << v->voz;
            D_8006B2E0[v->voz] = 1;
        } else if (f & 2) {
            if (v->id != id) {
                continue;
            }
            v->flags = 0;
            m = 1 << v->voz;
            if (activas & m) {
                apagar |= m;
            }
        } else if (f & 4) {
            v->cuenta++;
            m3 = 1 << v->voz;
            if (!(activas & m3)) {
                goto liberar;
            }
            if (v->objeto == 0) {
                goto liberar;
            }
            fe = e->flags;
            if ((fe & 2) && (s8)D_80069628 != 2) {
                continue;
            }
            if ((fe & 4) && (s16)v->cuenta == e->cuenta) {
                v->cuenta = 0;
                v->voz = func_8003FDEC(e->grupo, e->fila, v->vol, e->flags);
                if (v->voz < 0) {
                    v->flags = 0;
                } else {
                    encender |= 1 << v->voz;
                    D_8006B2E0[v->voz] = 1;
                }
            } else if ((e->flags & 8) && (s16)((s16)v->cuenta / 30) == e->cuenta) {
                v->cuenta = 0;
                v->voz = func_8003FDEC(e->grupo, e->fila, v->vol, e->flags);
                if (v->voz < 0) {
                    v->flags = 0;
                } else {
                    encender |= 1 << v->voz;
                    D_8006B2E0[v->voz] = 1;
                }
            }
            fe = e->flags;
            if (!(fe & 0x20) && (s8)D_80069628 != 2) {
                continue;
            }
            if ((fe & 1) || (D_800100E8 & 1)) {
                if (v->vol.c.izq > v->vol.c.der) {
                    v->vol.c.der = v->vol.c.izq;
                } else {
                    v->vol.c.izq = v->vol.c.der;
                }
            }
            func_8003FEEC(v->voz, e->grupo, e->fila, v->vol, e->flags);
        }
        continue;
    liberar:
        v->flags = 0;
    }
    if (encender != 0) {
        SpuSetKey(1, encender);
    }
    if (apagar != 0) {
        SpuSetKey(0, apagar);
    }
    if ((s8)D_80069628 == 2) {
        D_80069628 = 0;
    }
}

void func_8003F900(void* a0)
{
    s32 i;
    u16 f;
    Voz* v;

    v = D_8006B378;
    for (i = 0; i < 0x18; i++) {
        f = v->flags;
        if ((f & 0x8000) && v->objeto == a0 && (v->efecto->flags & 0x10)) {
            if (f & 1) {
                v->flags = 0;
            } else {
                v->flags = 0x8002;
            }
        }
        v++;
    }
}

void func_8003F984(void)
{
    SsUtReverbOff();
    SpuSetCommonMasterVolume(0x3FFF, 0x3FFF);
    SpuSetCommonCDMix(1);
    func_8004D860(0x3FFF, 0x3FFF);
}

s32 func_8003F9C4(u8* a0, u32 a1)
{
    s32 ret;

    ret = 0;
    SpuSetTransferStartAddr(D_8006951C);
    if (SpuRead(a0, a1) != a1) {
        ret = -1;
    }
    SpuIsTransferCompleted(1);
    return ret;
}

s32 func_8003FA2C(s32 a0, s16 a1)
{
    Sonido* s;
    Sonido* t;
    s32 v;

    t = D_80069F28;
    s = &t[a0];
    v = func_8003FB54(s->prioridad);
    if (v == -1) {
        return -1;
    }
    SpuSetVoiceVolume(v, s->vol_l, s->vol_r);
    SpuSetVoicePitch(v, s->pitch);
    if (a1 & 0x400) {
        SpuSetVoiceStartAddr(v, D_800695E4 + D_80069598[s->indice]);
    } else {
        /* D_80069550 es base de bytes en globales.h; aqui se lee como tabla de palabras. */
        SpuSetVoiceStartAddr(v, ((u32*)D_80069550)[s->indice] + 0x1010);
    }
    if (D_80069F28[a0].flags & 4) {
        SpuSetReverbVoice(1, 1 << v);
    } else {
        SpuSetReverbVoice(0, 1 << v);
    }
    return v;
}

s32 func_8003FB54(s8 a0)
{
    s32 menor;
    s32 libre;
    s32 i;
    s32 p;
    s32 minimo;

    menor = 0x19;
    minimo = a0;
    libre = menor;
    for (i = 0; i < 0x18; i++) {
        if (D_8006B2E0[i] == 0) {
            libre = i;
            break;
        }
        p = D_80069DD0[i];
        if (p < minimo) {
            menor = i;
            minimo = p;
        }
    }
    if (libre != 0x19) {
        D_80069DD0[libre] = a0;
        return libre;
    }
    if (menor != libre) {
        D_80069DD0[menor] = a0;
        return menor;
    }
    return -1;
}

u32 func_8003FC04(void)
{
    s32 i;
    u32 activas;
    u32 apagadas;

    SpuGetAllKeysStatus(D_8006B2E0);
    i = 0;
    activas = 0;
    apagadas = 0;
    for (; i < 0x18; i++) {
        if (D_8006B2E0[i] == 1) {
            activas |= 1 << i;
        } else {
            apagadas |= 1 << i;
            D_8006B2E0[i] = 0;
        }
    }
    SpuSetKey(0, apagadas);
    return activas;
}

void func_8003FC88(void)
{
    s32 i;

    D_800694CA = 0;
    func_8003FC04();
    for (i = 0; i < 0x18; i++) {
        if (D_8006B2E0[i] == 1) {
            D_8006D8C8[D_800694CA].voz = i;
            SpuGetVoicePitch(i, &D_8006D8C8[D_800694CA].pitch);
            SpuSetVoicePitch(i, 0);
            D_800694CA++;
        }
    }
    VSync(0);
    D_800694F6 = 1;
}

void func_8003FD60(void)
{
    s32 i;

    for (i = 0; i < D_800694CA; i++) {
        if (D_8006D8C8[i].voz != -1) {
            SpuSetVoicePitch(D_8006D8C8[i].voz, D_8006D8C8[i].pitch);
        }
    }
    D_800694CA = 0;
    D_800694F6 = 0;
}

s16 func_8003FDEC(s16 a0, s16 a1, VolVoz a2, u16 a3)
{
    s16* p;
    u8* base;

    if (a3 & 0x400) {
        p = D_800695FC + a0;
        base = D_800694EC;
    } else {
        p = D_800695AC + a0;
        base = D_8006966C;
    }
    base += *p;
    base += a1 << 4;
    D_80069F28[0].prioridad = base[0];
    D_80069F28[0].flags = base[1];
    D_80069F28[0].vol_l = *(s16*)(base + 2) * a2.c.izq;
    D_80069F28[0].vol_r = *(s16*)(base + 2) * a2.c.der;
    D_80069F28[0].s6 = base[4];
    D_80069F28[0].pitch = *(u16*)(base + 8);
    D_80069F28[0].wA = *(u16*)(base + 0xA);
    D_80069F28[0].wC = *(u16*)(base + 0xC);
    D_80069F28[0].indice = *(s16*)(base + 0xE);
    return func_8003FA2C(0, a3);
}

void func_8003FEEC(s16 a0, s16 a1, s16 a2, VolVoz a3, u16 a4)
{
    s16* p;
    u8* base;
    s32 v;

    if (a4 & 0x400) {
        p = D_800695FC + a1;
        base = D_800694EC;
    } else {
        p = D_800695AC + a1;
        base = D_8006966C;
    }
    base += *p;
    base += a2 << 4;
    v = ((ParamSonido*)base)->vol;
    SpuSetVoiceVolume(a0, v * a3.c.izq, v * a3.c.der);
}

INCLUDE_RODATA("asm/nonmatchings/audio_xa_y_spu", D_80067EF0);

INCLUDE_RODATA("asm/nonmatchings/audio_xa_y_spu", D_80067F08);
