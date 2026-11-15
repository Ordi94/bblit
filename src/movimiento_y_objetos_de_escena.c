#include "common.h"
#include "motor.h"

/*
 * Movimiento vertical del objeto: gravedad y salto. Decide la altura del siguiente cuadro a
 * partir del desplazamiento pedido: si cae mas de 200 unidades acelera la caida con una curva
 * seno, si sube o cae poco lo amortigua o lo limita a +-70, y fija o limpia las banderas de
 * suelo (0x2), salto (0x200) y caida libre segun toque el suelo o empiece un salto.
 */
void func_8001C424(Objeto* o, Movimiento* m, ResultadoBaldosa* orden)
{
    s32 nuevo;
    s32 v;
    s32 dy;
    s32 t;
    s32 tipo;

    dy = m->dy;
    nuevo = o->param.trans.vy + dy;
    if (nuevo >= o->param.trans.vy + 0xC8) {
        if (o->flags14 & 1) {
            goto calculo;
        }
        if (o->h108 >= 0xC00) {
            o->h108 = 0xC00;
        }
        t = 0x46 - (-(rsin(o->h108 + 0x400) * 0x46) >> 12);
        o->h108 += 0x44;
        o->h116 = t;
        if (o->flags14 & 0x10000) {
            t = o->param.trans.vy + 0xC;
        } else {
            t = o->param.trans.vy + (s16)t;
        }
        if (t >= nuevo) {
            if ((s16)orden->flags == 8 || (s16)orden->flags == 1) {
                o->flags14 &= ~2;
                if (!(o->flags14 & 4)) {
                    o->flags14 |= 0x200;
                }
            } else {
                goto despegue;
            }
        } else {
            if (o->flags14 & 0x10000) {
                v = 0xC;
            } else {
                v = o->h116;
            }
            m->dy = v;
            o->flags14 &= ~2;
            if (!(o->flags14 & 4)) {
                o->flags14 |= 0x200;
            }
        }
        goto fin;
    } else if (!(o->flags14 & 1)) {
        if (o->flags14 & 2) {
            if (dy > 0) {
                v = dy >> 1;
                if (v != 0) {
                    m->dy = v;
                }
            } else if (dy >= -0x45) {
                v = dy >> 1;
                if (v != 0) {
                    m->dy = v;
                }
            }
        } else {
            if (!(o->flags14 & 4)) {
                if (dy >= 0x47) {
                    m->dy = 0x46;
                } else if (dy < -0x46) {
                    m->dy = -0x46;
                }
            }
        }
    }
calculo:
    o->h116 = m->dy;
    if (m->dy + o->param.trans.vy == o->i100 + o->h10C && (s16)orden->flags != 8 && (s16)orden->flags != 1) {
despegue:
        /* El tipo de baldosa se lee antes de tocar las banderas: asi la mascara de banderas y el
         * tipo se reparten los registros de argumento como en el original. */
        tipo = orden->tipo;
        o->flags14 |= 2;
        o->h108 = 0x800;
        o->w10E = tipo;
        o->flags14 &= 0xFFFEFDFF;
    } else if (!(o->flags14 & 2)) {
        o->flags14 &= ~2;
        if (!(o->flags14 & 5)) {
            o->flags14 |= 0x200;
        }
    }
fin:
    if (o->flags14 & 4) {
        m->dy = dy;
    }
}

/*
 * Paso de movimiento horizontal contra el terreno. Con g = 8 (config/opciones_compilacion.toml) la
 * lectura del puntero global D_80069698 es una sola macro de carga: el ensamblador la expande tras
 * el hueco de retardo del salto previo, que queda en nop como en el original. Con -G0 el compilador
 * emite la parte alta de la direccion como instruccion propia y reorg la sube a ese hueco (100).
 */
