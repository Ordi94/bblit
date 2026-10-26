#include "common.h"
#include "objetos.h"
#include "psyq/MEMORY.H"

/*
 * Entrada de la tabla de identificadores D_800695D4 (0x58 bytes): 'id' en +0x0C y la marca de
 * libre en +0x04.
 */
typedef struct EntradaId {
    NodoLista cab;
    s32 w8;
    s32 id;
    u8 pad10[0x58 - 0x10];
} EntradaId;

/* Nodo de una lista con clave de busqueda en +0x18 (la lista de ayudantes de un objeto). */
typedef struct NodoClave {
    NodoLista cab;
    u8 pad08[0x18 - 0x08];
    s32 clave;
} NodoClave;

extern s16 D_800694E6;
extern EntradaId* D_800695D4;
extern s16 D_80069660;
extern Ayuda* D_8006964C;
extern ObjetoEscena* D_800694DC;
extern ObjetoEscena* D_800694B4;
extern void* D_80069508;

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
 * mantiene el nodo en $a0 y deriva el puntero inducido en $a1; GCC los intercambia. Variantes
 * probadas: 5.
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
Ayuda* func_80036474(ObjetoEscena* o, s32 clave)
{
    Ayuda* a;

    a = func_800363D4();
    if (a == 0) {
        for (;;) {
        }
    }
    o->ayudas = (Ayuda*)AppendListNode((NodoLista*)o->ayudas, (NodoLista*)a);
    a->flags8 = 0x8008;
    a->clave = clave;
    return a;
}

/* Quita de la lista de 'o' el ayudante de la clave dada; detiene el juego si no existe. */
void func_800364E0(ObjetoEscena* o, s32 clave)
{
    NodoClave* e;

    e = func_800361CC((NodoClave*)o->ayudas, clave);
    if (e == 0) {
        for (;;) {
        }
    }
    o->ayudas = (Ayuda*)RemoveListNode((NodoLista*)o->ayudas, (NodoLista*)e);
}

/*
 * Reserva un objeto de escena en el pozo D_8006968C, lo anade a la lista de la escena y lo deja
 * activo con los parametros por omision. Sin salida de error: si el pozo se agota se detiene.
 */
void func_8003652C(void)
{
    ObjetoEscena* o;

    D_800694DC = (ObjetoEscena*)AllocListNode((u8*)D_8006968C, 0x1F4, D_8006955C * 0x1F4);
    if (D_800694DC == 0) {
        for (;;) {
        }
    }
    D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)D_800694DC);
    o = D_800694DC;
    o->w1C = 5;
    o->s2A = 0;
    o->s2C = 7;
    o->cab.libre |= 2;
}

/*
 * Crea el objeto de la camara (D_800694B4) y los 47 objetos de la tabla D_8006AB70, que se
 * anaden a las listas D_80069518 y D_80069508. El objeto de la camara queda activo con la
 * rejilla vacia; los de la tabla, con el estado inicial 1 y la marca de identificador -1. Sin
 * salida de error: si el pozo se agota se detiene.
 */
void func_800365D0(void)
{
    ObjetoEscena* o;
    s32 i;

    D_800694B4 = (ObjetoEscena*)AllocListNode(D_8006968C, 0x1F4, D_8006955C * 0x1F4);
    if (D_800694B4 == 0) {
        for (;;) {
        }
    }
    D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)D_800694B4);
    o = D_800694B4;
    o->w1C = 0;
    o->w8 = 0;
    o->wC = 0;
    o->s2A = 5;
    o->s2C = 6;
    o->s3C = 0x40;
    D_80069508 = 0;
    o->ayudas = 0;
    o->cab.libre |= 2;
    for (i = 0; i < 47; i++) {
        D_8006AB70[i] = (ObjetoEscena*)AllocListNode(D_8006968C, 0x1F4, D_8006955C * 0x1F4);
        if (D_8006AB70[i] == 0) {
            for (;;) {
            }
        }
        D_80069508 = AppendListNode((NodoLista*)D_80069508, (NodoLista*)D_8006AB70[i]);
        D_8006AB70[i]->s3C = 1;
        D_8006AB70[i]->s26 = -1;
        D_8006AB70[i]->ayudas = 0;
    }
}

/*
 * Crea un objeto a partir de la plantilla de identificador 'id' (lista D_80069504): copia sus
 * 0x7D palabras, lo anade a la lista de la escena y a la de objetos solidos, y le pone la
 * posicion 'pos' y los angulos 'ang' si se dan. Devuelve NULL si 'id' no es positivo, no hay
 * plantilla o el pozo esta agotado.
 */
ObjetoEscena* func_80036734(s16 id, s32* pos, u16* ang)
{
    ObjetoEscena* t;
    ObjetoEscena* n;
    ObjetoEscena* l;
    u16 i;

    if (id > 0) {
        for (t = D_80069504; t != 0; t = (ObjetoEscena*)t->cab.siguiente) {
            if (t->w1C == id) {
                n = (ObjetoEscena*)AllocListNode((u8*)D_8006968C, 0x1F4, D_8006955C * 0x1F4);
                if (n == 0) {
                    return 0;
                }
                for (i = 0; i < 0x7D; i++) {
                    ((s32*)n)[(s16)i] = ((s32*)t)[(s16)i];
                }
                n->cab.siguiente = 0;
                D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)n);
                n->coord.param = &n->param;
                n->cab.libre |= 2;
                if (pos != 0) {
                    n->param.trans.vx = pos[0];
                    n->param.trans.vy = pos[1];
                    n->param.trans.vz = pos[2];
                }
                if (ang != 0) {
                    n->param.rotate.vx = ang[0];
                    n->param.rotate.vy = ang[1];
                    n->param.rotate.vz = ang[2];
                }
                l = (ObjetoEscena*)D_80069630;
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

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos", func_8003690C);
