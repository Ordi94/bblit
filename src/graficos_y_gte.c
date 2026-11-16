#include "geometria.h"
#include "globales.h"
#include "gte.h"
#include "psyq/GTEMAC.H"


/*
 * Area de trabajo de las consultas de segmento (func_80017478 y func_80018664): matriz inversa del
 * objeto candidato, matriz del objeto que se mueve, vectores locales, cuatro vertices mas un centro
 * de la caja barrida y los angulos de las esquinas del candidato vistas desde su centro.
 */
typedef struct ConsultaSondeo {
    MATRIX m;
    MATRIX m2;
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
    VECTOR destino;
    SVECTOR sal;
    s16 e_x;
    s16 pad72;
    s16 e_z;
    s16 pad76;
    u32 caja;
    s32 ang;
    s32 radio;
    s16 s84;
    s16 s86;
    Objeto* actual;
    Objeto* cadena;
    Objeto* a;
    Objeto* b;
    SVECTOR p[5];
    SVECTOR* pt;
    u32 dist2;
    s16 angs[4];
} ConsultaSondeo;


/* Esquinas del barrido y punto de prueba como pares (z, x) de 16 bits; func_80017478 las usa para elegir la arista mas cercana. */
typedef struct ParZX {
    s16 z;
    s16 x;
} ParZX;
extern ParZX D_80069D18[5];
extern VECTOR D_80069D08;
extern VECTOR D_80069C08;

/* Dato pequeno: el original lo direcciona como 0x60($gp) (area con signo mas baja de las aristas probadas). */
s32 D_80069380;

#define U16_2E(o) (*(u16*)((u8*)(o) + 0x2E))

/* Cabeza de la lista de nodos de plano (enlace en +0). */

/*
 * Busca el primer objeto solido cuyo volumen contiene a la caja del objeto a: el candidato se
 * lleva al sistema local del otro objeto con la inversa de sus angulos y se compara con su caja
 * ampliada por el radio. mascara filtra por indicadores; o es el area de trabajo.
 *
 * La matriz se asigna a una variable que vale 0 antes del bucle y se vuelve a asignar dentro: con una sola
 * asignacion el optimizador de bucles saca &o->m fuera del bucle, y el original lo calcula en cada vuelta.
 * El puntero de destino de la norma al cuadrado queda en a0, como en el original, porque GEO_NORMA2_XZ
 * declara v0 y v1 como destruidos.
 */
Objeto* func_80016C0C(Objeto* a, u32 mascara, ConsultaVolumen* o)
{
    SVECTOR* dif;
    SVECTOR* rot;
    MATRIX* m;

    o->actual = D_80069630;
    if (o->actual != 0) {
        dif = &o->dif;
        rot = &o->rot;
        m = 0;
        do {
            if ((o->actual->flags08 & mascara) && o->actual->tipo_volumen == 2 && a != o->actual
                && a->p70 != o->actual && a->p6C != o->actual && o->actual->p70 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->caja);
                if (o->caja != 0) {
                    GEO_CARGAR_W(&a->param.trans);
                    GEO_RESTAR_W(&o->actual->param.trans);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &o->dist2);
                    if (o->actual->alcance2 >= o->dist2) {
                        o->radio = o->actual->radio;
                        GEO_COMPLEMENTO(&o->actual->param.giro.rotate);
                        GEO_GUARDAR_H_T1(rot);
                        m = &o->m;
                        RotMatrixZYX(rot, m);
                        ApplyMatrixSV(m, dif, &o->res);
                        if (o->res.vx >= o->actual->min.vx - o->radio
                            && o->res.vx <= o->actual->max.vx + o->radio
                            && o->res.vz >= o->actual->min.vz - o->radio
                            && o->res.vz <= o->actual->max.vz + o->radio
                            && o->res.vy + a->min.vy >= o->actual->max.vy
                            && o->actual->min.vy >= o->res.vy + a->max.vy) {
                            return o->actual;
                        }
                    }
                }
            }
            o->actual = o->actual->sig10;
        } while (o->actual != 0);
    }
    return 0;
}

/*
 * Variante de func_80016C0C que copia antes del bucle la posicion y la caja del objeto a al
 * area de trabajo y compara contra esas copias; devuelve el primer objeto solido que la
 * contiene.
 * Con g = 8 (config/opciones_compilacion.toml) el puntero global se carga directamente en $s0;
 * con -G0 la parte alta iria a otro registro (230).
 */
