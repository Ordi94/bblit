#include "common.h"
#include "globales.h"
#include "gte.h"
#include "objetos.h"
#include "niveles.h"

/* Identificador del sonido de arrastre del bloque empujable: sh y lh de 16 bits (func_8002D68C). */
extern s16 D_800695DE;

#ifdef NON_MATCHING
/* Pendiente: puntuacion 3383 con la configuracion versionada (g = 8 del archivo). Orden de instrucciones y reparto de registros: el original comparte entre los modos 0x10 y 0x400 la llamada a ApplyMatrixLV, calcula el divisor del balancin con otro orden de cargas y reparte el paso y el empuje en a0 y v1. */
/*
 * Manejador de los objetos moviles por mascara (clases 12, 13, 18, 19 y 22 a 29): una sola rutina
 * atiende doce modos, uno por bit de la mascara (balancin, giro, bajar o subir con el jugador,
 * oscilacion senoidal, recorrido entre limites, rampa), arrastra al jugador cuando lo lleva encima,
 * recorre los disparadores y aplica dano al contacto. Los limites y el origen del recorrido
 * comparten memoria con +0x184..+0x198 del objeto (MOVIL_*).
 */
void func_80026298(Objeto* o, u32 mascara)
{
    TrabajoMovil* t;
    NodoDisparador* n;
    VECTOR v;
    s32 paso;
    s32 num;
    s32 sentido;
    void* area;

    t = TRABAJO_MOVIL;
    area = (void*)0x1F80001C;
    if (o->u78.p == 0) {
        func_8001F268(o, &o->trabajo, 5, 2, area);
        o->flags18 |= 0x80;
        if (mascara & 0x20) {
            o->w17C = (s16)o->w17C >> 1;
            MOVIL_ORIGEN_X(o) = o->param.trans.vx;
            MOVIL_ORIGEN_Z(o) = o->param.trans.vz;
            o->w17E = 0;
            MOVIL_LIMITE_ALTO(o) = o->param.trans.vy + (s16)o->w17C;
            if (o->s1E == 0) {
                o->s1E = 0x10;
            }
        } else if (mascara & 0x10) {
            func_8001CF50(o);
            o->w17C = (s16)o->w17C >> 1;
            v.vx = 0;
            v.vy = 0;
            v.vz = (s16)o->w17C;
            ApplyMatrixLV(&o->coord.coord, &v, &v);
            MOVIL_ORIGEN_X(o) = o->param.trans.vx + v.vx;
            MOVIL_LIMITE_ALTO(o) = o->param.trans.vy + v.vy;
            MOVIL_ORIGEN_Z(o) = o->param.trans.vz + v.vz;
            o->w17E = 0;
            if (o->s1E == 0) {
                o->s1E = 0x10;
            }
        } else if (mascara & 0x400) {
            func_8001CF50(o);
            MOVIL_ORIGEN_X(o) = o->param.trans.vx;
            MOVIL_LIMITE_ALTO(o) = o->param.trans.vy;
            MOVIL_ORIGEN_Z(o) = o->param.trans.vz;
            o->w17E = 0;
            if (o->s1E == 0) {
                o->s1E = 0x10;
            }
            o->flags14 |= 0x2000;
        } else if (mascara & 0xC4) {
            if (o->s1E == 0) {
                o->s1E = 5;
            }
            paso = (s16)o->w17C;
            if (paso < 0) {
                num = o->param.trans.vy;
                sentido = num;
                sentido += paso;
            } else {
                num = o->param.trans.vy;
                sentido = num;
                num += paso;
            }
            MOVIL_LIMITE_ALTO(o) = num;
            MOVIL_LIMITE_BAJO(o) = sentido;
            if (mascara & 0x40) {
                o->flags14 |= 0x2000;
            }
        } else if (mascara & 8) {
            if ((s16)o->w17C < 0) {
                o->w17E = 0x400;
                o->w17C = -o->w17C;
            } else {
                o->w17E = 0xC00;
            }
            if (o->s1E == 0) {
                o->s1E = 0x22;
            }
        } else if (mascara & 1) {
            o->param.giro.u.z = 0;
        }
    }
    if (mascara & 2) {
        if (mascara & 0x20) {
            o->param.giro.u.y += 0x44;
        } else {
            o->param.giro.u.y += o->w17C;
        }
    } else if (mascara & 1) {
        paso = o->s1E;
        if (paso == 0) {
            paso = 0x20;
        }
        if (o->p6C == D_80069698 && o->p6C->p70 == o) {
            num = o->p6C->i1A4;
            if (num < 0) {
                if (o->w17C & 1) {
                    goto decae;
                }
                if (o->param.giro.rotate.vz >= -0x163) {
                    o->param.giro.u.z += (num * paso) / (o->s20 - o->min.vx);
                }
                sentido = (o->param.giro.rotate.vz * paso) / (o->s20 - o->min.vx);
            } else {
                if (o->w17C & 2) {
                    goto decae;
                }
                if (o->param.giro.rotate.vz < 0x164) {
                    o->param.giro.u.z += (num * paso) / (o->max.vx + o->s20);
                }
                sentido = (o->param.giro.rotate.vz * paso) / (o->s20 + o->max.vx);
            }
            D_80069698->coord.param->trans.vx += sentido;
        } else {
decae:
            o->param.giro.u.z -= (s16)o->param.giro.u.z >> 4;
        }
    } else if (mascara & 4) {
        o->flags14 &= 0xFF9FFFFF;
        if (o->p6C == D_80069698 && o->p6C->p70 == o) {
            goto sube;
        }
        num = MOVIL_LIMITE_BAJO(o);
        if (num < o->param.trans.vy) {
            o->param.trans.vy -= 5;
            if (!(num < o->param.trans.vy)) {
                o->param.trans.vy = num;
                o->flags14 |= 0x200000;
            }
        }
    } else if (mascara & 0x80) {
        o->flags14 &= 0xFF9FFFFF;
        if (o->p6C != D_80069698 || o->p6C->p70 != o) {
            goto sube;
        }
        num = MOVIL_LIMITE_BAJO(o);
        if (num < o->param.trans.vy) {
            o->param.trans.vy -= 5;
            if (!(num < o->param.trans.vy)) {
                o->param.trans.vy = num;
                o->flags14 |= 0x200000;
            }
        }
        goto seguir;
sube:
        num = MOVIL_LIMITE_ALTO(o);
        if (o->param.trans.vy < num) {
            o->param.trans.vy += 5;
            if (!(o->param.trans.vy < num)) {
                o->flags14 |= 0x400000;
                o->param.trans.vy = num;
            }
        }
    } else if (mascara & 0x40) {
        if (o->flags14 & 0x400000) {
            num = MOVIL_LIMITE_ALTO(o);
            paso = o->param.trans.vy;
            o->flags14 &= ~0x2000;
            if (paso < num) {
                o->param.trans.vy = paso + o->s1E;
                if (!(o->param.trans.vy < num)) {
                    o->param.trans.vy = num;
                }
            } else {
                o->flags14 = (o->flags14 & 0xFF9FFFFF) | 0x2000;
            }
        } else if (o->flags14 & 0x200000) {
            num = MOVIL_LIMITE_BAJO(o);
            paso = o->param.trans.vy;
            o->flags14 &= ~0x2000;
            if (num < paso) {
                o->param.trans.vy = paso - o->s1E;
                if (!(num < o->param.trans.vy)) {
                    o->flags14 |= 0x2000;
                    o->param.trans.vy = num;
                }
            } else {
                o->flags14 = (o->flags14 & 0xFF9FFFFF) | 0x2000;
            }
        }
    } else if (mascara & 8) {
        o->flags14 &= 0xFF9FFFFF;
        num = rsin((s16)o->w17E) * (s16)o->w17C;
        o->w17E += o->s1E;
        o->param.giro.u.z = num >> 12;
        if ((s16)o->w17E >= 0x1000) {
            o->flags14 |= 0x200000;
            o->w17E -= 0x1000;
        }
        if (o->p6C == D_80069698 && o->p6C->p70 == o) {
            t->v.vx = 0;
            t->v.vy = 0;
            func_8001CFCC(&o->coord);
            t->v.vz = 0;
            func_8001CFCC(&D_80069698->coord);
            t->cursor = &D_80069698->coord;
            if (t->cursor != 0) {
                do {
                    gte_SetRotMatrix(&t->cursor->coord);
                    gte_ldv0(&t->v);
                    gte_rtv0();
                    gte_stlvnl(t);
                    t->ax += t->cursor->coord.t[0];
                    t->ay += t->cursor->coord.t[1];
                    t->az += t->cursor->coord.t[2];
                    t->v.vx = t->ax;
                    t->v.vy = t->ay;
                    t->v.vz = t->az;
                    t->cursor = t->cursor->super;
                } while (t->cursor != 0);
            }
            D_80069698->param.trans.vx = t->ax;
            D_80069698->param.trans.vy = t->ay;
            D_80069698->param.trans.vz = t->az;
        }
    } else if (mascara & 0x10) {
        v.vx = 0;
        v.vy = 0;
        v.vz = (rsin((s16)o->w17E) * (s16)o->w17C) >> 12;
        paso = (s16)o->w17E;
        o->w17E = (o->w17E + o->s1E) & 0xFFF;
        if (paso < 0x400 && (s16)o->w17E >= 0x400) {
            o->flags14 |= 0x2000;
        } else if (paso < 0xC00 && (s16)o->w17E >= 0xC00) {
            o->flags14 |= 0x2000;
        } else {
            o->flags14 &= ~0x2000;
        }
        goto aplica;
    } else if (mascara & 0x400) {
        if (o->flags14 & 0x400000) {
            if ((s16)o->w17E > 0) {
                o->flags14 &= ~0x2000;
                o->w17E -= o->s1E;
            } else {
                o->w17E = 0;
                o->flags14 = (o->flags14 & 0xFF9FFFFF) | 0x2000;
            }
        } else if (o->flags14 & 0x200000) {
            if ((s16)o->w17E < (s16)o->w17C) {
                o->flags14 &= ~0x2000;
                o->w17E += o->s1E;
            } else {
                o->w17E = o->w17C;
                o->flags14 = (o->flags14 & 0xFF9FFFFF) | 0x2000;
            }
        }
        v.vx = 0;
        v.vy = 0;
        v.vz = (s16)o->w17E;
aplica:
        ApplyMatrixLV(&o->coord.coord, &v, &v);
        o->param.trans.vx = v.vx + MOVIL_ORIGEN_X(o);
        o->param.trans.vy = v.vy + MOVIL_LIMITE_ALTO(o);
        o->param.trans.vz = v.vz + MOVIL_ORIGEN_Z(o);
    } else if (mascara & 0x100) {
        if (o->p6C == D_80069698 && o->p6C->p70 == o) {
            o->p6C->coord.param->trans.vz += (s16)o->w17C;
        }
    } else if (mascara & 0x200) {
        if (o->p6C == D_80069698 && o->p6C->p70 == o && (o->flags14 & 0x200000)) {
            o->p6C->coord.param->trans.vz += (s16)o->w17C;
        }
    }
seguir:
    if (mascara & 0x20) {
        v.vx = 0;
        v.vz = 0;
        v.vy = (rsin((s16)o->w17E) * (s16)o->w17C) >> 12;
        paso = (s16)o->w17E;
        o->w17E = o->w17E + o->s1E;
        if (paso < 0x400 && (s16)o->w17E >= 0x400) {
            o->flags14 |= 0x2000;
        } else if (paso < 0xC00 && (s16)o->w17E >= 0xC00) {
            o->flags14 |= 0x2000;
        } else {
            o->flags14 &= ~0x2000;
        }
        ApplyMatrixLV(&o->coord.coord, &v, &v);
        o->w17E = o->w17E & 0xFFF;
        o->param.trans.vx = v.vx + MOVIL_ORIGEN_X(o);
        o->param.trans.vy = v.vy + MOVIL_LIMITE_ALTO(o);
        o->param.trans.vz = v.vz + MOVIL_ORIGEN_Z(o);
    }
    n = (NodoDisparador*)o->apoyos;
    if (n != 0) {
        do {
            if (n->req14 == 0 || (o->flags14 & n->req14)) {
                if (n->req18 == 0 || (o->flags18 & n->req18)) {
                    if (TestLogicCond(o, &n->cond) != 0) {
                        RunLogicAction(o, &n->cond);
                        if (n->flags & 0x200) {
                            func_8003F06C(o, n->p1C, 1, D_8006967C);
                        }
                        if (n->flags & 0x400) {
                            func_8003F06C(o, n->p1C, 2, D_8006967C);
                        }
                        if (n->flags & 0x10000) {
                            o->flags14 |= 0x100;
                            return;
                        }
                        if (!(n->flags & 0x8000)) {
                            break;
                        }
                    }
                }
            }
            n = n->sig;
        } while (n != 0);
    }
    if (o->flags08 & 0x20000000) {
        if (!(D_80069698->flags14 & 0x10)) {
            o->flags14 |= 0x40;
            if ((D_80069698->flags14 & 0x03000020) == 0 || (o->flags08 & 0x40000000)) {
                if ((o->flags14 & 0x8000) || func_80018F80(D_80069698, o, area) != 0
                    || func_80018F80(o, D_80069698, area) != 0) {
                    func_8001D75C(o, 0, area);
                }
            }
            goto fin;
        }
    }
    o->flags14 &= ~0x40;
fin:
    func_8001CF50(o);
    o->flags14 &= 0xF1676F7F;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026298);
