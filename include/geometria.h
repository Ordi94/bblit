#ifndef GEOMETRIA_H
#define GEOMETRIA_H

/*
 * Tipos de geometria compartidos por la colision con el terreno y los calculos de volumenes
 * por objeto. Los desplazamientos son los que el ensamblador original lee con lw, lh y lhu.
 */
#include "common.h"
#include "globales.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"

/* Vector de tres s32 del juego (x, y, z); distinto de VECTOR del SDK, cuyos campos son vx, vy, vz. */
typedef struct Vec3 {
    s32 x;
    s32 y;
    s32 z;
} Vec3;

/*
 * Zona de colision: bloque de 0x44 bytes de la tabla que carga func_80019364. El primer campo
 * es el grupo (indice de la tabla de cabezas D_80069C18, 0..59). La caja de una zona es
 * [x, x + ancho_x) por [z, z + ancho_z) en el plano y (y_min, y_max] en altura; y_max es
 * tambien la altura base que func_8001C134 entrega como suelo. Los dos punteros de +0x1C y
 * +0x20 (mapa de baldosas y tabla de subceldas) se guardan en el archivo como desplazamientos
 * y la carga los convierte en direcciones sumando la base del bloque.
 */
typedef struct ZonaColision {
    u16 grupo;
    u16 pendiente;
    u16 columnas;
    u16 pad06;
    u16 ancho_x;
    u16 ancho_z;
    s32 x;
    s32 z;
    s32 y_max;
    s32 y_min;
    u16* baldosas;
    u8* subceldas;
    u8 pad24[0x44 - 0x24];
} ZonaColision;

/*
 * Resultado de la consulta de baldosa de func_8001C134. tipo conserva los cuatro bits altos del
 * valor de la baldosa; grupo es el grupo de la zona encontrada (-1 si ninguna) y zona la propia
 * zona. En las rutinas de movimiento, flags 8 y 1 marcan rampa y salto y los bits 4, 8 y 0x10
 * piden tipos de movimiento. suelo es la altura donde se apoya el punto y techo la altura del
 * techo sobre el punto: func_8001C998 la lee con lw 0xC para limitar el salto y func_8001C134
 * no la escribe.
 */
typedef struct ResultadoBaldosa {
    u16 clase;
    u16 flags;
    u16 pendiente;
    u16 pendiente_abs;
    u16 tipo;
    s16 grupo;
    s32 techo;
    s32 suelo;
    ZonaColision* zona;
} ResultadoBaldosa;

/* Angulos de un objeto: la sonda solo lee y reescribe el giro en Y (+2). */
typedef struct Giro {
    u16 x;
    u16 y;
    u16 z;
} Giro;

/*
 * Memoria de trabajo de ActualizarCamaraSeguimiento en el scratchpad (0x1F800000): vector local, rotacion, vector
 * (0, 0, distancia), resultados de las rotaciones, sondas, resultado de la consulta de baldosa,
 * parametros de seguimiento, matriz de rotacion y distancia. El area de 0x1C8 bytes que reciben
 * BarrerTerreno, func_8001C134 y func_80032B2C empieza en 0x1F8000F8. El scratchpad lo reparten por
 * turnos rutinas con disposiciones distintas; la de LogicaDirectorCamara es TrabajoDirectorCamara (niveles.h).
 * Evidencia de los campos: sw en 0x1F8000BC (zona_ant, 0x800333B0), sw en 0x1F8000C0..C8 (p0, p4, p8,
 * 0x80033630), sw en 0x1F800030..38 (v30, 0x80033740), 0x1F800070..78 (v70, 0x80033774), 0x1F800090..98
 * (v90, 0x80033728), sh en 0x1F8000AE (res.tipo, 0x80033804).
 */
typedef struct TrabajoCamara {
    SVECTOR local;              /* +0x00 */
    SVECTOR rot;                /* +0x08 */
    SVECTOR dir;                /* +0x10 */
    VECTOR v18;                 /* +0x18 */
    Giro rot28;                 /* +0x28 */
    u8 pad2E[2];
    VECTOR v30;                 /* +0x30 */
    VECTOR v40;                 /* +0x40 */
    VECTOR v50;                 /* +0x50 */
    u8 pad60[0x70 - 0x60];
    VECTOR v70;                 /* +0x70 */
    u8 pad80[0x90 - 0x80];
    VECTOR v90;                 /* +0x90 */
    u8 padA0[0xA4 - 0xA0];
    ResultadoBaldosa res;       /* +0xA4 */
    ZonaColision* zona_ant;     /* +0xBC */
    s32 p0;                     /* +0xC0 */
    s32 p4;                     /* +0xC4 */
    s32 p8;                     /* +0xC8 */
    MATRIX m;                   /* +0xCC */
    s32 dist;                   /* +0xEC */
    u8 padF0[4];
    s32 alt;                    /* +0xF4 */
} TrabajoCamara;

