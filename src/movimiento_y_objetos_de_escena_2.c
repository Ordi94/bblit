#include "common.h"
#include "gte.h"
#include "motor.h"

typedef struct Nodo Nodo;
struct Nodo {
    s32 pad0;
    MATRIX mtx;
    u8 pad24[0x44 - 0x24];
    Transformacion* transf;
    Nodo* padre;
};

typedef struct Entidad {
    Nodo* nodo;
    SVECTOR v;
    VECTOR acc;
} Entidad;

extern s16 D_800693F8;
extern s16 D_80069416;
extern s16 D_80069402;

/*
 * Coloca la camara detras de la posicion indicada: la rotacion del objeto controlado aplicada a
 * un vector fijo (0, 0, -100) da el desplazamiento del punto de vista, y la mira queda en la
 * posicion, 400 unidades por debajo. El resultado se copia a las cuatro copias del estado de
 * la camara y se marca la bandera 0x40 de seguimiento fijo.
 */
/* Pendiente: puntuacion 40 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y orden; en la suma de la posicion con el vector rotado el original carga el operando de la posicion en v0 y el del vector en a0, el C los carga al reves. Variantes probadas: 9. */
#ifdef NON_MATCHING
void func_8001CC68(VECTOR* p)
{
    MATRIX m;
    SVECTOR v;
    VECTOR r;
    CamaraMotor* c;
    s32 t;
    u16 ang;

    v.vy = 0;
    v.vx = 0;
    v.vz = -0x64;
    RotMatrix((SVECTOR*)&D_80069698->wDC, &m);
    ApplyMatrix(&m, &v, &r);
    c = CAMARA_MOTOR;
    t = p->vx;
    c->cA4 = t;
    c->x = t;
    t = p->vy - 0x190;
    c->cA8 = t;
    c->y = t;
    t = p->vz;
    c->cAC = t;
    c->z = t;
    t = p->vx + r.vx;
    c->c68 = t;
    c->c94 = t;
    c->vpx = t;
    c->cB4 = t;
    t = p->vy - 0x190;
    c->c6C = t;
    c->c98 = t;
    c->vpy = t;
    c->cB8 = t;
    t = p->vz + r.vz;
    D_800693F8 = 0;
    c->c70 = t;
    c->c9C = t;
    c->vpz = t;
    c->cBC = t;
    ang = D_80069698->wDE + 0x800;
    c->flags80 |= 0x40;
    D_80069416 = ang;
    D_80069402 = ang;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001CC68);
#endif

/*
 * Cursor de animacion de un objeto: fotograma actual en +0, nodo de la secuencia elegida en
 * +0xC, identificador pedido en +0x14 y desplazamiento de la secuencia anterior en +0x1C.
 */
typedef struct CursorAnim {
    RegistroAnim* actual;
    u8 pad04[0x0C - 0x04];
    NodoSecuencia* nodo;
    u8 pad10[0x14 - 0x10];
    u32 id;
    u8 pad18[0x1C - 0x18];
    s32 anterior;
} CursorAnim;

/*
 * Selecciona la secuencia de animacion de identificador `id` en la lista del objeto y deja el
 * cursor en su primer fotograma. Si el fotograma nuevo no conserva el estado del salto (bit 0x40)
 * o es otra secuencia, se reinician los acumuladores de movimiento del objeto.
 */
void func_8001CD84(ObjetoMotor* o, u32 id, CursorAnim* c)
{
    if (o->registro184 != NULL) {
        c->anterior = o->registro184->w06;
    } else {
        c->anterior = 0;
    }
    c->nodo = o->secuencias;
    c->id = id;
    while (c->nodo != NULL && c->nodo->id != id) {
        c->nodo = c->nodo->sig;
    }
    c->actual = (RegistroAnim*)(o->bloque + c->nodo->desplazamiento);
    o->nodo180 = c->nodo;
    o->registro184 = c->actual;
    o->flags14 = o->flags14 & 0xF9FFFDF6;
    if ((c->actual->w08 & 0x40) == 0 || c->actual->w06 != c->anterior) {
        o->i158 = 0;
        o->h146 = 0;
        o->b14C = 0;
        o->w17C = 0;
        o->flags15C = 0;
    }
}