Objeto* func_80016ED0(Objeto* a, u32 mascara, ConsultaCaja* o)
{
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    RotMatrixZYX(&o->rot, &o->m);
    GEO_CARGAR_W(&a->param.trans);
    GEO_GUARDAR_W_T1(&o->pos);
    GEO_CARGAR_WH(&a->min);
    GEO_GUARDAR_WH(&o->min);
    GEO_CARGAR_WH(&a->max);
    GEO_GUARDAR_WH(&o->max);
    o->radio = a->radio;
    o->actual = D_80069630;
    if (o->actual != 0) {
        do {
            if ((o->actual->flags08 & mascara) && o->actual->tipo_volumen == 2 && a != o->actual
                && a->p70 != o->actual && a->p6C != o->actual && o->actual->p70 != a) {
                GEO_CARGAR_WH(&o->actual->min);
                GEO_OR_WH(&o->actual->max);
                GEO_GUARDAR_1W_T1(&o->tmp);
                if (o->tmp != 0) {
                    GEO_CARGAR_W(&o->actual->param.trans);
                    GEO_RESTAR_W(&o->pos);
                    GEO_GUARDAR_H_T4(&o->dif);
                    GEO_NORMA2_XZ(&o->dif, &o->tmp);
                    if (o->tmp <= a->alcance2) {
                        ApplyMatrixSV(&o->m, &o->dif, &o->res);
                        if (o->res.vx >= o->min.vx - o->radio
                            && o->res.vx <= o->max.vx + o->radio
                            && o->res.vz >= o->min.vz - o->radio
                            && o->res.vz <= o->max.vz + o->radio
                            && o->res.vy + o->actual->min.vy >= o->max.vy
                            && o->res.vy + o->actual->max.vy <= o->min.vy) {
                            return o->actual;
                        }
                    }
                }
            }
            o->actual = o->actual->sig10;
        } while (o->actual != 0);
    }
    return 0;
}

/*
 * Variante con el punto a probar y una segunda mascara de exclusion como argumentos y el area
 * de trabajo como quinto argumento (en pila); el radio se ensancha 4 unidades.
 */
