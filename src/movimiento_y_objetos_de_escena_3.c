#include "common.h"
#include "gte.h"
#include "motor.h"
#include "animacion.h"
#include "objetos.h"
#include "arranque.h"

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
/*
 * La coordenada u del cuadro comparte la variable `coord_textura` con la copia del modo de la rama que delega:
 * en el original u es un pseudo que vive en mas de un bloque y se asigna despues de los locales (a3), mientras que
 * la pagina de textura, local del bloque de lectura del fotograma, toma v0.
 *
 * El decremento-incremento de la rama de la llamada no genera codigo. Causa medida: sin el, el pseudo de la
 * variable compartida (93) tiene 6 usos sobre 15 instrucciones (prioridad 2 * 6 / 15 = 0,80) y el puntero al
 * fotograma (83) 9 sobre 26 (3 * 9 / 26 = 1,04), de modo que el puntero se asigna primero, toma a3 y u cae en t0
 * (60). Con la pareja la variable pasa a 10 usos (3 * 10 / 15 = 2,0), se asigna antes que el puntero, toma a3 y el
 * puntero queda en t0, como el original. La pareja en la rama de la llamada, y no junto a la carga de u, deja el
 * orden de las lecturas intacto: junto a la carga alarga la cadena de u y el planificador la sube por encima de la
 * lectura del puntero del sprite (60). La forma del fuente original que producia este reparto se desconoce.
 */
void func_8001E528(Objeto* o, BloqueTrabajo* c, u32 modo)
{
    Fotograma* r;
    s32 w;
    SpritePlano* p;
    s8 u_fin;
    s8 v_fin;
    u8 v;
    s32 ancho;
    s32 clut;
    s32 alto_menos_uno;
    u32 pagina;
    u32 coord_textura;

    if (o->flags08 & 0x20) {
        coord_textura = modo;
        coord_textura--;
        coord_textura++;
        func_8001E600(o, c, coord_textura);
        return;
    }
    /* El fotograma se calcula en cada rama y no tras la union: con el indice calculado antes y las banderas
     * leidas al final, el compilador copia el desplazamiento del indice dentro de cada rama y mueve el
     * objeto a otro registro. */
    if (modo & 1) {
        r = c->fotogramas + (u16)c->cuadro;
    } else {
        r = c->fotogramas + c->duraciones[(u16)c->cuadro].indice;
    }
    p = (SpritePlano*)((u8*)o->u78.p + 0xC);
    /* La coordenada u se lee antes que v y vive en la variable que ya guarda la copia del modo: con una local
     * propia para u, o con v leida primero, el reparto de los registros de las lecturas del fotograma cambia. */
    coord_textura = r->u;
    v = r->v;
    w = r->w0C;
    /* La altura menos uno pasa por una variable de 32 bits: en la expresion `h - 1 + v` el compilador estrecha la resta a un byte (addiu 0xff) y el original suma -1. */
    alto_menos_uno = r->w0E - 1;
    pagina = r->pagina;
    /* La anchura menos uno pasa por una variable de 32 bits: con la suma en una sola expresion el compilador estrecha la carga de w a un byte (lbu) y el original carga media palabra (lhu). */
    ancho = w - 1;
    u_fin = coord_textura + ancho;
    p->tpage = pagina;
    clut = r->h0A;
    p->v0 = v;
    p->v1 = v;
    v_fin = alto_menos_uno + v;
    p->u0 = coord_textura;
    p->u1 = u_fin;
    p->u2 = coord_textura;
    p->v2 = v_fin;
    p->u3 = u_fin;
    p->v3 = v_fin;
    p->clut = clut;
    p->bandera = r->flags & 8;
}