#endif

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026FEC);

/*
 * Manejador de la zona de eventos (clase 16). Se anuncia como objeto activo cercano en D_8006D9B8
 * cuando lo pide la bandera 0x10 o el jugador esta a menos de 0x7D0 unidades en el plano. Cada
 * cuadro recorre los disparadores: filtra por azar, evalua la condicion (si falla salta al nodo
 * cuyo identificador indica el disparador) y por distancia al objeto o punto de referencia, y al
 * cumplirse ejecuta la accion y los efectos que pide flags (sonido, hijo, mover al jugador,
 * destruir otro objeto, cambiar de nivel, animar al jugador). Sin la bandera 0x8000 el recorrido
 * termina en el primer disparador ejecutado.
 */
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
/* Pendiente: puntuacion 365 con la configuracion versionada (g = 8 del archivo). Prologo y salida de la busqueda por id: el original deriva la matriz del scratchpad de la base despues de calcular la parte alta de la camara, y sale de la busqueda con un salto directo al caso sin origen en lugar de volver a probar el cursor. */
/*
 * Manejador del director de camara (clase 36): por cada disparador cuya condicion y distancia se
 * cumplen reescribe el destino de vista y de mira de la camara global, la distancia de acercamiento
 * y las banderas de seguimiento (flags80), o corta la camara de golpe copiando la vista actual a
 * todas sus copias. El origen del destino puede ser el jugador, otro objeto buscado por
 * identificador, este mismo objeto o constantes del disparador.
 */
