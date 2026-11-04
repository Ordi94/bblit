#include "common.h"
#include "globales.h"
#include "arranque.h"
#include "gte.h"
#include "objetos.h"
#include "niveles.h"

/* Identificador del sonido de arrastre del bloque empujable: sh y lh de 16 bits (LogicaBloqueEmpujable). */
extern s16 D_800695DE;

/*
 * Datos pequenos direccionados con desplazamiento($gp) por func_80026FEC: definiciones tentativas en
 * este archivo para que el ensamblador las reescriba a $gp (el enlace las coloca en 0x800693B4,
 * 0x800693B8, 0x800693C0 y 0x800693D0). D_800693B8 se declara ademas en globales.h.
 */
s32 D_800693B4;
s16 D_800693B8;
s32 D_800693C0;
u16 D_800693D0;

/* Actualizacion por cuadro de los indicadores de la interfaz (gestion_y_dibujo_de_objetos_2.c). */
extern void func_80039094(void);

#ifdef NON_MATCHING
/* Pendiente: puntuacion 2925 con la configuracion versionada (g = 8 del archivo). Reparto de registros y orden de instrucciones: el original comparte entre los modos 0x10 y 0x400 la llamada a ApplyMatrixLV, calcula el divisor del balancin con otro orden de cargas y reparte el paso y el empuje en a0 y v1. */
/*
 * Manejador de los objetos moviles por mascara (clases 12, 13, 18, 19 y 22 a 29): una sola rutina
 * atiende doce modos, uno por bit de la mascara (balancin, giro, bajar o subir con el jugador,
 * oscilacion senoidal, recorrido entre limites, rampa), arrastra al jugador cuando lo lleva encima,
 * recorre los disparadores y aplica dano al contacto. Los limites y el origen del recorrido
 * comparten memoria con +0x184..+0x198 del objeto (MOVIL_*).
 */