/*
 * Igual que func_8001E528 para el formato escalado: la profundidad de color del cuadro (bits
 * 7 y 8 de la pagina) desplaza las coordenadas horizontales (2 = 4 bits, 1 = 8 bits, 0 = 16
 * bits) y fija la anchura de la textura y el modo del sprite.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas,
 * 60 insertadas o borradas). Mismos accesos y almacenes que el original. Ya igual al original: la cabecera (tabla de
 * fotogramas leida en la reunion de las ramas, `lw v1,0x20(t3)` en 0x30 con `nop` en el hueco del `j`), la constante 2
 * al abrir el grupo de lecturas (`li t0,2`, 0x3c), la pagina en v1 y el orden de las cadenas aritmeticas, la lectura
 * tardia del puntero crudo en v0 con el campo 0x0E entre ella y la suma del puntero al sprite, esa suma antes del
 * primer almacen, las cadenas de +0 y +2, la tabla de saltos y la cola. Lo que queda, medido en `diff`: (1) las cargas
 * de u (+8) y de v (+9) salen en el orden contrario (u en 0x120 y v en 0x124 frente a v en 0x44 y u en 0x48); (2)
 * registros: la constante 2 toma a3 (t0 en el original), el objeto t0 (a3), el puntero al sprite t0 (v1), el campo
 * 0x0E v1 (a3), y u, v y la anchura toman a1, a0 y a2 (a0, a2 y a1).
 *
 * La sentencia `fotogramas = c->fotogramas + indice;` esta escrita en cada rama del indice y no genera codigo distinto
 * del original: el salto cruzado funde las dos colas en una (`lw`, `sll` y `addu` de la reunion, 0x30 a 0x38; `-dJ`:
 * dos lecturas de +0x20 hasta la segunda pasada de saltos y una despues). Causa medida con `-dl` y `-dg`: con la
 * sentencia una sola vez tras la reunion el puntero al fotograma (pseudo 90) es un pseudo local del bloque y toma a0 en
 * la asignacion local, antes que las lecturas del fotograma; con una copia en cada rama el pseudo se asigna en dos
 * bloques, pasa a global (pseudo 89: 10 usos sobre 35 instrucciones, 0,857), se reparte despues de los locales y toma
 * t1, como el original, y deja a0 libre para las lecturas.
 *
 * La `do { } while (0);` no genera codigo: el ensamblador es el que saldria sin ella, pero las notas de bucle que deja
 * el parser actuan como limite de la primera planificacion. Cubre la suma del puntero al sprite y la lectura del campo
 * 0x0E. Causa medida con `-ds` y `-dl` sobre el pseudo 126 (puntero crudo): sin la envoltura tiene 3 usos y una vida de
 * 8 instrucciones (prioridad `floor_log2(R) * R / L` de 0,375) y la lectura sube sobre la aritmetica del fotograma; con
 * ella tiene 5 usos y una vida de 4 (2,5), la lectura queda tras la aritmetica y el crudo toma v0 (`126 in 2`). Con ella
 * el objeto (pseudo 80: 3 usos sobre 62 instrucciones) no puede tomar a3 porque la constante 2 (pseudo 111: 3 usos
 * sobre 72 instrucciones) ya lo ocupa en la asignacion local; sin ella el objeto toma a3 pero el crudo y la suma suben
 * sobre la aritmetica. Los valores de +0 y +2 se calculan antes de la envoltura, en `coordenada_u` y `v_pagina`, para
 * que su aritmetica quede antes de la nota. El cuerpo de la envoltura es codigo real de la funcion, sin `break` ni
 * `continue`. Se supone, sin verificar, que el original no lleva envoltura y que lo que fija ese orden es otra
 * construccion que el volcado no distingue. La forma del fuente original que producia este reparto se desconoce. */
