#include "common.h"
#include "globales.h"
#include "psyq/LIBCD.H"
#include "psyq/LIBSPU.H"

/*
 * Audio: musica y voces en streaming XA, efectos por SPU y comprobacion del disco.
 *
 * El archivo se compila con umbral de datos pequenos (-G8, config/opciones_compilacion.toml):
 * el original direcciona el estado de la pista con desplazamiento($gp) y los almacenes a
 * variables de la zona 0x80069xxx son simbolicos (lui $at). Las variables pequenas que usa solo
 * este archivo se definen aqui sin extern para que maspsx las reescriba a $gp.
 */

/* Estado de la pista XA en curso (zona de datos pequenos, $gp = 0x80069320). */
u32 D_80069440;
CdlLOC D_80069444;
s16 D_80069448;
u32 D_8006944C;
u32 D_80069450;
u32 D_80069454;
u8 D_80069458;

/* Atributos comunes del SPU: volumen maestro, volumen del CD y mezcla del CD. */
extern SpuCommonAttr D_8006AD08;
extern u8 D_80069674;

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
extern CdlLOC D_8005F8FC;
/* Parametro de CdlSetmode (modo 0xCA: velocidad doble, XA-ADPCM, sector completo, filtro). */
extern u8 D_800694D0;
extern void func_8003E034(s32 a0);
extern void func_8003E88C(void);
extern u16 D_8005E9B8[];
extern u16 D_8005EA38[];
extern CdlLOC D_8005F90C;
extern u8 D_8006AA87[];
extern u8 D_80069501;
extern s16 D_800694C8;
extern s16 D_800694CE;
extern u8 D_80069540;
extern u8 D_80069541;
extern u8 D_80069586;
extern u8 D_80069620;
extern void func_8003E068(void);
extern void func_8003E094(void);
extern void func_8003E16C(u8 a0);
extern void func_8003FC88(void);
extern void func_8003FD60(void);

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

/*
 * Definicion de un efecto de sonido: 128 entradas de 8 bytes en D_8006AEE0. func_8003EB88 las
 * registra al cargar el nivel; func_8003F06C busca por identificador y func_8003F528 lee los
 * campos de la entrada que tiene asociada cada ranura de voz.
 */
typedef struct Efecto {
    u16 id;
    u8 vol_a;
    u8 vol_b;
    u16 flags;
    u8 cuenta;
    u8 b7;
} Efecto;

/* Lista de pistas XA pendientes: 40 entradas de 3 bytes (func_8003EC3C las llena). */
typedef struct Pista {
    u8 zona;
    u8 fila;
    u8 pista;
} Pista;

/* Ranura de voz de efecto: 24 entradas de 0x14 bytes en D_8006B378. */
typedef struct Voz {
    u16 flags;
    s16 voz;
    void* objeto;
    Efecto* efecto;
    u16 vol;
    u8 id;
    u8 pad0F;
    u16 cuenta;
    u8 pad12[2];
} Voz;

extern Efecto D_8006AEE0[];
extern Pista D_8006AC58[];
extern Voz D_8006B378[];
extern s16 D_80069568;
extern s16 D_800695D8;
extern s32 func_8003F9C4(u8* a0, u32 a1);
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

extern Sonido D_80069F28[];
extern s8 D_8006B2E0[];
extern s8 D_80069DD0[];
extern s16 D_800694CA;
extern u8 D_800694F6;
extern PitchVoz D_8006D8C8[];
extern u32 D_8006951C;
extern u32* D_80069598;
extern u32* D_80069550;
extern u32 D_800695E4;
extern s16* D_800695AC;
extern u8* D_8006966C;
extern s16* D_800695FC;
extern u8* D_800694EC;
/* LIBSND.H necesita <sys/types.h>, que el SDK incluido no trae: se declara solo lo que se usa. */
extern void SsUtReverbOff(void);
extern void func_8004D860(s32 a0, s32 a1);
extern s32 func_8003FB54(s8 a0);
extern s32 func_8003FA2C(s32 a0, s32 a1);
extern s16 func_8003FDEC(s16 a0, s16 a1, s16 a2, u16 a3);
extern void func_8003FEEC(s16 a0, s16 a1, s16 a2, s16 a3, u16 a4);

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
    CdControlB(0xD, param, 0);
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

