#include "common.h"
#include "arranque.h"
#include "globales.h"
#include "cargador.h"
#include "eventos.h"

/* Nombre del archivo de partida en la tarjeta de memoria: unidad, serie del disco y titulo. */
char D_8005E04C[] = "bu00:BASLUS-00838 BBLIT";

/* Interior de D_8005E04C: nombre del archivo sin el prefijo "bu00:", tal como lo lista el directorio. */
extern s8 D_8005E051[];

/* Directorio de cada tarjeta: 15 entradas DIRENTRY de 0x28 bytes por ranura (0x258 bytes). */
extern s8 D_800697B0[];

/* Entrada de directorio de libmcrd (struct DIRENTRY del SDK, 0x28 bytes): nombre, atributos, tamano, enlace, cabeza y sistema. */
typedef struct EntradaDirectorio {
    char nombre[20];
    s32 attr;
    s32 tam;
    s32 sig;
    s32 cabeza;
    s32 sistema;
} EntradaDirectorio;

/* Llamadas de la BIOS y de libapi. */
extern s32 VSync(s32 modo);
extern s32 open(char* nombre, u32 modo);
extern s32 lseek(s32 fd, s32 desplazamiento, s32 origen);
extern s32 read(s32 fd, void* destino, s32 cantidad);
extern s32 write(s32 fd, void* origen, s32 cantidad);
extern s32 close(s32 fd);
extern s32 MemCardSync(s32 modo, s32* cmds, s32* rslt);

extern s32 MemCardAccept(s32 canal);
extern s32 MemCardFormat(s32 canal);
extern s32 MemCardExist(s32 canal);
extern s32 MemCardGetDirentry(s32 canal, char* nombre, s8* dir, s32* cuenta, s32 desde, s32 maximo);
extern void func_80015EC0(void);

/* Patron de busqueda del directorio ("*") y copia del orden pendiente del banco de registros (+0xA), que se limpia al atenderla. */
extern char D_80069324[];
extern u8 D_8006AA7A[];

/*
 * Estado de la tarjeta en la zona direccionada por $gp (+0x30..+0x4C): el original lo declara como datos pequenos
 * (-G8), asi que se define aqui, sin extern, y el enlace le da la direccion de config/symbols.txt. Se declaran
 * ademas en la tabla de datos pequenos de la configuracion para que el ensamblador los reescriba a $gp: con
 * `base_gp` el almacen de la bandera +0x3C ocupaba el hueco de retardo del jal de func_80015E94 en lugar de
 * `li a0,1`. Los usan SondearTarjeta, func_80015E94 y func_80014AC4 (esta lee la cuenta por ranura en +0x38).
 * La bandera +0x3C se declara u8 (la escribe con sb func_80015E94); SondearTarjeta la lee con `lb`
 * (0x800157C0, 0x800158FC, 0x800159E8), de modo que sus lecturas pasan por un acceso s8.
 */
s32 D_80069350;     /* +0x30: suma de control recalculada del directorio */
s32 D_80069354;     /* +0x34: suma de control de referencia, tomada al leer la cabecera */
s32 D_80069358[2];  /* +0x38: entradas de directorio por ranura (la ranura 1 solapa D_8006935C) */
u8 D_8006935C;      /* +0x3C: la tarjeta esta lista (1) o hay que volver a leerla (0) */
s16 D_8006935E[2];  /* +0x3E: bloques usados por ranura (la ranura 1 solapa D_80069360) */
s32 D_80069360;     /* +0x40: orden de libmcrd que acaba de terminar (1 existe, 2 acepta) */
s32 D_80069368;     /* +0x48: resultado de esa orden (0 correcto, 3 tarjeta nueva, 4 sin formato) */
s16 D_8006936C;     /* +0x4C: indice del archivo de partida en el directorio, -1 si no esta */

/*
 * Cabecera del archivo de partida (0x168 bytes, en el desplazamiento 0x200 del archivo): una suma de
 * control en la primera palabra, la mascara de ranuras con partida en +4 y ocho registros de nivel de
 * 0x2C bytes desde +8, cada uno con un valor de 16 bits y un extra de 16 bits.
 */
