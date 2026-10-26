#include "common.h"
#include "objetos.h"

/*
 * Vista del ayudante a partir de +0x0C: el puntero a su GsCOORDINATE2 (+0x10 del nodo) y la
 * bandera de visibilidad (+0xB4 del nodo). Las rutinas de recorrido acceden por esta base.
 */
typedef struct AyudaCuerpo {
    s32 w0;
    GsCOORDINATE2* pcoord;
    u8 pad08[0xA8 - 0x08];
    u8 visible;
} AyudaCuerpo;

extern void* D_800694D8;
extern s32 D_80069534;
extern Ayuda* func_800363D4(void);
extern ObjetoEscena* D_800695EC;
extern s32 func_800375F8[];

/*
 * Recorre la lista de escena 'lista' (por el enlace de +0x10) y, para cada objeto activo,
 * decide la visibilidad de cada uno de sus ayudantes: marca 'visible' y guarda la matriz de
 * vista de los visibles. El puntero en curso vive en el scratchpad porque las rutinas llamadas
 * lo consultan.
 */
void func_80037048(ObjetoEscena* lista)
{
    Escritorio* sp;
    Ayuda* a;
    AyudaCuerpo* e;
    MATRIX* m;
    void* aux;
    u8 uno;

    sp = ESCRITORIO;
    aux = (void*)0x1F800038;
    sp->actual = lista;
    D_800694D8 = 0;
    if (lista != 0) {
        uno = 1;
        m = (MATRIX*)0x1F800008;
        do {
            if (!(sp->actual->cab.libre & 2)) {
                sp->actual = sp->actual->sig10;
            } else {
                sp->actual->coord.flg = 0;
                for (a = sp->actual->ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                    e = (AyudaCuerpo*)((u8*)a + 0xC);
                    if (a->flags8 & 8) {
                        e->visible = uno;
                    } else if (a->flags8 & 6) {
                        if (a->flags8 & 0x8000) {
                            e->visible = 0;
                        } else if (func_8003760C(e->pcoord, m, aux)) {
                            func_80037CF8((s32*)m, (s32*)&a->m94);
                            e->visible = uno;
                        } else {
                            e->visible = 0;
                        }
                    }
                }
                sp->actual = sp->actual->sig10;
            }
        } while (sp->actual != 0);
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 929 con la configuracion versionada (g = 8 del archivo). El cuerpo
 * coincide instruccion por instruccion salvo el reparto de registros: GCC iza la constante 1 de
 * la marca de visibilidad a $s5 fuera de los bucles y el original la carga junto al almacen.
 * Variantes probadas: 9.
 */
/*
 * Dibuja la lista de escena 'lista': para cada objeto activo con la bandera de dibujo (bit 3 de
 * flags18) lo refleja respecto del objeto de referencia D_800695EC segun los bits de s1E de este
 * (eje X, Y o Z), recalcula su matriz, decide la visibilidad de sus ayudantes, restaura su
 * posicion original y lo anade a la lista de dibujo D_800694D8 (que se encadena por +0x10).
 */
void func_80037184(ObjetoEscena* lista)
{
    Escritorio* sp;
    Ayuda* a;
    AyudaCuerpo* e;
    MATRIX* m;
    void* aux;
    ObjetoEscena* ref;
    ObjetoEscena* o;

    sp = ESCRITORIO;
    D_80069534 += 10;
    sp->actual = lista;
    if (lista != 0) {
        m = (MATRIX*)0x1F800008;
        aux = (void*)0x1F800038;
        do {
            if (!(sp->actual->cab.libre & 2) || !(sp->actual->flags18 & 8)) {
                sp->actual = sp->actual->sig10;
            } else {
                ref = D_800695EC;
                sp->pos = sp->actual->param.trans;
                if ((u16)ref->s1E & 1) {
                    sp->actual->param.trans.vx =
                        ref->param.trans.vx - (sp->actual->param.trans.vx - ref->param.trans.vx);
                    RotMatrix(&sp->actual->coord.param->rotate, &sp->actual->coord.coord);
                    sp->actual->coord.coord.m[0][0] *= -1;
                    sp->actual->coord.coord.m[0][1] *= -1;
                    sp->actual->coord.coord.m[0][2] *= -1;
                } else if ((u16)ref->s1E & 2) {
                    sp->actual->param.trans.vy =
                        ref->param.trans.vy - (sp->actual->param.trans.vy - ref->param.trans.vy);
                    RotMatrix(&sp->actual->coord.param->rotate, &sp->actual->coord.coord);
                    sp->actual->coord.coord.m[1][0] *= -1;
                    sp->actual->coord.coord.m[1][1] *= -1;
                    sp->actual->coord.coord.m[1][2] *= -1;
                } else {
                    sp->actual->param.trans.vz =
                        ref->param.trans.vz - (sp->actual->param.trans.vz - ref->param.trans.vz);
                    RotMatrix(&sp->actual->coord.param->rotate, &sp->actual->coord.coord);
                    sp->actual->coord.coord.m[2][0] *= -1;
                    sp->actual->coord.coord.m[2][1] *= -1;
                    sp->actual->coord.coord.m[2][2] *= -1;
                }
                TransMatrix(&sp->actual->coord.coord, &sp->actual->coord.param->trans);
                sp->actual->coord.flg = 0;
                for (a = sp->actual->ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
                    if (a->flags8 & 8) {
                        continue;
                    }
                    if (a->flags8 & 6) {
                        e = (AyudaCuerpo*)((u8*)a + 0xC);
                        if (a->flags8 & 0x8000) {
                            e->visible = 0;
                        } else if (func_8003760C(e->pcoord, m, aux)) {
                            func_80037CF8((s32*)m, (s32*)&a->m94);
                            e->visible = 1;
                        } else {
                            e->visible = 0;
                        }
                    }
                }
                sp->actual->param.trans = sp->pos;
                sp->actual->flags18 &= ~8;
                sp->actual->flags18 |= 0x10;
                if (D_800694D8 == 0) {
                    D_800694D8 = sp->actual;
                } else {
                    sp->previo->sig10 = sp->actual;
                }
                o = sp->actual;
                sp->previo = o;
                sp->actual = o->sig10;
                sp->previo->sig10 = 0;
            }
        } while (sp->actual != 0);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037184);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 160 con la configuracion versionada (g = 8 del archivo). Rutina de GTE
 * escrita a mano: carga ocho palabras en $t0..$t7 y las escribe en los registros de control 0 a
 * 7; la ultima escritura (ctc2 $t7,$7) va en el hueco de retardo del retorno, y GCC no mueve
 * una sentencia __asm__ a ese hueco. Variantes probadas: 2.
 */
void func_8003753C(s32* m)
{
    register s32 t0 __asm__("$8");
    register s32 t1 __asm__("$9");
    register s32 t2 __asm__("$10");
    register s32 t3 __asm__("$11");
    register s32 t4 __asm__("$12");
    register s32 t5 __asm__("$13");
    register s32 t6 __asm__("$14");
    register s32 t7 __asm__("$15");

    t0 = m[0];
    t1 = m[1];
    t2 = m[2];
    t3 = m[3];
    t4 = m[4];
    t5 = m[5];
    t6 = m[6];
    t7 = m[7];
    __asm__ volatile ("ctc2 %0, $0" : : "r"(t0));
    __asm__ volatile ("ctc2 %0, $1" : : "r"(t1));
    __asm__ volatile ("ctc2 %0, $2" : : "r"(t2));
    __asm__ volatile ("ctc2 %0, $3" : : "r"(t3));
    __asm__ volatile ("ctc2 %0, $4" : : "r"(t4));
    __asm__ volatile ("ctc2 %0, $5" : : "r"(t5));
    __asm__ volatile ("ctc2 %0, $6" : : "r"(t6));
    __asm__ volatile ("ctc2 %0, $7" : : "r"(t7));
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_8003753C);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 160 con la configuracion versionada (g = 8 del archivo). Rutina de GTE
 * escrita a mano: carga ocho palabras en $t0..$t7 y las escribe en los registros de control 0 a 4,
 * 24, 25 y 7; la ultima escritura (ctc2 $t7,$7) va en el hueco de retardo del retorno, y GCC no mueve
 * una sentencia __asm__ a ese hueco. Variantes probadas: 2.
 */
void func_80037580(s32* m)
{
    register s32 t0 __asm__("$8");
    register s32 t1 __asm__("$9");
    register s32 t2 __asm__("$10");
    register s32 t3 __asm__("$11");
    register s32 t4 __asm__("$12");
    register s32 t5 __asm__("$13");
    register s32 t6 __asm__("$14");
    register s32 t7 __asm__("$15");

    t0 = m[0];
    t1 = m[1];
    t2 = m[2];
    t3 = m[3];
    t4 = m[4];
    t5 = m[5];
    t6 = m[6];
    t7 = m[7];
    __asm__ volatile ("ctc2 %0, $0" : : "r"(t0));
    __asm__ volatile ("ctc2 %0, $1" : : "r"(t1));
    __asm__ volatile ("ctc2 %0, $2" : : "r"(t2));
    __asm__ volatile ("ctc2 %0, $3" : : "r"(t3));
    __asm__ volatile ("ctc2 %0, $4" : : "r"(t4));
    __asm__ volatile ("ctc2 %0, $24" : : "r"(t5));
    __asm__ volatile ("ctc2 %0, $25" : : "r"(t6));
    __asm__ volatile ("ctc2 %0, $7" : : "r"(t7));
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037580);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 20 con la configuracion versionada (g = 8 del archivo). Copia cinco
 * palabras del bloque de datos que hay en 0x800375F8 usando $a1 como origen y $t0..$t4 como
 * temporales, como una rutina escrita a mano. Variantes probadas: 3.
 */
void func_800375C4(s32* destino)
{
    register s32* origen __asm__("$5");
    register s32 t0 __asm__("$8");
    register s32 t1 __asm__("$9");
    register s32 t2 __asm__("$10");
    register s32 t3 __asm__("$11");
    register s32 t4 __asm__("$12");

    origen = func_800375F8;
    t0 = origen[0];
    t1 = origen[1];
    t2 = origen[2];
    t3 = origen[3];
    t4 = origen[4];
    destino[0] = t0;
    destino[1] = t1;
    destino[2] = t2;
    destino[3] = t3;
    destino[4] = t4;
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800375C4);
#endif

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800375F8);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_8003760C);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800379A0);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037B08);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037C00);

