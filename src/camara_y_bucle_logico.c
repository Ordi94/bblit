#include "common.h"
#include "globales.h"
#include "geometria.h"
#include "gte.h"

/*
 * Vista del estado de la camara con los campos que EstadoCamara (globales.h) todavia no declara:
 * las copias del punto de vista y de la mira que los eventos de camara reparten (0x68, 0x94, 0xB4
 * y 0xA4) y los parametros de la sacudida (0x86 a 0x90). Es la misma memoria que D_8006D928.
 */
typedef struct VistaCamara {
    s32 vpx;
    s32 vpy;
    s32 vpz;
    s32 mx;
    s32 my;
    s32 mz;
    u8 pad18[0x68 - 0x18];
    s32 vp68[3];
    u8 pad74[0x80 - 0x74];
    u16 flags80;
    u8 pad82[0x86 - 0x82];
    s16 s86;
    s16 s88;
    s16 s8A;
    s16 s8C;
    s16 s8E;
    s32 i90;
    s32 vp94[3];
    u8 padA0[0xA4 - 0xA0];
    s32 m4[3];
    u8 padB0[0xB4 - 0xB0];
    s32 vpB4[3];
} VistaCamara;

#define CAMARA ((VistaCamara*)&D_8006D928)

typedef struct Vec3 {
    s32 x;
    s32 y;
    s32 z;
} Vec3;

/* Campos de los objetos de escena que Objeto (globales.h) no declara. */
#define OBJ_U32(o, off) (*(u32*)((u8*)(o) + (off)))
#define OBJ_LISTA(o) ((void*)((u8*)(o) + 0x78))

/* Area de trabajo de la sonda de camara (func_800330AC): direccion, matriz, resultado y consulta de colision. */
typedef struct SondaCamara {
    SVECTOR rot;
    SVECTOR dir;
    MATRIX m;
    VECTOR res;
    VECTOR pos;
    u8 pad50[2];
    u16 f52;
    u8 pad54[6];
    s16 s5A;
    u8 pad5C[0x68 - 0x5C];
    s32 i68;
} SondaCamara;

/* Angulos de un objeto: la sonda solo lee y reescribe el giro en Y (+2). */
typedef struct Giro {
    u16 x;
    u16 y;
    u16 z;
} Giro;

/* Secuencia de teclas de los trucos: caso a ejecutar, paso actual y hasta diez teclas (0 termina). */
typedef struct Secuencia {
    s16 caso;
    s16 paso;
    s16 teclas[10];
} Secuencia;

typedef struct EstadoPrincipal {
    s32 modo;
    u8 pad04[0x41 - 0x04];
    u8 f41;
    u8 pad42;
    u8 f43;
    u8 pad44;
    u8 f45;
    u8 pad46;
    u8 f47;
    u8 f48;
    u8 pad49[0x64 - 0x49];
    u8 f64;
    u8 pad65[0x13C - 0x65];
    u8 f13C;
} EstadoPrincipal;

extern Secuencia D_8005E768[];
#define PRINCIPAL ((EstadoPrincipal*)0x80010000)

extern u16 D_8005E6F8[];
extern s16 D_80069D90[];
extern void func_80019474(void* pos, void* res, void* f50, void* i68);
extern long SquareRoot0(long x);
extern s32 rand(void);
extern void ClearList(void* lista);
extern Objeto* RemoveListNode(Objeto* lista, Objeto* nodo);
extern void func_8001CC68(void* a0);
extern void func_8001CF50(void* a0);
extern void func_8001CFCC(void* a0);
extern void func_8003F900(Objeto* a0);
extern s32 D_80069560;
extern s32 D_80069618;
extern s32 D_8006961C;
extern s32 D_80069624;
extern u8 D_80010076;
extern Vec3 D_80069DC0;

/* Variables de datos pequenos: el original las direcciona con desplazamiento($gp). */
u16 D_800693F4;
u16 D_800693F6;
u16 D_800693F8;
s32 D_800693F0;
u16 D_8006940C;
u16 D_80069414;
u16 D_80069416;
s16 D_80069424;


