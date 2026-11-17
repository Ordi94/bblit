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
            w->t0 = 0; \
            res->flags = 8; \
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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 120 con la configuracion versionada (g = 0 del archivo; ejes 216 de operando,
 * 0 reordenadas, 4 insertadas o borradas). Queda un solo tramo: el original coloca `sw s0,0x10(sp)` (0x80019498)
 * y `move s0,a3` (0x8001949C) tras el `lui`/`ori` (0x80019490, 0x80019494) de la guarda del area de trabajo y aqui
 * van antes de ellos; con la suma del desplazamiento escrita en otra forma (`(u32)w + 0x1C8 > 0x1F8003FF`,
 * o en una local) el codigo generado es el mismo. Volcado de la planificacion posterior al reparto (`-dR`): las
 * copias de los parametros (`move s7,a0` a `move s0,a3`) son los cuatro primeros insns del bloque y la carga de
 * la constante de la guarda (`lui`/`ori`) llega despues de ellos y la copia de `a3` queda antes de la constante;
 * en el original la constante va antes de esa copia. Se supone, sin verificar, que el planificador desempata
 * por el orden de entrada y que en el original la constante ya precedia a la copia de `a3` en esa entrada.
 * El reparto a2/a3 del producto `dsz_x * dsz_x` del recorrido de zona (`mflo`, 0x8001A0BC) coincide: el original
 * lo deja en a2 porque la lectura de `acc_z` para `ant_z` queda acabada antes del producto; con `ant_z` copiado
 * despues de `dsz_z` el producto empezaba antes de acabar esa copia y tomaba a3. La copia de `ant_z` va por eso
 * justo tras la de `ant_x`; con `acc_x` actualizado antes que `dsz_z` los dos temporales de esos calculos toman
 * v0 y v1 como en el original (con `dsz_z` antes la puntuacion es 650).
 * Los cuatro avances del recorrido general y la cola de los planos estaticos ya coinciden con el original:
 * ver la cabecera de la funcion.
 */
/*
 * Barrido de un desplazamiento (desp) del punto pos contra el terreno por baldosas: avanza baldosa a
 * baldosa (320 unidades) y subcelda a subcelda (40 unidades) hasta que una pared (celda 0x7F), un
 * escalon de mas de 100 unidades o el final de las zonas lo detiene; recorta desp a lo recorrido,
 * baja la altura de pos[1] a la base de la zona final y rellena res (clase, banderas, pendiente,
 * grupo, techo y zona). Sin desplazamiento solo consulta la baldosa bajo el punto. Devuelve 0 si el
 * punto sale de las zonas y 1 en los demas casos. w es el area de trabajo del scratchpad: si no cabe
 * ahi (w + 0x1C8 > 0x1F8003FF) la rutina se queda en un bucle infinito a proposito.
 *
 * Tres recorridos casi gemelos segun las componentes no nulas de desp: ambas (caso general, con
 * pendientes de 12 bits de fraccion), solo x y solo z. k es una constante de una sola asignacion
 * (el desfase de partida del historial en el cierre): el compilador la deja como equivalente a 0 y
 * no la pliega en las comparaciones del cierre. En los avances de subcelda el valor previo de un punto de
 * cruce se copia a rx y rz leyendo el campo, con `rx` en primer lugar y luego `aux` y `rz`, y la suma que
 * actualiza el propio punto de cruce es una asignacion compuesta (`+=`). Con ese orden las lecturas de `sz_y`
 * y `sz_z` (o `sx_y` y `sx_z`) quedan antes del `mult` y la de `sz_x` despues, como en el original, y la
 * asignacion compuesta deja la copia `move` de esa lectura antes del almacen de `rx` (0x8001A1BC en el avance
 * de z, 0x8001A258 en el de x). Escrita la suma como `((pend * celda) >> 12) + campo`, la puntuacion es 540.
 *
 * La cola de los planos 0x7E y 0x7F del caso estatico va tras una etiqueta comun (`plano`) y por rama
 * quedan solo las sentencias que el original tambien emite una vez por rama (`pos[1]`, la lectura de
 * la clase y las banderas con su constante): el original comparte una sola cola desde `sh v0,2(s3)`
 * (0x8001BEA0), con `li v0,8` en el hueco del salto y `li v0,6` al final de la otra rama; la clase se lee
 * en cada rama (`lhu v1,0x198(s0)`, 0x8001BE74 y 0x8001BE98) y se almacena al final de la cola, tras los dos
 * almacenes de ceros (`sh v1,0(s3)`, 0x8001BEAC). Por eso la clase pasa por la local `clase_plano`, asignada
 * en cada rama y almacenada en la cola, y las banderas se escriben en cada rama; escribir la clase directa en
 * cada rama la deja antes de los ceros y la puntuacion pasa de 120 a 145.
 * La sentencia `clase_plano = w->celdas[0];` esta repetida en las dos ramas y no genera codigo propio: la cola
 * ya es comun desde el fuente por la etiqueta, de modo que el compilador no tiene nada que fundir y el
 * ensamblador generado conserva una sola carga por rama y una sola cola, sin instrucciones de mas. Lo que decide
 * la copia por rama es la planificacion posterior al reparto de registros (volcado `-dR`): con la sentencia en
 * cada rama la carga `lhu` queda en el bloque de su rama, en `v1`, y el valor cruza el salto hasta el almacen
 * final, como en el original; con una sola copia tras la etiqueta la carga pasa a la cola, el planificador la
 * deja despues del almacen de las banderas y la toma en `v0`, y la puntuacion pasa de 120 a 425. Se supone,
 * sin verificar, que con las banderas escritas por rama el pseudo de la clase, que cruza el salto, es el unico
 * pseudo que puede recibir `v1` al asignarse despues de los pseudos locales de cada rama.
 * La forma del fuente original que producia este reparto se desconoce.
 */
