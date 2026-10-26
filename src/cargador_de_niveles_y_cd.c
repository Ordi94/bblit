#include "common.h"
#include "cargador.h"
#include "psyq/TYPES.H"
#include "psyq/LIBCD.H"

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

/* Estado de la lectura en curso (zona 0x80069478..0x800694AC, accesos $gp + 0x158..0x18C). */
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
u8 D_800694A8;
s32 D_800694AC;

extern EntradaSector D_8005EE78[];
extern RegistroArchivo D_8005F200[];
extern u8 D_80069540;
extern vu8 D_8006955E;
extern u8 D_8006933C[];
extern u8 D_8006A928[];

extern void func_80040E30(void);

typedef struct NodoA {
    struct NodoA* sig;
    u16 id;
    u16 ref[5];
} NodoA;

typedef struct NodoB {
    struct NodoB* sig;
    u16 id;
    u8 pad6[4];
    u16 refC;
    u8 padC[0x12];
    s16 desplazamiento;
} NodoB;

typedef struct NodoC {
    struct NodoC* sig;
    u16 id;
    u16 refA;
    u8 pad8[0x10];
    u32 banderas;
    u32 refA1;
    u32 refA2;
} NodoC;

typedef struct RefA {
    u8 pad0[6];
    u16 v;
} RefA;

typedef struct ContenedorCarga {
    u8 pad0[0x2C];
    u16 clase;
    u8 pad2E[0xF4 - 0x2E];
    NodoA* listaA;
    NodoB* listaB;
    NodoC* listaC;
} ContenedorCarga;


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

/*
 * Recorre la cabecera de secciones de un contenedor (n entradas de tipo, tamano y tamano alineado)
 * y calcula la posicion, en bytes desde el inicio del archivo, de los datos del banco que se pide:
 * devuelve la suma de los tamanos alineados de las secciones que hay entre la primera de tipo 6
 * y la de tipo `tipo`. Como efectos laterales deja el tamano alineado de la seccion `tipo` en
 * D_800694A0 y en D_80069478 la suma de las secciones siguientes hasta la de tipo 4.
 */
/* Pendiente: puntuacion 390 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones
   que el original; solo difiere el reparto de registros de la ultima etapa (el original deja el
   puntero del bucle en a2 y la constante 4 en a3, el indice en t0 en todas las etapas). Variantes
   probadas: 9 (orden de declaracion, puntero propio por etapa, bucles rotados, parametro de relleno). */
#ifdef NON_MATCHING
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
    CdReadyCallback(func_8004109C);
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

/*
 * Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en
 * desplazamientos dentro de cada lista, para que el codigo que las usa no tenga que buscar:
 * las cinco referencias de cada nodo de la lista A apuntan a la lista B (desplazamiento en
 * bytes, multiplo de 0x20), la de cada nodo de B apunta a la lista C (indice por 0x24), y la de
 * cada nodo de C apunta a A (desplazamiento multiplo de 0x10, y los dos campos extra, que solo
 * existen con la bandera 0x20, como indice por 0x10). Un identificador sin nodo se deja intacto.
 * Solo actua sobre las clases 2, 0xE y 0x22. Los nodos empiezan con el enlace al siguiente (+0)
 * y el identificador de 16 bits (+4).
 */
/* Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones
   y mismo flujo que el original; difiere el reparto de registros (el original deja el puntero de
   la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el
   original rellena. Variantes probadas: 14 (indice o puntero en el bucle de cinco, tipo del
   contador, temporales para el reparto, orden de declaracion). */
#ifdef NON_MATCHING
void func_80041298(ContenedorCarga* c)
{
    NodoA* a;
    NodoB* b;
    NodoC* k;
    NodoA* na;
    NodoB* nb;
    RefA* r;
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

INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", func_800415A0);