/* Pendiente: puntuacion 90 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003E16C(u8 track)
{
    s32 i;
    s32 n;
    s32 acc;
    s32 pos;
    CdlLOC* l;

    if (track >= 2) {
        acc = 0;
        n = (track + 14) / 8;
        for (i = 0; i <= n; i++) {
            D_80069450 = acc;
            acc += D_8005E968[i];
        }
        acc = D_8005E974[track] << 3;
        pos = CdPosToInt(&D_8005F8FC);
        D_80069450 = D_80069450 + pos;
        D_80069440 = D_80069450 + acc - 0x20;
        CdIntToPos(D_80069450, &D_80069444);
        CdReadyCallback(func_8003E680);
        D_800694D0 = 0xCA;
        CdControlB(0xE, &D_800694D0, 0);
        func_8003E034((track - 2) % 8);
        CdControlB(0x1B, (u8*)&D_80069444, 0);
    } else {
        func_8003E88C();
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003E16C);
#endif

/* Pendiente: puntuacion 130 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003E298(s32 a0)
{
    EstadoAudio* g;
    s32 i;
    s32 n;
    s32 acc;
    s32 off;
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
    g = (EstadoAudio*)0x80010000;
    acc = *(u16*)((u8*)D_8005EA38 + g->idioma * 2 + n * 16) << 3;
    pos = CdPosToInt(&D_8005F90C);
    D_80069450 = D_80069450 + pos;
    D_80069440 = D_80069450 + acc - 0x40;
    CdIntToPos(D_80069450, &D_80069444);
    CdReadyCallback(func_8003E680);
    D_800694D0 = 0xCA;
    CdControlB(0xE, &D_800694D0, 0);
    func_8003E034(g->idioma);
    CdControlF(0x15, (u8*)&D_80069444);
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

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003E3C0);

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003E680);

/* Pendiente: puntuacion 175 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003E88C(void)
{
    CdlLOC loc;
    u8 v;

    if (D_8006955E == 0) {
        do {
            VSync(0);
            CdControlB(9, 0, 0);
            CdControlB(1, 0, 0);
        } while (CdStatus() != 2);
        v = D_8006AA7C;
        if (v == 1) {
            D_8006955E = v;
            CdControlB(0x10, &D_800694D0, &D_80069540);
            loc.minute = D_80069540;
            loc.second = D_80069541;
            loc.sector = 0;
            D_80069454 = CdPosToInt(&loc);
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003E88C);
#endif

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
        D_800694D0 = 0xCA;
        CdControlB(0xE, &D_800694D0, &D_80069540);
        CdControlB(0x1B, (u8*)&loc, 0);
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
            CdControlB(1, &D_800694D0, &D_80069540);
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
    D_8006AEE0[D_80069568].vol_a = e->vol_a;
    D_8006AEE0[D_80069568].vol_b = e->vol_b;
    D_8006AEE0[D_80069568].flags = e->flags;
    D_8006AEE0[D_80069568].cuenta = e->cuenta;
    D_8006AEE0[D_80069568++].b7 = e->b7;
}

void func_8003EC3C(u8* e)
{
    if (D_800694CE == 0x28) {
        for (;;) {
        }
    }
    D_8006AC58[D_800694CE].zona = e[0];
    D_8006AC58[D_800694CE].fila = e[1];
    D_8006AC58[D_800694CE++].pista = e[2];
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

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003EDA8);

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003F06C);

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003F3F0);

INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003F528);

/* Pendiente: puntuacion 360 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003F900(void* a0)
{
    s32 i;
    u16 f;

    for (i = 0; i < 0x18; i++) {
        f = D_8006B378[i].flags;
        if ((f & 0x8000) && D_8006B378[i].objeto == a0 && (D_8006B378[i].efecto->flags & 0x10)) {
            if (f & 1) {
                D_8006B378[i].flags = 0;
            } else {
                D_8006B378[i].flags = 0x8002;
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003F900);
#endif

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

/* Pendiente: puntuacion 1705 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
s32 func_8003FA2C(s32 a0, s32 a1)
{
    Sonido* s;
    s32 v;

    s = &D_80069F28[a0];
    v = func_8003FB54(s->prioridad);
    if (v == -1) {
        return -1;
    }
    SpuSetVoiceVolume(v, s->vol_l, s->vol_r);
    SpuSetVoicePitch(v, s->pitch);
    if (a1 & 0x400) {
        SpuSetVoiceStartAddr(v, D_800695E4 + D_80069598[s->indice]);
    } else {
        SpuSetVoiceStartAddr(v, D_80069550[s->indice] + 0x1010);
    }
    SpuSetReverbVoice((D_80069F28[a0].flags & 4) ? 1 : 0, 1 << v);
    return v;
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FA2C);
#endif

/* Pendiente: puntuacion 1620 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
s32 func_8003FB54(s8 a0)
{
    s32 menor;
    s32 libre;
    s32 i;
    s32 p;
    s8 orig;

    orig = a0;
    menor = 0x19;
    libre = menor;
    for (i = 0; i < 0x18; i++) {
        if (D_8006B2E0[i] == 0) {
            libre = i;
            break;
        }
        p = D_80069DD0[i];
        if (p < a0) {
            menor = i;
            a0 = p;
        }
    }
    if (libre == 0x19) {
        if (menor == libre) {
            return -1;
        }
        D_80069DD0[menor] = orig;
        return menor;
    }
    D_80069DD0[libre] = orig;
    return libre;
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FB54);
#endif

/* Pendiente: puntuacion 25 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
u32 func_8003FC04(void)
{
    s32 i;
    u32 activas;
    u32 apagadas;

    SpuGetAllKeysStatus(D_8006B2E0);
    activas = 0;
    apagadas = 0;
    for (i = 0; i < 0x18; i++) {
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
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FC04);
#endif

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

/* Pendiente: puntuacion 225 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003FD60(void)
{
    s32 i;
    PitchVoz* p;

    i = 0;
    if (D_800694CA > 0) {
        p = D_8006D8C8;
        do {
            if (p->voz != -1) {
                SpuSetVoicePitch(p->voz, p->pitch);
            }
            i++;
            p++;
        } while (i < D_800694CA);
    }
    D_800694CA = 0;
    D_800694F6 = 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FD60);
#endif

/* Pendiente: puntuacion 1770 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
s16 func_8003FDEC(s16 a0, s16 a1, s16 a2, u16 a3)
{
    s16* idx;
    u8* base;
    u8* e;

    if (a3 & 0x400) {
        idx = D_800695FC;
        base = D_800694EC;
    } else {
        idx = D_800695AC;
        base = D_8006966C;
    }
    e = base + idx[a0] + (a1 << 4);
    D_80069F28[0].prioridad = e[0];
    D_80069F28[0].flags = e[1];
    D_80069F28[0].vol_l = *(s16*)(e + 2) * (a2 & 0xFF);
    D_80069F28[0].vol_r = *(s16*)(e + 2) * ((a2 >> 8) & 0xFF);
    D_80069F28[0].s6 = e[4];
    D_80069F28[0].pitch = *(u16*)(e + 8);
    D_80069F28[0].wA = *(u16*)(e + 0xA);
    D_80069F28[0].wC = *(u16*)(e + 0xC);
    D_80069F28[0].indice = *(s16*)(e + 0xE);
    return func_8003FA2C(0, a3);
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FDEC);
#endif

/* Pendiente: puntuacion 840 con la configuracion versionada (g = 8 del archivo). Por medir el motivo exacto. Variantes probadas: 0. */
#ifdef NON_MATCHING
void func_8003FEEC(s16 a0, s16 a1, s16 a2, s16 a3, u16 a4)
{
    s16* idx;
    u8* base;
    u8* e;
    s32 v;

    if (a4 & 0x400) {
        idx = D_800695FC;
        base = D_800694EC;
    } else {
        idx = D_800695AC;
        base = D_8006966C;
    }
    e = base + idx[a1] + (a2 << 4);
    v = *(s16*)(e + 2);
    SpuSetVoiceVolume(a0, v * (a3 & 0xFF), v * ((a3 >> 8) & 0xFF));
}
#else
INCLUDE_ASM("asm/nonmatchings/audio_xa_y_spu", func_8003FEEC);
#endif

INCLUDE_RODATA("asm/nonmatchings/audio_xa_y_spu", D_80067EF0);

INCLUDE_RODATA("asm/nonmatchings/audio_xa_y_spu", D_80067F08);
