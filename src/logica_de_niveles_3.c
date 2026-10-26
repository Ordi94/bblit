#include "common.h"
#include "globales.h"
#include "gte.h"
#include "objetos.h"
#include "niveles.h"

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026298);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026FEC);

void func_8002BA80(Objeto* o)
{
    TrabajoZona* t;
    NodoDisparador* n;
    Objeto* h;
    void* area;
    u32 azar;
    u16 salto;
    NodoDisparador* m;
    NodoDisparador* nx;
    s32 sj;

    t = TRABAJO_ZONA;
    area = (void*)0x1F800038;
    if (o->flags0C & 0x14) {
        if (o->flags0C & 0x10) {
            D_8006D9B8[0] = o;
        } else {
            t->vx = D_80069698->param.trans.vx - o->param.trans.vx;
            t->vy = 0;
            t->vz = D_80069698->param.trans.vz - o->param.trans.vz;
            if ((s32)func_80044940((s32*)0x1F800024) < 0x7D0) {
                D_8006D9B8[0] = o;
            }
        }
    }
    t->nodo = (NodoDisparador*)o->apoyos;
    if (t->nodo == 0) {
        return;
    }
    do {
        t->flags = t->nodo->flags;
        if (t->flags & 2) {
            n = t->nodo;
            azar = BugsRand() & 0xFFFF;
            if (!((u16)n->p1C < azar)) {
                goto siguiente;
            }
        } else if (t->flags & 0x20000) {
            n = t->nodo;
            azar = BugsRand() & 0xFFFF;
            if (!((u16)n->p20 < azar)) {
                goto siguiente;
            }
        }
        if (t->nodo->cond != 0 && TestLogicCond(o, &t->nodo->cond) == 0) {
            salto = t->nodo->desplazamiento;
            if (salto == 0) {
                goto siguiente;
            }
            t->salto = salto;
            sj = (s16)salto;
            m = t->nodo;
            if (sj != m->id) {
                do {
                    t->previo = m;
                    nx = t->nodo->sig;
                    t->nodo = nx;
                    m = nx;
                } while ((s16)salto != nx->id);
            }
            t->nodo = t->previo;
            goto siguiente;
        }
        if (t->flags & 0x18400000) {
            if (t->flags & 0x400000) {
                for (t->objeto = D_80069518; t->objeto != 0; t->objeto = t->objeto->siguiente) {
                    if (t->objeto->w1C == t->nodo->p20 && !(t->objeto->flags14 & 0x100)) {
                        break;
                    }
                }
                if (t->objeto == 0) {
                    goto siguiente;
                }
                func_8001CD84(t->objeto, t->nodo->p1C, area);
            } else {
                if (t->flags & 0x10000000) {
                    for (t->objeto = D_80069518; t->objeto != 0; t->objeto = t->objeto->siguiente) {
                        if (t->objeto->w1C == t->nodo->p20 && !(t->objeto->flags14 & 0x100)) {
                            break;
                        }
                    }
                    if (t->objeto == 0) {
                        goto siguiente;
                    }
                    t->dx = t->objeto->param.trans.vx - o->param.trans.vx;
                    t->dz = t->objeto->param.trans.vz - o->param.trans.vz;
                    if (t->flags & 1) {
                        t->dy = t->objeto->param.trans.vy - o->param.trans.vy;
                    } else {
                        t->dy = 0;
                    }
                } else {
                    t->dx = D_80069640[0] - o->param.trans.vx;
                    t->dz = D_80069640[2] - o->param.trans.vz;
                    if (t->flags & 1) {
                        t->dy = D_80069640[1] - o->param.trans.vy;
                    } else {
                        t->dy = 0;
                    }
                }
                gte_ldlvl(&t->dx);
                gte_sqr0();
                gte_stlvnl(&t->dx);
                t->distancia = SquareRoot0(t->dx + t->dy + t->dz);
                if (t->flags & 0x200000) {
                    if ((u32)t->distancia < t->nodo->p1C) {
                        goto siguiente;
                    }
                } else {
                    if (t->nodo->p1C < (u32)t->distancia) {
                        goto siguiente;
                    }
                }
            }
        }
        if (t->nodo->accion != 0) {
            RunLogicAction(o, &t->nodo->cond);
        }
        if (t->flags & 0x600) {
            if (t->flags & 0x200) {
                func_8003F06C(o, t->nodo->p1C, 1, D_8006967C);
            }
            if (t->flags & 0x400) {
                func_8003F06C(o, t->nodo->p1C, 2, D_8006967C);
            }
        }
        if (t->flags & 0x40100) {
            t->objeto = func_80036734((s16)t->nodo->p20, (s32*)&o->param.trans.vx, &o->param.giro.u.x);
            h = t->objeto;
            if (h == 0) {
                goto siguiente;
            }
            h->w26 = o->w26;
            if (t->flags & 0x1000) {
                ZONA_PONER_CERO_3W(&t->objeto->i134);
                ZONA_PONER_CERO_WH(&t->objeto->w12C);
                ZONA_RELLENAR_1000(t->objeto->escala_rel);
                t->objeto->coord.super = &D_80069698->coord;
                t->objeto->w26 = D_80069698->w26;
                t->objeto->p70 = D_80069698;
                t->objeto->coord.param = (GsCOORD2PARAM*)t->objeto->escala_rel;
                t->objeto->w26 = o->w26;
                func_8001CFCC(&t->objeto->coord);
            }
            if (t->flags & 0x40000) {
                azar = BugsRand();
                t->objeto->param.giro.u.y = azar & 0xFFF;
            }
            if (t->flags & 0x1000000) {
                t->objeto->s1E = o->s1E;
            }
        }
        if (t->flags & 0x84890800) {
            if (t->flags & 0x04000000) {
                for (t->objeto = D_80069518; t->objeto != 0; t->objeto = t->objeto->siguiente) {
                    if (t->objeto->w1C == t->nodo->p20 && !(t->objeto->flags14 & 0x100)) {
                        break;
                    }
                }
                if (t->objeto == 0) {
                    goto siguiente;
                }
                t->objeto->flags14 |= 0x100;
            }
            if (t->flags & 0x800) {
                D_80069698->param.giro.u.y = o->param.giro.u.y;
                func_8001D31C(o->param.trans.vx, o->param.trans.vy, o->param.trans.vz);
                D_80069698->flags14 |= 0x80000000;
            }
            if (t->flags < 0) {
                func_8001D0FC(o, t->nodo->p20, area);
            }
            if (t->flags & 0x80000) {
                D_80069662 = 1;
                D_80010000 = t->nodo->p1C;
            }
            if (t->flags & 0x10000) {
                o->flags14 |= 0x100;
                return;
            }
        }
        if (!(t->flags & 0x8000)) {
            return;
        }
siguiente:
        t->nodo = t->nodo->sig;
    } while (t->nodo != 0);
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 3551 con la configuracion versionada (g = 8 del archivo). Reparto de registros y orden de las cargas: el original conserva en s5 la parte alta de D_8006D928 y en s3 la matriz del scratchpad derivada de la misma base, relee las banderas del nodo de memoria tras cada almacen y planifica las cargas del giro del origen de otro modo. */
void func_8002C1DC(Objeto* o)
{
    TrabajoCamara* t;
    EstadoCamara* c;
    MATRIX* m;
    s32 paso;

    t = TRABAJO_CAMARA;
    c = &D_8006D928;
    m = (MATRIX*)0x1F800050;
    t->nodo = (NodoDisparador*)o->apoyos;
    if (t->nodo == 0) {
        return;
    }
    do {
        t->flags = t->nodo->flags;
        if (t->nodo->cond != 0 && TestLogicCond(o, &t->nodo->cond) == 0) {
            goto siguiente;
        }
        if (t->flags & 0x4000) {
            c->flags80 |= 8;
        }
        if (t->flags & 0x8010) {
            if (t->flags & 0x20) {
                t->origen = D_80069698;
            } else if (t->flags & 0x40) {
                for (t->origen = D_80069518; t->origen != 0; t->origen = t->origen->siguiente) {
                    if (t->origen->w1C == t->nodo->p20 && !(t->origen->flags14 & 0x100)) {
                        break;
                    }
                }
            }
            if (t->origen == 0) {
                goto siguiente;
            }
            t->dx = t->origen->param.trans.vx - o->param.trans.vx;
            t->dz = t->origen->param.trans.vz - o->param.trans.vz;
            if (t->flags & 0x100) {
                t->dy = t->origen->param.trans.vy - o->param.trans.vy;
            } else {
                t->dy = 0;
            }
            gte_ldlvl(&t->dx);
            gte_sqr0();
            gte_stlvnl(&t->dx);
            t->modulo = SquareRoot0(t->dx + t->dy + t->dz);
            if (t->flags & 0x10) {
                if ((u32)t->modulo < t->nodo->p1C) {
                    goto siguiente;
                }
            } else {
                if (t->nodo->p1C < (u32)t->modulo) {
                    goto siguiente;
                }
            }
        }
        if (t->nodo->accion != 0) {
            RunLogicAction(o, &t->nodo->cond);
        }
        if (t->flags & 1) {
            t->origen = 0;
            if ((t->flags & 0x42) == 0x40) {
                for (t->origen = D_80069518; t->origen != 0; t->origen = t->origen->siguiente) {
                    if (t->origen->w1C == t->nodo->p20 && !(t->origen->flags14 & 0x100)) {
                        break;
                    }
                }
            } else if (t->flags & 0x80) {
                t->origen = o;
            }
            if (t->origen != 0) {
                if (t->flags & 0x20000) {
                    t->vx = D_80069698->param.trans.vx - t->origen->param.trans.vx;
                    t->vy = 0;
                    t->vz = D_80069698->param.trans.vz - t->origen->param.trans.vz;
                    t->gz = 0;
                    t->gx = 0;
                    t->escala.vz = 0;
                    t->escala.vy = 0x1000;
                    t->escala.vx = 0x1000;
                    t->gy = 0x1000 - t->origen->param.giro.u.y;
                    RotMatrix((SVECTOR*)&t->gx, m);
                    ApplyMatrixSV(m, (SVECTOR*)&t->vx, (SVECTOR*)&t->vx);
                    RotMatrix(&t->origen->param.giro.rotate, m);
                    ScaleMatrix(m, &t->escala);
                    ApplyMatrixSV(m, (SVECTOR*)&t->vx, (SVECTOR*)&t->vx);
                    c->dvx = t->origen->param.trans.vx + (s16)t->vx;
                    c->dvy = t->origen->param.trans.vy + (s16)t->vy;
                    c->dvz = t->origen->param.trans.vz + (s16)t->vz;
                } else {
                    c->dvx = t->origen->param.trans.vx;
                    c->dvy = t->origen->param.trans.vy;
                    c->dvz = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80000) {
                t->vx = 0;
                t->vy = -(u16)t->nodo->p20;
                t->vz = (u16)t->nodo->p1C;
                GEO_IDENTIDAD(m);
                RotMatrixY(D_80069698->param.giro.rotate.vy + 0x800, m);
                ApplyMatrix(m, (SVECTOR*)&t->vx, &t->r);
                c->dvx += ((D_80069698->param.trans.vx + t->r.vx) - c->dvx) >> 2;
                c->dvy += ((D_80069698->param.trans.vy + t->r.vy) - c->dvy) >> 2;
                c->dvz += ((D_80069698->param.trans.vz + t->r.vz) - c->dvz) >> 2;
                c->dmx += (D_80069698->param.trans.vx - c->dmx) >> 2;
                c->dmy += (D_80069698->param.trans.vy - c->dmy) >> 2;
                c->dmz += (D_80069698->param.trans.vz - c->dmz) >> 2;
            } else if (t->flags & 0x100000) {
                c->dvx = D_8006D928.vpx;
                c->dvy = c->vpy;
                c->dvz = c->vpz;
            } else {
                c->dvx = t->nodo->p1C;
                c->dvy = t->nodo->p20;
                c->dvz = t->nodo->desplazamiento;
            }
            if (t->flags & 0x40000) {
                t->ex = D_8006D928.vpx - c->dvx;
                t->ey = c->vpy - c->dvy;
                t->ez = c->vpz - c->dvz;
                GEO_CARGAR_W(&t->ex);
                GEO_GUARDAR_W_T1(&t->r);
                gte_ldlvl(&t->r);
                gte_sqr0();
                gte_stlvnl(&t->r);
                t->modulo = SquareRoot0(t->r.vx + t->r.vy + t->r.vz) | 1;
                t->r.vx = (t->ex << 12) / t->modulo;
                t->r.vy = (t->ey << 12) / t->modulo;
                t->r.vz = (t->ez << 12) / t->modulo;
                paso = t->modulo - 0x1F4;
                if (paso < 0x1F4) {
                    t->modulo = t->modulo >> 3;
                } else {
                    t->modulo = paso;
                }
                if (t->modulo > 0) {
                    c->dvx += (t->r.vx * t->modulo) >> 12;
                    c->dvy += (t->r.vy * t->modulo) >> 12;
                    c->dvz += (t->r.vz * t->modulo) >> 12;
                }
            }
            c->flags80 |= 0x400;
        } else if (t->flags & 4) {
            c->flags80 &= 0xBBFF;
        }
        if (t->flags & 2) {
            if (t->flags & 0x40) {
                for (t->origen = D_80069518; t->origen != 0; t->origen = t->origen->siguiente) {
                    if (t->origen->w1C == t->nodo->p20 && !(t->origen->flags14 & 0x100)) {
                        break;
                    }
                }
                if (t->origen != 0) {
                    c->dmx = t->origen->param.trans.vx;
                    c->dmy = t->origen->param.trans.vy;
                    c->dmz = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80) {
                c->dmx = o->param.trans.vx;
                c->dmy = o->param.trans.vy;
                c->dmz = o->param.trans.vz;
            } else if (t->flags & 0x100000) {
                c->dmx = c->x;
                c->dmy = c->y;
                c->dmz = c->z;
            } else {
                c->dmx = t->nodo->p1C;
                c->dmy = t->nodo->p20;
                c->dmz = t->nodo->desplazamiento;
            }
            c->flags80 |= 0x800;
        } else if (t->flags & 8) {
            c->flags80 &= 0xB7FF;
        }
        if (t->flags & 0x400) {
            c->flags80 |= 0x1000;
            c->zoom = t->nodo->p1C;
        } else if (t->flags & 0x800) {
            c->flags80 &= 0xEFFF;
        }
        if (t->flags & 0x10000) {
            c->c68 = D_8006D928.vpx;
            c->c94 = D_8006D928.vpx;
            c->cB4 = D_8006D928.vpx;
            c->c6C = c->vpy;
            c->c98 = c->vpy;
            c->cB8 = c->vpy;
            c->c70 = c->vpz;
            c->c9C = c->vpz;
            c->cBC = c->vpz;
            c->cA4 = c->x;
            c->cA8 = c->y;
            c->cAC = c->z;
            c->flags80 |= 0x4000;
            return;
        }
        if (t->flags & 0x200) {
            o->flags14 |= 0x100;
            return;
        }
        if (!(t->flags & 0x1000)) {
            return;
        }
siguiente:
        t->nodo = t->nodo->sig;
    } while (t->nodo != 0);
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002C1DC);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 510 con la configuracion versionada (g = 8 del archivo). Difiere el orden de las instrucciones del avance de cuadro: el original carga el intervalo (b05) antes de incrementar el cuadro y lo guarda en el hueco del salto tras comparar con el ultimo cuadro. */
void func_8002CB8C(Objeto* o)
{
    BloqueTrabajo* b;
    NodoAnimacion* a;
    NodoDisparador* n;
    Fotograma* f;
    void* area;
    TablaFotogramas* tb;
    u16 i;
    s32 k;
    u8 w;

    area = (void*)0x1F800000;
    b = &o->trabajo;
    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
        o->u78.ayudas = func_800363D4();
        if (o->u78.ayudas == 0) {
            for (;;) {
            }
        }
        o->u78.ayudas->flags8 = 1;
        a = o->lista;
        o->coord.param = PARAMETROS_SDK(o);
        o->coord.sub = 0;
        o->coord.super = 0;
        o->coord.flg = 0;
        if (a != 0) {
            for (; a != 0; a = a->sig) {
                if (a->def->tipo == 8) {
                    break;
                }
            }
        }
        tb = a->def->tabla;
        o->tabla = tb;
        f = tb->fotogramas;
        b->fotogramas = f;
        b->actual = f;
        k = tb->cuenta;
        b->h02 = 0;
        b->b05 = 2;
        b->b08 = 2;
        b->h00 = k - 1;
        o->min.vx = -(f->w0C >> 1);
        o->min.vy = 0;
        o->min.vz = -(f->w0C >> 1);
        o->max.vx = f->w0C >> 1;
        o->max.vy = -f->w0E;
        o->max.vz = f->w0C >> 1;
        if (o->flags0C & 0x04000000) {
            o->param.trans.vy += f->w0E >> 1;
        }
        o->w2E = f->w0C >> 1;
        o->alcance2 = o->w2E * o->w2E + o->s20 * o->s20;
        func_8001CFCC(&o->coord);
        func_8001E528(o, b, 1, area);
    }
    if (b->b08 == 0) {
        i = b->h02 + 1;
        b->h02 = i;
        b->b08 = b->b05;
        if (b->h00 < i) {
            b->h02 = 0;
            b->actual = b->fotogramas;
        }
        func_8001E528(o, b, 1, area);
    }
    b->b08 -= 1;
    n = (NodoDisparador*)o->apoyos;
    if (n != 0) {
        do {
            if (TestLogicCond(o, &n->cond) != 0) {
                RunLogicAction(o, &n->cond);
                if (n->flags & 0x200) {
                    if (b->b08 == 0 && (u16)b->h02 == 0) {
                        func_8003F06C(o, n->p1C, 1, D_8006967C);
                    }
                }
                if (n->flags & 0x400) {
                    func_8003F06C(o, n->p1C, 2, D_8006967C);
                }
                if (n->flags & 0x10000) {
                    if (b->b08 == 0 && (u16)b->h02 >= b->h00) {
                        o->flags14 |= 0x100;
                    }
                }
                break;
            }
            n = n->sig;
        } while (n != 0);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002CB8C);
#endif

void func_8002CEC4(Objeto* o)
{
    BloqueTrabajo* b;
    NodoAnimacion* a;
    TablaFotogramas* tb;
    Fotograma* f;
    void* area;

    area = (void*)0x1F800000;
    b = &o->trabajo;
    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
        o->u78.ayudas = func_800363D4();
        if (o->u78.ayudas == 0) {
            for (;;) {
            }
        }
        o->u78.ayudas->flags8 = 0x20;
        a = o->lista;
        o->flags08 = 1;
        if (a != 0) {
            for (; a != 0; a = a->sig) {
                if (a->def->tipo == 8) {
                    break;
                }
            }
        }
        tb = a->def->tabla;
        o->tabla = tb;
        f = tb->fotogramas;
        b->fotogramas = f;
        b->actual = f;
        b->h00 = tb->cuenta - 1;
        b->h02 = (u16)o->max.vx;
        b->b05 = (u8)o->max.vz;
        b->b08 = (u8)o->max.vz;
        func_8001E600(o, b, 1, area);
    }
    if (b->b08 == 0) {
        b->b08 = b->b05;
        b->h02 += 1;
        if (b->h00 < (u16)b->h02) {
            b->h02 = 0;
        }
        func_8001E600(o, b, 1, area);
    }
    b->b08 -= 1;
    o->flags04 |= 2;
}

/*
 * Manejador de actor animado por secuencias sin movimiento (clase 2 de D_8005E35C). Elige la
 * secuencia de animacion de identificador 2 (o 1 si no existe) en el primer cuadro, avanza por
 * los pasos de la secuencia y, en cada fotograma, recorre los disparadores de su grupo: filtra
 * por golpe, estado o azar, evalua la condicion, ejecuta la accion y aplica los efectos que pide
 * flags (sonido, marcar un objeto para destruir, cambiar de nivel, animar al jugador, saltar a otra
 * secuencia). Las variables de trabajo viven en el scratchpad, por eso se leen de nuevo tras cada
 * escritura a traves de otro puntero.
 */
void func_8002D03C(Objeto* o)
{
    TrabajoDisparo* t;
    NodoSecuencia* n;
    Objeto* ob;
    void* area;

    t = TRABAJO_DISPARO;
    area = (void*)0x1F80002C;
    if (o->u78.p == 0) {
        o->flags08 = (o->flags08 & 0xFFDFFFFF) | 0x20;
        o->flags18 |= 0x80;
        t->secuencia = o->secuencias;
        t->resultado = 2;
        if (t->secuencia != 0) {
            while (1) { n = t->secuencia; if (n->id == 2) { break; } t->secuencia = n->sig; if (t->secuencia == 0) { break; } }
        }
        if (t->secuencia == 0) {
            t->secuencia = o->secuencias;
            t->resultado = 1;
            if (t->secuencia != 0) {
                while (1) { n = t->secuencia; if (n->id == 1) { break; } t->secuencia = n->sig; if (t->secuencia == 0) { break; } }
            }
        }
        t->fotograma = (RegistroAnim*)(o->bloque + t->secuencia->desplazamiento);
        o->p180 = t->secuencia;
        o->registro184 = t->fotograma;
        o->w17C = 0;
    }
    t->paso = *(u16*)((u8*)o->p180 + (o->w17C << 1) + 6);
    if (t->paso == 0xFFF0 || o->w17C >= 5) {
        if (o->registro184 != 0) {
            t->previo = o->registro184->w06;
        } else {
            t->previo = 0;
        }
        t->secuencia = o->secuencias;
        t->resultado = 1;
        if (t->secuencia != 0) {
            while (1) { n = t->secuencia; if (n->id == 1) { break; } t->secuencia = n->sig; if (t->secuencia == 0) { break; } }
        }
        t->fotograma = (RegistroAnim*)(o->bloque + t->secuencia->desplazamiento);
        o->p180 = t->secuencia;
        o->registro184 = t->fotograma;
        o->w17C = 0;
    } else {
        t->fotograma = o->registro184;
        t->secuencia = o->p180;
    }
    if (t->fotograma->w0A != 0) {
        t->cabeza = (NodoDisparador*)((u8*)o->apoyos + t->fotograma->w1E);
        t->nodo = t->cabeza;
        if (t->nodo != 0) {
            while (1) {
                if (t->nodo->id != t->fotograma->w0A) {
                    break;
                }
                t->destino = t->nodo->desplazamiento;
                t->flags = t->nodo->flags;
                if (t->flags != 0) {
                    if (t->flags & 0x40) {
                        if (t->nodo->p1C != (u16)o->trabajo.h02) {
                            goto siguiente;
                        }
                        if (o->trabajo.b08 != 0) {
                            goto siguiente;
                        }
                    } else if (t->flags & 4) {
                        if (!(o->trabajo.flags18 & 0x2000)) {
                            goto siguiente;
                        }
                        if (o->trabajo.b08 != 0) {
                            goto siguiente;
                        }
                    }
                    if (t->flags & 2) {
                        if (!(t->nodo->p1C < (BugsRand() & 0xFFFF))) {
                            goto siguiente;
                        }
                    } else if (t->flags & 0x20000) {
                        if (!((u32)t->nodo->p20 < (BugsRand() & 0xFFFF))) {
                            goto siguiente;
                        }
                    }
                }
                if (t->nodo->cond != 0) {
                    if (TestLogicCond(o, &t->nodo->cond) == 0) {
                        goto siguiente;
                    }
                }
                if (t->nodo->accion != 0) {
                    RunLogicAction(o, &t->nodo->cond);
                }
                if (t->flags != 0) {
                    if (t->flags & 0x600) {
                        if (t->flags & 0x200) {
                            func_8003F06C(o, t->nodo->p1C, 1, D_8006967C);
                        } else if (t->flags & 0x400) {
                            func_8003F06C(o, t->nodo->p1C, 2, D_8006967C);
                        }
                    }
                    if (t->flags & 0x04000000) {
                        {
                            for (t->buscado = D_80069518; t->buscado != 0; t->buscado = t->buscado->siguiente) {
                                if (t->buscado->w1C == t->nodo->p20 && !(t->buscado->flags14 & 0x100)) {
                                    break;
                                }
                            }
                            if (t->buscado != 0) {
                                t->buscado->flags14 |= 0x100;
                            }
                        }
                    }
                    if (t->flags & 0x80000) {
                        D_80069662 = 1;
                        D_80010000 = t->nodo->p1C;
                    }
                    if (t->flags < 0) {
                        func_8001D0FC(o, t->nodo->p20, area);
                    }
                    if (t->flags & 0x10000) {
                        o->flags14 |= 0x100;
                        return;
                    }
                    if (t->flags & 0x8000) {
                        goto siguiente;
                    }
                    if (t->flags & 0x10) {
                        break;
                    }
                }
                if (t->fotograma != 0) {
                    t->previo = t->fotograma->w06;
                } else {
                    t->previo = 0;
                }
                t->secuencia = (NodoSecuencia*)((u8*)o->secuencias + t->destino);
                t->fotograma = (RegistroAnim*)(o->bloque + t->secuencia->desplazamiento);
                o->p180 = t->secuencia;
                o->registro184 = t->fotograma;
                o->trabajo.i14 = 0;
                o->w17C = 0;
                break;
siguiente:
                t->nodo = t->nodo->sig;
                if (t->nodo == 0) {
                    break;
                }
            }
        }
    }
    if (o->trabajo.i14 != t->fotograma->w06) {
        t->resultado = func_8001E720(o, &o->trabajo, t->fotograma->w06, t->fotograma->w08, area);
    } else {
        t->resultado = func_8001E720(o, &o->trabajo, 0, 0, area);
    }
    if (t->resultado == 0x100) {
        o->trabajo.i14 = 0;
        if (t->fotograma->w0C & 4) {
            o->flags14 |= 0x100;
        } else {
            o->w17C += 1;
            t->paso = *(u16*)((u8*)t->secuencia + (o->w17C << 1) + 6);
            if (t->paso != 0xFFF0 && o->w17C < 5) {
                t->fotograma = (RegistroAnim*)(o->bloque + t->paso);
                o->registro184 = t->fotograma;
                o->trabajo.i14 = 0;
                o->trabajo.h02 = 0;
                o->trabajo.b08 = 0;
            }
        }
    }
}

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D68C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EA9C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EAA4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F018);

#ifdef NON_MATCHING
/* Pendiente: puntuacion 878 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original deja el objeto en s1 y la edad del efecto en s0, el compilador los intercambia, y no adelanta la suma del guion al hueco del salto compartido. */
void func_8002F510(Objeto* o)
{
    s16 vida;
    s16 idx;
    s32 edad;
    u16 bits;
    u16* base;

    vida = o->w17C;
    if (vida > 0) {
        edad = o->w22;
        if (edad == vida) {
            if (o->p180 != 0) {
                func_80045C4C(0, 0, o);
            } else {
                o->flags14 |= 0x100;
            }
            return;
        }
        idx = o->w17E;
        bits = o->w17E;
        if (idx & 0x8000) {
            o->w17E = bits & 0x7FFF;
            return;
        }
        base = D_80069590;
        func_80045498(o, (u8*)base + base[idx], &o->trabajo);
        o->w22 = edad;
        return;
    }
    idx = o->w17E;
    bits = o->w17E;
    if (idx & 0x8000) {
        o->w17E = bits & 0x7FFF;
        return;
    }
    edad = o->w22;
    base = D_80069590;
        func_80045498(o, (u8*)base + base[idx], &o->trabajo);
    o->w22 = edad;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F510);
#endif

void func_8002F614(Objeto* o)
{
    if (o->u78.p == 0) {
        if (o->lista == 0) {
            o->flags14 |= 0x100;
            return;
        }
        func_8001F268(o, &o->trabajo, 5, 2, (void*)0x1F800000);
    }
    o->param.trans.vx = D_8006D928.vpx;
    o->param.trans.vy = D_8006D928.vpy + o->s1E;
    o->param.trans.vz = D_8006D928.vpz;
    func_8001CF50(o);
}

void func_8002F6B4(Objeto* o)
{
    TrabajoSonda* t;
    u16 x;
    u16 y;
    u16 z;
    u16 bits;
    s32 a;
    void* area;

    area = (void*)0x1F800044;
    t = TRABAJO_SONDA;
    if (o->u78.p == 0) {
        func_8001F268(o, &o->trabajo, 5, 2, area);
    }
    x = (u16)D_8006D928.x - (u16)D_8006D928.vpx;
    t->cx = x;
    y = (u16)D_8006D928.y - (u16)D_8006D928.vpy;
    z = (u16)D_8006D928.z - (u16)D_8006D928.vpz;
    t->cy = y;
    t->cz = z;
    bits = o->w196;
    D_800695EC = o;
    if (bits & 1) {
        t->cy = -y;
        t->cz = -z;
    } else if (bits & 2) {
        t->cx = -x;
        t->cz = -z;
    } else {
        t->cx = -x;
        t->cy = -y;
    }
    GEO_COMPLEMENTO(&o->param.giro.rotate);
    ZONA_GUARDAR_H_T1(t);
    ZONA_CARGAR_H(&t->cx);
    ZONA_SUMAR_H(t);
    GEO_IDENTIDAD(&t->m);
    RotMatrixX(t->gx, &t->m);
    RotMatrixY((s16)t->gy, &t->m);
    RotMatrixZ((s16)t->gz, &t->m);
    t->actual = D_80069630;
    if (t->actual != 0) {
        do {
            GEO_CARGAR_W(&t->actual->param.trans);
            GEO_RESTAR_W(&o->param.trans);
            GEO_GUARDAR_H_T4(&t->px);
            ApplyMatrixSV(&t->m, (SVECTOR*)&t->px, (SVECTOR*)&t->qx);
            a = (s16)t->qx;
            if (o->min.vx < a && a < o->max.vx) {
                a = (s16)t->qz;
                if (o->min.vz < a && a < o->max.vz) {
                    t->actual->flags18 |= 8;
                }
            }
            t->actual = t->actual->sig10;
        } while (t->actual != 0);
    }
}

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F968);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F970);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 350 con la configuracion versionada. Dos 'lui' donde el original usa uno
 * solo para los dos bytes (los simbolos son variables externas distintas).
 *
 * Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el
 * bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico
 * 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de
 * retardo del primer salto; el compilador genera dos 'lui' porque son variables externas
 * distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
 *
 * El operando se trunca a un byte dentro de la rutina (andi 0xFF en 0x8002F9AC y 0x8002F9DC) y los
 * llamadores le pasan el valor de 16 bits sin truncar (lhu): por eso el parametro es s32 y el
 * truncamiento un cast. Declarado u8, cada llamador recorta el argumento con lbu.
 */
extern u8 D_8001013C[];
extern u8 D_80010047[];

void func_8002F990(s32 a0, s32 a1)
{
    u32 reg;
    u32 alto;

    reg = D_80010047[0] | (D_8001013C[0] << 8);
    if (a1 == 0) {
        reg = (u8)a0 + reg;
    }
    if (a1 == 1) {
        reg = reg + 1;
    }
    if (a1 == 2) {
        reg = reg - 1;
    }
    alto = reg & 0xFFFF;
    if (a1 == 3) {
        reg = reg - (u8)a0;
        alto = reg & 0xFFFF;
    }
    D_80010047[0] = reg;
    D_8001013C[0] = alto >> 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F990);
#endif