Objeto* func_800171E4(Objeto* a, VECTOR* p, u32 mascara, u32 excluir, ConsultaVolumen* o)
{
    Objeto* n;
    s32 r;
    SVECTOR* dif;
    SVECTOR* rot;
    MATRIX* m;
    ConsultaVolumen* consulta;

    /*
     * Copia local del area de trabajo: con ella el area y el radio ampliado reciben s2 y s3 en el
     * orden del original (global-alloc ordena por usos y vida del pseudo; el parametro puro invierte el par).
     */
    consulta = o;
    m = 0;
    n = D_80069630;
    if (n != 0) {
        dif = &consulta->dif;
        rot = &consulta->rot;
        do {
            if ((n->flags08 & mascara) && n->tipo_volumen == 2 && n != a && !(n->flags08 & excluir)) {
                GEO_CARGAR_WH(&n->min);
                GEO_OR_WH(&n->max);
                GEO_GUARDAR_1W_T1(&consulta->caja);
                if (consulta->caja != 0) {
                    GEO_CARGAR_W(p);
                    GEO_RESTAR_W(&n->param.trans);
                    GEO_GUARDAR_H_T4(dif);
                    GEO_NORMA2_XZ(dif, &consulta->dist2);
                    if (consulta->dist2 <= n->alcance2) {
                        r = n->radio + 4;
                        GEO_COMPLEMENTO(&n->param.giro.rotate);
                        GEO_GUARDAR_H_T1(rot);
                        m = &consulta->m;
                        RotMatrixZYX(rot, m);
                        ApplyMatrixSV(m, dif, &consulta->res);
                        if (consulta->res.vx >= n->min.vx - r
                            && consulta->res.vx <= n->max.vx + r
                            && consulta->res.vz >= n->min.vz - r
                            && consulta->res.vz <= n->max.vz + r
                            && consulta->res.vy >= n->max.vy
                            && n->min.vy >= consulta->res.vy) {
                            return n;
                        }
                    }
                }
            }
            n = n->sig10;
        } while (n != 0);
    }
    return 0;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 6941 con la configuracion versionada (g = 8 del archivo). Ejes medidos con `diff`: 93 de
 * operando, 19 reordenadas y 324 insertadas o borradas; el original ocupa 0x11EC bytes (1147 instrucciones), de modo
 * que casi todo el residuo es desalineacion encadenada de pocas inserciones. El marco del C es el del original, de
 * 0x50 bytes: la salida es una estructura SVECTOR local (`vx` en 0x10 y `vz` en 0x14, con el hueco de `vy`), y le
 * siguen `k` (0x18), `salida_y` (0x1c) y `lista` (0x20); con dos variables `s16` sueltas el marco era de 0x48 y la
 * cifra 11694 frente a 10909.
 * `k` es una sola variable que vive en memoria (se pasa su direccion a gte_NormalClip): en el original el contador
 * de impactos del bucle de puntos (`sw zero,0x18(sp)` en 0x80017B28, `lw`/`sw` 0x18(sp) en 0x80017ED4), los resultados de
 * NormalClip, el primer resultado de SquareRoot0 (`sw v0,0x18(sp)` en 0x80018344) y la bandera de impacto
 * (`sw zero,0x18(sp)` en 0x80018404) comparten la ranura 0x18(sp); unirlas baja de 18547 a 17782. El indice de
 * arista usa `i` (su valor y el del contador de los bucles de puntos tienen vida disjunta) y no `t2`: la cifra no
 * cambia (17782), pero el pseudo del radio de alcance deja de vivir 534 instrucciones a traves de 9 llamadas y de
 * tomar s1 (30 referencias sobre 534 insns).
 * Reparto medido en los volcados de `cc1` (`.lreg` y `.greg`). Original: `w` en s1 (524 usos sobre 1680 insns,
 * prioridad 2,81), direccion de D_80069D18 en s2, `mejor` en s3, `v` en s4, `a` en s5, constante 0x2000000 en s6,
 * `mejor_d` en s7 y `dif` (`w + 0x50`) en fp, con s0 solo para el segundo producto de cada norma (`mflo s0`).
 * Causa principal, resuelta con un acceso por desplazamiento: la parte alta de D_80069D08 (8 usos sobre 62 insns,
 * prioridad 0,39) y su direccion completa (6 usos sobre 68 insns, 0,18) cruzaban la segunda llamada a SquareRoot0
 * porque las lecturas posteriores usaban el mismo simbolo, y las tomaban en s0 y s1 antes de la asignacion global:
 * `w` quedaba en s2, el resto un registro desplazado, `dif` caia a la pila y el segundo producto de la norma y el
 * de la longitud se derramaban a 0x28(sp). El original recalcula el `lui` tras esa llamada (0x800183A4). Leer
 * D_80069D08 tras la llamada como un desplazamiento de 0x100 bytes desde D_80069C08, cuya parte alta ya se
 * calcula tras la llamada, deja de cruzar la llamada: la cifra baja de 17782 a 15249 y los globales `w`, direccion
 * de D_80069D18, `mejor`, constante, `mejor_d` y `dif` caen en s1, s2, s3, s6, s7 y fp como en el original. La
 * cifra del mismo C con el acceso por nombre (`D_80069D08.vx` y `.vz`) es 14632. Una copia reducida de la norma
 * fuera del repositorio comparte la parte alta y la direccion entre llamadas igual que el acceso por nombre.
 * Formas que no se conservan: leer los dos componentes de D_80069D08 en locales antes de la llamada (17894), una
 * local con `&D_80069D08` (17782, el CSE la pliega), una local propia para el radio de alcance (20852) y una para
 * el resultado tras SquareRoot0 en lugar del contador (20069).
 * Otras correcciones al fuente medidas con el ensamblador: los dos valores de `D_80069D08` se calculan en locales y
 * se almacenan juntos en cada rama (15249 a 13864); la busqueda en la cadena de padres usa `while` y no `do`
 * (13864 a 13209; el compilador rotaba el bucle y duplicaba la comparacion con `a`, 0x80017640 a 0x80017668 en el original); y
 * `p[4].vy` recibe `a->min.vy` (`lhu 0x4A` en 0x80017A60 y `sh 0xBA` en 0x80017A6C) en vez de cero (13209 a 12354).
 * El bucle de las aristas se escribe con etiqueta y salto hacia atras (`if (angs < 4) { ...; if (D_80069380 < 0)
 * goto ciclo_aristas; }`) porque el original comprueba `< 4` en la cabeza en cada vuelta y cierra con `bltz` a la
 * cabeza (0x80018194 y 0x80017F78), sin rotar el bucle: con `while` el compilador lo rotaba y duplicaba la prueba
 * (12354 a 11964). El segundo resultado de SquareRoot0 se guarda en `i` (el original lo copia a t2, `move t2,v0` en
 * 0x80018384, el registro del indice de arista que ya esta muerto): 11964 a 11694. Las comparaciones del barrido
 * se escriben con el lado de `w->pt` primero (`pt + sal > b->max + radio`): el original carga `w->pt` antes que
 * `w->b` (0x80017BB4 y 0x80017BB8, `lw a3,0xC0` y `lw a2,0x94`), 10909 a 7984 con las de `vz` y `vx` (9359 con solo las
 * de `vz`). Las dos primeras llamadas de la rama de angulo negativo restan el radio a `min.vx` (`subu a0,a0,a2` en
 * 0x8001798C y 0x800179BC), no lo suman: 7984 a 7584. Orden de los almacenes: las cuatro esquinas de D_80069D18
 * guardan `x` antes que `z` (0x80017F0C a 0x80017F64 en el original, 7584 a 7494) y la salida final almacena `vx`,
 * `vz` y `vy` en ese orden (7494 a 7041). Una lectura de las parejas de D_80069D18 como `((u32*)D_80069D18)[n]` en
 * vez de `*(u32*)&D_80069D18[n]` no cambia la cifra (7494). Las pruebas de la arista mas cercana se escriben
 * `D_80069380 > k` (el original carga `D_80069380` antes que `k`, 0x80018088 y 0x8001808C): 7041 a 6941.
 * Residuo de esa zona: el compilador calcula como valores las direcciones `D_80069D18 + 4`, `+ 0xC` y `+ 0x10` (tres
 * `addiu` en la cabeza del bucle de aristas) y las usa como base; el original las lee con desplazamiento fijo desde
 * la direccion de D_80069D18, sin esos valores. Se supone, sin verificar, que el original lee cada pareja como un
 * elemento de un arreglo de palabras y no como dereferencia de la direccion de una esquina.
 * Residuo conocido: `a` y `v` estan intercambiados (a en s4 y v en s5, 25 usos cada una sobre 1680 y 1688 insns;
 * prioridades 0,0595 y 0,0592: el original da a `v` mayor prioridad); la cola de la ultima rama de la comparacion con
 * la mascara 0x2000000 esta fuera de linea en el original (0x80017EAC) y en linea aqui; y se supone, sin
 * verificar, que el original carga `lista` en una temporal y la copia (`lhu t8,0x20(sp)` y `move v0,t8`,
 * 0x80017518 y 0x80017520) por la forma de su prueba, y que eso explica los dos `move v0,t8` que faltan (0x80017520
 * y 0x80017588).
 *
 * Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con
 * mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la
 * pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. Devuelve el candidato elegido (el de menor
 * distancia, con preferencia por los marcados con 8) o 0.
 */
Objeto* func_80017478(Objeto* a, SVECTOR* v, ConsultaSondeo* w, u32 mascara)
{
    Objeto* mejor;
    u32 mejor_d;
    s32 i;
    s32 t2;
    s32 k;
    s32 ax;
    s32 az;
    SVECTOR salida;
    s32 salida_y;
    u16 lista;
    SVECTOR* dif;

    mejor = 0;
    mejor_d = 0xFFFFFFFF;
    dif = &w->dif;
    salida_y = 0;
    lista = 0;
    w->destino.vx = a->param.trans.vx + v->vx;
    w->destino.vy = a->param.trans.vy + v->vy;
    w->destino.vz = a->param.trans.vz + v->vz;
    w->s86 = 0;
    w->s84 = 0;
    w->actual = D_80069630;
    for (;;) {
        if (lista == 0 && mejor != 0 && (mejor->flags08 & 0x20000) == 0 && w->actual == 0) {
            w->actual = D_80069630;
            lista = 1;
        } else if (w->actual == 0) {
            break;
        }
        if (lista != 0 && (w->actual->flags08 & 0x20000) == 0) {
            goto siguiente;
        }
        if ((w->actual->flags08 & mascara) == 0 || w->actual->tipo_volumen != 2 || a == w->actual
            || a->p70 == w->actual || a->p6C == w->actual || w->actual->p70 == a
            || w->actual->p6C == a || w->actual->p70 == (Objeto*)D_80069698) {
            goto siguiente;
        }
        w->cadena = w->actual->p70;
        while (w->cadena != 0) {
            if (w->cadena == a) {
                break;
            }
            w->cadena = w->cadena->p70;
        }
        if (w->cadena != 0) {
            goto siguiente;
        }
        GEO_CARGAR_WH(&w->actual->min);
        GEO_OR_WH(&w->actual->max);
        GEO_GUARDAR_1W_T1(&w->caja);
        if (w->caja == 0) {
            goto siguiente;
        }
        GEO_CARGAR_W(&w->destino);
        GEO_RESTAR_W(&w->actual->param.trans);
        GEO_GUARDAR_H_T4(dif);
        GEO_NORMA2_XZ(dif, &w->dist2);
        t2 = U16_2E(a) + U16_2E(w->actual) + w->actual->radio + a->radio;
        t2 = t2 * t2;
        if ((u32)t2 < w->dist2) {
            goto siguiente;
        }
        w->a = a;
        w->b = w->actual;
        GEO_CARGAR_W(&a->param.trans);
        GEO_RESTAR_W(&w->b->param.trans);
        GEO_GUARDAR_H_T4(dif);
        w->dif.vy = w->dif.vy + v->vy;
        w->radio = w->b->radio;
        GEO_COMPLEMENTO(&w->b->param.giro.rotate);
        GEO_GUARDAR_H_T1(&w->rot);
        RotMatrixZYX(&w->rot, &w->m);
        ApplyMatrixSV(&w->m, dif, &w->res);
        ApplyMatrixSV(&w->m, v, &w->sal);
        w->caja = w->actual->max.vy - w->res.vy;
        if (!(w->b->max.vy < w->res.vy + w->a->min.vy + v->vy)) {
            goto siguiente;
        }
        if (w->b->min.vy < w->res.vy + w->a->max.vy + v->vy) {
            goto siguiente;
        }
        w->p[0].vx = (w->b->max.vx >> 1) + (w->b->min.vx >> 1);
        w->p[0].vz = (w->b->max.vz >> 1) + (w->b->min.vz >> 1);
        w->ang = ratan2(w->res.vx - w->p[0].vx, w->res.vz - w->p[0].vz);
        if (w->ang >= 0) {
            w->angs[0] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
            w->angs[1] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
        } else {
            w->angs[2] = ratan2(w->b->min.vx - w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
            w->angs[3] = ratan2(w->b->min.vx - w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
        }
        w->p[0].vx = w->p[2].vx = w->a->min.vx - w->a->radio;
        w->p[1].vx = w->p[3].vx = w->a->max.vx + w->a->radio;
        w->p[0].vz = w->p[1].vz = w->a->max.vz + w->a->radio;
        w->p[2].vz = w->p[3].vz = w->a->min.vz - w->a->radio;
        w->p[4].vx = w->p[4].vz = 0;
        w->p[0].vy = w->p[1].vy = w->p[2].vy = w->p[3].vy = 0;
        w->p[4].vy = w->a->min.vy;
        RotMatrix(&w->a->param.giro.rotate, &w->m2);
        gte_SetRotMatrix(&w->m2);
        w->pt = w->p;
        for (i = 0; i < 5; i++) {
            gte_ldv0(w->pt);
            gte_rtv0();
            gte_stsv(w->pt);
            w->pt++;
        }
        gte_SetRotMatrix(&w->m);
        w->pt = w->p;
        k = 0;
        for (i = 0; i < 5; i++, w->pt++) {
            w->pt->vx += w->dif.vx;
            w->pt->vz += w->dif.vz;
            gte_ldv0(w->pt);
            gte_rtv0();
            gte_stsv(w->pt);
            if (w->ang >= 0) {
                if (w->ang < w->angs[0]) {
                    if (w->pt->vz + w->sal.vz > w->b->max.vz + w->radio) {
                        continue;
                    }
                    if (w->pt->vx + w->sal.vx > w->b->max.vx + w->radio) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vz = w->b->max.vz + w->radio - w->pt->vz;
                    }
                } else if (w->ang < w->angs[1]) {
                    if (w->pt->vx + w->sal.vx > w->b->max.vx + w->radio) {
                        continue;
                    }
                    if (w->pt->vz + w->sal.vz > w->b->max.vz + w->radio) {
                        continue;
                    }
                    if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vx = w->b->max.vx + w->radio - w->pt->vx;
                    }
                } else {
                    if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                        continue;
                    }
                    if (w->pt->vx + w->sal.vx > w->b->max.vx + w->radio) {
                        continue;
                    }
                    if ((w->b->flags08 & 0x2000000) == 0) {
                        w->sal.vz = w->b->min.vz - w->radio - w->pt->vz;
                    }
                }
            } else if (w->angs[2] < w->ang) {
                if (w->pt->vz + w->sal.vz > w->b->max.vz + w->radio) {
                    continue;
                }
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vz = w->b->max.vz + w->radio - w->pt->vz;
                }
            } else if (w->angs[3] < w->ang) {
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if (w->pt->vz + w->sal.vz > w->b->max.vz + w->radio) {
                    continue;
                }
                if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vx = w->b->min.vx - w->radio - w->pt->vx;
                }
            } else {
                if (w->pt->vz + w->sal.vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if (w->pt->vx + w->sal.vx < w->b->min.vx - w->radio) {
                    continue;
                }
                if ((w->b->flags08 & 0x2000000) == 0) {
                    w->sal.vz = w->b->min.vz - w->radio - w->pt->vz;
                }
            }
            k++;
        }
        if (k == 0) {
            D_80069D18[0].x = w->p[0].vx;
            D_80069D18[0].z = w->p[0].vz;
            D_80069D18[1].x = w->p[1].vx;
            D_80069D18[1].z = w->p[1].vz;
            D_80069D18[2].x = w->p[2].vx;
            D_80069D18[2].z = w->p[2].vz;
            D_80069D18[3].x = w->p[3].vx;
            D_80069D18[3].z = w->p[3].vz;
            D_80069380 = -1;
            w->angs[0] = 0;
ciclo_aristas:
            if (w->angs[0] < 4) {
                if (w->angs[0] == 0) {
                    D_80069D18[4].x = w->b->max.vx + w->radio;
                    D_80069D18[4].z = w->b->max.vz + w->radio;
                } else if (w->angs[0] == 1) {
                    D_80069D18[4].x = w->b->max.vx + w->radio;
                    D_80069D18[4].z = w->b->min.vz - w->radio;
                } else if (w->angs[0] == 2) {
                    D_80069D18[4].x = w->b->min.vx - w->radio;
                    D_80069D18[4].z = w->b->min.vz - w->radio;
                } else if (w->angs[0] == 3) {
                    D_80069D18[4].x = w->b->min.vx - w->radio;
                    D_80069D18[4].z = w->b->max.vz + w->radio;
                }
                D_80069380 = 0x7FFFFFFF;
                gte_NormalClip(*(u32*)&D_80069D18[0], *(u32*)&D_80069D18[1], *(u32*)&D_80069D18[4], &k);
                if (D_80069380 > k) {
                    D_80069380 = k;
                    i = 0;
                }
                gte_NormalClip(*(u32*)&D_80069D18[1], *(u32*)&D_80069D18[3], *(u32*)&D_80069D18[4], &k);
                if (D_80069380 > k) {
                    D_80069380 = k;
                    i = 1;
                }
                gte_NormalClip(*(u32*)&D_80069D18[3], *(u32*)&D_80069D18[2], *(u32*)&D_80069D18[4], &k);
                if (D_80069380 > k) {
                    D_80069380 = k;
                    i = 2;
                }
                gte_NormalClip(*(u32*)&D_80069D18[2], *(u32*)&D_80069D18[0], *(u32*)&D_80069D18[4], &k);
                if (D_80069380 > k) {
                    D_80069380 = k;
                    i = 3;
                }
                w->angs[0]++;
                if (D_80069380 < 0) {
                    goto ciclo_aristas;
                }
            }
            if (D_80069380 > 0) {
                if (i == 0) {
                    w->e_x = D_80069D18[1].x - D_80069D18[0].x;
                    w->e_z = D_80069D18[1].z - D_80069D18[0].z;
                    ax = D_80069D18[4].x - D_80069D18[0].x;
                    az = D_80069D18[4].z - D_80069D18[0].z;
                    D_80069D08.vx = ax;
                    D_80069D08.vz = az;
                } else if (i == 1) {
                    w->e_x = D_80069D18[3].x - D_80069D18[1].x;
                    w->e_z = D_80069D18[3].z - D_80069D18[1].z;
                    ax = D_80069D18[4].x - D_80069D18[1].x;
                    az = D_80069D18[4].z - D_80069D18[1].z;
                    D_80069D08.vx = ax;
                    D_80069D08.vz = az;
                } else if (i == 2) {
                    w->e_x = D_80069D18[2].x - D_80069D18[3].x;
                    w->e_z = D_80069D18[2].z - D_80069D18[3].z;
                    ax = D_80069D18[4].x - D_80069D18[3].x;
                    az = D_80069D18[4].z - D_80069D18[3].z;
                    D_80069D08.vx = ax;
                    D_80069D08.vz = az;
                } else if (i == 3) {
                    w->e_x = D_80069D18[0].x - D_80069D18[2].x;
                    w->e_z = D_80069D18[0].z - D_80069D18[2].z;
                    ax = D_80069D18[4].x - D_80069D18[2].x;
                    az = D_80069D18[4].z - D_80069D18[2].z;
                    D_80069D08.vx = ax;
                    D_80069D08.vz = az;
                }
                k = SquareRoot0(w->e_x * w->e_x + w->e_z * w->e_z);
                i = SquareRoot0(D_80069D08.vx * D_80069D08.vx + D_80069D08.vz * D_80069D08.vz);
                D_80069C08.vx = (w->e_x << 12) / k;
                D_80069C08.vz = (w->e_z << 12) / k;
                D_80069C08.vx = (D_80069C08.vx * i) >> 12;
                D_80069C08.vz = (D_80069C08.vz * i) >> 12;
                k = 1;
                /* Desplazamiento de 0x100 bytes desde D_80069C08: equivale a D_80069D08.vx y D_80069D08.vz. */
                w->sal.vx = w->sal.vx - (D_80069C08.vx - ((VECTOR*)((u8*)&D_80069C08 + 0x100))->vx);
                w->sal.vz = w->sal.vz - (D_80069C08.vz - ((VECTOR*)((u8*)&D_80069C08 + 0x100))->vz);
            } else {
                k = 0;
            }
        }
        if (k == 0) {
            goto siguiente;
        }
        RotMatrix(&w->b->param.giro.rotate, &w->m);
        ApplyMatrixSV(&w->m, &w->sal, &w->res);
        if (mejor != 0 && (w->b->flags08 & 0x20000) == 0) {
            salida.vx = (w->res.vx + v->vx) >> 1;
            salida.vz = (w->res.vz + v->vz) >> 1;
            v->vx = salida.vx;
            v->vz = salida.vz;
        } else {
            salida.vx = w->res.vx;
            v->vx = salida.vx;
            salida.vz = w->res.vz;
            v->vz = salida.vz;
        }
        if (w->dist2 < mejor_d || (w->actual->flags08 & 8) != 0) {
            /* sigue a la seleccion */
        } else if (mejor == 0 || (mejor->flags08 & 8) == 0) {
            goto siguiente;
        }
        if (mejor != 0 && (mejor->flags08 & 0x20000) != 0 && (w->actual->flags08 & 0x20000) == 0) {
            goto siguiente;
        }
        if ((w->actual->flags08 & 8) != 0) {
            if (mejor != 0 && (mejor->flags08 & 8) != 0) {
                if (!(w->dist2 < mejor_d)) {
                    goto siguiente;
                }
            }
            mejor = w->actual;
            mejor_d = w->dist2;
            salida_y = w->caja;
        } else {
            if (mejor != 0) {
                if ((mejor->flags08 & 8) != 0) {
                    goto siguiente;
                }
                if ((mejor->flags08 & 0x20000) != 0 && (w->actual->flags08 & 0x2000000) != 0) {
                    goto siguiente;
                }
            }
            mejor = w->actual;
            mejor_d = w->dist2;
            salida_y = w->caja;
        }
siguiente:
        w->actual = w->actual->sig10;
    }
    if (mejor != 0) {
        v->vx = salida.vx;
        v->vz = salida.vz;
        v->vy = salida_y;
    }
    return mejor;
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte", func_80017478);
#endif

