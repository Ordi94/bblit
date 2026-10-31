#include "common.h"
#include "gte.h"
#include "motor.h"
#include "animacion.h"
#include "objetos.h"

/*
 * Sprite del objeto en formato escalado: el bloque que sigue a los doce primeros bytes del
 * descriptor (func_8001E600). Pagina de textura en +0, v y bit alto en +2, paleta en +4 y +6,
 * anchura y altura de recorte en +0x10 y +0x12, y modo de color en +0x14 y +0x16.
 */
typedef struct SpriteEscalado {
    s16 s00;
    s16 s02;
    s16 s04;
    s16 s06;
    u16 w08;
    u16 w0A;
    u16 w0C;
    u16 w0E;
    s16 s10;
    u16 w12;
    s16 s14;
    s16 s16;
} SpriteEscalado;

/*
 * Sprite del objeto en formato plano (func_8001E528): coordenadas de textura repartidas en
 * bytes, paleta, pagina de textura y bandera de espejo.
 */
typedef struct SpritePlano {
    u8 pad00[4];
    u8 u0;
    u8 v0;
    u16 clut;
    u8 pad08[0x0C - 0x08];
    u8 u1;
    u8 v1;
    u16 tpage;
    u8 pad10[0x14 - 0x10];
    u8 u2;
    u8 v2;
    u8 pad16[0x1C - 0x16];
    u8 u3;
    u8 v3;
    u8 pad1E[0x20 - 0x1E];
    s32 bandera;
} SpritePlano;

/*
 * Asigna al sprite del objeto las coordenadas de textura del cuadro actual de un conjunto
 * (formato plano). Si el objeto usa el formato escalado (bandera 0x20) delega en
 * func_8001E600. `modo` con el bit 0 activo toma el cuadro tal cual; si no, pasa por la tabla
 * de indices del conjunto.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 1535 con la configuracion versionada (g = 8 del archivo). Mismos accesos y mismos almacenes; el original funde el desplazamiento de 16 bytes del registro tras la reunion de las dos ramas y reparte a0..a3 y t0 a las cuatro lecturas del registro, el C duplica el desplazamiento en cada rama y usa v0 y t0. */
void func_8001E528(Objeto* o, BloqueTrabajo* c, u32 modo)
{
    Fotograma* r;
    SpritePlano* p;
    u16 indice;
    u8 u;
    u8 v;
    u16 w;
    u16 h;
    u16 pagina;
    s8 u_fin;
    s8 v_fin;

    if (o->flags08 & 0x20) {
        func_8001E600(o, c, modo);
        return;
    }
    /* El cuadro actual (h02, con signo en el cursor) se lee con lhu: lhu 0x2 en 0x8001E55C y 0x8001E610. */
    if (modo & 1) {
        indice = (u16)c->cuadro;
    } else {
        indice = c->duraciones[(u16)c->cuadro].indice;
    }
    r = c->fotogramas + indice;
    p = (SpritePlano*)((u8*)o->u78.p + 0xC);
    u = r->u;
    v = r->v;
    w = r->w0C;
    h = r->w0E;
    pagina = r->pagina;
    u_fin = u + (w - 1);
    p->tpage = pagina;
    p->v0 = v;
    p->v1 = v;
    v_fin = v + (h - 1);
    p->u0 = u;
    p->u1 = u_fin;
    p->u2 = u;
    p->v2 = v_fin;
    p->u3 = u_fin;
    p->v3 = v_fin;
    p->clut = r->h0A;
    p->bandera = r->flags & 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_8001E528);
#endif

/*
 * Igual que func_8001E528 para el formato escalado: la profundidad de color del cuadro (bits
 * 7 y 8 de la pagina) desplaza las coordenadas horizontales (2 = 4 bits, 1 = 8 bits, 0 = 16
 * bits) y fija la anchura de la textura y el modo del sprite.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 2665 con la configuracion versionada (g = 8 del archivo). Mismos accesos y almacenes; el original calcula el desplazamiento de color en t2 y deja el puntero al sprite en v1, el C reparte otros registros y reordena las lecturas del registro del cuadro. */
