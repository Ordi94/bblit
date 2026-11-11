#include "common.h"
#include "gte.h"
#include "motor.h"
#include "menus.h"
#include "eventos.h"


/*
 * Dato pequeno direccionado con desplazamiento($gp): lo define este archivo (definicion
 * tentativa) para que el ensamblador lo reescriba a $gp, y el enlace lo coloca en 0x800693B8.
 * La declaracion compartida vive en globales.h; la definicion se conserva aqui porque
 * func_8001D0FC, func_8001D31C y func_8001D588 lo escriben con sh 0x98($gp) (0x8001D304,
 * 0x8001D3E8, 0x8001D750) y sin ella el acceso pasa a lui mas desplazamiento.
 */
s16 D_800693B8;


/*
 * Coloca la camara detras de la posicion indicada: la rotacion del objeto controlado aplicada a
 * un vector fijo (0, 0, -100) da el desplazamiento del punto de vista, y la mira queda en la
 * posicion, 400 unidades por debajo. El resultado se copia a las cuatro copias del estado de
 * la camara y se marca la bandera 0x40 de seguimiento fijo.
 *
 * Las sumas de la posicion con el vector rotado se escriben una sola vez y las demas copias
 * salen del campo ya escrito: con una variable temporal el compilador carga el vector rotado
 * antes que la posicion y el reparto de v0/a0 queda invertido respecto al original.
 */
void func_8001CC68(VECTOR* p)
{
    MATRIX m;
    SVECTOR v;
    VECTOR r;
    EstadoCamara* c;
    s32 t;
    u16 ang;

    v.vy = 0;
    v.vx = 0;
    v.vz = -0x64;
    RotMatrix(&D_80069698->param.giro.rotate, &m);
    ApplyMatrix(&m, &v, &r);
    c = &D_8006D928;
    t = p->vx;
    c->mira_a4_x = t;
    c->x = t;
    t = p->vy - 0x190;
    c->mira_a4_y = t;
    c->y = t;
    t = p->vz;
    c->mira_a4_z = t;
    c->z = t;
    c->vista_68_x = p->vx + r.vx;
    c->vista_94_x = c->vista_68_x;
    c->vpx = c->vista_68_x;
    c->vista_b4_x = c->vista_68_x;
    t = p->vy - 0x190;
    c->vista_68_y = t;
    c->vista_94_y = t;
    c->vpy = t;
    c->vista_b4_y = t;
    D_800693F8 = 0;
    c->vista_68_z = p->vz + r.vz;
    c->vista_94_z = c->vista_68_z;
    c->vpz = c->vista_68_z;
    c->vista_b4_z = c->vista_68_z;
    ang = D_80069698->param.giro.u.y + 0x800;
    c->flags80 |= 0x40;
    D_80069416 = ang;
    D_80069402 = ang;
}

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
void func_8001CD84(Objeto* o, u32 id, CursorAnim* c)
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
    o->p180 = c->nodo;
    o->registro184 = c->actual;
    o->flags14 = o->flags14 & 0xF9FFFDF6;
    if ((c->actual->w08 & 0x40) == 0 || c->actual->w06 != c->anterior) {
        o->trabajo.i14 = 0;
        o->trabajo.cuadro = 0;
        o->trabajo.ticks = 0;
        o->w17C = 0;
        o->trabajo.flags18 = 0;
    }
}

/*
 * Acumula la traslacion de cada nodo de la cadena de padres sobre el vector de una entidad:
 * rota el vector con la matriz del nodo en el GTE, suma la traslacion del nodo, recorta el
 * resultado a 16 bits y sube al nodo padre hasta llegar al raiz.
 */
void func_8001CE64(AcumuladorNodos* e)
{
    e->v.vx = 0;
    e->v.vy = 0;
    e->v.vz = 0;
    if (e->nodo != NULL) {
        do {
            gte_SetRotMatrix(&e->nodo->coord);
            gte_ldv0(&e->v);
            gte_rtv0();
            gte_stlvnl(&e->acc);
            e->acc.vx += e->nodo->coord.t[0];
            e->acc.vy += e->nodo->coord.t[1];
            e->acc.vz += e->nodo->coord.t[2];
            e->v.vx = e->acc.vx;
            e->v.vy = e->acc.vy;
            e->v.vz = e->acc.vz;
            e->nodo = e->nodo->super;
        } while (e->nodo != NULL);
    }
}

/*
 * Reconstruye la matriz de transformacion del objeto desde su transformacion (traslacion,
 * rotacion y escala). No actua si el objeto no tiene matriz propia o si la bandera 0x200000
 * indica que otra rutina la mantiene.
 */
void func_8001CF50(Objeto* o)
{
    if (o->u78.p != NULL) {
        if ((o->flags08 & 0x200000) == 0) {
            o->coord.flg = 0;
            TransMatrix(&o->coord.coord, &o->coord.param->trans);
            RotMatrix(&o->coord.param->rotate, &o->coord.coord);
            ScaleMatrix(&o->coord.coord, &o->coord.param->scale);
        }
    }
}