s32 BarrerTerreno(s32* pos, s32* desp, ResultadoBaldosa* res, TrabajoRecorrido* w)
{
    ZonaColision* zona;
    ZonaColision* cur;
    u16 grupo;
    u16 clase_plano;
    s16 c;
    s16 k = 0;
    s32 techo;
    s32 ret;
    s32 dx;
    s32 dz;
    s32 px;
    s32 pz;

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
                            w->ant_z = w->acc_z;
                            w->acc_x = w->rx + w->bx - w->x;
                            w->dsz_z = w->rz - w->sz_z;
                            w->acc_z = w->rz + w->bz - w->z;
                            w->dsx_x = w->rx - w->sx_x;
                            w->dsx_z = w->rz - w->sx_z;
                            w->d_sz = SquareRoot0(w->dsz_x * w->dsz_x + w->dsz_z * w->dsz_z);
                            w->d_sx = SquareRoot0(w->dsx_x * w->dsx_x + w->dsx_z * w->dsx_z);
                            if (w->d_sz < w->d_sx) {
                                if (w->dz > 0 ? w->acc_z < w->dz : w->dz < w->acc_z) {
                                    w->rx = w->sz_x;
                                    w->aux = w->sz_y;
                                    w->rz = w->sz_z;
                                    w->sz_z = w->lim_z = w->lim_z + w->celda_z;
                                    w->sz_x += (w->pend_z * w->celda_z) >> 12;
                                } else {
                                    w->acc_x = w->dx;
                                }
                            } else {
                                if (w->dx > 0 ? w->acc_x < w->dx : w->dx < w->acc_x) {
                                    w->rx = w->sx_x;
                                    w->aux = w->sx_y;
                                    w->rz = w->sx_z;
                                    w->sx_x = w->lim_x = w->lim_x + w->celda_x;
                                    w->sx_z += (w->pend_x * w->celda_x) >> 12;
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
                                /* Escrita como `t2 > t0`, la comparacion carga `t2` (a0) antes que
                                 * `t0` (v1) y emite `slt v0, v1, a0`, el orden de cargas y de
                                 * operandos del original. */
                                if (w->t2 > w->t0) {
                                    w->rx = w->rx + (w->t0 - w->t2);
                                }
                            }
                            if (w->dz < 0) {
                                if (w->t3 < w->t1) {
                                    w->rz = w->rz + (w->t1 - w->t3);
                                }
                            } else {
                                /* Comparacion conmutada (t3 > t1): GCC la canoniza igual y solo cambia el orden de
                                 * creacion de los pseudos, que baja la puntuacion de 2060 a 2040. */
                                if (w->t3 > w->t1) {
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
                            w->bx = w->cbz_x;
                            w->bz = w->cbz_z;
                            w->cbz_z = w->lin_z = w->lin_z + w->paso_z;
                            w->cbz_x = w->cbz_x + ((w->pend_z * w->paso_z) >> 12);
                        } else {
                            w->bx = w->cbx_x;
                            w->bz = w->cbx_z;
                            w->cbx_x = w->lin_x = w->lin_x + w->paso_x;
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
            /*
             * Camino inalcanzable (con dx y dz nulos se despacha al caso estatico): el original sale
             * sin asignar el valor de retorno, de modo que no se escribe aqui.
             */
            goto fin;
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
        /* Sentencia replicada: es la misma que la de las otras ramas. */
        clase_plano = w->celdas[0];
        res->flags = 8;
        goto plano;
    }
    if (c == 0x7F) {
        pos[1] = cur->y_max;
        /* Sentencia replicada: es la misma que la de las otras ramas. */
        clase_plano = w->celdas[0];
        res->flags = 6;
plano:
        res->pendiente = 0;
        res->pendiente_abs = 0;
        res->clase = clase_plano;
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
fin:
    ;
}
#else
INCLUDE_ASM("asm/nonmatchings/colision_y_terreno", BarrerTerreno);
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

/*
 * Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en
 * res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res
 * con la clase de terreno. 0x7E y 0x7F de la subcelda son transiciones de zona; cualquier otro
 * valor es una pendiente (su signo marca el sentido, el bit 0x20 de flags lo recuerda).
 */
void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w)
{
    ZonaColision* z;
    ZonaColision* zona_cuesta;
    TrabajoBaldosa* trabajo;
    TrabajoBaldosa* trabajo_baldosa;
    s32 col;
    u16 baldosa;

    /* Tres nombres para el area de trabajo y dos para la zona: el original reparte el area en s0 y el
     * resultado en s1 solo cuando el area tiene mas referencias que el resultado, y conserva una copia
     * de la zona (t2) para la rama de pendiente. */
    trabajo_baldosa = w;
    trabajo = trabajo_baldosa;
    GEO_CARGAR_W(pos);
    GEO_GUARDAR_W_T1(&trabajo->x);
    z = func_8001BF9C(&trabajo->x, r->grupo);
    zona_cuesta = z;
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
    trabajo_baldosa = trabajo;
    trabajo->baldosa = z->baldosas[(trabajo->x - z->x) / 320 + (trabajo->z - z->z) / 320 * z->columnas];
    r->tipo = trabajo->baldosa & 0xF000;
    /* La mascara de la baldosa se guarda antes de los almacenes de las coordenadas locales y la baldosa se relee
     * despues de ellos, como en el original: con la relectura pegada al almacen de la mascara la puntuacion es 385 y
     * con la mascara guardada despues de las coordenadas 1500. Se supone, sin verificar, que sin un almacen
     * intermedio el valor se reenvia sin pasar por memoria y por eso no sale el `andi 0xffff` del original. */
    trabajo_baldosa->baldosa &= 0xFFF;
    trabajo->x_local = trabajo->x % 320;
    trabajo->z_local = trabajo->z % 320;
    baldosa = trabajo->baldosa;
    /* El cociente de x va en una local propia: con el cociente dentro del indice la planificacion carga z antes que x
     * (715). */
    col = trabajo->x_local / 40;
    /* La tabla de subceldas son filas de 64 bytes por baldosa: el original suma la base y `baldosa << 6` antes que
     * la fila y la columna, y eso solo sale indexando por fila (con el indice plano
     * `col + (baldosa << 6) + trabajo->z_local / 40 * 8` la puntuacion es 755). */
    trabajo->celda = (s8)((u8 (*)[64])z->subceldas)[baldosa][trabajo->z_local / 40 * 8 + col];
    if (trabajo->celda == 0x7E) {
        pos[1] = z->y_max;
        r->clase = 0;
        r->flags = 8;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->grupo = z->grupo;
        r->suelo = pos[1];
        return;
    }
    if (trabajo->celda == 0x7F) {
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
    r->clase = trabajo->celda;
    r->flags = 2;
    if (trabajo->celda > 0) {
        trabajo->celda = -trabajo->celda;
        r->flags |= 0x20;
    }
    trabajo->celda = trabajo->celda * zona_cuesta->pendiente;
    r->pendiente = trabajo->celda;
    r->pendiente_abs = trabajo->celda;
    r->grupo = zona_cuesta->grupo;
    r->suelo = zona_cuesta->y_max + trabajo->celda;
}
