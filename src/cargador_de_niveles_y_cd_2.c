#include "common.h"
#include "globales.h"
#include "psyq/TYPES.H"
#include "psyq/LIBCD.H"
#include "cargador.h"

/*
 * Descompresor LZSS de las secciones de un contenedor y su lectura de sectores.
 *
 * Las dos rutinas no siguen la convencion de llamada del compilador: comparten el flujo de
 * entrada en registros que ninguna de las dos declara.
 *   - a0: puntero al byte de entrada actual.
 *   - t4: bytes que quedan por leer del sector en curso, menos uno.
 *   - t0: operaciones que quedan por decodificar.
 *   - s0: direccion del siguiente sector dentro del anillo de lectura.
 *   - s1: area de contexto en el scratchpad (la recibe el descompresor en a2).
 * func_80044664 guarda ra y s0..fp en esa area, sin marco de pila, y sale por func_80044904, que
 * los restaura y devuelve v0 (final de la salida, o 0 si el CD fallo). func_80044854 espera a que
 * el retorno de llamada de CD (func_8004109C) deje un sector completo en el anillo y reanuda con
 * a0 apuntando a el.
 *
 * Formato que descomprime func_80044664: el primer byte fija k (bits 0-2) y la escala de las
 * longitudes largas (bits 3-4); los tres siguientes, en big endian, son el numero de operaciones
 * menos una. Cada grupo de ocho operaciones va precedido de un byte de banderas (bit menos
 * significativo primero): 1 = literal; 0 = referencia de dos bytes cuyos 9 + k bits altos son la
 * distancia hacia atras y los 7 - k bajos el indice de la tabla de longitudes.
 */

/*
 * rutina escrita a mano en el original: sin addiu sp, guarda ra y s0..fp en el area de contexto
 * que recibe en a2 (sw ra,0(a2) en 0x80044664 y sw s0..fp,8..0x28(a2) a continuacion) y sale por
 * j func_80044904 (0x80044824, tras la ultima operacion, y 0x8004484C). Mantiene el flujo en a0, t4 y t0.
 */
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd_2", func_80044664);

/*
 * rutina escrita a mano en el original: sin addiu sp, guarda ra en el contexto del llamador
 * (sw ra,4(s1) en 0x80044854), devuelve el flujo en a0, t4 y t0, avanza s0 y sale por
 * j func_80044904 en 0x800448FC (error de la unidad de CD, rama de 0x8004488C).
 */
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd_2", func_80044854);