void func_8001C6CC(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w)
{
    s32* pos;
    u8* area;
    s32 v;
    u16 flags;
    TrabajoMov* trab;
    /* El original conserva el area de trabajo en un registro salvado desde la entrada; la
     * copia local del parametro reproduce ese reparto de registros. */
    trab = w;
    trab->x = o->param.trans.vx;
    trab->y = o->param.trans.vy;
    trab->z = o->param.trans.vz;
    area = trab->consulta;
    v = o->h10A;
    if (v < 0) {
        o->param.trans.vy = o->param.trans.vy + v;
    }
    pos = &o->param.trans.vx;
    trab->y10 = o->param.trans.vy;
    trab->h18 = d->x;
    trab->h1A = d->z;
    BarrerTerreno(pos, d, r, area);
    trab->dx = d->x;
    trab->dz = d->z;
    o->param.trans.vx = o->param.trans.vx + d->x;
    o->param.trans.vz = o->param.trans.vz + d->z;
    flags = r->flags;
    if (flags & 0x10) {
        trab->h1A = trab->h1A - d->z;
        /* El original resta h18 de d->x antes de poner a cero d->z. */
        d->x = trab->h18 - d->x;
        d->z = 0;
        o->param.trans.vy = trab->y10;
        BarrerTerreno(pos, d, r, area);
        v = d->x;
        if (v == 0) {
            o->h110 = 0;
        } else {
            trab->dx = trab->dx + v;
            o->param.trans.vx = o->param.trans.vx + d->x;
        }
        d->x = 0;
        d->z = trab->h1A;
        o->param.trans.vy = trab->y10;
        BarrerTerreno(&o->param.trans.vx, d, r, area);
        v = d->z;
        if (v == 0) {
            o->h112 = 0;
        } else {
            trab->dz = trab->dz + v;
            o->param.trans.vz = o->param.trans.vz + d->z;
        }
    } else if (flags & 4) {
        o->h110 = 0;
        o->h112 = 0;
        o->flags14 = o->flags14 | 0x100000;
    }
    if (r->flags & 8) {
        if (o == D_80069698 || !(o->flags14 & 1)) {
            o->param.trans.vy = o->param.trans.vy + 1;
            trab->w1C = r->grupo;
            func_8001C134(&o->param.trans.vx, r, (TrabajoBaldosa*)area);
            r->grupo = trab->w1C;
        }
    }
    o->i100 = o->param.trans.vy;
    o->h10C = r->pendiente_abs;
    o->param.trans.vx = trab->x;
    o->param.trans.vy = trab->y;
    o->param.trans.vz = trab->z;
    d->x = trab->dx;
    d->z = trab->dz;
}

/*
 * Movimiento vertical contra el suelo: calcula la altura hasta la que puede bajar o subir el
 * objeto este cuadro. Con la bandera 1 (apoyado) sigue el suelo de la baldosa, consulta el techo
 * y la baldosa bajo el siguiente punto si la altura de partida cabe debajo del techo, y limpia
 * las banderas de apoyo (9) cuando pierde el suelo; sin ella, solo limita la caida (200 como
 * maximo, o hasta el suelo anterior).
 */
#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 150 con la configuracion versionada (g = 8 del archivo; ejes 22 de operando,
 * 0 reordenadas, 19 insertadas o borradas). Mismas ramas, mismo orden de bloques y mismos almacenes que
 * el ensamblador; difiere en tres puntos de reparto de registros: (1) prologo: el original copia el
 * cuarto argumento con `move a2,a3` y desde esa copia hace `move s0,a2` y `addiu a2,a2,0x28`; aqui el
 * compilador funde la copia con el area de trabajo y emite `move s0,a3` y `addiu a2,s0,0x28` (una
 * instruccion menos). Se supone, sin verificar, que el original mantiene la copia como pseudo propio.
 * (2) mascara de las banderas (0x188 a 0x190): el original carga en v0, pone la constante en v1 y
 * deja el resultado en v0; aqui carga en v1 y la constante en v0. Medido en -dg: el pseudo de la
 * mascara (92) solo conflictua con 80, 81 y 87 y toma v0, de modo que la carga cae en v1. (3) altura
 * calculada (0x1a0, 0x1e4 y 0x1f0): el original la deja en v0; aqui el pseudo (91) conflictua con el
 * registro 2 en -dg y toma v1. Medido en -dS: el `li` de 200 queda entre el `lhu` de las banderas del
 * resultado y su `andi`; se supone, sin verificar, que ese solape es el conflicto con v0.
 *
 * La mascara `o->flags14 & ~9` esta escrita en tres ramas y no genera codigo adicional: el volcado -dR
 * muestra tres cargas de las banderas (insns 177, 211 y 283) y -dJ y -dd una sola (insn 283); el
 * ensamblador final tiene una sola `lw v0,0x14(s3)` en 0x188, a la que saltan las tres ramas desde
 * 0x110, 0x124 y 0x178, como el original. Cada copia es un pseudo local del bloque; la rama de perdida
 * de suelo (`f & ~9`, `and v0,a1,v0` en 0x154) comparte el almacen de 0x194. El original tiene tres
 * pruebas `cur < tope` separadas (0x120, 0x168 y 0x174) y aqui tambien salen tres.
 *
 * La envoltura do/while (0) de la consulta de la baldosa (cuatro almacenes, la llamada y la salida
 * hacia la rama de baldosa con suelo) no genera codigo: pondera por un nivel mas las referencias del
 * area de trabajo `w` (pseudo 83), de 9 a 16 usos ponderados sobre una vida de 78 (prioridad
 * floor_log2(R) * R / L: de 3 * 9 / 78 = 0,346 a 4 * 16 / 78 = 0,821; el logaritmo pasa de 3 a 4). La
 * altura nueva (88) tiene 10 usos sobre 51 (3 * 10 / 51 = 0,588), el suelo anterior (86) 10 sobre 62
 * (0,484), el objeto (80) 21 sobre 192 con la envoltura y 19 sin ella (0,438 y 0,396) y el tope (87)
 * 10 sobre 84 (0,357): sin la envoltura el area queda por detras de todos ellos; con ella se asigna
 * antes y toma s0, la altura nueva s1, el suelo anterior s2, el objeto s3 y el tope s4, como el
 * original. Sin la envoltura el C puntua 502. La salida hacia la rama con suelo va dentro de la
 * envoltura porque suma la lectura de `w->res.flags` con el peso del bucle; un `goto` a una etiqueta
 * tiene el mismo destino con o sin la envoltura y no cambia el flujo. El reparto es fragil: 16 es
 * justo el valor en que el logaritmo sube, y un uso ponderado menos en el area lo pierde.
 * La forma del fuente original que producia este reparto se desconoce.
 */
