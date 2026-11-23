#include "common.h"
#include "cargador.h"
#include "psyq/TYPES.H"
#include "psyq/LIBCD.H"
#include "globales.h"
#include "objetos.h"
#include "arranque.h"

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
 * y la posicion de CD (minuto, segundo, cuadro) que CargarContenedor usa para iniciar la lectura.
 *
 * D_80069540 se declara como escalar de un byte: con el umbral de datos pequenos el compilador
 * emite su direccion como simbolo (lui y addiu juntos, dentro del bucle de espera) y no la iza
 * fuera del bucle como haria con un arreglo; el original la calcula dentro del bucle.
 * Cada entrada se lee a locales antes de escribir el registro, que es el orden de las cargas.
 */
void ConstruirRegistrosArchivo(void)
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
 *
 * Los tres ultimos recorridos se escriben con el indice (`secciones[i]`) y no con un puntero que
 * avanza: asi el compilador deriva el puntero del bucle como una variable de induccion propia, con
 * la copia que tiene el original, y el reparto de registros coincide.
 */
s32 func_80040F78(EntradaSeccion* secciones, s32 n, s32 tipo)
{
    s32 i;
    s32 anterior;

    anterior = 0;
    D_80069478 = 0;
    i = 0;
    while (i < n) {
        if (secciones[i].tipo == tipo) {
            break;
        }
        i++;
    }
    D_800694A0 = secciones[i].alineado;
    for (i = 0; i < n; i++) {
        if (secciones[i].tipo == 6) {
            break;
        }
    }
    while (secciones[i].tipo != tipo) {
        if (i >= n) {
            break;
        }
        anterior += secciones[i].alineado;
        i++;
    }
    i++;
    while (secciones[i].tipo != 4) {
        if (i >= n) {
            break;
        }
        D_80069478 += secciones[i].alineado;
        i++;
    }
    return anterior;
}

/*
 * Retorno de llamada de la unidad (CdReadyCallback): cuando hay un sector listo (aviso 1) lo
 * copia con CdGetSector (0x200 palabras) y avanza los contadores. Con lectura comprimida
 * (D_80069494 distinto de cero) copia a un anillo entre D_80069490 y D_8006947C; si no, copia
 * linealmente a D_80069498. Al completar los bytes pedidos (D_800694A0) apaga la espera, pausa
 * la unidad y deja en D_800694AC y en la posicion D_8006A928 el sector siguiente al ultimo leido.
 */
void CallbackSectorListo(u8 aviso)
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

/* Inicia la lectura continua de sectores desde la posicion dada; CallbackSectorListo los recoge. */
void IniciarLecturaContinua(CdlLOC* posicion)
{
    D_8006955E = 1;
    CdReadyCallback((CdlCB)CallbackSectorListo);
    CdControl(6, (u8*)posicion, 0);
}

/*
 * Suma de control de una cabecera: suma de los bytes con signo (lb), como la que se guarda en
 * el offset 0x7FC de la cabecera de un contenedor y en la partida.
 */
s32 SumaControl(s8* datos, s32 n)
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
void CopiarBytes(u8* origen, u8* destino, s16 n)
{
    s32 i;

    for (i = 0; i < n; i++) {
        *destino++ = *origen++;
    }
}

/*
 * Reparto de registros: el original usa tres variables de recorrido, una por lista (A, B y C), y cada
 * una hace de recorrido exterior en un bucle y de busqueda en otro (la lista A es el recorrido del
 * primer bucle y la busqueda del tercero; la B, la busqueda del primero y el recorrido del segundo; la
 * C, la busqueda del segundo y el recorrido del tercero). Una variable por lista acumula las
 * referencias de sus dos usos y `global-alloc` le da prioridad antes que al puntero a los campos
 * (v1 para A, a1 para B y a2 para C, con el identificador en a3). Con una variable de busqueda
 * propia en cada bucle el reparto no coincide. El cociente de cada division por el tamano del nodo
 * es una local de bloque: con una sola local compartida, `global-alloc` la trata como un pseudo de
 * vida larga y el cociente y el producto quedan en los registros contrarios a los del original.
 *
 * El identificador se lee del campo dos veces: una en la prueba de la guarda y otra al guardarlo en
 * la variable. El original carga el campo en v0, lo compara y despues lo copia con `move a3,v0` en
 * el hueco del salto de la busqueda; con una sola lectura copiada a la variable antes de la prueba
 * la carga cae directa en el registro del identificador y no hay copia. El identificador es una
 * variable de 32 bits aunque los campos que lee sean de 16: con 16 bits aparece una conversion que
 * el original no tiene. En los dos campos extra del nodo de C el original carga el valor en a3
 * antes de la guarda de la lista A, y aqui tambien.
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
void ResolverReferenciasContenedor(ContenedorCarga* c)
{
    NodoA* a;
    NodoB* b;
    NodoC* k;
    /* De 32 bits aunque los campos que lee sean de 16 (ver la cabecera). */
    s32 id;
    u32 i;
    u32 desp;

    if (c->clase == 0xE || c->clase == 2 || c->clase == 0x22) {
        for (a = c->listaA; a != NULL; a = a->sig) {
            for (i = 0; i < 5; i++) {
                if (a->ref[i] == 0xFFF0) {
                    break;
                }
                id = a->ref[i];
                for (b = c->listaB; b != NULL; b = b->sig) {
                    if (b->id == id) {
                        break;
                    }
                }
                if (b != NULL) {
                    desp = ((u8*)b - (u8*)c->listaB) & 0xFFE0;
                    a->ref[i] = desp;
                }
            }
        }
        for (b = c->listaB; b != NULL; b = b->sig) {
            if (b->refC != 0) {
                id = b->refC;
                for (k = c->listaC; k != NULL; k = k->sig) {
                    if (k->id == id) {
                        break;
                    }
                }
                if (k != NULL) {
                    s32 indice;
                    indice = k - c->listaC;
                    b->desplazamiento = indice * 0x24;
                }
            }
        }
        for (k = c->listaC; k != NULL; k = k->sig) {
            if (k->refA != 0) {
                id = k->refA;
                for (a = c->listaA; a != NULL; a = a->sig) {
                    if (a->id == id) {
                        break;
                    }
                }
                if (a != NULL) {
                    desp = ((u8*)a - (u8*)c->listaA) & 0xFFF0;
                    k->refA = desp;
                }
            }
            if (k->banderas & 0x20) {
                id = k->refA1;
                for (a = c->listaA; a != NULL; a = a->sig) {
                    if (a->id == id) {
                        break;
                    }
                }
                if (a != NULL) {
                    s32 indice;
                    indice = a - c->listaA;
                    k->refA1 = indice * 0x10;
                }
                id = k->refA2;
                for (a = c->listaA; a != NULL; a = a->sig) {
                    if (a->id == id) {
                        break;
                    }
                }
                if (a != NULL) {
                    s32 indice;
                    indice = a - c->listaA;
                    k->refA2 = indice * 0x10;
                }
            }
        }
    }
}

void CopiarBytesSolapados(u8* origen, u32 n, u8* destino)
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

/*
 * Vista del bufer de etiquetas por arreglos de cada ancho: un elemento de arreglo de una union es un
 * acceso a miembro, y el compilador no lo da por afectado por los almacenes a variables globales
 * escalares que lo rodean (no relee ni retrasa las cargas).
 */
typedef union {
    u8 b[0x80];
    u16 h[0x40];
    s16 hs[0x40];
    s32 w[0x20];
} Etiquetas;

#define ETQ(ancho, base, i) (((Etiquetas*)(base))->ancho[i])

/*
 * Primeras etiquetas del chunk 0x3E (tamano de las listas de la escena). Se leen por nombre de
 * miembro y no por puntero con desplazamiento.
 */
