#include "geometria.h"
#include "globales.h"
#include "gte.h"
#include "psyq/GTEMAC.H"


/*
 * Area de trabajo de las consultas de segmento (func_80017478 y func_80018664): matriz inversa del
 * objeto candidato, matriz del objeto que se mueve, vectores locales, cuatro vertices mas un centro
 * de la caja barrida y los angulos de las esquinas del candidato vistas desde su centro.
 */
typedef struct ConsultaSondeo {
    MATRIX m;
    MATRIX m2;
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
    VECTOR destino;
    SVECTOR sal;
    s16 e_x;
    s16 pad72;
    s16 e_z;
    s16 pad76;
    u32 caja;
    s32 ang;
    s32 radio;
    s16 s84;
    s16 s86;
    Objeto* actual;
    Objeto* cadena;
    Objeto* a;
    Objeto* b;
    SVECTOR p[5];
    SVECTOR* pt;
    u32 dist2;
    s16 angs[4];
} ConsultaSondeo;


/* Esquinas del barrido y punto de prueba como pares (z, x) de 16 bits; func_80017478 las usa para elegir la arista mas cercana. */
typedef struct ParZX {
    s16 z;
    s16 x;
} ParZX;
extern ParZX D_80069D18[5];
extern VECTOR D_80069D08;
extern VECTOR D_80069C08;

/* Dato pequeno: el original lo direcciona como 0x60($gp) (area con signo mas baja de las aristas probadas). */
s32 D_80069380;

#define U16_2E(o) (*(u16*)((u8*)(o) + 0x2E))

/* Cabeza de la lista de nodos de plano (enlace en +0). */

/*
 * Busca el primer objeto solido cuyo volumen contiene a la caja del objeto a: el candidato se
 * lleva al sistema local del otro objeto con la inversa de sus angulos y se compara con su caja
 * ampliada por el radio. mascara filtra por indicadores; o es el area de trabajo.
 *
 * La matriz se asigna a una variable que vale 0 antes del bucle y se vuelve a asignar dentro: con una sola
 * asignacion el optimizador de bucles saca &o->m fuera del bucle, y el original lo calcula en cada vuelta.
 * El original la calcula justo despues de cargar el primer argumento de RotMatrixZYX; el C la calcula una
 * instruccion antes y esa es toda la diferencia (60).
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 70 con la configuracion versionada (g = 8 del archivo). Solo difiere la posicion de un addiu (el calculo de &o->m se emite una instruccion antes que en el original) y el registro del puntero de destino de la norma al cuadrado (v0 en lugar de a0). Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6. */
Objeto* func_80016C0C(Objeto* a, u32 mascara, ConsultaVolumen* o)
{
    SVECTOR* dif;
    SVECTOR* rot;
    MATRIX* m;

    o->actual = D_80069630;
    if (o->actual != 0) {
        dif = &o->dif;
        rot = &o->rot;
        m = 0;
        do {
            if ((o->actual->flags08 & mascara) && o->actual->s2A == 2 && a != o->actual
                && a->p70 != o->actual && a->p6C != o->actual && o->actual->p70 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->caja);
                if (o->caja != 0) {
                    GEO_CARGAR_W(&a->param.trans);
                    GEO_RESTAR_W(&o->actual->param.trans);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &o->dist2);
                    if (o->actual->alcance2 >= o->dist2) {
                        o->radio = o->actual->s20;
                        GEO_COMPLEMENTO(&o->actual->param.giro.rotate);
                        GEO_GUARDAR_H_T1(rot);
                        m = &o->m;
                        RotMatrixZYX(rot, m);
                        ApplyMatrixSV(m, dif, &o->res);
                        if (o->res.vx >= o->actual->min.vx - o->radio
                            && o->res.vx <= o->actual->max.vx + o->radio
                            && o->res.vz >= o->actual->min.vz - o->radio
                            && o->res.vz <= o->actual->max.vz + o->radio
                            && o->res.vy + a->min.vy >= o->actual->max.vy
                            && o->actual->min.vy >= o->res.vy + a->max.vy) {
                            return o->actual;
                        }
                    }
                }
            }
            o->actual = o->actual->sig10;
        } while (o->actual != 0);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80016C0C);
#endif

