#ifndef NIVELES_H
#define NIVELES_H

/*
 * Tipos de los manejadores de objeto de la logica de niveles (tabla D_8005E35C, indexada por
 * Objeto.w2C). El objeto de escena vive en globales.h y los registros de animacion en motor.h.
 */
#include "common.h"
#include "globales.h"
#include "motor.h"

/*
 * Nodo de la lista de disparadores del objeto (Objeto.apoyos, +0xFC): los registros de condicion y de
 * accion del interprete de eventos estan dentro del nodo, en +0x10, y se pasan por direccion a
 * TestLogicCond y RunLogicAction. El byte +0x10 elige la condicion y el +0x13 la accion; flags
 * decide que efectos acompanan al disparo. Cada campo cita la funcion cuyo ensamblador fija su
 * desplazamiento y su ancho.
 */
typedef struct NodoDisparador {
    struct NodoDisparador* sig;     /* func_8002D03C: lw 0x8002D568 */
    u16 id;                         /* func_8002D03C: lhu 0x8002D27C, grupo del fotograma */
    u16 desplazamiento;             /* func_8002D03C: lhu 0x8002D28C, posicion en la lista de secuencias */
    u8 pad08[8];
    u8 cond;                        /* func_8002D03C: lbu 0x8002D368, registro de condicion */
    u8 pad11[2];
    u8 accion;                      /* func_8002D03C: lbu 0x8002D38C, registro de accion */
    u8 pad14[4];
    s32 flags;                      /* func_8002D03C: lw 0x8002D298; el bit 31 pide animar al jugador */
    u32 p1C;                        /* func_8002D03C: lw, umbral de azar o valor de estado */
    s32 p20;                        /* func_8002D03C: lw, umbral de azar o identificador */
} NodoDisparador;

/*
 * Memoria de trabajo del recorrido de disparadores, en el scratchpad (0x1F800000): el original
 * guarda aqui sus variables, de modo que cada acceso es un lw / sw contra una base constante y
 * el estado sobrevive a las llamadas.
 */
typedef struct TrabajoDisparo {
    Objeto* buscado;                /* +0x00: objeto hallado por identificador */
    u8 pad04[4];
    RegistroAnim* fotograma;        /* +0x08 */
    NodoDisparador* cabeza;         /* +0x0C */
    NodoDisparador* nodo;           /* +0x10 */
    NodoSecuencia* secuencia;       /* +0x14 */
    u8 pad18[4];
    u16 paso;                       /* +0x1C */
    u16 destino;                    /* +0x1E */
    s32 flags;                      /* +0x20 */
    s32 resultado;                  /* +0x24 */
    s32 previo;                     /* +0x28 */
    u8 area[0x40];                  /* +0x2C: area que reciben func_8001D0FC y func_8001E720 */
} TrabajoDisparo;

#define TRABAJO_DISPARO ((TrabajoDisparo*)0x1F800000)

/*
 * Memoria de trabajo de la zona de eventos (scratchpad 0x1F800000): cursor del nodo en +0, nodo
 * anterior al salto en +4, objeto buscado o hijo creado en +8, vector de distancia en +0xC..+0x14,
 * distancia en +0x1C, banderas del nodo en +0x20, vector al jugador en +0x24..+0x2C, identificador
 * de salto en +0x34 y area de las rutinas de animacion en +0x38.
 */
typedef struct TrabajoZona {
    NodoDisparador* nodo;
    NodoDisparador* previo;
    Objeto* objeto;
    s32 dx;
    s32 dy;
    s32 dz;
    u8 pad18[4];
    s32 distancia;
    s32 flags;
    s32 vx;
    s32 vy;
    s32 vz;
    u8 pad30[4];
    u16 salto;
    u8 pad36[2];
    u8 area[0x20];
} TrabajoZona;

#define TRABAJO_ZONA ((TrabajoZona*)0x1F800000)

/*
 * Memoria de trabajo del director de camara (scratchpad 0x1F800000): nodo en +0, objeto de
 * origen en +4, vector de distancia en +8..+0x10, modulo en +0x18, banderas del nodo en +0x1C,
 * vector camara - destino en +0x20..+0x28, vector de giro en +0x30 (tres u16: el original los
 * guarda con sh y los relee con lhu), angulo en +0x38, escala en +0x40, matriz en +0x50 y
 * resultado en +0x70..+0x78.
 */