/* Envoltorio de rand() del SDK: la logica del juego pide aleatorios por aqui. */
s32 BugsRand(void)
{
    return rand();
}

/* Reinicia la camara y la sacudida al entrar en una escena. */
void func_80032894(void)
{
    Vec3 vp;
    Vec3 mira;

    GEO_CARGAR_W(&CAMARA->vpx);
    GEO_GUARDAR_W_T1(&vp);
    GEO_CARGAR_W(&CAMARA->mx);
    GEO_GUARDAR_W_T1(&mira);
    D_80069414 = 0;
    func_8001CC68(&D_80069698->xE4);
    if (mira.x != 0) {
        CAMARA->mx = mira.x;
        CAMARA->m4[0] = mira.x;
        CAMARA->my = mira.y;
        CAMARA->m4[1] = mira.y;
        CAMARA->mz = mira.z;
        CAMARA->m4[2] = mira.z;
    }
    if (vp.x != 0) {
        CAMARA->vpx = vp.x;
        CAMARA->vp68[0] = vp.x;
        CAMARA->vp94[0] = vp.x;
        CAMARA->vpB4[0] = vp.x;
        CAMARA->vpy = vp.y;
        CAMARA->vp68[1] = vp.y;
        CAMARA->vp94[1] = vp.y;
        CAMARA->vpB4[1] = vp.y;
        CAMARA->vpz = vp.z;
        CAMARA->vp68[2] = vp.z;
        CAMARA->vp94[2] = vp.z;
        CAMARA->vpB4[2] = vp.z;
    }
    if (D_80069698 != NULL) {
        D_80069DC0.x = D_80069698->xE4;
        D_80069DC0.y = D_80069698->yE8;
        D_80069DC0.z = D_80069698->zEC;
    }
    CAMARA->i90 = 0;
    CAMARA->flags80 = 0x40;
    D_80069624 = -200;
    D_80069618 = 600;
    D_800693F6 = 0;
    D_800693F8 = 0;
    D_8006961C = 1100;
    D_800693F4 = 0;
    D_80010076 = 0;
    D_800693F0 = 1100;
    D_80069416 = 0;
    D_8006940C = 0;
}

/* Sacudida de la camara: oscila con seno y coseno y se amortigua. */
void func_80032A24(void)
{
    s32 r;
    s16 a;

    if (CAMARA->s88 != 0) {
        CAMARA->s8C = (rsin(CAMARA->s8A) * CAMARA->s88) >> 11;
        r = rcos(CAMARA->s8A) * CAMARA->s88;
        CAMARA->mx = CAMARA->mx + CAMARA->s8C;
        CAMARA->s8A = CAMARA->s8A + CAMARA->s86;
        CAMARA->s8E = r >> 12;
        CAMARA->my = CAMARA->my + CAMARA->s8E;
        a = CAMARA->s8A;
        if (a >= 0x800) {
            if (CAMARA->s88 >= 4) {
                CAMARA->s88 = CAMARA->s88 - 3;
            } else {
                CAMARA->s88 = 0;
            }
        } else if (a >= 0x1000) {
            CAMARA->s8A = a - 0x1000;
            if (CAMARA->s88 >= 4) {
                CAMARA->s88 = CAMARA->s88 - 3;
            } else {
                CAMARA->s88 = 0;
            }
        }
    } else {
        CAMARA->s8C = 0;
        CAMARA->s8E = 0;
    }
}

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032B2C);

/*
 * Busca un giro en Y para el que la sonda de colision avance libre: prueba hasta 25 giros de la
 * tabla D_8005E6F8 y guarda la distancia de cada uno en D_80069D90. Devuelve 0 si el giro
 * inicial sirve, 1 si sirve otro y 2 si ninguno (entonces elige el de mayor distancia).
 */
