#include "common.h"
#include "gte.h"
#include "objetos.h"
#include "animacion.h"
#include "psyq/MEMORY.H"

/* Nodo de una lista con clave de busqueda en +0x18 (la lista de ayudantes de un objeto). */
typedef struct NodoClave {
    NodoLista cab;
    u8 pad08[0x18 - 0x08];
    s32 clave;
} NodoClave;

extern Objeto* D_800694DC;
extern Objeto* D_800694B4;

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 415 con la configuracion versionada (g = 8 del archivo). GCC deriva un
 * segundo puntero inducido (p + 4) para los dos accesos de campo y devuelve el puntero base; el
 * original usa un solo puntero con desplazamientos 0x0C y 0x04. Variantes probadas: 9.
 */
EntradaId* func_80036164(s32 id)
{
    s32 i;
    s32 n;
    EntradaId* p;

    n = D_800694E6;
    i = 0;
    if (n > 0) {
        p = D_800695D4;
        do {
            if (p->id == id) {
                if ((p->cab.libre & 1) == 0) {
                    return p;
                }
            }
            i++;
            p++;
        } while (i < n);
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_80036164);
#endif

/* Busca en una lista el nodo cuya clave coincide; devuelve NULL si no existe. */
NodoClave* func_800361CC(NodoClave* n, s32 clave)
{
    while (n != 0) {
        if (n->clave == clave) {
            return n;
        }
        n = (NodoClave*)n->cab.siguiente;
    }
    return 0;
}

/*
 * Devuelve el primer nodo libre de un pozo de nodos de 'paso' bytes, lo marca como ocupado
 * (borra la marca y el enlace) y devuelve NULL si el pozo de 'total' bytes se agota.
 */
NodoLista* AllocListNode(u8* base, s32 paso, s32 total)
{
    u8* p;
    u8* fin;

    p = base;
    fin = p + total;
    while (p < fin) {
        if (((NodoLista*)p)->libre & 1) {
            ((NodoLista*)p)->libre = 0;
            ((NodoLista*)p)->siguiente = 0;
            return (NodoLista*)p;
        }
        p = base + paso;
        base = p;
    }
    return 0;
}

/*
 * Prepara un pozo: pone a cero cada nodo de 'paso' bytes y lo marca como libre. El limite del
 * bucle se calcula sobre una copia de la direccion inicial: 'base' avanza con el pozo y, si el
 * limite se derivara de ella, el compilador reordenaria los registros del bucle.
 */
void InitListPool(u8* base, s32 paso, s32 total)
{
    u8* p;
    u8* ini;

    ini = base;
    p = base;
    while (p < ini + total) {
        memset(base, 0, paso);
        ((NodoLista*)p)->libre = 1;
        p = base + paso;
        base = p;
    }
}

/*
 * Quita 'nodo' de la lista que empieza en 'cab' y lo marca como libre; devuelve la nueva
 * cabeza. Las salidas "sin cambios" comparten un solo retorno con goto: asi el compilador deja
 * un unico bloque de salida que atienden tanto la lista de un solo nodo como el nodo ausente,
 * y reutiliza $a0 para el siguiente del nodo quitado mientras la cabeza espera en $v0.
 */
NodoLista* RemoveListNode(NodoLista* cab, NodoLista* nodo)
{
    NodoLista* prev;
    NodoLista* cur;
    NodoLista* r;

    if (cab == 0) {
        return 0;
    }
    if (cab == nodo) {
        cab->libre = 1;
        return cab->siguiente;
    }
    if (cab->siguiente == 0) {
        goto sin_cambios;
    }
    prev = cab;
    while (prev->siguiente != 0) {
        if (prev->siguiente == nodo) {
            break;
        }
        prev = prev->siguiente;
    }
    cur = prev->siguiente;
    if (cur == 0) {
        goto sin_cambios;
    }
    r = cab;
    cab = cur->siguiente;
    cur->libre = 1;
    prev->siguiente = cab;
    cur->siguiente = 0;
    return r;
sin_cambios:
    return cab;
}

/*
 * Libera todos los nodos de la lista que empieza en 'cab' (los marca libres y corta sus
 * enlaces) y devuelve siempre NULL: la cabeza de una lista vaciada. El puntero que avanza se
 * lee antes de cortar el enlace del nodo actual.
 */
NodoLista* ClearList(NodoLista* cab)
{
    NodoLista* cur;
    NodoLista* nxt;

    if (cab == 0) {
        return 0;
    }
    nxt = cab;
    do {
        cur = nxt;
        nxt = cur->siguiente;
        cur->libre = 1;
        cur->siguiente = 0;
    } while (nxt != 0);
    return 0;
}

/* Anade 'nodo' al final de la lista y devuelve la cabeza (el propio nodo si la lista estaba vacia). */
NodoLista* AppendListNode(NodoLista* cab, NodoLista* nodo)
{
    NodoLista* p;

    if (cab == 0) {
        return nodo;
    }
    p = cab;
    while (p->siguiente != 0) {
        p = p->siguiente;
    }
    p->siguiente = nodo;
    nodo->siguiente = 0;
    return cab;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 205 con la configuracion versionada (g = 8 del archivo). El original
 * mantiene el nodo en $a0 y deriva el puntero inducido en $a1; GCC los intercambia. Las 0x2E
 * escrituras de sw $zero,0($a2) del original son un bucle real de 0x2E vueltas (contador en $v1,
 * sltiu/bnez, la escritura en el hueco de retardo), no una secuencia desenrollada; escritas como
 * 0x2E sentencias explicitas el resultado empeora (895), porque GCC no las pliega a ese bucle.
 * Variantes probadas: 11.
 */
Ayuda* func_800363D4(void)
{
    s32 i;
    u32 j;
    Ayuda* e;
    Ayuda* p;
    GsCOORDINATE2* sub;
    s32 n;

    e = D_8006964C;
    n = D_80069660;
    for (i = 0; i < n; i++, e++) {
        if (e->cab.libre & 1) {
            p = e;
            e->cab.libre = 0;
            e->flags8 = 0;
            e->cab.siguiente = 0;
            for (j = 0; j < 0x2E; j++) {
                p->cab.siguiente = 0;
            }
            sub = &e->coord;
            e->pcoord = sub;
            e->wC = 0x80000000;
            e->clave = -1;
            e->coord.param = &e->param;
            sub->super = 0;
            e->w14 = 0;
            return e;
        }
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_800363D4);
#endif

/*
 * Crea un ayudante para el objeto 'o', lo anade a su lista y lo identifica con 'clave'. Detiene el
 * juego en un bucle infinito si el pozo de ayudantes esta agotado (el original no tiene salida
 * de error).
 */
Ayuda* func_80036474(Objeto* o, s32 clave)
{
    Ayuda* a;

    a = func_800363D4();
    if (a == 0) {
        for (;;) {
        }
    }
    o->u78.ayudas = (Ayuda*)AppendListNode((NodoLista*)o->u78.ayudas, (NodoLista*)a);
    a->flags8 = 0x8008;
    a->clave = clave;
    return a;
}

/* Quita de la lista de 'o' el ayudante de la clave dada; detiene el juego si no existe. */
void func_800364E0(Objeto* o, s32 clave)
{
    NodoClave* e;

    e = func_800361CC((NodoClave*)o->u78.ayudas, clave);
    if (e == 0) {
        for (;;) {
        }
    }
    o->u78.ayudas = (Ayuda*)RemoveListNode((NodoLista*)o->u78.ayudas, (NodoLista*)e);
}

/*
 * Reserva un objeto de escena en el pozo D_8006968C, lo anade a la lista de la escena y lo deja
 * activo con los parametros por omision. Sin salida de error: si el pozo se agota se detiene.
 */
void func_8003652C(void)
{
    Objeto* o;

    D_800694DC = (Objeto*)AllocListNode((u8*)D_8006968C, 0x1F4, D_8006955C * 0x1F4);
    if (D_800694DC == 0) {
        for (;;) {
        }
    }
    D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)D_800694DC);
    o = D_800694DC;
    o->w1C = 5;
    o->s2A = 0;
    o->w2C = 7;
    o->flags04 |= 2;
}

/*
 * Crea el primer objeto de la escena (D_800694B4) y los 47 objetos de la tabla D_8006AB70, y los
 * anade a las listas D_80069518 y D_80069508. El primero queda activo sin ayudantes; los de la
 * tabla, con el estado 1 y el identificador -1. Sin salida de error: si el pozo se agota se
 * detiene.
 */
void func_800365D0(void)
{
    Objeto* o;
    s32 i;

    D_800694B4 = (Objeto*)AllocListNode(D_8006968C, 0x1F4, D_8006955C * 0x1F4);
    if (D_800694B4 == 0) {
        for (;;) {
        }
    }
    D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)D_800694B4);
    o = D_800694B4;
    o->w1C = 0;
    o->flags08 = 0;
    o->flags0C = 0;
    o->s2A = 5;
    o->w2C = 6;
    o->w3C = 0x40;
    D_80069508 = 0;
    o->u78.ayudas = 0;
    o->flags04 |= 2;
    for (i = 0; i < 47; i++) {
        D_8006AB70[i] = (Objeto*)AllocListNode(D_8006968C, 0x1F4, D_8006955C * 0x1F4);
        if (D_8006AB70[i] == 0) {
            for (;;) {
            }
        }
        D_80069508 = AppendListNode((NodoLista*)D_80069508, (NodoLista*)D_8006AB70[i]);
        D_8006AB70[i]->w3C = 1;
        /* El original guarda la constante con signo (li v0,-1 ; sh v0,0x26): con el tipo u16 del campo saldria li v0,0xffff. */
        *(s16*)&D_8006AB70[i]->w26 = -1;
        D_8006AB70[i]->u78.ayudas = 0;
    }
}