/*
 * Reconstruye la matriz del nodo desde su transformacion, en el orden rotacion, escala y
 * traslacion (el inverso del de func_8001CF50).
 */
void func_8001CFCC(GsCOORDINATE2* n)
{
    MATRIX* m;

    m = &n->coord;
    n->flg = 0;
    RotMatrix(&n->param->rotate, m);
    ScaleMatrix(m, &n->param->scale);
    TransMatrix(m, &n->param->trans);
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
 *
 * El argumento p se avanza 0x38 bytes justo despues de copiarlo a w: mientras p valga lo mismo que w
 * el compilador usa uno solo de los dos registros para los almacenes; al cambiar p, los almacenes
 * usan w (registro salvado) y la copia de p queda en el registro del cuarto argumento de la llamada,
 * como en el original.
 */
void func_8001D028(Objeto* origen, Objeto* destino, u8* p)
{
    DesplazamientoObjetos* w;

    w = (DesplazamientoObjetos*)p;
    p += 0x38;
    w->d.vx = destino->param.trans.vx - origen->param.trans.vx;
    w->d.vy = destino->param.trans.vy - origen->param.trans.vy;
    w->d.vz = destino->param.trans.vz - origen->param.trans.vz;
    w->origen.vx = origen->param.trans.vx;
    w->origen.vy = origen->param.trans.vy;
    w->origen.vz = origen->param.trans.vz;
    *(s32*)p = 0;
    w->h2A = origen->w26;
    BarrerTerreno(&w->origen, w, w->consulta, p);
    destino->param.trans.vx = origen->param.trans.vx + w->d.vx;
    destino->param.trans.vz = origen->param.trans.vz + w->d.vz;
}

/*
 * Estado de la busqueda de una secuencia de animacion del objeto controlado: fotograma elegido
 * en +0, fotograma de apoyo en +4, desplazamiento de la secuencia en +8, nodo de la lista
 * de secuencias en +0xC y, desde +0x10, el area de trabajo del desplazamiento entre objetos.
 */
typedef struct BusquedaAnim {
    NodoSecuencia* fotograma;
    NodoSecuencia* apoyo;
    s32 desplazamiento;
    NodoSecuencia* nodo;
    DesplazamientoObjetos desp;
} BusquedaAnim;

/*
 * Asigna al objeto controlado la animacion de identificador `id` (secuencia, fotograma y apoyo
 * localizados en las tres listas del objeto) salvo que este bloqueado por la bandera
 * 0x1000000. Si el fotograma pide soltar la carga (bit 0x800) apaga las banderas 0x209, y si
 * el objeto controlado lleva otro objeto en brazos (p6C) y no es del tipo 0x22 lo coloca
 * delante, le copia orientacion y rotacion y lo enlaza a su propia lista. Anula el seguimiento.
 */
/*
 * El argumento b se avanza al area de trabajo del desplazamiento (+0x10) nada mas entrar y las
 * busquedas usan una copia (busqueda): el original deja el area en un registro guardado, que
 * sobrevive a las llamadas del final, y la estructura de busqueda en un temporal. Las dos
 * lecturas de D_80069698 (la asignacion de la animacion y la entrega de la carga) llevan
 * variables distintas (controlado y portador) porque sus vidas no se solapan y el original las
 * reparte en registros distintos.
 */
void func_8001D0FC(Objeto* otro, u32 id, BusquedaAnim* b)
{
    Objeto* controlado;
    Objeto* portador;
    Objeto* llevado;
    BusquedaAnim* busqueda;

    busqueda = b;
    b = (BusquedaAnim*)((u8*)b + 0x10);
    if (!(D_80069698->flags14 & 0x1000000)) {
        busqueda->nodo = D_80069698->secuencias;
        while (busqueda->nodo != NULL && busqueda->nodo->id != id) {
            busqueda->nodo = busqueda->nodo->sig;
        }
        busqueda->desplazamiento = busqueda->nodo->desplazamiento;
        busqueda->fotograma = (NodoSecuencia*)D_80069698->bloque;
        while (busqueda->fotograma != NULL && busqueda->fotograma->id != busqueda->desplazamiento) {
            busqueda->fotograma = busqueda->fotograma->sig;
        }
        busqueda->apoyo = D_80069698->apoyos;
        while (busqueda->apoyo != NULL && busqueda->apoyo->id != busqueda->fotograma->w0A) {
            busqueda->apoyo = busqueda->apoyo->sig;
        }
        controlado = D_80069698;
        controlado->w17C = id;
        controlado->p180 = busqueda->nodo;
        controlado->registro184 = (RegistroAnim*)busqueda->fotograma;
        controlado->nodo188 = busqueda->apoyo;
        controlado->trabajo.i14 = 0;
        controlado->raiz_ayudantes = 0;
        if (busqueda->fotograma->w10 & 0x800) {
            D_80069698->flags14 &= ~0x209;
        }
        portador = D_80069698;
        llevado = portador->p6C;
        portador->w17E = 0;
        portador->param.giro.u.z = 0;
        if (llevado != NULL && llevado->clase != 0x22) {
            llevado->coord.param = PARAMETROS_SDK(llevado);
            llevado->coord.super = NULL;
            llevado->flags14 = (llevado->flags14 & ~0x800) | 0x1000;
            llevado->w26 = otro->w26;
            llevado->param.giro.u.x = portador->param.giro.u.x;
            llevado->param.giro.u.y = portador->param.giro.u.y;
            llevado->param.giro.u.z = portador->param.giro.u.z;
            llevado->p70 = NULL;
            portador->p6C = NULL;
            func_8001CFCC(&llevado->coord);
            func_8001D028(D_80069698, llevado, (u8*)b);
        }
        D_800693B8 = -1;
    }
}

/*
 * Coloca al objeto controlado en (x, y, z): suelta lo que lleve en brazos (el objeto enlazado
 * en +0x70 vuelve a la lista de su propietario y se apagan las banderas 0x14), actualiza la
 * posicion y, salvo que el estado del nivel lo impida (mascara 0x304) o el contador de
 * guardado este activo, recoloca la camara detras de la nueva posicion. Termina apagando la
 * bandera 4 de la camara, anulando la bandera de seguimiento y encendiendo la de reinicio.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo; ejes 2 de operando, 0 reordenadas, 29 insertadas o borradas). Difiere en: reparto de registros del prologo. El original copia el primer argumento a a3 antes de cargar D_80069698 (puntero en a0, objeto llevado en v0 con su copia en v1); aqui el puntero queda en v1, el objeto llevado en a3 y la copia de x en t0, que ocupa el hueco de retardo del salto que en el original ocupa la copia del objeto llevado. El compilador funde la copia que el original conserva y no se ha encontrado una forma que la mantenga. */
void func_8001D31C(s32 x, s32 y, s32 z)
{
    VECTOR destino;
    Objeto* llevado;
    s32 x_copia;

    x_copia = x;
    llevado = D_80069698->p70;
    if (llevado != NULL) {
        D_80069698->coord.super = NULL;
        D_80069698->coord.param = PARAMETROS_SDK(D_80069698);
        llevado->p6C = D_80069698;
        if (D_80069698 != NULL) {
            D_80069698->p70->p6C = NULL;
        }
        D_80069698->p70 = NULL;
        D_80069698->flags14 &= ~0x14;
    }
    /* La posicion se escribe como tres palabras sueltas y no como campos de la estructura: con campos,
     * el planificador sube la lectura de D_8006D9A8 por encima de los almacenes (el original la deja
     * despues); medido, basta dejar uno solo como campo para que la puntuacion pase de 190 a 745 o mas.
     * Se supone, sin verificar en el volcado, que un acceso a miembro de estructura no se ordena frente
     * a una lectura que no lo es. */
    *(s32*)&D_80069698->param.trans.vx = x_copia;
    *(s32*)&D_80069698->param.trans.vy = y;
    *(s32*)&D_80069698->param.trans.vz = z;
    if (!(*(u32*)D_8006D9A8 & 0x304)) {
        if ((s8)D_80010076 <= 0) {
            destino.vx = x_copia;
            destino.vy = y;
            destino.vz = z;
            func_8001CC68(&destino);
        }
    }
    D_800693B8 = -1;
    D_80069608 |= 1;
    D_8006D928.flags80 &= 0xFFFB;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D31C);
#endif

/*
 * Sincroniza dos banderas de estado del objeto controlado (bits 8 y 0x10 de D_800694F2) con su
 * situacion: el bit 8 sigue a la bandera 0x10000 del objeto y el 0x10 a la 4 del objeto
 * combinada con la pulsacion de boton (D_8001000A & 0xF000) cuando el codigo de accion es
 * 0x8B. Cada cambio avisa a func_8003F06C con el codigo de aviso (0xD y 0x1B) y 1 al encender
 * o 2 al apagar.
 */
void func_8001D414(s16 accion)
{
    if (D_80069698->flags14 & 0x10000) {
        if (!(D_800694F2 & 8)) {
            D_800694F2 = D_800694F2 | 8;
            func_8003F06C(D_80069698, 0xD, 1, D_8006967C);
        }
    } else if (D_800694F2 & 8) {
        D_800694F2 = D_800694F2 & 0xF7;
        func_8003F06C(D_80069698, 0xD, 2, D_8006967C);
    }
    if (D_80069698->flags18 & 4) {
        if ((D_8001000A & 0xF000) && accion == 0x8B) {
            if (!(D_800694F2 & 0x10)) {
                D_800694F2 = D_800694F2 | 0x10;
                func_8003F06C(D_80069698, 0x1B, 1, D_8006967C);
            }
        } else if (D_800694F2 & 0x10) {
            D_800694F2 = D_800694F2 & 0xEF;
            func_8003F06C(D_80069698, 0x1B, 2, D_8006967C);
        }
    } else if (D_800694F2 & 0x10) {
        D_800694F2 = D_800694F2 & 0xEF;
        func_8003F06C(D_80069698, 0x1B, 2, D_8006967C);
    }
}

/*
 * Deja al objeto controlado listo para una escena guionizada: borra los contadores de
 * vibracion, fija el modo de la maquina de estados (a0), activa 0x1000004 y quita 0x10000 de
 * las banderas, suelta lo que lleve en brazos y al objeto que lo acompana (con la bandera
 * 0x100 si es del tipo 0x22), y si se da una posicion coloca al objeto y a la camara en ella
 * mirando hacia delante. Termina refrescando las banderas de situacion y anulando el
 * seguimiento.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 110 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 20 insertadas o borradas). Difiere en: copia del objeto enlazado, alias del objeto controlado y orden de un almacen. Mismas operaciones y almacenes; el original carga el objeto enlazado en +0x70 en v0 y lo copia a v1 en el hueco de retardo del salto (aqui se carga directo en v1), usa el objeto controlado en a2 sin copiarlo (aqui el alias de la variable `e` lo copia a a0) y ejecuta el almacen de la coordenada z del objeto (sw 0xec) antes del de cero a D_80069402 (el planificador lo hunde tras el). Leer p->vz por su desplazamiento (+8) antes de los almacenes al objeto, y las banderas y el enlace por su desplazamiento en bytes, mantiene las cargas tras los almacenes de bytes a D_8006965A y D_80069659 como en el original; la copia aparte del acompanante baja 5. */
void func_8001D588(s32 modo, VECTOR* p)
{
    Objeto* e;
    s32 pos_z;
    EstadoCamara* c;
    Objeto* j;
    Objeto* t;
    Objeto* acompanante;
    u16 ang;

    D_8006965A = 0;
    D_80069659 = 0;
    j = D_80069698;
    j->w17E = 0;
    j->w17C = modo;
    /* Las banderas y el enlace +0x70 se leen por su desplazamiento en bytes y no como miembros: asi el
     * planificador no sube la carga sobre los almacenes de bytes anteriores (ver la nota de pendiente). */
    j->flags14 = (*(u32*)((u8*)j + 0x14) | 0x1000004) & 0xFFFEFFFF;
    c = &D_8006D928;
    c->s88 = 0;
    c->h8C = 0;
    c->h8E = 0;
    t = *(Objeto**)((u8*)j + 0x70);
    D_80069690 = 0;
    D_800693F6 = 0;
    if (t != NULL) {
        j->coord.super = NULL;
        /* Alias del objeto controlado en la misma variable que luego recibe el acompanante:
         * separarlas sube la puntuacion de 110 a 175. */
        e = j;
        j->coord.param = PARAMETROS_SDK(j);
        t->p6C = NULL;
        e->p70 = NULL;
        j->flags14 &= ~0x14;
    }
    e = D_80069698->p6C;
    acompanante = e; /* copia aparte: la puntuacion es 115 sin ella frente a 110 con ella */
    if (acompanante != NULL) {
        if (acompanante->clase == 0x22) {
            acompanante->flags14 |= 0x100;
        }
        acompanante->coord.param = PARAMETROS_SDK(acompanante);
        acompanante->coord.super = NULL;
        acompanante->p70 = NULL;
        acompanante->flags14 = (acompanante->flags14 & ~0x800) | 0x1000;
        D_80069698->p6C = NULL;
        func_8001CFCC(&acompanante->coord);
    }
    if (p != NULL) {
        D_80069698->param.trans.vx = p->vx;
        D_80069698->param.trans.vy = p->vy;
        /* La coordenada z de la posicion se lee por su desplazamiento en bytes (+8), como en el original. */
        pos_z = *(s32*)((u8*)p + 8);
        D_80069698->param.giro.u.y = 0;
        D_80069698->param.trans.vz = pos_z;
        D_80069402 = 0;
        D_8006D928.vpx = p->vx;
        D_8006D928.vpy = p->vy;
        D_8006D928.vpz = *(s32*)((u8*)p + 8);
        D_8006D928.x = p->vx;
        D_8006D928.y = p->vy;
        D_8006D928.z = p->vz;
        ang = D_80069698->param.giro.u.y + 0x800;
        D_80069416 = ang;
        D_80069402 = ang;
    }
    func_8001D414(0);
    D_800693B8 = -1;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D588);
#endif

/*
 * El objeto `otro` golpea al controlado. Devuelve 1 si el golpe se aplica (resta salud a
 * D_80010041, reinicia el contador de invulnerabilidad D_80069690 a 30 cuadros y marca los
 * golpes recibidos) y 0 si lo impiden el estado del juego (menus, pausa, bandera 0x1000000
 * del objeto controlado) o el fotograma actual no admite golpe (bit 0x4000). El dano es el
 * del propio objeto (w1E) si es del tipo 0x1F, el del atacante `a1` (2 como maximo) o 1.
 * `a1` es el fotograma de animacion del atacante (w0C con el bit 0x200000 = golpe leve, w16 =
 * dano). El prototipo compartido de niveles.h declara ademas un tercer argumento (el area de trabajo
 * del llamador) que esta definicion no usa y no declara: con el parametro el reparto de registros
 * de `otro` cambia y la puntuacion sube.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador. */
s32 func_8001D75C(Objeto* otro, RegistroAnim* a1)
{
    Objeto* j;
    u32 estado;
    s32 danio;
    u32 v1;

    if (D_80069690 > 0) {
        return 0;
    }
    if (D_80069662 != 0) {
        return 0;
    }
    if ((s8)D_8006966A != 0) {
        return 0;
    }
    if (D_8006AA70[3] != 0) {
        return 0;
    }
    estado = D_8006D9A8[0];
    if (((estado & 0x100) || D_80069698->flags14 < 0) && (estado & 0x200) == 0) {
        return 0;
    }
    j = D_80069698;
    if (j->flags14 & 0x1000000) {
        return 0;
    }
    otro->flags14 |= 0x8000;
    if (j->registro184 == NULL) {
        return 0;
    }
    if (!(j->registro184->w0C & 0x4000)) {
        return 0;
    }
    j->id_atacante = otro->w1C;
    otro->id_atacante = 1;
    if (otro->clase == 0x1F) {
        /* 0x8001D860: lhu 0x1E(a3) y 0x8001D870: lbu 0x1E(a3); el campo es s16 para el interprete de eventos (lh), asi que el dano se lee sin signo con la conversion. */
        j->w38 = (u16)otro->s1E;
        D_80069690 = 0x1E;
        D_80010041 -= (u8)otro->s1E;
        goto marcar;
    }
    if (a1 != NULL) {
        if (!((otro->flags08 & 0x10000000) && (otro->flags14 & 1)) && !(a1->w0C & 0x200000)) {
            danio = (s16)a1->w16;
            if (danio != 0) {
                if (danio >= 3) {
                    danio = 2;
                }
                j->w38 = danio;
                D_80069690 = 0x1E;
                D_80010041 -= danio;
marcar:
                j->flags14 |= 0x2000000;
            }
            goto fin;
        }
    }
    D_80069698->w38 = 1;
    D_80069690 = 0x1E;
    D_80010041 -= 1;
    D_80069698->flags14 |= 0x2000000;
fin:
    v1 = otro->flags18;
    otro->flags18 = v1 | 0x4000;
    if ((s8)D_80010041 <= 0) {
        otro->flags18 = v1 | 0x6000;
    }
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001D75C);
#endif

/*
 * Reinicia al objeto controlado en el punto de reaparicion guardado (D_8006ACD0): borra sus
 * banderas, copia posicion y orientacion, coloca la camara detras, fija 30 cuadros de
 * invulnerabilidad y la salud a 6, y lanza el efecto de fundido 1 de 0x200 cuadros.
 */
void func_8001D994(Objeto* o)
{
    /* El original reserva 0x38 bytes de pila que el codigo no llega a usar. */
    u8 reserva[0x38];

    o->flags14 = 0;
    o->param.trans.vx = D_8006ACD0.x;
    o->param.trans.vy = D_8006ACD0.y;
    o->param.trans.vz = D_8006ACD0.z;
    D_80069402 = (u16)D_8006ACD0.ang;
    o->param.giro.u.y = (u16)D_8006ACD0.ang;
    func_8001CC68((VECTOR*)&D_8006ACD0);
    D_80069690 = 0x1E;
    D_80010041 = 6;
    func_8003AA50(1, 0x200);
}

/*
 * Area de trabajo de la busqueda de rumbo: angulo de prueba en +0 (x, y, z), desplazamiento
 * pedido en +8, matriz de rotacion en +0x10, desplazamiento rotado en +0x30, posicion de
 * partida en +0x40, resultado de la baldosa en +0x54, punto de consulta en +0x7C, grupo
 * encontrado en +0x8C y area de la consulta de baldosa en +0x90.
 */
typedef struct PasoBusqueda {
    SVECTOR rot;
    SVECTOR delta;
    MATRIX m;
    s32 v30;
    s32 v34;
    s32 v38;
    u8 pad3C[4];
    s32 pos40;
    s32 pos44;
    s32 pos48;
    u8 pad4C[4];
    s32 w50;
    ResultadoBaldosa res;
    u8 pad6C[0x7C - 0x6C];
    s32 p7C;
    s32 p80;
    s32 p84;
    u8 pad88[4];
    s32 w8C;
    TrabajoBaldosa tb;
} PasoBusqueda;

extern u16 D_8005E064[];
extern u16 D_8005E078[];

/*
 * Busca el rumbo libre para mover al objeto: prueba hasta nueve desviaciones de la tabla de
 * angulos (D_8005E064, o D_8005E078 con el bit 0x80000 de a3) hasta que el desplazamiento rotado
 * no choque (BarrerTerreno) y el suelo de la baldosa lo permita. a2 elige el modo: 0x80000 ignora
 * el borde de los precipicios y 0x40000000 fija la orientacion del objeto al resultado. El
 * desplazamiento realizado queda en `mov`.
 */
void func_8001DA14(Objeto* o, Movimiento* mov, u32 a2, u32 a3, PasoBusqueda* w)
{
    u16* tabla;
    s32 intento;
    s32 centrado;
    s32 estado;
    s32 banderas_paso;
    u16 banderas;
    s32 banderas_enlace;
    s32 bloqueos;
    s32 quitar_apoyo;
    /* Direcciones de los tres bloques del area que se pasan a BarrerTerreno y a func_8001C134.
     * Se guardan en locales (y no se escriben &w->campo en cada llamada) porque el original las
     * mantiene en registros salvados con este reparto: el bloque de trabajo de baldosa en el
     * primero, el modo centrado en el segundo, el resultado en el tercero y el desplazamiento
     * en el cuarto; el orden de asignacion fija la prioridad de cada uno. */
    s32* desplazamiento;
    ResultadoBaldosa* resultado;
    TrabajoBaldosa* trabajo;

    trabajo = &w->tb;
    w->pos40 = o->param.trans.vx;
    w->pos44 = o->param.trans.vy;
    w->pos48 = o->param.trans.vz;
    w->delta.vx = mov->x;
    w->delta.vy = mov->dy;
    w->delta.vz = mov->z;
    w->rot.vx = o->param.giro.u.x;
    w->rot.vz = o->param.giro.u.z;
    if (a3 & 0x80000) {
        tabla = D_8005E078;
    } else {
        tabla = D_8005E064;
    }
    intento = 0;
    desplazamiento = &w->v30;
    resultado = &w->res;
    centrado = a2 & 0x80000;
    do {
        w->rot.vy = tabla[intento];
        RotMatrix(&w->rot, &w->m);
        gte_SetRotMatrix(&w->m);
        gte_ldv0(&w->delta);
        gte_rtv0();
        gte_stlvnl(desplazamiento);
        w->w50 = w->v30 + w->v38;
        w->pos44 = o->param.trans.vy;
        trabajo->x_local = 0;
        w->res.grupo = o->w26;
        BarrerTerreno(&w->pos40, desplazamiento, resultado, trabajo);
        w->w8C = (s16)w->res.grupo;
        w->w50 = w->w50 - (w->v30 + w->v38);
        estado = o->flags14;
        if (!(estado & 4)) {
            banderas = w->res.flags;
            if (banderas & 8) {
                w->p7C = w->pos40 + w->v30;
                w->p80 = w->pos44 + 1;
                w->p84 = w->pos48 + w->v38;
                w->res.grupo = o->w26;
                func_8001C134(&w->p7C, resultado, trabajo);
                if ((s16)w->res.grupo == -1) {
                    w->res.flags = w->res.flags | 8;
                    w->res.grupo = o->w26;
                } else {
                    banderas_enlace = w->res.flags;
                    if ((banderas_enlace & 2) && (w->res.suelo - o->param.trans.vy) >= 0xC9) {
                        w->res.flags = (banderas_enlace & ~6) | 8;
                    }
                }
            } else if ((banderas & 2) && !(estado & 0x219) && (((s16)w->res.pendiente_abs + w->pos44) - o->param.trans.vy) >= 0xC9) {
                /* La mascara pasa por una local: con la constante en la expresion el compilador
                 * la pliega y reparte los registros de otro modo. */
                quitar_apoyo = ~6;
                w->res.flags = (banderas & quitar_apoyo) | 8;
            }
        } else {
            w->res.flags = (w->res.flags & ~8) | 2;
        }
        o->h10C = w->res.pendiente_abs;
        banderas_paso = w->res.flags;
        if ((banderas_paso & 4) || (centrado == 0 && (banderas_paso & 8)) || w->w50 != 0) {
            o->flags14 |= 0x100000;
        }
        if (w->res.flags & 8) {
            o->flags18 |= 0x20;
        }
        if ((a2 & 0x40000000) || w->w8C == (s16)o->w26) {
            bloqueos = (s16)w->res.flags;
            if (centrado == 0) {
                bloqueos = bloqueos & 0xC;
            } else {
                bloqueos = bloqueos & 4;
            }
            if (bloqueos == 0 && w->w50 == 0) {
                break;
            }
        }
        intento++;
    } while (intento < 9);
    if (a2 & 0x40000000) {
        if (o->p70 == D_80069698) {
            o->w26 = *D_80069558;
        } else {
            o->w26 = w->w8C;
        }
    }
    if (((o->flags18 & 0x20) && !(a2 & 0x80000))
        || (!(a2 & 0x40000000) && !(o->flags14 & 0x100000) && intento < 9)) {
        o->param.giro.u.y = o->param.giro.u.y + w->rot.vy;
    } else {
        o->param.giro.u.y = o->param.giro.u.y + ((s16)tabla[intento] >> 3);
    }
    if (intento == 9 && (o->flags14 & 0x100000)) {
        o->param.giro.u.y = o->param.giro.u.y + 0x800;
        mov->z = 0;
        mov->dy = 0;
        mov->x = 0;
        return;
    }
    mov->x = w->v30;
    mov->dy = w->v34;
    mov->z = w->v38;
}

/*
 * Proyecta el objeto en pantalla y calcula las esquinas de su sprite: si esta mas cerca de 150
 * unidades lo oculta (apaga la bandera 2 y enciende 0x100) y si no, escala su tamano con la
 * profundidad y reparte el recorte entre las dos mitades cuando la bandera 0x8000000 pide
 * centrar. Guarda la profundidad en el objeto (no negativa) y enciende la bandera 2.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 585 con la configuracion versionada (g = 8 del archivo). Mismo codigo GTE y mismas operaciones; solo difiere el bloque de la bandera 0x8000000: el original calcula h52 antes que h94, repite el desplazamiento `(s16)alto >> 1` en dos expresiones sin fundirlas y resta el valor de 32 bits de h94 de h4E sin releerlo, mientras que GCC funde el desplazamiento, calcula primero h94 y relee la mitad con signo de 16 bits. */
void* func_8001DF28(Objeto* o, ProyeccionSprite* b)
{
    Objeto* objeto;
    s32 alto;
    u16 coordenada;
    s16* p;
    s32 medida_doble;
    s32 mitad_inferior;
    s32 z;

    /* Copia local del objeto: sin ella el reparto de a2 y a3 empeora; el segundo argumento no se copia. */
    objeto = o;
    b->coordenadas = (s16*)((u8*)objeto->u78.p + 0xC);
    b->pos.vx = objeto->param.trans.vx;
    b->pos.vy = objeto->param.trans.vy;
    b->pos.vz = objeto->param.trans.vz;
    gte_SetRotMatrix(&D_80076130);
    gte_SetTransVector(&D_80076144);
    gte_ldv0(&b->pos);
    gte_rtps();
    MOTOR_GUARDAR_MAC3(&b->z54);
    if (b->z54 < 0x96) {
        objeto->flags04 &= ~2;
        objeto->flags18 |= 0x100;
        return &b->w58;
    }
    b->escala = 0x190000 / (b->z54 | 1);
    gte_stsxy2(&b->h4C);
    b->w5C = 0;
    b->w58 = 0x808080;
    /* El doble de cada medida pasa por una variable de 32 bits asignada justo antes de su producto: asi la escala se lee despues de la medida, como en el original. */
    medida_doble = objeto->max.vx * 2;
    b->h50 = b->h4C + (((medida_doble * b->escala) >> 12) * objeto->param.escala.vx >> 12);
    medida_doble = objeto->min.vx * 2;
    b->h4C = b->h4C + (((medida_doble * b->escala) >> 12) * objeto->param.escala.vx >> 12);
    medida_doble = objeto->max.vy * 2;
    alto = ((((medida_doble * b->escala) >> 12) * objeto->param.escala.vy) >> 12) * 15 >> 5;
    b->h94 = alto;
    if (objeto->flags0C & 0x8000000) {
        b->h52 = b->h4E + ((s16)alto >> 1);
        b->h94 = alto - ((s16)alto >> 1);
        /* La altura ya guardada se relee con signo de 16 bits antes de restarla de h4E. */
        mitad_inferior = (s16)b->h94;
        b->h4E -= mitad_inferior;
    } else {
        b->h52 = alto + b->h4E;
    }
    p = b->coordenadas;
    /* Las coordenadas se copian por una variable sin signo de 16 bits (lhu) y no por una de 32 bits (lh). */
    coordenada = b->h4C;
    p[8] = coordenada;
    p[0] = coordenada;
    p = b->coordenadas;
    coordenada = b->h52;
    p[5] = coordenada;
    p[1] = coordenada;
    p = b->coordenadas;
    coordenada = b->h50;
    p[12] = coordenada;
    p[4] = coordenada;
    p = b->coordenadas;
    coordenada = b->h4E;
    p[13] = coordenada;
    p[9] = coordenada;
    z = b->z54;
    objeto->param.escala.vz = z;
    if (z < 0) {
        objeto->param.escala.vz = 0;
    }
    objeto->flags04 |= 2;
    return &b->w58;
}
#else
INCLUDE_ASM("asm/nonmatchings/movimiento_y_objetos_de_escena_2", func_8001DF28);
#endif

/*
 * Evento de zona: registro de la lista que cuelga de cada nodo de plano (+0x30). Siguiente en
 * +0, tipo de objeto en +4, mascara de banderas en +8, elemento de logica en +0xC (la
 * condicion es el byte +0xC y la accion el byte +0xF), banderas de efecto en +0x14 y tres
 * valores (posicion o parametros) en +0x18, +0x1C y +0x20.
 */
typedef struct EventoZona {
    struct EventoZona* sig;
    s32 tipo;
    s32 mascara;
    u8 cond;
    u8 pad0D[2];
    u8 accion;
    u8 pad10[4];
    s32 flags;
    s32 v18;
    s32 v1C;
    s32 v20;
} EventoZona;

/* Definida en graficos_y_gte.c: devuelve el nodo de plano que toca el objeto (sin prototipo en las cabeceras, el retorno se tomaba como int). */
extern NodoVolumen* func_80019180(Objeto* a, VECTOR* p, ConsultaPlano* o);

/*
 * Recorre los eventos de la zona que toca el objeto (consulta de plano) y ejecuta los que le
 * corresponden: mismo tipo de objeto, mascara de banderas compatible y condicion cumplida. Cada
 * evento aplica los efectos que pidan sus banderas (accion, reaparicion, cambio de nivel, cambio de
 * secuencia de animacion, camara) y la lista continua solo si el evento lo permite (0x8000).
 *
 * Los dos pares `z--; z++` del bucle no generan codigo: el combinador los anula despues de la optimizacion de
 * bucles, pero hasta entonces suman cuatro instrucciones al bucle. El original iza fuera del bucle la direccion de
 * D_8006ACD0 y deja la de D_8006B558 dentro; el optimizador de bucles iza la de D_8006B558 cuando el bucle tiene
 * 174 instrucciones o menos y no la iza con 175 o mas. Medido en el volcado de bucles (`-dL`, `.loop`): el
 * pseudo que se iza es el (regno) 119, de vida 6 y con un ahorro de 1 instruccion al izarlo; con el bucle de 174
 * instrucciones el volcado dice `moved to 540` y con 175 (el argumento con `(s16)`) y con 176 (los dos pares)
 * dice `move-insn savings 1 not desirable`; sin los pares ni la conversion el bucle queda en 172 y tambien se
 * iza. Que el umbral sea 29 * ahorro * vida >= instrucciones del bucle (29 * 1 * 6 = 174) es una inferencia de
 * esos dos puntos, sin verificar contra el codigo del optimizador. Con los pares el argumento de func_8003F06C se
 * carga con lw sin conversion, como el original. La forma del fuente original que producia este reparto se
 * desconoce.
 */
void func_8001E1A4(Objeto* o, ConsultaPlano* c)
{
    VECTOR destino;
    EventoZona* z;
    NodoVolumen* nodo;
    Objeto* soltar;
    s32 f;
    s32* ref;

    if (D_80069662 != 0) {
        return;
    }
    nodo = func_80019180(o, (VECTOR*)&o->param.trans.vx, c);
    if (nodo == NULL) {
        return;
    }
    z = *(EventoZona**)((u8*)nodo + 0x30);
    while (z != NULL) {
        z--;
        z++;
        z--;
        z++;
        if (!((o->w1C != 6 && z->tipo != 6) || !(o->flags0C & 2))) {
            o->flags14 |= 0x100;
            return;
        }
        if (o->w1C == z->tipo && (z->mascara == 0 || (o->flags14 & z->mascara))
            && (z->cond == 0 || TestLogicCond(o, &z->cond) != 0)) {
            if (z->accion != 0) {
                RunLogicAction(o, &z->cond);
            }
            if (z->flags < 0) {
                func_8001D0FC(o, z->v18, (BusquedaAnim*)c);
            }
            if (z->flags & 0x800) {
                func_8001D31C(z->v18, z->v1C, z->v20);
            }
            if (z->flags & 0x800000) {
                D_8006B558[0] = z->v18;
                D_8006B558[1] = z->v1C;
                D_8006B558[2] = z->v20;
            }
            if (z->flags & 0x40000000) {
                soltar = o->p70;
                o->param.trans.vx = z->v18;
                o->param.trans.vy = z->v1C;
                o->param.trans.vz = z->v20;
                if (soltar != NULL) {
                    if (soltar->p6C == o) {
                        soltar->p6C = NULL;
                    }
                    o->coord.param = PARAMETROS_SDK(o);
                    o->coord.super = NULL;
                    o->p70 = NULL;
                    o->flags14 = (o->flags14 & ~0x14) | 0x202;
                    func_8001CFCC(&o->coord);
                }
            }
            if (z->flags & 0x80000) {
                D_80069662 = 1;
                D_80010000 = z->v18;
            }
            if (z->flags & 0x200000) {
                func_8001D588(z->v18, NULL);
                D_80010041 = 0;
            }
            if (z->flags & 0x400000) {
                D_800694F8 = z->v18;
            }
            if (z->flags & 0x100000) {
                D_8006ACD0.x = z->v18;
                D_8006ACD0.y = z->v1C;
                D_8006ACD0.z = z->v20;
                if (D_80069698 != NULL) {
                    D_8006ACD0.ang = (s16)D_80069698->param.giro.u.y;
                } else {
                    D_8006ACD0.ang = 0;
                }
            }
            f = z->flags;
            if (f & 0x10000) {
                o->flags14 |= 0x100;
                return;
            }
            if (f & 0x200) {
                func_8003F06C(NULL, z->v18, 1, D_8006967C);
            }
            if (z->flags & 0x2000) {
                func_8001CD84(o, z->v18, (CursorAnim*)c);
            }
            if (z->flags & 0x40) {
                destino.vx = z->v18;
                destino.vy = z->v1C;
                destino.vz = z->v20;
                func_8001CC68(&destino);
            }
            if (!(z->flags & 0x8000)) {
                return;
            }
        }
        z = z->sig;
    }
}