void func_8001E600(Objeto* o, BloqueTrabajo* c, u32 modo)
{
    Fotograma* r;
    SpriteEscalado* p;
    u16 indice;
    s32 desplazamiento;

    /* El cuadro actual (h02, con signo en el cursor) se lee con lhu: lhu 0x2 en 0x8001E55C y 0x8001E610. */
    if (modo & 1) {
        indice = (u16)c->cuadro;
    } else {
        indice = c->duraciones[(u16)c->cuadro].indice;
    }
    r = c->fotogramas + indice;
    desplazamiento = 2 - ((r->pagina >> 7) & 3);
    p = (SpriteEscalado*)((u8*)o->u78.p + 0xC);
    p->s00 = (r->u >> desplazamiento) + ((r->pagina & 0xF) << 6);
    p->s02 = r->v + ((r->pagina << 4) & 0x100);
    p->w08 = c->w2C;
    p->s10 = r->w0C >> desplazamiento;
    p->w12 = r->w0E;
    p->w0A = c->w2E;
    p->s04 = (r->h0A & 0x3F) * 0x10;
    p->s06 = r->h0A >> 6;
    p->w0C = c->w30;
    p->w0E = c->w32;
    if (desplazamiento == 2) {
        p->s14 = 0x10;
        p->s16 = 1;
        return;
    }
    if (desplazamiento == 1) {
        p->s14 = 0x100;
        p->s16 = desplazamiento;
        return;
    }
    p->s14 = 0;
    p->s16 = 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_8001E600);
#endif

/*
 * Avanza un cuadro la animacion de un objeto cuyo dibujo es un sprite. `modo` trae las ordenes:
 * 0x20 reinicia (estado 0x100, devuelve 0x20), 0x4 quita la pausa, 0x10 la pone (devuelve 0x200)
 * y 0x1, 0x2 u 0x8 empiezan una animacion (con 0x8 no se busca: se reutiliza el nodo ya
 * localizado). Devuelve 0x200 mientras la animacion sigue, 0x100 al terminar y 0x400 si la
 * animacion pedida no existe. `area` es el area de trabajo del llamador.
 *
 * El original crea el ayudante raiz del objeto la primera vez y se queda en un bucle infinito si
 * el pozo esta agotado. En cada cuadro dispara los sonidos y los eventos del cuadro actual: un
 * evento puede crear un hijo acoplado, un objeto suelto, agarrar o soltar al protagonista.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 570 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difieren el temporal del cociente de las multiplicaciones (el original usa $t4, el C $t5; la macro de escala 0x1000 escribe $t4 y lo declara destruido porque su cuerpo lo escribe, y esa lista no se altera), el reparto de $a0/$v1 en la lectura del estado y el orden de cuatro almacenes del bloque de parametros de agarre. */