/*
 * Estructura del original en los seis caminos de clasificacion del bucle (0x44c, 0x498, 0x4b4, 0x500,
 * 0x558 y 0x5b4, en el orden del fuente): cada camino evalua su propia cadena de comparaciones del bloque contra
 * el punto y su ultima prueba es su salida, `if (cmp) continue; return 1;`, escrita con las lecturas del area de
 * trabajo, sin variables intermedias. Las cadenas se distinguen por el conjunto y el orden de comparaciones:
 * el camino de 0x44c prueba z maxima y luego x maxima, el de 0x4b4 z minima y luego x maxima, el de 0x498 x
 * maxima, z maxima y z minima, el de 0x558 x minima, z maxima y z minima, el de 0x500 z maxima y luego x
 * minima, y el de 0x5b4 z minima y luego x minima. Aunque tres parejas acaban en la misma comparacion, llegan
 * a ella por pruebas distintas y todos los caminos terminan en `continue` o en `return`: no hay un punto comun
 * donde escribir una sola copia sin un resultado intermedio y un `goto`, de modo que son flujo de control
 * corriente y no una sentencia replicada. El compilador comparte el codigo final de los caminos (salto
 * cruzado), como el original: los caminos de 0x498 y 0x558 comparten la cadena de 0x570 a 0x5a0 (el primero
 * entra por `j 0x570`), los de 0x500 y 0x5b4 la de 0x518 a 0x540 (el segundo entra por `j 0x518`), y los de
 * 0x44c y 0x4b4 entran por `j 0x5a4` en la cola comun `bnez v0,0x5d0 ; li v0,1 ; j 0x5f0`, cada uno con su
 * `slt` en el hueco del salto. Se supone, sin verificar, que con las pruebas escritas directas todos los
 * resultados de comparacion son temporales de su bloque y caen en v0.
 *
 * Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el
 * cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca.
 *
 * Reserva de pila: el marco del original es de 0x28 bytes (`addiu sp` en 0x80018664) y el del C sin la local, de
 * 0x20; la cifra medida sin la local es 58 y con ella 0.
 */