typedef struct {
    u16 w00;
    u16 w02;
    u16 w04;
    u16 w06;
    u16 w08;
    u16 w0A;
    s32 d0C;
    s32 d10;
    u16 w14;
    u16 w16;
    s32 d18;
} EtiquetasListas;

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 4993 con la configuracion versionada (g = 8 del archivo; ejes 288 de
 * operandos, 5 de lineas reordenadas y 542 de lineas insertadas o borradas). La cifra incluye
 * palabras con direcciones absolutas dentro del archivo (saltos y tablas de saltos), de modo que
 * depende del tamano de las funciones anteriores y de cuantas instrucciones separan cada cuerpo de
 * caso del de su tabla. Medido: el codigo generado tiene 2951 instrucciones y el original 2955; la
 * diferencia son cuatro copias de registro (`move`) que el original conserva y el C no emite
 * (0x80041CDC, 0x80042F20, 0x80042F78 y 0x8004367C). La llamada a `func_80044664` de la
 * apertura del anillo (de 0x80041A04 a 0x80041A18) la comparte la lectura de las listas, que salta
 * hacia ella desde 0x800420C8, como en el original (ver mas abajo). Los cuerpos de los casos de los cinco `switch` y del
 * despacho de primer nivel van en el orden de direcciones de las tablas de saltos del original: el
 * orden del fuente decide el orden de emision, por eso los casos no van en orden numerico.
 *
 * Reparto de registros de las zonas: un par `libre--; libre++;` al abrir el caso 0x2C llego a darle
 * a `libre` las referencias que le faltaban para tomar s6; con la copia `monton = libre` escrita
 * como el original (ver abajo) el par ya no cambia la cifra y no se escribe. El
 * nodo de los chunks de recursos y modelos (pseudo 95, R 340, L 528, 5,152) supera al cursor del
 * script (pseudo 91, R 1074, L 2087, 5,146) sin ninguna referencia anadida (el cursor ya no se
 * reasigna desde `datos` al abrir el script), de modo que tampoco hace falta un par `nodo--;
 * nodo++;`.
 *
 * Variable compartida del desplazamiento: en el original el registro s7 lo ocupa un solo valor que
 * recibe, en vez de una variable por uso, el desplazamiento de los chunks (`lw s7,0x128($sp)` y
 * `lw s7,4($s4)`), el del banco de idioma (`lw s7,8($s4)` ... `lw s7,0x28($s4)`) y el resultado de
 * `func_80040F78` (`addu s7,v0,zero` en 0x80042030 y 0x800421F0); el desplazamiento de texturas y
 * el tamano de audio van en la pila (sw a 0x1DC y lw a 0x1D8) y la compensacion del chunk 0x3F en
 * un temporal. Por eso `desp_campo` hace de las tres variables. Con una variable por uso ese valor
 * no cruza llamadas, `global-alloc` le da un temporal (v1) y cada uso carga y suma por separado;
 * compartida cruza llamadas y toma un registro guardado.
 *
 * Variables de la pila: el orden de declaracion decide el orden de las ranuras de derrame (la
 * primera declarada queda en la direccion mas baja): `hijo`, `hijo_matriz`, `n_secciones`,
 * `es_jugador`, `pools_listos`, `banco_cargado`, `audio_cargado`, `tam_audio`, `desp_texturas`,
 * `tam_extra` y `datos_extra` van declaradas en el orden de las ranuras del original (0x1A8,
 * 0x1AC, 0x1B0, 0x1B8, 0x1C0, 0x1C8, 0x1D0, 0x1D8, 0x1DC, 0x1E0 y 0x1E4).
 *
 * Casos de lista (0x30 a 0x35): el original copia `campos` a un registro guardado (s0) en el hueco
 * de retardo de la prueba de la cabeza (`move s0,s4` en 0x80041F70 y los casos vecinos), lee los
 * campos por esa copia, carga la cabeza de la lista en un temporal y la copia al recorrido (`move
 * a0,v0`), que vive en un temporal. La copia es `aux`, la misma variable que en otros casos recibe
 * `campos` y se usa tras una llamada (casos 0x11 y los de dos llamadas): al cruzar llamadas toma el
 * primer registro guardado (pseudo 99, R 312, L 289, prioridad 8,64, s0); una variable propia de
 * los casos de lista, de vida corta y sin llamadas, toma otro registro guardado y desplaza a los
 * demas pseudos. La copia se hace antes de la prueba de la cabeza: el CSE
 * solo la conserva si queda fuera del bloque de las lecturas, que ocurren tras la union de las dos
 * ramas. `cabeza` guarda la cabeza leida y `elemento` es el recorrido, una local de cada caso para
 * que no cruce llamadas.
 *
 * Formas del original antes de los chunks (direcciones del original): la lectura de la seccion de
 * cada etiqueta 0x45 es `secciones[posicion++]` en la propia expresion (`addu v1,sp,s3` y `addiu
 * s3,s3,0xc` consecutivos en 0x80041BA8; con el incremento en otra sentencia el planificador separa
 * la direccion del elemento y el bloque no coincide); el bucle del anillo, el de lectura directa y el
 * despacho de chunks usan cada uno su propio puntero al bufer de etiquetas (el del anillo en s3,
 * `addiu s3,sp,0x128` en 0x80041960; los otros dos en s4, 0x80041B7C y 0x800422F4), por eso `campos` se
 * asigna al abrir cada fase y `bufer_anillo` es otro pseudo; la comprobacion `pools_listos != 1` salta
 * con una sola prueba (`bne t4,t1` en 0x80041CCC) al bucle infinito que queda tras `func_800365D0`
 * (0x80042088), escrito con una etiqueta; el chunk 0x41 copia con `dst[i] = src[i]` (dos
 * inducciones, a0 y a1, en 0x8004390C) y no con un puntero que avanza; las dos escrituras de `tamano`
 * van encadenadas (`D_800694A0 = D_800694A4 = x`: una sola carga en 0x800417EC); y la suma de las
 * alineaciones se agrupa como `a + (b + 0x800)` (`addu` en 0x80041914).
 *
 * Relecturas del original: tras un almacen a un miembro de un nodo el original vuelve a leer el campo
 * de las etiquetas (no lo reutiliza). En el chunk 0x1C el cuadrado se calcula con una segunda
 * lectura de `campos + 6`; en el 0x12 de modelos las tres lecturas del primer entero (`lw v0,0x128(sp)`,
 * 0x80042930, 0x80042948 y 0x80042960) se repiten y van por `ETQ(w, campos_mem, 0)` (con `*(s32*)campos_mem` el
 * compilador las reune en una sola carga), y en el
 * 0x13 el valor se guarda en una variable de 32 bits (`modo`; con 8 bits el compilador anade un
 * `andi 0xff` que el original no tiene) para compararlo sin releerlo tras el almacen. Los casos que
 * en el original usan un temporal y en el C tomaban el registro guardado de `aux` llevan un puntero
 * propio que no cruza llamadas (`modelo_gs` en el 0x24 de modelos, `enlace` en el 0x0F, `sonido` en
 * el 0x4C).
 *
 * Orden de las sentencias: el planificador emite las cargas en el orden del fuente y puede cruzar
 * los almacenes entre si; el orden de las cargas del original decide el del fuente (en el chunk que
 * lee los bytes 2 y 3 y el entero con signo de la base, `campos[2]`, `campos[3]` y despues el entero;
 * en el 0x24 de modelos las dos lecturas antes de la escritura del modo).
 *
 * Lectura de etiquetas por miembro: en los chunks 0x02, 0x3D y 0x3E el original lee los campos del
 * bufer sin releerlos tras un almacen a un global y agrupa las cargas antes de los almacenes; con un
 * puntero y un desplazamiento el compilador las intercala y relee. `Etiquetas` (union de arreglos de
 * cada ancho) y `EtiquetasListas` dan acceso por miembro; en los chunks cuyo destino es un
 * miembro de un nodo (0x26, 0x3F, 0x27, 0x28, 0x0D) o el vector de punto de vista (0x2B) la cifra no
 * cambia con el acceso por miembro y se deja el acceso por puntero. Se supone, sin verificar, que la
 * causa es que el compilador no da por afectado un miembro de un agregado por un almacen a un global
 * escalar, y que si lo hace con un puntero. En el chunk 0x3E las lecturas de 0x10 y 0x18 van por
 * miembro (`d10`, `d18`) y la de 0x14 por puntero: la ultima por miembro empeora la cifra. Las de
 * 0x10 y 0x18 se guardan ademas en las locales `d10_etiqueta` (ya enmascarada con `~7`) y
 * `d18_etiqueta` justo tras la copia: el original las carga en `v1` y `a1` (`lw v1,0x10(s4)`,
 * 0x80043110, y `lw a1,0x18(s4)`, 0x80043128) tras los almacenes a `D_80069660`, `D_80069670` y
 * `D_8006955C` (0x8004310C, 0x80043118 y 0x80043124) y antes de los demas, y las escribe al final
 * (`sw v1,D_8006954C`, 0x8004316C, y `sw a1,D_80069678`, 0x80043174); con la local de `d18` y la
 * lectura de `d10` dentro de la asignacion final la cifra es 5158 y con las dos locales 4993. En el
 * chunk 0x36 el segundo entero va por miembro (`ETQ(w, campos, 1)`) y se almacena despues del puntero
 * de zonas, como el original (`addu` en 0x80042FA8 antes del `sw` a 0x180($gp) en 0x80042FAC); con el almacen del
 * entero primero, o por puntero, la cifra sube.
 *
 * Orden de las sentencias de dos chunks: en el caso que fija `audio_cargado` el original almacena
 * la bandera (`sb t3,0x1d0($sp)`, 0x80042C4C) antes de las dos lecturas del bufer, por eso
 * `audio_cargado = 1` va antes de `cursor += 8`; con la bandera despues, el planificador sube las
 * lecturas por encima del almacen. En el chunk 0x3E el original carga las etiquetas 0x00 a 0x0C en
 * orden ascendente de direccion (`lhu v0,0x128($sp)` ... `lw t0,0xc($s4)`, 0x800430E4 a 0x800430FC),
 * y el fuente las lee en ese orden; los almacenes salen en el orden que decide el planificador.
 *
 * Segundo entero de las etiquetas leido antes de un almacen: en la etiqueta 0x25 del chunk 0x22, la 0x24
 * del chunk 0x20, la 0x37 del chunk 0x36 y la 0x48 del chunk 0x47 el original carga el entero de
 * `campos + 4` antes del almacen intermedio y lo guarda en D_800694A0 despues. Etiqueta 0x25: `lw v0,4(s0)`
 * en 0x800424C0, delante de `sw a0,8(a1)` en 0x800424D0 (el almacen de la direccion de la lista), con el `sw`
 * a 0x180($gp) en 0x800424C8. Etiqueta 0x24: `lw v1,4(s4)` en 0x80042808, delante de `sh v0,0xa(s1)` en
 * 0x80042810, con el `sw` a 0x180($gp) en 0x8004281C. Chunk 0x36: `lw v0,4(s4)` en 0x80042FA4, delante del
 * almacen del puntero de zonas (`sw a0,D_800694FC` en 0x80042FB4), con el `sw` a 0x180($gp) en 0x80042FAC.
 * Chunk 0x47: `lw v0,4(s4)` en 0x80043008, delante de `sb t2` a D_8001004F en 0x80043014, con el `sw` a
 * 0x180($gp) en 0x8004301C. Con la lectura dentro de la asignacion al global el planificador deja la carga
 * tras el almacen y adelanta el almacen al global (se supone, sin verificar, que un acceso por puntero no se
 * da por independiente de un almacen a otro objeto). Por eso la lectura se guarda en la local `compensacion`
 * y se almacena despues, como ya hacia el chunk 0x3F: la local fija la carga antes del almacen intermedio, como
 * el original.
 *
 * Tipo de `orden` y `tipo`: son enteros de 32 bits (`orden` con signo, como pide el `slti` del
 * despacho de primer nivel en 0x80041C94; `tipo` sin signo, `sltiu` en 0x80042300). Con 8 bits el
 * compilador anade un `andi 0xff` tras cada lectura que el original no tiene (0x80041C88 y
 * 0x800422F8). `campos` se asigna al abrir cada serie de chunks (`addiu s4,$sp,0x128` en
 * 0x800422F4) y no antes del bucle de ordenes: los casos 0x2C y 0x4B no lo usan.
 *
 * Orden de la seccion de anillo: el original calcula los dos tamanos de seccion y avanza la posicion
 * antes de sumar 0xA000 a `datos` (el `ori` y el `addu` salen tras `addiu s1,s1,0x2`, 0x800418D0 y
 * 0x800418D4), por eso `D_800694A0` y `posicion += 2` van antes de `datos += 0xA000`.
 *
 * Residuo por causas (cada fila insertada o borrada pesa unos 100 puntos): (1) el chunk 0x3E, donde el
 * original deja tres cargas (0x10, 0x14 y 0x18 de las etiquetas) intercaladas entre los almacenes; el C
 * adelanta las de 0x10 y 0x18 con locales y deja la de 0x14 junto a su almacen (guardada tambien en una
 * local de 32 bits la cifra es 7383); (2) la constante 0x2E en s0 de dos bucles de etiquetas (dos filas); (3)
 * la carga de `D_80069678`, que el original iza a a0 (0x80041D70) y el C deja junto a su uso, con
 * `D_8006954C` izada en su lugar (una fila y dos de operandos); (4) el orden de tres tramos del
 * comienzo: el original deja `sb zero,0x1c0(sp)` entre los almacenes de las banderas (0x80041668)
 * y el C lo deja en el hueco de retardo del `bgtz` de 0x800416C8 (volcado de la planificacion previa
 * al reparto: baja ese almacen por encima de las tres llamadas hasta el hueco de la carga `lbu` de
 * 0x800416BC); el original calcula la direccion de `registro` con `lui` y `addiu` de `D_8005F200`
 * (0x800416FC y 0x80041700) antes del `sll` del indice y el C al reves; y la suma `datos + 0xA000`
 * la hace el original en `v0` tras las cargas (0x80041778 y 0x80041784) y el C en `a1` antes de
 * ellas; (5) el reparto de
 * `v0` y `v1` entre la lectura de `campos + 4` y la suma `datos + desp_campo` en la etiqueta 0x25
 * (0x800424C0 a 0x800424D0), con el orden de sus almacenes (el original guarda `D_800694A0` antes del
 * `li` de 0x800424CC y `lista + 8` despues); (6) nombres de registro (unas 150 filas de 5 puntos).
 *
 * Llamada compartida de la apertura del anillo y las listas: el original deja el `jal` de
 * `func_80044664` en 0x80041A0C (la apertura) y la lectura de las listas salta hacia el
 * (`j` en 0x800420C8); la lectura del caso 0x4B conserva la suya y sale con `beqz v0` directo al
 * epilogo (0x80042264). En el ultimo pase de saltos el compilador recorre cada salto incondicional al
 * epilogo y funde su cola con la de otro salto igual. Medido en los volcados de cc1 (pases de
 * planificacion y de saltos): con la salida del caso 0x4B escrita como un bloque `return 1;` propio
 * la cola que desaparece es la de la apertura y el `jal` queda en la lectura de las listas (la cifra
 * es 5823); con la salida del caso 0x4B escrita como salto a la etiqueta `fallo_lectura`, que es la
 * salida de la primera lectura del anillo, desaparece la de las listas y el `jal` queda en la
 * apertura, como en el original, y el caso 0x4B sale con `beqz v0` directo (4993). Se supone, sin
 * verificar, que el orden en que el pase recorre los saltos al epilogo depende de que la salida del
 * 0x4B sea un bloque `li`/`j` propio.
 *
 * Bucles de etiquetas del chunk 0x05 (causa 2): escrito como `while (*cursor != 0x2E)` el
 * compilador iza la constante a s0 (`move s0,t3` como el original y `li s1,6`) pero deja la salida del
 * bucle como `beq` mas `j` y no recarga `*cursor` antes del bucle: la cifra sube.
 *
 * El original conserva `libre += x` y `monton = libre` en dos instrucciones (`addu s6,s6,v0` en
 * 0x80041E44 y `move s5,s6` en 0x80041E58, con las cargas de `D_80069548` y `D_8006952E` entre
 * ambas). El C las conserva al escribir `D_80069538 = libre;` antes de `monton = libre;`: con
 * `monton = libre` primero el compilador funde las dos sentencias en un solo `addu s5,s6,v0` y no
 * emite la copia.
 *
 * La constante 0x2E de las pruebas de fin de chunk no se iza a un registro guardado en ningun
 * bucle: hay 34 `li ...,46` en el codigo generado y 35 en el original. Lo que difiere es la forma
 * de los bucles de etiquetas (por ejemplo el del chunk 0x36, original 0x80042F68 a 0x80042FB8): el
 * original conserva el valor de la guarda en s0 (`addu s0,t4,zero` en 0x80042F78) y la etiqueta 0x37
 * en s1, y la prueba de salida del bucle compara con s0; aqui solo la etiqueta se iza (a s0) y la
 * prueba de salida recarga 0x2E con `li` en cada vuelta. `hijo_matriz` (pseudo 98, R 72, L 2297) vive
 * desde la entrada de la funcion porque se lee en algun camino sin asignacion previa; con la
 * variable compartida queda en la pila, como el original.
 *
 * Reserva de pila: el original reserva 0x210 (`addiu sp` en 0x800415A0) y sin la local el marco es
 * 0x200; la cifra medida sin la local es 6571 y con ella 4993. Las dos reservas de 8 bytes suman los
 * 16 que faltan: la primera va antes de `tamanos` (que queda en 0xE8, como el original) y la segunda
 * tras `campos_mem`. Residuo: el original tiene entre `n_secciones` (0x1B0) y `es_jugador` (0x1B8) una
 * ranura de derrame de 4 bytes que ninguna instruccion usa y el C no; se supone, sin verificar, que es
 * un pseudo que `global-alloc` no coloco y que `reload` recoloco en un registro, y que por eso los
 * derrames del C quedan 8 bytes mas arriba que los del original (0x1B0 frente a 0x1A8 en el primero).
 *
 * Carga un contenedor de nivel o escena por su identificador (indice de D_8005F200) en `datos`.
 * Lee la cabecera del archivo, descomprime el script (seccion de tipo 1) y las secciones que sus
 * comandos E piden, y despues interpreta el script: 0x2C reparte la memoria en listas y grupos y
 * lee las secciones de datos, 0x4B elige el banco del idioma y 0x2D abre una serie de chunks
 * (tipo y etiquetas de longitud fija) que construyen los recursos: sonido (0), parametros de
 * sonido (5), entidades (7, 8, 10), volumenes de escena (9), modelos jerarquicos (0x20), recursos
 * (0x22), imagenes (0x29), zonas de colision (0x36), camara y tamano de los grupos (0x3B),
 * demostracion (0x47) y textos (0x49). Devuelve 0 si todo salio bien y 1 si el disco falla, la
 * suma de control de la cabecera no coincide o una descompresion no termina.
 */
