#include "common.h"
#include "globales.h"
#include "gte.h"
#include "objetos.h"
#include "niveles.h"

/*
 * Manejador de la clase 0 de D_8005E35C: objeto con volumen escalado por su transformacion. En el
 * primer cuadro reserva el ayudante (si el objeto no tiene lista de animaciones se destruye; si no hay
 * ayudante libre el original se queda en un bucle sin salida), enlaza su coordenada a la del objeto
 * cuando el descriptor lo pide y escala las dos esquinas de la caja (+0x48 y +0x50) con una matriz
 * diagonal cuyas tres escalas son la parte baja de la escala del objeto. Cada cuadro termina
 * recalculando la matriz del objeto.
 */
void func_80025938(Objeto* o)
{
    MATRIX m;

    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
        if (o->lista == 0) {
            o->flags14 |= 0x100;
            return;
        }
        o->u78.ayudas = func_800363D4();
        if (o->u78.ayudas == 0) {
            for (;;) {
            }
        }
        if (o->lista->def->wA & 2) {
            o->u78.ayudas->flags8 |= 2;
            GsInitCoordinate2(0, o->u78.ayudas->pcoord);
            o->u78.ayudas->pcoord->super = &o->coord;
            o->coord.param = PARAMETROS_SDK(o);
            o->u78.ayudas->w14 = (s32)o->lista->def->tabla;
        }
        GEO_IDENTIDAD(&m);
        m.m[0][0] = (u16)o->coord.param->scale.vx;
        m.m[1][1] = (u16)o->coord.param->scale.vy;
        m.m[2][2] = (u16)o->coord.param->scale.vz;
        gte_SetRotMatrix(&m);
        gte_ldv0(&o->min);
        gte_rtv0();
        gte_stsv(&o->min);
        gte_ldv0(&o->max);
        gte_rtv0();
        gte_stsv(&o->max);
    }
    func_8001CF50(o);
}

/*
 * Manejador vacio de la clase 7 de D_8005E35C: el objeto no tiene logica propia. Conserva el prototipo
 * de la tabla (void (*)(Objeto*)) aunque no lea el parametro.
 */
