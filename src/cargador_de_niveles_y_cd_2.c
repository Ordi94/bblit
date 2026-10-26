#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBCD.H"

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
 * a0 apuntando a el. El compilador no puede producir esa forma: reserva marco, guarda ra en la
 * pila y no conserva a0, t4, t0 ni s0 entre llamadas. Por eso las dos conservan el ensamblador
 * original en la construccion normal y, bajo NON_MATCHING, una descripcion en C del flujo con el
 * estado explicito en una estructura.
 */

/* Area de contexto del descompresor en el scratchpad (la tabla de longitudes empieza en +0x38). */
typedef struct ContextoDescompresion {
    u32 retorno;
    u32 retorno_lectura;
    u32 guardados[9];
    u32 anillo_inicio;
    u32 anillo_fin;
    u16 umbral;
    u16 parametros;
    u16 longitudes[128];
} ContextoDescompresion;

/* Estado del flujo de entrada que el original conserva en registros (ver arriba). */
typedef struct FlujoEntrada {
    u8* actual;
    u8* sector_siguiente;
    s32 restantes;
    u32 operaciones;
    ContextoDescompresion* contexto;
} FlujoEntrada;

extern u32 D_8006947C;
extern u32 D_80069480;
extern u32 D_80069490;
extern u32 D_8006949C;
extern u16 D_8006955E;

extern s32 func_80044904(void);
/* Entrada y salida de seccion critica (llamadas al sistema de 16 bytes sin nombre en el simbolo). */
extern void func_8004E66C(void);
extern void func_8004E67C(void);
extern void func_80044854(FlujoEntrada* flujo);

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 13855 con la configuracion versionada (g = 0 del archivo). El original no
 * usa marco de pila, guarda ra y s0..fp en el area de contexto que recibe en a2 y mantiene el flujo
 * de entrada en a0, t4 y t0 durante todo el cuerpo, forma que GCC no emite. La descripcion en C
 * sigue el algoritmo instruccion por instruccion. Variantes probadas: 1 (estado en estructura); las
 * otras formas dependen de variables de registro, que no pueden ser los argumentos a0 a a2.
 *
 * Descomprime el flujo `entrada` en `salida`. El primer byte fija k (bits 0-2) y la escala de
 * las longitudes largas (bits 3-4); los tres siguientes, en big endian, son el numero de
 * operaciones menos una. Cada grupo de ocho operaciones va precedido de un byte de banderas
 * (bit menos significativo primero): 1 = literal; 0 = referencia de dos bytes cuyos 9 + k bits
 * altos son la distancia hacia atras y los 7 - k bajos el indice de la tabla de longitudes.
 * La tabla tiene (0x7F >> k) + 1 entradas; hasta el umbral crece de uno en uno desde 2 y
 * despues de 2^escala en 2^escala. Devuelve el final de la salida.
 */
s32 func_80044664(u8* entrada, u8* salida, ContextoDescompresion* contexto)
{
    FlujoEntrada flujo;
    u16 parametros;
    u32 k;
    u32 mascara;
    u32 i;
    u32 valor;
    u32 bandera;
    u32 banderas;
    u32 codigo;
    u8* origen;
    u16 longitud;
    u16 desplazamiento;

    contexto->anillo_inicio = D_80069490;
    contexto->anillo_fin = D_8006947C;
    flujo.actual = entrada;
    flujo.contexto = contexto;
    flujo.sector_siguiente = entrada;
    func_80044854(&flujo);
    parametros = *flujo.actual;
    flujo.actual++;
    contexto->umbral = 0x13;
    k = parametros & 7;
    mascara = (0x7F >> k) & 0xFFFF;
    contexto->parametros = parametros;
    if (mascara < 0x1F) {
        contexto->umbral = mascara >> 1;
    }
    desplazamiento = 7 - k;
    for (i = 0; i <= mascara; i++) {
        valor = i;
        if (contexto->umbral < (i & 0xFFFF)) {
            valor = contexto->umbral
                + (((i - contexto->umbral) & 0xFFFF) << ((contexto->parametros >> 3) & 3));
        }
        contexto->longitudes[i] = valor + 2;
    }
    flujo.operaciones = (flujo.actual[0] << 16) | (flujo.actual[1] << 8) | flujo.actual[2];
    flujo.actual += 3;
    flujo.restantes -= 4;
    mascara = 0x7F >> k;
    for (;;) {
        banderas = *flujo.actual++ | 0x100;
        if (flujo.restantes-- == 0) {
            func_80044854(&flujo);
        }
        for (;;) {
            bandera = banderas & 1;
            banderas >>= 1;
            if (banderas == 0) {
                break;
            }
            codigo = *flujo.actual++;
            if (bandera != 0) {
                *salida++ = codigo;
            } else {
                if (flujo.restantes-- == 0) {
                    func_80044854(&flujo);
                }
                codigo = (codigo << 8) + *flujo.actual++;
                origen = salida - (codigo >> desplazamiento);
                longitud = contexto->longitudes[codigo & mascara];
                do {
                    *salida++ = *origen++;
                } while (longitud-- != 0);
            }
            if (flujo.restantes-- == 0) {
                func_80044854(&flujo);
            }
            if (flujo.operaciones-- == 0) {
                D_8006949C = (u32)flujo.sector_siguiente;
                return (s32)salida;
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd_2", func_80044664);
#endif

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 5145 con la configuracion versionada (g = 0 del archivo). El original guarda
 * ra en el contexto del llamador (4(s1)), devuelve el flujo en a0, t4 y t0 y avanza s0, que son
 * registros del llamador que GCC no deja usar sin marco; no es expresable como funcion C con
 * parametros. Variantes probadas: 2 (estado en estructura, 5145; variables de registro globales en
 * a0, t4, t0, s0 y s1, 3955).
 *
 * Espera un sector completo en el anillo de lectura y deja el flujo apuntando a su primer byte.
 * Sondea el contador de bytes disponibles (D_80069480) hasta 0xFFFF veces; si la unidad informa
 * un error (estado & 0x15) abandona la descompresion con resultado 0, y si la lectura termino sin
 * datos pone a cero las operaciones restantes para que el descompresor cierre la salida. El
 * descuento del contador va entre las dos llamadas de seccion critica porque lo modifica tambien
 * el retorno de llamada de CD.
 */
void func_80044854(FlujoEntrada* flujo)
{
    s32 intentos;

    intentos = 0;
    while (D_80069480 == 0) {
        intentos++;
        if (intentos != 0xFFFF) {
            continue;
        }
        if (CdStatus() & 0x15) {
            func_80044904();
            return;
        }
        if (D_8006955E == 0) {
            flujo->operaciones = 0;
            flujo->restantes = 0x7FF;
            return;
        }
        intentos = 0;
    }
    func_8004E66C();
    D_80069480 -= 0x800;
    func_8004E67C();
    flujo->actual = flujo->sector_siguiente;
    flujo->sector_siguiente += 0x800;
    if ((u32)flujo->sector_siguiente >= flujo->contexto->anillo_fin) {
        flujo->sector_siguiente = (u8*)flujo->contexto->anillo_inicio;
    }
    flujo->restantes = 0x7FF;
}
#else
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd_2", func_80044854);
#endif
