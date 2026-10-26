#include "geometria.h"
#include "globales.h"
#include "gte.h"


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
    u8 pad70[0x78 - 0x70];
    u32 caja;
    s32 ang;
    s32 radio;
    s16 s84;
    s16 s86;
    ObjetoVolumen* actual;
    ObjetoVolumen* cadena;
    ObjetoVolumen* a;
    ObjetoVolumen* b;
    SVECTOR p[5];
    SVECTOR* pt;
    u32 dist2;
    s16 angs[4];
} ConsultaSondeo;

/* Cabeza de la lista de nodos de plano (enlace en +0). */
extern NodoVolumen* D_80069580;

/*
 * Busca el primer objeto solido cuyo volumen contiene a la caja del objeto a: el candidato se
 * lleva al sistema local del otro objeto con la inversa de sus angulos y se compara con su caja
 * ampliada por el radio. mascara filtra por indicadores; o es el area de trabajo.
 *
 * NON_MATCHING: puntuacion 456 (el archivo se compila con g = 8; 456 tambien con -G0).
 * Diferencia: el original no saca &o->m del bucle y el compilador si.
 */
#ifdef NON_MATCHING
ObjetoVolumen* func_80016C0C(ObjetoVolumen* a, u32 mascara, ConsultaVolumen* o)
{
    SVECTOR* dif;
    SVECTOR* rot;

    o->actual = D_80069630;
    if (o->actual != 0) {
        dif = &o->dif;
        rot = &o->rot;
        do {
            if ((o->actual->indicadores & mascara) && o->actual->tipo == 2 && a != o->actual
                && a->rel2 != o->actual && a->rel1 != o->actual && o->actual->rel2 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->caja);
                if (o->caja != 0) {
                    GEO_CARGAR_W(&a->pos);
                    GEO_RESTAR_W(&o->actual->pos);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &o->dist2);
                    if (o->actual->alcance2 >= o->dist2) {
                        o->radio = o->actual->radio;
                        GEO_COMPLEMENTO(&o->actual->rot);
                        GEO_GUARDAR_H_T1(rot);
                        RotMatrixZYX(rot, &o->m);
                        ApplyMatrixSV(&o->m, dif, &o->res);
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
            o->actual = o->actual->sig;
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
ObjetoVolumen* func_80016ED0(ObjetoVolumen* a, u32 mascara, ConsultaCaja* o)
{
    GEO_COMPLEMENTO(&a->rot);
    GEO_GUARDAR_H_T1(&o->rot);
    RotMatrixZYX(&o->rot, &o->m);
    GEO_CARGAR_W(&a->pos);
    GEO_GUARDAR_W_T1(&o->pos);
    GEO_CARGAR_WH(&a->min);
    GEO_GUARDAR_WH(&o->min);
    GEO_CARGAR_WH(&a->max);
    GEO_GUARDAR_WH(&o->max);
    o->radio = a->radio;
    o->actual = D_80069630;
    if (o->actual != 0) {
        do {
            if ((o->actual->indicadores & mascara) && o->actual->tipo == 2 && a != o->actual
                && a->rel2 != o->actual && a->rel1 != o->actual && o->actual->rel2 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->tmp);
                if (o->tmp != 0) {
                    GEO_CARGAR_W(&o->actual->pos);
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
            o->actual = o->actual->sig;
        } while (o->actual != 0);
    }
    return 0;
}

/*
 * Variante con el punto a probar y una segunda mascara de exclusion como argumentos y el area
 * de trabajo como quinto argumento (en pila); el radio se ensancha 4 unidades.
 *
 * NON_MATCHING: puntuacion 408 (el archivo se compila con g = 8; 603 con -G0). Misma diferencia
 * que func_80016C0C con &o->m.
 */
#ifdef NON_MATCHING
ObjetoVolumen* func_800171E4(ObjetoVolumen* a, VECTOR* p, u32 mascara, u32 excluir, ConsultaVolumen* o)
{
    ObjetoVolumen* n;
    s32 r;
    SVECTOR* dif;
    SVECTOR* rot;

    n = D_80069630;
    if (n != 0) {
        dif = &o->dif;
        rot = &o->rot;
        do {
            if ((n->indicadores & mascara) && n->tipo == 2 && n != a && !(n->indicadores & excluir)) {
                GEO_CARGAR_WH(&n->min);
                GEO_OR_WH(&n->max);
                GEO_GUARDAR_1W_T1(&o->caja);
                if (o->caja != 0) {
                    GEO_CARGAR_W(p);
                    GEO_RESTAR_W(&n->pos);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &o->dist2);
                    if (o->dist2 <= n->alcance2) {
                        r = n->radio + 4;
                        GEO_COMPLEMENTO(&n->rot);
                        GEO_GUARDAR_H_T1(rot);
                        RotMatrixZYX(rot, &o->m);
                        ApplyMatrixSV(&o->m, dif, &o->res);
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
            n = n->sig;
        } while (n != 0);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_800171E4);
#endif

INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80017478);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 2420 con la configuracion versionada (g = 8 del archivo). Reparto de registros del prologo (el original usa a0 como
 * copia de la posicion de a) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Variantes probadas: 3.
 *
 * Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el
 * cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca.
 */
s32 func_80018664(ObjetoVolumen* a, ObjetoVolumen* b, ConsultaSondeo* w)
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
    GEO_CARGAR_W(&a->pos);
    GEO_RESTAR_W(&b->pos);
    dif = &w->dif;
    GEO_GUARDAR_H_T4(dif);
    w->a = a;
    w->b = b;
    GEO_CARGAR_W(&w->a->pos);
    GEO_RESTAR_W(&w->b->pos);
    GEO_GUARDAR_H_T4(dif);
    w->radio = w->b->radio;
    GEO_COMPLEMENTO(&w->b->rot);
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
    w->p[0].vx = w->p[2].vx = w->a->min.vx - w->a->radio;
    w->p[1].vx = w->p[3].vx = w->a->max.vx + w->a->radio;
    w->p[0].vz = w->p[1].vz = w->a->max.vz + w->a->radio;
    w->p[2].vz = w->p[3].vz = w->a->min.vz - w->a->radio;
    w->p[4].vx = w->p[4].vy = w->p[4].vz = 0;
    w->p[0].vy = w->p[1].vy = w->p[2].vy = w->p[3].vy = 0;
    m2 = &w->m2;
    RotMatrix(&w->a->rot, m2);
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
s32 func_80018C68(ObjetoVolumen* a, ConsultaMatriz* o)
{
    GEO_COMPLEMENTO(&a->rot);
    GEO_GUARDAR_H_T1(&o->rot);
    /* 0x80018CC0..0x80018CD4: lw v0,%lo(D_80069698) ; addiu v0,v0,0xE4 ; lw 0x0/0x4/0x8 de esa base: tres s32 consecutivos que la macro lee como VECTOR. */
    GEO_CARGAR_W((VECTOR*)&D_80069698->xE4);
    GEO_RESTAR_W(&a->pos);
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
s32 func_80018D98(ObjetoVolumen* a, VECTOR* p, ConsultaVolumen* o)
{
    GEO_CARGAR_W(p);
    GEO_RESTAR_W(&a->pos);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    o->radio = a->radio;
    GEO_COMPLEMENTO(&a->rot);
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

/*
 * Igual que func_80018D98 pero la posicion a probar es la del objeto b y la caja de b
 * (extensiones en y) se suma al margen vertical.
 */
s32 func_80018F80(ObjetoVolumen* a, ObjetoVolumen* b, ConsultaVolumen* o)
{
    GEO_CARGAR_W(&b->pos);
    GEO_RESTAR_W(&a->pos);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    o->radio = a->radio;
    GEO_COMPLEMENTO(&a->rot);
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

/*
 * Recorre la lista de nodos de plano y devuelve el primero que contiene el punto p visto desde
 * el objeto a: pasa al sistema local del nodo (con rotacion si el bit 0 de sus indicadores esta
 * apagado) y acota x y z por sus limites; en y lo acota por el margen del objeto.
 * Con g = 8 (config/opciones_compilacion.toml) el puntero global se carga directamente en $s0;
 * con -G0 la parte alta iria a otro registro (205).
 */
NodoVolumen* func_80019180(ObjetoVolumen* a, VECTOR* p, ConsultaPlano* o)
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
            if ((n->indicadores & 2) || n->etiqueta == a->etiqueta) {
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
