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

/*
 * Pendiente de traducir: tiene marco de pila de 0x30 bytes con s0..s4 y ra guardados (no es manuscrita); la
 * marca Handwritten del particionador procede de las instrucciones sueltas del GTE (ctc2, mvmva, swc2).
 */
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_2", func_80025B2C);
