#ifndef MOTOR_H
#define MOTOR_H

/*
 * Tipos auxiliares del movimiento, la animacion de matrices y los eventos de zona. El objeto de
 * escena y el estado de la camara viven en globales.h (Objeto, EstadoCamara).
 */
#include "common.h"
#include "globales.h"
#include "geometria.h"

extern MATRIX* TransMatrix(MATRIX* m, VECTOR* v);

/*
 * Mueve un punto contra el terreno y los volumenes solidos (rutina de colision y terreno): recibe
 * la posicion a corregir, el desplazamiento deseado (se sustituye por el realizado), los
 * parametros de la zona y el area de trabajo de la consulta. Devuelve 0 cuando el punto no tiene zona
 * (v0 = 0 en 0x80019504) y 1 al terminar el barrido (v0 = 1 en 0x8001BEC0); los llamadores lo ignoran.
 */
extern s32 BarrerTerreno(void* pos, void* desplazamiento, void* zona, void* trabajo);

/*
 * Desplazamiento que un objeto pretende hacer en un cuadro (x en +0, altura en +4, z en +8).
 * Las rutinas de movimiento lo sustituyen por el desplazamiento permitido.
 */
typedef struct Movimiento {
    s32 x;
    s32 dy;
    s32 z;
} Movimiento;

/*
 * Area de trabajo del movimiento de un objeto: copia de la posicion de partida en +0, posicion
 * de trabajo (desplazamiento realizado) en +0xC y +0x14, altura en +0x10, copias de 16 bits del
 * desplazamiento en +0x18 y +0x1A, grupo de la baldosa en +0x1C y el area de la consulta de
 * colision en +0x20.
 */
typedef struct TrabajoMov {
    s32 x;
    s32 y;
    s32 z;
    s32 dx;
    s32 y10;
    s32 dz;
    s16 h18;
    s16 h1A;
    u16 w1C;
    u8 pad1E[0x20 - 0x1E];
    u8 consulta[0x40];
} TrabajoMov;

/*
 * Misma area de trabajo vista por la rutina de seguimiento del suelo: punto consultado en +0, el
 * resultado de la baldosa (ResultadoBaldosa) en +0x10 y el area de la consulta (TrabajoBaldosa)
 * en +0x28. El llamador reserva una sola area y cada rutina la reinterpreta.
 */
typedef struct TrabajoSuelo {
    s32 x;
    s32 y;
    s32 z;
    u8 pad0C[4];
    ResultadoBaldosa res;
    TrabajoBaldosa tb;
} TrabajoSuelo;

extern int rsin(int angulo);

/* Coloca la camara detras de una posicion (movimiento_y_objetos_de_escena_2.c). */

/* Consulta de baldosa de colision_y_terreno.c (la definicion vive alli). */
extern void func_8001C134(s32* pos, ResultadoBaldosa* r, TrabajoBaldosa* w);

/*
 * Registro de un fotograma dentro del bloque de animacion: desplazamiento de la secuencia en +6
 * y banderas en +8 (el bit 0x40 marca los fotogramas que conservan el estado del salto).
 */
typedef struct RegistroAnim {
    u8 pad00[6];
    u16 w06;
    u16 w08;
    u16 w0A;                /* grupo de disparadores del fotograma: lhu en LogicaActorSecuencias (0x8002D24C) */
    u32 w0C;
    u32 w10;                /* banderas de movimiento: lw en LogicaProyectil (0x8002F40C), bit 3 = el golpe se reparte */
    u8 pad14[0x16 - 0x14];
    u16 w16;                /* dano del golpe: lhu en LogicaEfectoAnclado (0x8002ED84) */
    u8 pad18[0x1E - 0x18];
    u16 w1E;                /* desplazamiento del primer disparador del fotograma: lhu en LogicaActorSecuencias (0x8002D25C) */
} RegistroAnim;

/*
 * Nodo de la lista de secuencias de un objeto: siguiente en +0, identificador en +4 y
 * desplazamiento del registro dentro del bloque de animacion en +6.
 */
typedef struct NodoSecuencia {
    struct NodoSecuencia* sig;
    u16 id;
    u16 desplazamiento;
    u16 w08;
    u16 w0A;
    u16 pad0C[2];
    u32 w10;
} NodoSecuencia;

/* Nodo de la lista de saltos (peldanos) de un objeto: siguiente en +0 y altura de destino en +0x10. */
typedef struct NodoPeldano {
    struct NodoPeldano* sig;
    u8 pad04[0x10 - 0x04];
    s32 w10;
} NodoPeldano;

/* Rutinas de movimiento de movimiento_y_objetos_de_escena.c que se llaman entre si. */
extern void func_8001C424(Objeto* o, Movimiento* m, ResultadoBaldosa* r);
extern void func_8001C6CC(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);
extern void func_8001C998(Objeto* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);

/*
 * Macro de lectura del GTE del juego: guarda MAC3 (registro 27 de datos) en la palabra de p
 * pasando por los temporales fijos $8 y $9. El original la escribio como ensamblador en linea
 * con los mismos temporales que las macros vectoriales de geometria.h.
 */
#define MOTOR_GUARDAR_MAC3(p) \
    __asm__ volatile ("move $9, %0\n\t" \
                      "mfc2 $8, $27\n\t" \
                      "nop\n\t" \
                      "sw $8, 0($9)" \
                      : : "r"(p) : "$8", "$9", "memory")

