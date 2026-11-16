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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 335 con la configuracion versionada (g = 8 del archivo; ejes 17 de
 * operando, 0 reordenadas, 108 insertadas o borradas; el diff no muestra ninguna linea de un solo lado,
 * todas son diferencias de registro). Mismas instrucciones, mismo flujo y mismos huecos de retardo que
 * el ensamblador; difiere solo en el reparto de registros. El original deja en
 * las cinco variables del primer bucle (lista A, puntero a los campos, busqueda en B, fin de los
 * campos e identificador) v1, a0, a1, a2 y a3, y el identificador en a3 en todos los bucles de
 * busqueda; aqui salen v1 (busqueda), a0, a1 (lista A), a2 (identificador) y a3 (fin). Medido en
 * -dg: global-alloc asigna por prioridad floor_log2(R) * R / L y cada pseudo toma el primer registro
 * libre; el orden de aqui es la busqueda (28 usos sobre 10, 11,2), el puntero a los campos (20 sobre
 * 19, 4,21), el nodo de C (44 sobre 57, 3,86), el identificador (27 sobre 30, 3,60), la lista A (12
 * sobre 24, 1,5) y el fin (5 sobre 18, 0,56). Respecto del original son dos pares intercambiados: la
 * lista A y la busqueda (v1 y a1 en el original) y el fin y el identificador (a2 y a3); en los bucles
 * de B y de C el identificador tambien queda en a2 donde el original lo deja en a3, y el recorrido
 * exterior queda en a3 (B) y a1 (C) frente a a1 y a2 del original. Para dejar a1 a la busqueda y
 * a3 al identificador la lista A tendria que asignarse antes que la busqueda y el identificador al
 * final; se supone, sin
 * verificar, que el original los asigna asi, pero ninguna forma medida mueve esas prioridades en la
 * proporcion que pide (la lista A necesitaria una prioridad mayor que 11,2). Tambien difiere la
 * secuencia de la division por el tamano del nodo: el original deja el cociente en v0 y el producto
 * en v1, aqui al reves (el cociente es la local `idx`; sin ella, con la expresion directa, la
 * puntuacion sube a 2480). Medido ademas: el recorrido de la lista B (pseudo de 28 usos sobre 10) y el de la lista A
 * de los bucles de C (60 sobre 30, 10,0) se asignan antes que el puntero (4,21), de modo que la lista A (12 sobre 24,
 * 1,5) solo podria pasar delante con unos 56 usos ponderados (floor_log2(56) * 56 / 24 = 11,7); un identificador por
 * bucle (`id`, `id2`, `id3`) deja 335, y escribir el bucle de campos con un puntero `p = (u16*)a` y un fin `p + 5`
 * explicitos da 970 (el optimizador de bucles deja de reducir la direccion y anade tres instrucciones).
 *
 * El identificador se lee del campo dos veces: una en la prueba de la guarda y otra al guardarlo en
 * la variable. Medido en el ensamblador: el original carga el campo en v0, lo compara y despues lo
 * copia con `move a3,v0` en el hueco del salto de la busqueda; con una sola lectura copiada a la
 * variable antes de la prueba la carga cae directa en el registro del identificador y no hay
 * copia. El identificador es una variable de 32 bits aunque los campos que lee sean de 16 (con 16
 * bits la puntuacion es 1115). En los dos campos extra del nodo de C el original carga el valor
 * en a3 antes de la guarda de la lista A, y aqui tambien.
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
    NodoA* na;
    NodoB* nb;
    /* De 32 bits aunque los campos que lee sean de 16 (ver la cabecera). */
    s32 id;
    u32 i;
    s32 idx;
    u32 desp;

    if (c->clase == 0xE || c->clase == 2 || c->clase == 0x22) {
        for (a = c->listaA; a != NULL; a = a->sig) {
            for (i = 0; i < 5; i++) {
                if (a->ref[i] == 0xFFF0) {
                    break;
                }
                id = a->ref[i];
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
            if (b->refC != 0) {
                id = b->refC;
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
            if (k->refA != 0) {
                id = k->refA;
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
                id = k->refA1;
                for (na = c->listaA; na != NULL; na = na->sig) {
                    if (na->id == id) {
                        break;
                    }
                }
                if (na != NULL) {
                    idx = na - c->listaA;
                    k->refA1 = idx * 0x10;
                }
                id = k->refA2;
                for (na = c->listaA; na != NULL; na = na->sig) {
                    if (na->id == id) {
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
INCLUDE_ASM("asm/nonmatchings/cargador_de_niveles_y_cd", ResolverReferenciasContenedor);
#endif

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

#ifdef NON_MATCHING
/*
 * Pendiente: puntuacion 29937 con la configuracion versionada (g = 8 del archivo). La cifra incluye
 * palabras con direcciones absolutas dentro del archivo (saltos y tablas de saltos), de modo que
 * depende del tamano de las funciones anteriores y de cuantas instrucciones separan cada cuerpo de
 * caso del de su tabla. Medido: el codigo generado tiene 2958 instrucciones frente a 2955 del
 * original, y alineando el texto de ambos 2812 coinciden en el mnemonico (95,2 %) y 1923 son
 * identicas (65,1 %). Los cuerpos de los casos de los cinco `switch` y del despacho de primer nivel
 * van en el orden de direcciones de las tablas de saltos del original: el orden del fuente decide
 * el orden de emision, por eso los casos no van en orden numerico.
 *
 * Reparto de registros guardados (volcado de `cc1`, prioridad `floor_log2(R) * R / L` de
 * `global-alloc`): el cursor del script (R 1071, L 2041, prioridad 5,25) toma s1 y el nodo de los
 * chunks de recursos y modelos (R 340, L 522, 5,21) toma s2; el original guarda el nodo en s1 y el
 * cursor en s2. Se supone, sin verificar, que basta acortar la vida del nodo en unas 5 instrucciones
 * (hay 5 instrucciones de mas en los chunks 0x22 y 0x20) para que su prioridad supere la del
 * cursor, porque con 5,29 frente a 5,27 el reparto coincidia con el original en una medicion
 * intermedia. Siete variables de toda la funcion (compensacion, desp_bancos, tam_audio,
 * desp_texturas, hijo, hijo_matriz y monton) estan vivas desde la entrada de la funcion en el
 * volcado de `cc1` (se leen en algun camino sin asignacion previa), de modo que su longitud de vida
 * es de unas 2270 instrucciones y quedan en la pila; el original las guarda tambien en la pila (sw
 * a 0x1B0, 0x1D8 y 0x1DC del marco). La constante 0x2E de las pruebas de fin de chunk se iza a un
 * registro guardado (pseudo de R 68, L 2281, prioridad 0,18) y ocupa s8; el original no la iza y
 * conserva 39 `li ...,46` sueltos, aqui hay menos. Se supone, sin verificar, que el original guarda
 * en s7 una de esas variables de toda la funcion y el parametro `datos` en fp, y que por eso la
 * constante no llega a registro.
 *
 * Reserva de pila: el marco del original es de 0x210 bytes (`addiu sp` en 0x800415A0) y el del C sin
 * la local, de 0x208; la cifra medida sin la local es 31052 y con ella 29937.
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
    u8* campos;
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
    /* Desplazamiento leido de los campos de un chunk: el original lo guarda aparte del indice de seccion. */
    s32 desp_campo;
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
    EstadoPrincipal* estado;

    /* Memoria de trabajo del cargador: el destino recibe primero el contenido y luego la memoria libre. */
    campos = campos_mem;
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
        D_800694A4 = registro->tamano;
        D_800694A0 = registro->tamano;
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
        datos += 0xA000;
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
                            CopiarBytes(cursor, campos, 1);
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
                    do {
                        tipo = *cursor++;
                        if (tipo == 0x45) {
                            CopiarBytes(cursor, campos, 1);
                            destino_seccion = (u8*)D_80067E98[campos_mem[0]];
                            D_800694A0 = secciones[posicion].alineado;
                            D_80069484 = 0;
                            D_80069498 = (u32)destino_seccion;
                            IniciarLecturaContinua((CdlLOC*)D_8006A928);
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
        IniciarLecturaContinua((CdlLOC*)D_8006A928);
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
        switch (orden) {
        case 0x2C:
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
                D_8006959C = (u32)libre;
                libre += D_8006954C;
            }
            for (i = 0; i < 3; i++) {
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
            monton = libre;
            D_80069538 = monton;
            libre = monton + D_80069548;
            D_800694B8 = libre;
            libre += (s16)D_8006952E * 8;
            D_80076188 = D_8006959C;
            D_80069680 = D_8006959C;
            D_8006958C = D_8006959C - 0x400 + D_8006954C;
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
            compensacion = func_80040F78(secciones, n_secciones, 4);
            datos = libre;
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
            IniciarLecturaContinua((CdlLOC*)D_8006A928);
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
                            /* El modelo se usa solo hasta la llamada: un temporal propio, no `aux`. */
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
                            lista = (u8*)AllocListNode((u8*)D_80069570, 0x14, D_80069670 * 0x14);
                            if (lista == NULL) {
                                for (;;) {
                                }
                            }
                            EN(u8*, nodo, 0x54) = lista;
                            desp_campo = *(s32*)campos_mem;
                            D_800694A0 = *(s32*)(campos + 4);
                            EN(u8*, lista, 8) = datos + desp_campo;
                            EN(u16, nodo, 0xA) = 4;
                            cab = EN(u8*, lista, 8);
                            EN(u8*, lista, 8) = cab + 4;
                            EN(u16, lista, 0x12) = EN(u16, cab, 2) >> 1;
                            EN(u8*, lista, 8) = cab + 8;
                            EN(u16, lista, 0xE) = EN(u16, cab, 4);
                            cursor += 8;
                            EN(u16, lista, 0x10) = EN(u16, cab + 8, 4);
                            break;
                        }
                        case 0x3F:
                            CopiarBytes(cursor, campos, 0xC);
                            desp_campo = *(s32*)(campos + 4);
                            compensacion = *(s32*)(campos + 8);
                            EN(u16, nodo, 0xA) = 1;
                            EN(u8*, nodo, 0x54) = datos + desp_campo;
                            EN(u16, nodo, 0x50) = *(u16*)campos_mem;
                            cursor += 0xC;
                            D_800694A0 = compensacion;
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
                    do {
                        etiqueta = *cursor++;
                        switch (etiqueta) {
                        case 0x24:
                            CopiarBytes(cursor, campos, 8);
                            desp_campo = *(s32*)campos_mem;
                            EN(u16, nodo, 0xA) = 2;
                            aux = datos + desp_campo + 4;
                            D_800694A0 = *(s32*)(campos + 4);
                            EN(u8*, nodo, 0x54) = aux;
                            GsMapModelingData((unsigned long*)aux);
                            cursor += 8;
                            EN(u8*, nodo, 0x54) += 8;
                            break;
                        case 0x21:
                            CopiarBytes(cursor, campos, 4);
                            cursor += 4;
                            EN(u16, nodo, 0x4E) = 0;
                            EN(s32, nodo, 0xC) = *(u16*)campos_mem;
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
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0) = *(s32*)campos_mem;
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 4) = *(s32*)campos_mem;
                            EN(s32, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 8) = *(s32*)campos_mem;
                            cursor += 0xC;
                            ScaleMatrix((MATRIX*)(EN(u8*, hijo_matriz, 4) + 4),
                                        (VECTOR*)EN(u8*, EN(u8*, hijo_matriz, 4), 0x44));
                            break;
                        case 0x11:
                            CopiarBytes(cursor, campos, 6);
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
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x10) = *(u16*)campos_mem;
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x12) = *(u16*)(campos + 2);
                            EN(u16, EN(u8*, EN(u8*, hijo_matriz, 4), 0x44), 0x14) = *(u16*)(campos + 4);
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
                    do {
                        etiqueta = *cursor++;
                        switch (etiqueta) {
                        case 0x01:
                            CopiarBytes(cursor, campos, 8);
                            cursor += 8;
                            audio_cargado = 1;
                            tam_audio = *(s32*)campos_mem;
                            libre += *(s32*)(campos + 4);
                            D_800694A0 = *(s32*)(campos + 4);
                            break;
                        case 0x02:
                            CopiarBytes(cursor, campos, 8);
                            desp_campo = *(s32*)campos_mem;
                            D_8006951C = 0x1010;
                            D_800694A0 = *(s32*)(campos + 4);
                            func_8003ECD4(datos + desp_campo, *(s32*)(campos + 4));
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
                            aux = datos + desp_texturas;
                            D_800694EC = aux;
                            D_80069598 = (u32*)aux;
                            D_800695FC = (s16*)(aux + 8);
                            cursor += 0x30;
                            D_800694EC = aux + *(s32*)aux;
                            D_80069598 = (u32*)(aux + *(s32*)(aux + 4));
                            libre += D_800694A0;
                            break;
                        case 0x4D:
                            CopiarBytes(cursor, campos, 0x30);
                            /* Igual que en 0x4C: el almacen del original (0x80042E8C) solo sigue a una coincidencia. */
                            if (D_80010050 == 0) {
                                desp_bancos = *(s32*)campos_mem;
                                D_800694A0 = *(s32*)(campos + 4);
                            } else if (D_80010050 == 1) {
                                desp_bancos = *(s32*)(campos + 8);
                                D_800694A0 = *(s32*)(campos + 12);
                            } else if (D_80010050 == 2) {
                                desp_bancos = *(s32*)(campos + 16);
                                D_800694A0 = *(s32*)(campos + 20);
                            } else if (D_80010050 == 3) {
                                desp_bancos = *(s32*)(campos + 24);
                                D_800694A0 = *(s32*)(campos + 28);
                            } else if (D_80010050 == 4) {
                                desp_bancos = *(s32*)(campos + 32);
                                D_800694A0 = *(s32*)(campos + 36);
                            } else if (D_80010050 == 5) {
                                desp_bancos = *(s32*)(campos + 40);
                                D_800694A0 = *(s32*)(campos + 44);
                            }
                            D_800695E4 = D_8006951C;
                            func_8003ECD4(datos + desp_bancos, D_800694A0);
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
                            D_800694A0 = *(s32*)(campos + 4);
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
                            D_800694A0 = *(s32*)(campos + 4);
                            D_8001004F = 1;
                            D_800695B0 = (u16*)(datos + desp_campo);
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
                        switch (etiqueta) {
                        case 0x3C:
                            CopiarBytes(cursor, campos, 4);
                            D_800695B4 = campos[2];
                            D_8006960C = *(s16*)campos_mem;
                            D_80069530 = campos[3];
                            cursor += 4;
                            break;
                        case 0x3E:
                            CopiarBytes(cursor, campos, 0x1C);
                            pools_listos = 1;
                            D_80069660 = *(u16*)(campos + 2);
                            D_80069670 = *(u16*)campos_mem;
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
                            D_800694B0 = *(s16*)campos_mem / 4;
                            D_800695F2 = *(s16*)(campos + 2) / 4;
                            D_800695F4 = *(s16*)(campos + 4) / 4;
                            cursor += 6;
                            D_8006969C = D_800694B0 - 0x80;
                            break;
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
                    do {
                        etiqueta = *cursor++;
                        switch (etiqueta) {
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
                        case 0x33:
                            /* Elemento de 0x24 bytes al final de la lista +0x30 del volumen. */
                            CopiarBytes(cursor, campos, 0x20);
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
                            EN(s32, aux, 4) = *(s32*)campos_mem;
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
                    do {
                        etiqueta = *cursor++;
                        switch (etiqueta) {
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
                                aux = campos;
                                do {
                                    *(u16*)(EN(u8*, entidad, 0x178) + i * 2) = *(u16*)aux;
                                    aux += 2;
                                    i++;
                                } while (*(u16*)aux != 0);
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
                            EN(s32, entidad, 0x30) = (s16)EN(u16, entidad, 0x2E) * (s16)EN(u16, entidad, 0x2E);
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
                        case 0x0F:
                            CopiarBytes(cursor, campos, 2);
                            modelo = func_80036164(*(u16*)campos_mem);
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
                            EN(u8*, entidad, 0x74) = (u8*)AppendListNode((NodoLista*)EN(u8*, entidad, 0x74), (NodoLista*)aux);
                            cursor += 2;
                            break;
                        case 0x13:
                            CopiarBytes(cursor, campos, 1);
                            EN(u16, entidad, 0x2C) = campos_mem[0];
                            if (campos_mem[0] == 1) {
                                D_80069640 = (s32*)(entidad + 0xE4);
                                EN(u16, entidad, 0x3C) = 0x40;
                                D_80069560 = entidad;
                                D_80069698 = (Objeto*)entidad;
                                EN(u16, entidad, 0x3E) = 0x3FFF;
                            }
                            cursor += 1;
                            break;
                        case 0x19:
                            CopiarBytes(cursor, campos, 4);
                            cursor += 4;
                            break;
                        case 0x30:
                            /* Elemento de 0x20 bytes que se encadena al final de la lista +0xF8 del entidad. */
                            CopiarBytes(cursor, campos, 0x20);
                            aux = EN(u8*, entidad, 0xF8);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xF8) = monton;
                            }
                            monton += 0x20;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos_mem;
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
                        case 0x34:
                            /* Elemento de 0x1C bytes al final de la lista +0xF8 del entidad. */
                            CopiarBytes(cursor, campos, 0x18);
                            aux = EN(u8*, entidad, 0xF8);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xF8) = monton;
                            }
                            monton += 0x1C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos_mem;
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
                        case 0x31:
                            /* Elemento de 0x24 bytes al final de la lista +0xFC del entidad. */
                            CopiarBytes(cursor, campos, 0x20);
                            aux = EN(u8*, entidad, 0xFC);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xFC) = monton;
                            }
                            monton += 0x24;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos_mem;
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
                        case 0x35:
                            /* Elemento de 0x2C bytes al final de la lista +0xFC del entidad. */
                            CopiarBytes(cursor, campos, 0x28);
                            aux = EN(u8*, entidad, 0xFC);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)monton = 0;
                                EN(u8*, entidad, 0xFC) = monton;
                            }
                            monton += 0x2C;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos_mem;
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
                        case 0x32:
                            /* Cinco referencias de 16 bits; el elemento (0x10 bytes) va a la lista +0xF4. */
                            CopiarBytes(cursor, campos, 0xC);
                            aux = EN(u8*, entidad, 0xF4);
                            if (aux != NULL) {
                                while (*(u8**)aux != NULL) {
                                    aux = *(u8**)aux;
                                }
                                *(u8**)aux = monton;
                                aux = monton;
                            } else {
                                aux = monton;
                                *(u32*)aux = 0;
                                EN(u8*, entidad, 0xF4) = aux;
                            }
                            monton += 0x10;
                            if (monton - D_80069538 >= D_80069548) {
                                for (;;) {
                                }
                            }
                            EN(u16, aux, 4) = *(u16*)campos_mem;
                            for (i = 0; i < 5; i++) {
                                EN(u16, aux, 6 + i * 2) = *(u16*)(campos + 2 + i * 2);
                            }
                            cursor += 0xC;
                            break;
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
                        case 0x17:
                            CopiarBytes(cursor, campos, 0x24);
                            for (i = 0; i < 9; i++) {
                                EN(u32, entidad, 0x104 + i * 4) = ((u32*)campos)[i];
                            }
                            cursor += 0x24;
                            break;
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
                            EN(s32, entidad, 4) = 2;
                            EN(u8*, entidad, 0x134) = EN(u8*, nodo, 0x54);
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
                    } while (*cursor != 0x2E);
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
