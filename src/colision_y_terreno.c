#include "geometria.h"
#include "globales.h"

/* Cabezas de lista por grupo: la primera zona de cada grupo de la tabla cargada. */
extern ZonaColision* D_80069C18[];

/*
 * La cuenta de zonas y el puntero a la tabla viven en $gp+0x58 y $gp+0x5C; el original los
 * accede con desplazamiento fijo sobre $gp aunque el archivo se compila con -G0. Depende de que
 * nada reasigne $gp (el arranque lo fija a 0x80069320 y no cambia).
 */

/*
 * Carga la tabla de zonas de un bloque: [cuenta][zonas de 0x44 bytes]. Registra cuenta y puntero,
 * deja en la tabla de cabezas la primera zona de cada grupo (un grupo fuera de 0..59 es un
 * error irrecuperable y se queda en un bucle infinito) y convierte los dos desplazamientos de
 * cada zona en direcciones sumando la base del bloque.
 */
void func_80019364(s32* a0)
{
    ZonaColision* p;
    ZonaColision* rec;
    ZonaColision** tab;
    s16 i;
    s32 n;

    tab = D_80069C18;
    rec = (ZonaColision*)(a0 + 1);
    *(s32*)(base_gp + 0x58) = *a0;
    *(ZonaColision**)(base_gp + 0x5C) = rec;
    i = 0;
    do {
        tab[i] = 0;
        i++;
    } while (i < 60);
    p = rec;
    i = 0;
    if (*(s32*)(base_gp + 0x58) > 0) {
        n = *(s32*)(base_gp + 0x58);
        do {
            if (p->grupo >= 60) {
                for (;;) { }
            }
            if (tab[p->grupo] == 0) {
                tab[p->grupo] = p;
            }
            i++;
            p++;
        } while (i < n);
    }
    p = rec;
    i = 0;
    n = *(s32*)(base_gp + 0x58);
    if (n > 0) {
        do {
            i++;
            p->baldosas = (u16*)((s32)p->baldosas + (s32)a0);
            p->subceldas = (u8*)((s32)p->subceldas + (s32)a0);
            p++;
        } while (i < n);
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 2135 con la configuracion versionada (g = 0 del archivo). El reparto de
 * registros coincide con el original; difieren el orden de planificacion en los avances por
 * subcelda y por baldosa, el cierre compartido de resultados y una constante de indice que el
 * original no pliega. diff solo compara las primeras 1024 instrucciones (completa: 7010).
 */
/*
 * Copia los 0x1C primeros bytes de una zona (todo salvo los dos punteros de datos) al historial
 * del barrido; la zona original es de solo lectura.
 */
#define COPIAR_ZONA(d, s) \
    { \
        (d)->grupo = grupo; \
        (d)->pendiente = (s)->pendiente; \
        (d)->columnas = (s)->columnas; \
        (d)->pad06 = (s)->pad06; \
        (d)->ancho_x = (s)->ancho_x; \
        (d)->ancho_z = (s)->ancho_z; \
        (d)->x = (s)->x; \
        (d)->z = (s)->z; \
        (d)->y_max = (s)->y_max; \
        (d)->y_min = (s)->y_min; \
    }

/* Al llegar a 15 entradas el historial conserva las cuatro ultimas y vuelve al indice 3. */
#define COMPACTAR_HISTORIAL \
    { \
        w->celdas[0] = w->celdas[w->n - 3]; \
        w->celdas[1] = w->celdas[w->n - 2]; \
        w->celdas[2] = w->celdas[w->n - 1]; \
        w->celdas[3] = w->celdas[w->n]; \
        w->zonas[0] = w->zonas[w->n - 3]; \
        w->zonas[1] = w->zonas[w->n - 2]; \
        w->zonas[2] = w->zonas[w->n - 1]; \
        w->zonas[3] = w->zonas[w->n]; \
        w->n = 3; \
    }

/* Indice de la celda previa: la anterior al indice de escritura, o la misma si es la primera. */
#define INDICE_PREVIO \
    { \
        if (w->n > 0) { \
            w->prev = w->n - 1; \
        } else { \
            w->prev = w->n; \
        } \
    }

/*
 * Cierre del barrido cuando el desplazamiento se recorrio entero: la celda final decide si el
 * resultado es un plano de transicion (0x7E) o una pendiente.
 */
#define CIERRE_COMPLETO \
    { \
        INDICE_PREVIO; \
        zona = w->zonas[w->n]; \
        if (w->celdas[w->n] == 0x7E) { \
            k = 0; \
            if (w->n < k) { \
                w->n = 0; \
            } \
            if (w->celdas[w->n - k] == 0x7E) { \
                pos[1] = zona->y_max; \
                res->clase = w->celdas[0]; \
                res->flags = 8; \
                res->pendiente = 0; \
                res->pendiente_abs = 0; \
                res->grupo = zona->grupo; \
                techo = zona->y_min; \
                ret = 1; \
                res->zona = zona; \
                res->techo = techo; \
                return ret; \
            } \
            pos[1] = zona->y_max; \
            res->clase = w->celdas[0]; \
            w->t0 = w->celdas[w->prev]; \
            if (w->t0 == 0x7E) { \
                w->t0 = 0; \
                res->flags = 8; \
            } else { \
                res->flags = 2; \
                if (w->t0 > 0) { \
                    w->t0 = -w->t0; \
                    res->flags = res->flags | 0x20; \
                } \
            } \
            w->t0 = w->t0 * zona->pendiente; \
            res->pendiente = w->t0; \
            res->pendiente_abs = w->t0; \
            res->grupo = zona->grupo; \
            techo = zona->y_min; \
            ret = 1; \
            res->zona = zona; \
            res->techo = techo; \
            return ret; \
        } \
        pos[1] = zona->y_max; \
        res->clase = w->celdas[0]; \
        w->t0 = w->celdas[w->prev]; \
        if (w->t0 == 0x7E) { \
            w->t0 = 0; \
            res->flags = 8; \
        } else { \
            res->flags = 2; \
            if (w->t0 > 0) { \
                w->t0 = -w->t0; \
            } \
        } \
        res->pendiente = w->t0 * zona->pendiente; \
        w->t0 = w->celdas[w->n]; \
        if (w->t0 > 0) { \
            w->t0 = -w->t0; \
            res->flags = res->flags | 0x20; \
        } \
        res->pendiente_abs = w->t0 * zona->pendiente; \
        res->grupo = zona->grupo; \
        techo = zona->y_min; \
        ret = 1; \
        res->zona = zona; \
        res->techo = techo; \
        return ret; \
    }

#define CIERRE_COMPLETO_XZ \
    { \
        INDICE_PREVIO; \
        zona = w->zonas[w->n]; \
        if (w->celdas[w->n] == 0x7E) { \
            k = 0; \
            if (w->n < k) { \
                w->n = 0; \
            } \
            if (w->celdas[w->n - k] == 0x7E) { \
                pos[1] = zona->y_max; \
                res->clase = w->celdas[0]; \
                res->flags = 8; \
                res->pendiente = 0; \
                res->pendiente_abs = 0; \
                res->grupo = zona->grupo; \
                techo = zona->y_min; \
                ret = 1; \
                res->zona = zona; \
                res->techo = techo; \
                return ret; \
            } \
            pos[1] = zona->y_max; \
            res->clase = w->celdas[0]; \
            w->t0 = w->celdas[w->prev]; \
            if (w->t0 == 0x7E) { \
                w->t0 = 0; \
                res->flags = 8; \
            } else { \
                res->flags = 2; \
                if (w->t0 > 0) { \
                    w->t0 = -w->t0; \
                    res->flags = res->flags | 0x20; \
                } \
            } \
            w->t0 = w->t0 * zona->pendiente; \
            res->pendiente = w->t0; \
            res->pendiente_abs = w->t0; \
            res->grupo = zona->grupo; \
            techo = zona->y_min; \
            ret = 1; \
            res->zona = zona; \
            res->techo = techo; \
            return ret; \
        } \
        pos[1] = zona->y_max; \
        res->clase = w->celdas[0]; \
        w->t0 = w->celdas[w->prev]; \
        if (w->t0 == 0x7E) { \
            w->t0 = 0; \
            res->flags = 8; \
        } else { \
            res->flags = 2; \
            if (w->t0 > 0) { \
                w->t0 = -w->t0; \
            } \
        } \
        res->pendiente = w->t0 * zona->pendiente; \
        w->t0 = w->celdas[w->n]; \
        if (w->t0 == 0x7E) { \
            res->flags = 8; \
            w->t0 = 0; \
        } else if (w->t0 > 0) { \
            w->t0 = -w->t0; \
            res->flags = res->flags | 0x20; \
        } \
        res->pendiente_abs = w->t0 * zona->pendiente; \
        res->grupo = zona->grupo; \
        techo = zona->y_min; \
        ret = 1; \
        res->zona = zona; \
        res->techo = techo; \
        return ret; \
    }

s32 func_80019474(s32* pos, s32* desp, ResultadoBaldosa* res, TrabajoRecorrido* w)
{
    ZonaColision* zona;
    ZonaColision* cur;
    u16 grupo;
    s16 c;
    s16 k = 0;
    s32 techo;
    s32 ret;
    u16 cl;
    u16 f;
    s32 dx;
    s32 dz;
    s32 px;
    s32 pz;
    s32 tx;
    s32 ty;
    s32 tz;

    if (0x1F8003FFU < (u32)w + 0x1C8) {
        for (;;) { }
    }
    GEO_CARGAR_W(pos);
    GEO_GUARDAR_W_T1(w);
    zona = func_8001BF9C((s32*)w, res->grupo);
    res->zona = zona;
    if (zona == NULL) {
        res->clase = 1;
        res->flags = 1;
        res->pendiente = 0;
        res->pendiente_abs = 0;
        res->tipo = 0;
        res->grupo = -1;
        return 0;
    }
    w->n = 0;
    w->cual = 0;
    w->prev = 0;
    w->celdas[w->n] = 0;
    cur = &w->copia[w->cual];
    w->zonas[w->n] = cur;
    grupo = zona->grupo;
    COPIAR_ZONA(cur, zona);
    GEO_CARGAR_W(w);
    GEO_GUARDAR_W_T1(&w->bx);
    GEO_CARGAR_W(w);
    GEO_GUARDAR_W_T1(&w->ax);
    if (desp != NULL) {
        dx = desp[0];
        w->dx = dx;
        dz = desp[2];
        w->dz = dz;
        if ((dx | dz) != 0) {
            if (w->dx != 0) {
                if (dz != 0) {
                    /* Caso general: avanza en x y en z a la vez. */
                    if (w->dx > 0) {
                        w->paso_x = 0x140;
                        w->celda_x = 0x28;
                        w->lin_x = (w->x / 320) * 0x140 + 0x140;
                    } else if (w->dx < 0) {
                        w->paso_x = -0x140;
                        w->celda_x = -0x28;
                        w->lin_x = (w->x / 320) * 0x140 - 1;
                    }
                    if (w->dz > 0) {
                        w->paso_z = 0x140;
                        w->celda_z = 0x28;
                        w->lin_z = (w->z / 320) * 0x140 + 0x140;
                    } else if (w->dz < 0) {
                        w->paso_z = -0x140;
                        w->celda_z = -0x28;
                        w->lin_z = (w->z / 320) * 0x140 - 1;
                    }
                    px = (w->dz << 12) / w->dx;
                    w->pend_x = px;
                    pz = (w->dx << 12) / w->dz;
                    w->pend_z = pz;
                    w->cbz_z = w->lin_z;
                    w->cbx_x = w->lin_x;
                    w->cbz_x = ((pz * (w->lin_z - w->z)) >> 12) + w->x;
                    w->cbx_z = ((px * (w->lin_x - w->x)) >> 12) + w->z;
                    do {
                        if (w->bx < cur->x || w->bx >= cur->x + cur->ancho_x
                            || w->bz < cur->z || w->bz >= cur->z + cur->ancho_z) {
                            w->aux = w->by;
                            w->by = w->y;
                            zona = func_8001BF9C(&w->bx, res->grupo);
                            if (zona == NULL) {
                                INDICE_PREVIO;
                                pos[1] = cur->y_max;
                                desp[0] = w->ax - w->x;
                                desp[2] = w->az - w->z;
                                res->clase = w->celdas[0];
                                res->flags = 2;
                                w->t0 = w->celdas[w->prev];
                                if (w->t0 == 0x7E) {
                                    w->t0 = 0;
                                } else if (w->t0 > 0) {
                                    w->t0 = -w->t0;
                                }
                                res->pendiente = w->t0 * cur->pendiente;
                                w->t0 = w->celdas[w->n];
                                if (w->t0 == 0x7E) {
                                    w->t0 = 0;
                                } else if (w->t0 > 0) {
                                    w->t0 = -w->t0;
                                    res->flags = res->flags | 0x20;
                                }
                                res->pendiente_abs = w->t0 * cur->pendiente;
                                res->grupo = grupo;
                                techo = cur->y_min;
                                ret = 0;
                                res->zona = zona;
                                res->techo = techo;
                                return ret;
                            }
                            w->cual = 1;
                            w->by = w->aux;
                            grupo = zona->grupo;
                            cur = &w->copia[w->cual];
                            COPIAR_ZONA(cur, zona);
                        }
                        w->baldosa = zona->baldosas[(w->bx - cur->x) / 320
                                                    + (w->bz - cur->z) / 320 * cur->columnas];
                        res->tipo = w->baldosa & 0xF000;
                        w->baldosa = w->baldosa & 0xFFF;
                        w->rx = w->bx % 320;
                        w->rz = w->bz % 320;
                        w->bx = w->bx - w->rx;
                        w->bz = w->bz - w->rz;
                        if (w->celda_x > 0) {
                            w->lim_x = (w->rx / 40) * 0x28 + 0x28;
                        } else {
                            w->lim_x = (w->rx / 40) * 0x28 - 1;
                        }
                        if (w->celda_z > 0) {
                            w->lim_z = (w->rz / 40) * 0x28 + 0x28;
                        } else {
                            w->lim_z = (w->rz / 40) * 0x28 - 1;
                        }
                        w->sz_z = w->lim_z;
                        w->sx_x = w->lim_x;
                        w->sz_x = ((w->pend_z * (w->lim_z - w->rz)) >> 12) + w->rx;
                        w->sx_z = ((w->pend_x * (w->lim_x - w->rx)) >> 12) + w->rz;
                        do {
                            w->n = w->n + 1;
                            w->celdas[w->n] = (s8)((u8(*)[64])zona->subceldas)[w->baldosa][w->rx / 40 + (w->rz / 40) * 8];
                            w->zonas[w->n] = cur;
                            c = w->celdas[w->n];
                            if (c == 0x7E) {
                                c = 0;
                            } else if (c > 0 && c < 0x7E) {
                                c = -c;
                            }
                            if (w->n == 0xF) {
                                COMPACTAR_HISTORIAL;
                            }
                            if ((c == 0x7F && w->n >= 2)
                                || cur->y_max + c * cur->pendiente - w->y < -0x64) {
                                if (w->n > 0) {
                                    w->n = w->n - 1;
                                }
                                zona = w->zonas[w->n];
                                pos[1] = zona->y_max;
                                w->bx = w->ax - w->x;
                                w->bz = w->az - w->z;
                                if (w->dx > 0) {
                                    if (w->bx < w->dx) {
                                        w->dx = w->bx;
                                    }
                                } else {
                                    if (w->dx < w->bx) {
                                        w->dx = w->bx;
                                    }
                                }
                                if (w->dz > 0) {
                                    if (w->bz < w->dz) {
                                        w->dz = w->bz;
                                    }
                                } else {
                                    if (w->dz < w->bz) {
                                        w->dz = w->bz;
                                    }
                                }
                                desp[0] = w->dx;
                                desp[2] = w->dz;
                                res->clase = w->celdas[0];
                                if (w->n == 0xE) {
                                    res->flags = 2;
                                } else {
                                    res->flags = 0x16;
                                }
                                w->t0 = w->celdas[w->n];
                                if (w->t0 == 0x7E) {
                                    w->t0 = 0;
                                    res->flags = 0x1C;
                                } else if (w->t0 > 0) {
                                    w->t0 = -w->t0;
                                    res->flags = res->flags | 0x20;
                                }
                                w->t0 = w->t0 * zona->pendiente;
                                res->pendiente = w->t0;
                                res->pendiente_abs = w->t0;
                                res->grupo = zona->grupo;
                                techo = zona->y_min;
                                ret = 1;
                                res->zona = zona;
                                res->techo = techo;
                                return ret;
                            }
                            w->ax = w->rx + w->bx;
                            w->dsz_x = w->rx - w->sz_x;
                            w->az = w->rz + w->bz;
                            w->ant_x = w->acc_x;
                            w->dsz_z = w->rz - w->sz_z;
                            w->ant_z = w->acc_z;
                            w->acc_x = w->rx + w->bx - w->x;
                            w->acc_z = w->rz + w->bz - w->z;
                            w->dsx_x = w->rx - w->sx_x;
                            w->dsx_z = w->rz - w->sx_z;
                            w->d_sz = SquareRoot0(w->dsz_x * w->dsz_x + w->dsz_z * w->dsz_z);
                            w->d_sx = SquareRoot0(w->dsx_x * w->dsx_x + w->dsx_z * w->dsx_z);
                            if (w->d_sz < w->d_sx) {
                                if (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z) {
                                    tx = w->sz_x;
                                    ty = w->sz_y;
                                    tz = w->sz_z;
                                    w->aux = ty;
                                    w->rz = tz;
                                    w->sz_z = w->lim_z = w->lim_z + w->celda_z;
                                    w->sz_x = tx + ((w->pend_z * w->celda_z) >> 12);
                                    w->rx = tx;
                                } else {
                                    w->acc_x = w->dx;
                                }
                            } else {
                                if (w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x) {
                                    tx = w->sx_x;
                                    ty = w->sx_y;
                                    tz = w->sx_z;
                                    w->aux = ty;
                                    w->rz = tz;
                                    w->sx_x = w->lim_x = w->lim_x + w->celda_x;
                                    w->sx_z = tz + ((w->pend_x * w->celda_x) >> 12);
                                    w->rx = tx;
                                } else {
                                    w->acc_z = w->dz;
                                }
                            }
                            w->t0 = w->x + w->dx;
                            w->t2 = w->rx + w->bx;
                            w->t1 = w->z + w->dz;
                            w->t3 = w->rz + w->bz;
                            if (w->dx < 0) {
                                if (w->t2 < w->t0) {
                                    w->rx = w->rx + (w->t0 - w->t2);
                                }
                            } else {
                                if (w->t0 < w->t2) {
                                    w->rx = w->rx + (w->t0 - w->t2);
                                }
                            }
                            if (w->dz < 0) {
                                if (w->t3 < w->t1) {
                                    w->rz = w->rz + (w->t1 - w->t3);
                                }
                            } else {
                                if (w->t1 < w->t3) {
                                    w->rz = w->rz + (w->t1 - w->t3);
                                }
                            }
                        } while ((u32)w->rx < 0x140U && (u32)w->rz < 0x140U
                                 && ((w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x)
                                     || (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z)));
                        w->ebz_x = w->x - w->cbz_x;
                        w->ebz_z = w->z - w->cbz_z;
                        w->ebx_x = w->x - w->cbx_x;
                        w->ebx_z = w->z - w->cbx_z;
                        w->d_bz = SquareRoot0(w->ebz_x * w->ebz_x + w->ebz_z * w->ebz_z);
                        w->d_bx = SquareRoot0(w->ebx_x * w->ebx_x + w->ebx_z * w->ebx_z);
                        if (w->d_bz < w->d_bx) {
                            w->bz = w->cbz_z;
                            w->cbz_z = w->lin_z = w->lin_z + w->paso_z;
                            w->bx = w->cbz_x;
                            w->cbz_x = w->cbz_x + ((w->pend_z * w->paso_z) >> 12);
                        } else {
                            w->bz = w->cbx_z;
                            w->cbx_x = w->lin_x = w->lin_x + w->paso_x;
                            w->bx = w->cbx_x;
                            w->cbx_z = w->cbx_z + ((w->pend_x * w->paso_x) >> 12);
                        }
                    } while ((w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x)
                             || (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z));
                    CIERRE_COMPLETO;
                }
                /* Solo en x (dz == 0). */
                if (w->dx > 0) {
                    w->paso_x = 0x140;
                    w->celda_x = 0x28;
                    w->lin_x = (w->x / 320) * 0x140 + 0x140;
                } else if (w->dx < 0) {
                    w->paso_x = -0x140;
                    w->celda_x = -0x28;
                    w->lin_x = (w->x / 320) * 0x140 - 1;
                }
                w->t1 = (w->bz - cur->z) / 320 * cur->columnas;
                w->rz = w->bz % 320;
                w->t3 = w->rz / 40 * 8;
                do {
                    if (w->bx < cur->x || w->bx >= cur->x + cur->ancho_x) {
                        w->aux = w->by;
                        w->by = w->y;
                        zona = func_8001BF9C(&w->bx, res->grupo);
                        if (zona == NULL) {
                            INDICE_PREVIO;
                            pos[1] = cur->y_max;
                            desp[0] = w->ax - w->x;
                            res->clase = w->celdas[0];
                            res->flags = 2;
                            w->t0 = w->celdas[w->prev];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 8;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                            }
                            res->pendiente = w->t0 * cur->pendiente;
                            w->t0 = w->celdas[w->n];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 8;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                                res->flags = res->flags | 0x20;
                            }
                            res->pendiente_abs = w->t0 * cur->pendiente;
                            res->grupo = grupo;
                            techo = cur->y_min;
                            ret = 0;
                            res->zona = zona;
                            res->techo = techo;
                            return ret;
                        }
                        w->cual = 1;
                        w->by = w->aux;
                        grupo = zona->grupo;
                        cur = &w->copia[w->cual];
                        COPIAR_ZONA(cur, zona);
                        w->t1 = (w->bz - cur->z) / 320 * cur->columnas;
                    }
                    w->baldosa = zona->baldosas[(w->bx - cur->x) / 320 + w->t1];
                    res->tipo = w->baldosa & 0xF000;
                    w->baldosa = w->baldosa & 0xFFF;
                    w->rx = w->bx % 320;
                    w->bx = w->bx - w->rx;
                    if (w->celda_x > 0) {
                        w->lim_x = (w->rx / 40) * 0x28 + 0x28;
                    } else {
                        w->lim_x = (w->rx / 40) * 0x28 - 1;
                    }
                    do {
                        w->n = w->n + 1;
                        w->celdas[w->n] = (s8)((u8(*)[64])zona->subceldas)[w->baldosa][w->rx / 40 + w->t3];
                        w->zonas[w->n] = cur;
                        c = w->celdas[w->n];
                        if (c == 0x7E) {
                            c = 0;
                        } else if (c > 0 && c < 0x7E) {
                            c = -c;
                        }
                        if (w->n == 0xF) {
                            COMPACTAR_HISTORIAL;
                        }
                        if ((c == 0x7F && w->n >= 2)
                            || cur->y_max + c * cur->pendiente - w->y < -0x64) {
                            if (w->n > 0) {
                                w->n = w->n - 1;
                            }
                            zona = w->zonas[w->n];
                            pos[1] = zona->y_max;
                            desp[0] = w->ax - w->x;
                            res->clase = w->celdas[0];
                            if (w->n == 0xE) {
                                res->flags = 2;
                            } else {
                                res->flags = 6;
                            }
                            w->t0 = w->celdas[w->n];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 0xC;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                                res->flags = res->flags | 0x20;
                            }
                            w->t0 = w->t0 * zona->pendiente;
                            res->pendiente = w->t0;
                            res->pendiente_abs = w->t0;
                            res->grupo = zona->grupo;
                            techo = zona->y_min;
                            ret = 1;
                            res->zona = zona;
                            res->techo = techo;
                            return ret;
                        }
                        w->acc_x = w->rx + w->bx - w->x;
                        w->ax = w->rx + w->bx;
                        w->rx = w->lim_x;
                        w->lim_x = w->lim_x + w->celda_x;
                    } while ((u32)w->rx < 0x140U
                             && (w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x));
                    w->bx = w->lin_x;
                    w->lin_x = w->lin_x + w->paso_x;
                } while (w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x);
                CIERRE_COMPLETO_XZ;
            }
            if (dz != 0) {
                /* Solo en z (dx == 0). */
                if (w->dz > 0) {
                    w->paso_z = 0x140;
                    w->celda_z = 0x28;
                    w->lin_z = (w->z / 320) * 0x140 + 0x140;
                } else if (w->dz < 0) {
                    w->paso_z = -0x140;
                    w->celda_z = -0x28;
                    w->lin_z = (w->z / 320) * 0x140 - 1;
                }
                w->t0 = (w->bx - cur->x) / 320;
                w->rx = w->bx % 320;
                w->t2 = w->rx / 40;
                do {
                    if (w->bz < cur->z || w->bz >= cur->z + cur->ancho_z) {
                        w->aux = w->by;
                        w->by = w->y;
                        zona = func_8001BF9C(&w->bx, res->grupo);
                        if (zona == NULL) {
                            INDICE_PREVIO;
                            pos[1] = cur->y_max;
                            desp[2] = w->az - w->z;
                            res->clase = w->celdas[0];
                            res->flags = 2;
                            w->t0 = w->celdas[w->prev];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 2;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                            }
                            res->pendiente = w->t0 * cur->pendiente;
                            w->t0 = w->celdas[w->n];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 2;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                                res->flags = res->flags | 0x20;
                            }
                            res->pendiente_abs = w->t0 * cur->pendiente;
                            res->grupo = grupo;
                            techo = cur->y_min;
                            ret = 0;
                            res->zona = zona;
                            res->techo = techo;
                            return ret;
                        }
                        w->cual = 1;
                        w->by = w->aux;
                        grupo = zona->grupo;
                        cur = &w->copia[w->cual];
                        COPIAR_ZONA(cur, zona);
                        w->t0 = (w->bx - cur->x) / 320;
                    }
                    w->baldosa = zona->baldosas[w->t0 + (w->bz - cur->z) / 320 * cur->columnas];
                    res->tipo = w->baldosa & 0xF000;
                    w->baldosa = w->baldosa & 0xFFF;
                    w->rz = w->bz % 320;
                    w->bz = w->bz - w->rz;
                    if (w->celda_z > 0) {
                        w->lim_z = (w->rz / 40) * 0x28 + 0x28;
                    } else {
                        w->lim_z = (w->rz / 40) * 0x28 - 1;
                    }
                    do {
                        w->n = w->n + 1;
                        w->celdas[w->n] = (s8)((u8(*)[64])zona->subceldas)[w->baldosa][(w->rz / 40) * 8 + w->t2];
                        w->zonas[w->n] = cur;
                        c = w->celdas[w->n];
                        if (c == 0x7E) {
                            c = 0;
                        } else if (c > 0 && c < 0x7E) {
                            c = -c;
                        }
                        if (w->n == 0xF) {
                            COMPACTAR_HISTORIAL;
                        }
                        if ((c == 0x7F && w->n >= 2)
                            || cur->y_max + c * cur->pendiente - w->y < -0x64) {
                            if (w->n > 0) {
                                w->n = w->n - 1;
                            }
                            zona = w->zonas[w->n];
                            pos[1] = zona->y_max;
                            desp[2] = w->az - w->z;
                            res->clase = w->celdas[0];
                            if (w->n == 0xE) {
                                res->flags = 2;
                            } else {
                                res->flags = 6;
                            }
                            w->t0 = w->celdas[w->n];
                            if (w->t0 == 0x7E) {
                                w->t0 = 0;
                                res->flags = 0xC;
                            } else if (w->t0 > 0) {
                                w->t0 = -w->t0;
                                res->flags = res->flags | 0x20;
                            }
                            w->t0 = w->t0 * zona->pendiente;
                            res->pendiente = w->t0;
                            res->pendiente_abs = w->t0;
                            res->grupo = zona->grupo;
                            techo = zona->y_min;
                            ret = 1;
                            res->zona = zona;
                            res->techo = techo;
                            return ret;
                        }
                        w->acc_z = w->rz + w->bz - w->z;
                        w->az = w->rz + w->bz;
                        w->rz = w->lim_z;
                        w->lim_z = w->lim_z + w->celda_z;
                    } while ((u32)w->rz < 0x140U
                             && (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z));
                    w->bz = w->lin_z;
                    w->lin_z = w->lin_z + w->paso_z;
                } while (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z);
                CIERRE_COMPLETO_XZ;
            }
            return 0;
        }
    }
    /* Sin desplazamiento: consulta de la baldosa bajo el punto. */
    w->baldosa = zona->baldosas[(w->bx - cur->x) / 320 + (w->bz - cur->z) / 320 * cur->columnas];
    res->tipo = w->baldosa & 0xF000;
    w->rx = w->bx % 320;
    w->rz = w->bz % 320;
    w->baldosa = w->baldosa & 0xFFF;
    w->celdas[++w->n] = (s8)((u8(*)[64])zona->subceldas)[w->baldosa][w->rx / 40 + w->rz / 40 * 8];
    c = w->celdas[w->n];
    if (c > 0 && c < 0x7E) {
        c = -c;
    }
    if (c == 0x7E) {
        pos[1] = cur->y_max;
        cl = w->celdas[0];
        f = 8;
        goto plano;
    }
    if (c == 0x7F) {
        pos[1] = cur->y_max;
        cl = w->celdas[0];
        f = 6;
plano:
        res->flags = f;
        res->pendiente = 0;
        res->pendiente_abs = 0;
        res->clase = cl;
        res->grupo = cur->grupo;
        techo = cur->y_min;
        ret = 1;
        res->zona = zona;
        res->techo = techo;
        return ret;
    }
    pos[1] = cur->y_max;
    res->clase = w->celdas[0];
    res->flags = 2;
    w->t0 = w->celdas[w->n];
    if (w->t0 > 0) {
        w->t0 = -w->t0;
        res->flags = res->flags | 0x20;
    }
    w->t0 = w->t0 * cur->pendiente;
    res->pendiente = w->t0;
    res->pendiente_abs = w->t0;
    res->grupo = cur->grupo;
    techo = cur->y_min;
    ret = 1;
    res->zona = zona;
    res->techo = techo;
    return ret;
}
#else
INCLUDE_ASM("asm/nonmatchings/colision_y_terreno", func_80019474);
#endif

