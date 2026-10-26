#ifndef NIVELES_H
#define NIVELES_H

/*
 * Tipos de la logica de niveles. Manejadores de objeto de la tabla D_8005E35C (indexada por
 * Objeto.w2C): memorias de trabajo del scratchpad (0x1F800000) y registros de las listas que el
 * objeto lleva en +0xF8 y +0xFC. El objeto de escena vive en globales.h y los registros de
 * animacion en motor.h. Los desplazamientos y anchos de cada tipo salen del ensamblador de la
 * funcion que se cita en su comentario.
 */
#include "common.h"
#include "arranque.h"
#include "globales.h"
#include "geometria.h"
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
    u32 req14;                      /* func_80026298: lw 0x80026DF4, mascara que flags14 del objeto debe cumplir (0 = sin requisito) */
    u32 req18;                      /* func_80026298: lw 0x80026E18, mascara que flags18 del objeto debe cumplir (0 = sin requisito) */
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
 * Memoria de trabajo del objeto movil por mascara (scratchpad 0x1F800000): acumulador de la cadena
 * de matrices en +0 (tres palabras), vector en +0x10 (tres medias palabras que el original guarda
 * con sh y relee con lhu), cursor de la cadena en +0x18 y area de las rutinas de animacion y de
 * solape en +0x1C.
 */
typedef struct TrabajoMovil {
    s32 ax;
    s32 ay;
    s32 az;
    u8 pad0C[4];
    SVECTOR v;
    GsCOORDINATE2* cursor;
} TrabajoMovil;

#define TRABAJO_MOVIL ((TrabajoMovil*)0x1F800000)

/*
 * Doble uso de +0x184..+0x198 del objeto: los actores animados lo leen como registro de fotograma
 * y estado de giro (Objeto.registro184, w192, w196) y los objetos moviles por mascara como limites
 * y origen del recorrido (tres palabras con signo). El campo declarado conserva el ancho del
 * primer uso y el segundo se accede con estos cast, cada uno con la instruccion que lo fija.
 */
#define MOVIL_LIMITE_BAJO(o) (*(s32*)&(o)->registro184)
#define MOVIL_ORIGEN_X(o) (*(s32*)((u8*)(o) + 0x190))
#define MOVIL_LIMITE_ALTO(o) (*(s32*)((u8*)(o) + 0x194))
#define MOVIL_ORIGEN_Z(o) (*(s32*)((u8*)(o) + 0x198))

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
 * Memoria de trabajo del proyectil (scratchpad 0x1F800000): resultado de la consulta de terreno en +2
 * (el bit 4 indica pared), zona del objeto en +0xA, vector de avance en +0x18 (salida del GTE),
 * posicion de prueba en +0x28, desplazamiento permitido en +0x38, velocidad local en +0x58,
 * objeto alcanzado en +0x90 y area de las consultas en +0x98.
 */
typedef struct TrabajoProyectil {
    u8 pad00[2];
    u16 bits;
    u8 pad04[6];
    u16 zona;
    u8 pad0C[0x18 - 0x0C];
    s32 mx;
    s32 my;
    s32 mz;
    u8 pad24[4];
    s32 px;
    s32 py;
    s32 pz;
    u8 pad34[4];
    s32 dx;
    s32 dy;
    s32 dz;
    u8 pad44[0x58 - 0x44];
    s16 vx;
    s16 vy;
    s16 vz;
    u8 pad5E[0x90 - 0x5E];
    Objeto* golpeado;
    u8 pad94[4];
    u8 area[0x20];
} TrabajoProyectil;

#define TRABAJO_PROYECTIL ((TrabajoProyectil*)0x1F800000)

/*
 * Memoria de trabajo del efecto anclado (scratchpad 0x1F800000): fotograma en +0, nodo de la
 * secuencia en +0xC, paso en +0x14, identificador buscado en +0x18, objeto alcanzado en +0x1C,
 * vector local en +0x20, posicion acumulada en +0x28, copia de 16 bits en +0x38, cursor de la
 * cadena de nodos en +0x40 y area de consultas en +0x44.
 */