/*
 * Crea un objeto a partir de la plantilla de identificador 'id' (lista D_80069504): copia sus
 * 0x7D palabras, lo anade a la lista de la escena y a la de objetos solidos, y le pone la
 * posicion 'pos' y los angulos 'ang' si se dan. Devuelve NULL si 'id' no es positivo, no hay
 * plantilla o el pozo esta agotado.
 */
Objeto* func_80036734(s16 id, s32* pos, u16* ang)
{
    Objeto* t;
    Objeto* n;
    Objeto* l;
    u16 i;

    if (id > 0) {
        for (t = D_80069504; t != 0; t = t->siguiente) {
            if (t->w1C == id) {
                n = (Objeto*)AllocListNode((u8*)D_8006968C, 0x1F4, D_8006955C * 0x1F4);
                if (n == 0) {
                    return 0;
                }
                for (i = 0; i < 0x7D; i++) {
                    ((s32*)n)[(s16)i] = ((s32*)t)[(s16)i];
                }
                n->siguiente = 0;
                D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)n);
                n->coord.param = PARAMETROS_SDK(n);
                n->flags04 |= 2;
                if (pos != 0) {
                    n->param.trans.vx = pos[0];
                    n->param.trans.vy = pos[1];
                    n->param.trans.vz = pos[2];
                }
                if (ang != 0) {
                    n->param.giro.rotate.vx = ang[0];
                    n->param.giro.rotate.vy = ang[1];
                    n->param.giro.rotate.vz = ang[2];
                }
                l = (Objeto*)D_80069630;
                if (l != 0) {
                    t = l;
                    while (t->sig10 != 0) {
                        t = t->sig10;
                    }
                    t->sig10 = n;
                    n->sig10 = 0;
                }
                return n;
            }
        }
    }
    return 0;
}

