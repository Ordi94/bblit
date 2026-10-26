#include "common.h"
#include "cargador.h"
#include "psyq/TYPES.H"
#include "psyq/LIBCD.H"
#include "globales.h"
#include "objetos.h"

/*
 * Cargador de contenedores del disco: tabla de posiciones, lectura de sectores por retorno de
 * llamada y carga de un archivo por identificador.
 *
 * Este archivo se compila con un umbral de datos pequenos (-G8, config/opciones_compilacion.toml):
 * el estado de la lectura vive en variables que el original direcciona con desplazamiento($gp).
 * Se definen aqui sin extern; maspsx las reescribe a $gp y el enlace les da su direccion (tabla
 * datos_pequenos). Algunas (D_80069488, D_800694A4 y D_800694A8) las define tambien otro archivo:
 * son simbolos comunes y el enlazador los funde en uno.
 */

/*
 * Estado de la lectura en curso (zona 0x80069478..0x800694AC, accesos $gp + 0x158..0x18C):
 * D_80069494 indica lectura comprimida por anillo, D_8006948C/D_80069498 son la posicion de
 * escritura (anillo o lineal), D_80069490/D_8006947C el inicio y el fin del anillo, D_80069480 los
 * bytes disponibles en el anillo, D_80069484/D_80069488 los bytes leidos y D_800694A0 los pedidos.
 * Los contadores D_80069484 y D_80069488 son volatile porque el retorno de llamada de CD los
 * modifica mientras el cargador los consulta; sin ello el compilador interpola las cargas de
 * ambos y el codigo ya no coincide con el original.
 */
u32 D_80069478;
u32 D_8006947C;
u32 D_80069480;
volatile s32 D_80069484;
volatile s32 D_80069488;
u32 D_8006948C;
u32 D_80069490;
u32 D_80069494;
u32 D_80069498;
u32 D_8006949C;
s32 D_800694A0;
s32 D_800694A4;
u8 D_800694A8;
s32 D_800694AC;

extern EntradaSector D_8005EE78[];
extern u8 D_8006933C[];
extern u8 D_8006A928[];

extern void func_80040E30(void);

/*
 * Construye al arrancar los registros de archivo a partir de la tabla de sectores: pausa la
 * unidad, espera a que termine el comando y, para cada una de las 113 entradas, deja el tamano
 * y la posicion de CD (minuto, segundo, cuadro) que func_800415A0 usa para iniciar la lectura.
 *
 * D_80069540 se declara como escalar de un byte: con el umbral de datos pequenos el compilador
 * emite su direccion como simbolo (lui y addiu juntos, dentro del bucle de espera) y no la iza
 * fuera del bucle como haria con un arreglo; el original la calcula dentro del bucle.
 * Cada entrada se lee a locales antes de escribir el registro, que es el orden de las cargas.
 */