void func_8002C1DC(Objeto* o)
{
    TrabajoCamara* t;
    MATRIX* m;
    s32 paso;
    s32 ca;
    s32 cb;
    s32 cc;
    s32 cd;
    s32 ce;
    s32 cf;
    u16 fl;
    s32 cond;

    t = TRABAJO_CAMARA;
    t->nodo = (NodoDisparador*)o->apoyos;
    if (t->nodo == 0) {
        return;
    }
    m = (MATRIX*)0x1F800050;
    do {
        t->flags = t->nodo->flags;
        if (t->nodo->cond != 0 && TestLogicCond(o, &t->nodo->cond) == 0) {
            goto siguiente;
        }
        if (t->flags & 0x4000) {
            D_8006D928.flags80 |= 8;
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
            cond = (t->flags & 0x42);
            t->origen = 0;
            if (cond == 0x40) {
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
                    t->vz = D_80069698->param.trans.vz - t->origen->param.trans.vz;
                    t->vy = 0;
                    t->gz = 0;
                    t->gx = 0;
                    t->gy = 0x1000 - t->origen->param.giro.u.y;
                    t->escala.vy = 0x1000;
                    t->escala.vx = 0x1000;
                    t->escala.vz = 0;
                    RotMatrix((SVECTOR*)&t->gx, m);
                    ApplyMatrixSV(m, (SVECTOR*)&t->vx, (SVECTOR*)&t->vx);
                    RotMatrix(&t->origen->param.giro.rotate, m);
                    ScaleMatrix(m, &t->escala);
                    ApplyMatrixSV(m, (SVECTOR*)&t->vx, (SVECTOR*)&t->vx);
                    D_8006D928.dvx = t->origen->param.trans.vx + (s16)t->vx;
                    D_8006D928.dvy = t->origen->param.trans.vy + (s16)t->vy;
                    D_8006D928.dvz = t->origen->param.trans.vz + (s16)t->vz;
                } else {
                    D_8006D928.dvx = t->origen->param.trans.vx;
                    D_8006D928.dvy = t->origen->param.trans.vy;
                    D_8006D928.dvz = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80000) {
                t->vx = 0;
                t->vy = -(u16)t->nodo->p20;
                t->vz = (u16)t->nodo->p1C;
                GEO_IDENTIDAD(m);
                RotMatrixY(D_80069698->param.giro.rotate.vy + 0x800, m);
                ApplyMatrix(m, (SVECTOR*)&t->vx, &t->r);
                D_8006D928.dvx += ((D_80069698->param.trans.vx + t->r.vx) - D_8006D928.dvx) >> 2;
                D_8006D928.dvy += ((D_80069698->param.trans.vy + t->r.vy) - D_8006D928.dvy) >> 2;
                D_8006D928.dvz += ((D_80069698->param.trans.vz + t->r.vz) - D_8006D928.dvz) >> 2;
                D_8006D928.dmx += (D_80069698->param.trans.vx - D_8006D928.dmx) >> 2;
                D_8006D928.dmy += (D_80069698->param.trans.vy - D_8006D928.dmy) >> 2;
                D_8006D928.dmz += (D_80069698->param.trans.vz - D_8006D928.dmz) >> 2;
            } else if (t->flags & 0x100000) {
                D_8006D928.dvx = D_8006D928.vpx;
                D_8006D928.dvy = D_8006D928.vpy;
                D_8006D928.dvz = D_8006D928.vpz;
            } else {
                D_8006D928.dvx = t->nodo->p1C;
                D_8006D928.dvy = t->nodo->p20;
                D_8006D928.dvz = t->nodo->desplazamiento;
            }
            if (t->flags & 0x40000) {
                t->ex = D_8006D928.vpx - D_8006D928.dvx;
                t->ey = D_8006D928.vpy - D_8006D928.dvy;
                t->ez = D_8006D928.vpz - D_8006D928.dvz;
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
                    D_8006D928.dvx += (t->r.vx * t->modulo) >> 12;
                    D_8006D928.dvy += (t->r.vy * t->modulo) >> 12;
                    D_8006D928.dvz += (t->r.vz * t->modulo) >> 12;
                }
            }
            D_8006D928.flags80 |= 0x400;
        } else if (t->flags & 4) {
            D_8006D928.flags80 &= 0xBBFF;
        }
        if (t->flags & 2) {
            if (t->flags & 0x40) {
                for (t->origen = D_80069518; t->origen != 0; t->origen = t->origen->siguiente) {
                    if (t->origen->w1C == t->nodo->p20 && !(t->origen->flags14 & 0x100)) {
                        break;
                    }
                }
                if (t->origen != 0) {
                    D_8006D928.dmx = t->origen->param.trans.vx;
                    D_8006D928.dmy = t->origen->param.trans.vy;
                    D_8006D928.dmz = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80) {
                D_8006D928.dmx = o->param.trans.vx;
                D_8006D928.dmy = o->param.trans.vy;
                D_8006D928.dmz = o->param.trans.vz;
            } else if (t->flags & 0x100000) {
                D_8006D928.dmx = D_8006D928.x;
                D_8006D928.dmy = D_8006D928.y;
                D_8006D928.dmz = D_8006D928.z;
            } else {
                D_8006D928.dmx = t->nodo->p1C;
                D_8006D928.dmy = t->nodo->p20;
                D_8006D928.dmz = t->nodo->desplazamiento;
            }
            D_8006D928.flags80 |= 0x800;
        } else if (t->flags & 8) {
            D_8006D928.flags80 &= 0xB7FF;
        }
        if (t->flags & 0x400) {
            D_8006D928.zoom = t->nodo->p1C;
            D_8006D928.flags80 |= 0x1000;
        } else if (t->flags & 0x800) {
            D_8006D928.flags80 &= 0xEFFF;
        }
        if (t->flags & 0x10000) {
            ca = D_8006D928.vpx;
            cb = D_8006D928.vpy;
            cc = D_8006D928.vpz;
            cd = D_8006D928.x;
            ce = D_8006D928.y;
            cf = D_8006D928.z;
            fl = D_8006D928.flags80;
            fl |= 0x4000;
            D_8006D928.c68 = ca;
            D_8006D928.c94 = ca;
            D_8006D928.cB4 = ca;
            D_8006D928.c6C = cb;
            D_8006D928.c98 = cb;
            D_8006D928.cB8 = cb;
            D_8006D928.c70 = cc;
            D_8006D928.c9C = cc;
            D_8006D928.cBC = cc;
            D_8006D928.cA4 = cd;
            D_8006D928.cA8 = ce;
            D_8006D928.cAC = cf;
            D_8006D928.flags80 = fl;
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

/*
 * Manejador del sprite animado con caja de colision y disparadores (clase 4 de D_8005E35C). En el
 * primer cuadro reserva el ayudante, busca el descriptor de tipo 8 en la lista de animaciones,
 * deriva la caja del objeto del tamano del primer cuadro y arma la matriz del nodo. Despues avanza
 * un cuadro cada b05 cuadros de juego y recorre los disparadores hasta el primero cuya condicion se
 * cumple: ejecuta su accion, avisa el sonido de inicio o fin y destruye el objeto si el disparador
 * lo pide y la animacion llego al ultimo cuadro. Si no hay ayudante disponible el original se queda
 * en un bucle sin salida.
 */
void func_8002CB8C(Objeto* o)
{
    BloqueTrabajo* b;
    NodoAnimacion* a;
    NodoDisparador* n;
    Fotograma* f;
    void* area;
    TablaFotogramas* tb;
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
        w = b->b05;
        b->h02 = b->h02 + 1;
        b->b08 = w;
        if ((u16)b->h02 > b->h00) {
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

/*
 * Manejador del sprite decorativo (clase 20): igual que el de sprite con caja pero sin disparadores
 * ni caja de colision. Toma el intervalo y el cuadro inicial de la caja del objeto, anima con la
 * variante de formato escalado y en cada cuadro vuelve a pedir el dibujo del objeto.
 */
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

#ifdef NON_MATCHING
/* Pendiente: puntuacion 4613 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original guarda el objeto en s4, el scratchpad en s3, el area en s5 y el margen de la caja en s6 y deja s0 a s2 para los punteros de la preparacion; el compilador los reparte un registro mas abajo. La estructura de las ocho esquinas y de los dos modos coincide. */
/*
 * Prueba de suelo bajo la posicion de prueba (t->py): si el bloque se despegaria mas de 0xC8
 * unidades del terreno, se anula el desplazamiento pedido. Solo se aplica con el modo 0x80.
 */
#define BLOQUE_SIN_SUELO() \
    { \
        if (o->w17C & 0x80) { \
            if (t->bits & 2) { \
                if ((s16)t->altura + t->py - o->param.trans.vy >= 0xC9) { \
                    t->bits |= 8; \
                } \
            } \
            if (t->bits & 8) { \
                t->dz = 0; \
                t->dx = 0; \
            } \
        } \
    }

/* Prueba una esquina de la caja girada moviendo en X: avance t->dx contra el terreno. */
#define BLOQUE_ESQUINA_X(ex, ez) \
    { \
        t->px = o->param.trans.vx + (s16)t->ex; \
        t->py = o->param.trans.vy; \
        t->vx = t->dx; \
        t->vz = 0; \
        t->vy = 0; \
        t->pz = o->param.trans.vz + (s16)t->ez; \
        *(s32*)area = 0; \
        t->zona = o->w26; \
        func_80019474(&t->px, &t->vx, t, area); \
        t->dx = t->vx; \
        BLOQUE_SIN_SUELO(); \
    }

/* Igual que BLOQUE_ESQUINA_X pero moviendo en Z: avance t->dz. */
#define BLOQUE_ESQUINA_Z(ex, ez) \
    { \
        t->px = o->param.trans.vx + (s16)t->ex; \
        t->py = o->param.trans.vy; \
        t->vz = t->dz; \
        t->vx = 0; \
        t->vy = 0; \
        t->pz = o->param.trans.vz + (s16)t->ez; \
        *(s32*)area = 0; \
        t->zona = o->w26; \
        func_80019474(&t->px, &t->vx, t, area); \
        t->dz = t->vz; \
        BLOQUE_SIN_SUELO(); \
    }

/* Filtra el desplazamiento pedido d segun el eje (bit eje) y el sentido permitido (0x100, 0x200). */
#define BLOQUE_FILTRAR(d, eje) \
    { \
        if (!(o->w17C & (eje))) { \
            d = 0; \
        } else { \
            if ((o->w17C & 0x100) && d < 0) { \
                d = 0; \
            } else if ((o->w17C & 0x200) && d > 0) { \
                d = 0; \
            } \
        } \
    }

/*
 * Manejador del bloque empujable (clase 5). El jugador deja en h40 y h44 el desplazamiento que
 * intenta hacer contra el bloque; w17C fija los ejes y sentidos permitidos (0x01 X, 0x02 Z, 0x100 y
 * 0x200 anulan el sentido negativo o positivo, 0x04 prueba en dos pasadas, 0x40 modo plataforma,
 * 0x80 no cae). El avance se prueba contra otros objetos y contra el terreno desde las cuatro
 * esquinas de la caja girada, se aplica al bloque, la parte que no pudo absorber vuelve al jugador y
 * se controla el sonido de arrastre. Termina con la gravedad del bloque.
 */
void func_8002D68C(Objeto* o)
{
    TrabajoBloque* t;
    NodoDisparador* n;
    MATRIX* m;
    void* area;
    s32 margen;
    s32 cuarto;
    Objeto* jugador;
    u8 flags;
    s16 id;
    s32 reserva[2];

    t = TRABAJO_BLOQUE;
    area = (void*)0x1F8000A8;
    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
        o->u78.ayudas = func_800363D4();
        if (o->u78.ayudas == 0) {
            for (;;) {
            }
        }
        m = &t->m;
        if (o->lista->def->wA & 2) {
            o->u78.ayudas->flags8 |= 2;
            GsInitCoordinate2(0, o->u78.ayudas->pcoord);
            o->u78.ayudas->pcoord->super = &o->coord;
            o->coord.param = PARAMETROS_SDK(o);
            o->u78.ayudas->w14 = (s32)o->lista->def->tabla;
        }
        GEO_IDENTIDAD(m);
        ScaleMatrix(m, (VECTOR*)&o->param);
        ApplyMatrixSV(m, &o->min, &o->min);
        ApplyMatrixSV(m, &o->max, &o->max);
        func_8001CF50(o);
        if (o->w17C & 0x20) {
            o->flags14 |= 4;
        }
    }
    if (o->w17C & 0x40) {
        D_80069698->param.trans.vx -= o->h40;
        D_80069698->param.trans.vz -= o->h44;
        o->h40 = 0;
        o->h44 = 0;
        goto reposo;
    }
    if (!((o->flags14 & 0x8000) && !(D_80069698->flags14 & 0x4000))) {
        if (func_80016C0C(o, 0x20000, area) == 0) {
            goto sin_empuje;
        }
    }
    m = &t->m;
    margen = (s16)o->s20 >> 1;
    RotMatrix(&o->param.giro.rotate, m);
    cuarto = margen >> 1;
    GEO_CARGAR_WH(&o->min);
    GEO_GUARDAR_WH(&t->mnx);
    GEO_CARGAR_WH(&o->max);
    GEO_GUARDAR_WH(&t->mxx);
    t->mnx -= cuarto;
    t->mnz -= cuarto;
    t->mxx += cuarto;
    t->mxz += cuarto;
    ApplyMatrixSV(m, (SVECTOR*)&t->mnx, (SVECTOR*)&t->mnx);
    ApplyMatrixSV(m, (SVECTOR*)&t->mxx, (SVECTOR*)&t->mxx);
    t->dz = o->h44;
    t->dy = 0;
    t->dx = o->h40;
    if (o->w17C & 4) {
        t->px = o->param.trans.vx;
        t->py = o->param.trans.vy;
        t->pz = o->param.trans.vz;
        if (!(o->w17C & 1)) {
            t->dx = 0;
        } else {
            t->px += (s16)t->mnx;
            if ((o->w17C & 0x100) && t->dx < 0) {
                t->dx = 0;
            } else if ((o->w17C & 0x200) && t->dx > 0) {
                t->dx = 0;
            }
        }
        if (!(o->w17C & 2)) {
            t->dz = 0;
        } else {
            t->pz += (s16)t->mnz;
            if ((o->w17C & 0x100) && t->dz < 0) {
                t->dz = 0;
            } else if ((o->w17C & 0x200) && t->dz > 0) {
                t->dz = 0;
            }
        }
        t->cx = t->dx;
        t->cy = t->dy;
        t->cz = t->dz;
        t->chocado = func_80017478(o, &t->cx, area, 0x2690A);
        if (t->chocado != 0) {
            t->chocado->flags14 |= 0x40000000;
            t->chocado->i34 = o->w1C;
            o->i34 = t->chocado->w1C;
            if (!(t->chocado->flags08 & 0x2000000)) {
                if (o->w17C & 1) {
                    t->dx = (s16)t->cx;
                }
                if (o->w17C & 2) {
                    t->dz = (s16)t->cz;
                }
            }
        }
        *(s32*)area = 0;
        t->zona = o->w26;
        func_80019474(&t->px, &t->dx, t, area);
        t->px = o->param.trans.vx;
        t->py = o->param.trans.vy;
        t->pz = o->param.trans.vz;
        if (o->w17C & 1) {
            t->px += (s16)t->mxx;
        }
        if (o->w17C & 2) {
            t->pz += (s16)t->mxz;
        }
        *(s32*)area = 0;
        t->zona = o->w26;
        func_80019474(&t->px, &t->dx, t, area);
        if (o->w17C & 0x80) {
            t->px = o->param.trans.vx + t->dx;
            t->py = o->param.trans.vy;
            t->pz = o->param.trans.vz + t->dz;
            t->zona = o->w26;
            func_8001C134(&t->px, (ResultadoBaldosa*)t, (TrabajoBaldosa*)area);
            if (t->bits & 2) {
                if ((s16)t->altura + t->py - o->param.trans.vy >= 0xC9) {
                    t->bits |= 8;
                }
            }
            if (t->bits & 8) {
                t->dz = 0;
                t->dx = 0;
            }
        }
        o->param.trans.vx += t->dx;
        o->param.trans.vz += t->dz;
        D_80069698->param.trans.vx -= o->h40 - t->dx;
        D_80069698->param.trans.vz -= o->h44 - t->dz;
        goto disparadores;
    }
    BLOQUE_FILTRAR(t->dx, 1);
    BLOQUE_FILTRAR(t->dz, 2);
    t->cx = t->dx;
    t->cy = t->dy;
    t->cz = t->dz;
    o->p70 = D_80069698;
    t->chocado = func_80017478(o, &t->cx, area, 0x2690A);
    if (t->chocado != 0) {
        t->chocado->flags14 |= 0x40000000;
        t->chocado->i34 = o->w1C;
        o->i34 = t->chocado->w1C;
        if (!(t->chocado->flags08 & 0x2000000)) {
            if (o->w17C & 1) {
                t->dx = (s16)t->cx;
            }
            if (o->w17C & 2) {
                t->dz = (s16)t->cz;
            }
        }
    }
    o->p70 = 0;
    BLOQUE_ESQUINA_X(mnx, mnz);
    BLOQUE_ESQUINA_Z(mnx, mnz);
    BLOQUE_ESQUINA_X(mxx, mnz);
    BLOQUE_ESQUINA_Z(mxx, mnz);
    BLOQUE_ESQUINA_X(mnx, mxz);
    BLOQUE_ESQUINA_Z(mxx, mxz);
    BLOQUE_ESQUINA_X(mxx, mxz);
    BLOQUE_ESQUINA_Z(mxx, mxz);
    if (!(o->flags0C & 0x80)) {
        if (t->dx != 0) {
            t->py = o->param.trans.vy;
            if (t->dx < 0) {
                t->px = o->param.trans.vx + o->min.vx - margen;
            } else {
                t->px = o->param.trans.vx + o->max.vx + margen;
            }
            t->pz = o->param.trans.vz + o->min.vz - margen;
            t->vx = 0;
            t->vy = 0;
            t->vz = o->max.vz - o->min.vz + margen;
            *(s32*)area = 0;
            t->zona = o->w26;
            func_80019474(&t->px, &t->vx, t, area);
            if (t->bits & 4) {
                t->dx = 0;
            }
        }
        if (t->dz != 0) {
            t->px = o->param.trans.vx + o->min.vx - margen;
            t->py = o->param.trans.vy;
            if (t->dz < 0) {
                t->pz = o->param.trans.vz + o->min.vz - margen;
            } else {
                t->pz = o->param.trans.vz + o->max.vz + margen;
            }
            t->vz = 0;
            t->vy = 0;
            t->vx = o->max.vx - o->min.vx + margen;
            *(s32*)area = 0;
            t->zona = o->w26;
            func_80019474(&t->px, &t->vx, t, area);
            if (t->bits & 4) {
                t->dz = 0;
            }
        }
    }
    if (o->w17C & 0x80) {
        t->px = o->param.trans.vx + t->dx;
        t->py = o->param.trans.vy;
        t->pz = o->param.trans.vz + t->dz;
        t->zona = o->w26;
        func_8001C134(&t->px, (ResultadoBaldosa*)t, (TrabajoBaldosa*)area);
        if (t->bits & 2) {
            if ((s16)t->altura + t->py - o->param.trans.vy >= 0xC9) {
                t->bits |= 8;
            }
        }
        if (t->bits & 8) {
            t->dz = 0;
            t->dx = 0;
        }
    }
    o->param.trans.vz += t->dz;
    id = o->s1E;
    o->param.trans.vx += t->dx;
    o->flags18 |= 0x8000;
    D_800695DE = id;
    if (t->dx != 0 || t->dz != 0) {
        flags = D_800694F2;
        if (!(flags & 1)) {
            D_800694F2 = flags | 1;
            func_8003F06C(o, id, 1, D_8006967C);
        }
    } else {
        flags = D_800694F2;
        if (flags & 1) {
            D_800694F2 = flags & 0xFE;
            func_8003F06C(o, id, 2, D_8006967C);
        }
    }
    t->vx = t->dx - o->h40;
    t->vy = 0;
    t->vz = t->dz - o->h44;
    jugador = D_80069698;
    t->px = jugador->param.trans.vx;
    t->py = jugador->param.trans.vy;
    t->pz = jugador->param.trans.vz;
    t->zona = o->w26;
    func_80019474(&t->px, &t->vx, t, area);
    D_80069698->param.trans.vx += t->vx;
    D_80069698->param.trans.vz += t->vz;
disparadores:
    n = (NodoDisparador*)o->apoyos;
    if (n != 0) {
        do {
            if (n->req14 == 0 || (o->flags14 & n->req14)) {
                if (TestLogicCond(o, &n->cond) != 0) {
                    RunLogicAction(o, &n->cond);
                    o->p70 = 0;
                    goto reposo;
                }
            }
            n = n->sig;
        } while (n != 0);
    }
    o->p70 = 0;
    goto reposo;
sin_empuje:
    if (o->flags18 & 0x8000) {
        o->flags18 &= 0xFFFF7FFF;
        flags = D_800694F2;
        if (flags & 1) {
            D_800694F2 = flags & 0xFE;
            func_8003F06C(o, D_800695DE, 2, D_8006967C);
        }
    }
reposo:
    ZONA_PONER_CERO_3W(&t->dx);
    func_8001CBB8(o, &t->dx, t, area);
    o->param.trans.vy += t->dy;
    func_8001CF50(o);
    o->h44 = 0;
    o->h40 = 0;
    o->flags14 &= 0xFFFF5FFF;
    if (o->flags08 & 0x1000000) {
        func_8001E1A4(o, area);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D68C);
#endif

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EA9C);

/*
 * Manejador del efecto anclado a un nodo de otro objeto (clase 34). Elige la secuencia de animacion
 * (la de w17E; al acabar vuelve a la de identificador 1), reparte el dano a un objeto cercano si el
 * fotograma lo pide, anima y, si el objeto cuelga de un nodo, acumula la posicion global recorriendo
 * la cadena de matrices con el GTE. Se destruye al terminar la animacion si el fotograma lo pide y
 * cuando pierde a su portador.
 */
void func_8002EAA4(Objeto* o)
{
    TrabajoEfecto* t;
    GsCOORDINATE2* c;
    u16 id;
    void* area;
    s32 r;
    NodoSecuencia* n;
    u8 reserva[0x20];

    t = TRABAJO_EFECTO;
    area = (void*)0x1F800044;
    if (o->u78.p == 0 && !(o->trabajo.flags18 & 0x4000)) {
        t->secuencia = o->secuencias;
        t->id = 2;
        if (t->secuencia != 0) {
            while (1) { n = t->secuencia; if (n->id == 2) { break; } t->secuencia = n->sig; if (t->secuencia == 0) { break; } }
        }
        o->flags18 |= 0x80;
        if (t->secuencia == 0) {
            t->secuencia = o->secuencias;
            t->id = 1;
            if (t->secuencia != 0) {
                while (1) { n = t->secuencia; if (n->id == 1) { break; } t->secuencia = n->sig; if (t->secuencia == 0) { break; } }
            }
        }
        o->w17E = t->id;
        o->p180 = t->secuencia;
        o->w17C = 0;
        t->fotograma = (RegistroAnim*)(o->bloque + t->secuencia->desplazamiento);
        o->registro184 = t->fotograma;
    }
    t->secuencia = o->secuencias;
    id = o->w17E;
    t->id = id;
    for (; t->secuencia != 0; t->secuencia = t->secuencia->sig) {
        if (t->secuencia->id == id) {
            break;
        }
    }
    t->paso = *(u16*)((u8*)t->secuencia + (o->w17C << 1) + 6);
    if (t->paso == 0xFFF0 || o->w17C >= 5) {
        for (t->secuencia = o->secuencias; t->secuencia != 0; t->secuencia = t->secuencia->sig) {
            if (t->secuencia->id == 1) {
                break;
            }
        }
        o->w17E = 1;
        o->p180 = t->secuencia;
        o->w17C = 0;
        o->flags14 &= 0xF9FFFFDF;
        t->fotograma = (RegistroAnim*)(o->bloque + t->secuencia->desplazamiento);
        o->registro184 = t->fotograma;
        o->p180 = t->secuencia;
        o->trabajo.i14 = 0;
    } else {
        t->fotograma = (RegistroAnim*)(o->bloque + *(u16*)((u8*)t->secuencia + (o->w17C << 1) + 6));
    }
    o->registro184 = t->fotograma;
    o->p180 = t->secuencia;
    if (t->fotograma->w0C & 0x20000) {
        t->otro = func_80016ED0(o, 0x80, area);
        if (t->otro != 0) {
            t->otro->flags14 |= 0x2000000;
            t->otro->i34 = o->w1C;
            o->i34 = t->otro->w1C;
            t->otro->w38 = t->fotograma->w16;
        }
    }
    if (o->trabajo.i14 != t->fotograma->w06) {
        func_8001F268(o, &o->trabajo, t->fotograma->w06, t->fotograma->w08, area);
    } else {
        r = func_8001F268(o, &o->trabajo, 0, 0, area);
        if (r == 0x100) {
            o->trabajo.i14 = 0;
            if (t->fotograma->w0C & 4) {
                o->flags14 |= 0x100;
                return;
            }
            o->w17C += 1;
        }
    }
    if (o->coord.super != 0) {
        t->vy = 0;
        t->vx = 0;
        t->vz = 0x1000;
        ZONA_PONER_CERO_WH(&t->ax);
        c = &o->coord;
        t->cursor = c;
        if (t->cursor != 0) {
            do {
                gte_SetRotMatrix(&t->cursor->coord);
                gte_ldv0(&t->ax);
                gte_rtv0();
                gte_stlvnl(&t->px);
                gte_SetRotMatrix(&t->cursor->coord);
                gte_ldv0(&t->vx);
                gte_rtv0();
                gte_stsv(&t->vx);
                GEO_CARGAR_W(&t->cursor->coord.t[0]);
                GEO_SUMAR_W(&t->px);
                GEO_CARGAR_W(&t->px);
                ZONA_GUARDAR_H_T1(&t->ax);
                t->cursor = t->cursor->super;
            } while (t->cursor != 0);
        }
        o->param.giro.u.y = ratan2(t->vx, t->vz);
        o->param.giro.u.z = 0;
        o->param.giro.u.x = 0;
        ZONA_CARGAR_H(&t->ax);
        GEO_GUARDAR_W_T1(&o->param.trans);
    }
    if (o->p70 == 0) {
        o->flags14 |= 0x100;
    }
}

/*
 * Manejador del proyectil balistico (clase 31): en el primer cuadro orienta el proyectil hacia el
 * jugador y crea el hijo de la plantilla 0x14. Durante 0x3C cuadros avanza segun la velocidad del
 * objeto rotada por su matriz, resuelve el choque contra el terreno y contra los objetos: si
 * alcanza al jugador le hace dano, si alcanza a otro objeto le deja el identificador del atacante;
 * al impactar o chocar con una pared crea el efecto 0x13 y se destruye.
 */
void func_8002F018(Objeto* o)
{
    TrabajoProyectil* t;
    Ayuda* a;
    Objeto* p;
    MATRIX* m;
    MATRIX* mm;
    s32* pos;
    s32 dx;
    s32 dz;
    s32 d;
    void* area;

    t = TRABAJO_PROYECTIL;
    area = (void*)0x1F800098;
    t->vz = 0;
    t->vy = 0;
    t->vx = 0;
    if (o->u78.p == 0) {
        o->flags18 |= 0x80;
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
        o->w3C |= 0x40;
        a = o->u78.ayudas;
        ZONA_PONER_CERO_WH(&a->param.rotate);
        ZONA_PONER_CERO_3W(&o->u78.ayudas->param.scale);
        ZONA_PONER_CERO_3W(&o->u78.ayudas->param.trans);
        o->w22 = 0;
        if (!(o->flags0C & 0x20020)) {
            p = D_80069698;
            dx = p->param.trans.vx - o->param.trans.vx;
            t->mx = dx;
            t->my = p->param.trans.vy - o->param.trans.vy + ((s16)p->max.vy >> 1);
            dz = p->param.trans.vz - o->param.trans.vz;
            t->mz = dz;
            d = SquareRoot0(dx * dx + dz * dz);
            o->param.giro.u.x = -ratan2(t->my, d);
            o->param.giro.u.z = 0;
            o->p6C = 0;
        }
        m = &o->coord.coord;
        TransMatrix(m, (VECTOR*)((u8*)o->coord.param + 0x18));
        if (!(o->flags0C & 0x20)) {
            RotMatrixZYX((SVECTOR*)((u8*)o->coord.param + 0x10), m);
            ScaleMatrix(m, (VECTOR*)o->coord.param);
        }
        func_80036734(0x14, (s32*)&o->param.trans.vx, &o->param.giro.u.x);
    } else {
        t->vz = (u16)o->s20;
    }
    if (o->w22 < 0x3D) {
        mm = &o->coord.coord;
        gte_SetRotMatrix(mm);
        gte_ldv0(&t->vx);
        gte_rtv0();
        gte_stlvnl(&t->mx);
        GEO_CARGAR_W(&t->mx);
        GEO_GUARDAR_W_T1(&t->dx);
        pos = (s32*)&o->param.trans;
        GEO_CARGAR_W(pos);
        GEO_GUARDAR_W_T1(&t->px);
        t->zona = o->w26;
        func_80019474(&t->px, &t->dx, t, area);
        t->px = o->param.trans.vx + t->dx;
        t->pz = o->param.trans.vz + t->dz;
        t->py = o->param.trans.vy + t->my;
        t->golpeado = func_800171E4(o, &t->px, 0x180, 0, area);
        if (t->golpeado != 0) {
            o->s1E = 1;
            if (D_80069698 == t->golpeado && !(D_80069698->flags14 & 0x03000000)) {
                if (func_8001D75C(o, 0, area) != 0 && (s16)o->w196 != 0) {
                    func_8001D0FC(o, (s16)o->w196, area);
                }
            } else {
                t->golpeado->i34 = (u16)o->w1C;
                if (t->golpeado->registro184 != 0 && (t->golpeado->registro184->w10 & 8)) {
                    t->golpeado->w38 = o->s1E;
                    t->golpeado->flags14 |= 0x2000000;
                } else {
                    t->golpeado->flags14 |= 0x40000000;
                }
            }
            func_80036734(0x13, (s32*)&o->param.trans.vx, &o->param.giro.u.x);
        } else {
            o->param.trans.vx += t->dx;
            o->param.trans.vz += t->dz;
            o->param.trans.vy += t->my;
            if (!(t->bits & 4)) {
                goto matriz;
            }
            func_80036734(0x13, pos, &o->param.giro.u.x);
        }
    }
    o->flags14 |= 0x100;
    return;
matriz:
    TransMatrix(mm, (VECTOR*)((u8*)o->coord.param + 0x18));
}

/*
 * Manejador de la animacion de modelo por guion (clase 32). w17C es el tiempo de vida y w17E el
 * indice del guion con el bit 15 como marca de guion ya lanzado: al cumplirse la edad reanuda el
 * guion en curso o destruye el objeto; si no, lanza el guion que indica D_80069590 y repone la edad
 * del objeto, que la rutina del guion sobrescribe.
 */
void func_8002F510(Objeto* o)
{
    s16 vida;
    s16 idx;
    s32 edad;
    s32 edad2;
    u16 bits;
    u16* base;
    s16 idx2;
    u16 bits2;
    u16* base2;

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
    idx2 = o->w17E;
    bits2 = o->w17E;
    if (idx2 & 0x8000) {
        o->w17E = bits2 & 0x7FFF;
        return;
    }
    edad2 = o->w22;
    base2 = D_80069590;
    func_80045498(o, (u8*)base2 + base2[idx2], &o->trabajo);
    o->w22 = edad2;
}

/*
 * Manejador del objeto pegado a la camara (clase 9): en el primer cuadro destruye el objeto si no
 * tiene modelo y arma su animacion; en cada cuadro copia la posicion de la camara (la altura mas el
 * desplazamiento propio) y reconstruye la matriz del nodo.
 */
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

/*
 * Manejador de la zona sonda (clase 10): gira la caja del objeto con el desplazamiento de la camara
 * y marca con el bit 8 de flags18 los objetos solidos cuyo punto, visto desde la camara, cae dentro
 * de la caja. w196 invierte el signo de los ejes del desplazamiento.
 */
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
 * Pendiente: puntuacion 350 con la configuracion versionada (g = 8 del archivo). Dos 'lui' donde
 * el original usa uno solo para los dos bytes (los simbolos son variables externas distintas).
 *
 * Los dos bytes se declaran como arreglos sin tamano: con el umbral de datos pequenos (-G8) un
 * escalar de un byte se emite en forma simbolica con 'lui $at' y la funcion sube de 350 a 855,
 * mientras que el arreglo da el 'lui' y el desplazamiento del original.
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