/*
 * Variante de func_80016C0C que copia antes del bucle la posicion y la caja del objeto a al
 * area de trabajo y compara contra esas copias; devuelve el primer objeto solido que la
 * contiene.
 * Con g = 8 (config/opciones_compilacion.toml) el puntero global se carga directamente en $s0;
 * con -G0 la parte alta iria a otro registro (230).
 */
Objeto* func_80016ED0(Objeto* a, u32 mascara, ConsultaCaja* o)
{
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    RotMatrixZYX(&o->rot, &o->m);
    GEO_CARGAR_W(&a->param.trans);
    GEO_GUARDAR_W_T1(&o->pos);
    GEO_CARGAR_WH(&a->min);
    GEO_GUARDAR_WH(&o->min);
    GEO_CARGAR_WH(&a->max);
    GEO_GUARDAR_WH(&o->max);
    o->radio = a->s20;
    o->actual = D_80069630;
    if (o->actual != 0) {
        do {
            if ((o->actual->flags08 & mascara) && o->actual->s2A == 2 && a != o->actual
                && a->p70 != o->actual && a->p6C != o->actual && o->actual->p70 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->tmp);
                if (o->tmp != 0) {
                    GEO_CARGAR_W(&o->actual->param.trans);
                    GEO_RESTAR_W(&o->pos);
                    GEO_GUARDAR_H_T4(&o->dif);
                    GEO_NORMA2_XZ(&o->dif, &o->tmp);
                    if (o->tmp <= a->alcance2) {
                        ApplyMatrixSV(&o->m, &o->dif, &o->res);
                        if (o->res.vx >= o->min.vx - o->radio
                            && o->res.vx <= o->max.vx + o->radio
                            && o->res.vz >= o->min.vz - o->radio
                            && o->res.vz <= o->max.vz + o->radio
                            && o->res.vy + o->actual->min.vy >= o->max.vy
                            && o->res.vy + o->actual->max.vy <= o->min.vy) {
                            return o->actual;
                        }
                    }
                }
            }
            o->actual = o->actual->sig10;
        } while (o->actual != 0);
    }
    return 0;
}

/*
 * Variante con el punto a probar y una segunda mascara de exclusion como argumentos y el area
 * de trabajo como quinto argumento (en pila); el radio se ensancha 4 unidades.
 *
 * NON_MATCHING: solo difiere el reparto de registros: el original guarda el area de trabajo y el
 * radio ampliado en s2 y s3 y el C los intercambia, ademas de la posicion del calculo de &o->m.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 308 con la configuracion versionada (g = 8 del archivo). El objeto de trabajo y el radio ampliado intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 12. */
Objeto* func_800171E4(Objeto* a, VECTOR* p, u32 mascara, u32 excluir, ConsultaVolumen* o)
{
    Objeto* n;
    s32 r;
    SVECTOR* dif;
    SVECTOR* rot;
    MATRIX* m;

    m = 0;
    n = D_80069630;
    if (n != 0) {
        dif = &o->dif;
        rot = &o->rot;
        do {
            if ((n->flags08 & mascara) && n->s2A == 2 && n != a && !(n->flags08 & excluir)) {
                GEO_CARGAR_WH(&n->min);
                GEO_OR_WH(&n->max);
                GEO_GUARDAR_1W_T1(&o->caja);
                if (o->caja != 0) {
                    GEO_CARGAR_W(p);
                    GEO_RESTAR_W(&n->param.trans);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &o->dist2);
                    if (o->dist2 <= n->alcance2) {
                        r = n->s20 + 4;
                        GEO_COMPLEMENTO(&n->param.giro.rotate);
                        GEO_GUARDAR_H_T1(rot);
                        m = &o->m;
                        RotMatrixZYX(rot, m);
                        ApplyMatrixSV(m, dif, &o->res);
                        if (o->res.vx >= n->min.vx - r
                            && o->res.vx <= n->max.vx + r
                            && o->res.vz >= n->min.vz - r
                            && o->res.vz <= n->max.vz + r
                            && o->res.vy >= n->max.vy
                            && n->min.vy >= o->res.vy) {
                            return n;
                        }
                    }
                }
            }
            n = n->sig10;
        } while (n != 0);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_800171E4);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 10583 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las
 * comparaciones de las regiones no se han ajustado al original. Variantes probadas: 1.
 *
 * Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con
 * mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la
 * pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. Devuelve el candidato elegido (el de menor
 * distancia, con preferencia por los marcados con 8) o 0.
 */