/*
 * Borra el banco B de registros del evento. El ensamblador original escribe 256 veces el mismo
 * byte (la direccion no avanza), de modo que solo el primer registro queda a cero.
 */
void func_800368E8(void)
{
    s32 i;
    u8* p;

    p = D_8006AA70;
    for (i = 0; i < 0x100; i++) {
        *p = 0;
    }
}

/*
 * Aplica un cuadro de la animacion de un objeto: lee del flujo de pistas del cursor (c->flujo) la
 * cabecera de dos palabras (numero de pistas en la mitad alta de la primera) y despues una pista
 * por nodo afectado. Cada pista empieza con una palabra [tamano:8][banderas:8][tipo:4][nodo:16];
 * segun el tipo actualiza la pose de un nodo, la caja del objeto, su posicion absoluta (acumulando
 * la cadena de nodos con el GTE), el vinculo con el nodo padre, el cuadro de sprite de un nodo,
 * un campo de 32 bits o crea y retira ayudantes. El flujo avanza por el tamano de cada pista.
 * `w` es el area de trabajo del llamador (AreaCuadro).
 *
 * El ayudante de la pista (s0) y su vista desde +0xC (s5) y los parametros del nodo (s4) se
 * conservan entre pistas: una pista cuyo nodo no existe reutiliza los de la anterior.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 510 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difiere el reparto de registros callee-saved: el original deja el area de trabajo en $s1 y el puntero del flujo en $s2, GCC (prioridad de global-alloc por referencias y longitud de vida) los intercambia o adelanta el area a $s0 al copiar el parametro; ademas el sumando s20 de la caja cae en $a0 en lugar de $v1. */