s32 func_80018664(Objeto* a, Objeto* b, ConsultaSondeo* w)
{
    s32 i;
    SVECTOR* dif;
    MATRIX* m2;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[2];
    GEO_CARGAR_WH(&b->min);
    GEO_OR_WH(&b->max);
    GEO_GUARDAR_1W_T1(&w->caja);
    if (w->caja == 0) {
        return 0;
    }
    GEO_CARGAR_W(&a->param.trans);
    GEO_RESTAR_W(&b->param.trans);
    dif = &w->dif;
    GEO_GUARDAR_H_T4(dif);
    w->a = a;
    w->b = b;
    GEO_CARGAR_W(&w->a->param.trans);
    GEO_RESTAR_W(&w->b->param.trans);
    GEO_GUARDAR_H_T4(dif);
    w->radio = w->b->radio;
    GEO_COMPLEMENTO(&w->b->param.giro.rotate);
    GEO_GUARDAR_H_T1(&w->rot);
    RotMatrixZYX(&w->rot, &w->m);
    ApplyMatrixSV(&w->m, dif, &w->res);
    w->p[0].vx = (w->b->max.vx >> 1) + (w->b->min.vx >> 1);
    w->p[0].vz = (w->b->max.vz >> 1) + (w->b->min.vz >> 1);
    w->ang = ratan2(w->res.vx - w->p[0].vx, w->res.vz - w->p[0].vz);
    if (w->ang >= 0) {
        w->angs[0] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
        w->angs[1] = ratan2(w->b->max.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
    } else {
        w->angs[2] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->max.vz + w->radio - w->p[0].vz);
        w->angs[3] = ratan2(w->b->min.vx + w->radio - w->p[0].vx, w->b->min.vz - w->radio - w->p[0].vz);
    }
    w->p[0].vx = w->p[2].vx = w->a->min.vx - w->a->radio;
    w->p[1].vx = w->p[3].vx = w->a->max.vx + w->a->radio;
    w->p[0].vz = w->p[1].vz = w->a->max.vz + w->a->radio;
    w->p[2].vz = w->p[3].vz = w->a->min.vz - w->a->radio;
    w->p[4].vx = w->p[4].vy = w->p[4].vz = 0;
    w->p[0].vy = w->p[1].vy = w->p[2].vy = w->p[3].vy = 0;
    m2 = &w->m2;
    RotMatrix(&w->a->param.giro.rotate, m2);
    gte_SetRotMatrix(m2);
    w->pt = w->p;
    i = 0;
    while (i < 4) {
        gte_ldv0(w->pt);
        gte_rtv0();
        gte_stsv(w->pt);
        w->pt++;
        i++;
    }
    gte_SetRotMatrix(&w->m);
    i = 0;
    w->pt = w->p;
    for (; i < 5; i++, w->pt++) {
        w->pt->vx += w->dif.vx;
        w->pt->vz += w->dif.vz;
        gte_ldv0(w->pt);
        gte_rtv0();
        gte_stsv(w->pt);
        if (w->ang >= 0) {
            if (w->ang < w->angs[0]) {
                if (w->b->max.vz + w->radio < w->pt->vz) {
                    continue;
                }
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
                return 1;
            } else if (w->ang < w->angs[1]) {
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
                if (w->b->max.vz + w->radio < w->pt->vz) {
                    continue;
                }
                if (w->pt->vz < w->b->min.vz - w->radio) {
                    continue;
                }
                return 1;
            } else {
                if (w->pt->vz < w->b->min.vz - w->radio) {
                    continue;
                }
                if (w->b->max.vx + w->radio < w->pt->vx) {
                    continue;
                }
                return 1;
            }
        } else if (w->angs[2] < w->ang) {
            if (w->b->max.vz + w->radio < w->pt->vz) {
                continue;
            }
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
            return 1;
        } else if (w->angs[3] < w->ang) {
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
            if (w->b->max.vz + w->radio < w->pt->vz) {
                continue;
            }
            if (w->pt->vz < w->b->min.vz - w->radio) {
                continue;
            }
            return 1;
        } else {
            if (w->pt->vz < w->b->min.vz - w->radio) {
                continue;
            }
            if (w->pt->vx < w->b->min.vx - w->radio) {
                continue;
            }
            return 1;
        }
    }
    return 0;
}

