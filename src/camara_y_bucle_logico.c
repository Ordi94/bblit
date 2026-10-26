#include "common.h"
#include "globales.h"
#include "geometria.h"
#include "gte.h"
#include "arranque.h"
#include "objetos.h"
#include "motor.h"

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

/* Area de trabajo del rayo de camara (func_80032B2C): matriz, vectores locales, caja del objeto y objeto en curso. */
typedef struct RayoCamara {
    MATRIX m;
    SVECTOR rot;
    SVECTOR v28;
    SVECTOR d30;
    VECTOR suma;
    SVECTOR a48;
    SVECTOR a50;
    s32 i58;
    s32 i5C;
    s32 i60;
    Objeto* cur;
} RayoCamara;

/* Memoria de trabajo de func_800353B0 en el scratchpad (0x1F800000). */
typedef struct Scratch {
    s32 d0;
    s32 d4;
    s32 d8;
    u8 padC[4];
    SVECTOR p10;
    s32 m18;
    s32 m1C;
    s32 m20;
    u8 pad24[0x2C - 0x24];
    Objeto* cur;
    Objeto* l30;
    Objeto* l34;
    Objeto* l38;
    EntradaVisible* tp3C;
    s32 i40;
    s32 i44;
    u8 pad48[0x68 - 0x48];
    s16 sx;
    s16 sy;
    s32 z6C;
    s32 i70;
    s32 r74;
    GsCOORDINATE2* n78;
    u8 pad7C[4];
    VECTOR v80[8];
    VECTOR* p100;
    SVECTOR c104[8];
    SVECTOR* p144;
} Scratch;

/*
 * Guarda MAC3 del GTE (profundidad tras rtps) en la palabra apuntada. mfc2 lee un registro del
 * coprocesador, el unico caso que el compilador no expresa en C.
 */
#define GUARDAR_MAC3(p) \
    __asm__ volatile ("move $9, %0\n\tmfc2 $8, $27\n\tnop\n\tsw $8, 0($9)" : : "r"(p) : "$8", "$9", "memory")

extern void (*D_8005E35C[])(Objeto*);
extern void func_80033358(void* a0, u32 a1);
extern void func_80035244(void);
extern void func_800351B4(Objeto* a0);
extern void func_8003502C(Objeto* a0);

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

extern Secuencia D_8005E768[];

extern u16 D_8005E6F8[];
extern s16 D_80069D90[];
extern void func_80019474(void* pos, void* res, void* f50, void* i68);
extern long SquareRoot0(long x);
extern s32 rand(void);
extern void func_8003F900(Objeto* a0);
extern Vec3 D_80069DC0;