/*
 * Acumula la traslacion de cada nodo de la cadena de padres sobre el vector de una entidad:
 * rota el vector con la matriz del nodo en el GTE, suma la traslacion del nodo, recorta el
 * resultado a 16 bits y sube al nodo padre hasta llegar al raiz.
 */
void func_8001CE64(Entidad* e)
{
    e->v.vx = 0;
    e->v.vy = 0;
    e->v.vz = 0;
    if (e->nodo != NULL) {
        do {
            gte_SetRotMatrix(&e->nodo->mtx);
            gte_ldv0(&e->v);
            gte_rtv0();
            gte_stlvnl(&e->acc);
            e->acc.vx += e->nodo->mtx.t[0];
            e->acc.vy += e->nodo->mtx.t[1];
            e->acc.vz += e->nodo->mtx.t[2];
            e->v.vx = e->acc.vx;
            e->v.vy = e->acc.vy;
            e->v.vz = e->acc.vz;
            e->nodo = e->nodo->padre;
        } while (e->nodo != NULL);
    }
}

/*
 * Reconstruye la matriz de transformacion del objeto desde su transformacion (traslacion,
 * rotacion y escala). No actua si el objeto no tiene matriz propia o si la bandera 0x200000
 * indica que otra rutina la mantiene.
 */
/*
 * Reconstruye la matriz de transformacion del objeto desde su transformacion (traslacion,
 * rotacion y escala). No actua si el objeto no tiene matriz propia o si la bandera 0x200000
 * indica que otra rutina la mantiene.
 */
void func_8001CF50(ObjetoMotor* o)
{
    if (o->p78 != NULL) {
        if ((o->flags08 & 0x200000) == 0) {
            o->w7C = 0;
            TransMatrix(&o->mtx, &o->transf->trans);
            RotMatrix(&o->transf->rot, &o->mtx);
            ScaleMatrix(&o->mtx, &o->transf->escala);
        }
    }
}

/*
 * Reconstruye la matriz del nodo desde su transformacion, en el orden rotacion, escala y
 * traslacion (el inverso del de func_8001CF50).
 */
void func_8001CFCC(Nodo* n)
{
    MATRIX* m;

    m = &n->mtx;
    n->pad0 = 0;
    RotMatrix(&n->transf->rot, m);
    ScaleMatrix(m, &n->transf->escala);
    TransMatrix(m, &n->transf->trans);
}

/*
 * Area de trabajo del desplazamiento entre dos objetos: vector de desplazamiento en +0, copia
 * de la posicion de origen en +0x10, parametros de la consulta de colision en +0x20 (angulo
 * de orientacion en +0x2A) y el resultado de la consulta en +0x38.
 */
typedef struct DesplazamientoObjetos {
    VECTOR d;
    VECTOR origen;
    u8 consulta[0x2A - 0x20];
    u16 h2A;
    u8 pad2C[0x38 - 0x2C];
    s32 w38;
} DesplazamientoObjetos;

/*
 * Lleva el objeto destino a la posicion del origen mas el desplazamiento que permite la
 * colision: calcula la distancia entre ambos, la limita con la consulta y reescribe solo
 * x y z del destino (la altura no se toca).
 */
/* Pendiente: puntuacion 300 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original copia el tercer argumento a a3 al principio y lo reutiliza como cuarto argumento de la llamada, el C lo copia despues. Variantes probadas: 9. */
#ifdef NON_MATCHING
void func_8001D028(ObjetoMotor* origen, ObjetoMotor* destino, u8* p)
{
    DesplazamientoObjetos* w;

    w = (DesplazamientoObjetos*)p;
    w->d.vx = destino->xE4 - origen->xE4;
    w->d.vy = destino->yE8 - origen->yE8;
    w->d.vz = destino->zEC - origen->zEC;
    w->origen.vx = origen->xE4;
    w->origen.vy = origen->yE8;
    w->origen.vz = origen->zEC;
    p += 0x38;
    *(s32*)p = 0;
    w->h2A = origen->w26;
    func_80019474(&w->origen, w, w->consulta, p);
    destino->xE4 = origen->xE4 + w->d.vx;
    destino->zEC = origen->zEC + w->d.vz;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D028);
#endif

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D0FC);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D31C);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D414);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D588);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D75C);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D994);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001DA14);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001DF28);

INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001E1A4);
