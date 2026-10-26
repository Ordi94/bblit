#include "geometria.h"
#include "globales.h"

/* Cabezas de lista por grupo: la primera zona de cada grupo de la tabla cargada. */
extern ZonaColision* D_80069C18[];

/*
 * La cuenta de zonas y el puntero a la tabla viven en $gp+0x58 y $gp+0x5C; el original los
 * accede con desplazamiento fijo sobre $gp aunque el archivo se compila con -G0. Depende de que
 * nada reasigne $gp (el arranque lo fija a 0x80069320 y no cambia).
 */

/*
 * Carga la tabla de zonas de un bloque: [cuenta][zonas de 0x44 bytes]. Registra cuenta y puntero,
 * deja en la tabla de cabezas la primera zona de cada grupo (un grupo fuera de 0..59 es un
 * error irrecuperable y se queda en un bucle infinito) y convierte los dos desplazamientos de
 * cada zona en direcciones sumando la base del bloque.
 */
void func_80019364(s32* a0)
{
    ZonaColision* p;
    ZonaColision* rec;
    ZonaColision** tab;
    s16 i;
    s32 n;

    tab = D_80069C18;
    rec = (ZonaColision*)(a0 + 1);
    *(s32*)(base_gp + 0x58) = *a0;
    *(ZonaColision**)(base_gp + 0x5C) = rec;
    i = 0;
    do {
        tab[i] = 0;
        i++;
    } while (i < 60);
    p = rec;
    i = 0;
    if (*(s32*)(base_gp + 0x58) > 0) {
        n = *(s32*)(base_gp + 0x58);
        do {
            if (p->grupo >= 60) {
                for (;;) { }
            }
            if (tab[p->grupo] == 0) {
                tab[p->grupo] = p;
            }
            i++;
            p++;
        } while (i < n);
    }
    p = rec;
    i = 0;
    n = *(s32*)(base_gp + 0x58);
    if (n > 0) {
        do {
            i++;
            p->baldosas = (u16*)((s32)p->baldosas + (s32)a0);
            p->subceldas = (u8*)((s32)p->subceldas + (s32)a0);
            p++;
        } while (i < n);
    }
}

INCLUDE_ASM("asm/nonmatchings/colision_y_terreno", func_80019474);

/*
 * Busca la zona que contiene el punto (x, y, z): primero entre las del grupo indicado (si es
 * valido) y despues en toda la tabla. Devuelve NULL si ninguna lo contiene.
 */
ZonaColision* func_8001BF9C(s32* a0, s16 a1)
{
    ZonaColision* zona;
    s32 x;
    s32 y;
    s32 z;
    s32 n;
    s16 i;

    x = a0[0];
    y = a0[1];
    z = a0[2];
    if (a1 >= 0) {
        zona = D_80069C18[a1];
        if (zona != 0) {
            do {
                if (y <= zona->y_max && zona->y_min < y
                    && x >= zona->x && x < zona->x + zona->ancho_x
                    && z >= zona->z && z < zona->z + zona->ancho_z) {
                    return zona;
                }
                zona++;
            } while (zona->grupo == a1);
        }
    }
    zona = *(ZonaColision**)(base_gp + 0x5C);
    i = 0;
    if (*(s32*)(base_gp + 0x58) > 0) {
        n = *(s32*)(base_gp + 0x58);
        do {
            if (y <= zona->y_max && zona->y_min < y
                && x >= zona->x && x < zona->x + zona->ancho_x
                && z >= zona->z && z < zona->z + zona->ancho_z) {
                return zona;
            }
            zona++;
            i++;
        } while (i < n);
    }
    return 0;
}

/*
 * Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en
 * res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res
 * con la clase de terreno. 0x7E y 0x7F de la subcelda son transiciones de zona; cualquier otro
 * valor es una pendiente (su signo marca el sentido, el bit 0x20 de flags lo recuerda).
 *
 * Pendiente: puntuacion 1078 con la configuracion versionada (g = 0, no carga globales). El compilador asigna s0/s1
 * al reves (el original guarda la estructura de trabajo en s0 y el resultado en s1) y falta un `move t2,a3`.
 * Variantes probadas: 9 (copias de z, orden de sentencias, barreras, copias locales de los punteros de trabajo).
 */
#ifdef NON_MATCHING
void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w)
{
    ZonaColision* z;

    GEO_CARGAR_W(pos);
    GEO_GUARDAR_W_T1(&w->x);
    z = func_8001BF9C(&w->x, r->grupo);
    r->zona = z;
    if (z == 0) {
        r->clase = 1;
        r->flags = 1;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->tipo = 0;
        r->grupo = -1;
        return;
    }
    w->baldosa = z->baldosas[(w->x - z->x) / 320 + (w->z - z->z) / 320 * z->columnas];
    r->tipo = w->baldosa & 0xF000;
    w->x_local = w->x % 320;
    w->z_local = w->z % 320;
    w->baldosa &= 0xFFF;
    w->celda = (s8)z->subceldas[(w->baldosa << 6) + w->z_local / 40 * 8 + w->x_local / 40];
    if (w->celda == 0x7E) {
        pos[1] = z->y_max;
        r->clase = 0;
        r->flags = 8;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->grupo = z->grupo;
        r->suelo = pos[1];
        return;
    }
    if (w->celda == 0x7F) {
        pos[1] = z->y_max;
        r->clase = 0;
        r->flags = 6;
        r->pendiente = 0;
        r->pendiente_abs = 0;
        r->grupo = z->grupo;
        r->suelo = pos[1];
        return;
    }
    pos[1] = z->y_max;
    r->clase = w->celda;
    r->flags = 2;
    if (w->celda > 0) {
        w->celda = -w->celda;
        r->flags |= 0x20;
    }
    w->celda = w->celda * z->pendiente;
    r->pendiente = w->celda;
    r->pendiente_abs = w->celda;
    r->grupo = z->grupo;
    r->suelo = z->y_max + w->celda;
}
#else
INCLUDE_ASM("asm/nonmatchings/colision_y_terreno", func_8001C134);
#endif