typedef struct TrabajoEfecto {
    RegistroAnim* fotograma;
    u8 pad04[8];
    NodoSecuencia* secuencia;
    u8 pad10[4];
    u16 paso;
    u8 pad16[2];
    s32 id;
    Objeto* otro;
    s16 vx;
    s16 vy;
    s16 vz;
    u8 pad26[2];
    s32 px;
    s32 py;
    s32 pz;
    u8 pad34[4];
    s16 ax;
    s16 ay;
    s16 az;
    u8 pad3E[2];
    GsCOORDINATE2* cursor;
    u8 area[0x20];
} TrabajoEfecto;

#define TRABAJO_EFECTO ((TrabajoEfecto*)0x1F800000)

/*
 * Memoria de trabajo del bloque empujable (scratchpad 0x1F800000): resultado de la consulta de
 * baldosa en +2 (bit 1 = hay suelo, bit 3 = sin suelo) y altura en +6, zona en +0xA, desplazamiento
 * pedido en +0x18..+0x20, posicion de prueba en +0x28, vector de avance en +0x58, caja girada en +0x68
 * (minimo) y +0x70 (maximo), recorte en +0x78, matriz en +0x80, objeto chocado en +0xA4 y area de
 * consultas en +0xA8. Las medias palabras se guardan con sh y se releen con lhu.
 */
typedef struct TrabajoBloque {
    u8 pad00[2];
    u16 bits;
    u8 pad04[2];
    u16 altura;
    u8 pad08[2];
    u16 zona;
    u8 pad0C[0x18 - 0x0C];
    s32 dx;
    s32 dy;
    s32 dz;
    u8 pad24[4];
    s32 px;
    s32 py;
    s32 pz;
    u8 pad34[0x58 - 0x34];
    s32 vx;
    s32 vy;
    s32 vz;
    u8 pad64[4];
    u16 mnx;
    u16 mny;
    u16 mnz;
    u8 pad6E[2];
    u16 mxx;
    u16 mxy;
    u16 mxz;
    u8 pad76[2];
    u16 cx;
    u16 cy;
    u16 cz;
    u8 pad7E[2];
    MATRIX m;
    u8 pad_a0[4];
    Objeto* chocado;
    u8 area[0x20];
} TrabajoBloque;

#define TRABAJO_BLOQUE ((TrabajoBloque*)0x1F800000)

/*
 * Registro de estado de la lista de +0xF8 del objeto (el estado vigente). El enlace va en +0 y
 * el identificador en +4 (tambien codigo de accion que recibe func_8001D414). s06 es la animacion
 * del estado (se compara con trabajo.i14), s08 sus parametros (el bit 0x8000 impide reiniciarla),
 * w0A la clave de la lista de transiciones, flags0C y flags10 las capacidades del estado, s14 el
 * multiplicador de velocidad y s16 y s18 la amplitud y el paso del salto.
 */
typedef struct RegistroEstado {
    struct RegistroEstado* sig;
    u16 id;
    s16 s06;
    s16 s08;
    u16 w0A;
    u32 flags0C;
    s32 flags10;
    s16 s14;
    s16 s16;
    s16 s18;
} RegistroEstado;

/*
 * Transicion de la lista de +0xFC del objeto: botones exigidos en w6 (0xFFF1 es comodin) y
 * mascara de botones w8, estado siguiente en wA (0xFFF3 no cambia de estado), accion sobre el
 * objeto portado en wC (0xD3 lo suelta), elemento de logica de 8 bytes en +0xE para TestLogicCond
 * y RunLogicAction, modo en w18 (el bit 2 invierte la mascara de m24 y el bit 1 la de m28) y las
 * mascaras que se comparan con los indicadores del portado (m1C), del apoyo (m20), del propio
 * objeto (m24) y de flags18 (m28).
 */
typedef struct Transicion {
    struct Transicion* sig;
    u16 id;
    u16 w6;
    u16 w8;
    u16 wA;
    u16 wC;
    u8 item[8];
    u8 pad16[2];
    u16 w18;
    u8 pad1A[2];
    u32 m1C;
    u32 m20;
    u32 m24;
    u32 m28;
} Transicion;

/*
 * Apoyo hallado por func_80020354: el objeto al que el jugador se agarra en +0 y, en +0xA, la
 * altura relativa que se copia a la traslacion del apoyo.
 */
typedef struct ApoyoHallado {
    Objeto* objeto;
    u8 pad04[6];
    s16 h0A;
} ApoyoHallado;

