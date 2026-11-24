#include "common.h"
#include "globales.h"
#include "geometria.h"
#include "gte.h"
#include "arranque.h"
#include "objetos.h"
#include "motor.h"

/* Area de trabajo de la sonda de camara (func_800330AC): direccion, matriz, resultado y consulta de colision. */
typedef struct SondaCamara {
    SVECTOR rot;
    SVECTOR dir;
    MATRIX m;
    VECTOR res;
    VECTOR pos;
    u8 pad50[2];
    u16 f52;
    u8 pad54[6];
    s16 s5A;
    u8 pad5C[0x68 - 0x5C];
    s32 i68;
} SondaCamara;

/* Area de trabajo del rayo de camara (func_80032B2C): matriz, vectores locales, caja del objeto y objeto en curso. */
typedef struct RayoCamara {
    MATRIX m;
    SVECTOR rot;
    SVECTOR v28;
    SVECTOR d30;
    VECTOR suma;
    SVECTOR a48;
    SVECTOR a50;
    s32 i58;
    s32 i5C;
    s32 i60;
    Objeto* cur;
} RayoCamara;

/* Memoria de trabajo de func_800353B0 en el scratchpad (0x1F800000). */
typedef struct Scratch {
    s32 d0;
    s32 d4;
    s32 d8;
    u8 padC[4];
    SVECTOR p10;
    s32 m18;
    s32 m1C;
    s32 m20;
    u8 pad24[0x2C - 0x24];
    Objeto* cur;
    Objeto* l30;
    Objeto* l34;
    Objeto* l38;
    EntradaVisible* tp3C;
    s32 i40;
    s32 i44;
    u8 pad48[0x68 - 0x48];
    s16 sx;
    s16 sy;
    s32 z6C;
    s32 i70;
    s32 r74;
    GsCOORDINATE2* n78;
    u8 pad7C[4];
    VECTOR v80[8];
    VECTOR* p100;
    SVECTOR c104[8];
    SVECTOR* p144;
} Scratch;

/*
 * Guarda MAC3 del GTE (profundidad tras rtps) en la palabra apuntada. mfc2 lee un registro del
 * coprocesador, el unico caso que el compilador no expresa en C.
 */
#define GUARDAR_MAC3(p) \
    __asm__ volatile ("move $9, %0\n\tmfc2 $8, $27\n\tnop\n\tsw $8, 0($9)" : : "r"(p) : "$8", "$9", "memory")

extern void (*D_8005E35C[])(Objeto*);
extern void ActualizarCamaraSeguimiento(Objeto* o, u32 reiniciar);
extern void func_80035244(void);
extern void func_800351B4(Objeto* a0);
extern void func_8003502C(Objeto* a0);

/* Secuencia de teclas de los trucos: caso a ejecutar, paso actual y hasta diez teclas (0 termina). */
typedef struct Secuencia {
    s16 caso;
    s16 paso;
    s16 teclas[10];
} Secuencia;

extern Secuencia D_8005E768[];

extern u16 D_8005E6F8[];
extern s16 D_80069D90[];
extern long SquareRoot0(long x);
extern s32 rand(void);
extern void func_8003F900(Objeto* a0);
extern Vec3 D_80069DC0;

/*
 * Variables de datos pequenos: el original las direcciona con desplazamiento($gp). Este archivo es
 * el dueno de todas: D_800693E8 y D_800693EA son el cabeceo de la camara de apuntado, D_800693F4 la
 * cuenta del giro suavizado, D_800693F6 y D_800693F8 los contadores de espera, D_80069402 el giro
 * de la camara, D_80069408 el paso lateral (se guarda con sw y se lee con lhu), D_8006940C el
 * indicador de apuntado y D_80069416 el rumbo guardado.
 */
s16 D_800693E8;
s16 D_800693EA;
s16 D_800693F4;
s16 D_800693F6;
s16 D_800693F8;
s32 D_800693F0;
s16 D_80069402;
s32 D_80069408;
s16 D_8006940C;
u16 D_80069414;
u16 D_80069416;
s16 D_80069424;

/* Desplazamiento de una sonda de apuntado en x y z (16 bits con signo; se aplica la mitad): la tabla D_8005E728 trae ocho pares. */
typedef struct ParSonda {
    u16 x;
    u16 z;
} ParSonda;

extern ParSonda D_8005E728[];
/*
 * Vistas por direccion absoluta de campos de D_8006D928: D_8006D9B8[0] (declarada en globales.h) es
 * EstadoCamara.i90 (+0x90) y D_8006D990[3] es vista_68_x..vista_68_z (+0x68). El original usa ambos accesos (sw %lo(D_8006D9B8) en 0x80033574 frente a
 * sw zero 0x90($a1) en 0x80033600; lui/addiu %lo(D_8006D990) en 0x80034138 frente a sw 0x68($s0) en 0x80033DDC),
 * asi que no se unifican.
 */
extern s32 D_8006D990[3];
extern u32 D_80010008;


/* Envoltorio de rand() del SDK: la logica del juego pide aleatorios por aqui. */
s32 BugsRand(void)
{
    return rand();
}

/* Reinicia la camara y la sacudida al entrar en una escena. */
void func_80032894(void)
{
    Vec3 vp;
    Vec3 mira;

    GEO_CARGAR_W(&D_8006D928.vpx);
    GEO_GUARDAR_W_T1(&vp);
    GEO_CARGAR_W(&D_8006D928.x);
    GEO_GUARDAR_W_T1(&mira);
    D_80069414 = 0;
    func_8001CC68(&D_80069698->param.trans.vx);
    if (mira.x != 0) {
        D_8006D928.x = mira.x;
        D_8006D928.mira_a4_x = mira.x;
        D_8006D928.y = mira.y;
        D_8006D928.mira_a4_y = mira.y;
        D_8006D928.z = mira.z;
        D_8006D928.mira_a4_z = mira.z;
    }
    if (vp.x != 0) {
        D_8006D928.vpx = vp.x;
        D_8006D928.vista_68_x = vp.x;
        D_8006D928.vista_94_x = vp.x;
        D_8006D928.vista_b4_x = vp.x;
        D_8006D928.vpy = vp.y;
        D_8006D928.vista_68_y = vp.y;
        D_8006D928.vista_94_y = vp.y;
        D_8006D928.vista_b4_y = vp.y;
        D_8006D928.vpz = vp.z;
        D_8006D928.vista_68_z = vp.z;
        D_8006D928.vista_94_z = vp.z;
        D_8006D928.vista_b4_z = vp.z;
    }
    if (D_80069698 != NULL) {
        D_80069DC0.x = D_80069698->param.trans.vx;
        D_80069DC0.y = D_80069698->param.trans.vy;
        D_80069DC0.z = D_80069698->param.trans.vz;
    }
    D_8006D928.i90 = 0;
    D_8006D928.flags80 = 0x40;
    D_80069624 = -200;
    D_80069618 = 600;
    D_800693F6 = 0;
    D_800693F8 = 0;
    D_8006961C = 1100;
    D_800693F4 = 0;
    D_80010076 = 0;
    D_800693F0 = 1100;
    D_80069416 = 0;
    D_8006940C = 0;
}