s32 func_800330AC(Giro* a0, Vec3* a1, Vec3* a2, SondaCamara* arg)
{
    SondaCamara* w;
    s32 i;
    s32 k;
    s32 s1;
    s32 x;
    s32 z;
    s32* q;
    /* El marco del original reserva 16 bytes de locales que ninguna sentencia toca. */
    s32 reserva[4];

    w = arg;
    q = &w->i68;
    w->pos.vx = a1->x;
    w->pos.vy = a1->y;
    w->pos.vz = a1->z;
    i = 0;
    w->dir.vx = (u16)a2->x;
    w->dir.vy = (u16)a2->y;
    w->dir.vz = (u16)a2->z;
    w->rot.vx = 0;
    w->rot.vz = 0;
    do {
        w->rot.vy = a0->y + D_8005E6F8[i];
        RotMatrix(&w->rot, &w->m);
        k = i;
        gte_SetRotMatrix(&w->m);
        gte_ldv0(&w->dir);
        gte_rtv0();
        gte_stlvnl(&w->res);
        w->pos.vy = a1->y;
        *q = 0;
        w->s5A = -1;
        s1 = w->res.vx + w->res.vz;
        func_80019474(&w->pos, &w->res, &w->pad50, q);
        x = w->res.vx;
        z = w->res.vz;
        s1 = s1 - (x + z);
        D_80069D90[i] = SquareRoot0(x * x + z * z);
        if ((w->f52 & 4) == 0 && s1 == 0) {
            break;
        }
        i++;
    } while (k < 0x18);
    GEO_CARGAR_W(&w->res);
    GEO_GUARDAR_W_T1(a2);
    a0->y = D_8005E6F8[i];
    if (i < 0x18) {
        if (i != 0) {
            return 1;
        }
    } else {
        i = 0;
        s1 = 0;
        do {
            w->dir.vx = 0;
            if (s1 < D_80069D90[i]) {
                s1 = D_80069D90[i];
                w->dir.vx = i;
            }
            i++;
        } while (i < 0x18);
        a0->y = D_8005E6F8[w->dir.vx];
        return 2;
    }
    return 0;
}

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80033358);

/* Al dar de baja un objeto, libera a los que lo tenian como padre (p70) y deshace los enlaces cruzados. */
void func_80034E7C(Objeto* o)
{
    Objeto* p;
    Objeto* sig;
    Objeto* a;

    if ((o->flags18 & 0x800) != 0) {
        p = D_80069518;
        if (p != NULL) {
            do {
                if (p->p70 == o) {
                    if ((p->flags18 & 0x400) != 0) {
                        a = p->p6C;
                        if (a != NULL && (a->flags18 & 0x400) == 0) {
                            a->flags14 &= ~0x814;
                            p->p6C->flags14 |= 0x1000;
                            p->p6C->iC4 = 0;
                            p->p6C->pC0 = (Objeto*)((u8*)p->p6C + 0xCC);
                            p->p6C->w26 = p->w26;
                            p->p6C->p70 = NULL;
                            func_8001CF50(p->p6C);
                            a = p->p6C;
                            if (a->w2C == 0xE) {
                                a->i158 = 0;
                            }
                        }
                        sig = p->siguiente;
                        ClearList(OBJ_LISTA(p));
                        D_80069518 = RemoveListNode(D_80069518, p);
                        func_8003F900(p);
                        func_80034E7C(p);
                        p = sig;
                        continue;
                    }
                    p->pC0 = (Objeto*)((u8*)p + 0xCC);
                    p->iC4 = 0;
                    p->p70 = NULL;
                    p->flags14 = (p->flags14 & ~0x14) | 0x1202;
                    func_8001CFCC((u8*)p + 0x7C);
                }
                if (p->p6C == o) {
                    p->p6C = NULL;
                }
                p = p->siguiente;
            } while (p != NULL);
        }
    }
}