void func_80040EB4(void)
{
    s16 i;
    EntradaSector* tabla;
    s32 sector;
    u32 tamano;

    CdControl(9, 0, 0);
    while (CdSync(1, &D_80069540) != 2) {
    }
    tabla = D_8005EE78;
    for (i = 0; i < 0x71; i++) {
        sector = tabla->sector;
        tamano = tabla->tamano;
        D_8005F200[i].habilitado = 1;
        D_8005F200[i].tamano = tamano;
        CdIntToPos(sector, (CdlLOC*)((u8*)D_8005F200 + 12 + i * 16));
        tabla++;
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 390 con la configuracion versionada (g = 8 del archivo). Mismas
 * instrucciones que el original; solo difiere el reparto de registros de la ultima etapa (el
 * original deja el puntero del bucle en a2 y la constante 4 en a3, el indice en t0 en todas las
 * etapas, y copia el puntero de la segunda etapa de una direccion calculada en v1).
 *
 * Recorre la cabecera de secciones de un contenedor (n entradas de tipo, tamano y tamano alineado)
 * y calcula la posicion, en bytes desde el inicio del archivo, de los datos del banco que se pide:
 * devuelve la suma de los tamanos alineados de las secciones que hay entre la primera de tipo 6
 * y la de tipo `tipo`. Como efectos laterales deja el tamano alineado de la seccion `tipo` en
 * D_800694A0 y en D_80069478 la suma de las secciones siguientes hasta la de tipo 4.
 */
s32 func_80040F78(EntradaSeccion* secciones, s32 n, s32 tipo)
{
    s32 i;
    s32 anterior;
    EntradaSeccion* p;

    D_80069478 = 0;
    anterior = 0;
    for (i = 0; i < n; i++) {
        if (secciones[i].tipo == tipo) {
            break;
        }
    }
    D_800694A0 = secciones[i].alineado;
    for (i = 0; i < n; i++) {
        if (secciones[i].tipo == 6) {
            break;
        }
    }
    p = &secciones[i];
    while (p->tipo != tipo) {
        if (i >= n) {
            break;
        }
        anterior += p->alineado;
        p++;
        i++;
    }
    i++;
    p = &secciones[i];
    while (p->tipo != 4) {
        if (i >= n) {
            break;
        }
        D_80069478 += p->alineado;
        p++;
        i++;
    }
    return anterior;
}
#else
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", func_80040F78);
#endif

/*
 * Retorno de llamada de la unidad (CdReadyCallback): cuando hay un sector listo (aviso 1) lo
 * copia con CdGetSector (0x200 palabras) y avanza los contadores. Con lectura comprimida
 * (D_80069494 distinto de cero) copia a un anillo entre D_80069490 y D_8006947C; si no, copia
 * linealmente a D_80069498. Al completar los bytes pedidos (D_800694A0) apaga la espera, pausa
 * la unidad y deja en D_800694AC y en la posicion D_8006A928 el sector siguiente al ultimo leido.
 */
void func_8004109C(u8 aviso)
{
    if (aviso == 1) {
        if (D_80069494 != 0) {
            CdGetSector((void*)D_8006948C, 0x200);
            D_8006948C += 0x800;
            if (D_8006948C >= D_8006947C) {
                D_8006948C = D_80069490;
            }
            D_80069480 += 0x800;
        } else {
            CdGetSector((void*)D_80069498, 0x200);
            D_80069498 += 0x800;
        }
        D_80069484 += 0x800;
        D_80069488 += 0x800;
        func_80040E30();
        if (D_80069484 >= D_800694A0) {
            D_8006955E = 0;
            CdReadyCallback(0);
            CdControl(9, 0, 0);
            D_800694AC = CdPosToInt((CdlLOC*)D_8006A928);
            D_800694AC = D_800694AC + (D_800694A0 + 0x7FF) / 2048;
            CdIntToPos(D_800694AC, (CdlLOC*)D_8006A928);
        }
    } else {
        printf(D_8006933C);
    }
}

/* Inicia la lectura continua de sectores desde la posicion dada; func_8004109C los recoge. */
void func_800411F0(CdlLOC* posicion)
{
    D_8006955E = 1;
    CdReadyCallback((CdlCB)func_8004109C);
    CdControl(6, (u8*)posicion, 0);
}

/*
 * Suma de control de una cabecera: suma de los bytes con signo (lb), como la que se guarda en
 * el offset 0x7FC de la cabecera de un contenedor y en la partida.
 */
s32 func_80041238(s8* datos, s32 n)
{
    s32 i;
    s32 suma;

    suma = 0;
    for (i = 0; i < n; i++) {
        suma += *datos++;
    }
    return suma;
}

/* Copia n bytes de origen a destino, de menor a mayor direccion (n con signo de 16 bits). */
void func_80041264(u8* origen, u8* destino, s16 n)
{
    s32 i;

    for (i = 0; i < n; i++) {
        *destino++ = *origen++;
    }
}

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas
 * instrucciones y mismo flujo que el original; difiere el reparto de registros (el original deja el
 * puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el
 * original rellena. Variantes probadas: 14 (indice o puntero en el bucle de cinco, tipo del
 * contador, temporales para el reparto, orden de declaracion).
 *
 * Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en
 * desplazamientos dentro de cada lista, para que el codigo que las usa no tenga que buscar:
 * las cinco referencias de cada nodo de la lista A apuntan a la lista B (desplazamiento en
 * bytes, multiplo de 0x20), la de cada nodo de B apunta a la lista C (indice por 0x24), y la de
 * cada nodo de C apunta a A (desplazamiento multiplo de 0x10, y los dos campos extra, que solo
 * existen con la bandera 0x20, como indice por 0x10). Un identificador sin nodo se deja intacto.
 * Solo actua sobre las clases 2, 0xE y 0x22. Los nodos empiezan con el enlace al siguiente (+0)
 * y el identificador de 16 bits (+4).
 */
void func_80041298(ContenedorCarga* c)
{
    NodoA* a;
    NodoB* b;
    NodoC* k;
    NodoA* na;
    NodoB* nb;
    u16 id;
    u32 i;
    s32 idx;
    u32 desp;

    if (c->clase == 0xE || c->clase == 2 || c->clase == 0x22) {
        for (a = c->listaA; a != NULL; a = a->sig) {
            for (i = 0; i < 5; i++) {
                id = a->ref[i];
                if (id == 0xFFF0) {
                    break;
                }
                for (nb = c->listaB; nb != NULL; nb = nb->sig) {
                    if (nb->id == id) {
                        break;
                    }
                }
                if (nb != NULL) {
                    desp = ((u8*)nb - (u8*)c->listaB) & 0xFFE0;
                    a->ref[i] = desp;
                }
            }
        }
        for (b = c->listaB; b != NULL; b = b->sig) {
            id = b->refC;
            if (id != 0) {
                for (k = c->listaC; k != NULL; k = k->sig) {
                    if (k->id == id) {
                        break;
                    }
                }
                if (k != NULL) {
                    idx = k - c->listaC;
                    b->desplazamiento = idx * 0x24;
                }
            }
        }
        for (k = c->listaC; k != NULL; k = k->sig) {
            id = k->refA;
            if (id != 0) {
                for (na = c->listaA; na != NULL; na = na->sig) {
                    if (na->id == id) {
                        break;
                    }
                }
                if (na != NULL) {
                    desp = ((u8*)na - (u8*)c->listaA) & 0xFFF0;
                    k->refA = desp;
                }
            }
            if (k->banderas & 0x20) {
                for (na = c->listaA; na != NULL; na = na->sig) {
                    if (na->id == k->refA1) {
                        break;
                    }
                }
                if (na != NULL) {
                    idx = na - c->listaA;
                    k->refA1 = idx * 0x10;
                }
                for (na = c->listaA; na != NULL; na = na->sig) {
                    if (na->id == k->refA2) {
                        break;
                    }
                }
                if (na != NULL) {
                    idx = na - c->listaA;
                    k->refA2 = idx * 0x10;
                }
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", func_80041298);
#endif

void func_8004153C(u8* origen, u32 n, u8* destino)
{
    s32 i;

    if (origen >= destino) {
        i = 0;
        while (i < n) {
            destino[i] = origen[i];
            i++;
        }
    } else {
        i = n - 1;
        while (i >= 0) {
            destino[i] = origen[i];
            i--;
        }
    }
}

INCLUDE_RODATA("asm/nonmatchings/cargador_de_niveles_y_cd", D_80067F18);

/*
 * Acceso por desplazamiento a los registros de la escena. Los nodos que el script de carga rellena
 * (entidades de 0x1F4 bytes, recursos de 0x58, volumenes de 0x3C...) solo se conocen por los
 * campos que esta rutina escribe; los que Objeto declara se usan en otros archivos y no se
 * redefinen aqui.
 */
#define EN(tipo, p, desp) (*(tipo*)((u8*)(p) + (desp)))

extern void* memset(void* destino, s32 valor, u32 cantidad);
extern void func_800368E8(void);
extern void func_8003ED6C(void);
extern void func_8003EAEC(void);
extern void func_8003EB48(void);
extern void func_8003EB88(u8* parametros);
extern void func_8003EC3C(u8* parametros);
extern void func_8003ECD4(u8* datos, s32 tamano);
extern void func_8003ECF8(u8* parametros);
extern void func_8003652C(void);
extern void func_800365D0(void);
extern void func_80040DDC(void);
extern void func_800443CC(void);

extern u16 D_800695B4;
extern void* D_80069648;
extern u8 D_80010050;
extern u8 D_8001004F;
extern u32 D_80067E98[];
extern u32 D_8006959C;
extern s32 D_80069678;
extern s16 D_80069670;
extern s16 D_8006967E;
extern s16 D_800695C2;
extern s16 D_8006952E;
extern s32 D_80069548;
extern u8* D_80069570;
extern u8* D_80069644;
extern u8* D_80069528;
extern u8* D_80069538;
extern u8* D_8006966C;
extern u32 D_8006951C;
extern u32 D_800695E4;

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 285 con la configuracion versionada (g = 8 del archivo). La estructura
 * (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco
 * de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados
 * desde el prologo), el orden de las cargas de la cabecera de secciones y el codigo de cada
 * etiqueta, que GCC emite en otro orden. Las posiciones de pila de la tabla de tamanos y de los
 * campos escalares tambien difieren (el original deja la imagen y el rectangulo en las direcciones
 * mas bajas del marco, despues la tabla de secciones y la de tamanos).
 *
 * Carga un contenedor de nivel o escena por su identificador (indice de D_8005F200) en `destino`.
 * Lee la cabecera del archivo, descomprime el script (seccion de tipo 1) y las secciones que sus
 * comandos E piden, y despues interpreta el script: 0x2C reparte la memoria en listas y grupos y
 * lee las secciones de datos, 0x4B elige el banco del idioma y 0x2D abre una serie de chunks
 * (tipo y etiquetas de longitud fija) que construyen los recursos: sonido (0), parametros de
 * sonido (5), entidades (7, 8, 10), volumenes de escena (9), modelos jerarquicos (0x20), recursos
 * (0x22), imagenes (0x29), zonas de colision (0x36), camara y tamano de los grupos (0x3B),
 * demostracion (0x47) y textos (0x49). Devuelve 0 si todo salio bien y 1 si el disco falla, la
 * suma de control de la cabecera no coincide o una descompresion no termina.
 */
s32 func_800415A0(s16 archivo, void* destino)
{
    s32 tamanos[15] = {
        0x4, 0x8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000,
        0x10000
    };
    EntradaSeccion secciones[14];
    u8 campos[0x80];
    GsIMAGE imagen;
    RECT rect;
    RegistroArchivo* registro;
    u8* cursor;
    u8* datos;
    u8* reserva;
    u8* monton;
    u8* nodo;
    u8* hijo;
    u8* hijo_matriz;
    u8* aux;
    u8* modelo;
    u8* destino_seccion;
    s32 posicion;
    s32 compensacion;
    s32 desp_bancos;
    s32 tam_audio;
    s32 desp_texturas;
    u32 n_secciones;
    u32 tam_extra;
    u8* datos_extra;
    u32 i;
    u16 es_jugador;
    u8 audio_cargado;
    u8 banco_cargado;
    u8 pools_listos;
    u8 orden;
    u8 tipo;
    u8 etiqueta;

    /* Memoria de trabajo del cargador: el destino recibe primero el contenido y luego la reserva. */
    datos = (u8*)destino;
    reserva = (u8*)destino;
    D_800695B4 = 1;
    memset(D_8006AA70, 0, 0x100);
    tam_extra = 0;
    datos_extra = NULL;
    es_jugador = 0;
    audio_cargado = 0;
    banco_cargado = 0;
    pools_listos = 0;
    D_8006D928.vpz = 0;
    D_8006D928.vpy = 0;
    D_8006D928.vpx = 0;
    D_80069518 = NULL;
    D_80069504 = NULL;
    D_80069648 = NULL;
    D_80069580 = NULL;
    D_80069590 = NULL;
    func_800368E8();
    func_8003ED6C();
    func_8003EAEC();
    if ((s8)D_80010041 <= 0) {
        D_80010041 = 6;
    }
    if (D_80010050 >= 6) {
        D_80010050 = 0;
    }
    D_800100E6 = D_80069594;
    registro = &D_8005F200[archivo];
    if (registro->tamano == 0) {
        printf("BouzeID %d not found\n", archivo);
    }
    D_800694D0 = 0x80;
    CdControlB(0xE, &D_800694D0, NULL);
    func_80040DDC();
    *(CdlLOC*)D_8006A928 = *(CdlLOC*)registro->posicion;
    *(u32*)(D_8006A928 + 4) = registro->tamano;
    datos = (u8*)destino + 0xA000;
    D_8006948C = (u32)destino;
    D_80069490 = (u32)destino;
    D_8006947C = (u32)datos;
    D_80069494 = registro->habilitado;

    if (D_80069494 != 0) {
        /*
         * Contenedor con lectura por anillo: los sectores van llegando al anillo de
         * D_80069490..D_8006947C y el descompresor los consume. Cabecera, seccion 0 (script) y los
         * comandos E del script, que descomprimen las secciones siguientes a sus destinos.
         */
        CdControlB(1, NULL, &D_80069540);
        if (D_80069540 & 0x10) {
            return 1;
        }
        if (CdControlB(0x15, D_8006A928, &D_80069540) == 0) {
            return 1;
        }
        D_80069484 = 0;
        D_80069488 = 0;
        D_80069480 = 0;
        D_800694A4 = registro->tamano;
        D_800694A0 = registro->tamano;
        func_800411F0((CdlLOC*)D_8006A928);
        if (D_80069480 == 0) {
            do {
                if (CdStatus() & 0x10) {
                    return 1;
                }
            } while (D_80069480 == 0);
        }
        cursor = (u8*)D_80069490;
        if (func_80041238((s8*)cursor, 0x7FC) != *(s32*)(cursor + 0x7FC)) {
            return 1;
        }
        D_80069480 = 0;
        D_80069494 = *(u32*)cursor;
        cursor += 4;
        n_secciones = *(u32*)cursor;
        cursor += 4;
        for (i = 0; i < n_secciones; i++) {
            secciones[i] = *(EntradaSeccion*)cursor;
            cursor += 12;
        }
        posicion = 0;
        D_80069498 = (u32)datos;
        D_800694A0 = secciones[posicion].alineado + secciones[posicion + 1].alineado + 0x800;
        D_8006949C = D_80069490 + 0x800;
        posicion += 2;
        if (func_80044664((u8*)D_8006949C, datos, (void*)0x1F800000) == 0) {
            return 1;
        }
        cursor = datos;
        if (cursor[1] == 0x45) {
            if (*cursor++ == 0x2D) {
                if (*cursor != 0x2E) {
                    do {
                        tipo = *cursor++;
                        if (tipo == 0x45) {
                            func_80041264(cursor, campos, 1);
                            cursor++;
                            destino_seccion = (u8*)D_80067E98[campos[0]];
                            D_800694A0 += secciones[posicion].alineado;
                            posicion++;
                            func_80044664((u8*)D_8006949C, destino_seccion, (void*)0x1F800000);
                            *(u32*)destino_seccion = (u32)D_8006B2F8;
                        }
                    } while (*cursor != 0x2E);
                }
                cursor++;
            }
        }
        datos += 0x1D000;
        D_80069498 = (u32)datos;
        if (func_80044664((u8*)D_8006949C, datos, (void*)0x1F800000) == 0) {
            return 1;
        }
    } else {
        /*
         * Contenedor sin lectura por anillo: cada seccion se lee entera a su destino con una orden
         * de lectura propia y se espera a que el retorno de llamada la complete.
         */
        D_80069484 = 0;
        D_80069488 = 0;
        D_800694A0 = 0x800;
        D_80069498 = (u32)datos;
        D_800694A4 = registro->tamano;
        func_800411F0((CdlLOC*)D_8006A928);
        while (D_8006955E != 0) {
        }
        if (func_80041238((s8*)datos, 0x7FC) != *(s32*)(datos + 0x7FC)) {
            return 1;
        }
        D_80069494 = *(u32*)datos;
        n_secciones = *(u32*)(datos + 4);
        cursor = datos + 8;
        for (i = 0; i < n_secciones; i++) {
            secciones[i] = *(EntradaSeccion*)cursor;
            cursor += 12;
        }
        posicion = 0;
        D_800694A0 = secciones[posicion].alineado;
        D_80069484 = 0;
        D_80069498 = (u32)datos;
        func_800411F0((CdlLOC*)D_8006A928);
        posicion++;
        while (D_8006955E != 0) {
        }
        cursor = datos;
        if (cursor[1] == 0x45) {
            if (*cursor++ == 0x2D) {
                if (*cursor != 0x2E) {
                    do {
                        tipo = *cursor++;
                        if (tipo == 0x45) {
                            func_80041264(cursor, campos, 1);
                            destino_seccion = (u8*)D_80067E98[campos[0]];
                            D_800694A0 = secciones[posicion].alineado;
                            D_80069484 = 0;
                            D_80069498 = (u32)destino_seccion;
                            func_800411F0((CdlLOC*)D_8006A928);
                            posicion++;
                            while (D_8006955E != 0) {
                            }
                            *(u32*)destino_seccion = (u32)D_8006B2F8;
                            cursor++;
                        }
                    } while (*cursor != 0x2E);
                }
                cursor++;
            }
        }
        datos += 0x1D000;
        D_800694A0 = secciones[posicion].alineado;
        D_80069484 = 0;
        D_80069498 = (u32)datos;
        func_800411F0((CdlLOC*)D_8006A928);
        while (D_8006955E != 0) {
        }
    }

    /*
     * Script de carga, ya descomprimido en `datos`. Ordenes de primer nivel hasta el fin 0x2F:
     * 0x2C reparte la memoria en listas y grupos y lee las secciones de datos, 0x4B elige el banco
     * del idioma y 0x2D abre una serie de chunks de recursos (tipo, y etiquetas con longitud
     * fija) hasta el cierre 0x2E.
     */
    cursor = datos;
    for (;;) {
        orden = *cursor;
        if (orden == 0x2F) {
            break;
        }
        cursor++;
        if (orden == 0x2D) {
            if (*cursor == 0x2E) {
                cursor++;
                continue;
            }
            do {
                tipo = *cursor++;
                if (tipo >= 0x4A) {
                    continue;
                }
                switch (tipo) {
                case 0x00:
                    /* Sonido (.-\0\1): audio, fuente de efectos, bancos de texturas e instrumentos. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 4) {
                            func_80041264(cursor, campos, 8);
                            func_8003EB88(campos);
                            cursor += 8;
                        } else if (etiqueta == 1) {
                            func_80041264(cursor, campos, 8);
                            cursor += 8;
                            audio_cargado = 1;
                            tam_audio = *(s32*)campos;
                            reserva += *(s32*)(campos + 4);
                            D_800694A0 = *(s32*)(campos + 4);
                        } else if (etiqueta == 2) {
                            func_80041264(cursor, campos, 8);
                            posicion = *(s32*)campos;
                            D_8006951C = 0x1010;
                            D_800694A0 = *(s32*)(campos + 4);
                            func_8003ECD4(datos + posicion, *(s32*)(campos + 4));
                            D_8006951C += D_800694A0;
                            cursor += 8;
                        } else if (etiqueta == 0x4C) {
                            func_80041264(cursor, campos, 0x30);
                            if (D_80010050 == 0) {
                                desp_texturas = *(s32*)campos;
                                compensacion = *(s32*)(campos + 4);
                            } else if (D_80010050 == 1) {
                                desp_texturas = *(s32*)(campos + 8);
                                compensacion = *(s32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                desp_texturas = *(s32*)(campos + 16);
                                compensacion = *(s32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                desp_texturas = *(s32*)(campos + 24);
                                compensacion = *(s32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                desp_texturas = *(s32*)(campos + 32);
                                compensacion = *(s32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                desp_texturas = *(s32*)(campos + 40);
                                compensacion = *(s32*)(campos + 44);
                            }
                            D_800694A0 = compensacion;
                            aux = datos + desp_texturas;
                            D_800694EC = aux;
                            D_80069598 = (u32*)aux;
                            D_800695FC = (s16*)(aux + 8);
                            cursor += 0x30;
                            D_800694EC = aux + *(s32*)aux;
                            D_80069598 = (u32*)(aux + *(s32*)(aux + 4));
                            reserva += D_800694A0;
                        } else if (etiqueta == 0x4D) {
                            func_80041264(cursor, campos, 0x30);
                            if (D_80010050 == 0) {
                                desp_bancos = *(s32*)campos;
                                compensacion = *(s32*)(campos + 4);
                            } else if (D_80010050 == 1) {
                                desp_bancos = *(s32*)(campos + 8);
                                compensacion = *(s32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                desp_bancos = *(s32*)(campos + 16);
                                compensacion = *(s32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                desp_bancos = *(s32*)(campos + 24);
                                compensacion = *(s32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                desp_bancos = *(s32*)(campos + 32);
                                compensacion = *(s32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                desp_bancos = *(s32*)(campos + 40);
                                compensacion = *(s32*)(campos + 44);
                            }
                            D_800694A0 = compensacion;
                            D_800695E4 = D_8006951C;
                            func_8003ECD4(datos + desp_bancos, D_800694A0);
                            cursor += 0x30;
                        } else if (etiqueta == 0x44) {
                            func_80041264(cursor, campos, 0xC);
                            func_8003ECF8(campos);
                            cursor += 0xC;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x05:
                    /* Parametros de sonido: la etiqueta 6 lleva tres bytes. */
                    func_8003EB48();
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 6) {
                            func_80041264(cursor, campos, 3);
                            func_8003EC3C(campos);
                            cursor += 3;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x08:
                    es_jugador = 1;
                    /* sigue con las entidades de los tipos 7 y 10 */
                case 0x07:
                case 0x0A:
                    /* Entidad de escena: un nodo de 0x1F4 bytes con sus etiquetas (posicion, giro...). */
                    nodo = (u8*)AllocListNode((u8*)D_8006968C, 0x1F4, (s16)D_8006955C * 0x1F4);
                    if (nodo == NULL) {
                        for (;;) {
                        }
                    }
                    if (es_jugador != 0) {
                        D_80069504 = (Objeto*)AppendListNode((NodoLista*)D_80069504, (NodoLista*)nodo);
                    } else {
                        D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)nodo);
                    }
                    EN(u16, nodo, 0x108) = 0xA00;
                    EN(u8*, nodo, 0xC0) = nodo + 0xCC;
                    EN(u16, nodo, 0x26) = 0xFFFF;
                    es_jugador = 0;
                    if (*cursor == 0x2E) {
                        func_80041298((ContenedorCarga*)nodo);
                        break;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta < 0x0B || etiqueta >= 0x47) {
                            continue;
                        }
                        switch (etiqueta) {
                        case 0x0B:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 0x170) = *(u16*)campos;
                            EN(u16, nodo, 0x172) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x0C:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 0x174) = *(u16*)campos;
                            EN(u16, nodo, 0x176) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x0F:
                            func_80041264(cursor, campos, 2);
                            modelo = func_80036164(*(u16*)campos);
                            if (modelo == NULL) {
                                for (;;) {
                                }
                            }
                            aux = (u8*)AllocListNode((u8*)D_80069644, 0xC, D_8006967E * 0xC);
                            if (aux == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, aux, 8) = modelo;
                            EN(u8*, nodo, 0x74) = (u8*)AppendListNode((NodoLista*)EN(u8*, nodo, 0x74), (NodoLista*)aux);
                            cursor += 2;
                            break;
                        case 0x10:
                            func_80041264(cursor, campos, 0xC);
                            EN(s32, nodo, 0xE4) = *(s32*)campos;
                            EN(s32, nodo, 0xE8) = *(s32*)(campos + 4);
                            EN(s32, nodo, 0xEC) = *(s32*)(campos + 8);
                            EN(s32, nodo, 0x100) = *(s32*)(campos + 4);
                            cursor += 0xC;
                            break;
                        case 0x11:
                            func_80041264(cursor, campos, 6);
                            EN(u16, nodo, 0xDC) = *(u16*)campos;
                            EN(u16, nodo, 0xDE) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0xE0) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x12:
                            func_80041264(cursor, campos, 0xC);
                            EN(s32, nodo, 0xCC) = *(s32*)campos;
                            EN(s32, nodo, 0xD0) = *(s32*)(campos + 4);
                            EN(s32, nodo, 0xD4) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            break;
                        case 0x13:
                            func_80041264(cursor, campos, 1);
                            EN(u16, nodo, 0x2C) = campos[0];
                            if (campos[0] == 1) {
                                D_80069640 = (s32*)(nodo + 0xE4);
                                EN(u16, nodo, 0x3C) = 0x40;
                                D_80069560 = nodo;
                                D_80069698 = (Objeto*)nodo;
                                EN(u16, nodo, 0x3E) = 0x3FFF;
                            }
                            cursor += 1;
                            break;
                        case 0x15:
                            func_80041264(cursor, campos, 1);
                            EN(u16, nodo, 0x2A) = campos[0];
                            cursor += 1;
                            break;
                        case 0x16:
                            func_80041264(cursor, campos, 8);
                            EN(s32, nodo, 8) = *(s32*)campos;
                            EN(s32, nodo, 0xC) = *(s32*)(campos + 4);
                            if (EN(u8*, nodo, 0x74) != NULL
                                && (EN(u16, EN(u8*, EN(u8*, nodo, 0x74), 8), 0xA) & 0x180) != 0) {
                                EN(u32, nodo, 8) |= 0x200000;
                            }
                            cursor += 8;
                            break;
                        case 0x17:
                            func_80041264(cursor, campos, 0x24);
                            for (i = 0; i < 9; i++) {
                                EN(u32, nodo, 0x104 + i * 4) = ((u32*)campos)[i];
                            }
                            cursor += 0x24;
                            break;
                        case 0x18:
                            /* Solo se copian 4 bytes, pero se leen 16 del bufer: lo restante es lo que dejo la etiqueta anterior. */
                            func_80041264(cursor, campos, 4);
                            EN(u8*, nodo, 0x118) = nodo + 0x128;
                            EN(u8, nodo, 0x128) = campos[0];
                            EN(u8, nodo, 0x129) = campos[1];
                            EN(u16, nodo, 0x12A) = *(u16*)(campos + 4);
                            EN(u16, nodo, 0x12C) = *(u16*)(campos + 6);
                            aux = campos;
                            modelo = func_80036164(*(u32*)(aux + 8));
                            if (modelo == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, nodo, 0x130) = EN(u8*, modelo, 0x54);
                            modelo = func_80036164(*(u32*)(aux + 12));
                            if (modelo == NULL) {
                                for (;;) {
                                }
                            }
                            cursor += 0x10;
                            EN(s32, nodo, 4) = 2;
                            EN(u8*, nodo, 0x134) = EN(u8*, modelo, 0x54);
                            break;
                        case 0x19:
                            func_80041264(cursor, campos, 4);
                            cursor += 4;
                            break;
                        case 0x1A:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 0x100) = *(u16*)campos;
                            cursor += 4;
                            break;
                        case 0x1B:
                            func_80041264(cursor, campos, 6);
                            EN(u16, nodo, 0x48) = *(u16*)campos;
                            EN(u16, nodo, 0x4A) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x4C) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x1C:
                            func_80041264(cursor, campos, 8);
                            EN(u16, nodo, 0x50) = *(u16*)campos;
                            EN(u16, nodo, 0x52) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x54) = *(u16*)(campos + 4);
                            EN(u16, nodo, 0x2E) = *(u16*)(campos + 6);
                            EN(s32, nodo, 0x30) = (s16)EN(u16, nodo, 0x2E) * (s16)EN(u16, nodo, 0x2E);
                            cursor += 8;
                            break;
                        case 0x1D:
                            func_80041264(cursor, campos, 4);
                            if (EN(u16, nodo, 0x2C) == 0xE || EN(u16, nodo, 0x2C) == 0x1F) {
                                EN(u16, nodo, 0x196) = *(u16*)campos;
                            } else if (EN(u16, nodo, 0x2C) == 8) {
                                EN(u16, nodo, 0x160) = *(u16*)campos;
                            } else {
                                EN(u16, nodo, 0x17C) = *(u16*)campos;
                            }
                            cursor += 4;
                            break;
                        case 0x1E:
                            func_80041264(cursor, campos, 2);
                            EN(u16, nodo, 0x1E) = *(u16*)campos;
                            cursor += 2;
                            break;
                        case 0x1F:
                            func_80041264(cursor, campos, 1);
                            EN(u16, nodo, 0x26) = campos[0];
                            cursor += 1;
                            break;
                        case 0x27:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 0x1C) = *(u16*)campos;
                            cursor += 4;
                            break;
                        case 0x30:
                            /* Elemento de 0x20 bytes que se encadena al final de la lista +0xF8 del nodo. */
                            func_80041264(cursor, campos, 0x20);
                            aux = EN(u8*, nodo, 0xF8);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0xF8) = monton;
                            }
                            monton += 0x20;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos;
                            EN(u16, aux, 6) = *(u16*)(campos + 2);
                            EN(u16, aux, 8) = *(u16*)(campos + 4);
                            EN(u16, aux, 0xA) = *(u16*)(campos + 8);
                            EN(s32, aux, 0xC) = *(s32*)(campos + 0xC);
                            EN(s32, aux, 0x10) = *(s32*)(campos + 0x10);
                            EN(u16, aux, 0x14) = *(u16*)(campos + 0x14);
                            EN(u16, aux, 0x16) = *(u16*)(campos + 0x16);
                            EN(u16, aux, 0x18) = *(u16*)(campos + 0x18);
                            EN(u16, aux, 0x1A) = *(u16*)(campos + 0x1A);
                            EN(u16, aux, 0x1C) = *(u16*)(campos + 0x1C);
                            cursor += 0x20;
                            break;
                        case 0x31:
                            /* Elemento de 0x24 bytes al final de la lista +0xFC del nodo. */
                            func_80041264(cursor, campos, 0x20);
                            aux = EN(u8*, nodo, 0xFC);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0xFC) = monton;
                            }
                            monton += 0x24;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos;
                            EN(u16, aux, 6) = *(u16*)(campos + 2);
                            EN(s32, aux, 8) = *(s32*)(campos + 4);
                            EN(s32, aux, 0xC) = *(s32*)(campos + 8);
                            EN(u8, aux, 0x10) = campos[0xC];
                            EN(u8, aux, 0x13) = campos[0xF];
                            EN(u8, aux, 0x11) = campos[0xD];
                            EN(u8, aux, 0x12) = campos[0xE];
                            EN(u16, aux, 0x14) = *(u16*)(campos + 0x10);
                            EN(u16, aux, 0x16) = *(u16*)(campos + 0x12);
                            EN(s32, aux, 0x18) = *(s32*)(campos + 0x14);
                            EN(s32, aux, 0x1C) = *(s32*)(campos + 0x18);
                            EN(s32, aux, 0x20) = *(s32*)(campos + 0x1C);
                            cursor += 0x20;
                            break;
                        case 0x32:
                            /* Cinco referencias de 16 bits; el elemento (0x10 bytes) va a la lista +0xF4. */
                            func_80041264(cursor, campos, 0xC);
                            aux = EN(u8*, nodo, 0xF4);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)aux = 0;
                                EN(u8*, nodo, 0xF4) = aux;
                            }
                            monton += 0x10;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos;
                            for (i = 0; i < 5; i++) {
                                EN(u16, aux, 6 + i * 2) = *(u16*)(campos + 2 + i * 2);
                            }
                            cursor += 0xC;
                            break;
                        case 0x34:
                            /* Elemento de 0x1C bytes al final de la lista +0xF8 del nodo. */
                            func_80041264(cursor, campos, 0x18);
                            aux = EN(u8*, nodo, 0xF8);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0xF8) = monton;
                            }
                            monton += 0x1C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos;
                            EN(u16, aux, 6) = *(u16*)(campos + 2);
                            EN(u16, aux, 8) = *(u16*)(campos + 4);
                            EN(s32, aux, 0xC) = *(s32*)(campos + 8);
                            EN(s32, aux, 0x10) = *(s32*)(campos + 0xC);
                            EN(u16, aux, 0xA) = *(u16*)(campos + 0x10);
                            EN(u16, aux, 0x14) = *(u16*)(campos + 0x12);
                            EN(u16, aux, 0x16) = *(u16*)(campos + 0x14);
                            EN(u16, aux, 0x18) = *(u16*)(campos + 0x16);
                            cursor += 0x18;
                            break;
                        case 0x35:
                            /* Elemento de 0x2C bytes al final de la lista +0xFC del nodo. */
                            func_80041264(cursor, campos, 0x28);
                            aux = EN(u8*, nodo, 0xFC);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0xFC) = monton;
                            }
                            monton += 0x2C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos;
                            EN(u16, aux, 6) = *(u16*)(campos + 2);
                            EN(u16, aux, 8) = *(u16*)(campos + 4);
                            EN(u16, aux, 0xA) = *(u16*)(campos + 8);
                            EN(u16, aux, 0xC) = *(u16*)(campos + 6);
                            EN(u8, aux, 0xE) = campos[0xA];
                            EN(u8, aux, 0x11) = campos[0xD];
                            EN(u8, aux, 0xF) = campos[0xB];
                            EN(u8, aux, 0x10) = campos[0xC];
                            EN(u16, aux, 0x12) = *(u16*)(campos + 0xE);
                            EN(u16, aux, 0x14) = *(u16*)(campos + 0x10);
                            EN(s32, aux, 0x28) = *(s32*)(campos + 0x24);
                            EN(u16, aux, 0x16) = *(u16*)(campos + 0x12);
                            EN(u16, aux, 0x18) = *(u16*)(campos + 0x14);
                            EN(s32, aux, 0x1C) = *(s32*)(campos + 0x18);
                            EN(s32, aux, 0x20) = *(s32*)(campos + 0x1C);
                            EN(s32, aux, 0x24) = *(s32*)(campos + 0x20);
                            cursor += 0x28;
                            break;
                        case 0x38:
                            func_80041264(cursor, campos, 2);
                            EN(u16, nodo, 0x20) = *(u16*)campos;
                            EN(s32, nodo, 0x30) += (s16)*(u16*)campos * (s16)*(u16*)campos;
                            cursor += 2;
                            break;
                        case 0x39:
                            func_80041264(cursor, campos, 2);
                            EN(u16, nodo, 0x28) = *(u16*)campos + 0x10;
                            cursor += 2;
                            break;
                        case 0x3A:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 0x3C) = *(u16*)campos;
                            EN(u16, nodo, 0x3E) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x41:
                            /* Lista de enteros de 16 bits terminada en cero, copiada al monton. */
                            func_80041264(cursor, campos, 0x14);
                            EN(u8*, nodo, 0x178) = monton;
                            i = 0;
                            if (*(u16*)campos != 0) {
                                aux = campos;
                                do {
                                    *(u16*)(EN(u8*, nodo, 0x178) + i * 2) = *(u16*)aux;
                                    aux += 2;
                                    i++;
                                } while (*(u16*)aux != 0);
                            }
                            monton += ((i + 1) & 0xFFFE) * 2;
                            EN(u8, nodo, 0x14A) = i;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            cursor += 0x14;
                            break;
                        case 0x42:
                            func_80041264(cursor, campos, 6);
                            EN(u16, nodo, 0x50) = *(u16*)campos;
                            EN(u16, nodo, 0x52) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x54) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x46:
                            func_80041264(cursor, campos, 2);
                            EN(u16, nodo, 0x3A) = *(u16*)campos;
                            cursor += 2;
                            break;
                        default:
                            break;
                        }
                    } while (*cursor != 0x2E);
                    func_80041298((ContenedorCarga*)nodo);
                    break;

                case 0x09:
                    /* Volumen de escena (0x3C bytes): posicion, giro, tamano y lista de 0x24 bytes. */
                    nodo = (u8*)AllocListNode((u8*)D_80069528, 0x3C, D_800695C2 * 0x3C);
                    if (nodo == NULL) {
                        for (;;) {
                        }
                    }
                    D_80069580 = (struct NodoVolumen*)AppendListNode((NodoLista*)D_80069580, (NodoLista*)nodo);
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta < 0x10 || etiqueta >= 0x34) {
                            continue;
                        }
                        switch (etiqueta) {
                        case 0x10:
                            func_80041264(cursor, campos, 0xC);
                            EN(s32, nodo, 0x10) = *(s32*)campos;
                            EN(s32, nodo, 0x14) = *(s32*)(campos + 4);
                            EN(s32, nodo, 0x18) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            break;
                        case 0x11:
                            func_80041264(cursor, campos, 6);
                            EN(u16, nodo, 0x20) = *(u16*)campos;
                            EN(u16, nodo, 0x22) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x24) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x16:
                            func_80041264(cursor, campos, 8);
                            EN(s32, nodo, 8) = *(s32*)campos;
                            EN(s32, nodo, 0xC) = *(s32*)(campos + 4);
                            cursor += 8;
                            break;
                        case 0x1C:
                            func_80041264(cursor, campos, 8);
                            EN(u16, nodo, 0x28) = *(u16*)campos;
                            EN(u16, nodo, 0x2A) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x2C) = *(u16*)(campos + 4);
                            EN(u16, nodo, 0x36) = *(u16*)(campos + 6);
                            cursor += 8;
                            break;
                        case 0x1F:
                            func_80041264(cursor, campos, 1);
                            EN(u16, nodo, 0x34) = campos[0];
                            cursor += 1;
                            break;
                        case 0x33:
                            /* Elemento de 0x24 bytes al final de la lista +0x30 del volumen. */
                            func_80041264(cursor, campos, 0x20);
                            aux = EN(u8*, nodo, 0x30);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0x30) = monton;
                            }
                            monton += 0x24;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(s32, aux, 4) = *(s32*)campos;
                            EN(s32, aux, 8) = *(s32*)(campos + 4);
                            EN(u8, aux, 0xC) = campos[8];
                            EN(u8, aux, 0xF) = campos[0xB];
                            EN(u8, aux, 0xD) = campos[9];
                            EN(u8, aux, 0xE) = campos[0xA];
                            EN(u16, aux, 0x10) = *(u16*)(campos + 0xC);
                            EN(u16, aux, 0x12) = *(u16*)(campos + 0xE);
                            EN(s32, aux, 0x14) = *(s32*)(campos + 0x10);
                            EN(s32, aux, 0x18) = *(s32*)(campos + 0x14);
                            EN(s32, aux, 0x1C) = *(s32*)(campos + 0x18);
                            EN(s32, aux, 0x20) = *(s32*)(campos + 0x1C);
                            cursor += 0x20;
                            break;
                        default:
                            break;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x20:
                    /* Modelo jerarquico (0x58 bytes): posicion, giro y escala de cada nodo de la jerarquia. */
                    nodo = (u8*)AllocListNode((u8*)D_800695D4, 0x58, D_800694E6 * 0x58);
                    if (nodo == NULL) {
                        for (;;) {
                        }
                    }
                    D_80069648 = AppendListNode((NodoLista*)D_80069648, (NodoLista*)nodo);
                    EN(u16, nodo, 0x10) = 0;
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta < 0x10 || etiqueta >= 0x44) {
                            continue;
                        }
                        switch (etiqueta) {
                        case 0x10:
                            func_80041264(cursor, campos, 0xC);
                            aux = EN(u8*, EN(u8*, hijo_matriz, 4), 0x44);
                            EN(s32, aux, 0x18) = *(s32*)campos;
                            EN(s32, aux, 0x1C) = *(s32*)(campos + 4);
                            EN(s32, aux, 0x20) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            TransMatrix((MATRIX*)(EN(u8*, hijo_matriz, 4) + 4),
                                        (VECTOR*)(EN(u8*, EN(u8*, hijo_matriz, 4), 0x44) + 0x18));
                            D_8006B568[EN(s32, nodo, 0xC)] = (struct ModeloDibujo*)hijo;
                            D_80069648 = RemoveListNode((NodoLista*)D_80069648, (NodoLista*)nodo);
                            break;
                        case 0x11:
                            func_80041264(cursor, campos, 6);
                            hijo = (u8*)func_800363D4();
                            if (hijo == NULL) {
                                for (;;) {
                                }
                            }
                            hijo_matriz = hijo + 0xC;
                            EN(u16, hijo, 8) |= 2;
                            EN(s32, hijo_matriz, 0xC) = -1;
                            EN(s32, hijo, 0xC) = 0;
                            EN(u8*, hijo_matriz, 8) = EN(u8*, nodo, 0x54);
                            aux = EN(u8*, hijo_matriz, 4);
                            EN(s32, aux, 0x4C) = 0;
                            EN(s32, aux, 0x48) = 0;
                            EN(u16, EN(u8*, aux, 0x44), 0x10) = *(u16*)campos;
                            EN(u16, EN(u8*, aux, 0x44), 0x12) = *(u16*)(campos + 2);
                            EN(u16, EN(u8*, aux, 0x44), 0x14) = *(u16*)(campos + 4);
                            EN(s32, aux, 0) = 0;
                            cursor += 6;
                            RotMatrix((SVECTOR*)(EN(u8*, EN(u8*, hijo_matriz, 4), 0x44) + 0x10),
                                      (MATRIX*)(EN(u8*, hijo_matriz, 4) + 4));
                            break;
                        case 0x12:
                            func_80041264(cursor, campos, 0xC);
                            aux = EN(u8*, EN(u8*, hijo_matriz, 4), 0x44);
                            EN(s32, aux, 0) = *(s32*)campos;
                            EN(s32, aux, 4) = *(s32*)campos;
                            EN(s32, aux, 8) = *(s32*)campos;
                            cursor += 0xC;
                            ScaleMatrix((MATRIX*)(EN(u8*, hijo_matriz, 4) + 4),
                                        (VECTOR*)EN(u8*, EN(u8*, hijo_matriz, 4), 0x44));
                            break;
                        case 0x21:
                            func_80041264(cursor, campos, 4);
                            cursor += 4;
                            EN(u16, nodo, 0x4E) = 0;
                            EN(s32, nodo, 0xC) = *(u16*)campos;
                            break;
                        case 0x24:
                            func_80041264(cursor, campos, 8);
                            posicion = *(s32*)campos;
                            EN(u16, nodo, 0xA) = 2;
                            aux = datos + posicion + 4;
                            D_800694A0 = *(s32*)(campos + 4);
                            EN(u8*, nodo, 0x54) = aux;
                            GsMapModelingData((unsigned long*)aux);
                            cursor += 8;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        case 0x39:
                            func_80041264(cursor, campos, 2);
                            EN(u16, hijo, 0xB6) = *(u16*)campos;
                            cursor += 2;
                            break;
                        case 0x43:
                            func_80041264(cursor, campos, 1);
                            EN(u8, hijo, 0xB5) = campos[0];
                            cursor += 1;
                            break;
                        default:
                            break;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x22:
                    /* Recurso (0x58 bytes): modelo, textura, animacion o color segun la etiqueta. */
                    nodo = (u8*)AllocListNode((u8*)D_800695D4, 0x58, D_800694E6 * 0x58);
                    if (nodo == NULL) {
                        for (;;) {
                        }
                    }
                    D_80069648 = AppendListNode((NodoLista*)D_80069648, (NodoLista*)nodo);
                    EN(u16, nodo, 0x10) = 0;
                    EN(u16, nodo, 0x12) = 0;
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta < 0x0D || etiqueta >= 0x41) {
                            continue;
                        }
                        switch (etiqueta) {
                        case 0x0D:
                            func_80041264(cursor, campos, 0xC);
                            i = EN(u16, nodo, 0x12);
                            EN(u16, nodo + i * 14, 0x24) = *(u16*)campos;
                            EN(u16, nodo + i * 14, 0x26) = *(u16*)(campos + 2);
                            EN(u16, nodo + i * 14, 0x28) = *(u16*)(campos + 4);
                            EN(u8, nodo + i * 14, 0x2D) = campos[9];
                            EN(u8, nodo + i * 14, 0x2A) = campos[6];
                            EN(u16, nodo + i * 14, 0x2E) = campos[10];
                            EN(u16, nodo + i * 14, 0x30) = campos[11];
                            EN(u8, nodo + i * 14, 0x2B) = campos[7];
                            EN(u8, nodo + i * 14, 0x2C) = campos[8];
                            cursor += 0xC;
                            EN(u16, nodo, 0x12) = EN(u16, nodo, 0x12) + 1;
                            break;
                        case 0x24:
                            func_80041264(cursor, campos, 8);
                            cursor += 8;
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            aux = datos + posicion + 4;
                            EN(u8*, nodo, 0x54) = aux;
                            GsMapModelingData((unsigned long*)aux);
                            EN(u16, nodo, 0xA) = 2;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        case 0x25:
                            func_80041264(cursor, campos, 8);
                            aux = (u8*)AllocListNode((u8*)D_80069570, 0x14, D_80069670 * 0x14);
                            if (aux == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, nodo, 0x54) = aux;
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            EN(u8*, aux, 8) = datos + posicion;
                            EN(u16, nodo, 0xA) = 4;
                            modelo = EN(u8*, aux, 8);
                            EN(u8*, aux, 8) = modelo + 4;
                            EN(u16, aux, 0x12) = EN(u16, modelo, 2) >> 1;
                            EN(u8*, aux, 8) = modelo + 8;
                            EN(u16, aux, 0xE) = EN(u16, modelo, 4);
                            cursor += 8;
                            EN(u16, aux, 0x10) = EN(u16, modelo + 8, 4);
                            break;
                        case 0x26:
                            func_80041264(cursor, campos, 4);
                            EN(u16, nodo, 8) = *(u16*)campos;
                            cursor += 4;
                            break;
                        case 0x27:
                            func_80041264(cursor, campos, 4);
                            EN(s32, nodo, 0xC) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x4E) = *(u16*)campos;
                            cursor += 4;
                            break;
                        case 0x28:
                            func_80041264(cursor, campos, 3);
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x14) = campos[0];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x15) = campos[1];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x16) = campos[2];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x17) = 0;
                            cursor += 3;
                            EN(u16, nodo, 0x10) = EN(u16, nodo, 0x10) + 1;
                            break;
                        case 0x3F:
                            func_80041264(cursor, campos, 0xC);
                            posicion = *(s32*)(campos + 4);
                            compensacion = *(s32*)(campos + 8);
                            EN(u16, nodo, 0xA) = 1;
                            EN(u8*, nodo, 0x54) = datos + posicion;
                            EN(u16, nodo, 0x50) = *(u16*)campos;
                            cursor += 0xC;
                            D_800694A0 = compensacion;
                            break;
                        case 0x40:
                            func_80041264(cursor, campos, 8);
                            cursor += 8;
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            aux = datos + posicion + 4;
                            EN(u8*, nodo, 0x54) = aux;
                            GsMapModelingData((unsigned long*)aux);
                            EN(u16, nodo, 0xA) = 0x100;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        default:
                            break;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x29:
                    /* Imagenes (.-)*): cada etiqueta 0x2A lleva el offset de un TIM que se sube a la VRAM. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x2A) {
                            func_80041264(cursor, campos, 8);
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            GsGetTimInfo((unsigned long*)(datos + posicion + 4), &imagen);
                            rect.x = imagen.px;
                            rect.y = imagen.py;
                            rect.w = imagen.pw;
                            rect.h = imagen.ph;
                            LoadImage(&rect, imagen.pixel);
                            DrawSync(0);
                            if ((imagen.pmode >> 3) & 1) {
                                rect.x = imagen.cx;
                                rect.y = imagen.cy;
                                rect.w = imagen.cw;
                                rect.h = imagen.ch;
                                func_80040D98(&rect, (s16*)imagen.clut);
                                LoadImage(&rect, imagen.clut);
                                DrawSync(0);
                            }
                            cursor += 8;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x36:
                    /* Zonas de colision del nivel: la etiqueta 0x37 da su posicion en la seccion. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x37) {
                            func_80041264(cursor, campos, 8);
                            cursor += 8;
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            D_800694FC = datos + posicion;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x47:
                    /* Demostracion: la etiqueta 0x48 da el flujo de botones grabado. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x48) {
                            func_80041264(cursor, campos, 8);
                            cursor += 8;
                            posicion = *(s32*)campos;
                            D_800694A0 = *(s32*)(campos + 4);
                            D_8001004F = 1;
                            D_800695B0 = (u16*)(datos + posicion);
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x3B:
                    /* Camara y reparto de memoria: 0x3E fija el tamano de cada grupo y habilita la orden 0x2C. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x3C) {
                            func_80041264(cursor, campos, 4);
                            D_800695B4 = campos[2];
                            D_8006960C = *(s16*)campos;
                            D_80069530 = campos[3];
                            cursor += 4;
                        } else if (etiqueta == 0x2B) {
                            func_80041264(cursor, campos, 0xC);
                            D_8006D928.vpx = *(s32*)campos;
                            D_8006D928.vpy = *(s32*)(campos + 4);
                            D_8006D928.vpz = *(s32*)(campos + 8);
                            cursor += 0xC;
                        } else if (etiqueta == 0x3D) {
                            func_80041264(cursor, campos, 6);
                            D_800694B0 = *(s16*)campos / 4;
                            D_800695F2 = *(s16*)(campos + 2) / 4;
                            D_800695F4 = *(s16*)(campos + 4) / 4;
                            cursor += 6;
                            D_8006969C = D_800694B0 - 0x80;
                        } else if (etiqueta == 0x3E) {
                            func_80041264(cursor, campos, 0x1C);
                            pools_listos = 1;
                            D_80069660 = *(u16*)(campos + 2);
                            D_80069670 = *(u16*)campos;
                            D_8006955C = *(u16*)(campos + 6);
                            D_800694E6 = *(u16*)(campos + 4);
                            D_8006967E = *(u16*)(campos + 8);
                            D_800695C2 = *(u16*)(campos + 10);
                            D_80069548 = *(s32*)(campos + 12);
                            D_8006952E = *(u16*)(campos + 0x14);
                            D_8006954C = *(s32*)(campos + 0x10) & ~7;
                            D_80069678 = *(s32*)(campos + 0x18);
                            if (D_8006952E < 0x12C) {
                                D_8006952E = 0x12C;
                            }
                            cursor += 0x1C;
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x49:
                    /* Textos (.-IJ): una pareja (offset, tamano) por idioma; se guarda la del idioma activo. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x4A) {
                            func_80041264(cursor, campos, 0x30);
                            if (D_80010050 == 0) {
                                posicion = *(s32*)campos;
                                tam_extra = *(u32*)(campos + 4);
                                datos_extra = datos + posicion;
                            } else if (D_80010050 == 1) {
                                datos_extra = datos + *(s32*)(campos + 8);
                                tam_extra = *(u32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                datos_extra = datos + *(s32*)(campos + 16);
                                tam_extra = *(u32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                datos_extra = datos + *(s32*)(campos + 24);
                                tam_extra = *(u32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                datos_extra = datos + *(s32*)(campos + 32);
                                tam_extra = *(u32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                datos_extra = datos + *(s32*)(campos + 40);
                                tam_extra = *(u32*)(campos + 44);
                            }
                            cursor += 0x30;
                        }
                    } while (*cursor != 0x2E);
                    break;

                default:
                    break;
                }
            } while (*cursor != 0x2E);
        fin_chunks:
            cursor++;
        } else if (orden == 0x2C) {
            /*
             * Reparte la memoria de trabajo: tres listas de ordenacion por buffer, los grupos de
             * entidades, modelos, volumenes y recursos, el monton y la zona de textos; despues
             * inicializa los grupos, busca la posicion de los datos de cada seccion en el
             * contenedor y lanza la lectura del resto.
             */
            if (pools_listos != 1) {
                for (;;) {
                }
            }
            if (banco_cargado == 0) {
                D_8006959C = (u32)reserva;
                reserva += D_8006954C;
            }
            for (i = 0; i < 3; i++) {
                D_8006AE20[i].length = 9;
                D_8006AE20[i].org = (GsOT_TAG*)reserva;
                reserva += tamanos[9];
                D_8006AE60[i].length = 8;
                D_8006AE60[i].org = (GsOT_TAG*)reserva;
                reserva += tamanos[8];
                D_8006AEA0[i].length = 9;
                D_8006AEA0[i].org = (GsOT_TAG*)reserva;
                reserva += tamanos[9];
            }
            D_8006968C = reserva;
            reserva += (s16)D_8006955C * 0x1F4;
            D_80069570 = reserva;
            reserva += D_80069670 * 0x14;
            D_8006964C = reserva;
            reserva += (s16)D_80069660 * 0xB8;
            D_800695D4 = reserva;
            reserva += (s16)D_800694E6 * 0x58;
            D_80069644 = reserva;
            reserva += D_8006967E * 0xC;
            D_80069528 = reserva;
            reserva += D_800695C2 * 0x3C;
            monton = reserva;
            D_80069538 = monton;
            reserva = monton + D_80069548;
            D_800694B8 = reserva;
            reserva += (s16)D_8006952E * 8;
            D_80076188 = D_8006959C;
            D_80069680 = D_8006959C;
            D_8006958C = D_8006959C - 0x400 + D_8006954C;
            D_80069610 = D_8006958C;
            D_80069614 = D_8006958C;
            if (D_80069678 != 0) {
                D_80069520 = reserva;
                reserva += D_80069678;
            } else {
                D_80069520 = NULL;
            }
            if (datos_extra != NULL && tam_extra != 0) {
                func_8004153C(datos_extra, tam_extra, reserva);
                D_80069590 = (u16*)reserva;
                datos_extra = NULL;
                reserva += tam_extra;
            }
            InitListPool(D_8006968C, 0x1F4, (s16)D_8006955C * 0x1F4);
            InitListPool((u8*)D_8006964C, 0xB8, (s16)D_80069660 * 0xB8);
            InitListPool(D_80069570, 0x14, D_80069670 * 0x14);
            InitListPool((u8*)D_800695D4, 0x58, (s16)D_800694E6 * 0x58);
            InitListPool(D_80069644, 0xC, D_8006967E * 0xC);
            InitListPool(D_80069528, 0x3C, D_800695C2 * 0x3C);
            memset(D_80069538, 0, D_80069548);
            compensacion = func_80040F78(secciones, n_secciones, 4);
            datos = reserva;
            if (audio_cargado == 1) {
                audio_cargado = 2;
                D_8006966C = datos + tam_audio;
                D_80069550 = datos + tam_audio;
                D_800695AC = (s16*)(datos + tam_audio + 8);
            }
            func_8003652C();
            func_800365D0();
            D_80069484 = 0;
            D_80069498 = (u32)datos;
            D_8006948C = D_80069490;
            D_8006949C = D_80069490;
            func_800411F0((CdlLOC*)D_8006A928);
            if (D_80069494 != 0) {
                if (func_80044664((u8*)D_8006949C, (u8*)D_80069498, (void*)0x1F800000) == 0) {
                    return 1;
                }
            } else {
                while (D_8006955E != 0) {
                }
            }
        } else if (orden == 0x4B) {
            /* Banco del idioma activo: busca su posicion en la cabecera y lee sus secciones. */
            banco_cargado = 1;
            D_8006959C = (u32)reserva;
            reserva += D_8006954C;
            if (datos_extra != NULL && tam_extra != 0) {
                func_8004153C(datos_extra, tam_extra, reserva);
                D_80069590 = (u16*)reserva;
                datos_extra = NULL;
                reserva += tam_extra;
            }
            datos = reserva;
            if (D_80010050 == 0) {
                compensacion = func_80040F78(secciones, n_secciones, 6);
            } else if (D_80010050 == 1) {
                compensacion = func_80040F78(secciones, n_secciones, 5);
            } else if (D_80010050 == 2) {
                compensacion = func_80040F78(secciones, n_secciones, 7);
            } else if (D_80010050 == 3) {
                compensacion = func_80040F78(secciones, n_secciones, 8);
            } else if (D_80010050 == 4) {
                compensacion = func_80040F78(secciones, n_secciones, 9);
            } else if (D_80010050 == 5) {
                compensacion = func_80040F78(secciones, n_secciones, 0xA);
            }
            D_80069484 = 0;
            D_80069498 = (u32)datos;
            D_8006948C = D_80069490;
            D_8006949C = D_80069490;
            D_800694AC = CdPosToInt((CdlLOC*)D_8006A928) + ((u32)compensacion >> 11);
            CdIntToPos(D_800694AC, (CdlLOC*)D_8006A928);
            func_800411F0((CdlLOC*)D_8006A928);
            if (D_80069494 != 0) {
                if (func_80044664((u8*)D_8006949C, (u8*)D_80069498, (void*)0x1F800000) == 0) {
                    return 1;
                }
            } else {
                while (D_8006955E != 0) {
                }
            }
            D_80069488 += compensacion + D_80069478;
            D_800694AC = CdPosToInt((CdlLOC*)D_8006A928);
            D_800694AC = D_800694AC + D_80069478 / 2048;
            CdIntToPos(D_800694AC, (CdlLOC*)D_8006A928);
        }
    }

    if (audio_cargado != 0) {
        D_8006966C += *(s32*)D_8006966C;
        D_80069550 += *(s32*)(D_80069550 + 4);
    }
    if ((D_800694A8 & 4) == 0) {
        SetDispMask(0);
        func_800443CC();
        SetDispMask(1);
    }
    D_800694A8 = 0;
    D_8006955E = 0;
    D_80069658 = 0;
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", func_800415A0);
#endif