typedef struct TrabajoCamara {
    NodoDisparador* nodo;
    Objeto* origen;
    s32 dx;
    s32 dy;
    s32 dz;
    u8 pad14[4];
    s32 modulo;
    s32 flags;
    s32 ex;
    s32 ey;
    s32 ez;
    u8 pad2C[4];
    u16 vx;
    u16 vy;
    u16 vz;
    u16 vpad;
    u16 gx;
    u16 gy;
    u16 gz;
    u16 gpad;
    VECTOR escala;
    MATRIX m;
    VECTOR r;
} TrabajoCamara;

#define TRABAJO_CAMARA ((TrabajoCamara*)0x1F800000)

/*
 * Memoria de trabajo de la zona sonda (scratchpad 0x1F800000): angulos de la matriz en +0 (tres
 * medias palabras: el eje X se relee con lh y los otros dos con lhu), desplazamiento de la camara
 * en +8, punto relativo en +0x10, punto girado en +0x18, matriz en +0x20 y objeto recorrido en +0x40.
 */
typedef struct TrabajoSonda {
    s16 gx;
    u16 gy;
    u16 gz;
    u8 pad06[2];
    u16 cx;
    u16 cy;
    u16 cz;
    u8 pad0E[2];
    u16 px;
    u16 py;
    u16 pz;
    u8 pad16[2];
    u16 qx;
    u16 qy;
    u16 qz;
    u8 pad1E[2];
    MATRIX m;
    Objeto* actual;
} TrabajoSonda;

#define TRABAJO_SONDA ((TrabajoSonda*)0x1F800000)

/*
 * Macros de CPU de la zona de eventos: reproducen las secuencias del original con los
 * temporales fijos $8 (t0) y $9..$12 (t1..t4); la lista de registros destruidos es exactamente
 * la que cada cuerpo escribe.
 */
#define ZONA_PONER_CERO_3W(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsw $0, 4($8)\n\tsw $0, 8($8)" \
                      : : "r"(p) : "$8", "memory")
#define ZONA_PONER_CERO_WH(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsh $0, 4($8)" \
                      : : "r"(p) : "$8", "memory")
#define ZONA_GUARDAR_H_T1(p)     __asm__ volatile ("move $8, %0
	sh $9, 0($8)
	sh $10, 2($8)
	sh $11, 4($8)"                       : : "r"(p) : "$8", "memory")
#define ZONA_CARGAR_H(p)     __asm__ volatile ("move $8, %0
	lh $9, 0($8)
	lh $10, 2($8)
	lh $11, 4($8)"                       : : "r"(p) : "$8", "$9", "$10", "$11", "memory")
#define ZONA_SUMAR_H(p)     __asm__ volatile ("move $8, %0
	lh $12, 0($8)
	lh $13, 2($8)
	lh $14, 4($8)
	"                       "add $12, $12, $9
	add $13, $13, $10
	add $14, $14, $11
	"                       "sh $12, 0($8)
	sh $13, 2($8)
	sh $14, 4($8)"                       : : "r"(p) : "$8", "$12", "$13", "$14", "memory")
#define ZONA_RELLENAR_1000(p) \
    __asm__ volatile ("move $8, %0\n\taddiu $12, $0, 0x1000\n\tmove $9, $12\n\tmove $10, $12\n\t" \
                      "move $11, $12\n\tsw $9, 0($8)\n\tsw $10, 4($8)\n\tsw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "$12", "memory")

extern s32 BugsRand(void);
extern s32 TestLogicCond(void* o, void* registro);
extern void RunLogicAction(void* o, void* registro);
extern s32 func_8003F06C(void* o, s32 id, s32 modo, s32 voz);
/* El original pasa el area de trabajo como cuarto argumento aunque la rutina solo declara tres. */
extern void func_8001E528(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern void func_8001E600(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern u32 func_80045C4C(u32 a0, void* a1, Objeto* a2);
extern u32 func_80045498(Objeto* objeto, void* guion, BloqueTrabajo* bloque);
extern void func_8001F268(Objeto* o, BloqueTrabajo* b, u32 anim, u32 params, void* area);
extern Objeto* func_80036734(s16 id, s32* pos, u16* ang);
extern void func_8001CD84(Objeto* o, u32 id, void* area);
extern void func_8001D31C(s32 x, s32 y, s32 z);
extern void func_8001D0FC(Objeto* o, s32 id, void* area);
extern s32 func_8001E720(Objeto* o, BloqueTrabajo* b, u32 anim, u32 params, void* area);

#endif