/*
 * Clasifica el punto del jugador respecto de la caja del objeto a en el eje z de su sistema
 * local: 1 si queda por debajo del minimo, 2 si por encima del maximo y 0 si dentro.
 */
s32 func_80018C68(Objeto* a, ConsultaMatriz* o)
{
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    /* 0x80018CC0..0x80018CD4: lw v0,%lo(D_80069698) ; addiu v0,v0,0xE4 ; lw 0x0/0x4/0x8 de esa base: tres s32 consecutivos que la macro lee como VECTOR. */
    GEO_CARGAR_W(&D_80069698->param.trans);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_IDENTIDAD(o);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (o->res.vz >= a->min.vz) {
        return (a->max.vz < o->res.vz) << 1;
    }
    return 1;
}

/*
 * Prueba si el punto p cae dentro del volumen del objeto a ampliado por su radio. Descarta antes
 * por distancia al cuadrado en el plano.
 * El do/while (0) no genera codigo: el optimizador de bucles pondera por un nivel mas las
 * referencias a a y o de su cuerpo (13 usos ponderados de a sobre 102 instrucciones de vida), y
 * eso sube la prioridad de a por encima de la del puntero a la diferencia (0,382 frente a 0,381)
 * y por debajo de la de o (0,415): el original guarda o en $s1, a en $s2 y el puntero a la
 * diferencia en $s3. Sin el, el puntero (4 usos sobre 21 instrucciones) se asigna antes que a y
 * $s2 y $s3 se invierten.
 * La forma del fuente original que producia este reparto se desconoce.
 */