/*
 * Copia 32 bytes (una matriz de GTE) usando $t0..$t7 como temporales: carga las ocho palabras
 * antes de escribir ninguna, como la rutina manuscrita original. GCC solo reproduce esa forma
 * si los ocho temporales se fijan a sus registros.
 */
void func_80037CF8(s32* origen, s32* destino)
{
    register s32 t0 __asm__("$8");
    register s32 t1 __asm__("$9");
    register s32 t2 __asm__("$10");
    register s32 t3 __asm__("$11");
    register s32 t4 __asm__("$12");
    register s32 t5 __asm__("$13");
    register s32 t6 __asm__("$14");
    register s32 t7 __asm__("$15");

    t0 = origen[0];
    t1 = origen[1];
    t2 = origen[2];
    t3 = origen[3];
    t4 = origen[4];
    t5 = origen[5];
    t6 = origen[6];
    t7 = origen[7];
    destino[0] = t0;
    destino[1] = t1;
    destino[2] = t2;
    destino[3] = t3;
    destino[4] = t4;
    destino[5] = t5;
    destino[6] = t6;
    destino[7] = t7;
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 125 con la configuracion versionada (g = 8 del archivo). Convierte un
 * valor de 0 a 999 en tres digitos BCD (centenas, decenas, unidades); el original conserva las
 * centenas en $a1 hasta el final y GCC las deja en $v0. Variantes probadas: 4.
 */
u32 func_80037D3C(u16 valor)
{
    u16 centenas;
    u16 decenas;

    centenas = valor / 100;
    valor = valor - centenas * 100;
    decenas = valor / 10;
    valor = valor - decenas * 10;
    return (centenas << 8) | (decenas << 4) | valor;
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037D3C);
#endif

/*
 * Reinicia el objeto 'o' a partir de la plantilla de identificador 'id': libera sus ayudantes,
 * copia la plantilla conservando los dos enlaces de lista, y, si el modelo tiene jerarquia,
 * crea el ayudante raiz con su coordenada y la posicion inicial 'pos'. 'modo' elige entre
 * dos tiempos de espera iniciales.
 */
void func_80037DB4(ObjetoEscena* o, s16 id, s16* pos, s16 modo)
{
    ObjetoEscena* t;
    ObjetoEscena* sig;
    ObjetoEscena* sig10;
    u32 i;
    s32* d;

    if (o->ayudas != 0) {
        ClearList((NodoLista*)&o->ayudas);
    }
    for (t = D_80069504; t != 0; t = (ObjetoEscena*)t->cab.siguiente) {
        if (t->w1C == id) {
            break;
        }
    }
    if (t != 0) {
        sig = (ObjetoEscena*)o->cab.siguiente;
        sig10 = o->sig10;
        i = 0;
        d = (s32*)o;
        for (; i < 0x7D; i++) {
            *d++ = *(s32*)t;
            t = (ObjetoEscena*)((s32*)t + 1);
        }
        o->coord.param = &o->param;
        o->cab.siguiente = (NodoLista*)sig;
        o->sig10 = sig10;
        o->cab.libre |= 2;
        if (o->p74 == 0) {
            o->flags14 |= 0x100;
        } else {
            o->ayudas = func_800363D4();
            if (o->ayudas == 0) {
                for (;;) {
                }
            }
            if (o->p74->datos->wA & 2) {
                o->ayudas->flags8 |= 2;
                GsInitCoordinate2(0, o->ayudas->pcoord);
                o->ayudas->pcoord->super = &o->coord;
                o->coord.param = &o->param;
                o->ayudas->w14 = o->p74->datos->w54;
            }
            o->coord.flg = 0;
            o->ayudas->wC = 0;
            func_800375C4((s32*)&o->ayudas->m94);
            o->ayudas->m94.t[0] = pos[0] << 16;
            o->ayudas->m94.t[1] = pos[1] << 16;
            if (modo != 0) {
                o->w22 = 0x3C;
                o->s1E = 0;
                o->ayudas->m94.t[2] = 0x4B0;
            } else {
                o->s1E = 1;
                o->w22 = 0;
                o->ayudas->m94.t[2] = 0x1F40;
            }
        }
    }
}

/* Apaga el bit 1 de la marca (objeto activo) de todos los nodos de la lista. */
void func_80037FB8(NodoLista* n)
{
    while (n != 0) {
        n->libre &= ~2;
        n = n->siguiente;
    }
}

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037FE8);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_8003861C);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80038884);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800389FC);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80038C2C);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 180 con la configuracion versionada (g = 8 del archivo). Coincide el
 * cuerpo del bucle; el original duplica el arranque del bucle (t0 = 0 y t1 = ~2) en los
 * huecos de retardo de cada rama previa y GCC los fusiona en un solo bloque. Variantes
 * probadas: 4.
 */