void func_8001C998(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* area)
{
    s32 i;
    TrabajoSuelo* w;
    s32 base;
    s32 tope;
    s32 cur;
    s32 modo;
    s32 f;
    s32 v;
    s32 m;
    s32 desfase_suelo;
    s32 pierde_suelo;
    TrabajoBaldosa* trabajo_baldosa;
    /* El area + 0x28 se calcula al entrar: el original lo deja en a2 antes de leer las banderas. */
    trabajo_baldosa = (TrabajoBaldosa*)((u8*)area + 0x28);
    /* El desfase del suelo se lee en una variable de 32 bits antes de sumarlo: leido dentro de la suma el reparto de registros empeora. */
    desfase_suelo = o->h10C;
    w = (TrabajoSuelo*)area;
    f = o->flags14;
    i = o->i100;
    base = i + desfase_suelo;
    tope = base;
    if (f & 1) {
        cur = o->param.trans.vy + o->h10A;
        if (o->h108 <= 0x800) {
            if (cur + o->max.vy < r->techo) {
                if (base >= cur) {
                    /* Envoltura sin codigo: pondera las referencias del area de trabajo (ver la cabecera). */
                    do {
                        w->x = o->param.trans.vx + d->x;
                        w->y = r->techo - 1;
                        w->z = o->param.trans.vz + d->z;
                        w->res.grupo = -1;
                        func_8001C134(&w->x, &w->res, trabajo_baldosa);
                        if (w->res.flags & 8) {
                            goto con_suelo;
                        }
                    } while (0);
                    tope = r->techo - o->max.vy;
                    if (base < tope) {
                        tope = base;
                    }
                    goto calcular;
con_suelo:
                    if (cur >= base) {
                        /* Sentencia replicada: es la misma que la de las otras ramas. */
                        m = o->flags14 & ~9;
                        goto guardar;
                    }
                    tope = cur;
                    goto calcular;
                }
            }
            if (cur < tope) {
                tope = cur;
                goto calcular;
            }
            /* Sentencia replicada: es la misma que la de las otras ramas. */
            m = o->flags14 & ~9;
            goto guardar;
        } else {
            modo = (s16)r->flags;
            /* La condicion de perdida de suelo se guarda en una variable antes de la rama: sin ella el compilador la parte en dos saltos. */
            pierde_suelo = (base < cur) & (modo != 8);
            if (pierde_suelo) {
                m = f & ~9;
                goto guardar;
            }
            if (modo == 8 || modo == 1) {
                o->i100 = i + 1;
            }
            if (cur < tope) {
                tope = cur;
                goto calcular;
            }
            /* Sentencia replicada: es la misma que la de las otras ramas. */
            m = o->flags14 & ~9;
        }
guardar:
        o->flags14 = m;
calcular:
        v = tope - o->param.trans.vy;
    } else {
        if (f & 4) {
            if (base < o->param.trans.vy + d->dy) {
                d->dy = base - o->param.trans.vy;
            }
            return;
        }
        v = 0xC8;
        if (!((u16)r->flags & 1)) {
            v = base - o->param.trans.vy;
        }
    }
    d->dy = v;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena", func_8001C998);
#endif

/*
 * Paso de movimiento de un objeto: el desplazamiento horizontal (func_8001C6CC), el vertical
 * contra el suelo (func_8001C998) y la gravedad y el salto (func_8001C424), en ese orden. La
 * orientacion del objeto se copia al resultado de la baldosa antes y se recupera despues
 * salvo que el terreno la invalide con -1.
 */
void func_8001CBB8(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w)
{
    r->grupo = o->w26;
    func_8001C6CC(o, d, r, w);
    if (r->flags & 4) {
        o->flags14 |= 0x100000;
    }
    if (r->grupo != -1) {
        o->w26 = r->grupo;
    }
    func_8001C998(o, d, r, w);
    func_8001C424(o, d, r);
}