void LogicaObjetoMovil(Objeto* o, u32 mascara)
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
            v.vz = (s16)o->w17C;
            v.vy = 0;
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
            num = o->p6C->u18C.agarre.trans.vx;
            if (num < 0) {
                if (o->w17C & 1) {
                    goto decae;
                }
                if (o->param.giro.rotate.vz >= -0x163) {
                    o->param.giro.u.z += (num * paso) / (o->radio - o->min.vx);
                }
                sentido = (o->param.giro.rotate.vz * paso) / (o->radio - o->min.vx);
            } else {
                if (o->w17C & 2) {
                    goto decae;
                }
                if (o->param.giro.rotate.vz < 0x164) {
                    o->param.giro.u.z += (num * paso) / (o->max.vx + o->radio);
                }
                sentido = (o->param.giro.rotate.vz * paso) / (o->radio + o->max.vx);
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
            t->v.vz = 0;
            func_8001CFCC(&o->coord);
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
        v.vz = (rsin((s16)o->w17E) * (s16)o->w17C) >> 12;
        v.vy = 0;
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
        v.vz = (s16)o->w17E;
        v.vy = 0;
        v.vx = 0;
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
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", LogicaObjetoMovil);
#endif

/*
 * Vista sin signo del giro Y de un bloque de parametros que llega como GsCOORD2PARAM*: el original
 * lo lee con lhu y lo escribe con sh (0x12), y las lecturas con signo del mismo campo usan
 * ->rotate.vy (lh).
 */
#define GIRO_Y(p) (((ParametrosObjeto*)(p))->giro.u.y)

#ifdef NON_MATCHING
/* Pendiente: puntuacion 42153 con la configuracion versionada (g = 8 del archivo). Traduccion completa de la logica; la funcion mide 186 instrucciones mas que el original y el reparto de registros y la forma de las ramas anidadas todavia difieren. */
/*
 * Manejador de un personaje animado de la escena (clase 14 de D_8005E35C): enemigo, jefe, ayudante,
 * vehiculo o animal que se controla. Cada cuadro elige la secuencia de animacion (la de golpe o
 * muerte si lo hirieron, la del paso siguiente si no), interpreta las banderas del fotograma
 * (ataque, dano, oscilacion, vuelo, movimiento con el mando o hacia un objetivo, lanzar y soltar
 * objetos), mueve al personaje con colision contra el terreno y contra el objeto portador,
 * recorre los disparadores del grupo del fotograma y avanza la animacion. Las variables de trabajo
 * viven en el scratchpad: se vuelven a leer tras cada escritura por otro puntero.
 */
void func_80026FEC(Objeto* o)
{
    TrabajoPersonaje* t;
    void* area;
    s32 choco;
    s32 id_sec;
    s32 onda;
    s32 giro;
    s32 suelo;
    s32 fase;
    s32 factor_a;
    s32 factor_b;
    AcumuladorNodos pila_nodo;
    u16 id_golpe;
    s32 arg_giro;
    NodoDisparador* nd_azar;
    s32 azar;
    s32* pos_hijo;
    u32 f14;
    GsCOORDINATE2* coord_o;

    t = (TrabajoPersonaje*)0x1F800000;
    area = (void*)0x1F800128;

    /* Primer cuadro: sin lista de ayudantes ni marca de objeto ya inicializado se parte de la
     * secuencia 2 y, si no existe, de la 1. */
    if (o->u78.p == 0 && !(o->trabajo.flags18 & 0x4000)) {
        o->flags18 |= 0x80;
        t->sec = o->secuencias;
        t->w114 = 2;
        for (; t->sec != 0; t->sec = t->sec->sig) {
            if (t->sec->id == t->w114) {
                break;
            }
        }
        if (t->sec == 0) {
            t->sec = o->secuencias;
            t->w114 = 1;
            for (; t->sec != 0; t->sec = t->sec->sig) {
                if (t->sec->id == t->w114) {
                    break;
                }
            }
        }
        /* Sin comprobar nulo: el original asume que al menos la secuencia 1 existe. */
        t->fot = (RegistroAnim*)(o->bloque + t->sec->desplazamiento);
        o->p180 = t->sec;
        o->registro184 = t->fot;
        o->h108 = 0x800;
        o->w17C = 0;
        o->u18C.estado.h194 = 0;
        o->u18C.estado.w192 = 0;
        o->h104 = 0x80;
        if (o->flags0C & 0x200) {
            D_8006AA70[1] = 0x80;
            D_800693D0 = (u16)o->s1E;
        }
    }

    /* Reaccion a golpe: solo si el fotograma en curso acepta el golpe recibido. */
    if ((o->flags14 & 0x06000000) &&
        (((o->registro184->w0C & 0x4000) && (o->flags14 & 0x04000000)) ||
         ((o->registro184->w10 & 0x8000) && ((o->flags14 & 0x04000080) == 0x04000080)) ||
         ((o->registro184->w10 & 8) && (o->flags14 & 0x02000000)))) {
        t->w_bc = 3;
        o->s1E = o->s1E - o->w38;
        o->w38 = 0;
        if (!(o->flags08 & 0x200)) {
            if (o->s1E <= 0) {
                t->w_bc = 4;
            }
        }
        if (o->registro184 != 0) {
            t->previo = o->registro184->w06;
        } else {
            t->previo = 0;
        }
        t->sec = o->secuencias;
        t->w114 = t->w_bc;
        for (; t->sec != 0; t->sec = t->sec->sig) {
            if (t->sec->id == t->w114) {
                break;
            }
        }
        if (t->sec == 0) {
            /* Sin secuencia de herido: la de muerte (4) sigue su camino en otro bloque,
             * salvo que el objeto no pueda morir (bandera 0x200). */
            if (!(o->flags08 & 0x200) && t->w_bc == 4) {
                goto L_8002B994;
            }
            goto L_800274A8;
        }
        t->fot = (RegistroAnim*)(o->bloque + t->sec->desplazamiento);
        o->w17C = 0;
        o->registro184 = t->fot;
        o->p180 = t->sec;
        /* Se conserva el contador de animacion solo si el fotograma lo permite (bit 0x40) y es
         * el mismo que el anterior; si no, se reinicia para que la animacion arranque limpia. */
        if (!(t->fot->w08 & 0x40) || t->fot->w06 != t->previo) {
            o->trabajo.ticks = 0xFF;
            o->trabajo.i14 = 0;
            *(u16*)&o->trabajo.cuadro = 0xFFFF;
        }
        o->flags14 &= 0xFFFFFFF6;
        if (t->fot->w10 & 0x4000) {
            o->param.giro.u.y = D_80069698->param.giro.u.y + 0x800;
        }
        t->aux = o->p6C;
        if (t->aux != 0) {
            t->aux->flags14 |= 0x1000;
        }
    } else {
        /* Paso de secuencia: el fotograma siguiente sale de la tabla de pasos de la secuencia
         * en curso; 0xFFF0 o cinco pasos agotados reinician en la secuencia 1. */
        t->w_bc = *(u16*)((u8*)o->p180 + (o->w17C << 1) + 6);
        if (t->w_bc == 0xFFF0 || o->w17C >= 5) {
            if (o->registro184 != 0) {
                t->previo = o->registro184->w06;
            } else {
                t->previo = 0;
            }
            t->sec = o->secuencias;
            t->w114 = 1;
            for (; t->sec != 0; t->sec = t->sec->sig) {
                if (t->sec->id == t->w114) {
                    break;
                }
            }
            t->fot = (RegistroAnim*)(o->bloque + t->sec->desplazamiento);
            o->p180 = t->sec;
            o->registro184 = t->fot;
            if (!((t->fot->w08 & 0x40) && t->fot->w06 == t->previo)) {
                o->trabajo.i14 = 0;
            }
            o->flags14 &= 0xF9FFFFFF;
            o->w17C = 0;
        } else {
            t->fot = o->registro184;
            t->sec = o->p180;
        }
    }

L_800274A8:
    /* Efectos de ataque de las banderas del fotograma (bits 0x830000). */
    t->banderas = t->fot->w0C;
    if ((t->banderas & 0x830000) && !(o->flags14 & 0x81000)) {
        o->flags14 |= 0x40;
        if (t->banderas & 0x10000) {
            if (o->raiz_ayudantes != 0) {
                if (!(D_80069698->flags14 & 0x3000000)) {
                    if ((s16)func_80018D98(D_80069698, &o->objetivo, area) != 0) {
                        /* func_8001D75C recibe aqui el puntero al fotograma (lw 0x1F8000AC). */
                        if (func_8001D75C(o, (s32)t->fot, area) != 0) {
                            if (t->fot->w1C != 0) {
                                func_8001D0FC(o, t->fot->w1C, area);
                            }
                        }
                    }
                }
            }
        }
        if (t->banderas & 0x800000) {
            o->flags14 |= 0x20000000;
            if (!(D_80069698->flags14 & 0x3000000) || (o->flags08 & 0x40000000)) {
                if (o->flags14 & 0x8000) {
                    if (func_8001D75C(o, (s32)t->fot, area) != 0) {
                        if (t->fot->w1C != 0) {
                            func_8001D0FC(o, t->fot->w1C, area);
                        }
                    }
                }
            }
            if (t->banderas & 0x20000) {
                t->aux = func_80016ED0(o, 0x80, area);
                if (t->aux == 0) {
                    goto L_80027808;
                }
                if (o->p70 == D_80069698) {
                    if (!(D_80069698->flags14 & 0x40)) {
                        goto L_80027808;
                    }
                    if (D_80069698->raiz_ayudantes == 0) {
                        goto L_80027808;
                    }
                    t->aux->id_atacante = o->w1C;
                    o->id_atacante = t->aux->w1C;
                    t->aux->w38 = t->fot->w16;
                    goto L_80027808;
                }
                if (t->aux == D_80069698) {
                    goto L_80027808;
                }
                t->aux->flags14 |= 0x02000000;
                t->aux->id_atacante = o->w1C;
                o->id_atacante = t->aux->w1C;
                t->aux->w38 = t->fot->w16;
                o->flags14 |= 0x40000000;
            }
        } else if (t->banderas & 0x20000) {
            if (o->raiz_ayudantes == 0) {
                goto L_80027808;
            }
            t->aux = func_800171E4(o, &o->objetivo, 0x80, 0, area);
            if (t->aux == 0) {
                goto L_80027808;
            }
            if (o->p70 == D_80069698) {
                if (!(D_80069698->flags14 & 0x40)) {
                    goto L_80027808;
                }
                if (D_80069698->raiz_ayudantes == 0) {
                    goto L_80027808;
                }
                t->aux->flags14 |= 0x06000000;
                t->aux->id_atacante = o->w1C;
                o->id_atacante = t->aux->w1C;
                t->aux->w38 = t->fot->w16;
                goto L_80027808;
            }
            t->aux->flags14 |= 0x02000000;
            t->aux->id_atacante = o->w1C;
            o->id_atacante = t->aux->w1C;
            t->aux->w38 = t->fot->w16;
            o->flags14 |= 0x40000000;
        }
    } else {
        o->flags14 &= 0xDFFFFFBF;
    }

L_80027808:
    /* Golpe por volumen (bit 0x1000000 de las banderas de comportamiento). */
    if (t->fot->w10 & 0x1000000) {
        if (o->raiz_ayudantes != 0) {
            t->aux = func_800171E4(o, &o->objetivo, 0x80, 0, area);
            if (t->aux != 0) {
                t->aux->id_atacante = o->w1C;
                o->id_atacante = t->aux->w1C;
                t->aux->flags14 |= 0x40000000;
                if (t->aux == D_80069698) {
                    o->flags14 |= 0x8000;
                } else {
                    o->flags14 |= 0x40000000;
                }
            }
        }
    }

    GEO_CERO_WH(&t->r.sv.a);
    GEO_CERO_W(&t->d);

    /* Nivel de animo: el acumulador global se acota a 0..0x999 y se traduce a 2..5. */
    if (t->fot->w10 & 0x2000000) {
        if (D_800693C0 < 0) {
            D_800693C0 = 0;
        }
        if (D_800693C0 >= 0x99A) {
            D_800693C0 = 0x999;
        }
        o->trabajo.b04 = ((D_800693C0 * 3) >> 11) + 2;
        if (o->trabajo.b04 >= 6) {
            o->trabajo.b04 = 5;
        }
        D_800693C0 = D_800693C0 - 8;
    }

    if (t->banderas & 1) {
        goto L_8002A11C;
    }
    if (o->flags14 & 0x800) {
        goto L_8002A11C;
    }
    if (!(t->fot->w10 & 1)) {
        if (!(t->banderas & 0x20040060)) {
            goto L_80028370;
        }
    } else {
        /* Oscilacion vertical: la fase y la amplitud se fijan al entrar (flags14 bit 0). */
        if (!(o->flags14 & 1)) {
            o->h106 = (u16)o->param.trans.vy;
            o->h108 = 0;
            o->h10A = 0;
            o->h104 = t->fot->w1A;
            o->flags14 |= 1;
        }
        o->param.trans.vy = o->h106 + ((o->h104 * rsin(o->h108)) >> 12);
        o->h108 = ((u16)o->h108 + t->fot->w18) & 0xFFF;
    }

    if (t->banderas & 0x20) {
        /* Lanzar el objeto que lleva: se busca en un punto fijo delante del personaje y se
         * engancha a su cadena de ayudantes. */
        if (o->raiz_ayudantes == 0) {
            goto L_80027D04;
        }
        if (o->p6C != 0) {
            goto L_80027D04;
        }
        if (t->aux->p70 != 0) {
            goto L_80027D04;
        }
        /* Matriz de 0x1F800068: salida de RotMatrix, la vista MATRIX de pad58 + 0x10. */
        t->sE8.vy = -0x32;
        t->sE8.vx = 0;
        t->sE8.vz = 0xC8;
        RotMatrix(&o->param.giro.rotate, &t->m68);
        ApplyMatrix(&t->m68, &t->sE8, &t->pF0);
        t->pF0.vx = t->pF0.vx + o->param.trans.vx;
        t->pF0.vy = t->pF0.vy + o->param.trans.vy;
        t->pF0.vz = t->pF0.vz + o->param.trans.vz;
        t->aux = func_800171E4(o, &t->pF0, 0x800, 0x2000000, area);
        if (t->aux == 0) {
            goto L_80027D04;
        }
        o->flags18 |= 0x800;
        o->p6C = t->aux;
        t->aux->flags14 &= 0xFFF7EFFD;
        t->aux->flags14 |= 0x800;
        t->aux->coord.super = o->raiz_ayudantes;
        t->aux->coord.param = (GsCOORD2PARAM*)&t->aux->portado;
        t->aux->p70 = o;
        GEO_CERO_W(&t->aux->portado.trans);
        GEO_CERO_WH(&t->aux->portado.giro);
        GEO_CARGAR_W(&t->aux->param.escala);
        GEO_GUARDAR_W_T1(&t->aux->portado.escala);
        func_8001CFCC(&t->aux->coord);
        goto L_80027D04;
    }
    if (t->banderas & 0x40) {
        /* Soltar el objeto que lleva: vuelve al sistema global en la posicion del punto de
         * interaccion y con el giro del que lo soltaba. */
        if (o->raiz_ayudantes == 0) {
            goto L_80027D04;
        }
        t->hijo = o->p6C;
        if (t->hijo == 0) {
            goto L_80027D04;
        }
        t->hijo->flags14 &= 0xFFFFF7FD;
        t->hijo->flags14 |= 0x1000;
        t->hijo->coord.super = 0;
        t->hijo->coord.param = (GsCOORD2PARAM*)&t->hijo->param;
        t->hijo->w26 = o->w26;
        o->p6C = 0;
        t->hijo->p70 = 0;
        GEO_CARGAR_W(&o->objetivo);
        GEO_GUARDAR_W_T1(&t->hijo->param.trans);
        GEO_CARGAR_WH(&o->param.giro);
        GEO_GUARDAR_WH(&t->hijo->param.giro);
        func_8001CFCC(&t->hijo->coord);
        func_8001D028(o, t->hijo, area);
    }


L_80027D04:
    /* El lw de banderas (0x80027D04) cae en este rango: el rango anterior termina en la etiqueta. */
    if (t->banderas & 0x20000000) {
        o->flags14 |= 4;
        if (!(o->flags14 & 1)) {
            /* Primera vez: la onda arranca en 0xC00 con la amplitud y la velocidad del fotograma. */
            o->h10A = 0;
            o->h108 = 0xC00;
            o->h106 = t->fot->w18;
            o->h104 = t->fot->w1A;
            o->flags14 |= 1;
        }
        onda = o->h104 * rsin(o->h108);
        fase = (u16)o->h108 + (u16)o->h106;
        o->h108 = fase;
        o->param.trans.vy += onda >> 12;
        if ((s16)fase >= 0x1000) {
            o->h108 = fase - 0x1000;
        }
        /* Sin zona de colision bajo el objeto no hay referencia de altura: se deja la onda tal cual. */
        if ((t->zona = func_8001BF9C((s32*)&o->param.trans, (s16)o->w26)) != 0) {
            GEO_CARGAR_W(&o->param.trans);
            GEO_GUARDAR_W_T1(&t->p30);
            t->res.grupo = o->w26;
            func_8001C134((s32*)&t->p30, &t->res, area);
            if (t->res.flags & 8) {
                t->w114 = D_80069698->param.trans.vy - 0xC8;
                t->w118 = D_80069698->param.trans.vy - 0x190;
            } else if ((t->banderas & 0x810000) && ((s16)o->w26 == (s16)D_80069698->w26)) {
                /* Acompana al jugador: el techo del vuelo es la menor altura entre el suelo y el jugador. */
                suelo = t->p30.vy + (s16)t->res.pendiente;
                if (suelo < D_80069698->param.trans.vy) {
                    t->w114 = suelo - 0xC8;
                    t->w118 = suelo - 0x190;
                } else {
                    t->w114 = D_80069698->param.trans.vy - 0x64;
                    t->w118 = D_80069698->param.trans.vy - 0x12C;
                }
            } else {
                suelo = t->p30.vy + (s16)t->res.pendiente;
                t->w114 = suelo - 0x190;
                t->w118 = suelo - 0x258;
            }
            /* Histeresis: el sentido solo cambia al salir de la banda [w118, w114]. */
            if (t->w114 < o->param.trans.vy) {
                o->u18C.estado.h194 = 0;
            } else if (o->param.trans.vy < t->w118) {
                o->u18C.estado.h194 = 1;
            }
            if ((s16)o->u18C.estado.w192 > 0) {
                o->u18C.estado.w192 = o->u18C.estado.w192 - 1;
                if (o->u18C.estado.h194 != 0) {
                    o->param.trans.vy += 4;
                } else {
                    o->param.trans.vy -= 4;
                }
            } else {
                o->u18C.estado.w192 = BugsRand() & 0xFF;
                o->u18C.estado.h194 = BugsRand() & 1;
            }
        }
    }
    if (t->banderas & 0x40000) {
        /* Sondeo de suelo delante del objeto: vector (0, 0, 0x64) girado por el rumbo del nodo. */
        t->s50.vy = 0;
        t->s50.vx = 0;
        t->s50.vz = 0x64;
        t->r.sv.g.vz = 0;
        t->r.sv.g.vx = 0;
        t->r.sv.g.vy = (u16)o->coord.param->rotate.vy;
        RotMatrix(&t->r.sv.g, &t->m68);
        gte_SetRotMatrix(&t->m68);
        gte_ldv0(&t->s50);
        gte_rtv0();
        gte_stlvnl(&t->p40);
        t->res.grupo = o->w26;
        GEO_CARGAR_W(&t->p40);
        GEO_CARGAR_SUMAR_W(&o->param.trans);
        GEO_GUARDAR_W_T4(&t->p58);
        func_8001C134((s32*)&t->p58, &t->res, area);
        if (!(t->res.flags & 0xC)) {
            t->w_a0 = (s16)t->res.pendiente_abs;
            t->p40.vx = o->param.trans.vx;
            t->p40.vy = o->param.trans.vy;
            t->p40.vz = o->param.trans.vz;
            t->res.grupo = o->w26;
            func_8001C134((s32*)&t->p40, &t->res, area);
            if (!(t->res.flags & 0xC)) {
                /* Diferencia de pendiente entre el punto sondeado y el del objeto: inclina el rumbo. */
                o->u18C.estado.w192 += ratan2(t->w_a0 - (s16)t->res.pendiente_abs, 0x64);
                if ((s16)o->u18C.estado.w192 < -0x1000) {
                    o->u18C.estado.w192 = -0x1000;
                }
                if ((s16)o->u18C.estado.w192 > 0x1000) {
                    o->u18C.estado.w192 = 0x1000;
                }
            }
        }
        /* El avance (+0x04) se lee y escribe como u16 (lhu / sh) y su signo elige el lado del sondeo. */
        t->r.h[2] += (t->fot->h14 * (s16)o->u18C.estado.w192) >> 12;
        t->s50.vy = 0;
        t->s50.vx = 0;
        t->r.sv.g.vz = 0;
        t->r.sv.g.vx = 0;
        t->s50.vz = 0x64;
        if ((s16)t->r.h[2] < 0) {
            t->r.sv.g.vy = (u16)o->coord.param->rotate.vy - 0x400;
        } else {
            t->r.sv.g.vy = (u16)o->coord.param->rotate.vy + 0x400;
        }
        RotMatrix(&t->r.sv.g, &t->m68);
        gte_SetRotMatrix(&t->m68);
        gte_ldv0(&t->s50);
        gte_rtv0();
        gte_stlvnl(&t->p40);
        t->res.grupo = o->w26;
        GEO_CARGAR_W(&t->p40);
        GEO_CARGAR_SUMAR_W(&o->param.trans);
        GEO_GUARDAR_W_T4(&t->p58);
        BarrerTerreno(&t->p58, 0, &t->res, area);
        if (!(t->res.flags & 0xC)) {
            t->w_a0 = (s16)t->res.pendiente_abs;
            t->p40.vz = -t->p40.vz;
            t->p40.vx = -t->p40.vx;
            t->res.grupo = o->w26;
            GEO_CARGAR_W(&t->p40);
            GEO_CARGAR_SUMAR_W(&o->param.trans);
        GEO_GUARDAR_W_T4(&t->p58);
            BarrerTerreno(&t->p58, 0, &t->res, area);
            if (!(t->res.flags & 0xC)) {
                t->w_a0 = t->w_a0 - (s16)t->res.pendiente_abs;
                if (t->w_a0 != 0) {
                    o->param.giro.u.y += ratan2(t->w_a0 >> 1, 0xC8);
                }
            }
        }
    }
L_80028370:
    /* Entrada desde el rango previo con t->banderas ya cargado. */
    if ((t->banderas & 0x02000C02) == 0 && (s32)t->fot->w10 >= 0) {
        goto L_80028AD8;
    }
    if ((s32)t->fot->w10 >= 0) {
        /* La rama de mando por teclas empieza probando banderas & 2 (queda en v0 en la ranura del salto). */
        goto L_800289B8;
    }
    if (!(t->banderas & 0x100000)) {
        goto L_80028410;
    }
    if (t->fot->w10 & 0x400000) {
        factor_a = D_80069694;
        factor_b = (s8)D_8006AA70[t->fot->h14] * 2;
    } else {
        factor_a = t->fot->h14;
        factor_b = D_80069694;
    }
    t->r.h[2] += factor_a * factor_b;

L_80028410:
    t->w118 = ratan2(D_8006D928.x - D_8006D928.vpx, D_8006D928.z - D_8006D928.vpz);
    if ((s16)D_80010012 == 0 && D_80010014 == 0) {
        goto L_80028928;
    }
    t->w114 = SquareRoot0((s16)D_80010012 * (s16)D_80010012 + (s16)D_80010014 * (s16)D_80010014);
    t->w114 = (t->w114 - D_8006952C) * (0x80 / D_8006952C);
    if (t->w114 > 0x80) {
        t->w114 = 0x80;
    }
    if (t->fot->w10 & 0x400000) {
        t->w_a0 = D_80069694 * (*(s8*)&D_8006AA70[t->fot->h14] << 1);
    } else {
        t->w_a0 = t->fot->h14 * D_80069694;
    }
    t->w114 = (t->w_a0 * t->w114) >> 7;
    if (t->w114 == 0) {
        t->w114 = 1;
    }
    if (o->coord.super == 0) {
        goto L_80028740;
    }
    /* seguimiento con ayudante: se rota (0,0,0x3E8) por la cadena de nodos para obtener el rumbo */
    t->sE8.vz = 0x3E8;
    t->sE8.vx = 0;
    t->sE8.vy = 0;
    t->cursor = &o->coord;
    while (t->cursor != 0) {
        ApplyMatrixSV(&t->cursor->coord, &t->sE8, &t->sE8);
        t->cursor = t->cursor->super;
    }
    t->w_a0 = ratan2(t->sE8.vx, t->sE8.vz);
    o->param.giro.u.y = t->w_a0;
    t->w_a0 -= (t->w118 + ratan2((s16)D_80010012, (s16)D_80010014)) % 0x1000;
    if (t->w_a0 > 0x800) {
        t->w_a0 -= 0x1000;
    }
    if (t->w_a0 < -0x800) {
        t->w_a0 += 0x1000;
    }
    if (t->banderas & 0x100000) {
        if (t->w_a0 > 0x1E) {
            t->w_a0 = 0x1E;
        } else if (t->w_a0 < -0x1E) {
            t->w_a0 = -0x1E;
        }
        if (t->w114 > 0x200) {
            t->w114 = 0x200;
        } else if (t->w114 < -0x200) {
            t->w114 = -0x200;
        }
        o->u78.ayudas->flags8 |= 0x400;
        GIRO_Y(o->u78.ayudas->pcoord->param) -= (o->u78.ayudas->pcoord->param->rotate.vy - t->w114) >> 5;
        func_8001CFCC(o->u78.ayudas->pcoord);
    } else {
        t->r.h[2] += (u16)t->w114;
        t->w_a0 = t->w_a0 >> 2;
    }
    GIRO_Y(o->coord.param) -= (u16)t->w_a0;
    goto L_80028A08;

L_80028740:
    /* seguimiento sin ayudante: el giro del propio objeto converge al rumbo del mando */
    t->w_a0 = ratan2((s16)D_80010012, (s16)D_80010014);
    t->w_a0 = (t->w_a0 + t->w118) % 0x1000;
    if (t->w_a0 > 0x800) {
        t->w_a0 -= 0x1000;
    }
    if (t->w_a0 < -0x800) {
        t->w_a0 += 0x1000;
    }
    if (o->param.giro.rotate.vy > 0x800) {
        o->param.giro.u.y -= 0x1000;
    }
    if (o->param.giro.rotate.vy < -0x800) {
        o->param.giro.u.y += 0x1000;
    }
    t->w_a0 -= o->param.giro.rotate.vy;
    if (t->w_a0 > 0x800) {
        t->w_a0 -= 0x1000;
    }
    if (t->w_a0 < -0x800) {
        t->w_a0 += 0x1000;
    }
    if (t->banderas & 0x100000) {
        t->w114 = t->w_a0;
        if (t->w_a0 > 0x1E) {
            t->w_a0 = 0x1E;
        } else if (t->w_a0 < -0x1E) {
            t->w_a0 = -0x1E;
        }
        if (t->w114 > 0x200) {
            t->w114 = 0x200;
        } else if (t->w114 < -0x200) {
            t->w114 = -0x200;
        }
        o->u78.ayudas->flags8 |= 0x400;
        GIRO_Y(o->u78.ayudas->pcoord->param) -= (o->u78.ayudas->pcoord->param->rotate.vy - t->w114) >> 5;
        func_8001CFCC(o->u78.ayudas->pcoord);
    } else {
        t->w_a0 = t->w_a0 >> 2;
        t->r.h[2] += (u16)t->w114;
    }
    o->param.giro.u.y += (u16)t->w_a0;
    goto L_80028A08;

L_80028928:
    /* mando en reposo: el ayudante recupera su giro hacia cero */
    if (!(t->banderas & 0x100000)) {
        goto L_80028A08;
    }
    giro = (s16)GIRO_Y(o->u78.ayudas->pcoord->param);
    t->w114 = giro;
    if ((giro >> 3) != 0) {
        t->w114 = giro >> 3;
    }
    GIRO_Y(o->u78.ayudas->pcoord->param) -= (u16)t->w114;
    func_8001CFCC(o->u78.ayudas->pcoord);
    goto L_80028A08;

L_800289B8:
    if ((t->banderas & 2) == 0) {
        goto L_80028A08;
    }
    if (t->fot->w10 & 0x400000) {
        t->r.h[2] += (s8)D_8006AA70[t->fot->h14] << 1;
    } else {
        t->r.h[2] += (u16)t->fot->h14;
    }

L_80028A08:
    if (t->banderas & 0x400) {
        t->r.h[1] -= t->fot->w1A;
    }
    if (t->banderas & 0x800) {
        t->r.h[1] += t->fot->w1A;
    }
    if (t->banderas & 0x2000000) {
        /* vaiven ocioso: un contador aleatorio fija durante cuantos cuadros gira hacia un lado */
        if (o->u18C.estado.w18E != 0) {
            o->u18C.estado.w18E--;
            if (o->u18C.estado.h190 != 0) {
                o->param.giro.u.y += 0xA;
            } else {
                o->param.giro.u.y -= 0xA;
            }
        } else {
            o->u18C.estado.w18E = BugsRand() & 0x1FF;
            o->u18C.estado.h190 = BugsRand() & 1;
        }
    }

L_80028AD8:
    if (!(t->fot->w10 & 0x10010)) {
        goto L_80028B94;
    }
    if (t->fot->w10 & 0x10000) {
        if (t->fot->w10 & 0x400000) {
            t->r.h[0] += (s8)D_8006AA70[t->fot->h14];
        } else {
            t->r.h[0] += (u16)t->fot->h14;
        }
    }
    if (t->fot->w10 & 0x10) {
        /* el objeto mira hacia la camara */
        t->p30.vx = D_8006D928.vpx - o->param.trans.vx;
        t->p30.vz = D_8006D928.vpz - o->param.trans.vz;
        o->param.giro.u.y = ratan2(t->p30.vx, t->p30.vz);
    }

L_80028B94:
    if (!(t->banderas & 0x10209000)) {
        goto L_80028FD0;
    }
    if (t->banderas & 0x200000) {
        /* busqueda por identificador en la lista de objetos de escena, saltando los marcados con 0x100 */
        t->aux = D_80069518;
        if (t->aux == 0) {
            goto L_80028FD0;
        }
busca_objetivo:
        if (t->aux->w1C != (s16)t->fot->w16 || (t->aux->flags14 & 0x100)) {
            t->aux = t->aux->siguiente;
            if (t->aux != 0) {
                goto busca_objetivo;
            }
            goto L_80028FD0;
        }
    } else {
        t->aux = D_80069698;
    }
    if (t->aux == 0) {
        goto L_80028FD0;
    }
    if (t->banderas & 0x10000000) {
        /* el vector se mide desde el objetivo hacia el objeto; la altura (+0x34) no se toca */
        t->p30.vx = o->param.trans.vx - t->aux->param.trans.vx;
        t->p30.vz = o->param.trans.vz - t->aux->param.trans.vz;
    } else {
        t->p30.vx = t->aux->param.trans.vx - o->param.trans.vx;
        t->p30.vy = t->aux->param.trans.vy + 0x32 + t->aux->max.vy - o->param.trans.vy;
        t->p30.vz = t->aux->param.trans.vz - o->param.trans.vz;
    }
    if ((t->banderas & 0x30000000) == 0x20000000) {
        /* distancia aproximada al objetivo; si es menor que 0x1000 la altura se corrige en proporcion */
        GEO_DISTANCIA_APROX_A(&t->p30, &t->w114);
        if (t->w114 < 0x1000) {
            t->r.h[1] += ((0x1000 - t->w114) * t->p30.vy) >> 16;
        }
    }
    t->w114 = ratan2(t->p30.vx, t->p30.vz);
    if (t->banderas & 0x1000) {
        /* giro directo hacia el objetivo, relativo al ayudante si lo hay */
        if (o->coord.super != 0) {
            o->coord.param->rotate.vy = t->w114 - o->coord.super->param->rotate.vy;
        } else {
            o->coord.param->rotate.vy = t->w114;
        }
        goto L_80028FD0;
    }
    if (t->w114 < 0) {
        t->w114 += 0x1000;
    }
    if (o->coord.super != 0) {
        t->w118 = (o->coord.param->rotate.vy + o->coord.super->param->rotate.vy) % 0x1000;
    } else {
        t->w118 = (s16)(o->coord.param->rotate.vy % 0x1000);
    }
    if (t->w118 < 0) {
        t->w118 += 0x1000;
    }
    t->w114 = t->w114 - t->w118;
    if (t->w114 < 0) {
        t->w114 += 0x1000;
    }
    if (t->w114 > 0x800) {
        t->w114 -= 0x1000;
    }
    if (t->fot->w10 & 0x400) {
        /* giro por pasos fijos de +-0x196 mientras la diferencia los supere */
        if (t->w114 < 0) {
            if (t->w114 < -(s16)o->u18C.estado.w196) {
                GIRO_Y(o->coord.param) -= (u16)o->u18C.estado.w196;
                goto L_80028FD0;
            }
        }
        if ((s16)o->u18C.estado.w196 < t->w114) {
            GIRO_Y(o->coord.param) += (u16)o->u18C.estado.w196;
        }
        goto L_80028FD0;
    }
    t->w_a0 = (s16)o->u18C.estado.w196;
    if (t->w_a0 == 0) {
        t->w_a0 = 4;
    }
    if (t->fot->w10 & 0x20) {
        GIRO_Y(o->coord.param) += t->w114 >> 1;
        goto L_80028FD0;
    }
    t->w_a0 = t->w114 >> t->w_a0;
    if (t->w_a0 != 0) {
        GIRO_Y(o->coord.param) += (u16)t->w_a0;
    } else {
        GIRO_Y(o->coord.param) += (u16)t->w114;
    }

L_80028FD0:
    RotMatrix(&o->param.giro.rotate, &t->m68);
    gte_SetRotMatrix(&t->m68);
    gte_ldv0(&t->r.sv.a);
    gte_rtv0();
    gte_stlvnl(&t->d);
    choco = 0;
    t->r.sv.b.vy = 0;
    t->r.sv.b.vx = 0;
    if (t->banderas & 0x400000) {
        goto L_80029A74;
    }
    /* copia de 12 bytes del desplazamiento rotado a +0x08 (invade c.vx y c.vy) */
    GEO_CARGAR_W(&t->d);
    GEO_GUARDAR_W_T1(&t->r.sv.b);


    /* Busca el objeto portador bajo el punto desplazado (t->r.sv.b); sin portador no hay enganche */
    t->aux = func_80017478(o, &t->r.sv.b, area, 0x20108);
    if (t->aux == 0) {
        goto L_80029A74;
    }
    t->aux->id_atacante = o->w1C;
    o->id_atacante = t->aux->w1C;

    /*
     * Enganche del objeto a un portador: solo si el fotograma lo pide (bit 0x200000), el grupo del
     * fotograma coincide con la plantilla del portador (w16 se compara con signo) y el portador no
     * esta marcado como no portable (bit 8).
     */
    if ((t->fot->w10 & 0x200000) &&
        (s16)t->fot->w16 == t->aux->w1C &&
        !(t->aux->flags08 & 0x8)) {
        o->portado.escala.vz = 0x1000;
        o->portado.escala.vy = 0x1000;
        o->portado.escala.vx = 0x1000;
        o->portado.trans.vz = 0;
        o->portado.trans.vy = 0;
        o->portado.trans.vx = 0;
        if (o->p70 != 0 && o->p70->p6C == o) {
            /* el portador actual ya apuntaba a este objeto: se limpia su enlace y se conserva el nodo */
            o->p70->p6C = 0;
            goto L_800291A8;
        }
        if (t->aux->raiz_ayudantes != 0) {
            /* la escala del portador se copia a la propia: el nodo cuelga de la raiz de ayudantes */
            GEO_CARGAR_W(t->aux->raiz_ayudantes->param);
            GEO_GUARDAR_W_T1(&o->portado.escala);
            o->coord.super = t->aux->raiz_ayudantes;
        } else {
            o->coord.super = &t->aux->coord;
        }
        o->w26 = t->aux->w26;
        o->p70 = t->aux;
L_800291A8:
        o->coord.param = (GsCOORD2PARAM*)&o->portado;
        t->aux->p6C = o;
        o->w26 = t->aux->w26;
        func_8001CFCC(&o->coord);
        o->flags14 &= 0xFFF7E5E4;
        /* la traslacion acumulada del nodo pasa a ser la posicion propia (area de pila de func_8001CE64) */
        pila_nodo.nodo = &o->coord;
        func_8001CE64(&pila_nodo);
        GEO_CARGAR_W(&pila_nodo.acc);
        GEO_GUARDAR_W_T1(&o->param.trans);
        o->flags14 |= 0x40000000;
        t->aux->flags14 |= 0x40000000;
        choco = 1;
    }

    /* Un portador marcado con 0x20000 en el fotograma recibe el dano del golpe (bit 0x2000000 evita repetirlo) */
    if ((t->banderas & 0x20000) &&
        !(t->aux->flags14 & 0x2000000) &&
        D_80069698 != t->aux &&
        !(t->aux->registro184 != 0 && (t->aux->registro184->w0C & 0x40))) {
        if (((o->flags08 & 0x10000000) && (o->flags14 & 0x201)) ||
            (t->fot->w0C & 0x200000)) {
            t->aux->w38 = 1;
        } else {
            t->aux->w38 = t->fot->w16;
        }
        t->aux->flags14 |= 0x2000000;
        o->flags14 |= 0x8000000;
    }

    /* El jugador portador (bit 0x800000) aplica el golpe de la plantilla que lleva el fotograma */
    if ((t->banderas & 0x800000) &&
        t->aux == D_80069698 &&
        !(t->aux->flags14 & 0x2000000)) {
        if (func_8001D75C(o, (s32)t->fot, area) != 0) {
            /* +0x1C del fotograma: lhu sin campo con nombre en RegistroAnim */
            id_golpe = t->fot->w1C;
            if (id_golpe != 0) {
                func_8001D0FC(o, id_golpe, area);
            }
        }
    }

    /*
     * Subir a la plataforma: el portador es solido (bit 8), el objeto ya no esta enganchado, no esta
     * en el aire (bits 0x10 y 1/8 de flags14) y la sonda no queda mas de 99 unidades bajo el portador.
     */
    if ((t->aux->flags08 & 0x8) &&
        ((o->flags08 & 0x40000) || (t->fot->w10 & 0x20000000)) &&
        o->p70 == 0 &&
        !(o->flags14 & 0x10) &&
        (!(o->flags14 & 0x1) || (o->flags14 & 0x8)) &&
        (s16)t->r.sv.b.vy >= -0x63 &&
        t->aux->u78.p != 0 &&
        o->u78.p != 0) {
        o->p70 = t->aux;
        if (t->aux->flags0C & 0x1000000) {
            t->r.sv.b.vz = 0;
            t->r.sv.b.vx = 0;
        } else {
            t->r.sv.b.vx = (u16)o->param.trans.vx - (u16)t->aux->param.trans.vx;
            t->r.sv.b.vz = (u16)o->param.trans.vz - (u16)o->p70->param.trans.vz;
        }
        t->r.sv.b.vy = o->p70->max.vy + 4;
        /*
         * choco guarda 0x1000 (unidad de punto fijo) mientras dura el calculo del giro relativo; al
         * ser distinto de cero marca tambien que hubo colision con el portador.
         */
        choco = 0x1000;
        t->r.sv.g.vx = choco - o->p70->param.giro.u.x;
        t->r.sv.g.vy = choco - o->p70->param.giro.u.y;
        t->r.sv.g.vz = choco - o->p70->param.giro.u.z;
        GEO_IDENTIDAD(&t->m68);
        RotMatrixX(t->r.sv.g.vx, &t->m68);
        RotMatrixY(t->r.sv.g.vy, &t->m68);
        RotMatrixZ(t->r.sv.g.vz, &t->m68);
        gte_SetRotMatrix(&t->m68);
        gte_ldv0(&t->r.sv.b);
        gte_rtv0();
        gte_stlvnl(&o->portado.trans);
        o->param.trans.vy = t->aux->max.vy + t->aux->param.trans.vy;
        t->d.vy = 0;
        o->coord.param = (GsCOORD2PARAM*)&o->portado;
        o->portado.escala.vz = choco;
        o->portado.escala.vy = choco;
        o->portado.escala.vx = choco;
        o->coord.super = &o->p70->coord;
        o->portado.giro.u.y = o->param.giro.u.y - o->p70->param.giro.u.y;
        if ((s32)t->aux->flags08 < 0 || (t->aux->flags0C & 0x400000)) {
            if (t->aux->flags0C & 0x400000) {
                o->coord.super = t->aux->raiz_ayudantes;
            } else {
                /* +0x10 del bloque de modelo: nodo de coordenadas sin campo con nombre */
                o->coord.super = *(GsCOORDINATE2**)((u8*)t->aux->u78.p + 0x10);
            }
            /* la traslacion relativa se mide desde el parametro del nodo superior */
            o->portado.trans.vx -= o->coord.super->param->trans.vx;
            o->portado.trans.vy -= o->coord.super->param->trans.vy;
            o->portado.trans.vz -= o->coord.super->param->trans.vz;
        }
        func_8001CFCC(&o->coord);
        o->h10A = 0;
        o->flags14 |= 0x40000000;
        t->aux->flags14 |= 0x40000000;
        choco = 1;
        t->aux->id_atacante = o->w1C;
        o->flags14 = (o->flags14 | 0x14) & 0xFFFFFDF6;
        o->id_atacante = t->aux->w1C;
    }

    /*
     * Portador sin el bit 0x2000000 y que no es el portador actual del objeto. Con el bit 0x40000
     * del fotograma el portador se orienta hacia el objeto con una desviacion aleatoria y el
     * desplazamiento sale de rotar su vector; en otro caso se consulta el suelo bajo el objeto.
     */
    if ((t->aux->flags08 & 0x2000000) || o->p70 == t->aux) {
        goto L_80029A4C;
    }
    if (t->banderas & 0x40000) {
        t->r.sv.b.vx = (u16)o->param.trans.vx - (u16)t->aux->param.trans.vx;
        t->r.sv.b.vz = (u16)o->param.trans.vz - (u16)t->aux->param.trans.vz;
        t->w114 = ratan2(t->r.sv.b.vx, t->r.sv.b.vz);
        if (t->aux->p70 != 0) {
            t->aux->portado.giro.u.y = (u16)t->w114 - (t->aux->p70->param.giro.u.y - 0x800);
        }
        t->aux->param.giro.u.y = (u16)t->w114 + 0x800;
        t->aux->u18C.estado.w192 = 0x1000;
        t->w118 = BugsRand();
        if (t->w118 >= 0) {
            t->w114 = t->w114 + (t->w118 & 0x1FF);
        } else {
            t->w114 = t->w114 - (t->w118 & 0x1FF);
        }
        if (o->p70 != 0) {
            o->portado.giro.u.y = (u16)t->w114 - o->p70->param.giro.u.y;
        }
        o->u18C.estado.w192 = 0x1000;
        o->param.giro.u.y = (u16)t->w114;
        /* +0x14 del fotograma: lhu sin campo con nombre en RegistroAnim; es la distancia del empuje */
        t->r.sv.a.vz = (u16)t->fot->h14;
        RotMatrix(&o->param.giro.rotate, &t->m68);
        gte_SetRotMatrix(&t->m68);
        gte_ldv0(&t->r.sv.a);
        gte_rtv0();
        gte_stlvnl(&t->d);
        goto L_80029A4C;
    }
    if (t->aux == D_80069698) {
        goto L_80029A74;
    }
    t->vC0.vx = (s16)t->r.sv.b.vx + o->param.trans.vx;
    t->vC0.vy = o->param.trans.vy;
    t->vC0.vz = (s16)t->r.sv.b.vz + o->param.trans.vz;
    t->res.grupo = o->w26;
    func_8001C134((s32*)&t->vC0, &t->res, area);
    o->flags14 |= 0x40000000;
    t->aux->flags14 |= 0x40000000;
    /* con 0x80000 en el fotograma solo cuenta la rampa (bit 4); sin el, rampa y salto (bits 4 y 8) */
    if ((t->fot->w0C & 0x80000) ? ((s16)t->res.flags & 0x4) : ((s16)t->res.flags & 0xC)) {
        goto L_80029A74;
    }
    if (o->flags08 & 0x2000000) {
        goto L_80029A74;
    }
    if (!(t->aux->flags08 & 0x20100)) {
        goto L_80029A74;
    }
    if (o->p70 == 0 &&
        (t->aux->flags08 & 0x8) &&
        (s16)t->r.sv.b.vy >= -0x63 &&
        ((o->flags08 & 0x40000) || (t->fot->w10 & 0x20000000))) {
        /* sobre un portador solido el desplazamiento vertical acumula la diferencia de altura */
        t->d.vy = t->d.vy + (s16)t->r.sv.b.vy;
    } else {
        t->d.vx = (s16)t->r.sv.b.vx;
        t->d.vz = (s16)t->r.sv.b.vz;
    }
    goto L_80029A74;
L_80029A4C:
    o->flags14 |= 0x40000000;
    t->aux->flags14 |= 0x40000000;
L_80029A74:
    /* Sin colision previa, con el bit 0x10 del fotograma y sin salto en curso, el barrido de terreno corre */
    if (!(t->banderas & 0x10) || choco != 0) {
        goto L_80029F28;
    }
    if ((t->fot->w10 & 0x800) ? (o->flags14 & 0x9) : (o->flags14 & 0x209)) {
        goto L_80029EF8;
    }
    if (!(o->flags14 & 0x10)) {
        goto L_80029B6C;
    }
    /* enganchado a un portador: el punto de barrido es la posicion del portador y el desplazamiento es el desfase relativo */
    t->p30.vy = 0;
    t->p30.vx = o->param.trans.vx - o->p70->param.trans.vx;
    t->p30.vz = o->param.trans.vz - o->p70->param.trans.vz;
    t->pF0.vx = o->p70->param.trans.vx;

    /* Continuacion del barrido del portado: lo que falta de la llamada a BarrerTerreno (a0 = &t->pF0, a1 = &t->p30). */
    t->pF0.vz = o->p70->param.trans.vz;
    t->pF0.vy = o->param.trans.vy;
    t->res.grupo = o->w26;
    BarrerTerreno(&t->pF0, &t->p30, &t->res, area);
    o->param.trans.vx = o->p70->param.trans.vx + t->p30.vx;
    o->param.trans.vz = o->p70->param.trans.vz + t->p30.vz;

L_80029B6C:
    /* Con el fotograma pidiendo cuenta de andadura y el objeto en el suelo o portado, se cuenta el cuadro y
       se suelta al portador si la andadura supera el umbral. */
    if (!(t->banderas & 0x08000000)) goto L_80029C44;
    if (!(o->flags14 & 0x12)) goto L_80029C44;
    o->u18C.estado.h194 = o->u18C.estado.h194 + 1;
    t->w118 = (s16)t->fot->w18 * (s16)o->u18C.estado.h194;
    if (t->w118 < 0x400) {
        /* Aun dentro del umbral: se suelta al portador y se empuja con el giro actual. */
        if (o->p70 != 0) {
            if (o->p70->p6C == o) {
                o->p70->p6C = 0;
            }
        }
        o->coord.param = PARAMETROS_SDK(o);
        o->coord.super = 0;
        o->p70 = 0;
        o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x2;
        func_8001CFCC(&o->coord);
        arg_giro = t->w118;
        goto L_80029EEC;
    }
    o->flags14 = (o->flags14 | 0x800000) & 0xFFF7EFFF;
    goto L_80029EF8;

L_80029C44:
    /* Quien es el portador candidato: el jugador cuando el objeto ya esta marcado o el fotograma lo pide;
       si no, el primer solido de la lista con la plantilla del fotograma. */
    t->w114 = 0;
    if ((o->flags08 & 0x08000000) || (t->fot->w10 & 0x100)) {
        t->w114 = 1;
    }
    if (t->w114 != 0) goto L_80029CB0;
    if (o->flags08 & 0x10000000) goto L_80029CB0;
    if ((t->fot->w10 & 0x100000) == 0) goto L_80029E9C;

L_80029CB0:
    if (t->w114 != 0) {
        t->aux = D_80069698;
        goto L_80029D24;
    }
    t->aux = D_80069630;
    if (D_80069630 == 0) goto L_80029EF8;
    do {
        /* Busqueda en linea por plantilla: se salta el solido si no coincide o si esta marcado como inactivo. */
        if (t->aux->w1C == (s16)t->fot->w16) {
            if (!(t->aux->flags14 & 0x100)) goto L_80029D24;
        }
        t->aux = t->aux->sig10;
    } while (t->aux != 0);

L_80029D24:
    if (t->aux == 0) goto L_80029EF8;
    t->r.sv.c.vx = (u16)t->aux->param.trans.vx - (u16)o->param.trans.vx;
    t->r.sv.c.vz = (u16)t->aux->param.trans.vz - (u16)o->param.trans.vz;
    t->w_a4 = SquareRoot0(t->r.sv.c.vx * t->r.sv.c.vx + t->r.sv.c.vz * t->r.sv.c.vz);
    /* La altura relativa (en unidades de 70) se descuenta de la distancia horizontal. */
    t->w_a4 = t->w_a4 - ((t->aux->param.trans.vy + (t->aux->max.vy >> 1) - o->param.trans.vy) / 70) * t->fot->h14;
    if (o->p70 != 0) {
        if (o->p70->p6C == o) {
            o->p70->p6C = 0;
        }
    }
    o->coord.param = PARAMETROS_SDK(o);
    o->coord.super = 0;
    o->p70 = 0;
    o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x2;
    func_8001CFCC(&o->coord);
    if (t->w_a4 > 0) {
        t->w_a4 = t->w_a4 / t->fot->h14;
        if (t->w_a4 != 0) {
            t->w_a4 = 0x800 / t->w_a4;
            arg_giro = t->w_a4;
            goto L_80029EEC;
        }
    }
    o->flags14 |= 0x200;
    goto L_80029EF8;

L_80029E9C:
    o->coord.super = 0;
    o->coord.param = PARAMETROS_SDK(o);
    if (o->p70 != 0) {
        if (o->p70->p6C == o) {
            o->p70->p6C = 0;
        }
    }
    o->p70 = 0;
    o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x2;
    func_8001CFCC(&o->coord);
    arg_giro = (s16)t->fot->w18;

L_80029EEC:
    func_80020210(o, arg_giro, (s16)t->fot->w1A);

L_80029EF8:
    if (t->banderas & 0x10) {
        if (o->flags14 & 0x1) {
            func_80020240(o);
        }
    }

L_80029F28:
    /* Sin desplazamiento pedido no hay barrido de colision. */
    if (t->d.vz == 0) {
        if ((t->d.vx | t->d.vy) == 0) goto L_8002A034;
    }
    if (t->banderas >= 0) {
        if (!(t->fot->w10 & 0x20002) && o->p70 == 0) {
            func_8001DA14(o, &t->d, t->banderas, t->fot->w10, area);
            goto L_8002A034;
        }
    }
    if (!(t->banderas & 0x40000000)) goto L_8002A034;
    GEO_CARGAR_W(&o->param.trans);
    GEO_GUARDAR_W_T1(&t->p30);
    GEO_CARGAR_W(&t->d);
    GEO_SUMAR_W(&t->p30);
    t->res.grupo = o->w26;
    func_8001C134((s32*)&t->p30, &t->res, (TrabajoBaldosa*)area);
    o->w26 = t->res.grupo;

L_8002A034:
    if (t->banderas < 0) {
        if (!(t->fot->w10 & 0x4)) {
            if (o->coord.super == 0) goto L_8002A448;
        }
    }
    t->w114 = t->d.vx + t->d.vz;
    t->w118 = t->d.vy;
    func_8001CBB8(o, (Movimiento*)&t->d, &t->res, area);
    if ((t->fot->w10 & 0x4) || t->banderas < 0) {
        t->d.vy = 0;
    }
    t->d.vy = t->d.vy + t->w118;
    if (t->res.flags & 0x8) {
        o->flags18 |= 0x20;
    }
    if (t->w114 != t->d.vx + t->d.vz) {
        o->flags14 |= 0x100000;
    }

L_8002A11C:
    if (o->coord.super == 0) goto L_8002A448;
    if (o->p70 != 0) {
        if (o->p70->flags14 & 0x100) {
            /* El portador esta inactivo: el objeto no puede seguir encima de el, salvo que ya este en la fase de suelta (0x400 de flags18), que resuelve otro bloque. */
            if (o->flags18 & 0x400) goto L_8002B994;
            o->coord.param = PARAMETROS_SDK(o);
            o->coord.super = 0;
            o->p70 = 0;
            o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x202;
            func_8001CFCC(&o->coord);
        }
        if (o->p70 != 0) {
            o->w26 = o->p70->w26;
            o->p70->flags18 |= 0x800;
        }
    }

    if (o->flags14 & 0x10) {
        /* Altura del apoyo sobre el portador: si el portador cuelga de otro nodo se resta la altura de ese nodo. */
        if ((s32)o->p70->flags08 < 0 || (o->p70->flags0C & 0x400000)) {
            o->portado.trans.vy = o->p70->max.vy - o->coord.super->param->trans.vy + 4;
        } else {
            o->portado.trans.vy = o->p70->max.vy + 4;
        }
        o->flags14 |= 0x40000000;
        o->p70->flags14 |= 0x40000000;
        if (o->p70->id_atacante == 0) {
            o->p70->id_atacante = o->w1C;
        }
        if (o->id_atacante == 0) {
            o->id_atacante = o->p70->w1C;
        }
    }

    /* Se acumula la cadena de nodos del portador para obtener el desfase del portado en el espacio del padre. */
    t->s50.vy = 0;
    t->s50.vx = 0;
    t->s50.vz = 0x1000;
    GEO_CERO_WH(&t->sE8);
    t->cursor = &o->coord;
    if (t->cursor != 0) {
        do {
            gte_SetRotMatrix(&t->cursor->coord);
            gte_ldv0(&t->sE8);
            gte_rtv0();
            gte_stlvnl(&t->pF0);
            gte_SetRotMatrix(&t->cursor->coord);
            gte_ldv0(&t->s50);
            gte_rtv0();
            gte_stsv(&t->s50);
            GEO_CARGAR_W(&t->cursor->coord.t[0]);
            GEO_SUMAR_W(&t->pF0);
            GEO_CARGAR_W(&t->pF0);
            GEO_GUARDAR_H_T1(&t->sE8);
            t->cursor = t->cursor->super;
        } while (t->cursor != 0);
    }
    o->param.giro.u.y = ratan2(t->s50.vx, t->s50.vz);
    o->param.giro.u.z = 0;
    o->param.giro.u.x = 0;
    GEO_CARGAR_H(&t->sE8);
    GEO_GUARDAR_W_T1(&o->param.trans);

L_8002A448:
    if (o->flags14 & 0x10) {
        /* Con portador: se decide entre soltarlo, seguirlo por el barrido o recoger su movimiento. */
        if ((o->p70->flags14 & 0x100) || !(o->p70->flags08 & 0x8)) {
            o->coord.param = PARAMETROS_SDK(o);
            o->coord.super = 0;
            o->p70 = 0;
            o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x2;
            func_8001CFCC(&o->coord);
            o->flags14 |= 0x200;
        } else if (o->p70->flags14 & 0x1000) {
            o->flags14 = (o->flags14 & 0xFFFFF7E9) | 0x1000;
            t->vC0.vx = o->p70->param.trans.vx;
            t->vC0.vy = o->param.trans.vy;
            t->vC0.vz = o->p70->param.trans.vz;
            t->pF0.vx = o->param.trans.vx - o->p70->param.trans.vx;
            t->pF0.vy = 0;
            t->pF0.vz = o->param.trans.vz - o->p70->param.trans.vz;
            t->res.grupo = o->w26;
            BarrerTerreno(&t->vC0, &t->pF0, &t->res, area);
            o->param.trans.vx = o->p70->param.trans.vx + t->pF0.vx;
            o->coord.param = PARAMETROS_SDK(o);
            o->coord.super = 0;
            o->param.trans.vz = o->p70->param.trans.vz + t->pF0.vz;
            o->param.giro.u.x = o->p70->param.giro.u.x;
            o->param.giro.u.y = o->p70->param.giro.u.y;
            /* El giro en Z se lee del portador antes de soltarlo y se escribe despues. */
            arg_giro = o->p70->param.giro.u.z;
            o->p70 = 0;
            o->param.giro.u.z = arg_giro;
            goto L_8002A6A0;
        } else {
            if (func_80018664(o, o->p70, area) != 0) goto L_8002A6A8;
            t->p30.vy = 0;
            t->p30.vx = o->param.trans.vx - o->p70->param.trans.vx;
            t->p30.vz = o->param.trans.vz - o->p70->param.trans.vz;
            GEO_CARGAR_W(&o->p70->param.trans);
            GEO_GUARDAR_W_T1(&t->pF0);
            t->pF0.vy = o->param.trans.vy;
            t->res.grupo = o->w26;
            BarrerTerreno(&t->pF0, &t->p30, &t->res, area);
            o->param.trans.vx = o->p70->param.trans.vx + t->p30.vx;
            arg_giro = o->p70->param.trans.vz;
            o->coord.param = PARAMETROS_SDK(o);
            o->param.giro.u.z = 0;
            o->coord.super = 0;
            o->p70 = 0;
            o->flags14 = (o->flags14 & 0xFFFFFFEB) | 0x200;
            o->param.trans.vz = arg_giro + t->p30.vz;
L_8002A6A0:
            func_8001CFCC(&o->coord);
        }
    }

L_8002A6A8:
    /* Sin portador y con el fotograma pidiendo movimiento propio, no hay nodo padre que componer. */
    if ((t->fot->w0C & 0x1) && !(t->fot->w10 & 0x4) && o->coord.super == 0) goto L_8002A804;
    if (o->coord.super != 0) {
        t->sE8.vz = 0;
        t->sE8.vx = 0;
        t->sE8.vy = -(u16)o->p70->param.giro.u.y;
        RotMatrix(&t->sE8, &t->m68);
        ApplyMatrixLV(&t->m68, &t->d, &t->d);
        GEO_CARGAR_W(&t->d);
        GEO_SUMAR_W(&o->portado.trans);
        func_8001CFCC(&o->coord);
        pila_nodo.nodo = &o->coord;
        func_8001CE64(&pila_nodo);
        GEO_CARGAR_W(&pila_nodo.acc);
        GEO_GUARDAR_W_T1(&o->param.trans);
        func_8001CFCC(&o->coord);
    } else {
        GEO_CARGAR_W(&t->d);
        GEO_SUMAR_W(&o->param.trans);
        func_8001CF50(o);
    }

L_8002A804:
    if (o->flags0C & 0x200) {
        D_8006AA70[1] = (o->s1E << 7) / (s16)D_800693D0;
    }
    if (t->fot->w0A == 0) goto L_8002B6D4;
    t->w_d4 = 0;
    t->w_d8 = 0;
    t->w_b0 = (s32)((u8*)o->apoyos + t->fot->w1E);
    t->w_dc = -1;
    t->nodo = (NodoDisparador*)t->w_b0;
    if (t->nodo == 0) goto L_8002B6D4;
    coord_o = &o->coord;
    /* La lista de disparadores del fotograma se recorre en linea: termina al cambiar el grupo (id). */

L_8002A87C:
    if (t->nodo->id != t->fot->w0A) goto L_8002B6D4;
    t->w_e0 = t->nodo->desplazamiento;
    t->banderas = t->nodo->flags;
    if (t->nodo->req14 != 0) {
        if (!(o->flags14 & t->nodo->req14)) goto L_8002B6BC;
    }
    if (t->nodo->req18 != 0) {
        if (!(o->flags18 & t->nodo->req18)) goto L_8002B6BC;
    }
    if (t->banderas == 0) goto L_8002A9A8;

    /* coord_o es s1 (= &o->coord, fijado en 0x8002A878); pila_nodo es el area de la pila (+0x18) que recibe func_8001CE64 */

    /* Arranque del rango: 0x8002A8FC es el hueco de retardo del beqz de 0x8002A8F8 (flags == 0 salta a L_8002A9A8). */
    if (t->banderas & 0x40) {
        if (t->nodo->p1C != (u16)o->trabajo.cuadro) {
            goto L_8002B6BC;
        }
        if (o->trabajo.ticks != 0) {
            goto L_8002B6BC;
        }
    } else if (t->banderas & 4) {
        if (!(o->trabajo.flags18 & 0x2000)) {
            goto L_8002B6BC;
        }
        if (o->trabajo.ticks != 0) {
            goto L_8002B6BC;
        }
    }
    if (t->banderas & 2) {
        nd_azar = t->nodo;
        azar = BugsRand() & 0xFFFF;
        if (!(nd_azar->p1C < (u32)azar)) {
            goto L_8002B6BC;
        }
    } else if (t->banderas & 0x20000) {
        nd_azar = t->nodo;
        azar = BugsRand() & 0xFFFF;
        if (!((u32)nd_azar->p20 < (u32)azar)) {
            goto L_8002B6BC;
        }
    }
L_8002A9A8:
    if (t->nodo->cond != 0) {
        if (TestLogicCond(o, &t->nodo->cond) == 0) {
            goto L_8002B6BC;
        }
    }
    if (t->banderas & 0x2000) {
        if (o->id_atacante != t->nodo->p20) {
            goto L_8002B6BC;
        }
    }
    if (t->banderas & 0x58400000) {
        if (t->banderas & 0x08000000) {
            /* Objetivo fijo: el jugador. La cache (+0xD4/+0xD8/+0xDC) se invalida al cambiar de objetivo. */
            t->aux = t->w_d4;
            if (t->aux != D_80069698) {
                t->w_d4 = D_80069698;
                t->aux = D_80069698;
                t->w_dc = -1;
            }
        } else if (t->w_d8 != t->nodo->p20) {
            /* Objetivo por identificador: se busca en la lista global y se guarda en la cache. */
            for (t->aux = D_80069518; t->aux != 0; t->aux = t->aux->siguiente) {
                if (t->aux->w1C == t->nodo->p20 && !(t->aux->flags14 & 0x100)) {
                    break;
                }
            }
            t->w_d4 = t->aux;
            t->w_dc = -1;
            t->w_d8 = t->nodo->p20;
        } else {
            t->aux = t->w_d4;
        }
        if (t->aux == 0) {
            goto L_8002B6BC;
        }
        if (t->banderas & 0x400000) {
            func_8001CD84(t->aux, t->nodo->p1C, area);
            goto L_8002AC3C;
        }
        if (t->banderas & 0x18000000) {
            t->p30.vx = t->aux->param.trans.vx - o->param.trans.vx;
            t->p30.vz = t->aux->param.trans.vz - o->param.trans.vz;
            if (t->banderas & 1) {
                t->p30.vy = t->aux->param.trans.vy - o->param.trans.vy;
            } else {
                t->p30.vy = 0;
            }
            gte_ldlvl(&t->p30);
            gte_sqr0();
            gte_stlvnl(&t->p30);
            t->w_a4 = t->w_dc = SquareRoot0(t->p30.vx + t->p30.vy + t->p30.vz);
            if (t->banderas & 0x200000) {
                if ((u32)t->w_a4 < t->nodo->p1C) {
                    goto L_8002B6BC;
                }
                goto L_8002AC3C;
            }
            if (t->nodo->p1C < (u32)t->w_a4) {
                goto L_8002B6BC;
            }
            goto L_8002AC3C;
        }
        if (t->banderas & 0x40000000) {
            if ((u16)t->aux->trabajo.cuadro != t->nodo->p1C) {
                goto L_8002B6BC;
            }
        }
    }
L_8002AC3C:
    if (t->nodo->accion != 0) {
        RunLogicAction(o, &t->nodo->cond);
    }
    if (t->banderas == 0) {
        goto L_8002B610;
    }
    if (t->banderas & 8) {
        /* Suelta al objeto que este lleva (p70): el portado vuelve a coordenadas de mundo. */
        if (o->p70 != 0) {
            if (o->p70->p6C == o) {
                o->p70->p6C = 0;
            }
            pila_nodo.nodo = coord_o;
            func_8001CE64(&pila_nodo);
            o->coord.super = 0;
            o->coord.param = PARAMETROS_SDK(o);
            o->param.trans.vx = pila_nodo.acc.vx;
            o->param.trans.vy = pila_nodo.acc.vy;
            o->p70 = 0;
            o->param.trans.vz = pila_nodo.acc.vz;
            func_8001CFCC(coord_o);
        }
    }
    if (t->banderas & 0x600) {
        if (t->banderas & 0x200) {
            func_8003F06C(o, t->nodo->p1C, 1, D_8006967C);
        } else if (t->banderas & 0x400) {
            func_8003F06C(o, t->nodo->p1C, 2, D_8006967C);
        }
    }
    if (t->banderas & 0x24041120) {
        if (t->banderas & 0x40100) {
            if (o->raiz_ayudantes != 0) {
                pos_hijo = (s32*)&o->objetivo;
            } else {
                pos_hijo = (s32*)&o->param.trans;
            }
            t->hijo = func_80036734((s16)t->nodo->p20, pos_hijo, &o->param.giro.u.x);
            if (t->hijo == 0) {
                goto L_8002B3B4;
            }
            if (t->banderas & 0x1000000) {
                *(u16*)&t->hijo->s1E = *(u16*)&o->s1E; /* lhu / sh 0x1E (0x8002AD98): el campo es s16, la copia es sin signo */
            }
            if (t->banderas & 0x80) {
                GEO_CERO_W(&t->hijo->portado.trans);
                GEO_CERO_WH(&t->hijo->portado.giro);
                GEO_RELLENAR_1000(&t->hijo->portado.escala);
                if (t->hijo->w1C == 1) {
                    D_800693B8 = -1;
                    D_80069608 |= 1;
                }
                if (t->banderas & 0x1000) {
                    t->hijo->coord.super = &D_80069698->coord;
                    t->hijo->w26 = D_80069698->w26;
                    t->hijo->p70 = D_80069698;
                } else {
                    if (o->raiz_ayudantes != 0) {
                        t->hijo->coord.super = o->raiz_ayudantes;
                    } else {
                        t->hijo->coord.super = coord_o;
                    }
                    t->hijo->w26 = o->w26;
                    t->hijo->p70 = o;
                    o->flags18 |= 0x800;
                }
                t->hijo->coord.param = (GsCOORD2PARAM*)&t->hijo->portado;
                goto L_8002B1B8;
            }
            /* Sin bandera 0x80 el hijo hereda la escala de la raiz de ayudantes y no se re-ancla. */
            if (o->raiz_ayudantes != 0) {
                t->hijo->param.escala.vx = o->raiz_ayudantes->param->scale.vx;
                t->hijo->param.escala.vy = o->raiz_ayudantes->param->scale.vy;
                t->hijo->param.escala.vz = o->raiz_ayudantes->param->scale.vz;
            }
            t->hijo->w26 = o->w26;
            if (t->nodo->flags & 0x40000) {
                azar = BugsRand();
                t->hijo->param.giro.u.y = azar & 0xFFF;
            }
            goto L_8002B3B4;
        }
        if (t->banderas & 0x20000000) {
            /* Reutiliza un objeto ya existente: se busca por identificador entre los vivos. */
            t->hijo = D_80069518;
            if (t->hijo == 0) {
                goto L_8002B3B4;
            }
            for (; t->hijo != 0; t->hijo = t->hijo->siguiente) {
                if (t->hijo->w1C == t->nodo->p20 && !(t->hijo->flags14 & 0x100)) {
                    break;
                }
            }
            if (t->hijo == 0) {
                goto L_8002B3B4;
            }
            if (t->banderas & 0x1000000) {
                *(u16*)&t->hijo->s1E = *(u16*)&o->s1E; /* lhu / sh 0x1E (0x8002B018) */
            }
            GEO_CERO_W(&t->hijo->portado.trans);
            GEO_CERO_WH(&t->hijo->portado.giro);
            GEO_RELLENAR_1000(&t->hijo->portado.escala);
            if (t->hijo->w1C == 1) {
                D_800693B8 = -1;
                D_80069608 |= 1;
            }
            if (t->hijo->p70 != 0) {
                if (t->hijo->p70->p6C == t->hijo) {
                    t->hijo->p70->p6C = 0;
                }
                o->flags14 &= 0xFFFFFFEB;
            }
            if (t->banderas & 0x1000) {
                t->hijo->coord.super = &D_80069698->coord;
                t->hijo->w26 = D_80069698->w26;
                t->hijo->p70 = D_80069698;
            } else {
                if (o->raiz_ayudantes != 0) {
                    t->hijo->coord.super = o->raiz_ayudantes;
                } else {
                    t->hijo->coord.super = coord_o;
                }
                t->hijo->w26 = o->w26;
                t->hijo->p70 = o;
                o->flags18 |= 0x800;
            }
            t->hijo->coord.param = (GsCOORD2PARAM*)&t->hijo->portado;
            if (!(t->banderas & 0x80)) {
                o->p6C = t->hijo;
            }
L_8002B1B8:
            t->hijo->w26 = o->w26;
            func_8001CFCC(&t->hijo->coord);
            pila_nodo.nodo = &t->hijo->coord;
            func_8001CE64(&pila_nodo);
            t->hijo->param.trans.vx = pila_nodo.acc.vx;
            t->hijo->param.trans.vy = pila_nodo.acc.vy;
            t->hijo->param.trans.vz = pila_nodo.acc.vz;
            goto L_8002B3B4;
        }
        if (t->banderas & 0x1000) {
            /* El propio objeto pasa a colgar del jugador: se reinicia su transformacion portada. */
            GEO_CERO_W(&o->portado.trans);
            GEO_CERO_WH(&o->portado.giro);
            GEO_RELLENAR_1000(&o->portado.escala);
            o->param.trans.vx = o->param.trans.vy = o->param.trans.vz = 0;
            o->param.escala.vx = o->param.escala.vy = o->param.escala.vz = 0x1000;
            o->coord.super = &D_80069698->coord;
            o->w26 = D_80069698->w26;
            o->p70 = D_80069698;
            o->coord.param = (GsCOORD2PARAM*)&o->portado;
            func_8001CFCC(coord_o);
            pila_nodo.nodo = coord_o;
            func_8001CE64(&pila_nodo);
            o->param.trans.vx = pila_nodo.acc.vx;
            o->param.trans.vy = pila_nodo.acc.vy;
            o->param.trans.vz = pila_nodo.acc.vz;
            goto L_8002B3B4;
        }
        if (t->banderas & 0x20) {
            t->w114 = func_80018C68(o, area);
            if (t->w114 == 1) {
                t->w_e0 = t->nodo->p1C;
                goto L_8002B3B4;
            }
            if (t->w114 != 2) {
                goto L_8002B6BC;
            }
            t->w_e0 = t->nodo->p20;
            goto L_8002B3B4;
        }
        if (!(t->banderas & 0x4000000)) {
            goto L_8002B3B4;
        }
        t->aux = D_80069518;
        if (t->aux == 0) {
            goto L_8002B3B4;
        }
        for (; t->aux != 0; t->aux = t->aux->siguiente) {
            if (t->aux->w1C == t->nodo->p20 && !(t->aux->flags14 & 0x100)) {
                break;
            }
        }
        if (t->aux == 0) {
            goto L_8002B3B4;
        }
        t->aux->flags14 |= 0x100;
    }
L_8002B3B4:
    if (!(t->banderas & 0x82194800)) {
        goto L_8002B5F8;
    }
    if (t->banderas & 0x80000) {
        D_80069662 = 1;
        D_80010000 = t->nodo->p1C;
    }
    if (t->banderas < 0) {
        func_8001D0FC(o, t->nodo->p20, area);
    }
    if (t->banderas & 0x100000) {
        D_8006ACD0.x = o->param.trans.vx;
        D_8006ACD0.y = o->param.trans.vy;
        D_8006ACD0.z = o->param.trans.vz;
        D_8006ACD0.ang = o->param.giro.rotate.vy;
    }
    if (t->banderas & 0x800) {
        if (o->raiz_ayudantes != 0) {
            func_8001D31C(o->objetivo.vx, o->objetivo.vy, o->objetivo.vz);
        } else {
            func_8001D31C(o->param.trans.vx, o->param.trans.vy, o->param.trans.vz);
        }
        D_80069698->param.giro.u.y = o->param.giro.u.y;
    }
    if (t->banderas & 0x4000) {
        if (o->p6C != 0) {
            o->p6C->flags14 &= 0xFFFFF5F6;
            o->p6C->flags14 |= 0x1000;
            pila_nodo.nodo = &o->p6C->coord;
            func_8001CE64(&pila_nodo);
            o->p6C->param.trans.vx = pila_nodo.acc.vx;
            o->p6C->param.trans.vy = pila_nodo.acc.vy;
            o->p6C->param.trans.vz = pila_nodo.acc.vz;
            o->p6C->coord.super = 0;
            o->p6C->coord.param = PARAMETROS_SDK(o->p6C);
            o->p6C->w26 = o->w26;
            o->p6C->param.giro.u.z = 0;
            o->p6C->param.giro.u.x = 0;
            o->p6C->p70 = 0;
            func_8001CFCC(&o->p6C->coord);
            o->p6C = 0;
        }
    }
    if (t->banderas & 0x10000) {
        if (t->nodo->p20 != 1) {
            goto L_8002B994;
        }
        func_8001D588(t->nodo->p1C, 0);
    }
    if (t->banderas & 0x2000000) {
        goto L_8002B994;
    }
L_8002B5F8:
    if (t->banderas & 0x8000) {
        goto L_8002B6BC;
    }
    if (t->banderas & 0x10) {
        goto L_8002B6D4;
    }
L_8002B610:
    /* Ultimo fotograma consumido: sirve para decidir si el estado del salto se conserva al cambiar de secuencia. */
    if (t->fot != 0) {
        t->previo = t->fot->w06;
    } else {
        t->previo = 0;
    }
    t->sec = (NodoSecuencia*)((u8*)o->secuencias + t->w_e0);
    t->fot = (RegistroAnim*)(o->bloque + t->sec->desplazamiento);
    o->p180 = t->sec;
    o->registro184 = t->fot;
    if (!(t->fot->w08 & 0x40) || t->fot->w06 != t->previo) {
        o->trabajo.i14 = 0;
    }
    o->w17C = 0;
    o->u18C.estado.h194 = 0; /* sh 0x194 (0x8002B6AC) */
    o->flags14 &= 0xF9FFFDF6;
    goto L_8002B6D4;
L_8002B6BC:
    t->nodo = t->nodo->sig;
    if (t->nodo != 0) {
        goto L_8002A87C;
    }
L_8002B6D4:
    if ((o->flags08 & 0x1000000) || (t->fot->w10 & 0x800000)) {
        func_8001E1A4(o, area);
    }
    if (o->trabajo.i14 != t->fot->w06) {
        t->w114 = func_8001F268(o, &o->trabajo, t->fot->w06, t->fot->w08, area);
        t->w118 = 0;
    } else {
        t->w114 = func_8001F268(o, &o->trabajo, 0, 0, area);
        t->w118 = 1;
    }
    if (o->trabajo.flags18 & 0x100) {
        o->flags14 &= 0xF9F7EFFF;
    }
    if (t->w114 == 0x100) {
        o->trabajo.i14 = 0;
        o->flags14 &= 0xF9F7EFFF;
        if (t->fot->w0C & 4) {
            goto L_8002B994;
        }
        o->w17C += 1;
        goto L_8002B868;
    }
    if (t->w118 != 0 && (t->fot->w0C & 0x80) && (o->flags14 & 0x12)) {
        f14 = o->flags14;
        f14 &= 0xF9FFFFFF;
        o->flags14 = f14;
        if (t->fot->w0C & 4) {
            o->flags14 = f14 | 0x100;
            goto L_8002BA58;
        }
        o->flags14 = f14 & ~0x1000;
        o->w17C += 1;
L_8002B868:
        t->w_bc = *(u16*)((u8*)t->sec + (o->w17C << 1) + 6);
        if (t->w_bc != 0xFFF0 && o->w17C < 5) {
            o->registro184 = t->fot = (RegistroAnim*)(o->bloque + t->w_bc);
            o->trabajo.i14 = 0;
            o->trabajo.cuadro = 0;
            o->trabajo.ticks = 0;
        }
    }
    if (t->fot->w10 & 0x2000000) {
        /* Contador de cuadros propio de la animacion: se lleva la diferencia con el valor anterior. */
        t->w114 = *(s32*)(*(u8**)(*(u8**)(*(u8**)o->u78.p + 0x10) + 0x44) + 0x1C);
        if ((u16)o->trabajo.cuadro != 1) {
            D_800693C0 += t->w114 - D_800693B4;
        }
        D_800693B4 = t->w114;
    }
    if ((o->flags0C & 0x14) || (t->fot->w10 & 0x40)) {
        if (o->flags0C & 0x10) {
            D_8006D9B8[0] = o;
        } else if (t->fot->w10 & 0x40) {
            D_8006D9B8[0] = o;
        } else {
            t->p30.vy = 0;
            t->p30.vx = D_80069698->param.trans.vx - o->param.trans.vx;
            t->p30.vz = D_80069698->param.trans.vz - o->param.trans.vz;
            if ((s32)func_80044940((s32*)&t->p30) < 0x7D0) {
                D_8006D9B8[0] = o;
            }
        }
    }
    if (o->flags0C & 0x20000000) {
        o->param.trans.vx = D_8006D928.vpx;
        o->param.trans.vy = D_8006D928.vpy + o->s1E;
        o->param.trans.vz = D_8006D928.vpz;
        func_8001CFCC(&o->coord);
    }
    o->id_atacante = 0;
    o->flags14 &= 0xB76F777F;
    o->flags18 &= ~0x6021;
    goto L_8002BA58;
L_8002B994:
    o->flags14 |= 0x100;
L_8002BA58: ;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026FEC);
#endif

/*
 * Manejador de la zona de eventos (clase 16). Se anuncia como objeto activo cercano en D_8006D9B8
 * cuando lo pide la bandera 0x10 o el jugador esta a menos de 0x7D0 unidades en el plano. Cada
 * cuadro recorre los disparadores: filtra por azar, evalua la condicion (si falla salta al nodo
 * cuyo identificador indica el disparador) y por distancia al objeto o punto de referencia, y al
 * cumplirse ejecuta la accion y los efectos que pide flags (sonido, hijo, mover al jugador,
 * destruir otro objeto, cambiar de nivel, animar al jugador). Sin la bandera 0x8000 el recorrido
 * termina en el primer disparador ejecutado.
 */
void LogicaZonaEventos(Objeto* o)
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
                GEO_CERO_W(&t->objeto->portado.trans);
                GEO_CERO_WH(&t->objeto->portado.giro);
                GEO_RELLENAR_1000(&t->objeto->portado.escala);
                t->objeto->coord.super = &D_80069698->coord;
                t->objeto->w26 = D_80069698->w26;
                t->objeto->p70 = D_80069698;
                t->objeto->coord.param = (GsCOORD2PARAM*)&t->objeto->portado;
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
void LogicaDirectorCamara(Objeto* o)
{
    TrabajoDirectorCamara* t;
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

    t = TRABAJO_DIRECTOR_CAMARA;
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
                    D_8006D928.destino_vista_x = t->origen->param.trans.vx + (s16)t->vx;
                    D_8006D928.destino_vista_y = t->origen->param.trans.vy + (s16)t->vy;
                    D_8006D928.destino_vista_z = t->origen->param.trans.vz + (s16)t->vz;
                } else {
                    D_8006D928.destino_vista_x = t->origen->param.trans.vx;
                    D_8006D928.destino_vista_y = t->origen->param.trans.vy;
                    D_8006D928.destino_vista_z = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80000) {
                t->vx = 0;
                t->vy = -(u16)t->nodo->p20;
                t->vz = (u16)t->nodo->p1C;
                GEO_IDENTIDAD(m);
                RotMatrixY(D_80069698->param.giro.rotate.vy + 0x800, m);
                ApplyMatrix(m, (SVECTOR*)&t->vx, &t->r);
                D_8006D928.destino_vista_x += ((D_80069698->param.trans.vx + t->r.vx) - D_8006D928.destino_vista_x) >> 2;
                D_8006D928.destino_vista_y += ((D_80069698->param.trans.vy + t->r.vy) - D_8006D928.destino_vista_y) >> 2;
                D_8006D928.destino_vista_z += ((D_80069698->param.trans.vz + t->r.vz) - D_8006D928.destino_vista_z) >> 2;
                D_8006D928.destino_mira_x += (D_80069698->param.trans.vx - D_8006D928.destino_mira_x) >> 2;
                D_8006D928.destino_mira_y += (D_80069698->param.trans.vy - D_8006D928.destino_mira_y) >> 2;
                D_8006D928.destino_mira_z += (D_80069698->param.trans.vz - D_8006D928.destino_mira_z) >> 2;
            } else if (t->flags & 0x100000) {
                D_8006D928.destino_vista_x = D_8006D928.vpx;
                D_8006D928.destino_vista_y = D_8006D928.vpy;
                D_8006D928.destino_vista_z = D_8006D928.vpz;
            } else {
                D_8006D928.destino_vista_x = t->nodo->p1C;
                D_8006D928.destino_vista_y = t->nodo->p20;
                D_8006D928.destino_vista_z = t->nodo->desplazamiento;
            }
            if (t->flags & 0x40000) {
                t->ex = D_8006D928.vpx - D_8006D928.destino_vista_x;
                t->ey = D_8006D928.vpy - D_8006D928.destino_vista_y;
                t->ez = D_8006D928.vpz - D_8006D928.destino_vista_z;
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
                    D_8006D928.destino_vista_x += (t->r.vx * t->modulo) >> 12;
                    D_8006D928.destino_vista_y += (t->r.vy * t->modulo) >> 12;
                    D_8006D928.destino_vista_z += (t->r.vz * t->modulo) >> 12;
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
                    D_8006D928.destino_mira_x = t->origen->param.trans.vx;
                    D_8006D928.destino_mira_y = t->origen->param.trans.vy;
                    D_8006D928.destino_mira_z = t->origen->param.trans.vz;
                }
            } else if (t->flags & 0x80) {
                D_8006D928.destino_mira_x = o->param.trans.vx;
                D_8006D928.destino_mira_y = o->param.trans.vy;
                D_8006D928.destino_mira_z = o->param.trans.vz;
            } else if (t->flags & 0x100000) {
                D_8006D928.destino_mira_x = D_8006D928.x;
                D_8006D928.destino_mira_y = D_8006D928.y;
                D_8006D928.destino_mira_z = D_8006D928.z;
            } else {
                D_8006D928.destino_mira_x = t->nodo->p1C;
                D_8006D928.destino_mira_y = t->nodo->p20;
                D_8006D928.destino_mira_z = t->nodo->desplazamiento;
            }
            D_8006D928.flags80 |= 0x800;
        } else if (t->flags & 8) {
            D_8006D928.flags80 &= 0xB7FF;
        }
        if (t->flags & 0x400) {
            D_8006D928.distancia_acercamiento = t->nodo->p1C;
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
            D_8006D928.vista_68_x = ca;
            D_8006D928.vista_94_x = ca;
            D_8006D928.vista_b4_x = ca;
            D_8006D928.vista_68_y = cb;
            D_8006D928.vista_94_y = cb;
            D_8006D928.vista_b4_y = cb;
            D_8006D928.vista_68_z = cc;
            D_8006D928.vista_94_z = cc;
            D_8006D928.vista_b4_z = cc;
            D_8006D928.mira_a4_x = cd;
            D_8006D928.mira_a4_y = ce;
            D_8006D928.mira_a4_z = cf;
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
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", LogicaDirectorCamara);
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
void LogicaSpriteConCaja(Objeto* o)
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
        o->trabajo.tabla = tb;
        f = tb->fotogramas;
        b->fotogramas = f;
        b->actual = f;
        k = tb->cuenta;
        b->cuadro = 0;
        b->espera = 2;
        b->ticks = 2;
        b->ultimo = k - 1;
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
        o->alcance2 = o->w2E * o->w2E + o->radio * o->radio;
        func_8001CFCC(&o->coord);
        ((DibujarSprite)func_8001E528)(o, b, 1, area);
    }
    if (b->ticks == 0) {
        w = b->espera;
        b->cuadro = b->cuadro + 1;
        b->ticks = w;
        if ((u16)b->cuadro > b->ultimo) {
            b->cuadro = 0;
            b->actual = b->fotogramas;
        }
        ((DibujarSprite)func_8001E528)(o, b, 1, area);
    }
    b->ticks -= 1;
    n = (NodoDisparador*)o->apoyos;
    if (n != 0) {
        do {
            if (TestLogicCond(o, &n->cond) != 0) {
                RunLogicAction(o, &n->cond);
                if (n->flags & 0x200) {
                    if (b->ticks == 0 && (u16)b->cuadro == 0) {
                        func_8003F06C(o, n->p1C, 1, D_8006967C);
                    }
                }
                if (n->flags & 0x400) {
                    func_8003F06C(o, n->p1C, 2, D_8006967C);
                }
                if (n->flags & 0x10000) {
                    if (b->ticks == 0 && (u16)b->cuadro >= b->ultimo) {
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
void LogicaSpriteDecorativo(Objeto* o)
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
        o->trabajo.tabla = tb;
        f = tb->fotogramas;
        b->fotogramas = f;
        b->actual = f;
        b->ultimo = tb->cuenta - 1;
        b->cuadro = (u16)o->max.vx;
        b->espera = (u8)o->max.vz;
        b->ticks = (u8)o->max.vz;
        ((DibujarSprite)func_8001E600)(o, b, 1, area);
    }
    if (b->ticks == 0) {
        b->ticks = b->espera;
        b->cuadro += 1;
        if (b->ultimo < (u16)b->cuadro) {
            b->cuadro = 0;
        }
        ((DibujarSprite)func_8001E600)(o, b, 1, area);
    }
    b->ticks -= 1;
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
void LogicaActorSecuencias(Objeto* o)
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
                        if (t->nodo->p1C != (u16)o->trabajo.cuadro) {
                            goto siguiente;
                        }
                        if (o->trabajo.ticks != 0) {
                            goto siguiente;
                        }
                    } else if (t->flags & 4) {
                        if (!(o->trabajo.flags18 & 0x2000)) {
                            goto siguiente;
                        }
                        if (o->trabajo.ticks != 0) {
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
        t->resultado = AvanzarAnimacionSprite(o, &o->trabajo, t->fotograma->w06, t->fotograma->w08, area);
    } else {
        t->resultado = AvanzarAnimacionSprite(o, &o->trabajo, 0, 0, area);
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
                o->trabajo.cuadro = 0;
                o->trabajo.ticks = 0;
            }
        }
    }
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 14728 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original guarda el objeto en s4, el scratchpad en s3, el area en s5 y el margen de la caja en s6 y deja s0 a s2 para los punteros de la preparacion; el compilador los reparte un registro mas abajo. La estructura de las ocho esquinas y de los dos modos coincide. */
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
        BarrerTerreno(&t->px, &t->vx, t, area); \
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
        BarrerTerreno(&t->px, &t->vx, t, area); \
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
 * Manejador del bloque empujable (clase 5). El jugador deja en empuje.vx y empuje.vz el desplazamiento que
 * intenta hacer contra el bloque; w17C fija los ejes y sentidos permitidos (0x01 X, 0x02 Z, 0x100 y
 * 0x200 anulan el sentido negativo o positivo, 0x04 prueba en dos pasadas, 0x40 modo plataforma,
 * 0x80 no cae). El avance se prueba contra otros objetos y contra el terreno desde las cuatro
 * esquinas de la caja girada, se aplica al bloque, la parte que no pudo absorber vuelve al jugador y
 * se controla el sonido de arrastre. Termina con la gravedad del bloque.
 */
void LogicaBloqueEmpujable(Objeto* o)
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
        D_80069698->param.trans.vx -= o->empuje.vx;
        D_80069698->param.trans.vz -= o->empuje.vz;
        o->empuje.vx = 0;
        o->empuje.vz = 0;
        goto reposo;
    }
    if (!((o->flags14 & 0x8000) && !(D_80069698->flags14 & 0x4000))) {
        if (func_80016C0C(o, 0x20000, area) == 0) {
            goto sin_empuje;
        }
    }
    m = &t->m;
    margen = (s16)o->radio >> 1;
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
    t->dz = o->empuje.vz;
    t->dy = 0;
    t->dx = o->empuje.vx;
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
        t->chocado = func_80017478(o, (SVECTOR*)&t->cx, area, 0x2690A);
        if (t->chocado != 0) {
            t->chocado->flags14 |= 0x40000000;
            t->chocado->id_atacante = o->w1C;
            o->id_atacante = t->chocado->w1C;
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
        BarrerTerreno(&t->px, &t->dx, t, area);
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
        BarrerTerreno(&t->px, &t->dx, t, area);
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
        D_80069698->param.trans.vx -= o->empuje.vx - t->dx;
        D_80069698->param.trans.vz -= o->empuje.vz - t->dz;
        goto disparadores;
    }
    BLOQUE_FILTRAR(t->dx, 1);
    BLOQUE_FILTRAR(t->dz, 2);
    t->cx = t->dx;
    t->cy = t->dy;
    t->cz = t->dz;
    o->p70 = D_80069698;
    t->chocado = func_80017478(o, (SVECTOR*)&t->cx, area, 0x2690A);
    if (t->chocado != 0) {
        t->chocado->flags14 |= 0x40000000;
        t->chocado->id_atacante = o->w1C;
        o->id_atacante = t->chocado->w1C;
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
            BarrerTerreno(&t->px, &t->vx, t, area);
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
            BarrerTerreno(&t->px, &t->vx, t, area);
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
    t->vx = t->dx - o->empuje.vx;
    t->vy = 0;
    t->vz = t->dz - o->empuje.vz;
    jugador = D_80069698;
    t->px = jugador->param.trans.vx;
    t->py = jugador->param.trans.vy;
    t->pz = jugador->param.trans.vz;
    t->zona = o->w26;
    BarrerTerreno(&t->px, &t->vx, t, area);
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
    GEO_CERO_W(&t->dx);
    func_8001CBB8(o, (Movimiento*)&t->dx, (ResultadoBaldosa*)t, area);
    o->param.trans.vy += t->dy;
    func_8001CF50(o);
    o->empuje.vz = 0;
    o->empuje.vx = 0;
    o->flags14 &= 0xFFFF5FFF;
    if (o->flags08 & 0x1000000) {
        func_8001E1A4(o, area);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", LogicaBloqueEmpujable);
#endif

/*
 * Manejador vacio de la clase 21 de D_8005E35C: el objeto no tiene logica propia. Conserva el prototipo
 * de la tabla (void (*)(Objeto*)) aunque no lea el parametro.
 */
void func_8002EA9C(Objeto* o)
{
}

/*
 * Manejador del efecto anclado a un nodo de otro objeto (clase 34). Elige la secuencia de animacion
 * (la de w17E; al acabar vuelve a la de identificador 1), reparte el dano a un objeto cercano si el
 * fotograma lo pide, anima y, si el objeto cuelga de un nodo, acumula la posicion global recorriendo
 * la cadena de matrices con el GTE. Se destruye al terminar la animacion si el fotograma lo pide y
 * cuando pierde a su portador.
 */
void LogicaEfectoAnclado(Objeto* o)
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
            t->otro->id_atacante = o->w1C;
            o->id_atacante = t->otro->w1C;
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
        GEO_CERO_WH(&t->ax);
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
                GEO_GUARDAR_H_T1(&t->ax);
                t->cursor = t->cursor->super;
            } while (t->cursor != 0);
        }
        o->param.giro.u.y = ratan2(t->vx, t->vz);
        o->param.giro.u.z = 0;
        o->param.giro.u.x = 0;
        GEO_CARGAR_H(&t->ax);
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
void LogicaProyectil(Objeto* o)
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
        GEO_CERO_WH(&a->param.rotate);
        GEO_CERO_W(&o->u78.ayudas->param.scale);
        GEO_CERO_W(&o->u78.ayudas->param.trans);
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
        t->vz = (u16)o->radio;
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
        BarrerTerreno(&t->px, &t->dx, t, area);
        t->px = o->param.trans.vx + t->dx;
        t->pz = o->param.trans.vz + t->dz;
        t->py = o->param.trans.vy + t->my;
        t->golpeado = func_800171E4(o, (VECTOR*)&t->px, 0x180, 0, area);
        if (t->golpeado != 0) {
            o->s1E = 1;
            if (D_80069698 == t->golpeado && !(D_80069698->flags14 & 0x03000000)) {
                if (func_8001D75C(o, 0, area) != 0 && (s16)o->u18C.estado.w196 != 0) {
                    func_8001D0FC(o, (s16)o->u18C.estado.w196, area);
                }
            } else {
                t->golpeado->id_atacante = (u16)o->w1C;
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
void LogicaAnimacionPorGuion(Objeto* o)
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
void LogicaObjetoDeCamara(Objeto* o)
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
void LogicaZonaSonda(Objeto* o)
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
    bits = o->u18C.estado.w196;
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
    GEO_GUARDAR_H_T1(t);
    GEO_CARGAR_H(&t->cx);
    GEO_SUMAR_H(t);
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

/*
 * Manejador vacio de las clases 3, 11, 15, 17, 30, 33 y 35 de D_8005E35C: esos objetos no tienen
 * logica propia. Conserva el prototipo de la tabla (void (*)(Objeto*)) aunque no lea el parametro.
 */
void func_8002F968(Objeto* o)
{
}

/*
 * Paso por cuadro de los indicadores de la interfaz de juego: no recibe argumentos (el llamado
 * carga todo de globales) y no devuelve valor, de modo que solo guarda y restaura $ra.
 */
void func_8002F970(void)
{
    func_80039094();
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 60 con la configuracion versionada (g = 8 del archivo). Los dos bytes se
 * leen y escriben con un unico lui y la copia del valor leido queda en el hueco del primer salto,
 * como el original; difiere solo el reparto de registros: el original deja el resultado de la
 * suma en a2 y GCC lo deja en v1 (los papeles de v1 y a2 estan invertidos).
 *
 * Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el
 * bajo y D_8001013C el alto: r[7] y r[0xFC] del banco del estado principal de 0x80010000). El operando se
 * trunca a un byte dentro de la rutina (andi 0xFF en 0x8002F9AC y 0x8002F9DC) y los llamadores
 * le pasan el valor de 16 bits sin truncar (lhu): por eso el parametro es s32 y el truncamiento
 * un cast. Declarado u8, cada llamador recorta el argumento con lbu.
 */
void func_8002F990(s32 a0, s32 a1)
{
    EstadoPrincipal* e;
    u32 reg;
    u32 res;
    u32 alto;

    e = ESTADO_PRINCIPAL;
    reg = e->r[7] | (e->r[0xFC] << 8);
    res = reg;
    if (a1 == 0) {
        res = (u8)a0 + reg;
    }
    if (a1 == 1) {
        res = reg + 1;
    }
    if (a1 == 2) {
        res = reg - 1;
    }
    if (a1 == 3) {
        res = reg - (u8)a0;
    }
    alto = res & 0xFFFF;
    e->r[7] = res;
    e->r[0xFC] = alto >> 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F990);
#endif