/*
 * Area de trabajo de func_8001C134: la copia del punto consultado, su resto dentro de la baldosa
 * (320 unidades) y el valor leido de la subcelda (40 unidades).
 */
typedef struct TrabajoBaldosa {
    s32 x_local;
    s32 pad04;
    s32 z_local;
    s32 pad0C;
    s32 x;
    s32 y;
    s32 z;
    s32 pad1C;
    s16 celda;
    u16 baldosa;
} TrabajoBaldosa;

/*
 * Area de trabajo de BarrerTerreno (0x1C8 bytes en el scratchpad): el barrido avanza el punto por
 * el plano baldosa a baldosa (320 unidades) y subcelda a subcelda (40 unidades). Todos los
 * valores intermedios viven en esta estructura y no en registros: el original los relee de
 * memoria en cada paso.
 *
 *  x, y, z           copia del punto de partida
 *  dx, dz            desplazamiento pedido (se recorta al recorrido posible)
 *  lim_x, lim_z      proximo limite de subcelda dentro de la baldosa
 *  sz_*, sx_*        puntos de cruce con el limite en z y en x dentro de la baldosa
 *  dsz_*, dsx_*      resto de la baldosa menos cada punto de cruce (para la distancia)
 *  rx, rz            resto del punto de la baldosa (x % 320, z % 320)
 *  bx, by, bz        baldosa actual; ax, ay, az: punto de llegada acumulado
 *  ebz_*, ebx_*      punto de partida menos cada cruce de baldosa
 *  cbz_*, cbx_*      cruces con la proxima linea de baldosa en z y en x
 *  lin_x, lin_z      proxima linea de baldosa; paso_*: avance de baldosa; celda_*: de subcelda
 *  acc_*, ant_*      desplazamiento acumulado y el anterior (16 bits)
 *  pend_x, pend_z    pendientes (dz << 12) / dx y (dx << 12) / dz
 *  copia[2]          las dos ultimas zonas visitadas (solo se copian los 0x1C primeros bytes)
 *  zonas, celdas     historial de zonas y de celdas de subcelda; n es el indice de escritura
 */
typedef struct TrabajoRecorrido {
    s32 x;
    s32 y;
    s32 z;
    s32 pad0C;
    s32 dx;
    s32 dz;
    s32 lim_x;
    s32 lim_z;
    s32 sz_x;
    s32 sz_y;
    s32 sz_z;
    s32 pad2C;
    s32 sx_x;
    s32 sx_y;
    s32 sx_z;
    s32 pad3C;
    s32 dsz_x;
    s32 dsz_z;
    s32 dsx_x;
    s32 dsx_z;
    s32 rx;
    s32 aux;
    s32 rz;
    s32 pad5C;
    s32 bx;
    s32 by;
    s32 bz;
    s32 pad6C;
    s32 ax;
    s32 ay;
    s32 az;
    s32 pad7C;
    s32 ebz_x;
    s32 ebz_z;
    s32 ebx_x;
    s32 ebx_z;
    s32 cbz_x;
    s32 cbz_z;
    s32 cbx_x;
    s32 cbx_z;
    s32 lin_x;
    s32 lin_z;
    s16 acc_x;
    s16 acc_z;
    s16 ant_x;
    s16 ant_z;
    s32 d_sz;
    s32 d_sx;
    s32 d_bz;
    s32 d_bx;
    s16 paso_x;
    s16 paso_z;
    s16 celda_x;
    s16 celda_z;
    s32 pend_x;
    s32 pend_z;
    ZonaColision copia[2];
    ZonaColision* zonas[16];
    s16 celdas[16];
    s16 n;
    s16 cual;
    s16 prev;
    u16 baldosa;
    s16 t0;
    s16 t1;
    s16 t2;
    s16 t3;
} TrabajoRecorrido;