/* Variables de datos pequenos: el original las direcciona con desplazamiento($gp). */
u16 D_800693F4;
s16 D_800693F6;
s16 D_800693F8;
s32 D_800693F0;
u16 D_8006940C;
u16 D_80069414;
s16 D_80069416;
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

    GEO_CARGAR_W(&D_8006D928.vpx);
    GEO_GUARDAR_W_T1(&vp);
    GEO_CARGAR_W(&D_8006D928.x);
    GEO_GUARDAR_W_T1(&mira);
    D_80069414 = 0;
    func_8001CC68(&D_80069698->param.trans.vx);
    if (mira.x != 0) {
        D_8006D928.x = mira.x;
        D_8006D928.cA4 = mira.x;
        D_8006D928.y = mira.y;
        D_8006D928.cA8 = mira.y;
        D_8006D928.z = mira.z;
        D_8006D928.cAC = mira.z;
    }
    if (vp.x != 0) {
        D_8006D928.vpx = vp.x;
        D_8006D928.c68 = vp.x;
        D_8006D928.c94 = vp.x;
        D_8006D928.cB4 = vp.x;
        D_8006D928.vpy = vp.y;
        D_8006D928.c6C = vp.y;
        D_8006D928.c98 = vp.y;
        D_8006D928.cB8 = vp.y;
        D_8006D928.vpz = vp.z;
        D_8006D928.c70 = vp.z;
        D_8006D928.c9C = vp.z;
        D_8006D928.cBC = vp.z;
    }
    if (D_80069698 != NULL) {
        D_80069DC0.x = D_80069698->param.trans.vx;
        D_80069DC0.y = D_80069698->param.trans.vy;
        D_80069DC0.z = D_80069698->param.trans.vz;
    }
    D_8006D928.i90 = 0;
    D_8006D928.flags80 = 0x40;
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

    if (D_8006D928.s88 != 0) {
        D_8006D928.h8C = (rsin(D_8006D928.s8A) * D_8006D928.s88) >> 11;
        r = rcos(D_8006D928.s8A) * D_8006D928.s88;
        D_8006D928.x = D_8006D928.x + D_8006D928.h8C;
        D_8006D928.s8A = D_8006D928.s8A + D_8006D928.s86;
        D_8006D928.h8E = r >> 12;
        D_8006D928.y = D_8006D928.y + D_8006D928.h8E;
        a = D_8006D928.s8A;
        if (a >= 0x800) {
            if (D_8006D928.s88 >= 4) {
                D_8006D928.s88 = D_8006D928.s88 - 3;
            } else {
                D_8006D928.s88 = 0;
            }
        } else if (a >= 0x1000) {
            D_8006D928.s8A = a - 0x1000;
            if (D_8006D928.s88 >= 4) {
                D_8006D928.s88 = D_8006D928.s88 - 3;
            } else {
                D_8006D928.s88 = 0;
            }
        }
    } else {
        D_8006D928.h8C = 0;
        D_8006D928.h8E = 0;
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 774 con la configuracion versionada (g = 8 del archivo). El flujo y las macros vectoriales
 * coinciden; difiere el reparto de los registros salvados (el original deja los argumentos en s5 y s2 y los
 * punteros hoisted &w->i58, &w->rot, &w->v28, &w->d30 en s6, s4, s3, s1). Variantes probadas: 15 (punteros locales
 * hoisted en distinto orden y subconjunto, asignacion al inicio o dentro del bloque).
 *
 * Rayo de camara contra la lista de objetos solidos D_80069630: para cada objeto cuyos indicadores casan con la
 * mascara y cuya caja esta a menos de su alcance, lleva la posicion al sistema local del objeto, comprueba la caja
 * ensanchada por el radio y, si el punto cae sobre el objeto, desplaza el vector de salida a la cara mas cercana
 * (cuatro rectas de la caja segun el angulo ratan2) y lo devuelve al sistema global; retorna el objeto o 0.
 */
s32 func_80032B2C(Vec3* a0, Vec3* a1, RayoCamara* w, u32 mascara)
{
    s32* p58;
    SVECTOR* pd30;
    SVECTOR* prot;

    w->suma.vx = a0->x + a1->x;
    w->suma.vy = a0->y + a1->y;
    w->cur = D_80069630;
    w->suma.vz = a0->z + a1->z;
    if (w->cur != NULL) {
        p58 = &w->i58;
        pd30 = &w->d30;
        prot = &w->rot;
        do {
            if ((w->cur->flags08 & mascara) != 0) {
                GEO_CARGAR_WH(&w->cur->min);
                GEO_OR_WH(&w->cur->max);
                GEO_GUARDAR_1W_T1(p58);
                if (w->i58 != 0) {
                    GEO_CARGAR_W(&w->suma);
                    GEO_RESTAR_W(&w->cur->param.trans);
                    GEO_GUARDAR_H_T4(pd30);
                    GEO_NORMA2_XZ(pd30, p58);
                    if (w->cur->alcance2 >= (u32)w->i58) {
                        w->i60 = w->cur->s20;
                        GEO_COMPLEMENTO(&w->cur->param.giro.rotate);
                        GEO_GUARDAR_H_T1(prot);
                        if (((w->cur->param.giro.rotate.vz + w->cur->param.giro.rotate.vx) & 0xFFF) == 0) {
                            if (((u16)w->cur->param.giro.rotate.vy & 0xFFF) == 0) {
                                GEO_CARGAR_WH(pd30);
                                GEO_GUARDAR_WH(&w->v28);
                            } else {
                                GEO_IDENTIDAD(w);
                                RotMatrixY(w->rot.vy, &w->m);
                                ApplyMatrixSV(&w->m, pd30, &w->v28);
                            }
                        } else {
                            RotMatrixZYX(prot, &w->m);
                            ApplyMatrixSV(&w->m, pd30, &w->v28);
                        }
                        if (w->v28.vx >= w->cur->min.vx - w->i60
                            && w->cur->max.vx + w->i60 >= w->v28.vx
                            && w->v28.vz >= w->cur->min.vz - w->i60
                            && w->cur->max.vz + w->i60 >= w->v28.vz
                            && w->cur->max.vy < w->v28.vy
                            && w->cur->min.vy >= w->v28.vy - 0xF0) {
                            w->i58 = w->cur->max.vy - w->v28.vy;
                            w->a48.vx = a0->x - w->cur->param.trans.vx;
                            w->a48.vy = 0;
                            w->a48.vz = a0->z - w->cur->param.trans.vz;
                            RotMatrixZYX(prot, &w->m);
                            ApplyMatrixSV(&w->m, &w->a48, &w->a50);
                            w->i5C = ratan2(w->a50.vx, w->a50.vz);
                            w->v28.vx = a1->x;
                            w->v28.vy = a1->y;
                            w->v28.vz = a1->z;
                            ApplyMatrixSV(&w->m, &w->v28, &w->v28);
                            w->i60 = w->i60 + 2;
                            if (w->i5C >= 0) {
                                if (w->i5C < ratan2(w->cur->max.vx + w->i60, w->cur->max.vz + w->i60)) {
                                    w->v28.vz = (u16)w->cur->max.vz + (u16)w->i60 - (u16)w->a50.vz;
                                } else if (w->i5C < ratan2(w->cur->max.vx + w->i60, w->cur->min.vz - w->i60)) {
                                    w->v28.vx = (u16)w->cur->max.vx + (u16)w->i60 - (u16)w->a50.vx;
                                } else {
                                    w->v28.vz = (u16)w->cur->min.vz - (u16)w->i60 - (u16)w->a50.vz;
                                }
                            } else {
                                w->i5C = -w->i5C;
                                if (w->i5C < -ratan2(w->cur->min.vx - w->i60, w->cur->max.vz + w->i60)) {
                                    w->v28.vz = (u16)w->cur->max.vz + (u16)w->i60 - (u16)w->a50.vz;
                                } else if (w->i5C < -ratan2(w->cur->min.vx - w->i60, w->cur->min.vz - w->i60)) {
                                    w->v28.vx = (u16)w->cur->min.vx - (u16)w->i60 - (u16)w->a50.vx;
                                } else {
                                    w->v28.vz = (u16)w->cur->min.vz - (u16)w->i60 - (u16)w->a50.vz;
                                }
                            }
                            RotMatrix(&w->cur->param.giro.rotate, &w->m);
                            ApplyMatrixSV(&w->m, &w->v28, &w->v28);
                            a1->x = w->v28.vx;
                            a1->y = w->i58;
                            a1->z = w->v28.vz;
                            return (s32)w->cur;
                        }
                    }
                }
            }
            w->cur = w->cur->sig10;
        } while (w->cur != NULL);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032B2C);
#endif

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
                            p->p6C->coord.super = NULL;
                            p->p6C->coord.param = PARAMETROS_SDK(p->p6C);
                            p->p6C->w26 = p->w26;
                            p->p6C->p70 = NULL;
                            func_8001CF50(p->p6C);
                            a = p->p6C;
                            if (a->w2C == 0xE) {
                                a->trabajo.i14 = 0;
                            }
                        }
                        sig = p->siguiente;
                        ClearList((NodoLista*)&p->u78.ayudas);
                        D_80069518 = (Objeto*)RemoveListNode((NodoLista*)D_80069518, (NodoLista*)p);
                        func_8003F900(p);
                        func_80034E7C(p);
                        p = sig;
                        continue;
                    }
                    p->coord.param = PARAMETROS_SDK(p);
                    p->coord.super = NULL;
                    p->p70 = NULL;
                    p->flags14 = (p->flags14 & ~0x14) | 0x1202;
                    func_8001CFCC(&p->coord);
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
    Objeto* v;

    if (o == D_80069560) {
        D_80069560 = D_80069698;
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
        o->p6C->coord.super = NULL;
        o->p6C->coord.param = PARAMETROS_SDK(o->p6C);
        o->p6C->w26 = o->w26;
        o->p6C->p70 = NULL;
        func_8001CF50(o->p6C);
        o->p6C->trabajo.i14 = 0;
        o->p6C = NULL;
    }
    if (o == D_80069630) {
        D_80069630 = o->sig10;
    } else {
        v = D_80069630;
        while (v != NULL && v->sig10 != o) {
            v = v->sig10;
        }
        if (v != NULL) {
            v->sig10 = o->sig10;
        }
    }
    ClearList((NodoLista*)&o->u78.ayudas);
    D_80069518 = (Objeto*)RemoveListNode((NodoLista*)D_80069518, (NodoLista*)o);
    func_8003F900(o);
    func_80034E7C(o);
}

