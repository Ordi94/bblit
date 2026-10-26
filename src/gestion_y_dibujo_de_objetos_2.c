#include "common.h"
#include "objetos.h"

/*
 * Vista del ayudante (Ayuda, objetos.h) a partir de +0x0C: el puntero a su GsCOORDINATE2 (+0x10
 * del nodo) y la bandera de visibilidad (+0xB4 del nodo). Es una vista aparte de Ayuda a proposito:
 * el original recorre la lista con un puntero desplazado 0xC (addiu sobre el nodo) distinto del
 * propio nodo. Accediendo por los campos de Ayuda func_80037048 sube de 0 a 604 puntos.
 */
typedef struct AyudaCuerpo {
    s32 w0;
    GsCOORDINATE2* pcoord;
    u8 pad08[0xA8 - 0x08];
    u8 visible;
} AyudaCuerpo;

/* Estado principal del juego en 0x80010000: se accede con un puntero constante (un solo lui). */
#define EST ((u8*)0x80010000)

/* Lista de objetos ya dibujados (se encadena por +0x10) y contador de cuadros. */

/* Objeto de referencia respecto del que func_80037184 refleja los demas. */

/* Contadores de la interfaz del estado principal (bytes sueltos de 0x80010000). */
extern u8 D_80010042;
extern u8 D_80010043;
extern u8 D_80010044;
extern u8 D_80010045;
extern u8 D_800100F7;
extern u8 D_800100F9;
extern u8 D_800100FA;

/* Nivel de unidades mostrado por los indicadores y nivel de fundido pedido. */

/*
 * Tablas del archivo: identificadores de plantilla de los grupos de objetos (D_8005E830), de los
 * digitos 0 a 9 (D_8005E81C) y posiciones (x, y) de cada objeto de cada grupo.
 */
extern s16 D_8005E830[];
extern s16 D_8005E81C[];
extern s16 D_8005E86C[][2];
extern s16 D_8005E928[][2];
extern s16 D_8005E938[][2];
extern s16 D_8005E8BC[][2];
extern s16 D_8005E8E0[][2];
extern s16 D_8005E8F8[][2];
extern s16 D_8005E910[][2];

/* Matriz inicial de un ayudante: cinco palabras de datos que el codigo del archivo copia. */
extern s32 func_800375F8[];

/*
 * Variables pequenas direccionadas con 0x110($gp), 0x114($gp) y 0x118($gp): el angulo de giro
 * del grupo de func_8003861C y los dos angulos de func_800389FC. Se definen en el archivo para
 * que el ensamblador los reescriba a $gp.
 */
u16 D_80069430;
s32 D_80069434;
s32 D_80069438;

extern s32 func_80038C2C(s32 idx, s32 valor, s32 modo);
extern void func_80038884(s32 idx, s32 modo);
extern void func_80037DB4(Objeto* o, s16 id, s16* pos, s16 modo);
extern u32 func_80037D3C(u16 valor);

/*
 * Algunos llamadores pasan a func_80037DB4 enteros de 32 bits ya extendidos sin la conversion
 * a s16 que impondria su prototipo: el original la llama sin prototipo visible. Este tipo de
 * funcion permite la misma llamada directa sin conversion de los argumentos.
 */
typedef void (*ReiniciarSinConversion)(Objeto* o, s32 id, s16* pos, s32 modo);

/* Idem para func_80037D3C: el llamador le pasa el valor entero sin truncarlo a u16. */
typedef u32 (*DigitosSinConversion)(s32 valor);

/*
 * Recorre la lista de escena 'lista' (por el enlace de +0x10) y, para cada objeto activo,
 * decide la visibilidad de cada uno de sus ayudantes: marca 'visible' y guarda la matriz de
 * vista de los visibles. El puntero en curso vive en el scratchpad porque las rutinas llamadas
 * lo consultan.
 */