u32 AvanzarAnimacionSprite(Objeto* o, BloqueTrabajo* c, u32 anim, u32 modo, u8* area)
{
    NodoAnimacion* n;
    Fotograma* fot;
    Ayuda* ay;
    Objeto* h;
    Objeto* j;
    GsCOORDINATE2* nc;
    u16 i;
    u16 i0;
    u16 r;
    s32 k;
    s32 t;
    s32 m;
    s32 reserva[4];        /* sin uso: reserva los 16 bytes que el original deja antes del giro y desplaza el marco a 0x78 */
    SVECTOR giro;
    VECTOR pos;
    AcumuladorNodos acc;

    if (modo & 0x20) {
        c->flags18 = 0x100;
        return 0x20;
    }
    if (modo & 4) {
        if (c->flags18 & 0x10) {
            c->flags18 = c->flags18 & ~0x10;
            goto sigue;
        }
    }
    if (modo & 0x10) {
        c->flags18 = c->flags18 | 0x10;
        return 0x200;
    }
sigue:
    c->flags18 = c->flags18 & ~0x3000;
    if (o->u78.p == 0) {
        ay = func_800363D4();
        o->u78.ayudas = ay;
        if (ay == 0) {
            for (;;) {
            }
        }
        for (n = o->lista; n != 0; n = n->sig) {
            if (n->def->tipo == 8) {
                break;
            }
        }
        c->tabla = n->def->tabla;
        if (o->flags08 & 0x200000) {
            o->u78.ayudas->flags8 = 1;
            if (o->p70 == 0) {
                o->coord.param = PARAMETROS_SDK(o);
                o->coord.super = 0;
            }
            func_8001CF50(o);
            func_8001CFCC(&o->coord);
        } else {
            o->u78.ayudas->flags8 = 0x20;
        }
    }
    if (modo & 0xB) {
        if (!(modo & 8)) {
            for (n = o->lista; n != 0; n = n->sig) {
                if (n->def->tipo == anim) {
                    break;
                }
            }
            if (n == 0) {
                c->flags18 = 0x100;
                return 0x400;
            }
        }
        fot = c->tabla->fotogramas;
        if (o->flags08 & 0x200000) {
            k = o->param.escala.vx;
            o->min.vx = o->min.vz = (-(fot->w0C >> 1) * k) >> 12;
            o->min.vy = 0;
            o->max.vx = o->max.vz = ((fot->w0C >> 1) * k) >> 12;
            o->max.vy = -((fot->w0E * o->param.escala.vy) >> 12);
            if (o->flags0C & 0x4000000) {
                o->param.trans.vy = o->param.trans.vy + (fot->w0E >> 1);
            }
            m = fot->w0C * 2;
            t = (m * o->param.escala.vx) >> 12;
            o->w2E = (u16)o->max.vx + t;
            o->alcance2 = o->w2E * o->w2E;
            o->radio = (u16)o->radio + t;
        }
        c->i14 = anim;
        c->sonidos = (RegistroSonido*)n->def->sonidos;
        c->n_sonidos = n->def->n_sonidos;
        c->eventos = (RegistroEvento*)n->def->eventos;
        c->n_eventos = n->def->n_eventos;
        c->fotogramas = fot;
        c->b04 = 0;
        c->flags18 = modo | ANIM_RECIEN_INICIADA | ANIM_EN_CURSO;
        FLUJO_PISTAS(c) = (u32*)fot;
        c->ultimo = n->def->n_cuadros - 1;
        c->duraciones = (ParCuadro*)n->def->tabla;
        c->cuadro = 0;
        c->ticks = c->espera = c->duraciones->ticks;
    }
    if ((u16)c->cuadro == c->ultimo) {
        if (c->ticks == 0) {
            t = c->flags18;
            if (t & 2) {
                t = (t & ~0x200) | 0x100;
                c->flags18 = t;
                if (t & 0x800) {
                    return 0x200;
                }
                return 0x100;
            }
            if (t & 1) {
                c->flags18 = t | 0x80;
            }
            t = c->duraciones->ticks;
            c->cuadro = 0;
            c->flags18 = c->flags18 | ANIM_RECIEN_INICIADA;
            c->ticks = c->espera = t;
        }
    }
    ((DibujarSprite)func_8001E528)(o, c, 0, area);
    if (c->ticks == 0) {
        if (c->n_sonidos != 0) {
            for (i = 0; i < c->n_sonidos; i++) {
                if ((u16)c->cuadro == c->sonidos[i].cuadro) {
                    func_8003F06C(o, c->sonidos[i].id, 1, D_8006967C);
                }
            }
        }
    }
    r = 1;
    if (c->n_eventos != 0) {
        if (c->ticks == 0) {
            i = 0;
            if (c->ticks < c->n_eventos) {
                do {
                    if ((u16)c->cuadro == c->eventos[i].cuadro && o->raiz_ayudantes != 0) {
                        r = TestLogicCond(o, c->eventos[i].cond);
                        if (r == 0) {
                            goto siguiente;
                        }
                        RunLogicAction(o, c->eventos[i].cond);
                        if (c->eventos[i].banderas & EVENTO_LIBERA_HIJO) {
                            if (o->p6C != 0) {
                                func_8003502C(o->p6C);
                                o->p6C = 0;
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_HIJO_ACOPLADO) {
                            h = func_80036734((s16)c->eventos[i].id, (s32*)&pos, (u16*)&giro);
                            if (h != 0) {
                                o->flags18 |= ANIM_HIJO_VIVO;
                                GEO_CERO_W(&h->portado.trans);
                                GEO_CERO_WH(&h->portado.giro);
                                MOTOR_UNOS_W(&h->portado.escala);
                                if (h->w1C == 1) {
                                    D_80069608 |= 1;
                                }
                                if (h->p70 != 0 && h->p70->p6C == h) {
                                    h->p70->p6C = 0;
                                }
                                h->coord.super = o->raiz_ayudantes;
                                h->w26 = o->w26;
                                h->p70 = o;
                                h->coord.param = (GsCOORD2PARAM*)&h->portado;
                                if (!(c->eventos[i].banderas & EVENTO_SIN_SUSTITUIR)) {
                                    if (o->p6C != 0) {
                                        func_8003502C(o->p6C);
                                    }
                                    o->p6C = h;
                                }
                                nc = &h->coord;
                                h->w26 = o->w26;
                                func_8001CFCC(nc);
                                acc.nodo = nc;
                                func_8001CE64(&acc);
                                h->param.trans.vx = acc.acc.vx;
                                h->param.trans.vy = acc.acc.vy;
                                h->param.trans.vz = acc.acc.vz;
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_HIJO_SUELTO) {
                            h = func_80036734((s16)c->eventos[i].id, &o->objetivo.vx, &o->param.giro.u.x);
                            if (h != 0) {
                                h->w26 = o->w26;
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_HIJO_CON_GIRO) {
                            h = func_80036734((s16)c->eventos[i].id, &o->objetivo.vx,
                                              (u16*)((u8*)o->raiz_ayudantes->param + 0x10));
                            if (h != 0) {
                                h->w26 = o->w26;
                                h->param.giro.u.y = h->param.giro.u.y + (u16)o->raiz_ayudantes->super->param->rotate.vy;
                                func_8001CF50(h);
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_AGARRA) {
                            if (!(D_80069698->flags14 & 0x3000000)) {
                                if (D_80069698->p70 == 0) {
                                    if ((s16)func_80018D98(D_80069698, &o->objetivo, area) != 0) {
                                        if (c->eventos[i].banderas & EVENTO_AGARRE_SIN_DESFASE) {
                                            D_80069698->u18C.agarre.trans.vx = 0;
                                            D_80069698->u18C.agarre.trans.vy = 0;
                                            D_80069698->u18C.agarre.trans.vz = 0;
                                        } else {
                                            D_80069698->u18C.agarre.trans.vx = D_80069698->param.trans.vx - o->objetivo.vx;
                                            D_80069698->u18C.agarre.trans.vy = D_80069698->param.trans.vy - o->objetivo.vy;
                                            D_80069698->u18C.agarre.trans.vz = D_80069698->param.trans.vz - o->objetivo.vz;
                                        }
                                        D_80069698->param.trans.vx = o->objetivo.vx;
                                        D_80069698->param.trans.vy = o->objetivo.vy;
                                        D_80069698->param.trans.vz = o->objetivo.vz;
                                        D_80069698->u18C.agarre.escala.vz = D_80069698->param.escala.vz;
                                        D_80069698->u18C.agarre.escala.vx = D_80069698->param.escala.vx;
                                        D_80069698->u18C.agarre.giro.u.x = 0;
                                        D_80069698->u18C.agarre.giro.u.y = 0;
                                        D_80069698->u18C.agarre.giro.u.z = 0;
                                        D_80069698->u18C.agarre.escala.vy = D_80069698->param.escala.vy;
                                        D_80069698->coord.param = (GsCOORD2PARAM*)&D_80069698->u18C.agarre;
                                        D_80069698->w17E = 0;
                                        D_80069698->coord.super = o->raiz_ayudantes;
                                        D_80069698->w17C = c->eventos[i].id;
                                        D_80069698->flags14 = 0x2000000;
                                        o->p6C = D_80069698;
                                        D_80069698->p70 = o;
                                        func_8001CFCC(&D_80069698->coord);
                                    }
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_SUELTA) {
                            if (D_80069698->p70 == o) {
                                if (o->p6C != 0) {
                                    D_80069698->param.giro.u.x = o->param.giro.u.x;
                                    D_80069698->param.giro.u.y = o->param.giro.u.y + 0x800;
                                    i0 = o->param.giro.u.z;
                                    D_80069698->coord.param = PARAMETROS_SDK(D_80069698);
                                    D_80069698->coord.super = 0;
                                    D_80069698->p70 = 0;
                                    D_80069698->param.giro.u.z = i0;
                                    o->p6C = 0;
                                    D_80069698->w17E = 0;
                                    D_80069698->w17C = c->eventos[i].id;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_COLOCA) {
                            if (!(D_80069698->flags14 & 0x3000000)) {
                                if (D_80069698->p70 == 0) {
                                    if ((s16)func_80018D98(D_80069698, &o->objetivo, area) != 0) {
                                        j = D_80069698;
                                        j->param.giro.u.y = o->param.giro.u.y + 0x800;
                                        j->w17E = 0;
                                        j->w17C = c->eventos[i].id;
                                        j->flags14 = 0x2000000;
                                    }
                                }
                            }
                        }
                    }
                    if (r == 1) {
                        break;
                    }
siguiente:
                    i++;
                } while (i < c->n_eventos);
            }
        }
    }
    if (c->ticks == 0) {
        c->cuadro = c->cuadro + 1;
        c->ticks = c->espera = c->duraciones[(u16)c->cuadro].ticks;
    }
    c->ticks = c->ticks - 1;
    if ((u16)c->cuadro == c->ultimo) {
        c->flags18 = c->flags18 | ANIM_ULTIMO_CUADRO;
    }
    return 0x200;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", AvanzarAnimacionSprite);
#endif

/* Pendiente de traducir: rutina de 0xFA8 bytes (unas mil instrucciones) que llama a func_8001D028,
 * func_8001CFCC, func_80036734 y AplicarCuadro; no hay C escrito todavia. */
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_8001F268);

/*
 * Prepara un movimiento senoidal del objeto (salto o bamboleo): fase inicial 0x400, velocidad
 * de fase `paso` y amplitud `amplitud`; enciende la bandera 1 y apaga las que dependen del
 * movimiento anterior (mascara 0xEFFFF9F1).
 */
void func_80020210(Objeto* o, u16 paso, u16 amplitud)
{
    o->h10A = 0;
    o->h108 = 0x400;
    o->h106 = paso;
    o->h104 = amplitud;
    o->flags14 = (o->flags14 | 1) & 0xEFFFF9F1;
}

/*
 * Avanza un cuadro el movimiento senoidal preparado por func_80020210: la altura relativa es
 * -amplitud * sen(fase) (doblada si la bandera 8 esta activa, es decir en la segunda mitad del
 * arco) y la fase crece `paso` cada cuadro hasta 0xC00. Al terminar deja la altura a cero, apaga
 * las banderas de movimiento y marca 0x200 si el objeto no estaba en suelo.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 605 con la configuracion versionada (g = 8 del archivo). La condicion de continuar (bit 4 apagado o bit 0x10 activo) y la reunion de las dos ramas de la altura no se reproducen: el compilador adelanta la carga de las banderas y repite el almacen de h10A en cada rama. */
void func_80020240(Objeto* o)
{
    s32 v;
    s32 t;
    s32 u;
    s32 f;

    if (o->h108 < 0x800) {
        o->flags14 = o->flags14 & ~8;
    } else {
        o->flags14 = o->flags14 | 8;
    }
    t = o->h108;
    u = o->flags14 & 4;
    if (t < 0xC01 && (u == 0 || (o->flags14 & 0x10))) {
        if (o->flags14 & 8) {
            v = ((-o->h104 * rsin(t)) >> 12) * 2;
        } else {
            v = (-o->h104 * rsin(t)) >> 12;
        }
        o->h10A = v;
        o->h108 = o->h108 + o->h106;
        return;
    }
    f = o->flags14;
    o->h10A = 0;
    o->flags14 = f & ~9;
    if (!(f & 2)) {
        o->flags14 = (f & ~9) | 0x200;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_80020240);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 9105 con la configuracion versionada (g = 8 del archivo). El original recorre los peldanos con punteros que avanzan 0x14 (x con uno y y, z con otro) y deja punto y mascara en s5 y s4; el compilador recalcula el indice en el bucle de busqueda y reparte punto y mascara al reves. */
/*
 * Busca el objeto solido que sirve de apoyo bajo un punto. Recorre la lista de solidos (D_80069630)
 * y, para cada uno que cumple la mascara, esta visible, es del mismo grupo, es un volumen solido
 * distinto del consultante, tiene modelo y queda al alcance en el plano, pasa el punto al sistema
 * local del solido (giro inverso). Si el solido es de caja plana (bandera 0x400000) comprueba el
 * semilado y la altura de la caja; si no, recorre la cadena de ayudantes de su modelo, acumula con
 * el GTE la posicion de cada peldano (hasta 20) y busca el que contiene el punto con holgura
 * vertical de 0x12C. Devuelve el apoyo hallado (dentro del area de trabajo) o nulo.
 */
ApoyoHallado* func_80020354(Objeto* o, VECTOR* punto, SondaApoyo* w, u32 mascara)
{
    VECTOR cero;
    GsCOORDINATE2* n;
    s16 i;
    s16 j;
    s16 k;
    s16 x1;
    s16 y1;
    s16 z1;
    s32 r;
    s32 h;

    w->caja_min.vx = o->min.vx;
    w->caja_min.vy = o->min.vy;
    w->caja_min.vz = o->min.vz;
    w->caja_max.vx = o->max.vx;
    w->caja_max.vy = o->max.vy;
    w->cur = D_80069630;
    w->caja_max.vz = o->max.vz;
    if (w->cur != 0) {
        do {
            if ((w->cur->flags08 & mascara) && !(w->cur->flags14 & 1) && (s16)w->cur->w26 == (s16)o->w26 &&
                w->cur->tipo_volumen == 2 && o != w->cur && w->cur->u78.p != 0) {
                GEO_CARGAR_W(punto);
                GEO_RESTAR_W(&w->cur->param.trans);
                GEO_GUARDAR_H_T4(&w->local);
                GEO_NORMA2_XZ(&w->local, &w->dist);
                if (w->cur->alcance2 >= w->dist) {
                    GEO_COMPLEMENTO(&w->cur->param.giro);
                    GEO_GUARDAR_H_T1(&w->rot);
                    w->rot.vx = 0;
                    w->rot.vz = 0;
                    RotMatrixZYX(&w->rot, &w->m);
                    ApplyMatrix(&w->m, &w->local, &w->out);
                    r = w->cur->radio;
                    w->dist = r;
                    if (w->cur->flags08 & 0x400000) {
                        if (w->out.vx >= -r && w->out.vx <= r && w->out.vz >= -r && w->out.vz <= r) {
                            h = w->out.vy - 0x12C;
                            if (h >= 0 && w->cur->trabajo.h0A >= h) {
                                w->res.objeto = w->cur;
                                w->res.coord = &w->cur->coord;
                                w->res.h0A = w->out.vy;
                                return &w->res;
                            }
                        }
                    } else {
                        w->ptr = w->cur->u78.ayudas;
                        while (w->ptr->cab.siguiente != 0) {
                            w->ptr = (Ayuda*)w->ptr->cab.siguiente;
                        }
                        n = w->ptr->pcoord;
                        GEO_CERO_W(&cero);
                        gte_SetTransVector(&cero);
                        i = 0;
                        if (n->super != 0) {
                            for (; n->super != 0; i++) {
                                if (i >= 0x14) {
                                    break;
                                }
                                w->pel[i].x = (u16)n->param->trans.vx;
                                w->pel[i].y = (u16)n->param->trans.vy;
                                w->pel[i].z = (u16)n->param->trans.vz;
                                w->pel[i].nodo = n;
                                if (i >= 2) {
                                    gte_SetRotMatrix(&w->pel[i - 1].nodo->coord);
                                    x1 = w->pel[i - 1].x;
                                    y1 = w->pel[i - 1].y;
                                    z1 = w->pel[i - 1].z;
                                    for (j = i - 2; j >= 0; j--) {
                                        gte_ldv0(&w->pel[j]);
                                        gte_rtv0();
                                        gte_stsv(&w->pel[j]);
                                    }
                                    for (j = i - 2; j >= 0; j--) {
                                        w->pel[j].x += x1;
                                        w->pel[j].y += y1;
                                        w->pel[j].z += z1;
                                    }
                                }
                                n = n->super;
                            }
                        }
                        w->rot.vx = (u16)n->param->rotate.vx;
                        w->rot.vy = 0;
                        w->rot.vz = 0;
                        RotMatrixZYX(&w->rot, &w->m);
                        gte_SetRotMatrix(&w->m);
                        for (k = 0; k < i; k++) {
                            gte_ldv0(&w->pel[k]);
                            gte_rtv0();
                            gte_stsv(&w->pel[k]);
                        }
                        w->pel[0].largo = 0;
                        w->pel[0].alto = w->cur->trabajo.h0A;
                        for (k = 1; k < i; k++) {
                            w->pel[k].alto = w->pel[k - 1].y - w->pel[k].y;
                            w->pel[k].largo = w->pel[k - 1].z - w->pel[k].z;
                        }
                        for (k = 0; k < i; k++) {
                            r = w->dist;
                            if (w->out.vx >= -r && w->out.vx <= r) {
                                if (w->pel[k].largo >= 0) {
                                    if (w->pel[k].z + w->pel[k].largo + r < w->out.vz || w->out.vz < w->pel[k].z - r) {
                                        continue;
                                    }
                                } else {
                                    if (w->out.vz < w->pel[k].z + w->pel[k].largo - r || w->pel[k].z + r < w->out.vz) {
                                        continue;
                                    }
                                }
                                h = w->out.vy - 0x12C;
                                if (w->pel[k].y < h && h < w->pel[k].y + w->pel[k].alto) {
                                    w->cur->portado.trans.vz = (s32)w->pel[k].nodo;
                                    w->res.coord = &w->cur->coord;
                                    w->res.objeto = w->cur;
                                    w->res.h0A = w->out.vy;
                                    w->res.x = w->pel[k].x;
                                    w->res.z = w->pel[k].z;
                                    return &w->res;
                                }
                            }
                        }
                    }
                }
            }
            w->cur = w->cur->sig10;
        } while (w->cur != 0);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_80020354);
#endif

/*
 * Busca el peldano que corresponde a la altura del objeto sobre el objeto de apoyo (p70):
 * entrega el apoyo por *apoyo y devuelve 1 si el objeto esta por encima del peldano, 2 si
 * esta en el suelo del apoyo y 0 si lo toca; guarda en el apoyo la altura del peldano
 * alcanzado (+0x13C). Si el apoyo es plano (bandera 0x400000) solo compara con su altura.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 2360 con la configuracion versionada (g = 8 del archivo). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica. */
u8 func_80020A90(Objeto* o, Movimiento* d, Objeto** apoyo)
{
    Objeto* t;
    NodoPeldano* nodo;
    s32 altura;
    s32 acc;
    s32 v;
    s32 paso;

    t = o->p70;
    *apoyo = t;
    if (o->p70 != NULL) {
        nodo = (NodoPeldano*)t->u78.p; /* lw 0x78(t): cabeza de la lista de peldanos */
        if (t->flags08 & 0x400000) {
            altura = o->u18C.agarre.trans.vy + d->dy - 0x12C;
            if (altura <= 0) {
                return 2;
            }
            return altura >= t->trabajo.h0A;
        }
        altura = o->u18C.agarre.trans.vy + d->dy - 0x12C;
        acc = 0;
        if (nodo != NULL) {
            paso = (u16)t->trabajo.h0A;
            v = acc + paso;
            do {
                acc = v;
                if (altura < (s16)v) {
                    break;
                }
                nodo = nodo->sig;
                v = acc + paso;
            } while (nodo != NULL);
        }
        if (nodo != NULL && altura > 0) {
            t->portado.trans.vz = nodo->w10;
            return 0;
        }
        (*apoyo)->portado.trans.vz = ((NodoPeldano*)(*apoyo)->u78.p)->w10;
        if (altura > 0) {
            return 1;
        }
        return 2;
    }
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_80020A90);
#endif