/* Sacudida de la camara: oscila con seno y coseno y se amortigua. */
void func_80032A24(void)
{
    s32 r;
    s16 a;

    if (D_8006D928.s88 != 0) {
        D_8006D928.h8C = (rsin(D_8006D928.s8A) * D_8006D928.s88) >> 11;
        r = rcos(D_8006D928.s8A) * D_8006D928.s88;
        D_8006D928.x = D_8006D928.x + D_8006D928.h8C;
        D_8006D928.s8A = D_8006D928.s8A + D_8006D928.s86;
        D_8006D928.h8E = r >> 12;
        D_8006D928.y = D_8006D928.y + D_8006D928.h8E;
        a = D_8006D928.s8A;
        if (a >= 0x800) {
            if (D_8006D928.s88 >= 4) {
                D_8006D928.s88 = D_8006D928.s88 - 3;
            } else {
                D_8006D928.s88 = 0;
            }
        } else if (a >= 0x1000) {
            D_8006D928.s8A = a - 0x1000;
            if (D_8006D928.s88 >= 4) {
                D_8006D928.s88 = D_8006D928.s88 - 3;
            } else {
                D_8006D928.s88 = 0;
            }
        }
    } else {
        D_8006D928.h8C = 0;
        D_8006D928.h8E = 0;
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 30 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el
 * reparto de los registros coinciden; difiere solo el orden de dos cargas contiguas de la cadena de pruebas: el original
 * carga v28.vy (`lh a0,0x2a(s0)`, 0x80032E00) antes que max.vy (`lh a2,0x52(a1)`, 0x80032E04) y GCC las emite al reves.
 * La prueba se escribe `max.vy < v28.vy` y no `v28.vy > max.vy`: con la segunda max.vy se carga despues de v28.vy
 * (como el original) pero el valor pasa a 7 usos ponderados sobre 8 instrucciones (1,75), supera al objeto en curso
 * (pseudo 143, 14 usos sobre 25 instrucciones, 1,68) y los registros a1 y a2 se intercambian en toda la cadena de
 * pruebas (cifra 60); con `max.vy < v28.vy` la carga de max.vy se emite antes, su vida pasa a 9 instrucciones (1,56) y
 * el objeto en curso conserva a1, pero las dos cargas salen en el orden contrario; se supone, sin verificar, que la
 * segunda planificacion conserva el orden de emision de dos cargas de igual prioridad.
 *
 * El almacen de i58 va como primera sentencia del do/while de a48. Medido en el volcado de la primera planificacion
 * (`-dS`): la primera instruccion tras la nota de inicio de bucle depende de todo lo anterior y todo acceso a memoria
 * posterior depende de ella. Con el almacen antes del do/while la primera instruccion de la nota es la lectura del
 * objeto (una carga `lw 0x64` que la recarga convierte en `move v1,a1`) y queda despues del almacen; el original
 * coloca la copia (`move v1,a1`, 0x80032E2C) antes del almacen (`sw v0,0x58(s0)`, 0x80032E30). Con la resta de i58
 * dentro del do/while la primera instruccion tras la nota es la resta y la copia sale antes del almacen, como en el
 * original. Ampliar el tercer do/while para que cubra la lectura del objeto de RotMatrix no cambia los 14 usos del
 * pseudo 143: esa lectura es posterior a las llamadas y es otro pseudo.
 *
 * Los tres do/while (0) no generan codigo: ponderan por un nivel mas las referencias de su cuerpo para que la
 * prioridad de global-alloc ordene los punteros como el original (v28 en s3, rot en s4, a0 en s5, i58 en s6):
 * v28 pasa a 11 usos ponderados (0,146), rot a 6 (0,130) y a0 a 10 (0,122), todos por encima de i58 (0,106).
 * La forma del fuente original que producia este reparto se desconoce.
 *
 * Rayo de camara contra la lista de objetos solidos D_80069630: para cada objeto cuyos indicadores casan con la
 * mascara y cuya caja esta a menos de su alcance, lleva la posicion al sistema local del objeto, comprueba la caja
 * ensanchada por el radio y, si el punto cae sobre el objeto, desplaza el vector de salida a la cara mas cercana
 * (cuatro rectas de la caja segun el angulo ratan2) y lo devuelve al sistema global; retorna el objeto o 0.
 */
s32 func_80032B2C(Vec3* a0, Vec3* a1, RayoCamara* w, u32 mascara)
{
    s32* p58;
    SVECTOR* pd30;
    SVECTOR* prot;
    /* El original conserva el vector de salida en un registro salvado distinto del argumento:
     * la copia local reproduce ese reparto. */
    Vec3* salida;

    salida = a1;
    w->suma.vx = a0->x + salida->x;
    w->suma.vy = a0->y + salida->y;
    w->suma.vz = a0->z + salida->z;
    w->cur = D_80069630;
    if (w->cur != NULL) {
        p58 = &w->i58;
        pd30 = &w->d30;
        prot = &w->rot;
        do {
            if ((w->cur->flags08 & mascara) != 0) {
                GEO_CARGAR_WH(&w->cur->min);
                GEO_OR_WH(&w->cur->max);
                GEO_GUARDAR_1W_T1(p58);
                if (w->i58 != 0) {
                    GEO_CARGAR_W(&w->suma);
                    GEO_RESTAR_W(&w->cur->param.trans);
                    GEO_GUARDAR_H_T4(pd30);
                    GEO_NORMA2_XZ(pd30, p58);
                    if (w->cur->alcance2 >= (u32)w->i58) {
                        w->i60 = w->cur->radio;
                        GEO_COMPLEMENTO(&w->cur->param.giro.rotate);
                        do {
                            GEO_GUARDAR_H_T1(prot);
                        } while (0);
                        if (((w->cur->param.giro.rotate.vz + w->cur->param.giro.rotate.vx) & 0xFFF) == 0) {
                            if (((u16)w->cur->param.giro.rotate.vy & 0xFFF) == 0) {
                                GEO_CARGAR_WH(pd30);
                                GEO_GUARDAR_WH(&w->v28);
                            } else {
                                GEO_IDENTIDAD(w);
                                RotMatrixY(w->rot.vy, &w->m);
                                ApplyMatrixSV(&w->m, pd30, &w->v28);
                            }
                        } else {
                            RotMatrixZYX(prot, &w->m);
                            ApplyMatrixSV(&w->m, pd30, &w->v28);
                        }
                        if (w->v28.vx >= w->cur->min.vx - w->i60
                            && w->cur->max.vx + w->i60 >= w->v28.vx
                            && w->v28.vz >= w->cur->min.vz - w->i60
                            && w->cur->max.vz + w->i60 >= w->v28.vz
                            && w->cur->max.vy < w->v28.vy
                            && w->cur->min.vy >= w->v28.vy - 0xF0) {
                            /* Las tres escrituras de a48 son independientes; van en el orden x, z, y porque
                             * asi el almacen de cero baja a su sitio, como en el original. */
                            do {
                                w->i58 = w->cur->max.vy - w->v28.vy;
                                w->a48.vx =a0->x - w->cur->param.trans.vx;
                                w->a48.vz = a0->z - w->cur->param.trans.vz;
                                w->a48.vy = 0;
                                /* Aqui el original calcula la direccion de la rotacion con un addiu propio en
                                 * lugar de reutilizar el puntero local, que queda para las otras dos llamadas. */
                                RotMatrixZYX(&w->rot, &w->m);
                            } while (0);
                            ApplyMatrixSV(&w->m, &w->a48, &w->a50);
                            w->i5C = ratan2(w->a50.vx, w->a50.vz);
                            w->v28.vx = salida->x;
                            w->v28.vy = salida->y;
                            w->v28.vz = salida->z;
                            ApplyMatrixSV(&w->m, &w->v28, &w->v28);
                            w->i60 = w->i60 + 2;
                            if (w->i5C >= 0) {
                                if (w->i5C < ratan2(w->cur->max.vx + w->i60, w->cur->max.vz + w->i60)) {
                                    w->v28.vz = (u16)w->cur->max.vz + (u16)w->i60 - (u16)w->a50.vz;
                                } else if (w->i5C < ratan2(w->cur->max.vx + w->i60, w->cur->min.vz - w->i60)) {
                                    w->v28.vx = (u16)w->cur->max.vx + (u16)w->i60 - (u16)w->a50.vx;
                                } else {
                                    w->v28.vz = (u16)w->cur->min.vz - (u16)w->i60 - (u16)w->a50.vz;
                                }
                            } else {
                                w->i5C = -w->i5C;
                                if (w->i5C < -ratan2(w->cur->min.vx - w->i60, w->cur->max.vz + w->i60)) {
                                    w->v28.vz = (u16)w->cur->max.vz + (u16)w->i60 - (u16)w->a50.vz;
                                } else if (w->i5C < -ratan2(w->cur->min.vx - w->i60, w->cur->min.vz - w->i60)) {
                                    w->v28.vx = (u16)w->cur->min.vx - (u16)w->i60 - (u16)w->a50.vx;
                                } else {
                                    w->v28.vz = (u16)w->cur->min.vz - (u16)w->i60 - (u16)w->a50.vz;
                                }
                            }
                            RotMatrix(&w->cur->param.giro.rotate, &w->m);
                            do {
                                ApplyMatrixSV(&w->m, &w->v28, &w->v28);
                            } while (0);
                            salida->x = w->v28.vx;
                            salida->y = w->i58;
                            salida->z = w->v28.vz;
                            return (s32)w->cur;
                        }
                    }
                }
            }
            w->cur = w->cur->sig10;
        } while (w->cur != NULL);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_80032B2C);
#endif

/*
 * Busca un giro en Y para el que la sonda de colision avance libre: prueba hasta 25 giros de la
 * tabla D_8005E6F8 y guarda la distancia de cada uno en D_80069D90. Devuelve 0 si el giro
 * inicial sirve, 1 si sirve otro y 2 si ninguno (entonces elige el de mayor distancia).
 *
 * Reserva de pila: el original reserva 0x48 (`addiu sp` en 0x800330AC) y sin la local el marco es
 * 0x38; la cifra medida sin la local es 490 y con ella 0.
 */
s32 func_800330AC(Giro* a0, Vec3* a1, Vec3* a2, SondaCamara* arg)
{
    SondaCamara* w;
    s32 i;
    s32 k;
    s32 s1;
    s32 x;
    s32 z;
    s32* q;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[4];

    w = arg;
    q = &w->i68;
    w->pos.vx = a1->x;
    w->pos.vy = a1->y;
    w->pos.vz = a1->z;
    i = 0;
    w->dir.vx = (u16)a2->x;
    w->dir.vy = (u16)a2->y;
    w->dir.vz = (u16)a2->z;
    w->rot.vx = 0;
    w->rot.vz = 0;
    do {
        w->rot.vy = a0->y + D_8005E6F8[i];
        RotMatrix(&w->rot, &w->m);
        k = i;
        gte_SetRotMatrix(&w->m);
        gte_ldv0(&w->dir);
        gte_rtv0();
        gte_stlvnl(&w->res);
        w->pos.vy = a1->y;
        *q = 0;
        w->s5A = -1;
        s1 = w->res.vx + w->res.vz;
        BarrerTerreno(&w->pos, &w->res, &w->pad50, q);
        x = w->res.vx;
        z = w->res.vz;
        s1 = s1 - (x + z);
        D_80069D90[i] = SquareRoot0(x * x + z * z);
        if ((w->f52 & 4) == 0 && s1 == 0) {
            break;
        }
        i++;
    } while (k < 0x18);
    GEO_CARGAR_W(&w->res);
    GEO_GUARDAR_W_T1(a2);
    a0->y = D_8005E6F8[i];
    if (i < 0x18) {
        if (i != 0) {
            return 1;
        }
    } else {
        i = 0;
        s1 = 0;
        do {
            w->dir.vx = 0;
            if (s1 < D_80069D90[i]) {
                s1 = D_80069D90[i];
                w->dir.vx = i;
            }
            i++;
        } while (i < 0x18);
        a0->y = D_8005E6F8[w->dir.vx];
        return 2;
    }
    return 0;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 555 con la configuracion versionada (g = 8 del archivo; ejes 127 de operandos, 0 de lineas
 * reordenadas y 218 de lineas insertadas o borradas). El flujo, las macros vectoriales y las constantes coinciden.
 * Residuo: en el bloque del giro por boton `g` y `pulsado` salen con los registros intercambiados (el original tiene
 * `g` en a2 y `pulsado` en a1; ver el ultimo tramo de esta nota). El resto de diferencias es de forma simbolica, sin
 * diferencia de bytes: los accesos por `$gp` del original frente al simbolo y las dos lecturas del byte de pausa, que
 * salen como `D_8006AA70+0xc`. Ese byte se nombra en toda la funcion como miembro del banco (`D_8006AA70[0xC]`,
 * como en el prologo de func_800353B0): con el simbolo suelto cambia el reparto de la prueba de los dos bits de la
 * direccion del ajuste de altura.
 *
 * Razones de la escritura, con desplazamientos desde 0x80033358. La resta `i = n - 10` del final de la funcion se
 * escribe antes de la prueba de zonas: el original la calcula en el hueco de retardo del primer `beq`
 * (`addiu s0,s1,-0xa` en 0x80034D94); escrita dentro de la prueba la cifra es 675. En los bucles de las ocho sondas
 * (modo de apuntado y seguimiento libre) `i++` va despues de la llamada a BarrerTerreno porque el original emite el
 * incremento del contador y del puntero despues de preparar los argumentos (0x498 y 0x49c). En el bloque de las
 * posiciones de la camara (0x17b0..0x1868) los tres almacenes de `v30` van tras el de `vpz`, en el orden `vx`, `vy`,
 * `vz`. En la prueba de los dos bits de la direccion (0xba0..0xbb8) la bandera enmascarada es el primer operando del
 * `or`. El par de modificaciones de banderas del giro (0xcc4..0xd30) coincide en el orden (almacen de
 * las banderas, carga del contador `D_80069402`, constante del paso) con las envolturas `do { } while (0);` que
 * describe la cabecera de la funcion.
 * El resultado de la raiz de la distancia (0x1324..0x13a8) se guarda en una variable propia, `raiz`, que se asigna
 * una sola vez y de la que salen el cociente y el resto (`i = raiz / 200`, `d = raiz - i * 200`): el copiado
 * `move s1,v0` queda tras los argumentos, como en el original (con la raiz guardada en `d` la cifra es 810). Se
 * supone, sin verificar con el volcado de planificacion, que una variable de una sola asignacion se hunde hasta su
 * primer consumidor y una de dos asignaciones queda donde esta escrita. El cuadrado de la velocidad
 * (0x15b8..0x15c4) relee `v90.vx` como el original porque el almacen de `flags80` va ANTES de calcular el cuadrado
 * (la relectura la provoca el almacen intermedio a un global que el CSE no distingue de `w->v90`). El bloque de
 * alturas usa `ec` y `vp` locales de cada copia (ver su comentario). El valor de 16 bits que el original guarda en
 * registros distintos segun la zona (el giro hacia el
 * objeto de seguimiento, `a0` en 0xc14; el giro por boton, `v0`; la cuenta del giro suavizado, `v1` en 0xeb0; el rumbo)
 * se guarda en cuatro variables, `cgiro`, `c`, `cuenta` y `crumbo`: con una sola variable la cuenta del giro tomaba
 * `a0` en 0xeb0 (se supone, sin verificar, que una variable que abarca las cuatro zonas suma las referencias de
 * todas y por eso toma el mismo registro en todas). La direccion de
 * acercamiento (0x990..0x9c4) coincide al leer `w->dist` en los tres productos. La prueba del giro tras el
 * bloque de la cuenta de espera (0xed4..0xfd8) coincide con una sola cola `w->rot.vy = D_80069402` y dos
 * `goto`, como el original.
 *
 * Reparto de `g` y `pulsado` (el residuo): con el orden de instrucciones del original `g` cuenta 7 usos sobre 30
 * instrucciones (0,467), por encima de `pulsado` (4 usos sobre 18, 0,444), y `g` toma `a1` y `pulsado` `a2`, al
 * reves que el original. Se supone, sin verificar, que el original tiene una referencia ponderada mas sobre
 * `pulsado`. La forma del fuente original que producia este reparto se desconoce.
 */
/*
 * Acerca la altura del punto de vista a la banda [base - 0x64, base + 0x64] desplazada por p4: si queda por encima
 * del limite inferior de la banda se mueve un octavo hacia el, y si queda por debajo del superior, hacia el otro.
 * El original repite el bloque entero en cada rama de la eleccion de `base`; llaves simples para que cada copia
 * sea un unico bloque basico. La direccion de la camara (`ec`) y la copia de la altura (`vp`) son locales de cada
 * copia y `vp` se asigna una sola vez: el original carga `vp` (`lw v1,4(a3)`, 0x80034C48) despues de la base y de
 * `w->p4` (`lw a0,0xe8(s4)` y `lw a2,0xc4(s3)`, 0x80034C40 y 0x80034C44), y escrita como variable de la funcion,
 * compartida por las tres copias y asignada tres veces, la carga de `vp` salia la primera (se supone, sin
 * verificar con el volcado de planificacion, que una variable de una sola asignacion se carga junto a su primer
 * consumidor). Con `ec` compartida el volcado de reparto (`.lreg`) daba 12 usos ponderados sobre 57 instrucciones
 * (0,62), por encima de `w->p4` (3 usos sobre 7, 0,43), y `ec` tomaba `a2` y `w->p4` `a3`, al reves que el original;
 * con `ec` local de cada copia son 4 usos sobre 38 instrucciones (0,21), `w->p4` toma `a2` y `ec` `a3`. Las tres
 * copias reciben los mismos registros y el compilador sigue fundiendo la cola comun (`sra`, `addu`, `sw` en
 * 0x80034CDC) y la segunda mitad de la comprobacion (desde `subu` en 0x80034CCC): el tamano de la funcion no cambia.
 */
#define ALTURA_CAMARA(base) \
    { \
        s32 t1; \
        s32 t2; \
        s32 techo; \
        s32 piso; \
        s32 vp; \
        EstadoCamara* ec; \
        ec = &D_8006D928; \
        vp = ec->vpy; \
        techo = (base) + 0x64; \
        t1 = techo - w->p4; \
        if (t1 < vp) { \
            ec->vpy = vp + ((t1 - vp) >> 3); \
        } else { \
            piso = (base) - 0x64; \
            t2 = piso - w->p4; \
            if (vp < t2) { \
                ec->vpy = vp + ((t2 - vp) >> 3); \
            } \
        } \
    }

/*
 * Camara de seguimiento de tercera persona, una vez por cuadro. Determina la zona bajo el objeto y bajo la
 * camara y actualiza el modelo de la sala; despues atiende, por prioridad, la cuenta atras de cambio de
 * zona, la camara bloqueada por un evento, el modo de apuntado (ocho sondas contra el terreno y los objetos
 * solidos), la transicion guiada (banderas 0xC00) y el seguimiento libre (giro por boton, distancia, rayo
 * por tramos contra los objetos y alturas contra el terreno). `reiniciar` suprime el suavizado.
 *
 * Las tres envolturas `do { } while (0);` del giro por boton no generan codigo (el ensamblador tiene las mismas
 * instrucciones con y sin cada una): la nota de inicio de bucle que deja el analizador limita lo que el
 * planificador reordena, y la primera instruccion que la sigue pasa a depender de las anteriores. `c` es el pseudo
 * 97 y el almacen de las banderas es el `sh` a `0x80` del puntero a la camara.
 * (1) Carga `c = D_80069402;` de la rama del paso 0x26. Volcado `-dS`: sin la envoltura la carga no tiene ninguna
 * dependencia y se emite por encima del `ori` de las banderas (pseudo 925 = `g | 0x82`) y de su `sh`; con ella
 * depende del `ori`, tiene una antidependencia con el `sh` y queda detras, como en el original (875 sin ella). En
 * `.greg` cambian con ella `c`, de a0 a v0, y `g` y `pulsado` (pseudos 106 y 107), de a2 y a1 a a1 y a2.
 * (2) La misma carga en la rama del paso -0x26: sin la envoltura sube por encima del `ori` (pseudo 944) y del `sh`;
 * con ella queda detras con las mismas dos dependencias (855 sin ella; 1160 sin las envolturas 1 y 2). En `.greg`
 * cambian con ella `c`, de a0 a v0, el puntero a la camara (pseudo 926), de a2 a a0, y la lectura de las banderas
 * (pseudo 936), de a1 a v1.
 * (3) Almacen `D_80069408 = k;` de la cola comun. El orden de `-dS` es el mismo con y sin la envoltura; el que
 * cambia es el de `-dR`: sin ella la suma `c + k` (`addu v0,v0,v1`, pseudo 946) se emite por encima del `sw` de `k`
 * (`sw v1,D_80069408`), porque las dos solo leen v1 y no hay dependencia entre ellas; con ella la suma tiene una
 * antidependencia con el `sw` y queda detras, como en el original (620 sin ella). `.greg` no cambia.
 * Con las tres la cifra es 555. La forma del fuente original que producia este reparto se desconoce.
 */
void ActualizarCamaraSeguimiento(Objeto* o, u32 reiniciar)
{
    s32 i;
    s32 k;
    TrabajoCamara* w;
    void* area;
    ZonaColision* zona;
    ZonaColision* z2;
    u16* zp;
    EstadoCamara* cam;
    EstadoPrincipal* e;
    s32 n;
    s32 ang;
    s32 d;
    s32 raiz;
    s32 hit;
    s32 r;
    u16 c;
    u16 cgiro;
    u16 cuenta;
    u16 crumbo;
    u16 c8;
    u16 c6;
    u16 f;
    u16 f1;
    u16 f2;
    s32 g;
    u16 pulsado;
    s32 pos_x;

    if (o == NULL) {
        return;
    }
    area = (void*)0x1F8000F8;
    w = (TrabajoCamara*)0x1F800000;
    zona = func_8001BF9C((s32*)&o->param.trans.vx, (s16)o->w26);
    w->zona_ant = zona;
    if (zona != NULL) {
        D_80069698->w26 = zona->grupo;
        D_80069558 = (u16*)w->zona_ant;
    } else {
        D_80069558 = NULL;
    }
    z2 = func_8001BF9C(&D_8006D928.vpx, -1);
    w->zona_ant = z2;
    if (z2 == NULL) {
        z2 = (ZonaColision*)D_80069558;
    }
    D_800695B8 = (u16*)z2;
    /*
     * Relectura forzosa: el original almacena el resultado con sw en 0x80033408 y lo vuelve a cargar con lw
     * de la misma direccion en 0x80033410, sin ningun almacen entre ambas, en lugar de reutilizar el registro.
     */
    zp = *(u16* volatile*)&D_800695B8;
    if (zp != NULL) {
        D_800694DC->u78.modelos = D_8006B568[*zp];
        D_800694DC->w28 = *(u16*)((u8*)D_800694DC->u78.modelos + 0xB6);
        D_800694DC->w26 = *zp;
    }
    D_80069608 = D_80069608 & ~2;
    if (o->u78.p == NULL) {
        return;
    }
    if (D_80069DC0.x != o->param.trans.vx || D_80069DC0.y != o->param.trans.vy
        || D_80069DC0.z != o->param.trans.vz) {
        reiniciar = 1;
    }
    D_80069DC0.x = o->param.trans.vx;
    D_80069DC0.y = o->param.trans.vy;
    D_80069DC0.z = o->param.trans.vz;
    if (o->clase == 0xE) {
        reiniciar = 1;
    }
    cam = &D_8006D928;
    if ((*(u32*)&cam->flags80 & 0x340) == 0x40) {
        c8 = D_800693F8;
        if (D_800693F8 < 10) {
            reiniciar = 1;
            D_800693F8 = c8 + 1;
        } else {
            cam->flags80 = cam->flags80 & 0xFFBF;
        }
    }
    c6 = D_800693F6;
    if (D_800693F6 != 0) {
        D_800693F6 = c6 - 1;
        o->flags14 = o->flags14 | 0x80000000;
        D_8006D9B8[0] = NULL;
        func_80032A24();
        return;
    }
    if (D_8006D9B8[0] != NULL) {
        if (D_8006D9B8[0]->registro184 != NULL) {
            if ((*(u32*)((u8*)D_8006D9B8[0]->registro184 + 0x10) & 0x200) != 0) {
                o = D_8006D9B8[0];
                o->flags14 = o->flags14 | 0x80000000;
            }
        }
    }
    if ((D_8006D928.flags80 & 0x300) != 0) {
        o->flags14 = o->flags14 | 0x80000000;
        D_800693F8 = 0;
        D_8006D928.i90 = 0;
        D_8006D928.flags80 = D_8006D928.flags80 | 0x40;
        func_80032A24();
        return;
    }
    w->p8 = D_80069624;
    w->p4 = D_80069618;
    w->p0 = D_8006961C;
    if ((o->flags14 & 0x1000000) != 0) {
        w->p0 = 0x1F4;
    }
    e = ESTADO_PRINCIPAL;
    if ((e->mando.botones_a & 0x10) != 0 && D_80069690 == 0 && (o->flags14 & 0x1015609) == 0
        && (o->flags18 & 4) == 0 && (D_8006D928.flags80 & 0x2000) == 0 && D_8006AA70[0xC] == 0
        && ((o->flags14 & 0x10000000) == 0 || reiniciar == 0) && e->r[BANCO_PAUSA] == 0
        && (D_8006D928.flags80 & 0x10) == 0) {
        o->flags14 = o->flags14 | 0x80000000;
        w->v90.vz = 0;
        w->v90.vy = 0;
        w->v90.vx = 0;
        i = 0;
        do {
            w->v30.vx = o->param.trans.vx;
            w->v30.vy = o->param.trans.vy + w->p8;
            w->v30.vz = o->param.trans.vz;
            w->v70.vx = (s16)D_8005E728[i].x >> 1;
            w->v70.vy = 0;
            w->v70.vz = (s16)D_8005E728[i].z >> 1;
            hit = func_80032B2C((Vec3*)&w->v30, (Vec3*)&w->v70, area, 0x24000);
            if (hit == 0) {
                w->v70.vx = w->v70.vx + ((s16)D_8005E728[i].x >> 1);
                w->v70.vy = 0;
                w->v70.vz = w->v70.vz + ((s16)D_8005E728[i].z >> 1);
                func_80032B2C((Vec3*)&w->v30, (Vec3*)&w->v70, area, 0x24000);
            }
            w->v30.vy = o->param.trans.vy + w->p8;
            w->res.grupo = -1;
            BarrerTerreno(&w->v30, &w->v70, &w->res, area);
            i++;
            w->v90.vx = w->v90.vx + w->v70.vx;
            w->v90.vz = w->v90.vz + w->v70.vz;
        } while (i < 8);
        w->v90.vx = (w->v90.vx * 3000) >> 12;
        w->v90.vz = (w->v90.vz * 3000) >> 12;
        if (D_8006940C == 0 || reiniciar != 0) {
            if ((w->v90.vx | w->v90.vz) != 0 && reiniciar == 0) {
                D_8006D928.x = o->param.trans.vx + w->v90.vx;
                D_8006D928.y = o->param.trans.vy - 400;
                D_8006940C = 1;
                D_8006D928.z = o->param.trans.vz + w->v90.vz;
            } else {
                D_8006D928.x = D_8006D928.x + ((o->param.trans.vx + w->v90.vx - D_8006D928.x) >> 2);
                {
                    s32 t;
                    t = D_8006D928.y + 400;
                    D_8006D928.y = D_8006D928.y + ((o->param.trans.vy - t) >> 2);
                }
                D_8006D928.z = D_8006D928.z + ((o->param.trans.vz + w->v90.vz - D_8006D928.z) >> 2);
            }
        }
        w->local.vx = 0;
        w->local.vy = 0;
        w->local.vz = -150;
        D_800693E8 = D_800693E8 + (((s16)ESTADO_PRINCIPAL->mando.eje_y * 5) >> 4);
        D_800693EA = D_800693EA + (((s16)ESTADO_PRINCIPAL->mando.eje_x * 5) >> 4);
        if (D_800693EA < -0x14A) {
            D_800693EA = -0x14A;
        }
        if (D_800693EA > 0x14A) {
            D_800693EA = 0x14A;
        }
        if (D_800693E8 < -0x14A) {
            D_800693E8 = -0x14A;
        }
        if (D_800693E8 > 0x14A) {
            D_800693E8 = 0x14A;
        }
        w->dist = D_800693EA + o->param.giro.rotate.vy;
        GEO_IDENTIDAD(&w->m);
        RotMatrixX(D_800693E8, &w->m);
        RotMatrixY(w->dist, &w->m);
        ApplyMatrix(&w->m, &w->local, &w->v50);
        D_8006D928.vpx = D_8006D928.vpx + ((D_8006D928.x + w->v50.vx - D_8006D928.vpx) >> 1);
        D_8006D928.vpy = D_8006D928.vpy + ((D_8006D928.y - w->v50.vy - D_8006D928.vpy) >> 1);
        D_8006D928.vpz = D_8006D928.vpz + ((D_8006D928.z + w->v50.vz - D_8006D928.vpz) >> 1);
        func_80032A24();
        D_80069608 = D_80069608 | 2;
        return;
    }
    f = D_8006D928.flags80;
    g = f & 0xFFEF;
    D_800693EA = 0;
    D_800693E8 = 0;
    D_8006940C = 0;
    D_80069608 = D_80069608 & ~2;
    D_8006D928.flags80 = g;
    if ((f & 0xC00) != 0) {
        if ((f & 0x800) != 0) {
            D_8006D928.x = D_8006D928.x - ((D_8006D928.x - D_8006D928.destino_mira_x) >> 2);
            D_8006D928.y = D_8006D928.y - ((D_8006D928.y - D_8006D928.destino_mira_y) >> 2);
            D_8006D928.z = D_8006D928.z - ((D_8006D928.z - D_8006D928.destino_mira_z) >> 2);
        } else {
            D_8006D928.x = D_8006D928.x - ((D_8006D928.x - o->param.trans.vx) >> 2);
            {
                s32 t;
                t = D_8006D928.y + 400;
                D_8006D928.y = D_8006D928.y - ((t - o->param.trans.vy) >> 2);
            }
            D_8006D928.z = D_8006D928.z - ((D_8006D928.z - o->param.trans.vz) >> 2);
        }
        if ((D_8006D928.flags80 & 0x1000) != 0) {
            w->local.vx = (u16)D_8006D928.destino_vista_x - (u16)D_8006D928.x;
            w->local.vy = (u16)D_8006D928.destino_vista_y - (u16)D_8006D928.y;
            w->local.vz = (u16)D_8006D928.destino_vista_z - (u16)D_8006D928.z;
            w->dist = SquareRoot0(w->local.vx * w->local.vx + w->local.vy * w->local.vy
                                  + w->local.vz * w->local.vz);
            if (w->dist == 0) {
                w->dist = 1;
            }
            w->v18.vx = (w->local.vx << 12) / w->dist;
            w->v18.vy = (w->local.vy << 12) / w->dist;
            w->v18.vz = (w->local.vz << 12) / w->dist;
            w->dist = D_8006D928.distancia_acercamiento;
            D_8006D928.destino_vista_x = D_8006D928.x + ((w->v18.vx * w->dist) >> 12);
            D_8006D928.destino_vista_y = D_8006D928.y + ((w->v18.vy * w->dist) >> 12);
            D_8006D928.destino_vista_z = D_8006D928.z + ((w->v18.vz * w->dist) >> 12);
        }
        f1 = D_8006D928.flags80;
        if ((f1 & 0x400) != 0) {
            D_8006D928.vpx = D_8006D928.vpx - ((D_8006D928.vpx - D_8006D928.destino_vista_x) >> 2);
            D_8006D928.vpy = D_8006D928.vpy - ((D_8006D928.vpy - D_8006D928.destino_vista_y) >> 2);
            D_8006D928.vpz = D_8006D928.vpz - ((D_8006D928.vpz - D_8006D928.destino_vista_z) >> 2);
        }
        if ((f1 & 0x4000) != 0) {
            D_8006D928.vista_68_x = D_8006D928.vpx;
            D_8006D928.vista_94_x = D_8006D928.vpx;
            D_8006D928.vista_b4_x = D_8006D928.vpx;
            D_8006D928.vista_68_y = D_8006D928.vpy;
            D_8006D928.vista_94_y = D_8006D928.vpy;
            D_8006D928.vista_b4_y = D_8006D928.vpy;
            D_8006D928.vista_68_z = D_8006D928.vpz;
            D_8006D928.vista_94_z = D_8006D928.vpz;
            D_8006D928.vista_b4_z = D_8006D928.vpz;
            D_8006D928.mira_a4_x = D_8006D928.x;
            D_8006D928.mira_a4_y = D_8006D928.y;
            D_8006D928.mira_a4_z = D_8006D928.z;
        }
        if ((f1 & 8) != 0) {
            D_8006D928.flags80 = f1 & 0xA3F7;
        }
        GEO_CARGAR_W(&D_8006D928);
        GEO_RESTAR_W(D_8006D934);
        GEO_GUARDAR_H_T4(w);
        D_80069402 = D_80069416 = ratan2(w->local.vx, w->local.vz);
        D_800693F0 = SquareRoot0(w->local.vx * w->local.vx + w->local.vz * w->local.vz) + 1;
        D_800693F4 = 0x3C;
        D_800693F8 = 0;
        D_8006D928.flags80 = D_8006D928.flags80 | 0x40;
        func_80032A24();
        return;
    }
    g = g & 0xA3E7;
    D_8006D928.flags80 = g;
    D_80069408 = 0;
    pulsado = D_8001000A;
    /* Mismo byte que D_8006AA7C, leido como miembro del banco D_8006AA70 igual que en el prologo de func_800353B0. */
    if ((pulsado & 4) == 0 && ((o->flags14 & 0x1000000) | D_8006AA70[0xC]) == 0) {
        if (D_8006D928.i90 != 0) {
            w->v70.vx = o->param.trans.vx - D_8006D928.i90->param.trans.vx;
            w->v70.vz = o->param.trans.vz - D_8006D928.i90->param.trans.vz;
            i = ratan2(w->v70.vx, w->v70.vz);
            if (i < 0) {
                i = i + 0x1000;
            }
            cgiro = D_80069402;
            r = (s16)(D_80069402 % 0x1000);
            if (r < 0) {
                r = r + 0x1000;
            }
            i = i - r;
            if (i < 0) {
                i = i + 0x1000;
            }
            if (i > 0x800) {
                i = i - 0x1000;
            }
            D_80069402 = cgiro + (i >> 4);
            D_8006D928.flags80 = D_8006D928.flags80 | 2;
            if (D_8006961C < 0x5DC) {
                w->p0 = 0x5DC;
            } else {
                w->p0 = D_8006961C;
            }
            D_8006D9B8[0] = NULL;
        } else {
            if ((pulsado & 1) != 0 && (pulsado & 2) == 0 && (g & 0x8000) == 0) {
                D_8006D928.flags80 = g | 0x82;
                do {
                    c = D_80069402;
                } while (0);
                k = 0x26;
                goto aplicar_giro;
            }
            if (D_8006D928.i90 == 0 && (D_80010008 & 0x30000) == 0x20000
                && ((s16)D_8006D928.flags80 & 0x8000) == 0) {
                D_8006D928.flags80 = D_8006D928.flags80 | 0x82;
                do {
                    c = D_80069402;
                } while (0);
                k = -0x26;
aplicar_giro:
                do {
                    D_80069408 = k;
                } while (0);
                D_80069402 = c + k;
            } else if (reiniciar != 0) {
                D_8006D928.flags80 = D_8006D928.flags80 & 0xFFFD;
            }
        }
    }
    D_80069402 = D_80069402 % 0x1000;
    D_8006D928.vista_68_x = D_8006D928.vista_b4_x;
    D_8006D928.vista_68_y = D_8006D928.vista_b4_y;
    D_8006D928.vista_68_z = D_8006D928.vista_b4_z;
    D_8006D928.x = D_8006D928.mira_a4_x;
    D_8006D928.y = D_8006D928.mira_a4_y;
    D_8006D928.z = D_8006D928.mira_a4_z;
    D_8006D928.vpx = D_8006D928.vista_94_x;
    D_8006D928.vpy = D_8006D928.vista_94_y;
    D_8006D928.vpz = D_8006D928.vista_94_z;
    GEO_CERO_WH(&w->v90);
    GEO_CARGAR_W(D_8006D990);
    GEO_RESTAR_W(&o->param.trans);
    GEO_GUARDAR_H_T4(w);
    i = w->local.vx * w->local.vx + w->local.vz * w->local.vz;
    w->rot.vx = 0;
    w->rot.vz = 0;
    if (i != 0) {
        w->dist = SquareRoot0(i) + 1;
        w->rot.vy = ratan2(w->local.vx, w->local.vz);
    } else {
        w->dist = 0x64;
        w->rot.vy = o->param.giro.u.y - 0x800;
    }
    if (reiniciar != 0) {
        D_800693F4 = 0x3C;
    }
    cuenta = D_800693F4;
    if (D_800693F4 > 0) {
        D_800693F4 = cuenta - 1;
    }
    f2 = D_8006D928.flags80;
    if ((f2 & 2) == 0) {
        if (D_800693F4 == 0 || reiniciar != 0) {
            ang = o->param.giro.rotate.vy + 0x800;
            i = ang % 0x1000;
            if (i < 0) {
                i = i + 0x1000;
            }
            crumbo = w->rot.vy;
            r = (s16)((s16)crumbo % 0x1000);
            if (r < 0) {
                r = r + 0x1000;
            }
            i = i - r;
            if (i < 0) {
                i = i + 0x1000;
            }
            if (i > 0x800) {
                i = i - 0x1000;
            }
            i = (i * 30) >> 11;
            if (i != 0) {
                w->rot.vy = crumbo + i;
            } else {
                D_8006D928.flags80 = f2 | 2;
            }
        }
        if ((D_8006D9A8[0] & 2) == 0) {
            goto guardar_giro;
        }
    }
    /*
     * Una sola copia de la lectura del giro, alcanzada por dos caminos: la prueba de f2 antes del bloque
     * (el original salta a ella con `bnez` en 0x8003422C hacia 0x80034318, sin recalcular el bit) y el final
     * del bloque cuando el byte D_8006D9A8 lo tiene (`beqz` en 0x80034310 hacia la escritura contraria, que
     * queda tras la lectura). `f2` es el valor de las banderas previo al bloque: el bloque escribe
     * `D_8006D928.flags80` sin actualizarlo, de modo que la cola compartida es equivalente a la condicion
     * compuesta en las cuatro combinaciones de `f2 & 2` y del byte (con `f2 & 2` activo se salta el bloque y se
     * llega a la lectura igual que con el byte activo; con ambos inactivos el bloque termina en `guardar_giro`).
     * Escrito como `if ((f2 & 2) != 0 || byte) {...} else {...}` el compilador vuelve a calcular `f2 & 2` en la union y emite una prueba de mas por cada camino del bloque.
     */
    w->rot.vy = D_80069402;
    goto fin_giro;
guardar_giro:
    D_80069402 = w->rot.vy;
fin_giro:
    w->dir.vy = 0;
    w->dir.vx = 0;
    w->dir.vz = w->dist;
    RotMatrix(&w->rot, &w->m);
    ApplyMatrix(&w->m, &w->dir, &w->v30);
    w->v70.vx = o->param.trans.vx;
    w->v70.vy = o->param.trans.vy - 0x1F4;
    w->v70.vz = o->param.trans.vz;
    if ((o->flags14 & 0x16) == 0) {
        w->v70.vy = o->param.trans.vy;
        w->res.grupo = -1;
        func_8001C134((s32*)&w->v70.vx, &w->res, area);
        w->zona_ant = w->res.zona;
        w->v70.vy = o->param.trans.vy - 0x1F4;
        func_8001C134((s32*)&w->v70.vx, &w->res, area);
        if (w->zona_ant != w->res.zona && (w->res.flags & 6) != 0 && (s16)w->res.grupo != -1) {
            w->v70.vy = w->res.zona->y_max + 0x1F4;
            if (o->param.trans.vy < w->v70.vy) {
                w->v70.vy = o->param.trans.vy;
            }
        } else {
            w->v70.vy = o->param.trans.vy - 0x1F4;
        }
    }
    w->res.grupo = -1;
    w->alt = w->v70.vy;
    w->v40.vx = w->v30.vx;
    w->v40.vy = w->v30.vy;
    w->v40.vz = w->v30.vz;
    BarrerTerreno(&w->v70, &w->v30, &w->res, area);
    D_8006D928.vista_68_x = o->param.trans.vx + w->v30.vx;
    D_8006D928.vista_68_z = o->param.trans.vz + w->v30.vz;
    w->dist = SquareRoot0(w->v30.vx * w->v30.vx + w->v30.vz * w->v30.vz) | 1;
    w->rot.vy = ratan2(w->v30.vx, w->v30.vz);
    if ((D_8006D928.flags80 & 2) == 0) {
        w->v30.vy = 0;
        w->v30.vx = 0;
        w->v30.vz = w->dist;
        /*
         * El original carga la posicion x del objeto (`lw v1,0xE4(s4)`, 0x8003453C) junto con la altura
         * del punto de vista, antes del primer almacen a `v70` (0x80034540); sin la local el
         * planificador la carga tras ese almacen y la cifra sube de 555 a 1065.
         */
        pos_x = o->param.trans.vx;
        w->v70.vy = D_8006D928.vpy;
        w->v70.vx = pos_x;
        w->v70.vz = o->param.trans.vz;
        GEO_CARGAR_WH(&w->rot);
        GEO_GUARDAR_WH(&w->rot28);
        func_800330AC(&w->rot28, (Vec3*)&w->v70, (Vec3*)&w->v30, area);
        w->rot.vy = w->rot.vy + ((s16)w->rot28.y >> 2);
    }
    if (w->dist < w->p0 - 0x64) {
        s32 t;
        t = w->dist + 0x64;
        w->dist = w->dist + ((w->p0 - t) >> 3);
    }
    if (w->p0 + 0x64 < w->dist) {
        s32 t;
        t = w->dist - 0x64;
        w->dist = w->dist + ((w->p0 - t) >> 1);
    }
    w->dir.vy = 0;
    w->dir.vx = 0;
    w->dir.vz = w->dist;
    RotMatrixZYX(&w->rot, &w->m);
    ApplyMatrix(&w->m, &w->dir, &w->v30);
    w->v70.vx = o->param.trans.vx;
    w->v70.vy = w->alt;
    w->v70.vz = o->param.trans.vz;
    w->res.grupo = -1;
    BarrerTerreno(&w->v70, &w->v30, &w->res, area);
    raiz = SquareRoot0(w->v30.vx * w->v30.vx + w->v30.vz * w->v30.vz);
    w->dir.vy = 0;
    w->dir.vx = 0;
    w->dir.vz = 200;
    ApplyMatrix(&w->m, &w->dir, &w->v40);
    GEO_CERO_W(&w->v50);
    i = raiz / 200;
    if (i >= 0) {
        d = raiz - i * 200;
        for (;;) {
            w->v70.vy = o->param.trans.vy - 0x1F4;
            if (i == 0) {
                w->dir.vz = d;
                ApplyMatrix(&w->m, &w->dir, &w->v40);
            }
            hit = func_80032B2C((Vec3*)&w->v70, (Vec3*)&w->v40, area, 0x20000);
            i--;
            w->v50.vx = w->v50.vx + w->v40.vx;
            w->v50.vz = w->v50.vz + w->v40.vz;
            w->v70.vx = w->v70.vx + w->v40.vx;
            w->v70.vz = w->v70.vz + w->v40.vz;
            if (i < 0 || hit != 0) {
                break;
            }
        }
    }
    GEO_CARGAR_W(&w->v50);
    GEO_GUARDAR_W_T1(&w->v30);
    i = 0;
    D_8006D928.vista_68_x = o->param.trans.vx + w->v30.vx;
    D_8006D928.vista_68_z = o->param.trans.vz + w->v30.vz;
    w->v90.vz = 0;
    w->v90.vy = 0;
    w->v90.vx = 0;
    w->v30.vy = o->param.trans.vy - 0x1F4;
    do {
        GEO_CARGAR_W(D_8006D990);
        GEO_GUARDAR_W_T1(&w->v30);
        w->v70.vx = (s16)D_8005E728[i].x >> 1;
        w->v70.vy = 0;
        w->v70.vz = (s16)D_8005E728[i].z >> 1;
        w->v30.vy = o->param.trans.vy - 0xC8;
        hit = func_80032B2C((Vec3*)&w->v30, (Vec3*)&w->v70, area, 0x20000);
        if (hit == 0) {
            w->v70.vx = w->v70.vx + ((s16)D_8005E728[i].x >> 1);
            w->v70.vy = 0;
            w->v70.vz = w->v70.vz + ((s16)D_8005E728[i].z >> 1);
            func_80032B2C((Vec3*)&w->v30, (Vec3*)&w->v70, area, 0x20000);
        }
        w->res.grupo = -1;
        w->v30.vy = w->alt;
        BarrerTerreno(&w->v30, &w->v70, &w->res, area);
        i++;
        w->v90.vx = w->v90.vx + w->v70.vx;
        w->v90.vz = w->v90.vz + w->v70.vz;
    } while (i < 8);
    if (reiniciar == 0 && (w->v90.vx | w->v90.vz) != 0) {
        D_8006D928.flags80 = D_8006D928.flags80 | 2;
        d = w->v90.vx * w->v90.vx + w->v90.vz * w->v90.vz;
        if (SquareRoot0(d) >= 0x1F5) {
            D_80069402 = (u16)D_80069402 - (u16)D_80069408;
        }
    }
    w->v90.vx = w->v90.vx >> 2;
    w->v90.vz = w->v90.vz >> 2;
    D_8006D928.vista_68_x = D_8006D928.vista_68_x + w->v90.vx;
    D_8006D928.vista_68_z = D_8006D928.vista_68_z + w->v90.vz;
    GEO_CARGAR_W(D_8006D990);
    GEO_RESTAR_W(&o->param.trans);
    GEO_GUARDAR_H_T4(w);
    w->dist = SquareRoot0(w->local.vx * w->local.vx + w->local.vz * w->local.vz) + 1;
    w->rot.vy = ratan2(w->local.vx, w->local.vz);
    w->rot.vz = 0;
    w->rot.vx = 0;
    if (reiniciar != 0 || (D_8006D928.flags80 & 0xC0) != 0) {
        D_800693F0 = w->dist;
        D_80069416 = w->rot.vy;
    } else {
        w->dist = D_800693F0;
        w->rot.vy = D_80069416;
    }
    w->dir.vy = 0;
    w->dir.vx = 0;
    w->dir.vz = w->dist;
    RotMatrix(&w->rot, &w->m);
    ApplyMatrix(&w->m, &w->dir, &w->v18);
    D_8006D928.vista_68_x = o->param.trans.vx + w->v18.vx;
    D_8006D928.vista_68_z = o->param.trans.vz + w->v18.vz;
    w->dir.vz = w->dist + 0x190;
    ApplyMatrix(&w->m, &w->dir, &w->v18);
    D_8006D928.x = D_8006D928.x + ((o->param.trans.vx - D_8006D928.x) >> 2);
    D_8006D928.y = D_8006D928.y + ((o->param.trans.vy + w->p8 - D_8006D928.y) >> 2);
    D_8006D928.z = D_8006D928.z + ((o->param.trans.vz - D_8006D928.z) >> 2);
    D_8006D928.vpx = D_8006D928.vpx + ((o->param.trans.vx + w->v18.vx - D_8006D928.vpx) >> 2);
    D_8006D928.vpz = D_8006D928.vpz + ((o->param.trans.vz + w->v18.vz - D_8006D928.vpz) >> 2);
    w->v30.vx = D_8006D928.vista_68_x;
    w->v30.vy = w->alt;
    w->v30.vz = D_8006D928.vista_68_z;
    w->res.grupo = -1;
    func_8001C134((s32*)&w->v30.vx, &w->res, area);
    if ((w->res.flags & 8) != 0 && w->res.suelo < o->param.trans.vy) {
        w->res.grupo = -1;
        w->v30.vy = w->v30.vy + 1;
        func_8001C134((s32*)&w->v30.vx, &w->res, area);
    }
    if ((w->res.flags & 4) != 0 || (s16)w->res.grupo == -1) {
        ALTURA_CAMARA(o->param.trans.vy);
    } else if (o->param.trans.vy < w->res.suelo) {
        ALTURA_CAMARA(o->param.trans.vy);
    } else {
        ALTURA_CAMARA(w->res.suelo);
    }
    D_8006D928.mira_a4_x = D_8006D928.x;
    D_8006D928.mira_a4_y = D_8006D928.y;
    D_8006D928.mira_a4_z = D_8006D928.z;
    D_8006D928.vista_94_x = D_8006D928.vpx;
    D_8006D928.vista_94_y = D_8006D928.vpy;
    D_8006D928.vista_68_y = D_8006D928.vpy;
    D_8006D928.vista_94_z = D_8006D928.vpz;
    w->v30.vx = D_8006D928.vpx;
    w->v30.vy = D_8006D928.vpy;
    w->v30.vz = D_8006D928.vpz;
    w->res.grupo = -1;
    func_8001C134((s32*)&w->v30.vx, &w->res, area);
    w->res.grupo = -1;
    w->v30.vy = D_8006D928.vpy - 0x258;
    w->zona_ant = w->res.zona;
    n = w->res.suelo;
    func_8001C134((s32*)&w->v30.vx, &w->res, area);
    i = n - 10;
    if (w->zona_ant != w->res.zona && (w->res.flags & 6) != 0 && (s16)w->res.grupo != -1) {
        if (w->res.zona->y_max >= n - 0x262) {
            D_8006D928.vpy = D_8006D928.vpy + ((i - D_8006D928.vpy) >> 3);
        } else {
            s32 t;
            t = D_8006D928.vpy - 0x258;
            D_8006D928.vpy = D_8006D928.vpy + ((w->res.zona->y_max - t) >> 3);
        }
        D_8006D928.vista_94_y = D_8006D928.vpy;
        D_8006D928.vista_68_y = D_8006D928.vpy;
    }
    D_8006D928.vista_b4_x = D_8006D928.vista_68_x;
    D_8006D928.vista_b4_y = D_8006D928.vista_68_y;
    D_8006D928.vista_b4_z = D_8006D928.vista_68_z;
    func_80032A24();
    D_8006D928.flags80 = D_8006D928.flags80 & 0xFF7F;
}
#undef ALTURA_CAMARA
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", ActualizarCamaraSeguimiento);
#endif

/* Al dar de baja un objeto, libera a los que lo tenian como padre (p70) y deshace los enlaces cruzados. */
void func_80034E7C(Objeto* o)
{
    Objeto* p;
    Objeto* sig;
    Objeto* a;

    if ((o->flags18 & 0x800) != 0) {
        p = D_80069518;
        if (p != NULL) {
            do {
                if (p->p70 == o) {
                    if ((p->flags18 & 0x400) != 0) {
                        a = p->p6C;
                        if (a != NULL && (a->flags18 & 0x400) == 0) {
                            a->flags14 &= ~0x814;
                            p->p6C->flags14 |= 0x1000;
                            p->p6C->coord.super = NULL;
                            p->p6C->coord.param = PARAMETROS_SDK(p->p6C);
                            p->p6C->w26 = p->w26;
                            p->p6C->p70 = NULL;
                            func_8001CF50(p->p6C);
                            a = p->p6C;
                            if (a->clase == 0xE) {
                                a->trabajo.i14 = 0;
                            }
                        }
                        sig = p->siguiente;
                        ClearList((NodoLista*)&p->u78.ayudas);
                        D_80069518 = (Objeto*)RemoveListNode((NodoLista*)D_80069518, (NodoLista*)p);
                        func_8003F900(p);
                        func_80034E7C(p);
                        p = sig;
                        continue;
                    }
                    p->coord.param = PARAMETROS_SDK(p);
                    p->coord.super = NULL;
                    p->p70 = NULL;
                    p->flags14 = (p->flags14 & ~0x14) | 0x1202;
                    func_8001CFCC(&p->coord);
                }
                if (p->p6C == o) {
                    p->p6C = NULL;
                }
                p = p->siguiente;
            } while (p != NULL);
        }
    }
}

/* Da de baja un objeto de escena: lo suelta de sus enlaces, de la lista solida y de la lista de objetos. */
void func_8003502C(Objeto* o)
{
    Objeto* p;
    Objeto* v;

    if (o == D_80069560) {
        D_80069560 = D_80069698;
    }
    if (D_80069698->p6C == o) {
        D_80069698->p6C = NULL;
    }
    p = o->p70;
    if (p != NULL) {
        if (p->p6C == o) {
            p->p6C = NULL;
        }
        o->p70 = NULL;
    }
    if (o->p6C != NULL) {
        o->p6C->flags14 &= ~0x814;
        o->p6C->coord.super = NULL;
        o->p6C->coord.param = PARAMETROS_SDK(o->p6C);
        o->p6C->w26 = o->w26;
        o->p6C->p70 = NULL;
        func_8001CF50(o->p6C);
        o->p6C->trabajo.i14 = 0;
        o->p6C = NULL;
    }
    if (o == D_80069630) {
        D_80069630 = o->sig10;
    } else {
        v = D_80069630;
        while (v != NULL && v->sig10 != o) {
            v = v->sig10;
        }
        if (v != NULL) {
            v->sig10 = o->sig10;
        }
    }
    ClearList((NodoLista*)&o->u78.ayudas);
    D_80069518 = (Objeto*)RemoveListNode((NodoLista*)D_80069518, (NodoLista*)o);
    func_8003F900(o);
    func_80034E7C(o);
}

/* Prepara un objeto para su baja: limpia banderas y suelta la lista enlazada si ya no la usa nadie. */
void func_800351B4(Objeto* o)
{
    o->flags04 &= ~2;
    o->flags18 |= 0x100;
    if ((o->flags08 & 0x1000) != 0) {
        if ((o->trabajo.flags18 & 0x4000) == 0) {
            if (o->u78.ayudas != NULL) {
                if (o->p70 == NULL) {
                    o->trabajo.flags18 |= 0x4000;
                    o->trabajo.i14 = 0;
                    ClearList((NodoLista*)&o->u78.ayudas);
                    o->u78.ayudas = NULL;
                }
            }
        }
    }
}

/*
 * Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron respecto al cuadro anterior (dato pequeno
 * 0x104($gp)), avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas);
 * al completar una ejecuta su caso con un switch de siete entradas.
 */
void func_80035244(void)
{
    s32 i;
    s32 estado;
    Secuencia* e;

    estado = D_80010010;
    estado &= 0xFFF6;
    if (D_80069424 != estado) {
        D_80069424 = estado;
        if (estado != 0) {
            i = 0;
            e = D_8005E768;
            while (i < 7) {
                if (e->teclas[e->paso] == estado) {
                    e->paso = e->paso + 1;
                    if (e->teclas[e->paso] == 0) {
                        switch (e->caso) {
                        case 0:
                            ESTADO_PRINCIPAL->r[0x24] |= 1;
                            break;
                        case 1:
                            ESTADO_PRINCIPAL->r[0x03] = 0x63;
                            ESTADO_PRINCIPAL->r[0x24] |= 2;
                            break;
                        case 2:
                            ESTADO_PRINCIPAL->r[0x08] |= 0x1F;
                            ESTADO_PRINCIPAL->r[0x24] |= 4;
                            break;
                        case 3:
                            ESTADO_PRINCIPAL->r[0x01] = 6;
                            ESTADO_PRINCIPAL->r[0x24] |= 8;
                            break;
                        case 4:
                            ESTADO_PRINCIPAL->r[0x08] |= 0x80;
                            ESTADO_PRINCIPAL->r[0x24] |= 0x10;
                            break;
                        case 5:
                            ESTADO_PRINCIPAL->r[0x07] = 0x4D;
                            ESTADO_PRINCIPAL->r[0xFC] = 1;
                            ESTADO_PRINCIPAL->r[0x05] = 0x7C;
                            /* Las dos sentencias finales se repiten en el caso 6 en lugar de caer en el: con una sola
                             * copia las constantes 0x47 y 1 tienen un unico uso y el optimizador de bucles las deja
                             * dentro de la rama; con dos usos las saca del bucle, como el original, y el compilador
                             * vuelve a unir las colas identicas. */
                            ESTADO_PRINCIPAL->nivel = 0x47;
                            D_80069662 = 1;
                            break;
                        case 6:
                            ESTADO_PRINCIPAL->nivel = 0x47;
                            D_80069662 = 1;
                            break;
                        }
                    }
                } else {
                    e->paso = 0;
                }
                /* El puntero avanza antes que el contador, como en el original. */
                e++;
                i++;
            }
        }
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 235 con la configuracion versionada (g = 8 del archivo): 93 diferencias de operando, 0 lineas
 * reordenadas y 88 insertadas o borradas. El flujo coincide. Quedan diferencias de registros y de forma simbolica:
 * (1) un puntero del contexto GTE en t7 y el original en a3 (la mayor parte de las diferencias); (2) el byte
 * D_8006AA7C que el original lee por el simbolo y aqui sale como `D_8006AA70+0xc`, y las direcciones del
 * scratchpad que el desensamblado del original nombra como simbolos (los mismos bytes).
 *
 * La atenuacion sigue el flujo del original: el original tiene una sola llamada a func_800351B4 (0x800358A4) y la
 * atenuacion por distancia y la de proyeccion saltan a ella tras recargar el objeto en `a0` (0x80035DCC), con la
 * `jal` en el sitio de la busqueda del modelo. Aqui las dos atenuaciones comparten la recarga (`recargar`, con la
 * asignacion de `t` desde `sc->cur` tras el almacen) y saltan a la llamada de la busqueda del modelo (`llamar`).
 *
 * Copias de `t`. El puntero al objeto en curso se copia en la local `t` con `t = sc->cur;` escrita cinco veces:
 * antes de las pruebas de la bandera 0x10000 de la busqueda del modelo, en `modelo_hallado`, tras la proyeccion de
 * un objeto simple, en `tras_proyeccion` (proyeccion de volumen) y en `recargar`. Es la sentencia duplicada en
 * caminos que se reunen (en `llamar` y en las pruebas de `atenuar`): una sola copia tras la union serviria
 * igual, pero el original carga `sc->cur` en `a0` en cada camino (0x8003584C y 0x80035888 en la busqueda del
 * modelo) y las copias no generan codigo mas alla de esa carga, que el original tambien tiene. Con una sola
 * asignacion en cada punto de reunion la cifra es 745 (una tras `atenuar` en lugar de las dos copias de las
 * proyecciones) y 500 (una tras `llamar` en lugar de las otras tres). La etiqueta `tras_proyeccion` va despues de
 * su copia: el salto desde la proyeccion simple llega con el objeto ya en `a0`, como el `j` de 0x80035A54, que
 * salta la carga y entra en 0x80035D8C (con la etiqueta antes de la copia la cifra es 240).
 * Volcado de `cc1` (`-dl` y `-dg`, `-G8`): `t` es un solo pseudo de usuario (84) con cinco asignaciones, las cinco
 * cargas de `sc->cur`, 30 usos sobre 31 insns, sin cruzar llamadas y con preferencia por `a0` (es el argumento de
 * `func_800351B4`): prioridad 3,871, quinto del orden del reparto global, y toma `a0`, como el original en
 * 0x8003584C, 0x80035888, 0x80035A24, 0x80035D88 y 0x80035DCC. La forma del fuente original que producia este
 * reparto se desconoce.
 *
 * La cola de la lista usa una local propia (`cola`) porque `t` vive en varios bloques y pasa por el reparto global.
 *
 * Envoltura `do { } while (0)`: rodea la comparacion `if (idx < lim) goto buscar_modelo;` de la busqueda
 * del modelo y no genera codigo (el optimizador de saltos la elimina). Causa medida (volcado `-dl`, `-dg`, `-G8`):
 * el limite `lim` (pseudo 93, 14 instrucciones de vida) pasa de 4 a 5 usos ponderados y su prioridad de
 * 2 * 4 / 14 = 0,571 a 2 * 5 / 14 = 0,714, por delante del puntero al objeto `busca` (pseudo 94, 4 usos sobre 13
 * instrucciones, 2 * 4 / 13 = 0,615); el orden de asignacion los invierte y el limite toma `a1` y el puntero `a2`,
 * como el original, en lugar de `a2` y `a1` (sin la envoltura la cifra es 255 y con ella 235). La forma del fuente
 * original que producia este reparto se desconoce.
 *
 * Par `pz--; pz++;` antes de la sentencia `GUARDAR_MAC3(pz);` del recorrido de proyeccion de los ocho puntos (el
 * segundo, con `sc->i40 < 8`): no genera codigo (el combinador anula el par y el ensamblador tiene las mismas
 * instrucciones que sin el). Causa medida (volcado `-dl`, `-dg`, `-G8`): el par suma cuatro referencias ponderadas
 * por la profundidad del bucle, de modo que el puntero `pz` (pseudo 89, 393 instrucciones de vida y 394 con el par)
 * pasa de 6 a 18 usos y su prioridad de 2 * 6 / 393 = 0,031 a 4 * 18 / 394 = 0,183, por delante de la constante
 * -3 (pseudo 90, 3 * 11 / 792 = 0,042) y del puntero a `sx` (pseudo 88, 2 * 6 / 395 = 0,030); el orden de
 * asignacion pasa a ser `pz` en s2, constante en s3 y `sx` en s4, que es el del original (`addiu s2` en
 * 0x80035540 y `addiu s4` en 0x8003553C, con -3 en s3). Sin el par la cifra es 280 y con el 235. La forma del
 * fuente original que producia este reparto se desconoce.
 *
 * El puntero de la matriz de rotacion del prologo (insn 91 del volcado de cc1, la macro de SetRotMatrix) lo
 * asigna el reparto global a `a0` y la recarga lo mueve despues a `t7` ("Spilling reg 15" para esa insn en el
 * volcado de la recarga); el original lo tiene en `a3`. Se supone, sin verificar, que la recarga evita `a3` porque
 * la lista de destruidos de las macros de distancia aproximada declara `$7`; el cuerpo lo escribe
 * (`addu $7,$10,$0`), de modo que la lista completa se conserva. La busqueda del
 * modelo copia el limite (`lim`) en una local propia dentro del bloque, como el original, que rellena con esa copia
 * el hueco del `beqz` de la primera comparacion (`addu a1,v1,zero` en 0x800357D4); sin `lim` la cifra es 375.
 *
 * La prueba de la bandera del modelo (`sc->i40 < D_80069588`) va dentro del bloque que entra en la busqueda: el
 * `beqz` de la primera comparacion (0x800357D0) salta a la prueba de indice no hallado (0x80035870), no a la de la
 * bandera (0x80035814). Con ella fuera del bloque el salto iba a esa segunda prueba y el hueco quedaba con un `nop`
 * (340 en lugar de 235). Con la entrada hallada se comprueba el bit 1 de la bandera y el bit 0x10000 de las
 * banderas del objeto, y sin el bit 1 se cae a la misma comparacion de indice que la rama de no hallado
 * (0x80035824 a 0x80035878).
 *
 * El bucle final copia el objeto en curso a `o` una sola vez, tras las rutinas de logica y antes de avanzar a la
 * lista siguiente: el original tiene `move a0,s0` en los huecos de retardo de los saltos al final del cuerpo
 * (0x800360B8 y 0x800360D4), no una copia viva durante las llamadas; y la direccion de la camara se
 * asigna dentro del cuerpo, despues de la llamada, para que el optimizador de bucles saque las tres direcciones en
 * el orden del original (D_8006AA70, D_8005E35C, D_8006D928). Con la asignacion antes del bucle la
 * direccion de la camara se calcula antes de las otras dos; sin variable (el simbolo en el cuerpo) no se iza.
 *
 * La distancia aproximada usa GEO_DISTANCIA_APROX_A con la base y el destino del propio vector (desplazamiento
 * 0x44): es la misma rutina manuscrita. La forma sin sufijo escribe un `nop` explicito en el hueco de la primera y
 * la tercera `bgez` y su `.set noreorder` va con un espacio, que maspsx no reconoce (solo `.set<tab>noreorder`):
 * maspsx sigue en modo de reordenacion y anade otro `nop` tras esas dos saltos (medido sobre una copia del bloque:
 * 2 `nop` anadidos con el espacio, 0 con el tabulador, y quitando los dos `nop` explicitos sale `bgez; nop; sub`
 * como el original). Arreglar
 * `GEO_DISTANCIA_APROX` exigiria cambiar la macro compartida, que no se toca aqui. La forma con sufijo depende del
 * espaciado de la directiva de la macro: si `maspsx` llegara a reconocer `.set noreorder` con espacio, se supone, sin
 * verificar, que el `sub` pasaria al hueco de la `bgez` y se invertiria el signo del valor absoluto.
 *
 * La busqueda del modelo guarda el indice leido en la condicion (`idx`) y lo reutiliza en el incremento, como el
 * original (`lw a0,0x40(s1)` en 0x800357B8 y `addiu v0,a0,1` en 0x800357F0 del original), en lugar de leer el
 * campo otra vez. La direccion del scratchpad se asigna despues de la llamada a la camara y no al
 * principio: con la asignacion inicial el compilador la calcula en el hueco de retardo del primer salto y
 * desplaza el resto del prologo; el original calcula `lui s1,0x1f80` mas tarde.
 *
 * Los dos recorridos de la rama de volumen (los nodos de coordenadas y la busqueda del modelo) se escriben con
 * salto hacia atras en lugar de `do { } while`: con el bucle natural el optimizador de bucles saca de ambos la
 * direccion de v80 y la de c104 (en el volcado de bucles, regno 367 y 368 "moved", y despues otra vez fuera del
 * recorrido principal con vida de 51 y 52 instrucciones), ocupan s5 y s6 y el marco sube de 0x28 a 0x30; el
 * original calcula esas direcciones en el sitio. El volcado confirma el efecto; se supone, sin verificar, que el
 * original tampoco tenia notas de bucle en esos dos recorridos. El resultado de la ultima comprobacion de
 * proyeccion se lee de los campos (sc->sx, sc->sy) donde el original los relee, no de locales.
 *
 * Lista de comprobaciones del cuadro: recorre los objetos de escena, los clasifica en cuatro listas
 * (segun sus indicadores) con la memoria de trabajo del scratchpad en 0x1F800000, los vuelve a enlazar en
 * D_80069630 y ejecuta la rutina de logica de cada uno (tabla D_8005E35C).
 */
void func_800353B0(Objeto* a0)
{
    Scratch* sc;
    Objeto* o;
    Objeto* s0;
    Objeto* t;
    Objeto* cola;
    GsCOORDINATE2* n;
    s32 r;
    s16* psx;
    s32* pz;
    s32 m3;
    s32 nmod;
    s32 idx;
    s32 lim;
    Objeto* busca;
    EstadoCamara* cam;

    D_80069652 = 0;
    D_800694D4 = D_800694B8;
    /* Mismo byte que D_8006AA7C, leido como miembro del banco D_8006AA70 en el prologo y en el bucle final. */
    if (D_8006AA70[0xC] == 0) {
        if (D_80069560 != 0) {
            ActualizarCamaraSeguimiento(D_80069560, D_80069698->reiniciar_camara);
        }
    }
    sc = (Scratch*)0x1F800000;
    func_80035244();
    sc->m18 = D_8006D928.x - D_8006D928.vpx;
    sc->m20 = D_8006D928.z - D_8006D928.vpz;
    sc->r74 = ratan2(sc->m18, sc->m20);
    gte_SetRotMatrix(&D_80076130);
    gte_SetTransVector(&D_80076144);
    if (D_80069698 != NULL && (D_8006D928.vpx + D_8006D928.vpy + D_8006D928.vpz) == 0) {
        sc->m18 = D_80069698->param.trans.vx;
        sc->m1C = D_80069698->param.trans.vy;
        sc->m20 = D_80069698->param.trans.vz;
    } else {
        sc->m18 = D_8006D928.vpx;
        sc->m1C = D_8006D928.vpy;
        sc->m20 = D_8006D928.vpz;
    }
    sc->l30 = NULL;
    sc->l34 = NULL;
    sc->l38 = NULL;
    sc->i70 = 0;
    D_80069630 = NULL;
    sc->cur = a0;
    if (a0 != NULL) {
        m3 = -3;
        psx = &sc->sx;
        pz = &sc->z6C;
        do {
            if ((sc->cur->flags14 & 0x100) != 0) {
                s0 = sc->cur->siguiente;
                func_8003502C(sc->cur);
                if (s0 == NULL) {
                    goto fin;
                }
                sc->cur = s0;
            }
            if (sc->cur->w24 != 0) {
                sc->cur->w24 = sc->cur->w24 - 1;
            }
            if ((sc->cur->flags0C & 0x40) != 0) {
                goto siguiente;
            }
            sc->cur->flags04 |= 2;
            sc->cur->flags18 &= ~0x100;
            if ((sc->cur->flags04 & 0x20) == 0 && sc->cur->w1C != 5 && sc->cur->clase != 0x14
                && sc->cur->p70 != D_80069698 && sc->cur->p6C != D_80069698 && sc->cur->w3C != 0) {
                if ((sc->cur->w3C & 2) != 0) {
                    sc->d0 = sc->m18 - sc->cur->param.trans.vx;
                    sc->d4 = sc->m1C - sc->cur->param.trans.vy;
                    sc->d8 = sc->m20 - sc->cur->param.trans.vz;
                    GEO_DISTANCIA_APROX_A(sc, sc, 0x44);
                    if (sc->cur->w3E < sc->i44) {
                        if ((sc->cur->w3C & 0x40) == 0) {
                            sc->cur->w24 = (sc->i44 - sc->cur->w3E) >> 7;
                            goto recargar;
                        }
                        sc->cur->flags04 &= m3;
                        sc->cur->flags18 |= 0x100;
                    }
                }
                if ((sc->cur->w3C & 1) != 0 && (sc->cur->flags04 & 2) != 0) {
                    sc->i40 = 0;
                    sc->tp3C = D_8006A940;
                    nmod = D_80069588;
                    idx = sc->i40;
                    if (idx < nmod) {
                        lim = nmod;
                        busca = sc->cur;
buscar_modelo:
                        if ((s16)busca->w26 != sc->tp3C->modelo) {
                            sc->i40 = idx + 1;
                            sc->tp3C++;
                            idx = sc->i40;
                            do {
                                if (idx < lim) {
                                    goto buscar_modelo;
                                }
                            } while (0);
                        }
                        if (sc->i40 < D_80069588) {
                            if ((sc->tp3C->bandera & 1) != 0) {
                                /* Sentencia replicada: es la misma que la de las otras ramas. */
                                t = sc->cur;
                                if ((t->flags08 & 0x10000) != 0) {
                                    goto sigue2;
                                }
                                goto modelo_hallado;
                            }
                        }
                    }
                    if (D_80069588 != sc->i40) {
                        goto sigue2;
                    }
modelo_hallado:
                    /* Sentencia replicada: es la misma que la de las otras ramas. */
                    t = sc->cur;
                    if ((t->w3C & 0x40) == 0) {
llamar:
                        func_800351B4(t);
                        goto siguiente;
                    }
                    sc->cur->flags04 &= m3;
                    sc->cur->flags18 |= 0x100;
                }
sigue2:
                if ((sc->cur->w3C & 0x20) != 0 && (sc->cur->flags04 & 2) != 0) {
                    if (sc->cur->u78.p == NULL && (sc->cur->flags18 & 0x80) == 0) {
                        sc->p10.vx = sc->cur->param.trans.vx;
                        sc->p10.vy = sc->cur->param.trans.vy;
                        sc->p10.vz = sc->cur->param.trans.vz;
                        gte_ldv0(&sc->p10);
                        gte_rtps();
                        gte_stsxy(psx);
                        GUARDAR_MAC3(pz);
                        if (sc->z6C < 0 || sc->sx + sc->cur->w2E < -0x100 || sc->sx - sc->cur->w2E > 0x100
                            || sc->sy < -0x78 || sc->sy + sc->cur->max.vy >= 0x79) {
                            sc->cur->flags04 &= m3;
                            sc->cur->flags18 |= 0x100;
                        }
                        /* Sentencia replicada: es la misma que la de las otras ramas. */
                        t = sc->cur;
                        if ((t->flags04 & 2) == 0) {
                            if ((t->w3C & 0xC0) == 0) {
                                goto atenuar;
                            }
                            goto tras_proyeccion;
                        }
                    } else {
                        sc->c104[0].vx = sc->c104[2].vx = sc->c104[4].vx = sc->c104[6].vx = sc->cur->min.vx;
                        sc->c104[1].vx = sc->c104[3].vx = sc->c104[5].vx = sc->c104[7].vx = sc->cur->max.vx;
                        sc->c104[0].vy = sc->c104[1].vy = sc->c104[2].vy = sc->c104[3].vy = sc->cur->max.vy;
                        sc->c104[4].vy = sc->c104[5].vy = sc->c104[6].vy = sc->c104[7].vy = sc->cur->min.vy;
                        sc->c104[0].vz = sc->c104[1].vz = sc->c104[4].vz = sc->c104[5].vz = sc->cur->max.vz;
                        sc->c104[2].vz = sc->c104[3].vz = sc->c104[6].vz = sc->c104[7].vz = sc->cur->min.vz;
                        sc->n78 = &sc->cur->coord;
                        if (sc->n78 != NULL) {
otro_nodo:
                            n = sc->n78;
                            gte_SetRotMatrix(&n->coord);
                            sc->d0 = n->coord.t[0];
                            sc->d4 = n->coord.t[1];
                            r = n->coord.t[2];
                            sc->i40 = 0;
                            sc->p100 = sc->v80;
                            sc->p144 = sc->c104;
                            sc->d8 = r;
                            while (sc->i40 < 8) {
                                gte_ldv0(sc->p144);
                                gte_rtv0();
                                gte_stlvnl(sc->p100);
                                GEO_CARGAR_W(sc);
                                GEO_SUMAR_W(sc->p100);
                                GEO_CARGAR_W(sc->p100);
                                GEO_GUARDAR_H_T1(sc->p144);
                                sc->i40++;
                                sc->p100++;
                                sc->p144++;
                            }
                            sc->n78 = sc->n78->super;
                            if (sc->n78 != NULL) {
                                goto otro_nodo;
                            }
                        }
                        gte_SetRotMatrix(&D_80076130);
                        sc->i40 = 0;
                        sc->p144 = sc->c104;
                        while (sc->i40 < 8) {
                            gte_ldv0(sc->p144);
                            gte_rtps();
                            gte_stsxy(psx);
                            pz--;
                            pz++;
                            GUARDAR_MAC3(pz);
                            if (sc->z6C >= 0 && (u16)(sc->sx + 0x100) < 0x201 && sc->sy >= -0x78 && sc->sy < 0x79) {
                                break;
                            }
                            sc->i40++;
                            sc->p144++;
                        }
                        if (sc->i40 == 8) {
                            sc->cur->flags04 &= m3;
                            sc->cur->flags18 |= 0x100;
                        }
                        /* Sentencia replicada: es la misma que la de las otras ramas. */
                        t = sc->cur;
tras_proyeccion:
                        if ((t->flags04 & 2) == 0 && (t->w3C & 0xC0) == 0) {
atenuar:
                            t->w24 = (0x400 - sc->i40) >> 7;
recargar:
                            /* Sentencia replicada: es la misma que la de las otras ramas. */
                            t = sc->cur;
                            goto llamar;
                        }
                    }
                }
            }
            if (sc->cur->clase == 0x10 || sc->cur->clase == 0x24) {
                sc->cur->flags04 &= m3;
                sc->cur->flags18 |= 0x100;
            }
            if (sc->cur->clase == 0x15) {
                sc->cur->sig10 = sc->l34;
                sc->l34 = sc->cur;
            } else if ((sc->cur->flags08 & 0x20000) != 0) {
                sc->cur->sig10 = sc->l30;
                sc->l30 = sc->cur;
            } else if ((sc->cur->flags08 & 8) != 0) {
                sc->cur->sig10 = sc->l38;
                sc->l38 = sc->cur;
            } else if (sc->cur->w1C == 1) {
                D_80069698 = sc->cur;
            } else {
                sc->cur->sig10 = D_80069630;
                D_80069630 = sc->cur;
            }
siguiente:
            sc->cur = sc->cur->siguiente;
        } while (sc->cur != NULL);
    }
fin:
    if (D_80069698 != NULL) {
        cola = D_80069630;
        D_80069630 = D_80069698;
        (D_80069698)->sig10 = cola;
    }
    if (sc->l38 != NULL) {
        sc->cur = sc->l38;
        while (sc->cur->sig10 != NULL) {
            sc->cur = sc->cur->sig10;
        }
        sc->cur->sig10 = D_80069630;
        D_80069630 = sc->l38;
    }
    if (sc->l30 != NULL) {
        sc->cur = sc->l30;
        while (sc->cur->sig10 != NULL) {
            sc->cur = sc->cur->sig10;
        }
        sc->cur->sig10 = D_80069630;
        D_80069630 = sc->l30;
    }
    if (sc->l34 != NULL) {
        sc->l34->sig10 = D_80069630;
        D_80069630 = sc->l34;
    }
    s0 = D_80069630;
    D_800695D0 = 0;
    D_800695EC = 0;
    D_80069560 = D_80069698;
    if (s0 != NULL) {
        do {
            /* Mismo byte que D_8006AA7C, leido como miembro del banco D_8006AA70 igual que en el prologo. */
            if (D_8006AA70[0xC] == 0) {
                if ((s0->flags14 & 0x100) == 0) {
                    D_8005E35C[s0->clase](s0);
                }
                cam = &D_8006D928;
                if ((*(u32*)&cam->flags80 & 0x300) != 0x100 || s0->clase == 0x20 || (s0->flags18 & 0x1000) != 0) {
                    s0->w22++;
                }
            } else if ((s0->flags14 & 0x100) == 0 && (s0->flags0C & 0x40000000) != 0) {
                D_8005E35C[s0->clase](s0);
                s0->w22++;
            }
            o = s0;
            s0 = s0->sig10;
            if ((o->flags14 & 0x100) != 0) {
                func_8003502C(o);
            }
        } while (s0 != NULL);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/camara_y_bucle_logico", func_800353B0);
#endif