void func_80037048(Objeto* lista)
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
            if (!(sp->actual->flags04 & 2)) {
                sp->actual = sp->actual->sig10;
            } else {
                sp->actual->coord.flg = 0;
                for (a = sp->actual->u78.ayudas; a != 0; a = (Ayuda*)a->cab.siguiente) {
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

/*
 * Dibuja la lista de escena 'lista': para cada objeto activo con la bandera de dibujo (bit 3 de
 * flags18) lo refleja respecto del objeto de referencia D_800695EC segun los bits de s1E de este
 * (eje X, Y o Z), recalcula su matriz, decide la visibilidad de sus ayudantes, restaura su
 * posicion original y lo anade a la lista de dibujo D_800694D8 (que se encadena por +0x10).
 *
 * El recorrido de ayudantes usa una etiqueta y no un for: el optimizador de bucles saca la constante 1 de la marca de
 * visibilidad a un registro guardado cuando el recorrido es un bucle interior de 29 instrucciones, y el original la carga
 * junto al almacen. La constante del area de trabajo se asigna antes que el puntero al escritorio para que cada una tenga
 * su propio lui, y el enlace del objeto en curso se guarda antes de releerlo para que el original conserve la copia.
 */
void func_80037184(Objeto* lista)
{
    Escritorio* sp;
    Ayuda* a;
    AyudaCuerpo* e;
    MATRIX* m;
    void* aux;
    Objeto* ref;
    Objeto* o;

    aux = (void*)0x1F800038;
    sp = ESCRITORIO;
    D_80069534 += 10;
    sp->actual = lista;
    if (lista != 0) {
        m = (MATRIX*)0x1F800008;
        do {
            if (!(sp->actual->flags04 & 2) || !(sp->actual->flags18 & 8)) {
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
                a = sp->actual->u78.ayudas;
                if (a != 0) {
                sig_ayuda:
                    if (!(a->flags8 & 8) && (a->flags8 & 6)) {
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
                    a = (Ayuda*)a->cab.siguiente;
                    if (a != 0) {
                        goto sig_ayuda;
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
                sp->previo = sp->actual;
                o = sp->actual;
                sp->actual = o->sig10;
                sp->previo->sig10 = 0;
            }
        } while (sp->actual != 0);
    }
}

/*
 * Rutina de GTE escrita a mano en el original (marca Handwritten del particionador): carga ocho
 * palabras en $t0..$t7 y las escribe en los registros de control 0 a 7; la ultima ctc2 va en el
 * hueco de retardo del jr ra. Se conserva en ensamblador porque GCC 2.8.1 no coloca una sentencia
 * en ese hueco ni reparte los temporales fijos del original.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_8003753C);

/*
 * Rutina de GTE escrita a mano en el original (marca Handwritten del particionador): igual que la
 * anterior pero escribe los registros de control 0 a 4, 24, 25 y 7, con la ultima ctc2 en el
 * hueco de retardo del jr ra. Se conserva en ensamblador.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037580);

/*
 * Rutina escrita a mano en el original: copia cinco palabras del bloque que hay en 0x800375F8 (la
 * matriz inicial de un ayudante) usando $a1 como origen y $t0..$t4 como temporales fijos, sin
 * prologo de pila. Se conserva en ensamblador: GCC elige otros temporales y pliega el
 * desplazamiento bajo en la primera carga.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800375C4);

/*
 * Dato, no funcion: cinco palabras (20 bytes, 0x800375F8..0x8003760B) incrustadas en .text entre func_800375C4 y
 * func_8003760C. Son la matriz inicial de un ayudante (nueve valores de 16 bits y relleno) que func_800375C4 copia. El
 * desensamblador las marca como instrucciones invalidas. Se conserva como bloque de palabras con INCLUDE_ASM: pasarlo a un
 * dato de C obligaria a mover su contenido a otra seccion y a cambiar el reparto del script de particion, y el bloque no
 * tiene tamano en config/symbols.txt. Se declara extern s32 func_800375F8[] mas arriba solo para direccionar el origen.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800375F8);

/*
 * Rutina escrita a mano en el original: calcula la matriz mundo de un nodo GsCOORDINATE2 recorriendo la jerarquia hacia la
 * raiz y componiendola de vuelta con las rutinas manuscritas que siguen. El particionador no la marca Handwritten, pero el
 * ensamblador tiene cuatro formas que GCC 2.8.1 no emite: constantes con `ori` en lugar de `addiu` (ori a1,zero,0x64 y ori
 * t0,zero,0x64 en 0x80037648 y 0x8003764C; ori a0,zero,4 en 0x800378F0; ori v0,zero,1 en 0x80037974); registros guardados
 * s4 (0xC), s5 (0x24) y s6 (0x8) fuera del orden de numeracion (0x80037624..0x8003762C); copias de matriz con ocho
 * cargas seguidas de ocho almacenes (0x80037864..0x800378A0 y 0x800378B0..0x800378EC); y marcos de pila abiertos a mitad de
 * la funcion (addiu sp,-0x18 en 0x80037808 y addiu sp,-0x20 en 0x80037920) alrededor de las llamadas a las rutinas de
 * rotacion y traslacion. Se conserva en ensamblador.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_8003760C);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_800379A0);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037B08);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037C00);

/*
 * Rutina escrita a mano en el original: copia 32 bytes (una matriz de GTE) cargando las ocho
 * palabras en $t0..$t7 antes de escribir ninguna, sin prologo de pila. Se conserva en
 * ensamblador: GCC asigna otros temporales y entrelaza cargas y almacenes.
 */
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037CF8);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). Convierte un
 * valor de 0 a 999 en tres digitos BCD (centenas, decenas, unidades); el original conserva las
 * centenas en $a1 hasta el final y calcula centenas << 8 justo despues de la multiplicacion,
 * mientras que GCC las deja en $v0 y las desplaza mas tarde (reparto de registros y orden de
 * evaluacion).
 */
u32 func_80037D3C(u16 valor)
{
    u16 centenas;
    u16 decenas;

    centenas = valor / 100;
    valor -= centenas * 100;
    decenas = valor / 10;
    valor -= decenas * 10;
    return (decenas << 4) | valor | (centenas << 8);
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
void func_80037DB4(Objeto* o, s16 id, s16* pos, s16 modo)
{
    Objeto* t;
    Objeto* sig;
    Objeto* sig10;
    u32 i;
    s32* d;

    if (o->u78.ayudas != 0) {
        ClearList((NodoLista*)&o->u78.ayudas);
    }
    for (t = D_80069504; t != 0; t = t->siguiente) {
        if (t->w1C == id) {
            break;
        }
    }
    if (t != 0) {
        sig = o->siguiente;
        sig10 = o->sig10;
        i = 0;
        d = (s32*)o;
        for (; i < 0x7D; i++) {
            *d++ = *(s32*)t;
            t = (Objeto*)((s32*)t + 1);
        }
        o->coord.param = PARAMETROS_SDK(o);
        o->siguiente = sig;
        o->sig10 = sig10;
        o->flags04 |= 2;
        if (o->lista == 0) {
            o->flags14 |= 0x100;
        } else {
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
            o->coord.flg = 0;
            o->u78.ayudas->wC = 0;
            func_800375C4((s32*)&o->u78.ayudas->m94);
            o->u78.ayudas->m94.t[0] = pos[0] << 16;
            o->u78.ayudas->m94.t[1] = pos[1] << 16;
            if (modo != 0) {
                o->w22 = 0x3C;
                o->s1E = 0;
                o->u78.ayudas->m94.t[2] = 0x4B0;
            } else {
                o->s1E = 1;
                o->w22 = 0;
                o->u78.ayudas->m94.t[2] = 0x1F40;
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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 3403 con la configuracion versionada (g = 8 del archivo). La estructura
 * de los seis grupos coincide, pero el original rematerializa el puntero a 0x80010000 en cada
 * grupo salvo en los tres ultimos, donde lo conserva en un registro salvado a traves de la
 * llamada a la conversion BCD; GCC lo trata como una sola constante y reparte los registros de
 * otra forma. Variantes probadas: 6.
 */
/*
 * Crea los objetos de los indicadores de la interfaz al entrar en un nivel: reinicia los
 * grupos de tres y cuatro digitos a partir de los contadores del estado principal (cada
 * valor se convierte a BCD con func_80037D3C y cada digito elige su plantilla en D_8005E81C)
 * y, para los contadores opcionales, fija el parametro de profundidad de cada ayudante a 0x5DC.
 */
void func_80037FE8(void* lista)
{
    s32 ids[6];
    s32* pid;
    s16 (*pos)[2];
    s32 i;
    s32 bcd;
    s32 pct;
    Objeto* o;
    s16 (*tpos)[2];
    u8* e;

    func_80038C2C(0, D_80010043, 1);
    func_80038884(0xE, 1);

    e = EST;
    bcd = ((DigitosSinConversion)func_80037D3C)((e[0x13C] << 8) | e[0x47]);
    ids[0] = D_8005E830[3];
    ids[1] = D_8005E81C[(bcd & 0xF00) >> 8];
    ids[2] = D_8005E81C[(bcd & 0xF0) >> 4];
    ids[3] = D_8005E81C[bcd & 0xF];
    pos = D_8005E928;
    for (i = 0; i < 4; i++) {
        ((ReiniciarSinConversion)func_80037DB4)(D_8006AB70[3 + i], ids[i], pos[i], 1);
    }

    i = 0;
    bcd = ((DigitosSinConversion)func_80037D3C)(D_80010045);
    ids[0] = D_8005E830[7];
    ids[1] = D_8005E81C[(bcd & 0xF00) >> 8];
    ids[2] = D_8005E81C[(bcd & 0xF0) >> 4];
    ids[3] = D_8005E81C[bcd & 0xF];
    pos = D_8005E938;
    for (; i < 4; i++) {
        ((ReiniciarSinConversion)func_80037DB4)(D_8006AB70[7 + i], ids[i], pos[i], 1);
    }

    i = 0;
    e = EST;
    pct = ((e[0x13C] << 8) + e[0x47] + e[0x45]) * 100 / 457;
    bcd = ((DigitosSinConversion)func_80037D3C)(pct);
    ids[0] = D_8005E81C[(bcd & 0xF00) >> 8];
    ids[1] = D_8005E81C[(bcd & 0xF0) >> 4];
    ids[3] = D_8005E830[0x14];
    ids[2] = D_8005E81C[bcd & 0xF];
    pos = D_8005E8BC;
    for (; i < 4; i++) {
        if (i == 0) {
            if (ids[0] == 0x1D8) {
                continue;
            }
        } else if (i == 1) {
            if (ids[0] == 0x1D8 && ids[1] == ids[0]) {
                continue;
            }
        }
        ((ReiniciarSinConversion)func_80037DB4)(D_8006AB70[20 + i], ids[i], pos[i], 1);
    }

    if (D_800100F7 != 0) {
        e = EST;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0x40 + e[0xF6]]);
        ids[0] = D_8005E830[3];
        ids[1] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[2] = D_8005E81C[bcd & 0xF];
        i = 0;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0xF7]);
        ids[3] = D_8005E830[0x19];
        ids[4] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[5] = D_8005E81C[bcd & 0xF];
        pos = D_8005E8E0;
        for (; i < 6; i++) {
            o = D_8006AB70[29 + i];
            ((ReiniciarSinConversion)func_80037DB4)(o, ids[i], pos[i], 1);
            o->u78.ayudas->m94.t[2] = 0x5DC;
        }
    }

    if (D_800100F9 != 0) {
        e = EST;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0x40 + e[0xF8]]);
        ids[0] = D_8005E830[7];
        ids[1] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[2] = D_8005E81C[bcd & 0xF];
        i = 0;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0xF9]);
        ids[3] = D_8005E830[0x19];
        ids[4] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[5] = D_8005E81C[bcd & 0xF];
        pos = D_8005E8F8;
        tpos = D_8005E8F8 - 6;
        for (; i < 6; i++) {
            o = D_8006AB70[35 + i];
            if (D_800100F7 != 0) {
                ((ReiniciarSinConversion)func_80037DB4)(o, ids[i], pos[i], 1);
            } else {
                ((ReiniciarSinConversion)func_80037DB4)(o, ids[i], tpos[i], 1);
            }
            o->u78.ayudas->m94.t[2] = 0x5DC;
        }
    }

    if (D_800100FA != 0) {
        e = EST;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0x44]);
        ids[0] = D_8005E830[0x18];
        ids[1] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[2] = D_8005E81C[bcd & 0xF];
        i = 0;
        bcd = ((DigitosSinConversion)func_80037D3C)(e[0xFA]);
        ids[3] = D_8005E830[0x19];
        ids[4] = D_8005E81C[(bcd & 0xF0) >> 4];
        ids[5] = D_8005E81C[bcd & 0xF];
        pos = D_8005E910;
        for (; i < 6; i++) {
            o = D_8006AB70[41 + i];
            ((ReiniciarSinConversion)func_80037DB4)(o, ids[i], pos[i], 1);
            o->u78.ayudas->m94.t[2] = 0x5DC;
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80037FE8);
#endif

