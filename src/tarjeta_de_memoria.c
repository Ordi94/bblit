#include "common.h"
#include "arranque.h"
#include "globales.h"

/* Nombre del archivo de partida en la tarjeta de memoria: unidad, serie del disco y titulo. */
char D_8005E04C[] = "bu00:BASLUS-00838 BBLIT";

/* Interior de D_8005E04C: nombre del archivo sin el prefijo "bu00:", tal como lo lista el directorio. */
extern s8 D_8005E051[];

/* Directorio de cada tarjeta: 15 entradas DIRENTRY de 0x28 bytes por ranura (0x258 bytes). */
extern s8 D_800697B0[];

/* Llamadas de la BIOS y de libapi. */
extern s32 VSync(s32 modo);
extern s32 open(char* nombre, u32 modo);
extern s32 lseek(s32 fd, s32 desplazamiento, s32 origen);
extern s32 read(s32 fd, void* destino, s32 cantidad);
extern s32 write(s32 fd, void* origen, s32 cantidad);
extern s32 close(s32 fd);
extern s32 MemCardSync(s32 modo, s32* cmds, s32* rslt);

/* Los contadores y resultados de libmcrd viven en la zona direccionada por $gp. */

/*
 * Cabecera del archivo de partida (0x168 bytes, en el desplazamiento 0x200 del archivo): una suma de
 * control en la primera palabra, un byte en +4 y ocho registros de nivel de 0x2C bytes desde +8, cada
 * uno con un valor de 16 bits y un extra de 16 bits.
 */
typedef struct RegistroNivel {
    u16 valor;
    u16 extra;
    u8 resto[0x28];
} RegistroNivel;

typedef struct CabeceraGuardado {
    u32 suma;
    u8 b4;
    u8 pad5[3];
    RegistroNivel nivel[8];
} CabeceraGuardado;

/* La cabecera viaja en un bloque de 0x200 bytes; el resto no se inicializa. */
typedef struct BloqueCabecera {
    CabeceraGuardado c;
    u8 relleno[0x200 - 0x168];
} BloqueCabecera;

extern CabeceraGuardado D_8006D060;
/* D_80010076 se escribe como simbolo (cc1 -G8 emite `sb $0,D_80010076`): por un puntero cambiaria la secuencia. */
extern u8 D_80010076;
extern u8* D_80069520;

extern u32 func_80041238(void* datos, s32 cantidad);
extern s32 func_80014BA0(void* destino, s32 cantidad, s32 desplazamiento);
extern s32 func_80014EF8(void* origen, s32 cantidad, s32 desplazamiento);
extern s32 func_80014FAC(void);

#ifdef NON_MATCHING
/*
 * Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18
 * caracteres de D_8005E051 y devuelve su indice, o -1 si no esta.
 *
 * Pendiente: puntuacion 895 con la configuracion versionada (g = 8 del archivo). El original direcciona la tabla de
 * cuentas con `addiu v0,gp,0x38`, que maspsx solo emite desde ASPSX 2.80 (hoy 2.79), y calcula la base del nombre
 * una sola vez antes del bucle. Variantes probadas: 8 (bucles por indice y por puntero).
 */
s32 func_80014AC4(s16 ranura)
{
    s16 i;
    s16 j;
    s32 n;
    s8* p;
    s8* q;

    n = ((s32*)(base_gp + 0x38))[ranura];
    for (i = 0; i < n; i++) {
        p = &D_800697B0[ranura * 0x258] + i * 0x28;
        q = D_8005E051;
        for (j = 0; j < 0x12; j++) {
            if (*p++ != *q++) {
                break;
            }
        }
        if (j == 0x12) {
            return i;
        }
    }
    return -1;
}
#else
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", func_80014AC4);
#endif

/*
 * Lee `cantidad` bytes del archivo de partida a partir de `desplazamiento`; 1 si se leyo completo.
 *
 */