s32 func_80018D98(Objeto* a, VECTOR* p, ConsultaVolumen* o)
{
    GEO_CARGAR_W(p);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    o->radio = a->radio;
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    GEO_IDENTIDAD(&o->m);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (a->min.vx - o->radio < o->res.vx
        && o->res.vx < a->max.vx + o->radio
        && a->min.vz - o->radio < o->res.vz
        && o->res.vz < a->max.vz + o->radio) {
        do {
            if (o->res.vy < a->min.vy && a->max.vy < o->res.vy) {
                return 1;
            }
        } while (0);
    }
    return 0;
}

/*
 * Igual que func_80018D98 pero la posicion a probar es la del objeto b y la caja de b
 * (extensiones en y) se suma al margen vertical.
 * Los dos do/while (0) no generan codigo: ponderan por un nivel mas la copia del radio y las
 * pruebas en y, de modo que a suma 14 usos ponderados (0,3818 sobre 110 instrucciones de vida),
 * por encima del puntero a la diferencia (0,3810) y por debajo de o (0,447). Con uno solo, a
 * queda en 13 usos (0,3545) y $s2 y $s3 se invierten; extender el segundo a la prueba de z sube
 * a 14 pero cambia entre v1 y a0 el registro de las cargas temporales.
 * La forma del fuente original que producia este reparto se desconoce.
 */
