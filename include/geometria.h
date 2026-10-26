#ifndef GEOMETRIA_H
#define GEOMETRIA_H

/*
 * Tipos de geometria compartidos por la colision con el terreno y los calculos de volumenes
 * por objeto. Los desplazamientos son los que el ensamblador original lee con lw, lh y lhu.
 */
#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"

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
 * zona. suelo es la altura donde se apoya el punto.
 */
typedef struct ResultadoBaldosa {
    u16 clase;
    u16 flags;
    u16 pendiente;
    u16 pendiente_abs;
    u16 tipo;
    s16 grupo;
    u8 pad0C[4];
    s32 suelo;
    ZonaColision* zona;
} ResultadoBaldosa;

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
 * Macros de vector del motor. El original las escribio como sentencias de ensamblador en linea
 * con los temporales fijos $8..$14 (t0..t6): el ejecutable las delata porque cada vector entra
 * por "move $t0, puntero" y se resta con sub/add (con captura de desbordamiento), que GCC no
 * genera desde C. No son comandos del GTE salvo GEO_NORMA2_XZ. Las sentencias se encadenan por
 * los temporales: una deja t1..t3 cargados y la siguiente los consume, de modo que el orden
 * entre ellas es el de las macros. El resto de cada funcion (ramas, bucles, llamadas) es C
 * ordinario; las llamadas a libgte se hacen con sus prototipos de LIBGTE.H.
 *
 * Las que reciben una direccion la copian a $t0 al principio; las listas de registros
 * destruidos reproducen el efecto sobre la asignacion de registros: GEO_NORMA2_XZ declara tambien
 * $v0 y $v1, lo que desplaza el puntero de destino a $a0 (sin ellos GCC lo deja en $v0); no se
 * sabe que lista declaraba el original.
 *
 * GEO_CARGAR_W(p)        t1..t3 = vector de 3 palabras en p
 * GEO_RESTAR_W(p)        t4..t6 = t1..t3 - (vector de 3 palabras en p)
 * GEO_GUARDAR_H_T4(p)    vector de 3 medias palabras en p = t4..t6
 * GEO_GUARDAR_W_T1(p)    vector de 3 palabras en p = t1..t3
 * GEO_COMPLEMENTO(p)     t1..t3 = 0x1000 - vector de 3 medias palabras en p
 * GEO_GUARDAR_H_T1(p)    vector de 3 medias palabras en p = t1..t3
 * GEO_IDENTIDAD(p)       matriz de 3x3 de medias palabras en p = identidad (0x1000)
 * GEO_CARGAR_WH(p)       t1 = palabra y t2 = media palabra de los 6 bytes de p
 * GEO_OR_WH(p)           t1 = t1 | t2 | (palabra de p) | (media palabra de p + 4)
 * GEO_GUARDAR_WH(p)      6 bytes de p = t1 (palabra) y t2 (media palabra)
 * GEO_GUARDAR_1W_T1(p) palabra de p = t1
 * GEO_NORMA2_XZ(v, d)    *d = x*x + z*z del vector de medias palabras v (producto por el GTE)
 */
#define GEO_CARGAR_W(p) \
    __asm__ volatile ("move $8, %0\n\tlw $9, 0($8)\n\tlw $10, 4($8)\n\tlw $11, 8($8)" \
                      : : "r"(p) : "$8", "$9", "$10", "$11", "memory")
#define GEO_RESTAR_W(p) \
    __asm__ volatile ("move $8, %0\n\tlw $12, 0($8)\n\tlw $13, 4($8)\n\tlw $14, 8($8)\n\t" \
                      "sub $12, $9, $12\n\tsub $13, $10, $13\n\tsub $14, $11, $14" \
                      : : "r"(p) : "$8", "$12", "$13", "$14", "memory")
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
#define GEO_GUARDAR_H_T1(p) \
    do { \
        __asm__ volatile ("move $8, %0\n\tsh $9, 0($8)" : : "r"(p) : "$8", "memory"); \
        __asm__ volatile ("sh $10, 2($8)\n\tsh $11, 4($8)" : : : "memory"); \
    } while (0)
/*
 * Barrera vacia: no emite codigo. Cada sentencia asm cuenta como una instruccion para el
 * asignador de registros; las barreras alargan la vida de los punteros de trabajo.
 */
#define GEO_BARRERA() __asm__ volatile ("" : : : "memory")
/*
 * La matriz identidad se parte en una sentencia por almacen (mas dos barreras). El binario es el
 * mismo que con una sola sentencia; la particion es un recurso de asignacion de registros, no
 * un dato del original: con una sentencia, func_80018D98 y func_80018F80 asignan s2 y s3 al reves.
 */
#define GEO_IDENTIDAD(p) \
    do { \
        __asm__ volatile ("move $8, %0\n\tori $9, $0, 0x1000" : : "r"(p) : "$8", "$9", "memory"); \
        __asm__ volatile ("sw $9, 0($8)" : : : "memory"); \
        __asm__ volatile ("sw $0, 4($8)" : : : "memory"); \
        __asm__ volatile ("sw $9, 8($8)" : : : "memory"); \
        __asm__ volatile ("sw $0, 12($8)" : : : "memory"); \
        __asm__ volatile ("sh $9, 16($8)" : : : "memory"); \
        __asm__ volatile ("sw $0, 20($8)" : : : "memory"); \
        __asm__ volatile ("sw $0, 24($8)" : : : "memory"); \
        __asm__ volatile ("sw $0, 28($8)" : : : "memory"); \
        GEO_BARRERA(); \
        GEO_BARRERA(); \
    } while (0)
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
#define GEO_NORMA2_XZ(v, d) \
    __asm__ volatile ("lh $8, 0(%1)\n\tlh $9, 4(%1)\n\tmtc2 $8, $9\n\tmtc2 $9, $11\n\tnop\n\tnop\n\t" \
                      "sqr 0\n\tmfc2 $8, $25\n\tmfc2 $9, $27\n\tnop\n\tadd $8, $8, $9\n\tsw $8, 0(%0)" \
                      : : "r"(d), "r"(v) : "$2", "$3", "$8", "$9", "memory")
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

/*
 * Objeto del motor tal como lo ven los calculos de volumen: indicadores en +8, lista enlazada
 * en +0x10 (la cabeza vive en D_80069630), radio en +0x20, tipo en +0x2A (2 = solido), alcance
 * al cuadrado en +0x30, cajas minima y maxima en +0x48 y +0x50, enlaces de pertenencia en +0x6C
 * y +0x70, angulos en +0xDC y posicion en +0xE4.
 */
typedef struct ObjetoVolumen {
    u8 pad00[0x08];
    u32 indicadores;
    u8 pad0C[0x04];
    struct ObjetoVolumen* sig;
    u8 pad14[0x20 - 0x14];
    s16 radio;
    u8 pad22[0x26 - 0x22];
    s16 etiqueta;
    u8 pad28[0x2A - 0x28];
    s16 tipo;
    u8 pad2C[0x30 - 0x2C];
    u32 alcance2;
    u8 pad34[0x48 - 0x34];
    SVECTOR min;
    SVECTOR max;
    u8 pad58[0x6C - 0x58];
    struct ObjetoVolumen* rel1;
    struct ObjetoVolumen* rel2;
    u8 pad74[0xDC - 0x74];
    SVECTOR rot;
    VECTOR pos;
} ObjetoVolumen;

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
    ObjetoVolumen* actual;
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
    ObjetoVolumen* actual;
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

#endif