Objeto* func_80017478(Objeto* a, SVECTOR* v, ConsultaSondeo* w, u32 mascara)
{
    Objeto* mejor;
    u32 mejor_d;
    s32 i;
    s32 t2;
    s32 hits;
    s32 k;
    s32 len1;
    s32 len2;
    s16 salida_x;
    s16 salida_z;
    s32 salida_y;
    u16 lista;
    SVECTOR* dif;

    mejor = 0;
    mejor_d = 0xFFFFFFFF;
    dif = &w->dif;
    salida_y = 0;
    lista = 0;
    w->destino.vx = a->param.trans.vx + v->vx;
    w->destino.vy = a->param.trans.vy + v->vy;
    w->destino.vz = a->param.trans.vz + v->vz;
    w->s86 = 0;
    w->s84 = 0;
    w->actual = D_80069630;
    for (;;) {
        if (lista == 0 && mejor != 0 && (mejor->flags08 & 0x20000) == 0 && w->actual == 0) {
            w->actual = D_80069630;
            lista = 1;
        } else if (w->actual == 0) {
            break;
        }
        if (lista != 0 && (w->actual->flags08 & 0x20000) == 0) {
            goto siguiente;
        }
        if ((w->actual->flags08 & mascara) == 0 || w->actual->s2A != 2 || a == w->actual
            || a->p70 == w->actual || a->p6C == w->actual || w->actual->p70 == a
            || w->actual->p6C == a || w->actual->p70 == (Objeto*)D_80069698) {
            goto siguiente;
        }
        w->cadena = w->actual->p70;
        if (w->cadena != 0) {
            do {
                if (w->cadena == a) {
                    break;
                }
                w->cadena = w->cadena->p70;
            } while (w->cadena != 0);
            if (w->cadena != 0) {
                goto siguiente;
            }
        }
        GEO_CARGAR_WH(&w->actual->min);
        GEO_OR_WH(&w->actual->max);
        GEO_GUARDAR_1W_T1(&w->caja);
        if (w->caja == 0) {
            goto siguiente;
        }
        GEO_CARGAR_W(&w->destino);
        GEO_RESTAR_W(&w->actual->param.trans);
        GEO_GUARDAR_H_T4(dif);
        GEO_NORMA2_XZ(dif, &w->dist2);
        t2 = U16_2E(a) + U16_2E(w->actual) + w->actual->s20 + a->s20;
        t2 = t2 * t2;
        if ((u32)t2 < w->dist2) {
            goto siguiente;
        }
        w->a = a;
        w->b = w->actual;
        GEO_CARGAR_W(&a->param.trans);
        GEO_RESTAR_W(&w->b->param.trans);
        GEO_GUARDAR_H_T4(dif);
        w->dif.vy = w->dif.vy + v->vy;
        w->radio = w->b->s20;
        GEO_COMPLEMENTO(&w->b->param.giro.rotate);
        GEO_GUARDAR_H_T1(&w->rot);
        RotMatrixZYX(&w->rot, &w->m);
        ApplyMatrixSV(&w->m, dif, &w->res);
        ApplyMatrixSV(&w->m, v, &w->sal);
        w->caja = w->actual->max.vy - w->res.vy;
        if (!(w->b->max.vy < w->res.vy + w->a->min.vy + v->vy)) {
            goto siguiente;
        }
        if (w->b->min.vy < w->res.vy + w->a->max.vy + v->vy) {
            goto siguiente;
        }
        w->p[0].vx = (w->b->max.vx >> 1) + (w->b->min.vx >> 1);
        w->p[0].vz = (w->b->max.vz >> 1) + (w->b->min.vz >> 1);
        w->ang = ratan2(w->res.vx - w->p[0].vx, w->res.vz - w->p[0].vz);
        if (w->ang >= 0) {
            w->angs[0] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
            w->angs[1] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
        } else {
            w->angs[2] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
            w->angs[3] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
        }
        w->p[0].vx = w->p[2].vx = w->a->min.vx - w->a->s20;
        w->p[1].vx = w->p[3].vx = w->a->max.vx + w->a->s20;
        w->p[0].vz = w->p[1].vz = w->a->max.vz + w->a->s20;
        w->p[2].vz = w->p[3].vz = w->a->min.vz - w->a->s20;
        w->p[4].vx = w->p[4].vy = w->p[4].vz = 0;
        w->p[0].vy = w->p[1].vy = w->p[2].vy = w->p[3].vy = 0;
        RotMatrix(&w->a->param.giro.rotate, &w->m2);
        gte_SetRotMatrix(&w->m2);
        w->pt = w->p;
        for (i = 0; i < 5; i++) {
            gte_ldv0(w->pt);
            gte_rtv0();
            gte_stsv(w->pt);
            w->pt++;
        }
        gte_SetRotMatrix(&w->m);
        w->pt = w->p;
        hits = 0;
        for (i = 0; i < 5; i++, w->pt++) {
            w->pt->vx += w->dif.vx;
            w->pt->vz += w->dif.vz;
            gte_ldv0(w->pt);
            gte_rtv0();
            gte_stsv(w->pt);
            if (w->ang >= 0) {
                if (w->ang < w->angs[0]) {
                    if (w->b->max.vz + w->radio < w->pt->vz + w->sal.vz) {
                        continue;
                    }
                    if (w->b->max.vx + w->radio < w->pt->vx + w->sal.vx) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vz = w->b->max.vz + w->radio - w->pt->vz;
                    }
                } else if (w->ang < w->angs[1]) {
                    if (w->b->max.vx + w->radio < w->pt->vx + w->sal.vx) {
                        continue;
                    }
                    if (w->b->max.vz + w->radio < w->pt->vz + w->sal.vz) {
                        continue;
                    }
                    if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vx = w->b->max.vx + w->radio - w->pt->vx;
                    }
                } else {
                    if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                        continue;
                    }
                    if (w->b->max.vx + w->radio < w->pt->vx + w->sal.vx) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vz = w->b->min.vz - w->radio - w->pt->vz;
                    }
                }
            } else if (w->angs[2] < w->ang) {
                if (w->b->max.vz + w->radio < w->pt->vz + w->sal.vz) {
                    continue;
                }
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vz = w->b->max.vz + w->radio - w->pt->vz;
                }
            } else if (w->angs[3] < w->ang) {
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if (w->b->max.vz + w->radio < w->pt->vz + w->sal.vz) {
                    continue;
                }
                if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vx = w->b->min.vx - w->radio - w->pt->vx;
                }
            } else {
                if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vz = w->b->min.vz - w->radio - w->pt->vz;
                }
            }
            hits++;
        }
        if (hits == 0) {
            D_80069D18[0].z = w->p[0].vz;
            D_80069D18[0].x = w->p[0].vx;
            D_80069D18[1].z = w->p[1].vz;
            D_80069D18[1].x = w->p[1].vx;
            D_80069D18[2].z = w->p[2].vz;
            D_80069D18[2].x = w->p[2].vx;
            D_80069D18[3].z = w->p[3].vz;
            D_80069D18[3].x = w->p[3].vx;
            D_80069380 = -1;
            w->angs[0] = 0;
            while (w->angs[0] < 4) {
                if (w->angs[0] == 0) {
                    D_80069D18[4].x = w->b->max.vx + w->radio;
                    D_80069D18[4].z = w->b->max.vz + w->radio;
                } else if (w->angs[0] == 1) {
                    D_80069D18[4].x = w->b->max.vx + w->radio;
                    D_80069D18[4].z = w->b->min.vz - w->radio;
                } else if (w->angs[0] == 2) {
                    D_80069D18[4].x = w->b->min.vx - w->radio;
                    D_80069D18[4].z = w->b->min.vz - w->radio;
                } else if (w->angs[0] == 3) {
                    D_80069D18[4].x = w->b->min.vx - w->radio;
                    D_80069D18[4].z = w->b->max.vz + w->radio;
                }
                D_80069380 = 0x7FFFFFFF;
                gte_NormalClip(*(u32*)&D_80069D18[0], *(u32*)&D_80069D18[1], *(u32*)&D_80069D18[4], &k);
                if (k < D_80069380) {
                    D_80069380 = k;
                    t2 = 0;
                }
                gte_NormalClip(*(u32*)&D_80069D18[1], *(u32*)&D_80069D18[3], *(u32*)&D_80069D18[4], &k);
                if (k < D_80069380) {
                    D_80069380 = k;
                    t2 = 1;
                }
                gte_NormalClip(*(u32*)&D_80069D18[3], *(u32*)&D_80069D18[2], *(u32*)&D_80069D18[4], &k);
                if (k < D_80069380) {
                    D_80069380 = k;
                    t2 = 2;
                }
                gte_NormalClip(*(u32*)&D_80069D18[2], *(u32*)&D_80069D18[0], *(u32*)&D_80069D18[4], &k);
                if (k < D_80069380) {
                    D_80069380 = k;
                    t2 = 3;
                }
                w->angs[0]++;
                if (D_80069380 >= 0) {
                    break;
                }
            }
            if (D_80069380 > 0) {
                if (t2 == 0) {
                    w->e_x = D_80069D18[1].x - D_80069D18[0].x;
                    w->e_z = D_80069D18[1].z - D_80069D18[0].z;
                    D_80069D08.vx = D_80069D18[4].x - D_80069D18[0].x;
                    D_80069D08.vz = D_80069D18[4].z - D_80069D18[0].z;
                } else if (t2 == 1) {
                    w->e_x = D_80069D18[3].x - D_80069D18[1].x;
                    w->e_z = D_80069D18[3].z - D_80069D18[1].z;
                    D_80069D08.vx = D_80069D18[4].x - D_80069D18[1].x;
                    D_80069D08.vz = D_80069D18[4].z - D_80069D18[1].z;
                } else if (t2 == 2) {
                    w->e_x = D_80069D18[2].x - D_80069D18[3].x;
                    w->e_z = D_80069D18[2].z - D_80069D18[3].z;
                    D_80069D08.vx = D_80069D18[4].x - D_80069D18[3].x;
                    D_80069D08.vz = D_80069D18[4].z - D_80069D18[3].z;
                } else if (t2 == 3) {
                    w->e_x = D_80069D18[0].x - D_80069D18[2].x;
                    w->e_z = D_80069D18[0].z - D_80069D18[2].z;
                    D_80069D08.vx = D_80069D18[4].x - D_80069D18[2].x;
                    D_80069D08.vz = D_80069D18[4].z - D_80069D18[2].z;
                }
                len1 = SquareRoot0(w->e_x * w->e_x + w->e_z * w->e_z);
                len2 = SquareRoot0(D_80069D08.vx * D_80069D08.vx + D_80069D08.vz * D_80069D08.vz);
                D_80069C08.vx = (w->e_x << 12) / len1;
                D_80069C08.vz = (w->e_z << 12) / len1;
                D_80069C08.vx = (D_80069C08.vx * len2) >> 12;
                D_80069C08.vz = (D_80069C08.vz * len2) >> 12;
                hits = 1;
                w->sal.vx = w->sal.vx - (D_80069C08.vx - D_80069D08.vx);
                w->sal.vz = w->sal.vz - (D_80069C08.vz - D_80069D08.vz);
            } else {
                hits = 0;
            }
        }
        if (hits == 0) {
            goto siguiente;
        }
        RotMatrix(&w->b->param.giro.rotate, &w->m);
        ApplyMatrixSV(&w->m, &w->sal, &w->res);
        if (mejor != 0 && (w->b->flags08 & 0x20000) == 0) {
            salida_x = (w->res.vx + v->vx) >> 1;
            salida_z = (w->res.vz + v->vz) >> 1;
            v->vx = salida_x;
            v->vz = salida_z;
        } else {
            salida_x = w->res.vx;
            v->vx = salida_x;
            salida_z = w->res.vz;
            v->vz = salida_z;
        }
        if (w->dist2 < mejor_d || (w->actual->flags08 & 8) != 0) {
            /* sigue a la seleccion */
        } else if (mejor == 0 || (mejor->flags08 & 8) == 0) {
            goto siguiente;
        }
        if (mejor != 0 && (mejor->flags08 & 0x20000) != 0 && (w->actual->flags08 & 0x20000) == 0) {
            goto siguiente;
        }
        if ((w->actual->flags08 & 8) != 0) {
            if (mejor != 0 && (mejor->flags08 & 8) != 0) {
                if (!(w->dist2 < mejor_d)) {
                    goto siguiente;
                }
            }
            mejor = w->actual;
            mejor_d = w->dist2;
            salida_y = w->caja;
        } else {
            if (mejor != 0) {
                if ((mejor->flags08 & 8) != 0) {
                    goto siguiente;
                }
                if ((mejor->flags08 & 0x20000) != 0 && (w->actual->flags08 & 0x2000000) != 0) {
                    goto siguiente;
                }
            }
            mejor = w->actual;
            mejor_d = w->dist2;
            salida_y = w->caja;
        }