/*
 * Avanza un paso la animacion de aparicion y desaparicion de tres objetos consecutivos de la
 * tabla D_8006AB70 a partir de 'idx': cuando el temporizador de cada uno llega a cero, el
 * parametro de profundidad del ayudante (m94.t[2]) crece o decrece segun el estado s1E (0
 * aparece, 1 y 2 desaparecen con distinta inercia) y, al terminar, el objeto se desactiva.
 */
void func_80038E84(s32 idx, s32 paso)
{
    ObjetoEscena* v[3];
    ObjetoEscena** p;
    ObjetoEscena* o;
    s32 i;

    v[0] = D_8006AB70[idx];
    v[1] = D_8006AB70[idx + 1];
    v[2] = D_8006AB70[idx + 2];
    if (v[0]->cab.libre & 2) {
        if (v[1]->s1E == 0) {
            if (v[2]->s1E != 0) {
                v[0]->w22 = 0x29;
                v[1]->w22 = 0x29;
            } else {
                v[0]->w22 = v[1]->w22;
            }
        } else if (v[0]->s1E == 0) {
            if (v[1]->s1E == 1) {
                v[0]->w22 = 0x29;
            }
        }
        for (i = 0, p = v; i < 3; i++, p++) {
            o = *p;
            if (o->w22 == 0) {
                if (o->s1E == 0) {
                    o->ayudas->m94.t[2] += 0xC8 + (o->ayudas->m94.t[2] >> 2);
                    if (o->ayudas->m94.t[2] > 0x1F40) {
                        o->cab.libre &= ~2;
                    }
                } else if (o->s1E == 1) {
                    o->ayudas->m94.t[2] -= (o->ayudas->m94.t[2] >> 2) + paso;
                    if (o->ayudas->m94.t[2] < 0x4B0) {
                        o->w22 = 0x28;
                        o->s1E = 0;
                        o->ayudas->m94.t[2] = 0x4B0;
                    }
                } else if (o->s1E == 2) {
                    o->ayudas->m94.t[2] -= (o->ayudas->m94.t[2] >> o->s1E) + paso;
                    if (o->ayudas->m94.t[2] < 0) {
                        o->cab.libre &= ~2;
                        o->ayudas->m94.t[2] = 0;
                    }
                }
            } else {
                o->w22 = o->w22 - 1;
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80038E84);
#endif

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80039094);