/* Da de baja un objeto de escena: lo suelta de sus enlaces, de la lista solida y de la lista de objetos. */
void func_8003502C(Objeto* o)
{
    Objeto* p;
    ObjetoVolumen* v;

    if ((s32)o == D_80069560) {
        D_80069560 = (s32)D_80069698;
    }
    if (D_80069698->p6C == o) {
        D_80069698->p6C = NULL;
    }
    p = o->p70;
    if (p != NULL) {
        if (p->p6C == o) {
            p->p6C = NULL;
        }
        o->p70 = NULL;
    }
    if (o->p6C != NULL) {
        o->p6C->flags14 &= ~0x814;
        o->p6C->iC4 = 0;
        o->p6C->pC0 = (Objeto*)((u8*)o->p6C + 0xCC);
        o->p6C->w26 = o->w26;
        o->p6C->p70 = NULL;
        func_8001CF50(o->p6C);
        o->p6C->i158 = 0;
        o->p6C = NULL;
    }
    if ((ObjetoVolumen*)o == D_80069630) {
        D_80069630 = ((ObjetoVolumen*)o)->sig;
    } else {
        v = D_80069630;
        while (v != NULL && v->sig != (ObjetoVolumen*)o) {
            v = v->sig;
        }
        if (v != NULL) {
            v->sig = ((ObjetoVolumen*)o)->sig;
        }
    }
    ClearList(OBJ_LISTA(o));
    D_80069518 = RemoveListNode(D_80069518, o);
    func_8003F900(o);
    func_80034E7C(o);
}

/* Prepara un objeto para su baja: limpia banderas y suelta la lista enlazada si ya no la usa nadie. */
void func_800351B4(Objeto* o)
{
    OBJ_U32(o, 4) &= ~2;
    o->flags18 |= 0x100;
    if ((OBJ_U32(o, 8) & 0x1000) != 0) {
        if ((o->flags15C & 0x4000) == 0) {
            if (*(void**)OBJ_LISTA(o) != NULL) {
                if (o->p70 == NULL) {
                    o->flags15C |= 0x4000;
                    o->i158 = 0;
                    ClearList(OBJ_LISTA(o));
                    *(void**)OBJ_LISTA(o) = NULL;
                }
            }
        }
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 550 con la configuracion versionada (g = 8 del archivo). El original carga antes del
 * bucle las constantes 0x47 y 1 de la ultima rama (t2 y t1) y por eso la tabla de saltos cae en t3; GCC las deja
 * dentro de la rama. Variantes: indexado por D_8005E768[i], constantes en locales, paso++, puntero local al estado.
 *
 * Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron respecto al cuadro anterior (dato pequeno
 * 0x104($gp)), avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas);
 * al completar una ejecuta su caso con un switch de siete entradas.
 */
void func_80035244(void)
{
    s32 i;
    Secuencia* e;
    s32 estado;

    estado = D_80010010;
    estado &= 0xFFF6;
    if (D_80069424 != estado) {
        D_80069424 = estado;
        if (estado != 0) {
            e = D_8005E768;
            for (i = 0; i < 7; i++, e++) {
                if (e->teclas[e->paso] == estado) {
                    e->paso = e->paso + 1;
                    if (e->teclas[e->paso] == 0) {
                        switch (e->caso) {
                        case 0:
                            PRINCIPAL->f64 |= 1;
                            break;
                        case 1:
                            PRINCIPAL->f43 = 0x63;
                            PRINCIPAL->f64 |= 2;
                            break;
                        case 2:
                            PRINCIPAL->f48 |= 0x1F;
                            PRINCIPAL->f64 |= 4;
                            break;
                        case 3:
                            PRINCIPAL->f41 = 6;
                            PRINCIPAL->f64 |= 8;
                            break;
                        case 4:
                            PRINCIPAL->f48 |= 0x80;
                            PRINCIPAL->f64 |= 0x10;
                            break;
                        case 5:
                            PRINCIPAL->f47 = 0x4D;
                            PRINCIPAL->f13C = 1;
                            PRINCIPAL->f45 = 0x7C;
                        case 6:
                            PRINCIPAL->modo = 0x47;
                            D_80069662 = 1;
                            break;
                        }
                    }
                } else {
                    e->paso = 0;
                }
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80035244);
#endif

INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800353B0);
