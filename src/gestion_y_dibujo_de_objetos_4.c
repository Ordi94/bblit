#include "common.h"
#include "geometria.h"
#include "objetos.h"


/*
 * Area de trabajo de la sonda de altura: la entidad que transforma func_8001CE64 (nodo,
 * vector local y posicion transformada en +0x0C), el resultado de la consulta de baldosa en
 * +0x1C y su area de trabajo en +0x34.
 */
typedef struct Sonda {
    AcumuladorNodos ent;
    ResultadoBaldosa r;
    TrabajoBaldosa w;
} Sonda;

/* Posicion que la sonda entrega, en +0x18 de la estructura de salida. */
typedef struct SalidaSonda {
    u8 pad00[0x18];
    VECTOR pos;
} SalidaSonda;

extern void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w);

/*
 * Descriptor de la sombra que func_8003A5C8 arma en el scratchpad (0x1F800000) y consumen el
 * dibujador de modelos y las rutinas de matriz: escala en +0, +4 y +8, giros en +0x10..+0x14
 * y altura de referencia (techo de la busqueda y, al volver, altura del apoyo) en +0x1C.
 */
typedef struct DescSombra {
    s32 escala_x;
    s32 escala_y;
    s32 escala_z;
    u8 pad0C[4];
    s16 giro_x;
    s16 giro_y;
    s16 giro_z;
    u8 pad16[6];
    s32 altura;
} DescSombra;

/*
 * Area de trabajo de func_80039D44 (0xB4 bytes). Entre +8 y +0x77 la misma memoria tiene dos
 * disposiciones segun la fase: 's' cuando el objeto cae dentro de un solido (matriz inversa del
 * solido, vectores de 16 bits y producto escalar) y 't' cuando se muestrea el terreno (centro,
 * tres esquinas de 12 bytes y los dos vectores de plano con su producto vectorial). La consulta
 * de baldosa usa r en +0x78 y tb en +0x90.
 */
typedef struct SondaSombra {
    u8 pad00[4];
    s32 escala;
    union {
        struct {
            MATRIX m;
            SVECTOR giro;
            SVECTOR local;
            SVECTOR dif;
            SVECTOR n;
            SVECTOR e;
            s32 dot;
            u8 pad54[0x70 - 0x4C];
        } s;
        struct {
            VECTOR c;
            VECTOR p1;
            VECTOR p2;
            VECTOR p3;
            VECTOR v1;
            VECTOR v2;
            VECTOR nrm;
        } t;
    } u;
    ResultadoBaldosa r;
    TrabajoBaldosa tb;
} SondaSombra;

/* Resta de vectores de tres componentes: resultado = b - a. */
void func_80039BFC(s32* a, s32* b, s32* resultado)
{
    resultado[0] = b[0] - a[0];
    resultado[1] = b[1] - a[1];
    resultado[2] = b[2] - a[2];
}

/* Producto vectorial de dos vectores de tres componentes: resultado = a x b (sin GTE). */
void func_80039C3C(s32* a, s32* b, s32* resultado)
{
    resultado[0] = a[1] * b[2] - a[2] * b[1];
    resultado[1] = a[2] * b[0] - a[0] * b[2];
    resultado[2] = a[0] * b[1] - a[1] * b[0];
}

/*
 * Espera a que el contador de posicion del anillo de dibujo D_80069610, que reescribe el retorno
 * de llamada de VSync, quede a menos de 0x800 posiciones por delante de 'limite' (el anillo
 * tiene D_8006954C posiciones: la diferencia negativa se corrige con su longitud). Si pasan
 * cuatro VSync sin avanzar, restaura la posicion anterior D_80069614 para no bloquearse.
 */
void func_80039CD0(s32 limite)
{
    s32 anillo;
    u32 previo;
    s32 d;

    anillo = D_8006954C;
    previo = D_80069614;
    for (;;) {
        d = D_80069610 - limite;
        if (d < 0) {
            d -= 0x400;
            d += anillo;
        }
        if (d >= 0x800) {
            return;
        }
        if ((s16)D_800695A6 >= 4) {
            D_80069610 = previo;
        }
    }
}

/*
 * Busca la superficie sobre la que se apoya 'o' para orientar y escalar su sombra. Primero
 * recorre los objetos solidos (D_80069630) y devuelve el primero cuyo plano superior queda entre
 * la altura del objeto y d->altura, casa con 'mascara' (o tiene la bandera 0x2000) y contiene al
 * objeto en su caja local: rellena 'd' con la escala por distancia al plano, el giro del solido
 * y la altura del plano. Si ninguno sirve, muestrea el terreno en tres esquinas de la base del
 * objeto, descarta las alturas a mas de 0x23 de la de referencia, y deduce los giros X y Z de la
 * sombra con el producto vectorial de los dos lados del triangulo. Devuelve el solido o 0.
 */