/*
 * Macros vectoriales de la animacion de objetos: reproducen rutinas manuscritas del original con
 * los temporales fijos $8..$12, como las de geometria.h, y su lista de registros destruidos
 * contiene exactamente los que el cuerpo escribe.
 *
 * MOTOR_UNOS_W(p): vector de tres palabras de p = 0x1000. El original (0x8001ECE8 a 0x8001ED00,
 * AvanzarAnimacionSprite) copia la direccion a $t0, carga 0x1000 en $t4 una sola vez, lo copia a $t1..$t3
 * con addu y almacena las tres palabras; el cuerpo escribe $8 a $12, y todos los almacenes
 * pasan por $9..$11.
 */
#define MOTOR_UNOS_W(p) \
    __asm__ volatile ("move $8, %0\n\t" \
                      "addiu $12, $0, 0x1000\n\t" \
                      "move $9, $12\n\t" \
                      "move $10, $12\n\t" \
                      "move $11, $12\n\t" \
                      "sw $9, 0($8)\n\t" \
                      "sw $10, 4($8)\n\t" \
                      "sw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "$12", "memory")

/*
 * MOTOR_DIAGONAL_CERO(p): pone a cero los elementos de la diagonal de la matriz de p (sw en +0,
 * sw en +8 y sh en +0x10). El original (0x80036F90 a 0x80036FA0, AplicarCuadro) copia la direccion
 * a $t0, pone $t1 a cero con addu y almacena tres veces; el cuerpo escribe $8 y $9.
 */
#define MOTOR_DIAGONAL_CERO(p) \
    __asm__ volatile ("move $8, %0\n\t" \
                      "move $9, $0\n\t" \
                      "sw $9, 0($8)\n\t" \
                      "sw $9, 8($8)\n\t" \
                      "sh $9, 16($8)" \
                      : : "r"(p) : "$8", "$9", "memory")

/*
 * Proyeccion de un objeto sobre la pantalla: area de trabajo de la proyeccion de un sprite que
 * func_8001DF28 rellena a partir de la posicion (+0x38) y devuelve en +0x58: profundidad en
 * +0x54, escala en +0x90, esquinas del cuadro en +0x4C..+0x52 y puntero a las coordenadas
 * del sprite en +0x98.
 */
typedef struct ProyeccionSprite {
    u8 pad00[0x38];
    SVECTOR pos;
    u8 pad40[0x4C - 0x40];
    s16 h4C;
    s16 h4E;
    s16 h50;
    s16 h52;
    s32 z54;
    s32 w58;
    s32 w5C;
    u8 pad60[0x90 - 0x60];
    s32 escala;
    s16 h94;
    u8 pad96[0x98 - 0x96];
    s16* coordenadas;
} ProyeccionSprite;

/*
 * Apoyo hallado por func_80020354: el objeto al que el jugador se agarra en +0, su coordenada en
 * +4 y el punto de contacto en el sistema local del objeto (x en +8, altura relativa en +0xA, que
 * el jugador copia a la traslacion del apoyo, y z en +0xC). Las escrituras de func_80020354 fijan
 * cada ancho (sw 0x80020A08, sh 0x80020A1C, 0x80020A18, 0x80020A2C).
 */
typedef struct ApoyoHallado {
    Objeto* objeto;
    GsCOORDINATE2* coord;
    s16 x;
    s16 h0A;
    s16 z;
    u8 pad0E[2];
} ApoyoHallado;

/*
 * Un peldano de la cadena de ayudantes que func_80020354 recorre: posicion en el sistema del objeto
 * apoyo (x, y, z), alto y largo del peldano (diferencias con el anterior, 0xA y 0xC) y la
 * coordenada del ayudante que lo origina (+0x10). Mide 0x14 bytes y caben 20.
 */
typedef struct PeldanoApoyo {
    s16 x;
    s16 y;
    s16 z;
    u8 pad06[0x0A - 0x06];
    s16 alto;
    s16 largo;
    u8 pad0E[0x10 - 0x0E];
    GsCOORDINATE2* nodo;
} PeldanoApoyo;

/*
 * Area de trabajo de func_80020354 (la que reserva el jugador en el scratchpad, +0x148): matriz del
 * apoyo en +0, giro inverso en +0x20, punto local en +0x28, objeto solido en curso en +0x30,
 * ayudante en curso en +0x34, caja del consultante en +0x38 y +0x40 (solo se copia), resultado en
 * +0x48, hasta 20 peldanos desde +0x58, distancia al cuadrado o semilado en +0x1E8 y el punto en
 * el sistema local del objeto en +0x1EC.
 */
typedef struct SondaApoyo {
    MATRIX m;
    SVECTOR rot;
    SVECTOR local;
    Objeto* cur;
    struct Ayuda* ptr;
    SVECTOR caja_min;
    SVECTOR caja_max;
    ApoyoHallado res;
    PeldanoApoyo pel[20];
    u32 dist;
    VECTOR out;
} SondaApoyo;

extern void func_8001CF50(Objeto* o);
extern void func_8001CFCC(GsCOORDINATE2* n);
extern void func_8001D588(s32 modo, VECTOR* p);
extern void* func_8001DF28(Objeto* o, ProyeccionSprite* b);
extern u32 func_80044940(s32* v);
extern void func_8001CC68(VECTOR* p);

#endif