typedef struct RegistroNivel {
    u16 valor;
    u16 extra;
    u8 resto[0x28];
} RegistroNivel;

typedef struct CabeceraGuardado {
    u32 suma;
    u32 mascara;    /* +4: ranuras con partida guardada, un bit por ranura (SondearTarjeta); func_80014C54 copia su byte bajo al banco de registros */
    RegistroNivel nivel[8];
} CabeceraGuardado;

/* La cabecera viaja en un bloque de 0x200 bytes; el resto no se inicializa. */
typedef struct BloqueCabecera {
    CabeceraGuardado c;
    u8 relleno[0x200 - 0x168];
} BloqueCabecera;

extern CabeceraGuardado D_8006D060;

extern s32 func_80014BA0(void* destino, s32 cantidad, s32 desplazamiento);
extern s32 func_80014EF8(void* origen, s32 cantidad, s32 desplazamiento);
extern s32 func_80014FAC(void);

/*
 * Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18
 * caracteres de D_8005E051 y devuelve su indice, o -1 si no esta.
 */
s32 func_80014AC4(s16 ranura)
{
    s16 i;
    s16 j;
    s8* p;
    s8* q;

    /* El numero de entradas se vuelve a leer en la condicion: el original lo compara contra una
     * copia de la misma carga, no contra una variable aparte. */
    for (i = 0; i < D_80069358[ranura]; i++) {
        /* Primero el nombre buscado y se compara en el orden q, p, como el original. */
        q = D_8005E051;
        p = &D_800697B0[ranura * 0x258] + i * 0x28;
        for (j = 0; j < 0x12; j++) {
            if (*q++ != *p++) {
                break;
            }
        }
        if (j == 0x12) {
            return i;
        }
    }
    return -1;
}

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
            p->c.suma = SumaControl(p, 0x200);
            if (p->c.suma == suma) {
                D_8006D060 = p->c;
                D_8006AA70[4] = D_8006D060.mascara;
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
 * Lee la partida del slot ESTADO_PRINCIPAL->r[BANCO_PARTIDA] (0x180 bytes a partir de 0x400 + (slot - 1) * 0x180) al
 * buffer D_80069520, comprueba la suma de control de los primeros 0x140 bytes (palabra en +4 a cero
 * durante el calculo) y los copia al estado principal; hasta cinco intentos.
 *
 * Reserva de pila: el original reserva 0x220 (`addiu sp` en 0x80014E24) y sin la local el marco es
 * 0x20; la cifra medida sin la local es 4131 y con ella 0.
 */
s32 func_80014E24(void)
{
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[128];
    u8* buf;
    u8* origen;
    u8* destino;
    s32 i;
    u32 suma;
    u32 calculada;

    buf = D_80069520;
    for (i = 0; i < 5; i++) {
        if (func_80014BA0(buf, 0x180, (ESTADO_PRINCIPAL->r[BANCO_PARTIDA] - 1) * 0x180 + 0x400) == 1) {
            suma = *(u32*)(buf + 4);
            *(u32*)(buf + 4) = 0;
            calculada = SumaControl(buf, 0x140);
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
    valor = estado->r[0x07] + (estado->r[0xFC] << 8);
    nivel = estado->r[BANCO_PARTIDA];
    if (nivel == 1) {
        D_8006D060.nivel[0].valor = valor;
        D_8006D060.nivel[0].extra = estado->r[0x05];
    } else if (nivel == 2) {
        D_8006D060.nivel[1].valor = valor;
        D_8006D060.nivel[1].extra = estado->r[0x05];
    } else if (nivel == 3) {
        D_8006D060.nivel[2].valor = valor;
        D_8006D060.nivel[2].extra = estado->r[0x05];
    } else if (nivel == 4) {
        D_8006D060.nivel[3].valor = valor;
        D_8006D060.nivel[3].extra = estado->r[0x05];
    } else if (nivel == 5) {
        D_8006D060.nivel[4].valor = valor;
        D_8006D060.nivel[4].extra = estado->r[0x05];
    } else if (nivel == 6) {
        D_8006D060.nivel[5].valor = valor;
        D_8006D060.nivel[5].extra = estado->r[0x05];
    }
    buf.c = D_8006D060;
    D_8006D060.suma = SumaControl(&buf, 0x200);
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
 * +4 a cero), actualiza la cabecera y escribe el bloque de 0x180 bytes del slot ESTADO_PRINCIPAL->r[BANCO_PARTIDA] (hasta
 * cinco intentos).
 *
 */
s32 func_8001515C(void)
{
    EstadoPrincipal* estado;
    s32 i;

    estado = ESTADO_PRINCIPAL;
    estado->suma = 0;
    estado->suma = SumaControl(estado, 0x140);
    if (func_80014FAC() != 0) {
        for (i = 0; i < 5; i++) {
            if (func_80014EF8((void*)0x80010000, 0x180, (ESTADO_PRINCIPAL->r[BANCO_PARTIDA] - 1) * 0x180 + 0x400) == 1) {
                break;
            }
        }
    } else {
        i = 5;
    }
    return i != 5;
}

/*
 * Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la
 * tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de
 * D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write
 * (hasta cinco intentos), comprobando despues la lectura.
 *
 * Los tipos de las copias fijan el codigo que emite el compilador para cada asignacion de estructura:
 * una estructura de bytes de alineacion 1 genera la comprobacion de alineacion en ejecucion (el
 * original la tiene en la copia del bloque de 0x200 bytes, Fragmento, y en las dos de la cabecera de
 * 0x168 bytes, Copia168); las de palabras (Imagen32 de 0x20 bytes y Bloque80 de 0x80 bytes) generan la
 * copia por palabras sin comprobacion, como las del bloque local, porque el original las hace asi. La
 * direccion dest + 0x200 se escribe en cada uso en lugar de guardarla en una local, y el byte de
 * cabecera es con signo porque el original lo carga con lb.
 *
 * El titulo es una cadena literal del original: sus 46 bytes en Shift-JIS mas el terminador ocupan 0x2F
 * bytes en el .rodata de este archivo (0x80067E34, rellenado hasta 0x30). Se copia con strcpy porque el
 * ensamblador copia exactamente 0x2F bytes, la longitud de la cadena con su terminador, desde una
 * direccion de palabra conocida por el compilador, sin comprobar la alineacion; desde un simbolo externo
 * esa copia pide la comprobacion. Los bytes se escriben con escapes octales para no depender de la
 * codificacion del fuente.
 */
typedef struct BloqueTarjeta {
    s8 cab[4];
    u8 titulo[0x40];
    u8 reservado[0x1C];
    u8 imagen[0x20];
    u8 paleta[0x80];
    u8 cuadro_a[0x80];
    u8 cuadro_b[0x80];
} BloqueTarjeta;

/* Bloque de 0x200 bytes con alineacion de un byte: la copia al buffer comprueba la alineacion en ejecucion, como el original. */
typedef struct Fragmento {
    u8 b[0x200];
} Fragmento;

/* Copia de la cabecera de guardado (0x168 bytes) con alineacion de un byte: el original comprueba la alineacion en ejecucion. */
typedef struct Copia168 {
    u8 b[0x168];
} Copia168;

/* Imagen de icono (0x20 bytes) como ocho palabras: alineacion 4 y copia por palabras, sin comprobacion, como en el original. */
typedef struct Imagen32 {
    u32 w[8];
} Imagen32;

/* Paleta y cuadros de animacion (0x80 bytes cada uno) como 32 palabras: misma copia por palabras que Imagen32. */
typedef struct Bloque80 {
    u32 w[0x20];
} Bloque80;

extern u8 D_8005DFA0[];
extern u8 D_8005DFCC[];
extern void* memset(void* destino, s32 valor, u32 cantidad);
extern char* strcpy(char* destino, const char* origen);

s32 func_800151FC(void)
{
    BloqueTarjeta blq;
    u8* base;
    u8* dest;
    s32 i;
    s32 fd;
    u32 suma;

    blq.cab[0] = 0x53;
    blq.cab[1] = 0x43;
    blq.cab[2] = 0x13;
    blq.cab[3] = 1;
    strcpy((char*)blq.titulo,
           "\202\141\202\225\202\207\202\223\201\100\202\141\202\225\202\216\202\216\202\231\201\100\202\153"
           "\202\217\202\223\202\224\201\100\202\211\202\216\201\100\202\163\202\211\202\215\202\205");
    memset(blq.reservado, 0, 0x1C);
    *(Imagen32*)blq.imagen = *(Imagen32*)D_8005DFA0;
    *(Bloque80*)blq.paleta = *(Bloque80*)(D_8005DFA0 + 0x2C);
    *(Bloque80*)blq.cuadro_a = *(Bloque80*)D_8005DFCC;
    *(Bloque80*)blq.cuadro_b = *(Bloque80*)D_8005DFCC;
    base = D_80069520;
    memset(&D_8006D060, 0, 0x168);
    dest = base + 0x2000;
    memset(dest, 0, 0x2000);
    *(Fragmento*)dest = *(Fragmento*)&blq;
    *(Copia168*)(dest + 0x200) = *(Copia168*)&D_8006D060;
    D_8006D060.suma = SumaControl(dest + 0x200, 0x200);
    *(Copia168*)(dest + 0x200) = *(Copia168*)&D_8006D060;
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
                    suma = SumaControl(base + 0x200, 0x200);
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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 605 con la configuracion versionada (g = 8 del archivo; ejes 73 de operando, 0 reordenadas,
 * 214 insertadas o borradas). Flujo, orden de instrucciones y distribucion de bloques iguales al original;
 * quedan permutaciones de registros temporales (v0/v1) en el resultado de MemCardFormat, en la mascara de ranuras y en el
 * bloque de tarjeta sin formato, el reparto de la suma de bloques por 0x2000 y el reparto de registros del recorrido del directorio.
 * Recorrido del directorio: el original recalcula en cada uso el desplazamiento de la ranura (tres cadenas
 * `sll 4 ; subu ; sll 3` en 0x80015CC0, 0x80015D10 y 0x80015D40) y tiene como registros propios la base del directorio (t1)
 * y la base mas 0x24 (t2). El bucle exterior se escribe con etiqueta y salto hacia atras (`siguiente_entrada`): el optimizador
 * de bucles (`-dL`) no lo recorre, de modo que las tres cadenas de `grupo * 120` quedan en el cuerpo y no se izan como
 * invariantes (solo se recorren los bucles interiores, el de relleno y el de bloques). La fila es una variable de bucle propia
 * (`fila += 0x28; i++;`) y el contador es el mismo `i` de los bucles anteriores (el original usa a1 como contador de los tres
 * bucles y tambien lo toma aqui); las dos bases viven en locales (`directorio`, `sistema`) y las inicializaciones del
 * bucle van dentro de la guardia (`i < D_80069358[0]`), la de `fila` tras la de las bases, como el preludio del original
 * (0x80015CA4 a 0x80015CB8). El relleno de 0x96 palabras avanza un puntero (`*palabras++ = 0;`): la base se carga antes de
 * `move a1,zero`, como en el original (0x80015BAC a 0x80015BB4).
 * La busqueda del final del nombre y el relleno de ceros leen la fila por copias propias (`fila_busqueda`, asignada antes de la
 * guardia de la busqueda, y `fila_relleno`, asignada dentro de la guardia del relleno): el compilador no las propaga a los
 * bucles y deja un `move` en el preludio de cada uno, como los `move a3,a2` del original (0x80015CE0 y 0x80015D14), con lo
 * que la cadena queda en a0. Las dos direcciones se suman como `(j + fila) + grupo * 120` y despues la base, el
 * mismo orden de sumas del original.
 * Queda el reparto de registros de las variables del bucle exterior: la fila cae en a3 (a2 en el original), las copias de la
 * fila en a2 (a3), la base en t0 (t1) y `grupo` en t1 (t0). Volcado `-dg`: la fila tiene 7 referencias ponderadas sobre 46
 * instrucciones de vida y cada copia 3 sobre 9 y 11 (3 * 1 / 9 frente a 7 * 2 / 46), de modo que el asignador toma una copia
 * antes que la fila; la base (8 sobre 96) se toma antes que `grupo` (7 sobre 100).
 * Suma de la entrada del directorio: el original suma primero la fila y el desplazamiento del grupo y
 * despues las dos bases (`addu v0,a2,v0` en 0x80015D4C y `addu v1,v0,t1` y `addu v0,v0,t2` tras ella), de modo que
 * la entrada y la palabra de 0x24 se escriben como `base + (fila + grupo * 120)`. El `move a1,v0 ; bnez a1` de la llamada de
 * formateo (el original comprueba una copia del resultado que despues compara con 1) se reproduce guardando el resultado en
 * la local `rc`, compartida con la del sondeo. La busqueda del final del nombre se
 * escribe con guardia (`j = 0; if (nombre[j] != 0) { do { j++; } while (nombre[j] != 0); }`) como el original
 * (`beqz` a 0x80015D08 tras la primera lectura, 0x80015CDC, y el `addiu` de `j` ya en el cuerpo).
 *
 * Sondeo por cuadro de la tarjeta de memoria. Primero atiende la orden pendiente del banco de registros (D_8006AA70[0xA]: 1 aceptar,
 * 2 formatear, 3 crear el archivo, 4 grabar con sonido, 5 cargar, 6 grabar) y la limpia; despues sondea con MemCardSync(1) la ultima
 * operacion asincrona de libmcrd (cmds = D_80069360, rslt = D_80069368). Con la tarjeta lista lee el directorio de la ranura 0, cuenta
 * los bloques que ocupa cada archivo y comprueba el de la partida. Los destinos de tarjeta nueva y de partidas presentes viven entre
 * las ramas de la orden 6 y se alcanzan con goto desde el sondeo: el original los coloca ahi y el compilador no reordena bloques.
 * El argumento que pasa main se ignora.
 *
 * Reserva de pila: el original reserva 0x40 (`addiu sp` en 0x800156F4) y sin la local el marco es
 * 0x30; la cifra medida sin la local es 807 y con ella 605. La funcion es pendiente: con la local la
 * cifra es menor que sin ella.
 */
void SondearTarjeta(void)
{
    CabeceraGuardado* cabecera;
    s32 cuenta_previa;
    s32 con_parcial;
    s32 completos;
    EntradaDirectorio* entrada;
    s16* bloques;
    s32 grupo;
    s8* directorio;
    s8* sistema;
    s32* palabras;
    s32 salvado;
    u8 valor_salvado_a6;
    s32 partida;
    s32 tam;
    s32 j;
    s32 i;
    s32 fila;
    s32 fila_busqueda;
    s32 fila_relleno;
    u32 rslt;
    s32 estado;
    s32 cmds;
    s32 orden;
    s32 rc;
    s16 ranura;
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva[4];

    ranura = 0;
    if (D_8006AA70[3] == 1) {
        D_8006935C = 0;
        MemCardSync(0, &D_80069360, &D_80069368);
        MemCardAccept(0);
        D_8006AA70[3] = 2;
    }
    orden = D_8006AA70[0xA];
    if (orden != 0) {
        if (orden == 1) {
            D_8006935C = 0;
            MemCardSync(0, &D_80069360, &D_80069368);
            MemCardAccept(0);
        } else if (orden == 2) {
            MemCardSync(0, &D_80069360, &D_80069368);
            rc = MemCardFormat(0);
            if (rc == 0) {
                D_8006AA70[0x1B] = 0xB;
            } else if (rc == 1) {
                D_8006AA70[0x1B] = 0xC;
            }
        } else if (orden == 3) {
            if (*(s8*)&D_8006935C == 1) {
                MemCardSync(0, &D_80069360, &D_80069368);
                if (D_8006935E[0] >= 15) {
                    D_8006AA70[0x1B] = 7;
                } else {
                    func_800151FC();
                    MemCardSync(0, &D_80069360, &D_80069368);
                    MemCardAccept(0);
                }
            }
        } else if (orden == 4) {
            if ((D_8006D060.mascara & (1 << (ESTADO_PRINCIPAL->r[BANCO_PARTIDA] - 1))) != 0 && D_8006AA70[0x1A] == 0) {
                D_8006AA70[0x1B] = 0x13;
                D_8006AA70[0x1A] = 2;
            } else {
                func_8003F06C(D_80069698, 0x40, 1, D_8006967C);
                salvado = ESTADO_PRINCIPAL->r[0x10];
                D_8006AA70[0x25] = 1;
                D_8006AA70[0x1C] = 0;
                D_8006AA70[0x1A] = 0;
                D_8006AA70[0x1B] = 0x10;
                partida = ESTADO_PRINCIPAL->r[BANCO_PARTIDA];
                func_80015EC0();
                ESTADO_PRINCIPAL->r[0xE] = 0x38;
                ESTADO_PRINCIPAL->r[0x8D] = 3;
                ESTADO_PRINCIPAL->r[BANCO_PARTIDA] = partida;
                ESTADO_PRINCIPAL->r[0x10] = salvado;
                cabecera = &D_8006D060;
                cabecera->mascara |= 1 << (partida - 1);
            }
        } else if (orden == 5) {
            if (*(s8*)&D_8006935C == 1) {
                if ((D_8006D060.mascara & (1 << (ESTADO_PRINCIPAL->r[BANCO_PARTIDA] - 1))) != 0) {
                    D_8006AA70[0x1C] = 0;
                    D_8006AA70[0x25] = 1;
                    D_8006AA70[0x1B] = 0x10;
                    func_8003F06C(D_80069698, 0x40, 1, D_8006967C);
                    salvado = ESTADO_PRINCIPAL->r[0x10];
                    if (func_80014E24() != 0) {
                        if (ESTADO_PRINCIPAL->nivel != 0) {
                            ESTADO_PRINCIPAL->r[0xE] = ESTADO_PRINCIPAL->nivel;
                        } else {
                            ESTADO_PRINCIPAL->r[0xE] = 0x38;
                        }
                        D_80069594 = ESTADO_PRINCIPAL->r[0xA6];
                        ESTADO_PRINCIPAL->r[0x10] = salvado;
                        ESTADO_PRINCIPAL->r[0xFB] = 0;
                        ESTADO_PRINCIPAL->r[0x8D] = 3;
                    } else {
                        D_8006AA70[0x1B] = 0x14;
                    }
                } else {
                    func_8003F06C(D_80069698, 0x41, 1, D_8006967C);
                }
            }
        } else if (orden == 6) {
            if (*(s8*)&D_8006935C != 1) {
                goto sin_bandera;
            }
            /* El valor del banco que se restaura tras la llamada vive en una local propia de esta orden: con la
             * local `salvado` de las otras dos ordenes, que guardan otro registro del banco, el reparto de
             * registros del recorrido del directorio empeora (de 725 a 760). */
            valor_salvado_a6 = ESTADO_PRINCIPAL->r[0xA6];
            ESTADO_PRINCIPAL->r[0xA6] = D_80069594;
            if (func_8001515C() != 0) {
                D_8006AA70[8] = 0xA;
            } else {
                D_8006AA70[8] = 1;
                D_8006AA70[0x12] = 1;
            }
            ESTADO_PRINCIPAL->r[0xA6] = valor_salvado_a6;
            goto fin_ordenes;
        tarjeta_nueva:
            D_8006935C = 0;
            MemCardAccept(0);
            D_8006AA70[0x1B] = cmds;
            D_8006AA70[0x1C] = 0;
            D_8006AA70[0x1D] = 0;
            D_8006AA70[0x1E] = 0;
            D_8006AA70[0x22] = 0;
            D_8006AA70[0x20] = 0;
            D_8006AA70[0x23] = 0;
            D_8006AA70[0x24] = 0;
            return;
        con_partidas:
            D_8006AA70[0x24] = 1;
            return;
        sin_bandera:
            D_8006AA70[8] = 2;
            D_8006AA70[0x12] = 1;
        }
    fin_ordenes:
        D_8006AA7A[0] = 0;
    }
    rc = MemCardSync(1, &D_80069360, &D_80069368);
    switch (rc) {
    case -1:
        MemCardExist(0);
        break;
    case 0:
        break;
    case 1:
        cmds = D_80069360;
        switch (cmds) {
        case 1:
            rslt = D_80069368;
            if (rslt != 0) {
                if (rslt == 3) {
                    goto tarjeta_nueva;
                }
                estado = D_8006AA70[0x1B];
                if (estado != 4 && estado != 0xF && estado != 0x10) {
                    D_8006935C = 0;
                    D_80069358[0] = 0;
                    D_80069358[1] = 0;
                    D_8006AA70[0x1B] = 4;
                    D_8006AA70[0x1C] = 0;
                    D_8006AA70[0x1D] = 0;
                    D_8006AA70[0x1E] = cmds;
                    D_8006AA70[0x22] = 0;
                    D_8006AA70[0x20] = 0;
                    D_8006AA70[0x23] = 0;
                    D_8006AA70[0x24] = 0;
                }
            }
            break;
        case 2:
            rslt = D_80069368;
            switch (rslt) {
            case 0:
            case 3:
                D_8006935C = 1;
                palabras = (s32*)D_800697B0;
                for (i = 0; i < 0x96U; i++) {
                    *palabras++ = 0;
                }
                MemCardGetDirentry(ranura, D_80069324, &D_800697B0[ranura * 0x258], &D_80069358[ranura], 0, 15);
                bloques = &D_8006935E[ranura];
                *bloques = 0;
                for (i = 0; i < D_80069358[ranura]; i++) {
                    tam = ((EntradaDirectorio*)((s8*)D_800697B0 + ranura * 0x258))[i].tam;
                    completos = tam / 0x2000;
                    cuenta_previa = *bloques;
                    if ((tam & 0x1FFF) != 0) {
                        /* El bloque parcial se suma en una temporal antes de los completos: el reparto
                         * de registros de la suma se acerca al original (740 a 725). */
                        con_parcial = cuenta_previa + 1;
                        *bloques = con_parcial + completos;
                    } else {
                        *bloques = cuenta_previa + completos;
                    }
                }
                i = 0;
                if (i < D_80069358[0]) {
                    grupo = i;
                    directorio = D_800697B0;
                    sistema = D_800697B0 + 0x24;
                    fila = i;
                siguiente_entrada:
                    j = 0;
                    fila_busqueda = fila;
                    if (directorio[j + fila + grupo * 120] != 0) {
                        do {
                            j++;
                        } while (directorio[j + fila_busqueda + grupo * 120] != 0);
                    }
                    if (j < 0x14) {
                        fila_relleno = fila;
                        do {
                            directorio[j + fila_relleno + grupo * 120] = 0;
                            j++;
                        } while (j < 0x14);
                    }
                    entrada = (EntradaDirectorio*)(directorio + (fila + grupo * 120));
                    entrada->attr = 0;
                    entrada->tam = 0;
                    entrada->sig = 0;
                    entrada->cabeza = 0;
                    *(s32*)(sistema + (fila + grupo * 120)) = 0;
                    fila += 0x28;
                    i++;
                    if (i < D_80069358[0]) {
                        goto siguiente_entrada;
                    }
                }
                D_8006936C = func_80014AC4(ranura);
                if (D_8006936C >= 0) {
                    if (ESTADO_PRINCIPAL->nivel == 0) {
                        D_80069354 = SumaControl(D_800697B0, D_80069358[ranura] * 0x28);
                        func_80014C54();
                    } else {
                        D_80069350 = SumaControl(D_800697B0, D_80069358[ranura] * 0x28);
                        if (D_80069350 != D_80069354) {
                            D_8006935C = 0;
                        }
                    }
                    D_8006AA70[0x1B] = 0xE;
                    if ((D_8006D060.mascara & 0x3F) != 0) {
                        goto con_partidas;
                    }
                    D_8006AA70[0x24] = 2;
                } else {
                    D_8006AA70[0x1B] = 2;
                    D_8006AA70[0x22] = 1;
                }
                break;
            case 4:
                D_8006AA70[0x1B] = 5;
                D_8006AA70[0x1D] = 2;
                break;
            }
            break;
        }
        break;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", SondearTarjeta);
#endif

/*
 * Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...).
 */
void func_80015E94(void)
{
    D_8006935C = 0;
    MemCardSync(1, &D_80069360, &D_80069368);
}