s32 CargarContenedor(s16 archivo, u8* datos)
{
    RECT rect;
    GsIMAGE imagen;
    EntradaSeccion secciones[14];
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva_pila[2];
    s32 tamanos[15] = {
        0x4, 0x8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000,
        0x10000
    };
    /*
     * Bufer de las etiquetas del script. El original lo direcciona por un registro base (s4) en todos
     * los campos salvo el primero, que lee con desplazamiento sobre el puntero de pila: `campos` es el
     * puntero y `campos_mem` el bufer, que se usa directo solo en el primer campo de cada etiqueta.
     */
    u8 campos_mem[0x80];
    /* Reserva de pila: local sin uso que completa el marco del original. */
    s32 reserva_cima[2];
    u8* campos;
    u8* bufer_anillo;
    RegistroArchivo* registro;
    u8* cursor;
    /* Puntero de la lectura de la cabecera de secciones: el original lo guarda aparte del cursor del script. */
    u8* cabecera;
    u8* libre;
    u8* monton;
    u8* nodo;
    /* Nodo del chunk de entidades: el original lo guarda en otro registro que el de los demas chunks. */
    u8* entidad;
    u8* hijo;
    u8* hijo_matriz;
    u8* aux;
    u8* modelo;
    u8* destino_seccion;
    s32 posicion;
    /*
     * Desplazamiento leido de los campos de un chunk, desplazamiento del banco de idioma y resultado
     * de la busqueda de seccion de datos: un solo valor, como en el original (s7). Cada uso lo
     * asigna antes, salvo la lectura del banco con un idioma fuera de 0..5, que 0x800416DC ya
     * reinicia a 0 y que por tanto no se alcanza.
     */
    s32 desp_campo;
    s32 compensacion;
    u32 n_secciones;
    u32 i;
    u16 es_jugador;
    u8 pools_listos;
    u8 banco_cargado;
    u8 audio_cargado;
    s32 tam_audio;
    s32 desp_texturas;
    u32 tam_extra;
    u8* datos_extra;
    s32 orden;
    u32 tipo;
    u8 etiqueta;
    EstadoPrincipal* estado;
    s32 d18_etiqueta;
    s32 d10_etiqueta;

    /* Memoria de trabajo del cargador: el destino recibe primero el contenido y luego la memoria libre. */
    libre = datos;
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
    /*
     * Los tres bytes del banco de registros (0x80010041, 0x80010050 y 0x800100E6) se acceden con una sola
     * base (`lui` en 0x800416B8); el resto de los accesos a D_80010050 usan un `lui` propio.
     */
    estado = ESTADO_PRINCIPAL;
    if ((s8)estado->r[0x01] <= 0) {
        estado->r[0x01] = 6;
    }
    if (estado->r[0x10] >= 6) {
        estado->r[0x10] = 0;
    }
    estado->r[0xA6] = D_80069594;
    registro = &D_8005F200[archivo];
    if (registro->tamano == 0) {
        printf("BouzeID %d not found\n", archivo);
    }
    D_800694D0 = 0x80;
    CdControlB(0xE, &D_800694D0, NULL);
    func_80040DDC();
    *(CdlLOC*)D_8006A928 = *(CdlLOC*)registro->posicion;
    *(u32*)(D_8006A928 + 4) = registro->tamano;
    D_8006948C = (u32)datos;
    D_80069490 = (u32)datos;
    D_8006947C = (u32)datos + 0xA000;
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
        D_800694A0 = D_800694A4 = registro->tamano;
        IniciarLecturaContinua((CdlLOC*)D_8006A928);
        posicion = 0;
        if (D_80069480 == 0) {
            do {
                if (CdStatus() & 0x10) {
                    return 1;
                }
            } while (D_80069480 == 0);
        }
        cabecera = (u8*)D_80069490;
        if (SumaControl((s8*)cabecera, 0x7FC) != *(s32*)(cabecera + 0x7FC)) {
            return 1;
        }
        D_80069480 = 0;
        D_80069494 = *(u32*)cabecera;
        cabecera += 4;
        n_secciones = *(u32*)cabecera;
        cabecera += 4;
        for (i = 0; i < n_secciones; i++) {
            secciones[i].tipo = *(s32*)cabecera;
            secciones[i].tamano = *(u32*)(cabecera + 4);
            secciones[i].alineado = *(u32*)(cabecera + 8);
            cabecera += 12;
        }
        D_800694A0 = secciones[posicion].alineado + (secciones[posicion + 1].alineado + 0x800);
        posicion += 2;
        datos += 0xA000;
        D_80069498 = (u32)datos;
        D_8006949C = D_80069490 + 0x800;
        if (func_80044664((u8*)D_8006949C, datos, (void*)0x1F800000) == 0) {
        fallo_lectura:
            return 1;
        }
        cursor = datos;
        if (cursor[1] == 0x45) {
            if (*cursor++ == 0x2D) {
                if (*cursor != 0x2E) {
                    bufer_anillo = campos_mem;
                    do {
                        tipo = *cursor++;
                        if (tipo == 0x45) {
                            CopiarBytes(cursor, bufer_anillo, 1);
                            cursor++;
                            destino_seccion = (u8*)D_80067E98[campos_mem[0]];
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
        datos = datos + 0xA000;
        D_80069484 = 0;
        D_80069488 = 0;
        D_800694A0 = 0x800;
        D_80069498 = (u32)datos;
        D_800694A4 = registro->tamano;
        IniciarLecturaContinua((CdlLOC*)D_8006A928);
        posicion = 0;
        while (D_8006955E != 0) {
        }
        if (SumaControl((s8*)datos, 0x7FC) != *(s32*)(datos + 0x7FC)) {
            return 1;
        }
        D_80069494 = *(u32*)datos;
        n_secciones = *(u32*)(datos + 4);
        cabecera = datos + 8;
        for (i = 0; i < n_secciones; i++) {
            secciones[i].tipo = *(s32*)cabecera;
            secciones[i].tamano = *(u32*)(cabecera + 4);
            secciones[i].alineado = *(u32*)(cabecera + 8);
            cabecera += 12;
        }
        D_800694A0 = secciones[posicion].alineado;
        D_80069484 = 0;
        D_80069498 = (u32)datos;
        IniciarLecturaContinua((CdlLOC*)D_8006A928);
        posicion++;
        while (D_8006955E != 0) {
        }
        cursor = datos;
        if (cursor[1] == 0x45) {
            if (*cursor++ == 0x2D) {
                if (*cursor != 0x2E) {
                    campos = campos_mem;
                    do {
                        tipo = *cursor++;
                        if (tipo == 0x45) {
                            CopiarBytes(cursor, campos, 1);
                            destino_seccion = (u8*)D_80067E98[campos_mem[0]];
                            D_800694A0 = secciones[posicion++].alineado;
                            D_80069498 = (u32)destino_seccion;
                            D_80069484 = 0;
                            IniciarLecturaContinua((CdlLOC*)D_8006A928);
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
        IniciarLecturaContinua((CdlLOC*)D_8006A928);
        while (D_8006955E != 0) {
        }
    }

    /*
     * Script de carga, ya descomprimido en `datos`. Ordenes de primer nivel hasta el fin 0x2F:
     * 0x2C reparte la memoria en listas y grupos y lee las secciones de datos, 0x4B elige el banco
     * del idioma y 0x2D abre una serie de chunks de recursos (tipo, y etiquetas con longitud
     * fija) hasta el cierre 0x2E. El cursor continua donde lo dejo la lectura de las secciones, sobre
     * el buffer del script: `datos` ya apunta mas alla (suma 0x1D000) y el original no copia `datos` al
     * cursor (el salto de 0x80041C84 al bucle conserva `s2`).
     */
    for (;;) {
        orden = *cursor;
        if (orden == 0x2F) {
            break;
        }
        cursor++;
        switch (orden) {
        case 0x2C:
            /*
             * Reparte la memoria de trabajo: tres listas de ordenacion por buffer, los grupos de
             * entidades, modelos, volumenes y recursos, el monton y la zona de textos; despues
             * inicializa los grupos, busca la posicion de los datos de cada seccion en el
             * contenedor y lanza la lectura del resto.
             */
            if (pools_listos != 1) {
                /* El original sale con `bne t4,t1` (0x80041CCC) al bucle infinito de 0x80042088. */
                goto sin_listas;
            }
            if (banco_cargado == 0) {
                D_8006959C = (u32)libre;
                libre += D_8006954C;
            }
            /* El original compara el contador con signo (`slti`, 0x80041D5C). */
            for (i = 0; (s32)i < 3; i++) {
                D_8006AE20[i].length = 9;
                D_8006AE20[i].org = (GsOT_TAG*)libre;
                libre += tamanos[9];
                D_8006AE60[i].length = 8;
                D_8006AE60[i].org = (GsOT_TAG*)libre;
                libre += tamanos[8];
                D_8006AEA0[i].length = 9;
                D_8006AEA0[i].org = (GsOT_TAG*)libre;
                libre += tamanos[9];
            }
            D_8006968C = libre;
            libre += (s16)D_8006955C * 0x1F4;
            D_80069570 = libre;
            libre += D_80069670 * 0x14;
            D_8006964C = libre;
            libre += (s16)D_80069660 * 0xB8;
            D_800695D4 = libre;
            libre += (s16)D_800694E6 * 0x58;
            D_80069644 = libre;
            libre += D_8006967E * 0xC;
            D_80069528 = libre;
            libre += D_800695C2 * 0x3C;
            D_80069538 = libre;
            monton = libre;
            libre = monton + D_80069548;
            D_800694B8 = libre;
            libre += (s16)D_8006952E * 8;
            D_80076188 = D_8006959C;
            D_80069680 = D_8006959C;
            D_8006958C = D_8006959C + D_8006954C - 0x400;
            D_80069610 = D_8006958C;
            D_80069614 = D_8006958C;
            if (D_80069678 != 0) {
                D_80069520 = libre;
                libre += D_80069678;
            } else {
                D_80069520 = NULL;
            }
            if (datos_extra != NULL && tam_extra != 0) {
                CopiarBytesSolapados(datos_extra, tam_extra, libre);
                D_80069590 = (u16*)libre;
                datos_extra = NULL;
                libre += tam_extra;
            }
            InitListPool(D_8006968C, 0x1F4, (s16)D_8006955C * 0x1F4);
            InitListPool((u8*)D_8006964C, 0xB8, (s16)D_80069660 * 0xB8);
            InitListPool(D_80069570, 0x14, D_80069670 * 0x14);
            InitListPool((u8*)D_800695D4, 0x58, (s16)D_800694E6 * 0x58);
            InitListPool(D_80069644, 0xC, D_8006967E * 0xC);
            InitListPool(D_80069528, 0x3C, D_800695C2 * 0x3C);
            memset(D_80069538, 0, D_80069548);
            desp_campo = func_80040F78(secciones, n_secciones, 4);
            datos = libre;
            if (audio_cargado == 1) {
                audio_cargado = 2;
                D_8006966C = datos + tam_audio;
                D_80069550 = datos + tam_audio;
                D_800695AC = (s16*)(datos + tam_audio + 8);
            }
            func_8003652C();
            func_800365D0();
            /* El original salta con `j` (0x80042080) por encima del bucle infinito de 0x80042088. */
            goto con_listas;
        sin_listas:
            for (;;) {
            }
        con_listas:
            D_80069484 = 0;
            D_80069498 = (u32)datos;
            D_8006948C = D_80069490;
            D_8006949C = D_80069490;
            IniciarLecturaContinua((CdlLOC*)D_8006A928);
            if (D_80069494 != 0) {
                if (func_80044664((u8*)D_8006949C, (u8*)D_80069498, (void*)0x1F800000) == 0) {
                    return 1;
                }
            } else {
                while (D_8006955E != 0) {
                }
            }
            break;
        case 0x4B:
            /* Banco del idioma activo: busca su posicion en la cabecera y lee sus secciones. */
            banco_cargado = 1;
            D_8006959C = (u32)libre;
            libre += D_8006954C;
            if (datos_extra != NULL && tam_extra != 0) {
                CopiarBytesSolapados(datos_extra, tam_extra, libre);
                D_80069590 = (u16*)libre;
                datos_extra = NULL;
                libre += tam_extra;
            }
            datos = libre;
            if (D_80010050 == 0) {
                desp_campo = func_80040F78(secciones, n_secciones, 6);
            } else if (D_80010050 == 1) {
                desp_campo = func_80040F78(secciones, n_secciones, 5);
            } else if (D_80010050 == 2) {
                desp_campo = func_80040F78(secciones, n_secciones, 7);
            } else if (D_80010050 == 3) {
                desp_campo = func_80040F78(secciones, n_secciones, 8);
            } else if (D_80010050 == 4) {
                desp_campo = func_80040F78(secciones, n_secciones, 9);
            } else if (D_80010050 == 5) {
                desp_campo = func_80040F78(secciones, n_secciones, 0xA);
            }
            D_80069484 = 0;
            D_80069498 = (u32)datos;
            D_8006948C = D_80069490;
            D_8006949C = D_80069490;
            D_800694AC = CdPosToInt((CdlLOC*)D_8006A928) + ((u32)desp_campo >> 11);
            CdIntToPos(D_800694AC, (CdlLOC*)D_8006A928);
            IniciarLecturaContinua((CdlLOC*)D_8006A928);
            if (D_80069494 != 0) {
                if (func_80044664((u8*)D_8006949C, (u8*)D_80069498, (void*)0x1F800000) == 0) {
                    goto fallo_lectura;
                }
            } else {
                while (D_8006955E != 0) {
                }
            }
            D_80069488 += desp_campo + D_80069478;
            D_800694AC = CdPosToInt((CdlLOC*)D_8006A928);
            /*
             * El original divide con signo (`bgez`, `addiu 0x7FF` y `sra 11` en 0x800422B4..0x800422C0,
             * sin `srl`): D_80069478 se declara u32 y el molde a s32 reproduce esa instruccion.
             */
            D_800694AC = D_800694AC + (s32)D_80069478 / 2048;
            CdIntToPos(D_800694AC, (CdlLOC*)D_8006A928);
            break;
        case 0x2D:
            if (*cursor == 0x2E) {
                cursor++;
                continue;
            }
            campos = campos_mem;
            do {
                tipo = *cursor++;
                if (tipo >= 0x4A) {
                    continue;
                }
                switch (tipo) {
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
                    /*
                     * La etiqueta se lee una sola vez, en la prueba del bucle: el original reutiliza ese
                     * registro para el rango de la tabla de saltos y para el avance del cursor.
                     */
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x26:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, nodo, 8) = *(u16*)campos_mem;
                            cursor += 4;
                            break;
                        case 0x24: {
                            /*
                             * El original tiene un cuerpo por etiqueta (dos entradas de la tabla de saltos:
                             * 0x800423E8 para 0x24 y 0x80042424 para 0x40) que comparten solo la cola del
                             * almacen de la clase en 0x8004245C; por eso el C repite el cuerpo y no es una
                             * sentencia replicada. Unidos en un solo cuerpo con la clase elegida por la
                             * etiqueta la cifra sube a 30877. El modelo se usa solo hasta la llamada: un
                             * temporal propio, no `aux`.
                             */
                            u8* modelo_gs;
                            CopiarBytes(cursor, campos, 8);
                            cursor += 8;
                            desp_campo = *(s32*)campos_mem;
                            D_800694A0 = *(s32*)(campos + 4);
                            modelo_gs = datos + desp_campo + 4;
                            EN(u8*, nodo, 0x54) = modelo_gs;
                            GsMapModelingData((unsigned long*)modelo_gs);
                            EN(u16, nodo, 0xA) = 2;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        }
                        case 0x40: {
                            u8* modelo_gs;
                            CopiarBytes(cursor, campos, 8);
                            cursor += 8;
                            desp_campo = *(s32*)campos_mem;
                            D_800694A0 = *(s32*)(campos + 4);
                            modelo_gs = datos + desp_campo + 4;
                            EN(u8*, nodo, 0x54) = modelo_gs;
                            GsMapModelingData((unsigned long*)modelo_gs);
                            EN(u16, nodo, 0xA) = 0x100;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        }
                        case 0x25: {
                            /*
                             * La lista de 0x14 bytes y la cabecera del modelo viven solo en este caso: con
                             * locales propias cada una cae en un temporal (a1 y a0 en el original) y deja de
                             * ocupar un registro guardado que `aux` y `modelo` comparten con otros chunks.
                             */
                            u8* lista;
                            u8* cab;
                            CopiarBytes(cursor, campos, 8);
                            aux = campos;
                            lista = (u8*)AllocListNode((u8*)D_80069570, 0x14, D_80069670 * 0x14);
                            if (lista == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, nodo, 0x54) = lista;
                            desp_campo = *(s32*)aux;
                            compensacion = *(s32*)(aux + 4);
                            EN(u8*, lista, 8) = datos + desp_campo;
                            D_800694A0 = compensacion;
                            EN(u16, nodo, 0xA) = 4;
                            /* El original lee la cabecera del modelo dos veces: la primera (`lw v0,8(a1)`, 0x800424D8)
                             * alimenta la media palabra de `cab + 2` (`lhu v1,2(v0)`, 0x800424E4) y se copia a `cab`
                             * (`move a0,v0`, 0x800424E0); `cab` avanza en su sitio (`addiu a0,a0,8`, 0x800424FC) y la
                             * ultima lectura va por `cab` ya avanzado (0x80042508). La media palabra se lee antes de
                             * escribir `lista + 8` (`sw` de 0x800424EC) y el primer almacen a `lista + 8` se conserva
                             * aunque se sobrescribe en 0x80042500. */
                            EN(u16, lista, 0x12) = EN(u16, EN(u8*, lista, 8), 2) >> 1;
                            cab = EN(u8*, lista, 8);
                            EN(u8*, lista, 8) = cab + 4;
                            EN(u16, lista, 0xE) = EN(u16, cab, 4);
                            EN(u8*, lista, 8) = cab += 8;
                            cursor += 8;
                            EN(u16, lista, 0x10) = EN(u16, cab, 4);
                            break;
                        }
                        case 0x3F:
                            CopiarBytes(cursor, campos, 0xC);
                            desp_campo = *(s32*)(campos + 4);
                            compensacion = *(s32*)(campos + 8);
                            EN(u16, nodo, 0xA) = 1;
                            EN(u8*, nodo, 0x54) = datos + desp_campo;
                            cursor += 0xC;
                            D_800694A0 = compensacion;
                            /* En el original el `sh` de 0x50 (0x80042550) ocupa el hueco del salto de salida, tras
                             * el `addiu` del cursor y el `sw` a 0x180($gp); su carga (`lhu`, 0x80042540) va antes.
                             * Con la sentencia delante del avance del cursor el `sh` sale antes que ambos. */
                            EN(u16, nodo, 0x50) = *(u16*)campos_mem;
                            break;
                        case 0x27:
                            CopiarBytes(cursor, campos, 4);
                            EN(s32, nodo, 0xC) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x4E) = *(u16*)campos_mem;
                            cursor += 4;
                            break;
                        case 0x28:
                            CopiarBytes(cursor, campos, 3);
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x14) = campos_mem[0];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x15) = campos[1];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x16) = campos[2];
                            EN(u8, nodo + EN(u16, nodo, 0x10) * 4, 0x17) = 0;
                            cursor += 3;
                            EN(u16, nodo, 0x10) = EN(u16, nodo, 0x10) + 1;
                            break;
                        case 0x0D:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(u16, nodo + EN(u16, nodo, 0x12) * 14, 0x24) = *(u16*)campos_mem;
                            EN(u16, nodo + EN(u16, nodo, 0x12) * 14, 0x26) = *(u16*)(campos + 2);
                            EN(u16, nodo + EN(u16, nodo, 0x12) * 14, 0x28) = *(u16*)(campos + 4);
                            EN(u8, nodo + EN(u16, nodo, 0x12) * 14, 0x2D) = campos[9];
                            EN(u8, nodo + EN(u16, nodo, 0x12) * 14, 0x2A) = campos[6];
                            EN(u16, nodo + EN(u16, nodo, 0x12) * 14, 0x2E) = campos[10];
                            EN(u16, nodo + EN(u16, nodo, 0x12) * 14, 0x30) = campos[11];
                            EN(u8, nodo + EN(u16, nodo, 0x12) * 14, 0x2B) = campos[7];
                            EN(u8, nodo + EN(u16, nodo, 0x12) * 14, 0x2C) = campos[8];
                            cursor += 0xC;
                            EN(u16, nodo, 0x12) = EN(u16, nodo, 0x12) + 1;
                            break;
                        default:
                            break;
                        }
                    }
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
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x24: {
                            u8* modelo_gs;

                            CopiarBytes(cursor, campos, 8);
                            desp_campo = *(s32*)campos_mem;
                            compensacion = *(s32*)(campos + 4);
                            EN(u16, nodo, 0xA) = 2;
                            D_800694A0 = compensacion;
                            modelo_gs = datos + desp_campo + 4;
                            EN(u8*, nodo, 0x54) = modelo_gs;
                            GsMapModelingData((unsigned long*)modelo_gs);
                            cursor += 8;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        }
                        case 0x21:
                            CopiarBytes(cursor, campos, 4);
                            cursor += 4;
                            EN(s32, nodo, 0xC) = *(u16*)campos_mem;
                            EN(u16, nodo, 0x4E) = 0;
                            break;
                        case 0x10:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x18) = *(s32*)campos_mem;
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x1C) = *(s32*)(campos + 4);
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x20) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            TransMatrix((MATRIX*)(EN(u8*, hijo_matriz, 4) + 4),
                                        (VECTOR*)(EN(u8*, EN(u8*, hijo_matriz, 4), 0x44) + 0x18));
                            D_8006B568[EN(s32, nodo, 0xC)] = (struct ModeloDibujo*)hijo;
                            D_80069648 = RemoveListNode((NodoLista*)D_80069648, (NodoLista*)nodo);
                            break;
                        case 0x12:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0) = ETQ(w, campos_mem, 0);
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 4) = ETQ(w, campos_mem, 0);
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 8) = ETQ(w, campos_mem, 0);
                            cursor += 0xC;
                            ScaleMatrix((MATRIX*)(EN(u8*, hijo_matriz, 4) + 4),
                                        (VECTOR*)EN(u8*, EN(u8*, hijo_matriz, 4), 0x44));
                            break;
                        case 0x11:
                            CopiarBytes(cursor, campos, 6);
                            aux = campos;
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
                            EN(s32, EN(u8*, hijo_matriz, 4), 0x4C) = 0;
                            EN(s32, EN(u8*, hijo_matriz, 4), 0x48) = 0;
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x10) = *(u16*)aux;
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x12) = *(u16*)(aux + 2);
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x14) = *(u16*)(aux + 4);
                            EN(s32, EN(u8*, hijo_matriz, 4), 0) = 0;
                            cursor += 6;
                            RotMatrix((SVECTOR*)(EN(u8*, EN(u8*, hijo_matriz, 4), 0x44) + 0x10),
                                      (MATRIX*)(EN(u8*, hijo_matriz, 4) + 4));
                            break;
                        case 0x39:
                            CopiarBytes(cursor, campos, 2);
                            EN(u16, hijo, 0xB6) = *(u16*)campos_mem;
                            cursor += 2;
                            break;
                        case 0x43:
                            CopiarBytes(cursor, campos, 1);
                            EN(u8, hijo, 0xB5) = campos_mem[0];
                            cursor += 1;
                            break;
                        default:
                            break;
                        }
                    }
                    break;

                case 0x29:
                    /* Imagenes (.-)*): cada etiqueta 0x2A lleva el offset de un TIM que se sube a la VRAM. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x2A) {
                            CopiarBytes(cursor, campos, 8);
                            desp_campo = *(s32*)campos_mem;
                            D_800694A0 = *(s32*)(campos + 4);
                            GsGetTimInfo((unsigned long*)(datos + desp_campo + 4), &imagen);
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

                case 0x00:
                    /* Sonido (.-\0\1): audio, fuente de efectos, bancos de texturas e instrumentos. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x01:
                            CopiarBytes(cursor, campos, 8);
                            audio_cargado = 1;
                            cursor += 8;
                            tam_audio = *(s32*)campos_mem;
                            libre += *(s32*)(campos + 4);
                            D_800694A0 = *(s32*)(campos + 4);
                            break;
                        case 0x02:
                            CopiarBytes(cursor, campos, 8);
                            desp_campo = ((Etiquetas*)campos_mem)->w[0];
                            D_8006951C = 0x1010;
                            D_800694A0 = ((Etiquetas*)campos)->w[1];
                            func_8003ECD4(datos + desp_campo, D_800694A0);
                            D_8006951C += D_800694A0;
                            cursor += 8;
                            break;
                        case 0x4C:
                            CopiarBytes(cursor, campos, 0x30);
                            /*
                             * D_800694A0 se escribe solo dentro de cada coincidencia: el almacen del
                             * original (0x80042D8C) lo alcanzan las seis ramas y, con un idioma fuera
                             * de 0..5 (que 0x800416DC ya reinicia a 0), el salto de 0x80042D70 pasa a
                             * 0x80042D90 sin escribirlo.
                             */
                            if (D_80010050 == 0) {
                                desp_texturas = *(s32*)campos_mem;
                                D_800694A0 = *(s32*)(campos + 4);
                            } else if (D_80010050 == 1) {
                                desp_texturas = *(s32*)(campos + 8);
                                D_800694A0 = *(s32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                desp_texturas = *(s32*)(campos + 16);
                                D_800694A0 = *(s32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                desp_texturas = *(s32*)(campos + 24);
                                D_800694A0 = *(s32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                desp_texturas = *(s32*)(campos + 32);
                                D_800694A0 = *(s32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                desp_texturas = *(s32*)(campos + 40);
                                D_800694A0 = *(s32*)(campos + 44);
                            }
                            {
                                u8* sonido;

                                sonido = datos + desp_texturas;
                                D_800694EC = sonido;
                                D_80069598 = (u32*)sonido;
                                D_800695FC = (s16*)(sonido + 8);
                                cursor += 0x30;
                                D_800694EC = sonido + *(s32*)sonido;
                                D_80069598 = (u32*)(sonido + *(s32*)(sonido + 4));
                            }
                            libre += D_800694A0;
                            break;
                        case 0x4D:
                            CopiarBytes(cursor, campos, 0x30);
                            /* Igual que en 0x4C: el almacen del original (0x80042E8C) solo sigue a una coincidencia. */
                            if (D_80010050 == 0) {
                                desp_campo = *(s32*)campos_mem;
                                D_800694A0 = *(s32*)(campos + 4);
                            } else if (D_80010050 == 1) {
                                desp_campo = *(s32*)(campos + 8);
                                D_800694A0 = *(s32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                desp_campo = *(s32*)(campos + 16);
                                D_800694A0 = *(s32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                desp_campo = *(s32*)(campos + 24);
                                D_800694A0 = *(s32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                desp_campo = *(s32*)(campos + 32);
                                D_800694A0 = *(s32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                desp_campo = *(s32*)(campos + 40);
                                D_800694A0 = *(s32*)(campos + 44);
                            }
                            D_800695E4 = D_8006951C;
                            func_8003ECD4(datos + desp_campo, D_800694A0);
                            cursor += 0x30;
                            break;
                        case 0x04:
                            CopiarBytes(cursor, campos, 8);
                            func_8003EB88(campos);
                            cursor += 8;
                            break;
                        case 0x44:
                            CopiarBytes(cursor, campos, 0xC);
                            func_8003ECF8(campos);
                            cursor += 0xC;
                            break;
                        }
                    }
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
                            CopiarBytes(cursor, campos, 3);
                            func_8003EC3C(campos);
                            cursor += 3;
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
                            CopiarBytes(cursor, campos, 8);
                            cursor += 8;
                            desp_campo = *(s32*)campos_mem;
                            compensacion = ETQ(w, campos, 1);
                            D_800694A0 = compensacion;
                            D_800694FC = datos + desp_campo;
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
                            CopiarBytes(cursor, campos, 8);
                            cursor += 8;
                            desp_campo = *(s32*)campos_mem;
                            compensacion = *(s32*)(campos + 4);
                            D_8001004F = 1;
                            D_800694A0 = compensacion;
                            D_800695B0 = (u16*)(datos + desp_campo);
                        }
                    } while (*cursor != 0x2E);
                    break;

                case 0x3B:
                    /* Camara y reparto de memoria: 0x3E fija el tamano de cada grupo y habilita la orden 0x2C. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x3C:
                            CopiarBytes(cursor, campos, 4);
                            D_800695B4 = campos[2];
                            D_80069530 = campos[3];
                            D_8006960C = *(s16*)campos_mem;
                            cursor += 4;
                            break;
                        case 0x3E:
                            CopiarBytes(cursor, campos, 0x1C);
                            d10_etiqueta = ((EtiquetasListas*)campos)->d10 & ~7;
                            d18_etiqueta = ((EtiquetasListas*)campos)->d18;
                            pools_listos = 1;
                            D_80069670 = ((EtiquetasListas*)campos_mem)->w00;
                            D_80069660 = ((EtiquetasListas*)campos)->w02;
                            D_800694E6 = ((EtiquetasListas*)campos)->w04;
                            D_8006955C = ((EtiquetasListas*)campos)->w06;
                            D_8006967E = ((EtiquetasListas*)campos)->w08;
                            D_800695C2 = ((EtiquetasListas*)campos)->w0A;
                            D_80069548 = ((EtiquetasListas*)campos)->d0C;
                            D_8006952E = *(u16*)(campos + 0x14);
                            D_8006954C = d10_etiqueta;
                            D_80069678 = d18_etiqueta;
                            if (D_8006952E < 0x12C) {
                                D_8006952E = 0x12C;
                            }
                            cursor += 0x1C;
                            break;
                        case 0x2B:
                            CopiarBytes(cursor, campos, 0xC);
                            D_8006D928.vpx = *(s32*)campos_mem;
                            D_8006D928.vpy = *(s32*)(campos + 4);
                            D_8006D928.vpz = *(s32*)(campos + 8);
                            cursor += 0xC;
                            break;
                        case 0x3D:
                            CopiarBytes(cursor, campos, 6);
                            D_800694B0 = ETQ(hs, campos_mem, 0) / 4;
                            D_800695F2 = ETQ(hs, campos, 1) / 4;
                            D_800695F4 = ETQ(hs, campos, 2) / 4;
                            cursor += 6;
                            D_8006969C = D_800694B0 - 0x80;
                            break;
                        }
                    }
                    break;

                case 0x49:
                    /* Textos (.-IJ): una pareja (offset, tamano) por idioma; se guarda la del idioma activo. */
                    if (*cursor == 0x2E) {
                        goto fin_chunks;
                    }
                    do {
                        etiqueta = *cursor++;
                        if (etiqueta == 0x4A) {
                            CopiarBytes(cursor, campos, 0x30);
                            if (D_80010050 == 0) {
                                datos_extra = datos + *(s32*)campos_mem;
                                tam_extra = *(u32*)(campos + 4);
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
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x16:
                            CopiarBytes(cursor, campos, 8);
                            EN(s32, nodo, 8) = *(s32*)campos_mem;
                            EN(s32, nodo, 0xC) = *(s32*)(campos + 4);
                            cursor += 8;
                            break;
                        case 0x10:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(s32, nodo, 0x10) = *(s32*)campos_mem;
                            EN(s32, nodo, 0x14) = *(s32*)(campos + 4);
                            EN(s32, nodo, 0x18) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            break;
                        case 0x1F:
                            CopiarBytes(cursor, campos, 1);
                            EN(u16, nodo, 0x34) = campos_mem[0];
                            cursor += 1;
                            break;
                        case 0x1C:
                            CopiarBytes(cursor, campos, 8);
                            EN(u16, nodo, 0x28) = *(u16*)campos_mem;
                            EN(u16, nodo, 0x2A) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x2C) = *(u16*)(campos + 4);
                            EN(u16, nodo, 0x36) = *(u16*)(campos + 6);
                            cursor += 8;
                            break;
                        case 0x11:
                            CopiarBytes(cursor, campos, 6);
                            EN(u16, nodo, 0x20) = *(u16*)campos_mem;
                            EN(u16, nodo, 0x22) = *(u16*)(campos + 2);
                            EN(u16, nodo, 0x24) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x33: {
                            u8* elemento;
                            u8* cabeza;

                            /* Elemento de 0x24 bytes al final de la lista +0x30 del volumen. */
                            CopiarBytes(cursor, campos, 0x20);
                            aux = campos;
                            cabeza = EN(u8*, nodo, 0x30);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)monton = 0;
                                EN(u8*, nodo, 0x30) = monton;
                            }
                            monton += 0x24;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(s32, elemento, 4) = *(s32*)aux;
                            EN(s32, elemento, 8) = *(s32*)(aux + 4);
                            EN(u8, elemento, 0xC) = aux[8];
                            EN(u8, elemento, 0xF) = aux[0xB];
                            EN(u8, elemento, 0xD) = aux[9];
                            EN(u8, elemento, 0xE) = aux[0xA];
                            EN(u16, elemento, 0x10) = *(u16*)(aux + 0xC);
                            EN(u16, elemento, 0x12) = *(u16*)(aux + 0xE);
                            EN(s32, elemento, 0x14) = *(s32*)(aux + 0x10);
                            EN(s32, elemento, 0x18) = *(s32*)(aux + 0x14);
                            EN(s32, elemento, 0x1C) = *(s32*)(aux + 0x18);
                            EN(s32, elemento, 0x20) = *(s32*)(aux + 0x1C);
                            cursor += 0x20;
                            break;
                        }
                        default:
                            break;
                        }
                    }
                    break;

                case 0x08:
                    es_jugador = 1;
                    /* sigue con las entidades de los tipos 7 y 10 */
                case 0x07:
                case 0x0A:
                    /* Entidad de escena: una entidad de 0x1F4 bytes con sus etiquetas (posicion, giro...). */
                    entidad = (u8*)AllocListNode((u8*)D_8006968C, 0x1F4, (s16)D_8006955C * 0x1F4);
                    if (entidad == NULL) {
                        for (;;) {
                        }
                    }
                    if (es_jugador != 0) {
                        D_80069504 = (Objeto*)AppendListNode((NodoLista*)D_80069504, (NodoLista*)entidad);
                    } else {
                        D_80069518 = (Objeto*)AppendListNode((NodoLista*)D_80069518, (NodoLista*)entidad);
                    }
                    EN(u16, entidad, 0x108) = 0xA00;
                    EN(u8*, entidad, 0xC0) = entidad + 0xCC;
                    EN(u16, entidad, 0x26) = 0xFFFF;
                    es_jugador = 0;
                    if (*cursor == 0x2E) {
                        ResolverReferenciasContenedor((ContenedorCarga*)entidad);
                        break;
                    }
                    while (*cursor != 0x2E) {
                        switch (*cursor++) {
                        case 0x1F:
                            CopiarBytes(cursor, campos, 1);
                            EN(u16, entidad, 0x26) = campos_mem[0];
                            cursor += 1;
                            break;
                        case 0x27:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, entidad, 0x1C) = *(u16*)campos_mem;
                            cursor += 4;
                            break;
                        case 0x15:
                            CopiarBytes(cursor, campos, 1);
                            EN(u16, entidad, 0x2A) = campos_mem[0];
                            cursor += 1;
                            break;
                        case 0x38:
                            CopiarBytes(cursor, campos, 2);
                            EN(u16, entidad, 0x20) = *(u16*)campos_mem;
                            EN(s32, entidad, 0x30) += (s16)*(u16*)campos_mem * (s16)*(u16*)campos_mem;
                            cursor += 2;
                            break;
                        case 0x46:
                            CopiarBytes(cursor, campos, 2);
                            EN(u16, entidad, 0x3A) = *(u16*)campos_mem;
                            cursor += 2;
                            break;
                        case 0x39:
                            CopiarBytes(cursor, campos, 2);
                            EN(u16, entidad, 0x28) = *(u16*)campos_mem + 0x10;
                            cursor += 2;
                            break;
                        case 0x3A:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, entidad, 0x3C) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x3E) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x1E:
                            CopiarBytes(cursor, campos, 2);
                            EN(u16, entidad, 0x1E) = *(u16*)campos_mem;
                            cursor += 2;
                            break;
                        case 0x0B:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, entidad, 0x170) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x172) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x42:
                            CopiarBytes(cursor, campos, 6);
                            EN(u16, entidad, 0x50) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x52) = *(u16*)(campos + 2);
                            EN(u16, entidad, 0x54) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x0C:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, entidad, 0x174) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x176) = *(u16*)(campos + 2);
                            cursor += 4;
                            break;
                        case 0x41:
                            /* Lista de enteros de 16 bits terminada en cero, copiada al monton. */
                            CopiarBytes(cursor, campos, 0x14);
                            EN(u8*, entidad, 0x178) = monton;
                            i = 0;
                            if (*(u16*)campos_mem != 0) {
                                do {
                                    ((u16*)EN(u8*, entidad, 0x178))[i] = ((u16*)campos)[i];
                                    i++;
                                } while (((u16*)campos)[i] != 0);
                            }
                            monton += ((i + 1) & 0xFFFE) * 2;
                            EN(u8, entidad, 0x14A) = i;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            cursor += 0x14;
                            break;
                        case 0x10:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(s32, entidad, 0xE4) = *(s32*)campos_mem;
                            EN(s32, entidad, 0xE8) = *(s32*)(campos + 4);
                            EN(s32, entidad, 0xEC) = *(s32*)(campos + 8);
                            EN(s32, entidad, 0x100) = *(s32*)(campos + 4);
                            cursor += 0xC;
                            break;
                        case 0x1B:
                            CopiarBytes(cursor, campos, 6);
                            EN(u16, entidad, 0x48) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x4A) = *(u16*)(campos + 2);
                            EN(u16, entidad, 0x4C) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x1C:
                            CopiarBytes(cursor, campos, 8);
                            EN(u16, entidad, 0x50) = *(u16*)campos_mem;
                            EN(u16, entidad, 0x52) = *(u16*)(campos + 2);
                            EN(u16, entidad, 0x54) = *(u16*)(campos + 4);
                            EN(u16, entidad, 0x2E) = *(u16*)(campos + 6);
                            EN(s32, entidad, 0x30) = (s16)*(u16*)(campos + 6) * (s16)*(u16*)(campos + 6);
                            cursor += 8;
                            break;
                        case 0x11:
                            CopiarBytes(cursor, campos, 6);
                            EN(u16, entidad, 0xDC) = *(u16*)campos_mem;
                            EN(u16, entidad, 0xDE) = *(u16*)(campos + 2);
                            EN(u16, entidad, 0xE0) = *(u16*)(campos + 4);
                            cursor += 6;
                            break;
                        case 0x12:
                            CopiarBytes(cursor, campos, 0xC);
                            EN(s32, entidad, 0xCC) = *(s32*)campos_mem;
                            EN(s32, entidad, 0xD0) = *(s32*)(campos + 4);
                            EN(s32, entidad, 0xD4) = *(s32*)(campos + 8);
                            cursor += 0xC;
                            break;
                        case 0x0F: {
                            u8* enlace;

                            CopiarBytes(cursor, campos, 2);
                            modelo = func_80036164(*(u16*)campos_mem);
                            if (modelo == NULL) {
                                for (;;) {
                                }
                            }
                            enlace = (u8*)AllocListNode((u8*)D_80069644, 0xC, D_8006967E * 0xC);
                            if (enlace == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, enlace, 8) = modelo;
                            EN(u8*, entidad, 0x74) = (u8*)AppendListNode((NodoLista*)EN(u8*, entidad, 0x74), (NodoLista*)enlace);
                            cursor += 2;
                            break;
                        }
                        case 0x13: {
                            u32 modo;

                            CopiarBytes(cursor, campos, 1);
                            modo = campos_mem[0];
                            EN(u16, entidad, 0x2C) = modo;
                            if (modo == 1) {
                                D_80069640 = (s32*)(entidad + 0xE4);
                                EN(u16, entidad, 0x3C) = 0x40;
                                D_80069560 = entidad;
                                D_80069698 = (Objeto*)entidad;
                                EN(u16, entidad, 0x3E) = 0x3FFF;
                            }
                            cursor += 1;
                            break;
                        }
                        case 0x19:
                            CopiarBytes(cursor, campos, 4);
                            cursor += 4;
                            break;
                        case 0x30: {
                            u8* elemento;
                            u8* cabeza;

                            /* Elemento de 0x20 bytes que se encadena al final de la lista +0xF8 del entidad. */
                            CopiarBytes(cursor, campos, 0x20);
                            aux = campos;
                            cabeza = EN(u8*, entidad, 0xF8);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xF8) = monton;
                            }
                            monton += 0x20;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, elemento, 4) = *(u16*)aux;
                            EN(u16, elemento, 6) = *(u16*)(aux + 2);
                            EN(u16, elemento, 8) = *(u16*)(aux + 4);
                            EN(u16, elemento, 0xA) = *(u16*)(aux + 8);
                            EN(s32, elemento, 0xC) = *(s32*)(aux + 0xC);
                            EN(s32, elemento, 0x10) = *(s32*)(aux + 0x10);
                            EN(u16, elemento, 0x14) = *(u16*)(aux + 0x14);
                            EN(u16, elemento, 0x16) = *(u16*)(aux + 0x16);
                            EN(u16, elemento, 0x18) = *(u16*)(aux + 0x18);
                            EN(u16, elemento, 0x1A) = *(u16*)(aux + 0x1A);
                            EN(u16, elemento, 0x1C) = *(u16*)(aux + 0x1C);
                            cursor += 0x20;
                            break;
                        }
                        case 0x34: {
                            u8* elemento;
                            u8* cabeza;

                            /* Elemento de 0x1C bytes al final de la lista +0xF8 del entidad. */
                            CopiarBytes(cursor, campos, 0x18);
                            aux = campos;
                            cabeza = EN(u8*, entidad, 0xF8);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xF8) = monton;
                            }
                            monton += 0x1C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, elemento, 4) = *(u16*)aux;
                            EN(u16, elemento, 6) = *(u16*)(aux + 2);
                            EN(u16, elemento, 8) = *(u16*)(aux + 4);
                            EN(s32, elemento, 0xC) = *(s32*)(aux + 8);
                            EN(s32, elemento, 0x10) = *(s32*)(aux + 0xC);
                            EN(u16, elemento, 0xA) = *(u16*)(aux + 0x10);
                            EN(u16, elemento, 0x14) = *(u16*)(aux + 0x12);
                            EN(u16, elemento, 0x16) = *(u16*)(aux + 0x14);
                            EN(u16, elemento, 0x18) = *(u16*)(aux + 0x16);
                            cursor += 0x18;
                            break;
                        }
                        case 0x31: {
                            u8* elemento;
                            u8* cabeza;

                            /* Elemento de 0x24 bytes al final de la lista +0xFC del entidad. */
                            CopiarBytes(cursor, campos, 0x20);
                            aux = campos;
                            cabeza = EN(u8*, entidad, 0xFC);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xFC) = monton;
                            }
                            monton += 0x24;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, elemento, 4) = *(u16*)aux;
                            EN(u16, elemento, 6) = *(u16*)(aux + 2);
                            EN(s32, elemento, 8) = *(s32*)(aux + 4);
                            EN(s32, elemento, 0xC) = *(s32*)(aux + 8);
                            EN(u8, elemento, 0x10) = aux[0xC];
                            EN(u8, elemento, 0x13) = aux[0xF];
                            EN(u8, elemento, 0x11) = aux[0xD];
                            EN(u8, elemento, 0x12) = aux[0xE];
                            EN(u16, elemento, 0x14) = *(u16*)(aux + 0x10);
                            EN(u16, elemento, 0x16) = *(u16*)(aux + 0x12);
                            EN(s32, elemento, 0x18) = *(s32*)(aux + 0x14);
                            EN(s32, elemento, 0x1C) = *(s32*)(aux + 0x18);
                            EN(s32, elemento, 0x20) = *(s32*)(aux + 0x1C);
                            cursor += 0x20;
                            break;
                        }
                        case 0x35: {
                            u8* elemento;
                            u8* cabeza;

                            /* Elemento de 0x2C bytes al final de la lista +0xFC del entidad. */
                            CopiarBytes(cursor, campos, 0x28);
                            aux = campos;
                            cabeza = EN(u8*, entidad, 0xFC);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xFC) = monton;
                            }
                            monton += 0x2C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, elemento, 4) = *(u16*)aux;
                            EN(u16, elemento, 6) = *(u16*)(aux + 2);
                            EN(u16, elemento, 8) = *(u16*)(aux + 4);
                            EN(u16, elemento, 0xA) = *(u16*)(aux + 8);
                            EN(u16, elemento, 0xC) = *(u16*)(aux + 6);
                            EN(u8, elemento, 0xE) = aux[0xA];
                            EN(u8, elemento, 0x11) = aux[0xD];
                            EN(u8, elemento, 0xF) = aux[0xB];
                            EN(u8, elemento, 0x10) = aux[0xC];
                            EN(u16, elemento, 0x12) = *(u16*)(aux + 0xE);
                            EN(u16, elemento, 0x14) = *(u16*)(aux + 0x10);
                            EN(s32, elemento, 0x28) = *(s32*)(aux + 0x24);
                            EN(u16, elemento, 0x16) = *(u16*)(aux + 0x12);
                            EN(u16, elemento, 0x18) = *(u16*)(aux + 0x14);
                            EN(s32, elemento, 0x1C) = *(s32*)(aux + 0x18);
                            EN(s32, elemento, 0x20) = *(s32*)(aux + 0x1C);
                            EN(s32, elemento, 0x24) = *(s32*)(aux + 0x20);
                            cursor += 0x28;
                            break;
                        }
                        case 0x32: {
                            u8* elemento;
                            u8* cabeza;
                            s32 j;

                            /* Cinco referencias de 16 bits; el elemento (0x10 bytes) va a la lista +0xF4. */
                            CopiarBytes(cursor, campos, 0xC);
                            aux = campos;
                            cabeza = EN(u8*, entidad, 0xF4);
                            if (cabeza != NULL) {
                                elemento = cabeza;
                                while (*(u8**)elemento != NULL) {
                                    elemento = *(u8**)elemento;
                                }
                                *(u8**)elemento = monton;
                                elemento = monton;
                            } else {
                                elemento = monton;
                                *(u32*)elemento = 0;
                                EN(u8*, entidad, 0xF4) = elemento;
                            }
                            monton += 0x10;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, elemento, 4) = *(u16*)aux;
                            for (j = 0; j < 5; j++) {
                                EN(u16, elemento, 6 + j * 2) = *(u16*)(aux + 2 + j * 2);
                            }
                            cursor += 0xC;
                            break;
                        }
                        case 0x16:
                            CopiarBytes(cursor, campos, 8);
                            EN(s32, entidad, 8) = *(s32*)campos_mem;
                            EN(s32, entidad, 0xC) = *(s32*)(campos + 4);
                            if (EN(u8*, entidad, 0x74) != NULL
                                && (EN(u16, EN(u8*, EN(u8*, entidad, 0x74), 8), 0xA) & 0x180) != 0) {
                                EN(u32, entidad, 8) |= 0x200000;
                            }
                            cursor += 8;
                            break;
                        case 0x1A:
                            CopiarBytes(cursor, campos, 4);
                            EN(u16, entidad, 0x100) = *(u16*)campos_mem;
                            cursor += 4;
                            break;
                        case 0x17: {
                            /*
                             * Tabla de nueve enteros de la entidad: el original recorre dos punteros que
                             * avanzan (origen `campos` y destino con la base ya sumada, `addiu a0,s3,0x104` en
                             * 0x800441A8). Con el desplazamiento escrito dentro del indice el compilador deja
                             * la base sin sumar y lo pone en el almacen (0x104(v1)); con el puntero `tabla`
                             * como variable la base se suma antes del bucle.
                             */
                            u32* tabla;
                            CopiarBytes(cursor, campos, 0x24);
                            tabla = (u32*)(entidad + 0x104);
                            for (i = 0; i < 9; i++) {
                                tabla[i] = ((u32*)campos)[i];
                            }
                            cursor += 0x24;
                            break;
                        }
                        case 0x18:
                            /* Solo se copian 4 bytes, pero se leen 16 del bufer: lo restante es lo que dejo la etiqueta anterior. */
                            CopiarBytes(cursor, campos, 4);
                            EN(u8*, entidad, 0x118) = entidad + 0x128;
                            EN(u8, entidad, 0x128) = campos_mem[0];
                            EN(u8, entidad, 0x129) = campos[1];
                            EN(u16, entidad, 0x12A) = *(u16*)(campos + 4);
                            EN(u16, entidad, 0x12C) = *(u16*)(campos + 6);
                            aux = campos;
                            /* Los modelos de esta etiqueta van en s1, el mismo registro que el nodo de los demas chunks (0x8004422C). */
                            nodo = func_80036164(*(u32*)(aux + 8));
                            if (nodo == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, entidad, 0x130) = EN(u8*, nodo, 0x54);
                            nodo = func_80036164(*(u32*)(aux + 12));
                            if (nodo == NULL) {
                                for (;;) {
                                }
                            }
                            cursor += 0x10;
                            /* Orden del original (0x80044268 en adelante): `addiu` del cursor, carga de `nodo + 0x54`,
                             * almacen de la constante 2 en la espera de la carga y almacen del puntero. La
                             * constante delante de la carga hace que el planificador la emita antes. */
                            EN(u8*, entidad, 0x134) = EN(u8*, nodo, 0x54);
                            EN(s32, entidad, 4) = 2;
                            break;
                        case 0x1D:
                            CopiarBytes(cursor, campos, 4);
                            if (EN(u16, entidad, 0x2C) == 0xE || EN(u16, entidad, 0x2C) == 0x1F) {
                                EN(u16, entidad, 0x196) = *(u16*)campos_mem;
                            } else if (EN(u16, entidad, 0x2C) == 8) {
                                EN(u16, entidad, 0x160) = *(u16*)campos_mem;
                            } else {
                                EN(u16, entidad, 0x17C) = *(u16*)campos_mem;
                            }
                            cursor += 4;
                            break;
                        default:
                            break;
                        }
                    }
                    ResolverReferenciasContenedor((ContenedorCarga*)entidad);
                    break;

                default:
                    break;
                }
            } while (*cursor != 0x2E);
        fin_chunks:
            cursor++;
            break;
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
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", CargarContenedor);
#endif