void func_8003690C(Objeto* o, BloqueTrabajo* c, AreaCuadro* a2)
{
    AreaCuadro* w;
    u32* p;
    u32 nodo;
    u32 f;
    u32 n;
    Ayuda* a;

    NucleoAyuda* e;
    GsCOORD2PARAM* param;
    u16* h;

    w = a2;
    w->cab.w = *c->flujo++;
    w->npistas = w->cab.h.alto;
    w->palabra2 = *c->flujo++;
    o->i68 = 0;
    w->modo = 1;
    if (o->u78.ayudas != 0) {
        w->tabla = &w->ayudas[0];
        p = (u32*)&w->ayudas[1];
        for (a = o->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
            *(Ayuda**)p = a;
            p++;
        }
        w->modo = 0;
    }
    w->idx = 0;
    if (w->npistas != 0) {
        do {
            p = c->flujo;
            nodo = *p++;
            w->tipo = nodo & 0xF0000;
            w->banderas = nodo & 0xF00000;
            w->tam = nodo >> 24;
            nodo &= 0xFFFF;
            if (w->modo != 0) {
                a = (Ayuda*)o->u78.ayudas;
                while (a != 0 && a->clave != nodo) {
                    a = (Ayuda*)a->cab.siguiente;
                }
            } else {
                a = 0;
                if (nodo != 0) {
                    a = w->tabla[nodo];
                }
            }
            if (a != 0) {
                e = (NucleoAyuda*)&a->wC;
                w->m = &e->pcoord->coord;
                param = e->pcoord->param;
                e->pcoord->flg = 0;
            }
            switch (w->tipo) {
            case PISTA_POSE:
                f = a->flags8;
                a->flags8 = f & 0x7FFF;
                if (w->banderas & 0x600000) {
                    if (w->banderas & 0x200000) {
                        if (!(f & 0x400)) {
                            GEO_CARGAR_WH(p);
                            GEO_GUARDAR_WH(&param->rotate);
                        }
                        p += 2;
                    }
                    if (w->banderas & 0x400000) {
                        if (!(a->flags8 & 0x400)) {
                            ANIM_CARGAR_H3(p);
                            GEO_GUARDAR_W_T1(&param->scale);
                        }
                        p += 2;
                    }
                    if (!(a->flags8 & 0x400)) {
                        RotMatrix(&param->rotate, w->m);
                        ScaleMatrix(w->m, &param->scale);
                    }
                }
                if (w->banderas & 0x800000) {
                    if (!(a->flags8 & 0x400)) {
                        param->trans.vx = p[0];
                        param->trans.vy = p[1];
                        param->trans.vz = p[2];
                        TransMatrix(w->m, &param->trans);
                    }
                }
                break;
            case PISTA_CAJA:
                GEO_CARGAR_WH(p);
                GEO_GUARDAR_WH(&o->min);
                h = (u16*)p;
                f = o->s20;
                o->max.vx = h[3];
                o->max.vy = h[4];
                o->max.vz = h[5];
                o->w2E = h[6];
                n = o->w2E + f;
                o->alcance2 = n * n;
                break;
            case PISTA_POSICION:
                w->v.vx = 0;
                w->v.vy = 0;
                w->v.vz = 0;
                w->nodo = e->pcoord;
                if (w->nodo != 0) {
                    do {
                        gte_SetRotMatrix(&w->nodo->coord);
                        gte_ldv0(&w->v);
                        gte_rtv0();
                        gte_stlvnl(&w->acc);
                        w->acc.vx += w->nodo->coord.t[0];
                        w->acc.vy += w->nodo->coord.t[1];
                        w->acc.vz += w->nodo->coord.t[2];
                        w->v.vx = w->acc.vx;
                        w->v.vy = w->acc.vy;
                        w->v.vz = w->acc.vz;
                        w->nodo = w->nodo->super;
                    } while (w->nodo != 0);
                }
                o->apar[0] = w->acc.vx;
                o->apar[1] = w->acc.vy;
                o->apar[2] = w->acc.vz;
                o->i68 = e->pcoord;
                break;
            case PISTA_SPRITE:
                w->n = *(u16*)p;
                if (w->n != 0) {
                    a->flags8 = 4;
                    e->w8 = (s32)c->fotogramas + (w->n - 1) * 0x1C;
                } else {
                    a->flags8 = 8;
                    e->w8 = 0;
                }
                break;
            case PISTA_PADRE:
                if (p[0] == 0 || p[0] == 0xFFFF) {
                    e->pcoord->super = &o->coord;
                } else {
                    nodo = p[0];
                    for (w->p70 = (Ayuda*)o->u78.ayudas; w->p70 != 0; w->p70 = (Ayuda*)w->p70->cab.siguiente) {
                        if (w->p70->clave == nodo) {
                            break;
                        }
                    }
                    w->aux = (NucleoAyuda*)&w->p70->wC;
                    e->pcoord->super = w->aux->pcoord;
                }
                break;
            case PISTA_AYUDANTE:
                f = w->banderas;
                switch ((f >> 20) & 1) {
                case 0:
                    switch ((f >> 21) & 7) {
                    case 0:
                        func_80036474(o, nodo);
                        break;
                    case 1:
                        func_80036474(o, nodo)->flags8 = 0x40;
                        o->flags04 |= 0x20;
                        break;
                    case 2:
                        func_80036474(o, nodo)->flags8 = 0x80;
                        break;
                    case 3:
                        func_80036474(o, nodo)->flags8 = 0x100;
                        break;
                    case 4:
                        func_80036474(o, nodo)->flags8 = 0x200;
                        break;
                    case 5:
                        a->flags8 &= 0x7FFF;
                        break;
                    }
                    break;
                case 1:
                    if (((f >> 21) & 7) == 5) {
                        param->scale.vz = 0;
                        param->scale.vy = 0;
                        param->scale.vx = 0;
                        ANIM_DIAGONAL_CERO(w->m);
                        a->flags8 |= 0x8000;
                    } else {
                        func_800364E0(o, nodo);
                    }
                    break;
                }
                break;
            case PISTA_CAMPO32:
                param->trans.pad = p[0];
                break;
            case PISTA_MASCARA:
                e->w0 = (e->w0 & p[0]) | p[1];
                break;
            }
            c->flujo += w->tam;
            w->idx++;
        } while (w->idx < w->npistas);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_8003690C);
#endif