s32 func_80014BA0(void* destino, s32 cantidad, s32 desplazamiento)
{
    s32 fd;

    VSync(0);
    fd = open(D_8005E04C, 1);
    if (fd != -1 && lseek(fd, desplazamiento, 0) != -1) {
        if (read(fd, destino, cantidad) == cantidad) {
            close(fd);
            return 1;
        }
        close(fd);
    }
    return 0;
}

/*
 * Lee y valida la cabecera del archivo de partida (hasta cinco intentos): comprueba la suma de
 * control sobre los 0x200 bytes con la primera palabra a cero, la copia a D_8006D060 y, si el estado
 * principal vale 0, vuelca los seis registros de nivel en el banco de registros del interprete.
 *
 */
s32 func_80014C54(void)
{
    BloqueCabecera buf;
    BloqueCabecera* p;
    s32 i;
    u32 suma;
    s32 ok;

    for (i = 0; i < 5; i++) {
        if (func_80014BA0(&buf, 0x200, 0x200) != 0) {
            p = &buf;
            suma = p->c.suma;
            p->c.suma = 0;
            p->c.suma = func_80041238(p, 0x200);
            if (p->c.suma == suma) {
                D_8006D060 = p->c;
                D_8006AA70[4] = D_8006D060.b4;
                if (ESTADO_PRINCIPAL->nivel == 0) {
                    D_8006AA70[0x2A] = D_8006D060.nivel[0].valor;
                    D_8006AA70[0x2B] = D_8006D060.nivel[0].valor >> 8;
                    D_8006AA70[0x3A] = D_8006D060.nivel[0].extra;
                    D_8006AA70[0x2C] = D_8006D060.nivel[1].valor;
                    D_8006AA70[0x2D] = D_8006D060.nivel[1].valor >> 8;
                    D_8006AA70[0x3B] = D_8006D060.nivel[1].extra;
                    D_8006AA70[0x2E] = D_8006D060.nivel[2].valor;
                    D_8006AA70[0x2F] = D_8006D060.nivel[2].valor >> 8;
                    D_8006AA70[0x3C] = D_8006D060.nivel[2].extra;
                    D_8006AA70[0x30] = D_8006D060.nivel[3].valor;
                    D_8006AA70[0x31] = D_8006D060.nivel[3].valor >> 8;
                    D_8006AA70[0x3D] = D_8006D060.nivel[3].extra;
                    D_8006AA70[0x32] = D_8006D060.nivel[4].valor;
                    D_8006AA70[0x33] = D_8006D060.nivel[4].valor >> 8;
                    D_8006AA70[0x3E] = D_8006D060.nivel[4].extra;
                    D_8006AA70[0x34] = D_8006D060.nivel[5].valor;
                    D_8006AA70[0x35] = D_8006D060.nivel[5].valor >> 8;
                    D_8006AA70[0x3F] = D_8006D060.nivel[5].extra;
                }
                break;
            }
        }
    }
    ok = 0;
    if (i != 5) {
        ok = 1;
        D_80010076 = 0;
    }
    return ok;
}

/*
 * Lee la partida del slot ESTADO_PRINCIPAL->fDF (0x180 bytes a partir de 0x400 + (slot - 1) * 0x180) al
 * buffer D_80069520, comprueba la suma de control de los primeros 0x140 bytes (palabra en +4 a cero
 * durante el calculo) y los copia al estado principal; hasta cinco intentos. La reserva de 0x200
 * bytes en la pila no se usa: el marco de pila del original la conserva.
 *
 */