void func_8001E600(Objeto* o, BloqueTrabajo* c, u32 modo)
{
    SpriteEscalado* p;
    s32 coordenada_u;
    s32 desplazamiento_color;
    s32 indice;
    s32 ancho_cuadro;
    /* El campo 0x2E del contexto se lee antes del almacen de `s10`, como el original (carga en 0x8001E698,
     * almacen en 0x8001E6A8). */
    u16 ancho_bloque;
    Fotograma* fotogramas;
    s16 v_pagina;
    /* El campo 0x0E del fotograma se lee antes del primer almacen, como el original (carga en 0x8001E67C,
     * almacen en 0x8001E6A4). */
    u16 campo_0e;

    /* El cuadro actual (h02, con signo en el cursor) se lee con lhu: lhu 0x2 en 0x8001E55C y 0x8001E610. */
    if (modo & 1) {
        indice = (u16)c->cuadro;
        /* Sentencia replicada: es la misma que la de las otras ramas. */
        fotogramas = c->fotogramas + indice;
    } else {
        indice = (c->duraciones + (u16)c->cuadro)->indice;
        /* Sentencia replicada: es la misma que la de las otras ramas. */
        fotogramas = c->fotogramas + indice;
    }
    ancho_cuadro = fotogramas->w0C;
    desplazamiento_color = 2 - ((fotogramas->pagina >> 7) & 3);
    /* Los valores de +0 y +2 se calculan antes de la envoltura (ver la cabecera). */
    coordenada_u = (fotogramas->u >> desplazamiento_color) + ((fotogramas->pagina & 0xF) << 6);
    v_pagina = fotogramas->v + (0x100 & (fotogramas->pagina << 4));
    do {
        p = (SpriteEscalado*)(0xC + (u8*)o->u78.p);
        campo_0e = fotogramas->w0E;
    } while (0);
    p->s00 = coordenada_u;
    p->s02 = v_pagina;
    p->w08 = c->w2C;
    ancho_bloque = c->w2E;
    p->s10 = ancho_cuadro >> desplazamiento_color;
    p->w12 = campo_0e;
    p->w0A = ancho_bloque;
    p->s04 = (0x3F & fotogramas->h0A) * 0x10;
    p->s06 = fotogramas->h0A >> 6;
    p->w0C = c->w30;
    p->w0E = c->w32;
    if (desplazamiento_color == 2) {
        p->s14 = 0x10;
        p->s16 = 1;
        return;
    }
    if (desplazamiento_color == 1) {
        p->s14 = 0x100;
        p->s16 = desplazamiento_color;
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
 *
 * Reserva de pila: el original reserva 0x78 (`addiu sp` en 0x8001E720) y sin la local el marco es
 * 0x68; la cifra medida sin la local es 361 y con ella 0. La reserva queda antes del giro,
 * como en el original.
 */
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
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[4];
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
            /* Las banderas se releen de la memoria en cada prueba, sin local: el original no las
             * conserva en un registro y la local cambia el reparto de los registros de argumento. */
            if (c->flags18 & 2) {
                c->flags18 = (c->flags18 & ~0x200) | 0x100;
                if (c->flags18 & 0x800) {
                    return 0x200;
                }
                return 0x100;
            }
            if (c->flags18 & 1) {
                c->flags18 = c->flags18 | 0x80;
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
            for (i = 0; i < c->n_eventos; i++) {
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
                                    /* Escala copiada en orden vx, vy, vz: el original carga
                                     * las componentes juntas y las almacena intercaladas
                                     * con los ceros del giro; con vz antes que vy el
                                     * planificador reparte esas cargas de otra forma. */
                                    D_80069698->u18C.agarre.escala.vx = D_80069698->param.escala.vx;
                                    D_80069698->u18C.agarre.escala.vy = D_80069698->param.escala.vy;
                                    D_80069698->u18C.agarre.escala.vz = D_80069698->param.escala.vz;
                                    D_80069698->u18C.agarre.giro.u.x = 0;
                                    D_80069698->u18C.agarre.giro.u.y = 0;
                                    D_80069698->u18C.agarre.giro.u.z = 0;
                                    D_80069698->coord.param = (GsCOORD2PARAM*)&D_80069698->u18C.agarre;
                                    D_80069698->coord.super = o->raiz_ayudantes;
                                    D_80069698->w17E = 0;
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
                /* C89 exige una sentencia tras la etiqueta; el salto de la prueba fallida llega aqui, al
                 * incremento del bucle, y la sentencia vacia no genera codigo. */
siguiente:
                ;
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

/*
 * Avanza un cuadro la animacion de un objeto con jerarquia de matrices (todo objeto cuyo dibujo no
 * es un sprite; el de sprite delega en AvanzarAnimacionSprite). `modo` trae las ordenes: 0 repite
 * el estado anterior, 0x20 reinicia (estado 0x100, devuelve 0x20), 0x4 quita la pausa, 0x10 la pone
 * (devuelve 0x200) y 0x1, 0x2 u 0x8 empiezan una animacion (con 0x8 no se busca: se reutiliza el
 * nodo ya localizado). Devuelve 0x200 mientras la animacion sigue, 0x100 al terminar y 0x400 si la
 * animacion pedida no existe. `area` es el area de trabajo del llamador.
 *
 * La primera vez crea el ayudante raiz aplicando el primer cuadro. En cada cuadro dispara los
 * sonidos y los eventos del cuadro actual: un evento puede crear un hijo acoplado o suelto, soltar
 * o reorientar el hijo, y agarrar, soltar o colocar al protagonista.
 *
 * Reserva de pila: el original reserva 0xB8 (`addiu sp` en 0x8001F268) y sin la local el marco es
 * 0x70 (sin las tres reservas juntas); la cifra medida sin la local es 1280 y con ella 0. Las
 * tres reservas (16, 24 y 32 bytes) dejan el vector de aparicion (giro y pos) en +0x28 y +0x30 y el acumulador de nodos
 * en +0x58, como el original.
 */
u32 func_8001F268(Objeto* o, BloqueTrabajo* c, u32 anim, s32 modo_ancho, u8* area)
{
    /* El recorte a 16 bits vive aqui y no en el prototipo (ver la declaracion en animacion.h). */
    u16 modo = modo_ancho;
    NodoAnimacion* n;
    CabeceraPistas* cab;
    Objeto* h;
    GsCOORDINATE2* nc;
    u16 i;
    u16 giro_z;
    u32 banderas_cursor;
    u32 banderas_cierre;
    u8 espera_pistas;
    u8 n_eventos_def;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[4];
    SVECTOR giro;
    VECTOR pos;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva2[6];
    AcumuladorNodos acc;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva3[8];

    if (o->flags08 & 0x200000) {
        return AvanzarAnimacionSprite(o, c, anim, modo, area);
    }
    if (modo == 0) {
        if (c->flags18 & ANIM_PAUSA) {
            return 0x200;
        }
        if (c->flags18 & ANIM_TERMINADA) {
            if (c->flags18 & ANIM_HIJO_VIVO) {
                return 0x200;
            }
            return 0x100;
        }
    } else {
        if (modo & 0x20) {
            c->flags18 = ANIM_TERMINADA;
            return 0x20;
        }
        if (modo & 4) {
            if (c->flags18 & ANIM_PAUSA) {
                c->flags18 = c->flags18 & ~ANIM_PAUSA;
                goto sigue;
            }
        }
        if (modo & 0x10) {
            c->flags18 = c->flags18 | ANIM_PAUSA;
            return 0x200;
        }
    }
sigue:
    c->flags18 = c->flags18 & ~(ANIM_RECIEN_INICIADA | ANIM_ULTIMO_CUADRO);
    if (o->u78.p == 0) {
        for (n = o->lista; n != 0; n = n->sig) {
            if (n->def->tipo == 7) {
                break;
            }
        }
        c->fotogramas = (Fotograma*)n->def->tabla;
        for (n = o->lista; n != 0; n = n->sig) {
            if (n->def->tipo == 4) {
                break;
            }
        }
        FLUJO_PISTAS(c) = ((CabeceraPistas*)n->def->tabla)->flujo;
        c->cuadro = 0;
        AplicarCuadro(o, c, (AreaCuadro*)area);
        o->u78.ayudas->coord.super = &o->coord;
        if (o->p70 == 0) {
            o->coord.param = PARAMETROS_SDK(o);
            o->coord.super = 0;
        }
        c->flags18 = c->flags18 & ~0x4000;
        func_8001CF50(o);
    }
    if (modo & 0xB) {
        if (modo & 8) {
            cab = CABECERA_PISTAS(c);
        } else {
            for (n = o->lista; n != 0; n = n->sig) {
                if (n->def->tipo == anim) {
                    break;
                }
            }
            if (n == 0) {
                c->flags18 = ANIM_TERMINADA;
                return 0x400;
            }
            cab = (CabeceraPistas*)n->def->tabla;
        }
        /* El numero de eventos y los ticks de la cabecera se leen antes de escribir en el cursor: una
         * lectura por otro puntero no sube sobre un almacen anterior, y el original las hace antes. */
        c->i14 = anim;
        c->sonidos = (RegistroSonido*)n->def->sonidos;
        c->n_sonidos = n->def->n_sonidos;
        c->eventos = (RegistroEvento*)n->def->eventos;
        n_eventos_def = n->def->n_eventos;
        c->duraciones = (ParCuadro*)cab;
        c->b04 = 0;
        c->flags18 = (modo | ANIM_RECIEN_INICIADA | ANIM_EN_CURSO) & 0xFFFF;
        c->n_eventos = n_eventos_def;
        FLUJO_PISTAS(c) = cab->flujo;
        c->ultimo = cab->n_cuadros - 1;
        espera_pistas = CABECERA_PISTAS(c)->espera;
        c->cuadro = 0;
        c->ticks = 0;
        c->espera = espera_pistas;
    }
    if (c->ticks == 0) {
        if ((u16)c->cuadro == c->ultimo) {
            o->flags14 = o->flags14 & 0xFFF7EFFF;
            /* Las banderas se leen una vez y la misma copia sirve al final de la animacion de una sola
             * pasada (termina) y al marcar el regreso al primer cuadro. */
            banderas_cursor = c->flags18;
            if (banderas_cursor & ANIM_UNA_PASADA) {
                goto termina;
            }
            if (banderas_cursor & ANIM_EN_BUCLE) {
                c->flags18 = banderas_cursor | ANIM_VUELTA;
            }
            cab = CABECERA_PISTAS(c);
            FLUJO_PISTAS(c) = cab->flujo;
            c->ultimo = cab->n_cuadros - 1;
            c->cuadro = 0;
            c->ticks = 0;
            c->flags18 = c->flags18 | ANIM_RECIEN_INICIADA;
            AplicarCuadro(o, c, (AreaCuadro*)area);
        } else if (c->b04 != 0) {
            if (c->b04 + (u16)c->cuadro < c->ultimo) {
                c->cuadro = c->b04 + ((u16)c->cuadro + 0xFFFF);
                if (c->b04 != 0) {
                    do {
                        AplicarCuadro(o, c, (AreaCuadro*)area);
                        c->b04 = c->b04 - 1;
                    } while (c->b04 != 0);
                }
            } else {
                c->cuadro = c->ultimo - 1;
                c->ticks = c->espera;
            }
        } else {
            AplicarCuadro(o, c, (AreaCuadro*)area);
        }
        if (c->ticks == 0) {
            if (c->n_sonidos != 0) {
                for (i = 0; i < c->n_sonidos; i++) {
                    if ((u16)c->cuadro == c->sonidos[i].cuadro) {
                        if (c->sonidos[i].cuenta == 0) {
                            c->sonidos[i].cuenta = c->sonidos[i].recarga;
                            func_8003F06C(o, c->sonidos[i].id, 1, D_8006967C);
                        } else {
                            c->sonidos[i].cuenta = c->sonidos[i].cuenta - 1;
                        }
                    }
                }
            }
        }
        if (c->n_eventos != 0) {
            if (c->ticks == 0) {
                /* Con "for" el compilador sustituye el cero inicial por el registro de ticks (que vale
                 * cero aqui) en la prueba previa, como el original; con "do { } while" precedido de
                 * "if (ticks < n_eventos)" reparte al reves los dos contadores de 8 bits. */
                for (i = 0; i < c->n_eventos; i++) {
                    if (((u16)c->cuadro == c->eventos[i].cuadro || (c->eventos[i].banderas & 0x800))
                        && (o->raiz_ayudantes != 0 || (c->eventos[i].banderas & 0x4000))
                        && (u16)TestLogicCond(o, c->eventos[i].cond) != 0) {
                        RunLogicAction(o, c->eventos[i].cond);
                        if (c->eventos[i].banderas & EVENTO_LIBERA_HIJO) {
                            if (o->p6C != 0) {
                                func_8003502C(o->p6C);
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
                                if (o == D_80069698) {
                                    h->flags0C |= 0x20000;
                                }
                                if (c->eventos[i].banderas & EVENTO_COMPONE) {
                                    func_8001CFCC(&h->coord);
                                    GEO_IDENTIDAD(&h->coord.coord);
                                    nc = o->raiz_ayudantes;
                                    if (nc != 0) {
                                        do {
                                            MulMatrix2(&nc->coord, &h->coord.coord);
                                            nc = nc->super;
                                        } while (nc != 0);
                                    }
                                    h->flags0C |= 0x20;
                                } else {
                                    h->param.escala.vx = o->raiz_ayudantes->param->scale.vx;
                                    h->param.escala.vy = o->raiz_ayudantes->param->scale.vy;
                                    h->param.escala.vz = o->raiz_ayudantes->param->scale.vz;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_SUELTA_HIJO) {
                            h = o->p6C;
                            if (h != 0) {
                                h->coord.param = PARAMETROS_SDK(h);
                                h->coord.super = 0;
                                h->flags14 = (h->flags14 & ~0x800) | 0x1000;
                                h->param.trans.vx = o->objetivo.vx;
                                h->param.trans.vy = o->objetivo.vy;
                                h->param.trans.vz = o->objetivo.vz;
                                h->w26 = o->w26;
                                h->param.giro.u.x = o->param.giro.u.x;
                                h->param.giro.u.y = o->param.giro.u.y;
                                h->param.giro.u.z = o->param.giro.u.z;
                                h->p70 = 0;
                                o->p6C = 0;
                                func_8001CFCC(&h->coord);
                                func_8001D028(o, h, area);
                                if (o == D_80069698) {
                                    h->flags0C |= 0x20000;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_HIJO_CON_GIRO) {
                            h = func_80036734((s16)c->eventos[i].id, &o->objetivo.vx, &o->param.giro.u.x);
                            if (h != 0) {
                                func_8001D028(o, h, area);
                                h->w26 = o->w26;
                                h->param.giro.u.y = h->param.giro.u.y + (u16)o->raiz_ayudantes->param->rotate.vy;
                                if (o == D_80069698) {
                                    h->flags0C |= 0x20000;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_HIJO_CON_GIRO_X) {
                            h = func_80036734((s16)c->eventos[i].id, &o->objetivo.vx, &o->param.giro.u.x);
                            if (h != 0) {
                                func_8001D028(o, h, area);
                                h->param.giro.u.x = h->param.giro.u.x + (u16)o->raiz_ayudantes->param->rotate.vx;
                                h->w26 = o->w26;
                                if (o == D_80069698) {
                                    h->flags0C |= 0x20000;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_AGARRA) {
                            if (!(D_80069698->flags14 & 0x3000000)) {
                                if ((c->eventos[i].banderas & EVENTO_SIN_PRUEBA)
                                    || (s16)func_80018D98(D_80069698, &o->objetivo, area) != 0) {
                                    if (D_80069698->p70 != 0) {
                                        D_80069698->coord.super = 0;
                                        D_80069698->coord.param = PARAMETROS_SDK(D_80069698);
                                        D_80069698->p70->p6C = 0;
                                        D_80069698->p70 = 0;
                                        D_80069698->flags14 = D_80069698->flags14 & ~0x14;
                                    }
                                    h = D_80069698->p6C;
                                    if (h != 0) {
                                        h->coord.param = PARAMETROS_SDK(h);
                                        h->coord.super = 0;
                                        h->flags14 = (h->flags14 & ~0x800) | 0x1000;
                                        h->w26 = o->w26;
                                        h->param.giro.u.x = D_80069698->param.giro.u.x;
                                        h->param.giro.u.y = D_80069698->param.giro.u.y;
                                        h->param.giro.u.z = D_80069698->param.giro.u.z;
                                        h->p70 = 0;
                                        D_80069698->p6C = 0;
                                        func_8001CFCC(&h->coord);
                                        func_8001D028(D_80069698, h, area);
                                    }
                                    if (c->eventos[i].banderas & EVENTO_AGARRE_SIN_DESFASE) {
                                        D_80069698->u18C.agarre.trans.vx = 0;
                                        D_80069698->u18C.agarre.trans.vy = 0;
                                        D_80069698->u18C.agarre.trans.vz = 0;
                                    } else {
                                        D_80069698->u18C.agarre.trans.vx =
                                            D_80069698->param.trans.vx - o->objetivo.vx;
                                        D_80069698->u18C.agarre.trans.vy =
                                            D_80069698->param.trans.vy - o->objetivo.vy;
                                        D_80069698->u18C.agarre.trans.vz =
                                            D_80069698->param.trans.vz - o->objetivo.vz;
                                    }
                                    D_80069698->param.trans.vx = o->objetivo.vx;
                                    D_80069698->param.trans.vy = o->objetivo.vy;
                                    D_80069698->param.trans.vz = o->objetivo.vz;
                                    D_80069698->u18C.agarre.escala.vx = 0x1000;
                                    D_80069698->u18C.agarre.escala.vy = 0x1000;
                                    D_80069698->u18C.agarre.escala.vz = 0x1000;
                                    D_80069698->u18C.agarre.giro.u.x = 0;
                                    D_80069698->u18C.agarre.giro.u.y = 0;
                                    D_80069698->u18C.agarre.giro.u.z = 0;
                                    D_80069698->coord.param = (GsCOORD2PARAM*)&D_80069698->u18C.agarre;
                                    D_80069698->coord.super = o->raiz_ayudantes;
                                    D_80069698->w17E = 0;
                                    D_80069698->w17C = c->eventos[i].id;
                                    D_80069698->flags14 = 4;
                                    o->p6C = D_80069698;
                                    D_80069698->p70 = o;
                                    func_8001CFCC(&D_80069698->coord);
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_SUELTA) {
                            if (D_80069698->p70 == o) {
                                if (o->p6C != 0) {
                                    if (c->eventos[i].banderas & EVENTO_AGARRE_SIN_DESFASE) {
                                        D_80069698->param.trans.vx = o->objetivo.vx;
                                        D_80069698->param.trans.vy = o->objetivo.vy;
                                        D_80069698->param.trans.vz = o->objetivo.vz;
                                    }
                                    D_80069698->param.giro.u.x = o->param.giro.u.x;
                                    D_80069698->param.giro.u.y = o->param.giro.u.y + 0x800;
                                    giro_z = o->param.giro.u.z;
                                    D_80069698->coord.param = PARAMETROS_SDK(D_80069698);
                                    D_80069698->coord.super = 0;
                                    D_80069698->p70 = 0;
                                    D_80069698->param.giro.u.z = giro_z;
                                    o->p6C = 0;
                                    D_80069698->w17E = 0;
                                    D_80069698->w17C = c->eventos[i].id;
                                    func_8001D028(o, D_80069698, area);
                                    /* D_80010041 es r[1] del estado principal: por esa vista el compilador
                                     * comparte el lui entre la lectura y el almacen, como el original
                                     * (con el simbolo suelto el almacen lleva su propio lui). */
                                    if (o->registro184 != 0) {
                                        ESTADO_PRINCIPAL->r[1] -= (u8)o->registro184->w16;
                                    }
                                    D_80069698->flags14 = D_80069698->flags14 & 0xFDFFFFDB;
                                }
                            }
                        }
                        if (c->eventos[i].banderas & EVENTO_COLOCA) {
                            if (!(D_80069698->flags14 & 0x3000020)) {
                                if (D_80069698->p70 == 0) {
                                    if ((s16)func_80018D98(D_80069698, &o->objetivo, area) != 0) {
                                        D_80069698->param.giro.u.y = o->param.giro.u.y + 0x800;
                                        D_80069698->w17E = 0;
                                        D_80069698->w17C = c->eventos[i].id;
                                        D_80069698->flags14 = 0x2000000;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        if (c->ticks == 0) {
            c->ticks = c->espera;
            c->cuadro = c->cuadro + 1;
        }
    }
    c->ticks = c->ticks - 1;
    if ((u16)c->cuadro == c->ultimo - 1) {
        c->flags18 = c->flags18 | ANIM_ULTIMO_CUADRO;
    }
    if (c->ticks == 0 && (u16)c->cuadro == c->ultimo) {
        banderas_cursor = c->flags18;
        if (banderas_cursor & ANIM_UNA_PASADA) {
termina:
            /* Fin de una animacion de una sola pasada: deja de estar en curso, queda terminada y
             * devuelve 0x200 si hay un hijo vivo. */
            banderas_cierre = (banderas_cursor & ~ANIM_EN_CURSO) | ANIM_TERMINADA;
            c->flags18 = banderas_cierre;
            if (banderas_cierre & ANIM_HIJO_VIVO) {
                return 0x200;
            }
            return 0x100;
        }
        return 0x200;
    }
    return 0x200;
}

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
void func_80020240(Objeto* o)
{
    s32 t;
    s32 bit4;
    s32 f;

    if (o->h108 < 0x800) {
        o->flags14 = o->flags14 & ~8;
    } else {
        o->flags14 = o->flags14 | 8;
    }
    t = o->h108;
    /* La bandera 4 se lee solo si la fase no ha pasado de 0xC00 y la altura se escribe directa en cada
     * rama: con la lectura incondicional o con la altura en una variable intermedia el compilador
     * adelanta la carga de las banderas y reparte los registros de otro modo. Toda lectura de bit4
     * queda bajo la misma condicion que la asigna (t < 0xC01, por el cortocircuito del &&), asi que
     * nunca se lee sin valor. */
    if (t < 0xC01) {
        bit4 = o->flags14 & 4;
    }
    if (t < 0xC01 && (bit4 == 0 || (o->flags14 & 0x10))) {
        if (o->flags14 & 8) {
            o->h10A = ((-o->h104 * rsin(t)) >> 12) * 2;
        } else {
            o->h10A = (-o->h104 * rsin(t)) >> 12;
        }
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
    u32 ms;
    VECTOR* pt;
    GsCOORDINATE2* n;
    PeldanoApoyo* p;
    PeldanoApoyo* q;
    s16 i;
    s16 k;
    s32 x1;
    s32 y1;
    s32 z1;
    s32 r;
    s32 rs;
    s32 h;
    /* Copia de 16 bits de la x del peldano, tomada antes de los almacenes al resultado. */
    s16 x_pel;

    pt = punto;
    ms = mascara;
    w->caja_min.vx = o->min.vx;
    w->caja_min.vy = o->min.vy;
    w->caja_min.vz = o->min.vz;
    w->caja_max.vx = o->max.vx;
    w->caja_max.vy = o->max.vy;
    w->caja_max.vz = o->max.vz;
    w->cur = D_80069630;
    if (w->cur != 0) {
        do {
            if ((w->cur->flags08 & ms) && !(w->cur->flags14 & 1) && (s16)w->cur->w26 == (s16)o->w26 &&
                w->cur->tipo_volumen == 2 && o != w->cur && w->cur->u78.p != 0) {
                GEO_CARGAR_W(pt);
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
                                p = &w->pel[i];
                                p->x = (u16)n->param->trans.vx;
                                p->y = (u16)n->param->trans.vy;
                                p->z = (u16)n->param->trans.vz;
                                p->nodo = n;
                                if (i >= 2) {
                                    q = &w->pel[i - 1];
                                    gte_SetRotMatrix(&q->nodo->coord);
                                    x1 = q->x;
                                    y1 = q->y;
                                    z1 = q->z;
                                    /* Un solo contador (k) para todos los bucles de peldanos: con uno
                                     * aparte en estos dos, el reparto de a3, t0 y t1 cambia. */
                                    for (k = i - 2, q = &w->pel[k]; k >= 0; k--, q--) {
                                        gte_ldv0(q);
                                        gte_rtv0();
                                        gte_stsv(q);
                                    }
                                    for (k = i - 2, q = &w->pel[k]; k >= 0; k--, q--) {
                                        q->x += x1;
                                        q->y += y1;
                                        q->z += z1;
                                    }
                                }
                                n = n->super;
                            }
                        }
                        w->rot.vx = (u16)n->param->rotate.vx;
                        w->rot.vz = 0;
                        w->rot.vy = 0;
                        RotMatrixZYX(&w->rot, &w->m);
                        gte_SetRotMatrix(&w->m);
                        for (k = 0, p = w->pel; k < i; k++, p++) {
                            gte_ldv0(p);
                            gte_rtv0();
                            gte_stsv(p);
                        }
                        w->pel[0].alto = w->cur->trabajo.h0A;
                        w->pel[0].largo = 0;
                        for (k = 1; k < i; k++) {
                            w->pel[k].alto = w->pel[k - 1].y - w->pel[k].y;
                            w->pel[k].largo = w->pel[k - 1].z - w->pel[k].z;
                        }
                        for (k = 0, p = w->pel; k < i; k++, p++) {
                            rs = w->dist;
                            if (w->out.vx >= -rs && w->out.vx <= rs) {
                                if (p[0].largo >= 0) {
                                    if (p[0].z + p[0].largo + rs < w->out.vz || w->out.vz < p[0].z - rs) {
                                        continue;
                                    }
                                } else {
                                    if (w->out.vz < p[0].z + p[0].largo - rs || p[0].z + rs < w->out.vz) {
                                        continue;
                                    }
                                }
                                h = w->out.vy - 0x12C;
                                if (p[0].y < h && h < p[0].y + p[0].alto) {
                                    w->cur->portado.trans.vz = (s32)p[0].nodo;
                                    /* El objeto se guarda antes que su sistema de coordenadas: asi
                                     * la carga de w->cur queda en el registro que usa el original. */
                                    w->res.objeto = w->cur;
                                    w->res.coord = &w->cur->coord;
                                    x_pel = p[0].x;
                                    w->res.h0A = w->out.vy;
                                    w->res.x = x_pel;
                                    w->res.z = p[0].z;
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

/*
 * Busca el peldano que corresponde a la altura del objeto sobre el objeto de apoyo (p70):
 * entrega el apoyo por *apoyo y devuelve 1 si el objeto esta por encima del peldano, 2 si
 * esta en el suelo del apoyo y 0 si lo toca; guarda en el apoyo la altura del peldano
 * alcanzado (+0x13C). Si el apoyo es plano (bandera 0x400000) solo compara con su altura.
 *
 * Estructura del original que el C reproduce: la guarda de apoyo nulo es un retorno anticipado
 * (el 1 de esa guarda y el 1 del peldano no alcanzado comparten el mismo bloque `jr ra`/`li v0,1`
 * de 0x80020B74); el bucle `while (nodo != NULL)` con la suma primero lo rota el compilador por
 * si mismo (guarda de entrada `beqz a3` y suma repetida en el hueco del salto de vuelta); y la
 * cola deja el retorno 0 al final, de modo que el `blez a1` de 0x80020B6C y el retorno 0 comparten
 * el `jr ra`/`nop` de 0x80020B88.
 *
 * La envoltura `do { } while (0)` de la copia del acumulador no genera codigo. Causa medida: el
 * `sll` de la comparacion del peldano lee la suma (pseudo 87, en `$v0`) en el original
 * (`move a0,v0` y despues `sll v0,v0,0x10`). Sin la envoltura, tras la primera planificacion el
 * `sll` todavia lee el pseudo 87 (con su nota de muerte) y en el volcado de la asignacion local ya
 * lee el acumulador (pseudo 86, en `$a0`): sale `sll v0,a0,0x10` (puntuacion 5, una sola
 * diferencia de operando). Con la envoltura sigue leyendo el pseudo 87 (7 usos ponderados sobre 3
 * instrucciones de vida, antes 4 sobre 2; el acumulador pasa de 7 a 6 usos sobre 13) y el
 * ensamblador es identico al original (puntuacion 0, sin instrucciones nuevas). Se supone, sin
 * verificar, que el cambio lo hace el paso de propagacion de copias entre pseudos que corre antes
 * de la asignacion local y que se detiene ante una nota de bucle entre la copia y el uso. La forma
 * del fuente original que producia este reparto se desconoce.
 */
u8 func_80020A90(Objeto* o, Movimiento* d, Objeto** apoyo)
{
    Objeto* t;
    NodoPeldano* nodo;
    s32 altura;
    s32 acc;
    s32 v;

    t = o->p70;
    *apoyo = t;
    if (o->p70 == NULL) {
        return 1;
    }
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
    while (nodo != NULL) {
        v = acc + (u16)t->trabajo.h0A;
        do {
            acc = v;
        } while (0);
        if (altura < (s16)v) {
            break;
        }
        nodo = nodo->sig;
    }
    if (nodo == NULL || altura <= 0) {
        (*apoyo)->portado.trans.vz = ((NodoPeldano*)(*apoyo)->u78.p)->w10;
        if (altura <= 0) {
            return 2;
        }
        return 1;
    }
    t->portado.trans.vz = nodo->w10;
    return 0;
}