s32 func_80018F80(Objeto* a, Objeto* b, ConsultaVolumen* o)
{
    GEO_CARGAR_W(&b->param.trans);
    GEO_RESTAR_W(&a->param.trans);
    GEO_GUARDAR_H_T4(&o->dif);
    GEO_NORMA2_XZ(&o->dif, &o->dist2);
    if (o->dist2 > a->alcance2) {
        return 0;
    }
    do {
        o->radio = a->radio;
    } while (0);
    GEO_COMPLEMENTO(&a->param.giro.rotate);
    GEO_GUARDAR_H_T1(&o->rot);
    GEO_IDENTIDAD(&o->m);
    RotMatrixZYX(&o->rot, &o->m);
    ApplyMatrixSV(&o->m, &o->dif, &o->res);
    if (a->min.vx - o->radio < o->res.vx
        && o->res.vx < a->max.vx + o->radio
        && a->min.vz - o->radio < o->res.vz
        && o->res.vz < a->max.vz + o->radio) {
        do {
            if (o->res.vy + b->max.vy < a->min.vy
                && a->max.vy < o->res.vy + b->min.vy) {
                return 1;
            }
        } while (0);
    }
    return 0;
}

/*
 * Recorre la lista de nodos de plano y devuelve el primero que contiene el punto p visto desde
 * el objeto a: pasa al sistema local del nodo (con rotacion si el bit 0 de sus indicadores esta
 * apagado) y acota x y z por sus limites; en y lo acota por el margen del objeto.
 * Con g = 8 (config/opciones_compilacion.toml) el puntero global se carga directamente en $s0;
 * con -G0 la parte alta iria a otro registro (205).
 */
NodoVolumen* func_80019180(Objeto* a, VECTOR* p, ConsultaPlano* o)
{
    NodoVolumen* n;
    s32 z;
    SVECTOR* rot;
    SVECTOR* dif;

    n = D_80069580;
    if (n != 0) {
        dif = &o->dif;
        rot = &o->rot;
        do {
            if ((n->indicadores & 2) || n->etiqueta == (s16)a->w26) {
                GEO_CARGAR_W(p);
                GEO_RESTAR_W(&n->pos);
                GEO_GUARDAR_H_T4(dif);
                if (o->dif.vy + a->max.vy <= 0 && o->dif.vy >= n->lim_y) {
                    if (n->indicadores & 1) {
                        if (o->dif.vx < 0 || n->lim_x < o->dif.vx) {
                            goto siguiente;
                        }
                        z = o->dif.vz;
                    } else {
                        GEO_COMPLEMENTO(&n->rot);
                        GEO_GUARDAR_H_T1(rot);
                        RotMatrixZYX(rot, &o->m);
                        ApplyMatrixSV(&o->m, dif, &o->res);
                        if (o->res.vx < 0 || n->lim_x < o->res.vx) {
                            goto siguiente;
                        }
                        z = o->res.vz;
                    }
                    if (z >= 0 && n->lim_z >= z) {
                        return n;
                    }
                }
            }
siguiente:
            n = n->sig;
        } while (n != 0);
    }
    return 0;
}