siguiente:
        w->actual = w->actual->sig10;
    }
    if (mejor != 0) {
        v->vx = salida_x;
        v->vy = salida_y;
        v->vz = salida_z;
    }
    return mejor;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80017478);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 2420 con la configuracion versionada (g = 8 del archivo). Reparto de registros del prologo (el original usa a0 como
 * copia de la posicion de a) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Variantes probadas: 3.
 *
 * Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el
 * cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca.
 */
s32 func_80018664(Objeto* a, Objeto* b, ConsultaSondeo* w)
{
    s32 i;
    SVECTOR* dif;
    MATRIX* m2;
    /* El marco del original reserva 8 bytes de locales que ninguna sentencia toca. */
    SVECTOR reserva;


    GEO_CARGAR_WH(&b->min);
    GEO_OR_WH(&b->max);
    GEO_GUARDAR_1W_T1(&w->caja);
    if (w->caja == 0) {
        return 0;
    }
    GEO_CARGAR_W(&a->param.trans);
    GEO_RESTAR_W(&b->param.trans);
    dif = &w->dif;
    GEO_GUARDAR_H_T4(dif);
    w->a = a;
    w->b = b;
    GEO_CARGAR_W(&w->a->param.trans);
    GEO_RESTAR_W(&w->b->param.trans);
    GEO_GUARDAR_H_T4(dif);
    w->radio = w->b->s20;
    GEO_COMPLEMENTO(&w->b->param.giro.rotate);
    GEO_GUARDAR_H_T1(&w->rot);
    RotMatrixZYX(&w->rot, &w->m);
    ApplyMatrixSV(&w->m, dif, &w->res);
    w->p[0].vx = (w->b->max.vx >> 1) + (w->b->min.vx >> 1);
    w->p[0].vz = (w->b->max.vz >> 1) + (w->b->min.vz >> 1);
    w->ang = ratan2(w->res.vx - w->p[0].vx, w->res.vz - w->p[0].vz);
    if (w->ang >= 0) {
        w->angs[0] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
        w->angs[1] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
    } else {
        w->angs[2] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
        w->angs[3] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
    }
    w->p[0].vx = w->p[2].vx = w->a->min.vx - w->a->s20;
    w->p[1].vx = w->p[3].vx = w->a->max.vx + w->a->s20;
    w->p[0].vz = w->p[1].vz = w->a->max.vz + w->a->s20;
    w->p[2].vz = w->p[3].vz = w->a->min.vz - w->a->s20;
    w->p[4].vx = w->p[4].vy = w->p[4].vz = 0;
    w->p[0].vy = w->p[1].vy = w->p[2].vy = w->p[3].vy = 0;
    m2 = &w->m2;
    RotMatrix(&w->a->param.giro.rotate, m2);
    gte_SetRotMatrix(m2);
    w->pt = w->p;
    for (i = 0; i < 4; i++) {
        gte_ldv0(w->pt);
        gte_rtv0();
        gte_stsv(w->pt);
        w->pt++;
    }
    gte_SetRotMatrix(&w->m);
    w->pt = w->p;
    for (i = 0; i < 5; i++, w->pt++) {
        w->pt->vx += w->dif.vx;
        w->pt->vz += w->dif.vz;
        gte_ldv0(w->pt);
        gte_rtv0();
        gte_stsv(w->pt);
        if (w->ang >= 0) {
            if (w->ang < w->angs[0]) {
                if (w->b->max.vz + w->radio < w->pt->vz) {
                    continue;
                }
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
            } else if (w->ang < w->angs[1]) {
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
                if (w->b->max.vz + w->radio < w->pt->vz) {
                    continue;
                }
                if (w->pt->vz < w->b->min.vz - w->radio) {
                    continue;
                }
            } else {
                if (w->pt->vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
            }
        } else if (w->angs[2] < w->ang) {
            if (w->b->max.vz + w->radio < w->pt->vz) {
                continue;
            }
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
        } else if (w->angs[3] < w->ang) {
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
            if (w->b->max.vz + w->radio < w->pt->vz) {
                continue;
            }
            if (w->pt->vz < w->b->min.vz - w->radio) {
                continue;
            }
        } else {
            if (w->pt->vz < w->b->min.vz - w->radio) {
                continue;
            }
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
        }
        return 1;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018664);
#endif

/*
 * Clasifica el punto del jugador respecto de la caja del objeto a en el eje z de su sistema
 * local: 1 si queda por debajo del minimo, 2 si por encima del maximo y 0 si dentro.
 */
s32 func_80018C68(Objeto* a, ConsultaMatriz* o)
{
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    /* 0x80018CC0..0x80018CD4: lw v0,%lo(D_80069698) ; addiu v0,v0,0xE4 ; lw 0x0/0x4/0x8 de esa base: tres s32 consecutivos que la macro lee como VECTOR. */
    GEO_CARGAR_W(&D_80069698->param.trans);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_IDENTIDAD(o);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (o->res.vz >= a->min.vz) {
        return (a->max.vz < o->res.vz) << 1;
    }
    return 1;
}

/*
 * Prueba si el punto p cae dentro del volumen del objeto a ampliado por su radio. Descarta antes
 * por distancia al cuadrado en el plano.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 108 con la configuracion versionada (g = 8 del archivo). El area de trabajo y el puntero a la diferencia intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6. */
s32 func_80018D98(Objeto* a, VECTOR* p, ConsultaVolumen* o)
{
    GEO_CARGAR_W(p);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    o->radio = a->s20;
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    GEO_IDENTIDAD(&o->m);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (a->min.vx - o->radio < o->res.vx
        && o->res.vx < a->max.vx + o->radio
        && a->min.vz - o->radio < o->res.vz
        && o->res.vz < a->max.vz + o->radio
        && o->res.vy < a->min.vy
        && a->max.vy < o->res.vy) {
        return 1;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018D98);
#endif

/*
 * Igual que func_80018D98 pero la posicion a probar es la del objeto b y la caja de b
 * (extensiones en y) se suma al margen vertical.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 108 con la configuracion versionada (g = 8 del archivo). El area de trabajo y el puntero a la diferencia intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6. */
s32 func_80018F80(Objeto* a, Objeto* b, ConsultaVolumen* o)
{
    GEO_CARGAR_W(&b->param.trans);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    o->radio = a->s20;
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    GEO_IDENTIDAD(&o->m);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (a->min.vx - o->radio < o->res.vx
        && o->res.vx < a->max.vx + o->radio
        && a->min.vz - o->radio < o->res.vz
        && o->res.vz < a->max.vz + o->radio
        && o->res.vy + b->max.vy < a->min.vy
        && a->max.vy < o->res.vy + b->min.vy) {
        return 1;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018F80);
#endif

/*
 * Recorre la lista de nodos de plano y devuelve el primero que contiene el punto p visto desde
 * el objeto a: pasa al sistema local del nodo (con rotacion si el bit 0 de sus indicadores esta
 * apagado) y acota x y z por sus limites; en y lo acota por el margen del objeto.
 * Con g = 8 (config/opciones_compilacion.toml) el puntero global se carga directamente en $s0;
 * con -G0 la parte alta iria a otro registro (205).
 */
NodoVolumen* func_80019180(Objeto* a, VECTOR* p, ConsultaPlano* o)
{
    NodoVolumen* n;
    s32 z;
    SVECTOR* rot;
    SVECTOR* dif;

    n = D_80069580;
    if (n != 0) {
        dif = &o->dif;
        rot = &o->rot;
        do {
            if ((n->indicadores & 2) || n->etiqueta == (s16)a->w26) {
                GEO_CARGAR_W(p);
                GEO_RESTAR_W(&n->pos);
                GEO_GUARDAR_H_T4(dif);
                if (o->dif.vy + a->max.vy <= 0 && o->dif.vy >= n->lim_y) {
                    if (n->indicadores & 1) {
                        if (o->dif.vx < 0 || n->lim_x < o->dif.vx) {
                            goto siguiente;
                        }
                        z = o->dif.vz;
                    } else {
                        GEO_COMPLEMENTO(&n->rot);
                        GEO_GUARDAR_H_T1(rot);
                        RotMatrixZYX(rot, &o->m);
                        ApplyMatrixSV(&o->m, dif, &o->res);
                        if (o->res.vx < 0 || n->lim_x < o->res.vx) {
                            goto siguiente;
                        }
                        z = o->res.vz;
                    }
                    if (z >= 0 && n->lim_z >= z) {
                        return n;
                    }
                }
            }
siguiente:
            n = n->sig;
        } while (n != 0);
    }
    return 0;
}
