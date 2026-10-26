#include "common.h"
#include "motor.h"

/*
 * Movimiento vertical del objeto: gravedad y salto. Decide la altura del siguiente cuadro a
 * partir del desplazamiento pedido: si cae mas de 200 unidades acelera la caida con una curva
 * seno, si sube o cae poco lo amortigua o lo limita a +-70, y fija o limpia las banderas de
 * suelo (0x2), salto (0x200) y caida libre segun toque el suelo o empiece un salto.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 1135 con la configuracion versionada (-G0). Misma estructura de ramas y mismos almacenes; en el bloque de despegue el original conserva dos copias de las banderas (move v1,v0) y ordena los almacenes de h108 y w10E de otro modo. Variantes probadas: 14. */
void func_8001C424(Objeto* o, Movimiento* m, ResultadoBaldosa* orden)
{
    s32 dy;
    s32 nuevo;
    s32 t;
    s32 v;
    s32 f;

    dy = m->dy;
    nuevo = o->param.trans.vy + dy;
    if (nuevo >= o->param.trans.vy + 0xC8) {
        if (o->flags14 & 1) {
            goto calculo;
        }
        if (o->h108 >= 0xC00) {
            o->h108 = 0xC00;
        }
        t = 0x46 - ((-(rsin(o->h108 + 0x400) * 0x46)) >> 12);
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
    } else {
        if (!(o->flags14 & 1)) {
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
            } else if (!(o->flags14 & 4)) {
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
        f = o->flags14 | 2;
        o->flags14 = f;
        o->h108 = 0x800;
        o->w10E = orden->tipo;
        o->flags14 = f & 0xFFFEFDFF;
    } else {
        if (!(o->flags14 & 2)) {
            o->flags14 &= ~2;
            if (!(o->flags14 & 5)) {
                o->flags14 |= 0x200;
            }
        }
    }
fin:
    if (o->flags14 & 4) {
        m->dy = dy;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena", func_8001C424);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 498 con la configuracion versionada (-G0). Misma secuencia de llamadas y almacenes; el original reparte s1 al objeto y s0 al area de trabajo y ordena un almacen de d->z antes de la lectura de w->h18, el C los asigna al reves. Variantes probadas: 7. */
void func_8001C6CC(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w)
{
    s32* pos;
    u8* area;
    s32 v;
    u16 flags;

    w->x = o->param.trans.vx;
    w->y = o->param.trans.vy;
    w->z = o->param.trans.vz;
    area = w->consulta;
    v = o->h10A;
    if (v < 0) {
        o->param.trans.vy = o->param.trans.vy + v;
    }
    pos = &o->param.trans.vx;
    w->y10 = o->param.trans.vy;
    w->h18 = d->x;
    w->h1A = d->z;
    func_80019474(pos, d, r, area);
    w->dx = d->x;
    w->dz = d->z;
    o->param.trans.vx = o->param.trans.vx + d->x;
    o->param.trans.vz = o->param.trans.vz + d->z;
    flags = r->flags;
    if (flags & 0x10) {
        w->h1A = w->h1A - d->z;
        d->z = 0;
        d->x = w->h18 - d->x;
        o->param.trans.vy = w->y10;
        func_80019474(pos, d, r, area);
        v = d->x;
        if (v == 0) {
            o->h110 = 0;
        } else {
            w->dx = w->dx + v;
            o->param.trans.vx = o->param.trans.vx + d->x;
        }
        d->x = 0;
        d->z = w->h1A;
        o->param.trans.vy = w->y10;
        func_80019474(&o->param.trans.vx, d, r, area);
        v = d->z;
        if (v == 0) {
            o->h112 = 0;
        } else {
            w->dz = w->dz + v;
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
            w->w1C = r->grupo;
            func_8001C134(&o->param.trans.vx, r, (TrabajoBaldosa*)area);
            r->grupo = w->w1C;
        }
    }
    o->i100 = o->param.trans.vy;
    o->h10C = r->pendiente_abs;
    o->param.trans.vx = w->x;
    o->param.trans.vy = w->y;
    o->param.trans.vz = w->z;
    d->x = w->dx;
    d->z = w->dz;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena", func_8001C6CC);
#endif

/*
 * Movimiento vertical contra el suelo: calcula la altura hasta la que puede bajar o subir el
 * objeto este cuadro. Con la bandera 1 (apoyado) sigue el suelo de la baldosa, consulta el techo
 * y la baldosa bajo el siguiente punto si la altura de partida cabe debajo del techo, y limpia
 * las banderas de apoyo (9) cuando pierde el suelo; sin ella, solo limita la caida (200 como
 * maximo, o hasta el suelo anterior).
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 3636 con la configuracion versionada (-G0). Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a la altura nueva y s2 al suelo anterior, y precalcula area + 0x28 al principio, el C asigna los registros en otro orden y cambia el reparto de los saltos. Variantes probadas: 2. */
void func_8001C998(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* area)
{
    TrabajoSuelo* w;
    s32 base;
    s32 tope;
    s32 cur;
    s32 modo;
    s32 f;
    s32 v;
    s32 i;

    w = (TrabajoSuelo*)area;
    i = o->i100;
    f = o->flags14;
    base = i + o->h10C;
    tope = base;
    if (f & 1) {
        cur = o->param.trans.vy + o->h10A;
        if (o->h108 <= 0x800) {
            if (cur + o->max.vy < r->techo) {
                if (base >= cur) {
                    w->x = o->param.trans.vx + d->x;
                    w->y = r->techo - 1;
                    w->res.grupo = -1;
                    w->z = o->param.trans.vz + d->z;
                    func_8001C134(&w->x, &w->res, &w->tb);
                    if (!(w->res.flags & 8)) {
                        tope = r->techo - o->max.vy;
                        if (base < tope) {
                            tope = base;
                        }
                    } else if (cur < base) {
                        tope = cur;
                    } else {
                        goto soltar;
                    }
                    goto calcular;
                }
            }
            if (cur < tope) {
                tope = cur;
                goto calcular;
            }
            goto soltar;
        } else {
            modo = (s16)r->flags;
            if (base < cur && modo != 8) {
                v = f & ~9;
                goto guardar;
            }
            if (modo == 8 || modo == 1) {
                o->i100 = i + 1;
            }
            if (cur < tope) {
                tope = cur;
                goto calcular;
            }
soltar:
            v = o->flags14 & ~9;
guardar:
            o->flags14 = v;
        }
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