/*
 * Este archivo contiene solo macros que reproducen las instrucciones del original, y la lista de
 * registros destruidos de cada una contiene unicamente los registros que su ensamblador escribe
 * (mas "memory" cuando almacena).
 *
 * Macros de vector del motor. El original las escribio como sentencias de ensamblador en linea
 * con los temporales fijos $8..$14 (t0..t6): el ejecutable las delata porque cada vector entra
 * por "move $t0, puntero" y se resta con sub/add (con captura de desbordamiento), que GCC no
 * genera desde C. No son comandos del GTE salvo GEO_NORMA2_XZ. Las sentencias se encadenan por
 * los temporales: una deja t1..t3 cargados y la siguiente los consume, de modo que el orden
 * entre ellas es el de las macros. El resto de cada funcion (ramas, bucles, llamadas) es C
 * ordinario; las llamadas a libgte se hacen con sus prototipos de LIBGTE.H.
 *
 * Las que reciben una direccion la copian a $t0 al principio.
 *
 * GEO_CARGAR_W(p)        t1..t3 = vector de 3 palabras en p
 * GEO_RESTAR_W(p)        t4..t6 = t1..t3 - (vector de 3 palabras en p)
 * GEO_GUARDAR_W_T4(p)    vector de 3 palabras en p = t4..t6 (tras GEO_RESTAR_W)
 * GEO_GUARDAR_H_T4(p)    vector de 3 medias palabras en p = t4..t6
 * GEO_GUARDAR_W_T1(p)    vector de 3 palabras en p = t1..t3
 * GEO_COMPLEMENTO(p)     t1..t3 = 0x1000 - vector de 3 medias palabras en p
 * GEO_GUARDAR_H_T1(p)    vector de 3 medias palabras en p = t1..t3
 * GEO_IDENTIDAD(p)       matriz de 3x3 de medias palabras en p = identidad (0x1000)
 * GEO_CARGAR_WH(p)       t1 = palabra y t2 = media palabra de los 6 bytes de p
 * GEO_OR_WH(p)           t1 = t1 | t2 | (palabra de p) | (media palabra de p + 4)
 * GEO_GUARDAR_WH(p)      6 bytes de p = t1 (palabra) y t2 (media palabra)
 * GEO_GUARDAR_1W_T1(p) palabra de p = t1
 * GEO_CERO_W(p)          vector de 3 palabras en p = 0
 * GEO_CERO_WH(p)         6 bytes de p = 0 (una palabra y una media palabra)
 * GEO_NORMA2_XZ(v, d)    *d = x*x + z*z del vector de medias palabras v (producto por el GTE)
 * GEO_CARGAR_H(p)        t1..t3 = vector de 3 medias palabras con signo en p
 * GEO_SUMAR_H(p)         las 3 medias palabras de p += t1..t3 (tras GEO_CARGAR_H)
 * GEO_RELLENAR_1000(p)   vector de 3 palabras en p = 0x1000 (t1..t3 y t4 quedan con 0x1000)
 */