void func_80025B24(Objeto* o)
{
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 760 con la configuracion versionada (-G0). El original reparte el lui de D_8006967C en a3 en las dos llamadas a func_8003F06C (v0 queda con la constante 1 y la segunda llamada la copia con move) y carga el pozo D_8006964C entre la lectura de u78 y su almacen; el compilador usa v0 para el lui y carga el pozo justo antes de la llamada. */
/*
 * Manejador de la clase 8 de D_8005E35C: cadena de segmentos que se balancea. En el primer cuadro
 * devuelve al pozo el primer ayudante, cuenta los que quedan, reparte el largo del objeto entre
 * ellos y rellena la caja. Cada cuadro recalcula el giro de cada eslabon con un seno tabulado
 * (con un desfase de 9 grados por eslabon), dispara un sonido al cruzar el cero del balanceo, gira
 * el conjunto, avanza la fase y amortigua la amplitud, y acumula con el GTE la extension total de la
 * cadena para fijar el alcance y la caja de colision.
 */
void func_80025B2C(Objeto* o)
{
    TrabajoCadena* t;
    GsCOORDINATE2* c;
    s16* tabla;
    s32 fase;
    s32 giro_y;
    Ayuda* pozo;
    void* area;

    t = TRABAJO_CADENA;
    area = (void*)0x1F800030;
    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
        func_8001F268(o, (BloqueTrabajo*)&o->i100, 5, 2, area);
        func_8001CF50(o);
        pozo = D_8006964C;
        t->nodo = o->u78.ayudas;
        o->u78.ayudas = (Ayuda*)t->nodo->cab.siguiente;
        o->u78.ayudas->pcoord->super = &o->coord;
        RemoveListNode((NodoLista*)pozo, (NodoLista*)t->nodo);
        t->nodo = o->u78.ayudas;
        t->n = 1;
        if (t->nodo->cab.siguiente != 0) {
            do {
                t->nodo = (Ayuda*)t->nodo->cab.siguiente;
                t->n = t->n + 1;
            } while (t->nodo->cab.siguiente != 0);
        }
        o->trabajo.h0A = o->min.vy / (s16)t->n;
        c = t->nodo->pcoord;
        OSC_AMPLITUD(o) = 0x64;
        OSC_FASE(o) = 0x118;
        OSC_I148(o) = 0;
        OSC_ULTIMO(o) = c;
        if (o->s1E == 0) {
            o->s1E = 0x80;
        }
        o->min.vx = -(u16)o->radio;
        o->max.vy = 0;
        o->max.vx = (u16)o->radio;
        if (o->flags08 & 0x400000) {
            o->w2E = o->radio;
            o->alcance2 = o->radio * o->radio;
        }
    }
    giro_y = o->param.giro.rotate.vy;
    o->param.giro.rotate.vy = giro_y - (giro_y / 0x1000) * 0x1000;
    if (!(o->flags08 & 0x400000) && OSC_ULTIMO(o) != 0) {
        fase = OSC_FASE(o);
        t->cabeceo = (D_8005E08C[fase] * OSC_AMPLITUD(o)) >> 10;
        t->giro.vx = 0;
        t->giro.vy = 0;
        t->giro.vz = 0;
        t->angulo = 0x118;
        c = OSC_ULTIMO(o);
        if (c->super != 0) {
            tabla = D_8005E08C;
            do {
                if (OSC_SEL(o) == c) {
                    t->angulo = 0xB4;
                }
                if (t->angulo >= 0xB5) {
                    t->giro.vx = ((t->cabeceo >> 3) * tabla[t->angulo]) >> 10;
                    c->flg = 0;
                    RotMatrix(&t->giro, &c->coord);
                    t->angulo -= 9;
                } else {
                    t->giro.vx = 0;
                    c->flg = 0;
                    RotMatrix(&t->giro, &c->coord);
                }
                c = c->super;
            } while (c->super != 0);
        }
        fase += 0x5A;
        OSC_SEL(o) = 0;
        if (fase >= 0x168) {
            fase -= 0x168;
        }
        t->giro.vx = (D_8005E08C[fase] * OSC_AMPLITUD(o)) >> 10;
        c->flg = 0;
        if ((s16)t->giro.vx < o->param.giro.rotate.vx) {
            if (OSC_SIGNO(o) == 0) {
                if (OSC_SONIDO(o) != 0) {
                    func_8003F06C(o, OSC_SONIDO(o), 1, D_8006967C);
                }
            }
            OSC_SIGNO(o) = 1;
        } else {
            if (OSC_SIGNO(o) == 1) {
                if (OSC_SONIDO(o) != 0) {
                    func_8003F06C(o, OSC_SONIDO(o), OSC_SIGNO(o), D_8006967C);
                }
            }
            OSC_SIGNO(o) = 0;
        }
        o->param.giro.rotate.vx = t->giro.vx;
        t->giro.vx = 0;
        t->giro.vy = 0;
        t->giro.vz = 0;
        o->coord.flg = 0;
        RotMatrixYXZ(&o->param.giro.rotate, &o->coord.coord);
        TransMatrix(&o->coord.coord, &o->param.trans);
        OSC_FASE(o) = OSC_FASE(o) + 4;
        if (OSC_FASE(o) >= 0x168) {
            OSC_FASE(o) = OSC_FASE(o) - 0x168;
        }
        if (OSC_FASE(o) & 2) {
            OSC_AMPLITUD(o) = OSC_AMPLITUD(o) - 1;
        }
        OSC_AMPLITUD(o) = OSC_AMPLITUD(o) - 1;
        if (OSC_AMPLITUD(o) < o->s1E) {
            OSC_AMPLITUD(o) = o->s1E;
        } else if (OSC_AMPLITUD(o) >= 0x12D) {
            OSC_AMPLITUD(o) = 0x12C;
        }
        t->ext.vx = 0;
        t->ext.vy = o->trabajo.h0A;
        t->ext.vz = 0;
        c = OSC_ULTIMO(o);
        if (c->super != 0) {
            do {
                gte_SetRotMatrix(&c->coord);
                gte_ldv0(&t->ext);
                gte_rtv0();
                gte_stlvnl(&t->r);
                t->r.vy += c->coord.t[1];
                t->r.vz += c->coord.t[2];
                t->ext.vy = t->r.vy;
                t->ext.vz = t->r.vz;
                c = c->super;
            } while (c->super != 0);
        }
        gte_SetRotMatrix(&c->coord);
        gte_ldv0(&t->ext);
        gte_rtv0();
        gte_stlvnl(&t->r);
        o->alcance2 = t->r.vx * t->r.vx + t->r.vz * t->r.vz + o->radio * o->radio;
        o->w2E = SquareRoot0(o->alcance2);
        if (t->r.vz < 0) {
            o->min.vz = o->w2E;
            o->max.vz = 0;
        } else {
            o->max.vz = o->w2E;
            o->min.vz = 0;
        }
        o->min.vy = t->r.vy;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_2", func_80025B2C);
#endif
