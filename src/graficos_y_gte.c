#include "geometria.h"

/* Cabeza de la lista de objetos solidos del nivel (enlace en +0x10). */
extern ObjetoVolumen* D_80069630;
/* Objeto del jugador. */
extern ObjetoVolumen* D_80069698;
/* Cabeza de la lista de nodos de plano (enlace en +0). */
extern NodoVolumen* D_80069580;

/*
 * Busca el primer objeto solido cuyo volumen contiene a la caja del objeto a: el candidato se
 * lleva al sistema local del otro objeto con la inversa de sus angulos y se compara con su caja
 * ampliada por el radio. mascara filtra por indicadores; o es el area de trabajo.
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
 */
#ifdef NON_MATCHING
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
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80016ED0);
#endif

/*
 * Variante con el punto a probar y una segunda mascara de exclusion como argumentos y el area
 * de trabajo como quinto argumento (en pila); el radio se ensancha 4 unidades.
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

INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018664);

/*
 * Clasifica el punto del jugador respecto de la caja del objeto a en el eje z de su sistema
 * local: 1 si queda por debajo del minimo, 2 si por encima del maximo y 0 si dentro.
 */
s32 func_80018C68(ObjetoVolumen* a, ConsultaMatriz* o)
{
    GEO_COMPLEMENTO(&a->rot);
    GEO_GUARDAR_H_T1(&o->rot);
    GEO_CARGAR_W(&D_80069698->pos);
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
#ifdef NON_MATCHING
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
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018D98);
#endif

/*
 * Igual que func_80018D98 pero la posicion a probar es la del objeto b y la caja de b
 * (extensiones en y) se suma al margen vertical.
 */
#ifdef NON_MATCHING
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
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80018F80);
#endif

/*
 * Recorre la lista de nodos de plano y devuelve el primero que contiene el punto p visto desde
 * el objeto a: pasa al sistema local del nodo (con rotacion si el bit 0 de sus indicadores esta
 * apagado) y acota x y z por sus limites; en y lo acota por el margen del objeto.
 */
#ifdef NON_MATCHING
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
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80019180);
#endif
