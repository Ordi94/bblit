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
 * Pendiente: puntuacion 1055 con la configuracion versionada (g = 8 del archivo; ejes 15 de operando,
 * 1 reordenada, 43 insertadas o borradas). Difiere en: reparto de registros y orden de bloques de
 * salto. Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a
 * la altura nueva, s2 al suelo anterior y s4 al tope, y con la envoltura el C los reparte igual; queda
 * el orden de los bloques de salto del final. El area + 0x28 se precalcula como el original.
 *
 * La envoltura do/while (0) de la consulta de la baldosa no genera codigo: pondera por un nivel mas
 * las referencias del area de trabajo `w`, de 9 a 15 usos ponderados sobre una vida de 78 (prioridad
 * floor_log2(R) * R / L: de 3 * 9 / 78 = 0,346 a 3 * 15 / 78 = 0,577). La altura nueva tiene 10 usos
 * sobre 52 (0,577), de modo que con la envoltura el area queda empatada con ella y global-alloc la
 * asigna antes (desempate por numero de pseudo, ver abajo), y le da el primer
 * registro guardado, s0, como el original; sin la envoltura la altura nueva toma s0 y el area s4.
 *
 * El empate y su desempate vienen de la fuente de GCC 2.8.1 (global.c, lineas 594-616): el asignador
 * global ordena los pseudos por prioridad floor_log2(refs) * refs / vida y, a igual prioridad,
 * por numero de pseudo en orden de declaracion. 3 * 15 / 78 y 3 * 10 / 52 son el mismo racional
 * (15/26), de modo que la decision depende solo de ese desempate. El reparto es fragil: un uso
 * ponderado de mas o de menos en el area de trabajo o en la altura nueva rompe el empate e
 * invierte los registros.
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
                    } while (0);
                    if (!(w->res.flags & 8)) {
                        tope = r->techo - o->max.vy;
                        if (base < tope) {
                            tope = base;
                        }
                    } else if (cur >= base) {
                        goto soltar;
                    } else {
                        tope = cur;
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
            /* La condicion de perdida de suelo se guarda en una variable antes de la rama: sin ella el compilador la parte en dos saltos. */
            pierde_suelo = base < cur && modo != 8;
            if (pierde_suelo) {
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
            /* La mascara en una sentencia propia reproduce el original: carga de las banderas en v0, mascara en v1 y un solo and. */
            v = ~9;
            v &= o->flags14;
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