/*
 * Busca la zona que contiene el punto (x, y, z): primero entre las del grupo indicado (si es
 * valido) y despues en toda la tabla. Devuelve NULL si ninguna lo contiene.
 */
ZonaColision* func_8001BF9C(s32* a0, s16 a1)
{
    ZonaColision* zona;
    s32 x;
    s32 y;
    s32 z;
    s32 n;
    s16 i;

    x = a0[0];
    y = a0[1];
    z = a0[2];
    if (a1 >= 0) {
        zona = D_80069C18[a1];
        if (zona != 0) {
            do {
                if (y <= zona->y_max && zona->y_min < y
                    && x >= zona->x && x < zona->x + zona->ancho_x
                    && z >= zona->z && z < zona->z + zona->ancho_z) {
                    return zona;
                }
                zona++;
            } while (zona->grupo == a1);
        }
    }
    zona = *(ZonaColision**)(base_gp + 0x5C);
    i = 0;
    if (*(s32*)(base_gp + 0x58) > 0) {
        n = *(s32*)(base_gp + 0x58);
        do {
            if (y <= zona->y_max && zona->y_min < y
                && x >= zona->x && x < zona->x + zona->ancho_x
                && z >= zona->z && z < zona->z + zona->ancho_z) {
                return zona;
            }
            zona++;
            i++;
        } while (i < n);
    }
    return 0;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 1078 con la configuracion versionada (g = 0, no carga globales). El compilador asigna s0/s1
 * al reves (el original guarda la estructura de trabajo en s0 y el resultado en s1) y falta un `move t2,a3`.
 * Variantes probadas: 9 (copias de z, orden de sentencias, barreras, copias locales de los punteros de trabajo).
 *
 * Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en
 * res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res
 * con la clase de terreno. 0x7E y 0x7F de la subcelda son transiciones de zona; cualquier otro
 * valor es una pendiente (su signo marca el sentido, el bit 0x20 de flags lo recuerda).
 */
void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w)
{
    ZonaColision* z;

    GEO_CARGAR_W(pos);
    GEO_GUARDAR_W_T1(&w->x);
    z = func_8001BF9C(&w->x, r->grupo);
    r->zona = z;
    if (z == 0) {
        r->clase = 1;
        r->flags = 1;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->tipo = 0;
        r->grupo = -1;
        return;
    }
    w->baldosa = z->baldosas[(w->x - z->x) / 320 + (w->z - z->z) / 320 * z->columnas];
    r->tipo = w->baldosa & 0xF000;
    w->x_local = w->x % 320;
    w->z_local = w->z % 320;
    w->baldosa &= 0xFFF;
    w->celda = (s8)z->subceldas[(w->baldosa << 6) + w->z_local / 40 * 8 + w->x_local / 40];
    if (w->celda == 0x7E) {
        pos[1] = z->y_max;
        r->clase = 0;
        r->flags = 8;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->grupo = z->grupo;
        r->suelo = pos[1];
        return;
    }
    if (w->celda == 0x7F) {
        pos[1] = z->y_max;
        r->clase = 0;
        r->flags = 6;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->grupo = z->grupo;
        r->suelo = pos[1];
        return;
    }
    pos[1] = z->y_max;
    r->clase = w->celda;
    r->flags = 2;
    if (w->celda > 0) {
        w->celda = -w->celda;
        r->flags |= 0x20;
    }
    w->celda = w->celda * z->pendiente;
    r->pendiente = w->celda;
    r->pendiente_abs = w->celda;
    r->grupo = z->grupo;
    r->suelo = z->y_max + w->celda;
}
#else
INCLUDE_ASM("asm/nonmatchings/colision_y_terreno", func_8001C134);
#endif