#define GEO_CARGAR_W(p) \
    __asm__ volatile ("move $8, %0\n\tlw $9, 0($8)\n\tlw $10, 4($8)\n\tlw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "memory")
#define GEO_RESTAR_W(p) \
    __asm__ volatile ("move $8, %0\n\tlw $12, 0($8)\n\tlw $13, 4($8)\n\tlw $14, 8($8)\n\t" \
                      "sub $12, $9, $12\n\tsub $13, $10, $13\n\tsub $14, $11, $14" \
                      : : "r"(p) : "$8", "$12", "$13", "$14", "memory")
/*
 * Guarda en p el vector de tres palabras de t4..t6 ($12..$14). Depende de que un GEO_RESTAR_W previo
 * haya dejado ahi la resta; la direccion se copia a $8 como en el resto de macros del grupo.
 */
#define GEO_GUARDAR_W_T4(p) \
    __asm__ volatile ("move $8, %0\n\tsw $12, 0($8)\n\tsw $13, 4($8)\n\tsw $14, 8($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_GUARDAR_H_T4(p) \
    __asm__ volatile ("move $8, %0\n\tsh $12, 0($8)\n\tsh $13, 2($8)\n\tsh $14, 4($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_GUARDAR_W_T1(p) \
    __asm__ volatile ("move $8, %0\n\tsw $9, 0($8)\n\tsw $10, 4($8)\n\tsw $11, 8($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_COMPLEMENTO(p) \
    __asm__ volatile ("move $8, %0\n\taddi $12, $0, 0x1000\n\tlh $9, 0($8)\n\tlh $10, 2($8)\n\t" \
                      "lh $11, 4($8)\n\tsub $9, $12, $9\n\tsub $10, $12, $10\n\tsub $11, $12, $11" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "$12", "memory")
/*
 * GEO_GUARDAR_H_T1(p): tres medias palabras de p = t1..t3 en una sola sentencia asm, que es como el
 * original las emite (move $t0, puntero y tres sh sobre $t0: 0x80016F20, 0x80018CAC, 0x800192B8, 0x8002EF68
 * y 0x8002F7A0). Partirla en dos sentencias no existe en el original y solo cambia el reparto de registros
 * del compilador. Lee $9..$11 sin declararlos, igual que GEO_GUARDAR_W_T1: el acoplamiento con la macro
 * previa es del original y debe conservarse el orden de sentencias.
 */
#define GEO_GUARDAR_H_T1(p) \
    __asm__ volatile ("move $8, %0\n\tsh $9, 0($8)\n\tsh $10, 2($8)\n\tsh $11, 4($8)" \
                      : : "r"(p) : "$8", "memory")
/*
 * Matriz identidad de 3x3 medias palabras mas traslacion nula, en una sola sentencia: el original la
 * escribe con "move t0, puntero ; ori t1, zero, 0x1000" y diez almacenes seguidos (sw/sh sobre t0).
 */
#define GEO_IDENTIDAD(p) \
    __asm__ volatile ("move $8, %0\n\tori $9, $0, 0x1000\n\tsw $9, 0($8)\n\tsw $0, 4($8)\n\t" \
                      "sw $9, 8($8)\n\tsw $0, 12($8)\n\tsh $9, 16($8)\n\tsw $0, 20($8)\n\t" \
                      "sw $0, 24($8)\n\tsw $0, 28($8)" \
                      : : "r"(p) : "$8", "$9", "memory")
#define GEO_CARGAR_WH(p) \
    __asm__ volatile ("move $8, %0\n\tlw $9, 0($8)\n\tlh $10, 4($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "memory")
#define GEO_OR_WH(p) \
    __asm__ volatile ("move $8, %0\n\tlw $11, 0($8)\n\tlh $12, 4($8)\n\t" \
                      "or $9, $10, $9\n\tor $9, $11, $9\n\tor $9, $12, $9" \
                      : : "r"(p) : "$8", "$9", "$11", "$12", "memory")
#define GEO_GUARDAR_WH(p) \
    __asm__ volatile ("move $8, %0\n\tsw $9, 0($8)\n\tsh $10, 4($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_GUARDAR_1W_T1(p) \
    __asm__ volatile ("move $8, %0\n\tsw $9, 0($8)" : : "r"(p) : "$8", "memory")
/*
 * Puesta a cero de un vector de tres palabras (GEO_CERO_W) y de seis bytes, una palabra y una
 * media palabra (GEO_CERO_WH), y carga de tres medias palabras con signo en t1..t3
 * (GEO_CARGAR_H). El original las escribio con "move t0, puntero" y almacenes o cargas sobre t0
 * (func_80020B90): GEO_CERO_W en 0x80020CE4, 0x800251A4 y 0x80025690; GEO_CERO_WH en 0x80020CF8,
 * 0x80024F1C y 0x800251C0; GEO_CARGAR_H en 0x80023290. Las usa tambien la logica de niveles:
 * GEO_CERO_W en 0x8002BF3C (LogicaZonaEventos), 0x8002EA04 (LogicaBloqueEmpujable) y 0x8002F134 y 0x8002F150
 * (LogicaProyectil); GEO_CERO_WH en 0x8002BF58, 0x8002EE3C y 0x8002F11C; GEO_CARGAR_H en 0x8002EFBC
 * (LogicaEfectoAnclado) y 0x8002F7B4 (LogicaZonaSonda); GEO_GUARDAR_H_T1 en 0x8002EF68 y 0x8002F7A0.
 */
#define GEO_CERO_W(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsw $0, 4($8)\n\tsw $0, 8($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_CERO_WH(p) \
    __asm__ volatile ("move $8, %0\n\tsw $0, 0($8)\n\tsh $0, 4($8)" \
                      : : "r"(p) : "$8", "memory")
#define GEO_CARGAR_H(p) \
    __asm__ volatile ("move $8, %0\n\tlh $9, 0($8)\n\tlh $10, 2($8)\n\tlh $11, 4($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "memory")
#define GEO_NORMA2_XZ(v, d) \
    __asm__ volatile ("lh $8, 0(%1)\n\tlh $9, 4(%1)\n\tmtc2 $8, $9\n\tmtc2 $9, $11\n\tnop\n\tnop\n\t" \
                      "sqr 0\n\tmfc2 $8, $25\n\tmfc2 $9, $27\n\tnop\n\tadd $8, $8, $9\n\tsw $8, 0(%0)" \
                      : : "r"(d), "r"(v) : "$8", "$9", "memory")
/*
 * GEO_SUMAR_W(p): las tres palabras de p += t1..t3 (los temporales que dejo la macro anterior,
 * normalmente GEO_CARGAR_W). Queda en ensamblador en linea (no es GTE) porque consume t1..t3 de la
 * sentencia previa y el original lo escribio con los temporales fijos $8, $12..$14 y add con
 * captura de desbordamiento: escrita en C (p->x += d0, ...) func_800353B0 pasa de 7961 a 9641
 * puntos, porque sin la sentencia que lo reserva GCC reparte de otro modo los registros s del
 * bucle de las esquinas (el original no hoistea &v80 ni &c104) y carga los sumandos con lw a
 * otros registros.
 */
#define GEO_SUMAR_W(p) \
    __asm__ volatile ("move $8, %0\n\tlw $12, 0($8)\n\tlw $13, 4($8)\n\tlw $14, 8($8)\n\t" \
                      "add $12, $12, $9\n\tadd $13, $13, $10\n\tadd $14, $14, $11\n\t" \
                      "sw $12, 0($8)\n\tsw $13, 4($8)\n\tsw $14, 8($8)" \
                      : : "r"(p) : "$8", "$12", "$13", "$14", "memory")
/*
 * GEO_SUMAR_H(p): las tres medias palabras de p += t1..t3, con los temporales que dejo la macro
 * anterior (GEO_CARGAR_H) y los mismos $8, $12..$14 y add con captura de desbordamiento que
 * GEO_SUMAR_W: el original la escribio en 0x8002F7C4 (LogicaZonaSonda, tras GEO_CARGAR_H en
 * 0x8002F7B4). Lee $9..$11 sin declararlos: GCC 2.8.1 no admite fijar un registro como entrada
 * sin una variable de registro, asi que el acoplamiento con la macro previa es el mismo que el
 * de GEO_GUARDAR_W_T4 y GEO_SUMAR_W y debe conservarse el orden de las sentencias.
 */
#define GEO_SUMAR_H(p) \
    __asm__ volatile ("move $8, %0\n\tlh $12, 0($8)\n\tlh $13, 2($8)\n\tlh $14, 4($8)\n\t" \
                      "add $12, $12, $9\n\tadd $13, $13, $10\n\tadd $14, $14, $11\n\t" \
                      "sh $12, 0($8)\n\tsh $13, 2($8)\n\tsh $14, 4($8)" \
                      : : "r"(p) : "$8", "$12", "$13", "$14", "memory")
/*
 * GEO_RELLENAR_1000(p): las tres palabras de p = 0x1000 (escala unidad de un vector de tres
 * palabras). El original carga el valor en $12 (addiu $t4, zero, 0x1000), lo copia a t1..t3 y lo
 * almacena con tres sw sobre $t0, y deja esos cuatro temporales con 0x1000 (LogicaZonaEventos,
 * 0x8002BF70..0x8002BF8C).
 */
#define GEO_RELLENAR_1000(p) \
    __asm__ volatile ("move $8, %0\n\taddiu $12, $0, 0x1000\n\tmove $9, $12\n\tmove $10, $12\n\t" \
                      "move $11, $12\n\tsw $9, 0($8)\n\tsw $10, 4($8)\n\tsw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "$12", "memory")
/*
 * GEO_DISTANCIA_APROX(p): distancia aproximada al vector de tres palabras de p (d0, d4, d8): el
 * maximo de |x|, |y|, |z| mas un cuarto de cada uno de los otros dos; el resultado, con el bit 0
 * activo, se guarda en p + 0x44. Queda en ensamblador en linea (no es GTE) porque el original lo
 * escribio a mano con noreorder y GCC 2.8.1 no puede reproducir su forma desde C: cada salto
 * condicional lleva un nop explicito en su hueco de retardo, el valor absoluto es bgez + neg sobre
 * el propio registro, la comparacion usa $at (slt $at, t0, t1) y la suma es add con captura de
 * desbordamiento. Escrita en C (valor absoluto, dos comparaciones y una suma) func_800353B0 pasa de
 * 7961 a 11566 puntos: GCC emite el valor absoluto sin saltos y reparte otros registros.
 */
#define GEO_DISTANCIA_APROX(p) \
    __asm__ volatile (".set push\n\t.set noreorder\n\t.set noat\n\t" \
                      "addu $4, %0, $0\n\tlw $8, 0($4)\n\tlw $9, 4($4)\n\tlw $10, 8($4)\n\t" \
                      "bgez $8, 1f\n\tnop\n\tsub $8, $0, $8\n" \
                      "1:\tbgez $9, 2f\n\tnop\n\tsub $9, $0, $9\n" \
                      "2:\taddu $2, $8, $0\n\tbgez $10, 3f\n\tnop\n\tsub $10, $0, $10\n" \
                      "3:\taddu $3, $9, $0\n\tslt $1, $8, $9\n\tbeqz $1, 4f\n\tnop\n\t" \
                      "addu $2, $9, $0\n\taddu $3, $8, $0\n" \
                      "4:\taddu $7, $10, $0\n\tslt $1, $2, $10\n\tbeqz $1, 5f\n\tnop\n\t" \
                      "addu $7, $2, $0\n\taddu $2, $10, $0\n" \
                      "5:\tsrl $3, $3, 2\n\tsrl $7, $7, 2\n\tadd $2, $2, $3\n\tadd $2, $2, $7\n\t" \
                      "ori $2, $2, 1\n\taddiu $5, %0, 0x44\n\taddu $4, $5, $0\n\tsw $2, 0($4)\n\t" \
                      ".set pop" \
                      : : "r"(p) : "$1", "$2", "$3", "$4", "$5", "$7", "$8", "$9", "$10", "memory")

/* Area de trabajo de func_80018C68: matriz de rotacion inversa del objeto y vectores locales. */
typedef struct ConsultaMatriz {
    MATRIX m;
    u8 pad20[0x40 - 0x20];
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
} ConsultaMatriz;

/*
 * Area de trabajo de los calculos de volumen contra el objeto actual: nodo en curso, matriz de
 * rotacion inversa del objeto, vectores local (rot, res, dif), indicadores de caja, distancia al
 * cuadrado en el plano y radio.
 */
typedef struct ConsultaVolumen {
    Objeto* actual;
    u8 pad04[0x14 - 0x04];
    MATRIX m;
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
    u8 pad4C[0x50 - 0x4C];
    u32 caja;
    u32 dist2;
    s32 radio;
} ConsultaVolumen;

/*
 * Nodo de la lista D_80069580 que recorre func_80019180: indicadores en +8 (bit 1 = siempre
 * candidato, bit 0 = prueba directa sin rotar), posicion en +0x10, angulos en +0x20, limites
 * en x (+0x28), y (+0x2A) y z (+0x2C) y etiqueta de grupo en +0x34.
 */
typedef struct NodoVolumen {
    struct NodoVolumen* sig;
    u8 pad04[0x08 - 0x04];
    u32 indicadores;
    u8 pad0C[0x10 - 0x0C];
    VECTOR pos;
    SVECTOR rot;
    s16 lim_x;
    s16 lim_y;
    s16 lim_z;
    u8 pad2E[0x34 - 0x2E];
    s16 etiqueta;
} NodoVolumen;

/* Area de trabajo de func_80019180: matriz de rotacion inversa, vectores local y diferencia. */
typedef struct ConsultaPlano {
    MATRIX m;
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
} ConsultaPlano;

/*
 * Area de trabajo de func_80016ED0: nodo en curso, matriz de rotacion inversa del objeto,
 * vectores local (rot, res, dif), copia de la caja del objeto (min, max), valor temporal de
 * banderas o distancia al cuadrado, radio y copia de la posicion.
 */
typedef struct ConsultaCaja {
    Objeto* actual;
    MATRIX m;
    SVECTOR rot;
    SVECTOR res;
    SVECTOR dif;
    SVECTOR min;
    SVECTOR max;
    u32 tmp;
    s32 radio;
    VECTOR pos;
} ConsultaCaja;
extern void func_80019364(s32* zonas);
extern ZonaColision* func_8001BF9C(s32* punto, s16 grupo);

#endif