/*
 * Actualiza el grupo de tres objetos 'idx'..'idx + 2' de la tabla D_8006AB70 segun el nivel
 * pedido en D_8006AA70[1]: acerca de uno en uno el nivel actual (D_800695F6) al pedido, escala
 * el segundo objeto en proporcion y, si el grupo no estaba activo, lo reinicia con func_80037DB4
 * a partir de las tablas de plantillas D_8005E830 y de posiciones D_8005E86C. Con nivel pedido y
 * actual en cero desactiva los tres objetos.
 */
void func_8003861C(s32 idx)
{
    Objeto* v[3];
    VECTOR esc;
    u8 pedido;
    u8 actual;
    s16* ids;
    s32 id0;
    s32 id1;
    s32 id2;

    v[0] = D_8006AB70[idx];
    v[1] = D_8006AB70[idx + 1];
    v[2] = D_8006AB70[idx + 2];
    pedido = D_8006AA70[1];
    if (pedido != 0 || D_800695F6 != 0) {
        if (D_800695F6 == 0) {
            D_800695F6 = pedido;
        }
        actual = D_800695F6;
        if (actual < pedido) {
            D_800695F6 = D_800695F6 + 1;
        } else if (pedido < actual) {
            D_800695F6 = D_800695F6 - 1;
        }
        esc.vz = 0x1000;
        esc.vy = 0x1000;
        esc.vx = 0x1000 - (D_800695F6 << 5);
        if (!(v[0]->flags04 & 2)) {
            ids = &D_8005E830[idx];
            id0 = ids[0];
            id1 = ids[1];
            id2 = ids[2];
            func_80037DB4(v[0], id0, D_8005E86C[idx], 1);
            func_80037DB4(v[1], id1, D_8005E86C[idx + 1], 1);
            func_80037DB4(v[2], id2, D_8005E86C[idx + 2], 1);
            D_80069430 = 0;
            ScaleMatrix(&v[1]->u78.ayudas->m94, &esc);
        } else {
            D_80069430 += 0x50;
            if ((s16)D_80069430 >= 0x1000) {
                D_80069430 -= 0x1000;
            }
            func_800375C4((s32*)&v[0]->u78.ayudas->m94);
            RotMatrixY((s16)D_80069430, &v[0]->u78.ayudas->m94);
            func_800375C4((s32*)&v[1]->u78.ayudas->m94);
            ScaleMatrix(&v[1]->u78.ayudas->m94, &esc);
        }
    } else if (v[0]->flags04 & 2) {
        v[0]->flags04 &= ~2;
        v[1]->flags04 &= ~2;
        v[2]->flags04 &= ~2;
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 170 con la configuracion versionada (g = 8 del archivo). Coincide la
 * estructura y el marco de pila (la reserva de 8 bytes sin uso lo iguala); difiere la asignacion de
 * registros salvados (el original deja los tres identificadores en $s7, $s6 y $s5, el parametro
 * en $s4 y la tabla de posiciones en $s3) y el registro del indice j ($a2 en el original).
 */
/*
 * Reinicia, de dos en dos, los objetos del grupo 'idx' (tres consecutivos de la tabla
 * D_8006AB70) para cada unidad de D_80010042: el identificador de plantilla de cada uno se
 * elige entre los tres de D_8005E830 segun cuantas unidades de D_80069524 alcanzan ese
 * indice, y la posicion sale de D_8005E86C.
 */
void func_80038884(s32 idx, s32 modo)
{
    Objeto* v[3];
    /* Sin uso: el original deja 8 bytes de pila libres entre los argumentos y los registros salvados. */
    s32 reserva[2];
    Objeto** p;
    Objeto* o;
    s16* ids;
    s32 id0;
    s32 id1;
    s32 id2;
    s32 k;
    s32 j;
    s32 id;
    s32 nivel;

    ids = &D_8005E830[idx];
    id0 = ids[0];
    id1 = ids[1];
    id2 = ids[2];
    v[0] = D_8006AB70[idx];
    v[1] = D_8006AB70[idx + 1];
    v[2] = D_8006AB70[idx + 2];
    k = 0;
    if (D_80010042 != 0) {
        p = v;
        do {
            nivel = D_80069524;
            if (nivel >= k + 2) {
                j = k / 2;
                o = p[j];
                id = id0;
            } else if (nivel >= k + 1) {
                j = k / 2;
                o = p[j];
                id = id1;
            } else {
                j = k / 2;
                o = p[j];
                id = id2;
            }
            ((ReiniciarSinConversion)func_80037DB4)(o, id, D_8005E86C[idx + j], modo);
            k += 2;
        } while (k < D_80010042);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80038884);
#endif

/*
 * Posiciona los tres objetos 'idx'..'idx + 2' de la tabla D_8006AB70: si 'apagar' es cero los
 * activa (reiniciandolos desde las tablas de plantillas y de posiciones si estaban inactivos) y
 * gira alrededor de Z la matriz de los dos primeros: el primero 'valor' / 960 y el segundo
 * 'valor' / 7680, ambos con 0x800 de desfase (0x1000 es una vuelta); si no, los desactiva.
 */
void func_800389FC(s32 idx, s32 valor, s32 apagar)
{
    Objeto* v[3];
    s16* ids;
    s32 id0;
    s32 id1;
    s32 id2;
    s32 n;

    v[0] = D_8006AB70[idx];
    v[1] = D_8006AB70[idx + 1];
    v[2] = D_8006AB70[idx + 2];
    if (apagar == 0) {
        if (!(v[0]->flags04 & 2)) {
            ids = &D_8005E830[idx];
            id0 = ids[0];
            id1 = ids[1];
            id2 = ids[2];
            func_80037DB4(v[0], id0, D_8005E86C[idx], 1);
            func_80037DB4(v[1], id1, D_8005E86C[idx + 1], 1);
            func_80037DB4(v[2], id2, D_8005E86C[idx + 2], 1);
        }
        n = valor << 12;
        D_80069434 = n / 960 + 0x800;
        D_80069438 = n / 7680 + 0x800;
        while (D_80069434 >= 0x1000) {
            D_80069434 -= 0x1000;
        }
        while (D_80069438 >= 0x1000) {
            D_80069438 -= 0x1000;
        }
        func_800375C4((s32*)&v[0]->u78.ayudas->m94);
        RotMatrixZ(D_80069434, &v[0]->u78.ayudas->m94);
        func_800375C4((s32*)&v[1]->u78.ayudas->m94);
        RotMatrixZ(D_80069438, &v[1]->u78.ayudas->m94);
    } else {
        v[0]->flags04 &= ~2;
        v[1]->flags04 &= ~2;
        v[2]->flags04 &= ~2;
    }
}

/*
 * Muestra 'valor' (0 a 999) con tres objetos consecutivos de la tabla D_8006AB70 a partir de
 * 'idx', uno por digito BCD: centenas (con el identificador fijo de la tabla D_8005E830),
 * decenas y unidades (con los de D_8005E81C). Reinicia el objeto de un digito solo si estaba
 * inactivo, o cambia su estado cuando el digito mostrado ya no es el pedido. Devuelve 1 si
 * acaba de reiniciar el objeto de las unidades y 0 en otro caso.
 */
s32 func_80038C2C(s32 idx, s32 valor, s32 modo)
{
    Objeto* c;
    Objeto* d;
    Objeto* u;
    s32 bcd;
    s32 id0;
    s32 idDec;
    s32 idUni;
    s32 nuevo;

    nuevo = 0;
    bcd = ((DigitosSinConversion)func_80037D3C)(valor);
    id0 = D_8005E830[idx];
    idDec = D_8005E81C[(bcd & 0xF0) >> 4];
    idUni = D_8005E81C[bcd & 0xF];
    c = D_8006AB70[idx];
    d = D_8006AB70[idx + 1];
    u = D_8006AB70[idx + 2];
    if (c->flags04 & 2) {
        if (c->s1E == 0 && c->w22 == 0) {
            c->s1E = 1;
        }
    } else {
        ((ReiniciarSinConversion)func_80037DB4)(c, id0, D_8005E86C[idx], modo);
    }
    if (d->flags04 & 2) {
        if (d->s1E != 2 && d->w1C != idDec && u->u78.ayudas->m94.t[2] <= 0x4B0) {
            d->w22 = 0;
            d->s1E = 2;
            d->u78.ayudas->m94.t[2] = u->u78.ayudas->m94.t[2];
        } else if (d->s1E == 0 && d->w22 == 0) {
            d->s1E = 1;
        }
    } else {
        ((ReiniciarSinConversion)func_80037DB4)(d, idDec, D_8005E86C[idx + 1], modo);
    }
    if (u->flags04 & 2) {
        if (u->w1C != idUni) {
            u->s1E = 2;
            u->w22 = 0;
        } else if (u->s1E == 0 && u->w22 == 0) {
            u->s1E = 1;
        }
    } else {
        nuevo = 1;
        ((ReiniciarSinConversion)func_80037DB4)(u, idUni, D_8005E86C[idx + 2], modo);
    }
    return nuevo;
}

/*
 * Avanza un paso la animacion de aparicion y desaparicion de tres objetos consecutivos de la
 * tabla D_8006AB70 a partir de 'idx': cuando el temporizador de cada uno llega a cero, el
 * parametro de profundidad del ayudante (m94.t[2]) crece o decrece segun el estado s1E (0
 * aparece, 1 y 2 desaparecen con distinta inercia) y, al terminar, el objeto se desactiva.
 * El contador y la mascara se inician justo antes del bucle: el compilador los reparte en los
 * huecos de retardo de las ramas previas.
 */
void func_80038E84(s32 idx, s32 paso)
{
    Objeto* v[3];
    Objeto** p;
    Objeto* o;
    s32 i;
    s32 mascara;

    v[0] = D_8006AB70[idx];
    v[1] = D_8006AB70[idx + 1];
    v[2] = D_8006AB70[idx + 2];
    if (v[0]->flags04 & 2) {
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
        i = 0;
        mascara = ~2;
        for (p = v; i < 3; i++, p++) {
            o = *p;
            if (o->w22 == 0) {
                if (o->s1E == 0) {
                    o->u78.ayudas->m94.t[2] += 0xC8 + (o->u78.ayudas->m94.t[2] >> 2);
                    if (o->u78.ayudas->m94.t[2] > 0x1F40) {
                        o->flags04 &= mascara;
                    }
                } else if (o->s1E == 1) {
                    o->u78.ayudas->m94.t[2] -= (o->u78.ayudas->m94.t[2] >> 2) + paso;
                    if (o->u78.ayudas->m94.t[2] < 0x4B0) {
                        o->w22 = 0x28;
                        o->s1E = 0;
                        o->u78.ayudas->m94.t[2] = 0x4B0;
                    }
                } else if (o->s1E == 2) {
                    o->u78.ayudas->m94.t[2] -= (o->u78.ayudas->m94.t[2] >> o->s1E) + paso;
                    if (o->u78.ayudas->m94.t[2] < 0) {
                        o->flags04 &= mascara;
                        o->u78.ayudas->m94.t[2] = 0;
                    }
                }
            } else {
                o->w22 = o->w22 - 1;
            }
        }
    }
}

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_2", func_80039094);