s32 func_80014E24(void)
{
    u8 reserva[0x200];
    u8* buf;
    u8* origen;
    u8* destino;
    s32 i;
    u32 suma;
    u32 calculada;

    buf = D_80069520;
    for (i = 0; i < 5; i++) {
        if (func_80014BA0(buf, 0x180, (ESTADO_PRINCIPAL->fDF - 1) * 0x180 + 0x400) == 1) {
            suma = *(u32*)(buf + 4);
            *(u32*)(buf + 4) = 0;
            calculada = func_80041238(buf, 0x140);
            *(u32*)(buf + 4) = calculada;
            if (calculada == suma) {
                origen = buf;
                destino = (u8*)0x80010000;
                i = 0;
                do {
                    *destino++ = *origen++;
                    i++;
                } while (i < 0x140U);
                D_80010076 = 0;
                break;
            }
        }
    }
    return i != 5;
}

/*
 * Escribe `cantidad` bytes en el archivo de partida a partir de `desplazamiento`; 1 si se escribio completo.
 *
 */
s32 func_80014EF8(void* origen, s32 cantidad, s32 desplazamiento)
{
    s32 fd;

    VSync(0);
    fd = open(D_8005E04C, 2);
    if (fd != -1 && lseek(fd, desplazamiento, 0) != -1) {
        if (write(fd, origen, cantidad) == cantidad) {
            close(fd);
            return 1;
        }
        close(fd);
    }
    return 0;
}

/*
 * Escribe la cabecera del archivo de partida: guarda el valor de 16 bits formado por los bytes
 * 0x13C (alto) y 0x47 (bajo) del estado principal y el byte 0x45 en el registro del nivel que indica
 * el byte 0xDF, recalcula la suma de control sobre el bloque de 0x200 bytes y lo graba (hasta cinco
 * intentos).
 *
 */
s32 func_80014FAC(void)
{
    BloqueCabecera buf;
    EstadoPrincipal* estado;
    s32 i;
    u16 valor;
    u8 nivel;

    estado = ESTADO_PRINCIPAL;
    D_8006D060.suma = 0;
    valor = estado->f47 + (estado->f13C << 8);
    nivel = estado->fDF;
    if (nivel == 1) {
        D_8006D060.nivel[0].valor = valor;
        D_8006D060.nivel[0].extra = estado->f45;
    } else if (nivel == 2) {
        D_8006D060.nivel[1].valor = valor;
        D_8006D060.nivel[1].extra = estado->f45;
    } else if (nivel == 3) {
        D_8006D060.nivel[2].valor = valor;
        D_8006D060.nivel[2].extra = estado->f45;
    } else if (nivel == 4) {
        D_8006D060.nivel[3].valor = valor;
        D_8006D060.nivel[3].extra = estado->f45;
    } else if (nivel == 5) {
        D_8006D060.nivel[4].valor = valor;
        D_8006D060.nivel[4].extra = estado->f45;
    } else if (nivel == 6) {
        D_8006D060.nivel[5].valor = valor;
        D_8006D060.nivel[5].extra = estado->f45;
    }
    buf.c = D_8006D060;
    D_8006D060.suma = func_80041238(&buf, 0x200);
    buf.c = D_8006D060;
    for (i = 0; i < 5; i++) {
        if (func_80014EF8(&buf, 0x200, 0x200) != 0) {
            break;
        }
    }
    return i != 5;
}

/*
 * Graba la partida: calcula la suma de control del estado principal (0x140 bytes con la palabra
 * +4 a cero), actualiza la cabecera y escribe el bloque de 0x180 bytes del slot ESTADO_PRINCIPAL->fDF (hasta
 * cinco intentos).
 *
 */
s32 func_8001515C(void)
{
    EstadoPrincipal* estado;
    s32 i;

    estado = ESTADO_PRINCIPAL;
    estado->suma = 0;
    estado->suma = func_80041238(estado, 0x140);
    if (func_80014FAC() != 0) {
        for (i = 0; i < 5; i++) {
            if (func_80014EF8((void*)0x80010000, 0x180, (ESTADO_PRINCIPAL->fDF - 1) * 0x180 + 0x400) == 1) {
                break;
            }
        }
    } else {
        i = 5;
    }
    return i != 5;
}