/* Velocidad local del cuadro: x sin uso, altura en y, avance en z (carga GTE de VXY0 y VZ0). */
typedef struct VelocidadLocal {
    s16 x;
    u16 y;
    u16 z;
    s16 pad06;
} VelocidadLocal;

/*
 * Memoria de trabajo de la logica del jugador en el scratchpad (0x1F800000). Se borra entera al
 * entrar y no sobrevive al cuadro. Los anchos y signos de cada campo (lh, lhu, lw) son los que el
 * ensamblador de func_80020B90 usa; paso se carga como vector de medias palabras en el GTE y
 * func_80017478 lo recibe como SVECTOR. A partir de 0x148 empieza el area de trabajo que reciben
 * las consultas de terreno y de volumen (func_80019474 exige 0x1C8 bytes libres por debajo de
 * 0x1F8003FF).
 */
typedef struct ScratchJugador {
    s16 paso_x;
    u16 paso_y;
    u16 paso_z;
    u16 pad06;
    VelocidadLocal vel;
    u16 ang_x;
    u16 ang_y;
    u16 ang_z;
    u16 pad16;
    Vec3 desp;
    u8 pad24[4];
    Vec3 resp;
    u8 pad34[4];
    VECTOR punto;
    MATRIX m;
    ResultadoBaldosa res;
    u8 pad80[0xA8 - 0x80];
    ApoyoHallado* apoyo_hallado;
    s16 res_peldano;
    u8 padAE[2];
    s32 tmp;
    Objeto* tocado;
    VECTOR rel;
    Objeto* tocado2;
    RegistroEstado* reg;
    Transicion* trans;
    Transicion* cand;
    NodoSecuencia* sec;
    u8 padDC[4];
    u16 paso_vigente;
    u16 estado_sig;
    GsCOORDINATE2* cursor;
    SVECTOR tmp_sv;
    VECTOR tmp_v;
    u32 resp_apoyo[3];
    u8 pad10C[0x12C - 0x10C];
    AcumuladorNodos acum;
} ScratchJugador;

/* Transformacion del jugador relativa al apoyo (+0x18C) y la del objeto portado (Objeto.portado, +0x11C). */
#define APOYO(o) ((ParametrosObjeto*)((u8*)(o) + 0x18C))
#define PORTADO(o) (&(o)->portado)

extern s32 BugsRand(void);
extern s32 TestLogicCond(void* o, void* registro);
extern void RunLogicAction(void* o, void* registro);
extern s32 func_8003F06C(void* o, s32 id, s32 modo, s32 voz);
/* El original pasa el area de trabajo como cuarto argumento aunque la rutina solo declara tres. */
extern void func_8001E528(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern void func_8001E600(Objeto* o, BloqueTrabajo* b, u32 modo, void* area);
extern u32 func_80045C4C(u32 a0, void* a1, Objeto* a2);
extern u32 func_80045498(Objeto* objeto, void* guion, BloqueTrabajo* bloque);
extern s32 func_8001F268(Objeto* o, BloqueTrabajo* b, s32 id, s32 arg, void* w);
extern Objeto* func_80036734(s16 id, s32* pos, u16* ang);
extern void func_8001CD84(Objeto* o, u32 id, void* area);
extern void func_8001D31C(s32 x, s32 y, s32 z);
extern s16 func_80018F80(Objeto* a, Objeto* b, void* area);
extern s32 func_8001D75C(Objeto* o, s32 modo, void* area);
extern Objeto* func_800171E4(Objeto* a, VECTOR* p, u32 mascara, u32 excluir, ConsultaVolumen* o);
extern Objeto* func_80016ED0(Objeto* a, u32 mascara, void* area);
extern Objeto* func_80016C0C(Objeto* a, u32 mascara, ConsultaVolumen* o);
extern Objeto* func_80017478(Objeto* a, SVECTOR* v, void* w, u32 mascara);
extern void func_8001CBB8(Objeto* o, Movimiento* d, ResultadoBaldosa* r, void* w);
extern void func_8001E1A4(Objeto* o, ConsultaPlano* c);
extern void func_8001D0FC(Objeto* o, s32 id, void* area);
extern s32 func_8001E720(Objeto* o, BloqueTrabajo* b, u32 anim, u32 params, void* area);

#endif
