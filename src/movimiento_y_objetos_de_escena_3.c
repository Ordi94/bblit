#include "common.h"
#include "gte.h"
#include "motor.h"

/*
 * Registro de dieciseis bytes de un cuadro de sprite: banderas en +2 (bit 3 = espejo), pagina
 * de textura en +6 (bits 0 a 3 = columna de 64, bits 7 y 8 = profundidad de color), origen u, v
 * en +8 y +9, paleta en +0xA (bits 0 a 5 = x en 16, bits 6 y siguientes = y), y tamano en +0xC y
 * +0xE.
 */
typedef struct RegistroSprite {
    u8 pad00[2];
    u8 flags;
    u8 pad03[3];
    u16 pagina;
    u8 u;
    u8 v;
    u16 paleta;
    u16 w;
    u16 h;
} RegistroSprite;

/*
 * Descriptor de un conjunto de cuadros: cuadro actual en +2, tabla de indices en +0x1C,
 * registros en +0x20 y cuatro valores de color/escala en +0x2C..+0x32.
 */
typedef struct ConjuntoSprites {
    u8 pad00[2];
    u16 actual;
    u8 pad04[0x1C - 0x04];
    u16* tabla;
    RegistroSprite* registros;
    u8 pad24[0x2C - 0x24];
    u16 c2C;
    u16 c2E;
    u16 c30;
    u16 c32;
} ConjuntoSprites;

extern void func_8001E600(Objeto* o, ConjuntoSprites* c, u32 modo);

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
/* Pendiente: puntuacion 1535 con la configuracion versionada (-G0). Mismos accesos y mismos almacenes; el original funde el desplazamiento de 16 bytes del registro tras la reunion de las dos ramas y reparte a0..a3 y t0 a las cuatro lecturas del registro, el C duplica el desplazamiento en cada rama y usa v0 y t0. Variantes probadas: 8. */
void func_8001E528(Objeto* o, ConjuntoSprites* c, u32 modo)
{
    RegistroSprite* r;
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
    if (modo & 1) {
        indice = c->actual;
    } else {
        indice = *(u8*)(c->tabla + c->actual);
    }
    r = c->registros + indice;
    p = (SpritePlano*)((u8*)o->u78.p + 0xC);
    u = r->u;
    v = r->v;
    w = r->w;
    h = r->h;
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
    p->clut = r->paleta;
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
/* Pendiente: puntuacion 2665 con la configuracion versionada (-G0). Mismos accesos y almacenes; el original calcula el desplazamiento de color en t2 y deja el puntero al sprite en v1, el C reparte otros registros y reordena las lecturas del registro del cuadro. Variantes probadas: 3. */
void func_8001E600(Objeto* o, ConjuntoSprites* c, u32 modo)
{
    RegistroSprite* r;
    SpriteEscalado* p;
    u16 indice;
    s32 desplazamiento;

    if (modo & 1) {
        indice = c->actual;
    } else {
        indice = *(u8*)(c->tabla + c->actual);
    }
    r = c->registros + indice;
    desplazamiento = 2 - ((r->pagina >> 7) & 3);
    p = (SpriteEscalado*)((u8*)o->u78.p + 0xC);
    p->s00 = (r->u >> desplazamiento) + ((r->pagina & 0xF) << 6);
    p->s02 = r->v + ((r->pagina << 4) & 0x100);
    p->w08 = c->c2C;
    p->s10 = r->w >> desplazamiento;
    p->w12 = r->h;
    p->w0A = c->c2E;
    p->s04 = (r->paleta & 0x3F) * 0x10;
    p->s06 = r->paleta >> 6;
    p->w0C = c->c30;
    p->w0E = c->c32;
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

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_8001E720);

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
/* Pendiente: puntuacion 605 con la configuracion versionada (-G0). La condicion de continuar (bit 4 apagado o bit 0x10 activo) y la reunion de las dos ramas de la altura no se reproducen: el compilador adelanta la carga de las banderas y repite el almacen de h10A en cada rama. Variantes probadas: 10. */
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

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_3", func_80020354);

/*
 * Busca el peldano que corresponde a la altura del objeto sobre el objeto de apoyo (p70):
 * entrega el apoyo por *apoyo y devuelve 1 si el objeto esta por encima del peldano, 2 si
 * esta en el suelo del apoyo y 0 si lo toca; guarda en el apoyo la altura del peldano
 * alcanzado (+0x13C). Si el apoyo es plano (bandera 0x400000) solo compara con su altura.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 2360 con la configuracion versionada (-G0). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica. Variantes probadas: 4. */
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
            altura = o->i1A8 + d->dy - 0x12C;
            if (altura <= 0) {
                return 2;
            }
            return altura >= t->trabajo.h0A;
        }
        altura = o->i1A8 + d->dy - 0x12C;
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