#ifdef NON_MATCHING
/*
 * Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la
 * tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de
 * D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write
 * (hasta cinco intentos), comprobando despues la lectura.
 *
 * Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). Variantes probadas: 1. No se reprodujo la disposicion de los bloques locales de la pila ni las copias
 * de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento.
 */
typedef struct BloqueTarjeta {
    u8 cab[4];
    u8 titulo[0x40];
    u8 reservado[0x1C];
    u8 imagen[0x20];
    u8 paleta[0x80];
    u8 cuadro_a[0x80];
    u8 cuadro_b[0x80];
} BloqueTarjeta;

typedef struct Fragmento {
    u8 b[0x200];
} Fragmento;

/* El titulo ocupa 0x2F bytes de origen (dos vueltas de 16 y una cola de 15); el campo destino es de 0x40. */
typedef struct TituloTarjeta {
    u8 b[0x2F];
} TituloTarjeta;

extern u8 D_80067E34[];
extern u8 D_8005DFA0[];
extern u8 D_8005DFCC[];
extern void* memset(void* destino, s32 valor, u32 cantidad);

/*
 * NON_MATCHING: intento sin cerrar. Puntuacion 17285 (el archivo se compila con g = 8; 17295 con -G0).
 */
s32 func_800151FC(void)
{
    BloqueTarjeta blq;
    u8* base;
    u8* dest;
    u8* sumada;
    s32 i;
    s32 fd;
    u32 suma;

    blq.cab[0] = 0x53;
    blq.cab[1] = 0x43;
    blq.cab[2] = 0x13;
    blq.cab[3] = 1;
    *(TituloTarjeta*)blq.titulo = *(TituloTarjeta*)D_80067E34;
    memset(blq.reservado, 0, 0x1C);
    base = D_80069520;
    memset(&D_8006D060, 0, 0x168);
    dest = base + 0x2000;
    memset(dest, 0, 0x2000);
    *(Fragmento*)dest = *(Fragmento*)&blq;
    sumada = dest + 0x200;
    *(CabeceraGuardado*)sumada = D_8006D060;
    D_8006D060.suma = func_80041238(sumada, 0x200);
    *(CabeceraGuardado*)sumada = D_8006D060;
    for (i = 0; i < 5; i++) {
        fd = open(D_8005E04C, (blq.cab[3] << 16) | 0x200);
        if (fd != -1) {
            close(fd);
            fd = open(D_8005E04C, 2);
            if (fd != -1) {
                if (write(fd, dest, 0x400) != 0x400) {
                    close(fd);
                    continue;
                }
                close(fd);
                if (func_80014BA0(base, 0x400, 0) != 0) {
                    *(u32*)(base + 0x200) = 0;
                    suma = func_80041238(base + 0x200, 0x200);
                    *(u32*)(base + 0x200) = suma;
                    if (suma == D_8006D060.suma) {
                        break;
                    }
                }
            }
        }
    }
    return i != 5;
}
#else
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", func_800151FC);
#endif

/*
 * Sondeo por cuadro de la tarjeta de memoria (maquina de estados sobre D_8006AA70[0x0A]: 0, 1, 2, 3,
 * 4, 5, 6 con MemCardAccept, MemCardFormat y MemCardSync). Usa $gp en 35 accesos (0x38..0x4C($gp)):
 * pendiente de soporte -G8; sin intento en C, por lo que no hay puntuacion de diff que informar.
 */
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", func_800156F4);

#ifdef NON_MATCHING
/*
 * Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...).
 * Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). El original calcula las dos
 * direcciones de $gp con `addiu a1,gp,0x40` y `addiu a2,gp,0x48` (ASPSX 2.80) y coloca el almacen del byte antes de
 * cargar el modo; con 2.79 la forma no se emite. Variantes probadas: 3.
 */
void func_80015E94(void)
{
    *(u8*)(base_gp + 0x3C) = 0;
    MemCardSync(1, (s32*)(base_gp + 0x40), (s32*)(base_gp + 0x48));
}
#else
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", func_80015E94);
#endif