/* Prepara un objeto para su baja: limpia banderas y suelta la lista enlazada si ya no la usa nadie. */
void func_800351B4(Objeto* o)
{
    o->flags04 &= ~2;
    o->flags18 |= 0x100;
    if ((o->flags08 & 0x1000) != 0) {
        if ((o->trabajo.flags18 & 0x4000) == 0) {
            if (o->u78.ayudas != NULL) {
                if (o->p70 == NULL) {
                    o->trabajo.flags18 |= 0x4000;
                    o->trabajo.i14 = 0;
                    ClearList((NodoLista*)&o->u78.ayudas);
                    o->u78.ayudas = NULL;
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
                            ESTADO_PRINCIPAL->r[0x24] |= 1;
                            break;
                        case 1:
                            ESTADO_PRINCIPAL->r[0x03] = 0x63;
                            ESTADO_PRINCIPAL->r[0x24] |= 2;
                            break;
                        case 2:
                            ESTADO_PRINCIPAL->r[0x08] |= 0x1F;
                            ESTADO_PRINCIPAL->r[0x24] |= 4;
                            break;
                        case 3:
                            ESTADO_PRINCIPAL->r[0x01] = 6;
                            ESTADO_PRINCIPAL->r[0x24] |= 8;
                            break;
                        case 4:
                            ESTADO_PRINCIPAL->r[0x08] |= 0x80;
                            ESTADO_PRINCIPAL->r[0x24] |= 0x10;
                            break;
                        case 5:
                            ESTADO_PRINCIPAL->r[0x07] = 0x4D;
                            ESTADO_PRINCIPAL->r[0xFC] = 1;
                            ESTADO_PRINCIPAL->r[0x05] = 0x7C;
                        case 6:
                            ESTADO_PRINCIPAL->nivel = 0x47;
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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales
 * y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la
 * mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia
 * (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original
 * relee el puntero guardado en el scratchpad en cada vuelta). Variantes probadas: 12 (locales del objeto,
 * punteros hoisted, mascara en local, macro de distancia con salida por registro o por puntero, y la suma de
 * vectores y la distancia reescritas en C, que dan 9641 y 11566: ver GEO_SUMAR_W y GEO_DISTANCIA_APROX).
 */
/*
 * Lista de comprobaciones del cuadro: recorre los objetos de escena, los clasifica en cuatro listas
 * (segun sus indicadores) con la memoria de trabajo del scratchpad en 0x1F800000, los vuelve a enlazar en
 * D_80069630 y ejecuta la rutina de logica de cada uno (tabla D_8005E35C).
 */
void func_800353B0(Objeto* a0)
{
    Scratch* sc;
    Objeto* o;
    Objeto* s0;
    Objeto* t;
    GsCOORDINATE2* n;
    s32 sx;
    s32 sy;
    s32 r;
    s16* psx;
    s32* pz;
    s32 m3;

    sc = (Scratch*)0x1F800000;
    D_80069652 = 0;
    D_800694D4 = D_800694B8;
    if (D_8006AA70[0xC] == 0) {
        if (D_80069560 != 0) {
            func_80033358(D_80069560, D_80069698->w1B4);
        }
    }
    func_80035244();
    sc->m18 = D_8006D928.x - D_8006D928.vpx;
    sc->m20 = D_8006D928.z - D_8006D928.vpz;
    sc->r74 = ratan2(sc->m18, sc->m20);
    gte_SetRotMatrix(&D_80076130);
    gte_SetTransVector(&D_80076144);
    if (D_80069698 != NULL && (D_8006D928.vpx + D_8006D928.vpy + D_8006D928.vpz) == 0) {
        sc->m18 = D_80069698->param.trans.vx;
        sc->m1C = D_80069698->param.trans.vy;
        sc->m20 = D_80069698->param.trans.vz;
    } else {
        sc->m18 = D_8006D928.vpx;
        sc->m1C = D_8006D928.vpy;
        sc->m20 = D_8006D928.vpz;
    }
    sc->l30 = NULL;
    sc->l34 = NULL;
    sc->l38 = NULL;
    sc->i70 = 0;
    D_80069630 = NULL;
    sc->cur = a0;
    if (a0 != NULL) {
        m3 = -3;
        psx = &sc->sx;
        pz = &sc->z6C;
        do {
            if ((sc->cur->flags14 & 0x100) != 0) {
                s0 = sc->cur->siguiente;
                func_8003502C(sc->cur);
                if (s0 == NULL) {
                    goto fin;
                }
                sc->cur = s0;
            }
            if (sc->cur->w24 != 0) {
                sc->cur->w24 = sc->cur->w24 - 1;
            }
            if ((sc->cur->flags0C & 0x40) != 0) {
                goto siguiente;
            }
            sc->cur->flags04 |= 2;
            sc->cur->flags18 &= ~0x100;
            if ((sc->cur->flags04 & 0x20) == 0 && sc->cur->w1C != 5 && sc->cur->w2C != 0x14
                && sc->cur->p70 != D_80069698 && sc->cur->p6C != D_80069698 && sc->cur->w3C != 0) {
                if ((sc->cur->w3C & 2) != 0) {
                    sc->d0 = sc->m18 - sc->cur->param.trans.vx;
                    sc->d4 = sc->m1C - sc->cur->param.trans.vy;
                    sc->d8 = sc->m20 - sc->cur->param.trans.vz;
                    GEO_DISTANCIA_APROX(sc);
                    if (sc->cur->w3E < sc->i44) {
                        if ((sc->cur->w3C & 0x40) == 0) {
                            sc->cur->w24 = (sc->i44 - sc->cur->w3E) >> 7;
                            func_800351B4(sc->cur);
                            goto siguiente;
                        }
                        sc->cur->flags04 &= m3;
                        sc->cur->flags18 |= 0x100;
                    }
                }
                if ((sc->cur->w3C & 1) != 0 && (sc->cur->flags04 & 2) != 0) {
                    sc->i40 = 0;
                    sc->tp3C = D_8006A940;
                    if (sc->i40 < D_80069588) {
                        do {
                            if ((s16)sc->cur->w26 == sc->tp3C->modelo) {
                                break;
                            }
                            sc->i40++;
                            sc->tp3C++;
                        } while (sc->i40 < D_80069588);
                    }
                    if (sc->i40 < D_80069588) {
                        if ((sc->tp3C->bandera & 1) != 0 && (sc->cur->flags08 & 0x10000) != 0) {
                            goto sigue2;
                        }
                    } else if (D_80069588 != sc->i40) {
                        goto sigue2;
                    }
                    if ((sc->cur->w3C & 0x40) == 0) {
                        func_800351B4(sc->cur);
                        goto siguiente;
                    }
                    sc->cur->flags04 &= m3;
                    sc->cur->flags18 |= 0x100;
                }
sigue2:
                if ((sc->cur->w3C & 0x20) != 0 && (sc->cur->flags04 & 2) != 0) {
                    if (sc->cur->u78.p == NULL && (sc->cur->flags18 & 0x80) == 0) {
                        sc->p10.vx = sc->cur->param.trans.vx;
                        sc->p10.vy = sc->cur->param.trans.vy;
                        sc->p10.vz = sc->cur->param.trans.vz;
                        gte_ldv0(&sc->p10);
                        gte_rtps();
                        gte_stsxy(psx);
                        GUARDAR_MAC3(pz);
                        sx = sc->sx;
                        sy = sc->sy;
                        if (sc->z6C < 0 || sx + sc->cur->w2E < -0x100 || sx - sc->cur->w2E > 0x100 || sy < -0x78
                            || sy + sc->cur->max.vy >= 0x79) {
                            sc->cur->flags04 &= m3;
                            sc->cur->flags18 |= 0x100;
                        }
                        if ((sc->cur->flags04 & 2) == 0) {
                            if ((sc->cur->w3C & 0xC0) == 0) {
                                goto atenuar;
                            }
                            goto tras_proyeccion;
                        }
                    } else {
                        sc->c104[0].vx = sc->c104[2].vx = sc->c104[4].vx = sc->c104[6].vx = sc->cur->min.vx;
                        sc->c104[1].vx = sc->c104[3].vx = sc->c104[5].vx = sc->c104[7].vx = sc->cur->max.vx;
                        sc->c104[0].vy = sc->c104[1].vy = sc->c104[2].vy = sc->c104[3].vy = sc->cur->max.vy;
                        sc->c104[4].vy = sc->c104[5].vy = sc->c104[6].vy = sc->c104[7].vy = sc->cur->min.vy;
                        sc->c104[0].vz = sc->c104[1].vz = sc->c104[4].vz = sc->c104[5].vz = sc->cur->max.vz;
                        sc->c104[2].vz = sc->c104[3].vz = sc->c104[6].vz = sc->c104[7].vz = sc->cur->min.vz;
                        sc->n78 = &sc->cur->coord;
                        if (sc->n78 != NULL) {
                            do {
                                n = sc->n78;
                                gte_SetRotMatrix(&n->coord);
                                sc->d0 = n->coord.t[0];
                                sc->d4 = n->coord.t[1];
                                r = n->coord.t[2];
                                sc->i40 = 0;
                                sc->p100 = sc->v80;
                                sc->p144 = sc->c104;
                                sc->d8 = r;
                                while (sc->i40 < 8) {
                                    gte_ldv0(sc->p144);
                                    gte_rtv0();
                                    gte_stlvnl(sc->p100);
                                    GEO_CARGAR_W(sc);
                                    GEO_SUMAR_W(sc->p100);
                                    GEO_CARGAR_W(sc->p100);
                                    GEO_GUARDAR_H_T1(sc->p144);
                                    sc->i40++;
                                    sc->p100++;
                                    sc->p144++;
                                }
                                sc->n78 = sc->n78->super;
                            } while (sc->n78 != NULL);
                        }
                        gte_SetRotMatrix(&D_80076130);
                        sc->i40 = 0;
                        sc->p144 = sc->c104;
                        while (sc->i40 < 8) {
                            gte_ldv0(sc->p144);
                            gte_rtps();
                            gte_stsxy(psx);
                            GUARDAR_MAC3(pz);
                            sy = sc->sy;
                            if (sc->z6C >= 0 && (u16)(sc->sx + 0x100) < 0x201 && sy >= -0x78 && sy < 0x79) {
                                break;
                            }
                            sc->i40++;
                            sc->p144++;
                        }
                        if (sc->i40 == 8) {
                            sc->cur->flags04 &= m3;
                            sc->cur->flags18 |= 0x100;
                        }
tras_proyeccion:
                        if ((sc->cur->flags04 & 2) == 0 && (sc->cur->w3C & 0xC0) == 0) {
atenuar:
                            sc->cur->w24 = (0x400 - sc->i40) >> 7;
                            func_800351B4(sc->cur);
                            goto siguiente;
                        }
                    }
                }
            }
            if (sc->cur->w2C == 0x10 || sc->cur->w2C == 0x24) {
                sc->cur->flags04 &= m3;
                sc->cur->flags18 |= 0x100;
            }
            if (sc->cur->w2C == 0x15) {
                sc->cur->sig10 = sc->l34;
                sc->l34 = sc->cur;
            } else if ((sc->cur->flags08 & 0x20000) != 0) {
                sc->cur->sig10 = sc->l30;
                sc->l30 = sc->cur;
            } else if ((sc->cur->flags08 & 8) != 0) {
                sc->cur->sig10 = sc->l38;
                sc->l38 = sc->cur;
            } else if (sc->cur->w1C == 1) {
                D_80069698 = sc->cur;
            } else {
                sc->cur->sig10 = D_80069630;
                D_80069630 = sc->cur;
            }
siguiente:
            sc->cur = sc->cur->siguiente;
        } while (sc->cur != NULL);
    }
fin:
    if (D_80069698 != NULL) {
        t = D_80069630;
        D_80069630 = D_80069698;
        (D_80069698)->sig10 = t;
    }
    if (sc->l38 != NULL) {
        sc->cur = sc->l38;
        while (sc->cur->sig10 != NULL) {
            sc->cur = sc->cur->sig10;
        }
        sc->cur->sig10 = D_80069630;
        D_80069630 = sc->l38;
    }
    if (sc->l30 != NULL) {
        sc->cur = sc->l30;
        while (sc->cur->sig10 != NULL) {
            sc->cur = sc->cur->sig10;
        }
        sc->cur->sig10 = D_80069630;
        D_80069630 = sc->l30;
    }
    if (sc->l34 != NULL) {
        sc->l34->sig10 = D_80069630;
        D_80069630 = sc->l34;
    }
    s0 = D_80069630;
    D_800695D0 = 0;
    D_800695EC = 0;
    D_80069560 = D_80069698;
    if (s0 != NULL) {
        do {
            o = s0;
            if (D_8006AA70[0xC] == 0) {
                if ((s0->flags14 & 0x100) == 0) {
                    D_8005E35C[s0->w2C](s0);
                }
                if ((*(u32*)&D_8006D928.flags80 & 0x300) != 0x100 || s0->w2C == 0x20 || (s0->flags18 & 0x1000) != 0) {
                    s0->w22++;
                    o = s0;
                }
            } else if ((s0->flags14 & 0x100) == 0 && (s0->flags0C & 0x40000000) != 0) {
                D_8005E35C[s0->w2C](s0);
                s0->w22++;
                o = s0;
            }
            s0 = s0->sig10;
            if ((o->flags14 & 0x100) != 0) {
                func_8003502C(o);
            }
        } while (s0 != NULL);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800353B0);
#endif