Objeto* func_80039D44(Objeto* o, DescSombra* d, u32 mascara, SondaSombra* w)
{
    Objeto* cur;
    TrabajoBaldosa* tb;
    s32 h;
    s32 top;
    s32 y;
    s32 r;

    cur = D_80069630;
    tb = &w->tb;
    for (; cur != 0; cur = cur->sig10) {
        h = cur->max.vy;
        top = cur->param.trans.vy + h;
        if (h < 0x47) {
            top += 0x28;
        } else {
            top += 0x50;
        }
        if (top >= o->param.trans.vy && d->altura >= top &&
            ((cur->flags08 & mascara) || (cur->flags0C & 0x2000)) && !(cur->flags08 & 1) &&
            cur->s2A == 2 && o != cur) {
            w->u.s.giro.vx = 0x1000 - cur->param.giro.u.x;
            w->u.s.giro.vy = 0x1000 - cur->param.giro.u.y;
            w->u.s.giro.vz = 0x1000 - cur->param.giro.u.z;
            w->u.s.dif.vx = o->param.trans.vx - cur->param.trans.vx;
            w->u.s.dif.vy = o->param.trans.vy - cur->param.trans.vy;
            w->u.s.dif.vz = o->param.trans.vz - cur->param.trans.vz;
            GEO_IDENTIDAD(&w->u.s.m);
            RotMatrixX(w->u.s.giro.vx, &w->u.s.m);
            RotMatrixY(w->u.s.giro.vy, &w->u.s.m);
            RotMatrixZ(w->u.s.giro.vz, &w->u.s.m);
            ApplyMatrixSV(&w->u.s.m, &w->u.s.dif, &w->u.s.local);
            /* El radio se extiende a 32 bits en esta sentencia (variable s32): el original carga s20 antes que la caja del solido. */
            r = cur->s20;
            if (w->u.s.local.vx >= cur->min.vx - r && cur->max.vx + r >= w->u.s.local.vx &&
                w->u.s.local.vz >= cur->min.vz - r && cur->max.vz + r >= w->u.s.local.vz) {
                w->u.s.giro.vx = 0;
                w->u.s.giro.vy = cur->max.vy;
                w->u.s.giro.vz = 0;
                ApplyMatrixSV(&cur->coord.coord, &w->u.s.giro, &w->u.s.local);
                w->u.s.giro.vy = 0x1000;
                ApplyMatrixSV(&cur->coord.coord, &w->u.s.giro, &w->u.s.n);
                w->u.s.giro.vy = cur->param.escala.vy;
                ApplyMatrixSV(&cur->coord.coord, &w->u.s.giro, &w->u.s.e);
                w->u.s.dot = w->u.s.n.vx * w->u.s.local.vx + w->u.s.n.vy * w->u.s.local.vy +
                             w->u.s.n.vz * w->u.s.local.vz;
                y = cur->param.trans.vy +
                    (w->u.s.dot - w->u.s.n.vx * w->u.s.dif.vx - w->u.s.n.vz * w->u.s.dif.vz) /
                        (s16)(w->u.s.e.vy | 1);
                d->altura = y;
                w->escala = (o->param.trans.vy - y) * 4 + 0x1000;
                if (w->escala < 0x800) {
                    w->escala = 0x800;
                }
                d->escala_x = w->escala;
                d->escala_y = 0x1000;
                d->escala_z = w->escala;
                GEO_CARGAR_WH(&cur->param.giro);
                GEO_GUARDAR_WH(&d->giro_x);
                return cur;
            }
        }
    }
    GEO_CARGAR_W(&o->param.trans);
    GEO_GUARDAR_W_T1(&w->u.t.c);
    w->r.grupo = o->w26;
    w->u.t.p1.vx = w->u.t.c.vx + o->min.vx;
    w->u.t.p1.vy = w->u.t.c.vy;
    w->u.t.p1.vz = w->u.t.c.vz + o->min.vz;
    func_8001C134((s32*)&w->u.t.p1, &w->r, tb);
    if (w->r.flags & 4) {
        w->u.t.p1.vy = d->altura;
    } else {
        w->u.t.p1.vy += (s16)w->r.pendiente_abs;
        if (w->u.t.p1.vy >= d->altura + 0x23 || d->altura - 0x23 >= w->u.t.p1.vy) {
            w->u.t.p1.vy = d->altura;
        }
    }
    w->u.t.p2.vx = w->u.t.c.vx + o->max.vx;
    w->u.t.p2.vy = w->u.t.c.vy;
    w->u.t.p2.vz = w->u.t.p1.vz;
    func_8001C134((s32*)&w->u.t.p2, &w->r, tb);
    if (w->r.flags & 4) {
        w->u.t.p2.vy = d->altura;
    } else {
        w->u.t.p2.vy += (s16)w->r.pendiente_abs;
        if (w->u.t.p2.vy >= d->altura + 0x23 || d->altura - 0x23 >= w->u.t.p2.vy) {
            w->u.t.p2.vy = d->altura;
        }
    }
    w->u.t.p3.vx = w->u.t.p1.vx;
    w->u.t.p3.vy = w->u.t.c.vy;
    w->u.t.p3.vz = w->u.t.c.vz + o->max.vz;
    func_8001C134((s32*)&w->u.t.p3, &w->r, tb);
    if (w->r.flags & 4) {
        w->u.t.p3.vy = d->altura;
    } else {
        w->u.t.p3.vy += (s16)w->r.pendiente_abs;
        if (w->u.t.p3.vy >= d->altura + 0x23 || d->altura - 0x23 >= w->u.t.p3.vy) {
            w->u.t.p3.vy = d->altura;
        }
    }
    if (d->altura < o->param.trans.vy) {
        w->escala = 0x1000;
    } else {
        w->escala = (o->param.trans.vy - d->altura) * 4 + 0x1000;
        if (w->escala < 0x800) {
            w->escala = 0x800;
        }
    }
    d->escala_x = w->escala;
    d->escala_y = 0x1000;
    d->escala_z = w->escala;
    if (w->u.t.p1.vy == w->u.t.p2.vy && w->u.t.p1.vy == w->u.t.p3.vy) {
        d->giro_z = 0;
        d->giro_x = 0;
        d->giro_y = o->param.giro.u.y;
    } else {
        func_80039BFC((s32*)&w->u.t.p1, (s32*)&w->u.t.p2, (s32*)&w->u.t.v1);
        func_80039BFC((s32*)&w->u.t.p1, (s32*)&w->u.t.p3, (s32*)&w->u.t.v2);
        func_80039C3C((s32*)&w->u.t.v1, (s32*)&w->u.t.v2, (s32*)&w->u.t.nrm);
        d->giro_x = ratan2(w->u.t.nrm.vz, w->u.t.nrm.vy);
        d->giro_y = 0;
        d->giro_z = ratan2(w->u.t.nrm.vx, w->u.t.nrm.vy);
    }
    return 0;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 316 con la configuracion versionada (g = 8 del archivo). El cuerpo y los
 * saltos coinciden; difiere solo el reparto de registros salvados: el original deja el area de
 * trabajo en $s0, la salida en $s1, el objeto en $s2 y la direccion de la baldosa en $s3; GCC da
 * $s0 a la salida y $s3 al objeto. Ni el orden de las declaraciones locales, ni izar la direccion
 * de la baldosa o la constante -1 antes de la primera rama, ni un bucle con salida explicita
 * cambian el reparto (las dos ultimas formas empeoran a 1144 y 1326). Variantes probadas: 17.
 */
/*
 * Calcula la posicion de apoyo de 'o' en 'sal': parte de la posicion del primer ayudante
 * visible (transformada por su jerarquia) o de la del propio objeto, la baja por el terreno con
 * func_8001C134 y la limita por D_8006960C y, salvo que el nivel lo desactive, por la altura
 * del objeto. Devuelve 0 si el ayudante no es visible y 1 en otro caso.
 */
s32 func_8003A3D0(Objeto* o, SalidaSonda* sal, Sonda* s)
{
    Ayuda* a;
    Ayuda* b;
    Objeto* p;
    TrabajoBaldosa* w;
    s32 sin_grupo;

    a = o->u78.ayudas;
    w = &s->w;
    if (a != 0 && (b = (Ayuda*)a->cab.siguiente) != 0) {
        if (b->visible == 0) {
            return 0;
        }
        s->ent.nodo = &b->coord;
        func_8001CE64(&s->ent);
        GEO_CARGAR_W(&s->ent.acc);
        GEO_GUARDAR_W_T1(&sal->pos);
    } else {
        if (a->visible == 0) {
            return 0;
        }
        GEO_CARGAR_W(&o->param.trans);
        GEO_GUARDAR_W_T1(&sal->pos);
    }
    p = o->p70;
    if (p != 0 && ((p->flags08 & 8) || (p->flags0C & 0x2000))) {
        sal->pos.vy = o->param.trans.vy;
    } else {
        s->r.grupo = (s16)o->w26;
        func_8001C134((s32*)&sal->pos, &s->r, w);
        sin_grupo = -1;
        while (s->r.flags & 8) {
            if (s->r.grupo == sin_grupo) {
                break;
            }
            sal->pos.vy = sal->pos.vy + 1;
            func_8001C134((s32*)&sal->pos, &s->r, w);
        }
        sal->pos.vy = sal->pos.vy + (s16)s->r.pendiente_abs;
        if (D_8006960C < sal->pos.vy) {
            sal->pos.vy = D_8006960C;
        }
        if (!(D_8006D9A8[0] & 0x100)) {
            if (sal->pos.vy < o->param.trans.vy) {
                sal->pos.vy = o->param.trans.vy;
            }
        }
    }
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_8003A3D0);
#endif

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_8003A5C8);
