#ifndef MOTOR_H
#define MOTOR_H

/*
 * Vista de los objetos de escena para el movimiento, la animacion de matrices y los eventos de
 * zona. Cada campo corresponde a un acceso del ensamblador original (ancho y signo de la
 * instruccion de carga y de almacen); los huecos son relleno. Es la misma memoria que Objeto
 * (globales.h), que solo declara los campos que usan los demas archivos: los desplazamientos
 * comunes se comprueban en tiempo de compilacion al final de este archivo, de modo que una
 * discrepancia entre las dos vistas rompe la compilacion en lugar de generar codigo distinto.
 */
#include "common.h"
#include "globales.h"
#include "geometria.h"

/*
 * Transformacion que cada objeto o nodo referencia: escala en +0 (VECTOR), rotacion en +0x10
 * (SVECTOR) y traslacion en +0x18 (VECTOR). Alimenta ScaleMatrix, RotMatrix y TransMatrix.
 */
typedef struct Transformacion {
    VECTOR escala;
    SVECTOR rot;
    VECTOR trans;
} Transformacion;

extern MATRIX* TransMatrix(MATRIX* m, VECTOR* v);

/*
 * Mueve un punto contra el terreno y los volumenes solidos (rutina de colision y terreno): recibe
 * la posicion a corregir, el desplazamiento deseado (se sustituye por el realizado), los
 * parametros de la zona y el area de trabajo de la consulta.
 */
extern void func_80019474(void* pos, void* desplazamiento, void* zona, void* trabajo);

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
 * La orden de movimiento de un objeto es el resultado de la consulta de baldosa
 * (ResultadoBaldosa, geometria.h): +2 banderas del terreno (8 y 1 = rampa y salto, bits 4, 8 y
 * 0x10 piden tipos de movimiento), +6 pendiente absoluta, +8 tipo y +0xA grupo. La altura del
 * techo en +0xC cae en el hueco que geometria.h deja sin nombre.
 */
#define ORDEN_TECHO(r) (*(s32*)((u8*)(r) + 0xC))

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
} RegistroAnim;

/*
 * Nodo de la lista de secuencias de un objeto: siguiente en +0, identificador en +4 y
 * desplazamiento del registro dentro del bloque de animacion en +6.
 */
typedef struct NodoSecuencia {
    struct NodoSecuencia* sig;
    u16 id;
    u16 desplazamiento;
} NodoSecuencia;

/* Nodo de la lista de saltos (peldanos) de un objeto: siguiente en +0 y altura de destino en +0x10. */
typedef struct NodoPeldano {
    struct NodoPeldano* sig;
    u8 pad04[0x10 - 0x04];
    s32 w10;
} NodoPeldano;

/*
 * Objeto de escena con los campos del movimiento. Posicion en +0xE4 (s32 x, y, z), angulos en
 * +0xDC, matriz de transformacion en +0x80 (func_8001CF50) y transformacion en +0xC0.
 */
typedef struct ObjetoMotor {
    struct ObjetoMotor* siguiente;
    u8 pad04[0x08 - 0x04];
    u32 flags08;
    u8 pad0C[0x14 - 0x0C];
    u32 flags14;
    u8 pad18[0x26 - 0x18];
    u16 w26;
    u8 pad28[0x52 - 0x28];
    s16 h52;
    u8 pad54[0x70 - 0x54];
    struct ObjetoMotor* p70;
    u8 pad74[0x78 - 0x74];
    NodoPeldano* p78;
    s32 w7C;
    MATRIX mtx;
    u8 padA0[0xC0 - 0xA0];
    Transformacion* transf;
    u8 padC4[0xDC - 0xC4];
    u16 wDC;
    u16 wDE;
    u16 wE0;
    u8 padE2[0xE4 - 0xE2];
    s32 xE4;
    s32 yE8;
    s32 zEC;
    u8 padF0[0xF4 - 0xF0];
    NodoSecuencia* secuencias;
    u8* bloque;
    u8 padFC[0x100 - 0xFC];
    s32 i100;
    s16 h104;
    s16 h106;
    s16 h108;
    s16 h10A;
    s16 h10C;
    u16 w10E;
    s16 h110;
    s16 h112;
    u8 pad114[0x116 - 0x114];
    s16 h116;
    u8 pad118[0x13C - 0x118];
    s32 i13C;
    u8 pad140[0x146 - 0x140];
    s16 h146;
    u8 pad148[0x14C - 0x148];
    u8 b14C;
    u8 pad14D[0x14E - 0x14D];
    s16 h14E;
    u8 pad150[0x158 - 0x150];
    s32 i158;
    u32 flags15C;
    u8 pad160[0x17C - 0x160];
    u16 w17C;
    u8 pad17E[0x180 - 0x17E];
    NodoSecuencia* nodo180;
    RegistroAnim* registro184;
    u8 pad188[0x1A8 - 0x188];
    s32 i1A8;
} ObjetoMotor;

