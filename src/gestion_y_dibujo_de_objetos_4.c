#include "common.h"
#include "geometria.h"
#include "objetos.h"

extern u32 D_80069610;
extern u32 D_80069614;
extern s32 D_8006954C;
extern vu16 D_800695A6;
extern s32 D_8006960C;

/*
 * Area de trabajo de la sonda de altura: la entidad que transforma func_8001CE64 (nodo,
 * vector local y posicion transformada en +0x0C), el resultado de la consulta de baldosa en
 * +0x1C y su area de trabajo en +0x34.
 */
typedef struct Sonda {
    EntidadTransformada ent;
    ResultadoBaldosa r;
    TrabajoBaldosa w;
} Sonda;

/* Posicion que la sonda entrega, en +0x18 de la estructura de salida. */
typedef struct SalidaSonda {
    u8 pad00[0x18];
    VECTOR pos;
} SalidaSonda;

extern void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w);

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

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_80039D44);

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