/*
 * Estado de la camara y de la escena (D_8006D928) con los campos de posicionamiento: la vista
 * de EstadoCamara en globales.h solo declara los primeros 0x20 bytes y las banderas de +0x80.
 * Los dos puntos de vista (vp) y de mira (x, y, z) se repiten en cuatro copias que la
 * rutina de seguimiento interpola (+0x68, +0x94, +0xA4 y +0xB4).
 */
typedef struct CamaraMotor {
    s32 vpx;
    s32 vpy;
    s32 vpz;
    s32 x;
    s32 y;
    s32 z;
    u8 pad18[0x68 - 0x18];
    s32 c68;
    s32 c6C;
    s32 c70;
    u8 pad74[0x80 - 0x74];
    u16 flags80;
    u8 pad82[0x94 - 0x82];
    s32 c94;
    s32 c98;
    s32 c9C;
    u8 padA0[0xA4 - 0xA0];
    s32 cA4;
    s32 cA8;
    s32 cAC;
    u8 padB0[0xB4 - 0xB0];
    s32 cB4;
    s32 cB8;
    s32 cBC;
} CamaraMotor;

/* Rutinas de movimiento de movimiento_y_objetos_de_escena.c que se llaman entre si. */
extern void func_8001C424(ObjetoMotor* o, Movimiento* m, ResultadoBaldosa* r);
extern void func_8001C6CC(ObjetoMotor* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);
extern void func_8001C998(ObjetoMotor* o, Movimiento* d, ResultadoBaldosa* r, TrabajoMov* w);

/* Comprobacion de coherencia con Objeto (globales.h): el arreglo tiene tamano negativo si difiere. */
#define MOTOR_MISMO_OFFSET(campo_motor, campo_objeto) \
    typedef char motor_offset_##campo_motor[ \
        ((u32)&((ObjetoMotor*)0)->campo_motor == (u32)&((Objeto*)0)->campo_objeto) ? 1 : -1]
MOTOR_MISMO_OFFSET(flags14, flags14);
MOTOR_MISMO_OFFSET(w26, w26);
MOTOR_MISMO_OFFSET(wDC, wDC);
MOTOR_MISMO_OFFSET(wDE, wDE);
MOTOR_MISMO_OFFSET(wE0, wE0);
MOTOR_MISMO_OFFSET(xE4, xE4);
MOTOR_MISMO_OFFSET(yE8, yE8);
MOTOR_MISMO_OFFSET(zEC, zEC);
MOTOR_MISMO_OFFSET(w17C, w17C);
MOTOR_MISMO_OFFSET(flags15C, flags15C);
MOTOR_MISMO_OFFSET(i158, i158);

#define MOTOR_CAMARA_MISMO_OFFSET(campo)     typedef char motor_camara_offset_##campo[         ((u32)&((CamaraMotor*)0)->campo == (u32)&((EstadoCamara*)0)->campo) ? 1 : -1]
MOTOR_CAMARA_MISMO_OFFSET(vpx);
MOTOR_CAMARA_MISMO_OFFSET(vpy);
MOTOR_CAMARA_MISMO_OFFSET(vpz);
MOTOR_CAMARA_MISMO_OFFSET(x);
MOTOR_CAMARA_MISMO_OFFSET(y);
MOTOR_CAMARA_MISMO_OFFSET(z);
MOTOR_CAMARA_MISMO_OFFSET(flags80);

/* Estado de la camara visto con los campos del movimiento (misma memoria que D_8006D928). */
#define CAMARA_MOTOR ((CamaraMotor*)&D_8006D928)

#endif
