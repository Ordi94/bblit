#include "common.h"
#include "globales.h"
#include "gte.h"

/*
 * Estado del fundido de pantalla (todas las variables son datos pequenos que el original
 * direcciona con lui + desplazamiento y escribe con lui at, de ahi g = 8 para este archivo).
 * D_80069566: nivel actual del fundido, en 1/4096. D_80069668: nivel complementario que usa el
 * dibujo. D_80069686: paso por cuadro. D_8006966A: banderas de fase (ver func_8003ABB4).
 */
extern s16 D_80069566;
extern s16 D_80069668;
extern u16 D_80069686;

/*
 * Anillo de marcas de tiempo de los cuadros (los mismos datos que usa la presentacion de cuadros):
 * D_80069610 la reescribe el retorno de llamada de VSync, D_800695A6 cuenta los VSync desde el
 * ultimo dibujo y D_8006954C es la longitud del anillo.
 */
extern s32 D_8006954C;
extern u32 D_80069610;
extern u32 D_80069614;
extern vu16 D_800695A6;

/*
 * Cursor de escritura de primitivas GPU: direccion de la siguiente primitiva libre del cuadro. Se
 * compara con signo contra los limites del contexto, por eso es s32 y no un puntero.
 */
extern s32 D_80076188;
extern void func_80039CD0(s32 cursor);

/* Entrada de D_8006A940: sala o modelo visible con su bandera (12 bytes por entrada). */
typedef struct EntradaVisible {
    s16 modelo;
    u16 bandera;
    u8 pad04[8];
} EntradaVisible;

/*
 * Entrada de la lista de dibujo de modelos (D_8006A940, 12 bytes por entrada) y argumento de
 * func_8003B26C: indice del modelo, nivel de profundidad y grupo. Los accesos de func_8003B26C
 * leen los dos ultimos campos como bytes (lbu).
 */
typedef struct PedidoModelo {
    s16 modelo;
    s16 profundidad;
    u16 grupo;
} PedidoModelo;

/*
 * Modelo de la tabla D_8006B568 y elemento de las cadenas de dibujo de func_8003C014: enlace al
 * siguiente en +0, banderas en +8 y +0xC, geometria en +0x10, un byte de visibilidad en +0xB4 y
 * un byte de estado en +0xB5.
 */
typedef struct ModeloDibujo {
    struct ModeloDibujo* siguiente;
    u8 pad04[4];
    u16 banderas;
    u8 pad0A[2];
    u32 modo;
    void* geometria;
    u8 pad14[0xB4 - 0x14];
    s8 visible;
    u8 estado;
} ModeloDibujo;

/*
 * Objeto de escena visto por las rutinas de dibujo (la misma memoria que Objeto): banderas en +4,
 * +8 y +0xC, identificadores en +0x26..+0x3E, el nodo de jerarquia empotrado en +0x7C, un
 * contador en +0xC4, la profundidad en +0xD4 y la posicion en +0xE4..+0xEC.
 */
typedef struct ObjetoEscena {
    u8 pad00[0x04];
    u32 flags04;
    u32 flags08;
    u32 flags0C;
    u8 pad10[0x26 - 0x10];
    u16 w26;
    u16 w28;
    u8 pad2A[2];
    u16 w2C;
    u8 pad2E[0x3C - 0x2E];
    u16 w3C;
    u16 w3E;
    u8 pad40[0x7C - 0x40];
    u8 nodo[4];
    u8 pad80[0xC4 - 0x80];
    s32 iC4;
    u8 padC8[0xD4 - 0xC8];
    s32 iD4;
    u8 padD8[0xE4 - 0xD8];
    s32 xE4;
    s32 yE8;
    s32 zEC;
} ObjetoEscena;

/* Pila de func_8003AF8C para func_8001CE64: puntero al nodo, vector de entrada y acumulador (E-07). */
typedef struct PilaNodo {
    void* nodo;
    SVECTOR v;
    VECTOR acc;
} PilaNodo;

/* Resultado de func_8001DF28: color base del sprite proyectado y desplazamiento de su textura. */
typedef struct ColorYDesplazamiento {
    u32 color;
    s32 desplazamiento;
} ColorYDesplazamiento;

/*
 * Sprite de cuatro vertices que func_8003AF8C emite como POLY_FT4: +8 banderas (bit 4 = fijo),
 * +0xC..+0x28 las ocho palabras de vertices y coordenadas de textura, +0x2C = semitransparente.
 */
typedef struct SpriteDibujo {
    u8 pad00[0x08];
    u16 banderas;
    u8 pad0A[2];
    u32 palabras[8];
    u32 semitransparente;
} SpriteDibujo;

/* Vista que reciben las rutinas de dibujo: +4 desplazamiento, +0xC y +0xE limites de profundidad. */
typedef struct VistaDibujo {
    u8 pad00[0x04];
    s16 s4;
    u8 pad06[0x0C - 0x06];
    u16 w0C;
    u16 w0E;
} VistaDibujo;


/* Vertice de la caja que func_8003DD70 prueba contra la pantalla: x en +8, y en +0xA, 12 bytes. */
typedef struct VerticeCaja {
    u8 pad00[8];
    s16 x;
    s16 y;
} VerticeCaja;

/* Semi-ancho y semi-alto de la ventana de recorte (+4 y +6). */
typedef struct LimitesPantalla {
    u8 pad00[4];
    s16 x;
    s16 y;
} LimitesPantalla;

extern ModeloDibujo* D_8006B568[];
extern u16 D_8006969C;
extern u16 D_800694B0;
extern u8 D_80069600;
extern s32 func_80010258(void* modelo, s32 cursor, void* vista, void* estado);
extern s16 D_800695DA;
extern void* D_800695C4;
extern u8 D_8006D1C8[];
extern EntradaVisible D_8006A940[];
extern s16 D_80069588;
extern s16 D_80069688;
extern u16 D_800694E2;
extern void func_8001CE64(void* pila);
extern ColorYDesplazamiento* func_8001DF28(void* objeto, void* vista);
extern s32 func_8003760C(void* geometria, void* vista, void* vista_siguiente);
extern void func_8003753C(void* vista);
extern s32 func_80010204(void* modelo, s32 cursor, void* estado, void* vista);
extern void func_8003C1C8(void* vista);

/*
 * Contexto de dibujo de la escena. +4..+6: bytes de estado que se pasan al dibujador de modelos
 * (func_8003B26C y func_8003B354); +8: profundidad del objeto (func_8003AF8C) que func_8003D880 resta del indice; +0xA: desplazamiento
 * de profundidad; +0xC: indice de la lista de ordenacion; +0x1C/+0x20/+0x24: bases de las tres
 * listas de ordenacion, de resolucion decreciente; +0x28: entrada elegida; +0x2C/+0x30: inicio
 * y limite del buffer de primitivas; +0x34: objeto que fija la sala visible.
 */
typedef struct ContextoDibujo {
    u8 pad00[0x04];
    u8 b4;
    u8 b5;
    u8 b6;
    u8 pad07;
    s16 profundidad;
    s16 desplazamiento;
    s32 indice;
    u8 pad10[0x1C - 0x10];
    u32* ot0;
    u32* ot1;
    u32* ot2;
    u32* destino;
    s32 inicio;
    s32 limite;
    ObjetoEscena* objeto;
} ContextoDibujo;

void func_8003AA38(void)
{
}

void func_8003AA40(void)
{
}

void func_8003AA48(void)
{
}

void func_8003AA50(u8 modo, u16 duracion)
{
    D_8006966A = modo;
    D_80069686 = duracion;
    D_80069566 = 0;
    D_80069668 = 0x1000;
}

void func_8003AA7C(u8 modo, u16 duracion)
{
    D_8006966A = modo;
    D_80069686 = duracion;
    D_80069566 = 0x1000;
    D_80069668 = 0;
}

void func_8003AAA8(void)
{
    u16 actual;
    u8 fase;

    actual = D_80069566;
    if (D_80069566 >= 0x1000) {
        fase = D_8006966A;
        D_80069566 = 0x1000;
        D_80069668 = 0;
        if (fase & 0x40) {
            D_8006966A = (fase & 0xFE) | 2;
        } else {
            D_8006966A = 0x10;
        }
    } else {
        D_80069668 = 0x1000 - actual;
        D_80069566 = actual + D_80069686;
    }
}

void func_8003AB3C(void)
{
    u16 actual;
    u8 fase;

    actual = D_80069566;
    if (D_80069566 <= 0) {
        fase = D_8006966A;
        D_80069566 = 0;
        D_80069668 = 0x1000;
        if (fase & 0x40) {
            D_8006966A = 0x20;
        }
    } else {
        D_80069668 = 0x1000 - actual;
        D_80069566 = actual - D_80069686;
    }
}

void func_8003ABB4(void)
{
    u8 fase;

    fase = D_8006966A;
    if (D_8006966A != 0) {
        if (fase & 4) {
            func_8003AA50(1, 0x100);
        } else if (fase & 8) {
            func_8003AA7C(2, 0x100);
        } else if (D_8006AA70[0x19] == 0) {
            if (fase & 2) {
                func_8003AB3C();
            } else if (fase & 1) {
                func_8003AAA8();
            }
        }
        if (D_8006966A & 0x30) {
            D_8006966A = 0;
            D_80069668 = 0;
        }
    } else if (D_8006AA70[0xC] != 0) {
        D_80069668 = 0xE00;
    } else {
        D_80069668 = 0;
    }
}

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003ACA8);

/* Pendiente: puntuacion 1245 con la configuracion versionada (g = 8 del archivo). El cursor de primitivas se carga antes que en el original y los registros t0/t1/a1/v1 se reparten distinto; la estructura de las dos primitivas de 6 palabras coincide. Variantes probadas: 14 (orden de las 6 escrituras, 720 permutaciones del primer bloque, macro sobre D_80076188, estructura de paquete). */
#ifdef NON_MATCHING
s32 func_8003AE08(u32* puntos, ContextoDibujo* ctx)
{
    u32* tabla;
    s32 actual;
    s32 siguiente;

    func_80039CD0(D_80076188);
    tabla = (u32*)D_8006AEA0[D_8006967C].org;
    actual = D_80076188;
    ((u32*)actual)[0] = *tabla | 0x05000000;
    ((u32*)actual)[2] = 0x80000000;
    ((u32*)actual)[1] = 1;
    ((u32*)actual)[3] = puntos[3];
    ((u32*)actual)[4] = puntos[5];
    ((u32*)actual)[5] = puntos[7];
    *tabla = (actual << 8) >> 8;
    actual = D_80076188;
    siguiente = actual + 0x18;
    D_80076188 = siguiente;
    if (puntos[8] != 0) {
        tabla = (u32*)D_8006AEA0[D_8006967C].org;
        ((u32*)actual)[6] = *tabla | 0x05000000;
        ((u32*)siguiente)[1] = 1;
        ((u32*)siguiente)[2] = 0x80000000;
        ((u32*)siguiente)[3] = puntos[4];
        ((u32*)siguiente)[4] = puntos[6];
        ((u32*)siguiente)[5] = puntos[8];
        *tabla = (siguiente << 8) >> 8;
        D_80076188 += 0x18;
    }
    if (ctx->limite < D_80076188) {
        D_80076188 = ctx->inicio;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003AE08);
#endif

/* Pendiente: puntuacion 1680 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y flujo; difiere el reparto de registros (el desplazamiento de la textura cae en a0 y la plantilla en v1, en lugar de a2 y a0) y la posicion del almacen de la profundidad, que el original deja justo antes de indexar la lista de ordenacion. Variantes probadas: 160 (forma de la plantilla, orden de declaracion de los locales, acumulacion del color). */
#ifdef NON_MATCHING
void func_8003AF8C(SpriteDibujo* sprite, ContextoDibujo* ctx, u8* vista)
{
    u32 color;
    s32 desplazamiento;
    s32 k;
    ColorYDesplazamiento* par;
    PilaNodo pila;
    u32* p;
    u32* q;
    u32* orden;
    u32* ranura;
    u32 palabra;
    u32 modo;
    s32 n;

    func_80039CD0(D_80076188);
    if (sprite->banderas & 0x10) {
        if (D_8006966A != 0) {
            k = 0x80 - ((s16)D_800694E2 >> 5);
            color = (k << 16) + (k << 8) + k;
        } else {
            color = 0x808080;
        }
        desplazamiento = 0;
        ctx->profundidad = 0;
    } else {
        if (ctx->objeto->iC4 != 0) {
            pila.nodo = ctx->objeto->nodo;
            func_8001CE64(&pila);
            ctx->objeto->xE4 = pila.acc.vx;
            ctx->objeto->yE8 = pila.acc.vy;
            ctx->objeto->zEC = pila.acc.vz;
        }
        par = func_8001DF28(ctx->objeto, vista);
        color = par->color;
        desplazamiento = par->desplazamiento;
        ctx->profundidad = (ctx->objeto->iD4 >> 2) - ctx->desplazamiento;
    }
    if ((ctx->objeto->flags04 & 2) && color != 0 && ctx->profundidad >= 0) {
        q = sprite->palabras;
        p = (u32*)D_80076188;
        p[2] = sprite->palabras[0];
        p[3] = q[1] + desplazamiento;
        p[4] = q[2];
        p[5] = q[3];
        p[6] = q[4];
        p[7] = q[5];
        p[8] = q[6];
        p[9] = q[7];
        if (ctx->profundidad < 0x200) {
            orden = (u32*)D_8006AE20[D_8006967C].org;
        } else {
            if (ctx->profundidad < 0x400) {
                n = (s16)((u16)ctx->profundidad - 0x200) >> 1;
                orden = (u32*)D_8006AE60[D_8006967C].org;
            } else {
                n = (s16)((u16)ctx->profundidad - 0x400) >> 5;
                orden = (u32*)D_8006AEA0[D_8006967C].org;
            }
            ctx->profundidad = n;
        }
        ranura = orden + ctx->profundidad;
        palabra = *ranura | 0x09000000;
        if (sprite->semitransparente != 0) {
            modo = 0x2E000000;
        } else {
            modo = 0x2C000000;
        }
        color |= modo;
        color |= 0x2C000000;
        p[0] = palabra;
        p[1] = color;
        *ranura = (s32)((s32)p << 8) >> 8;
        D_80076188 += 0x28;
        if (ctx->limite < D_80076188) {
            D_80076188 = ctx->inicio;
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003AF8C);
#endif

void func_8003B26C(PedidoModelo* pedido, ContextoDibujo* escena, u8* vista)
{
    ModeloDibujo* modelo;

    modelo = D_8006B568[pedido->modelo];
    if (func_8003760C(modelo->geometria, vista, vista + 0x20) != 0) {
        func_8003753C(vista);
        escena->b4 = (u8)pedido->grupo;
        escena->b5 = modelo->estado;
        escena->b6 = (u8)pedido->profundidad + 1;
        D_800695DA = 0;
        D_800695C4 = D_8006D1C8;
        D_80076188 = func_80010204(modelo, D_80076188, &escena->b4, vista);
        if (D_800695DA != 0) {
            func_8003C1C8(vista);
        }
    }
}

/* Pendiente: puntuacion 485 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; solo difiere el reparto de v0/v1/a0 en la comparacion del numero de salas (la constante 0x10000 se carga antes del almacen de la profundidad) y en el puntero de la entrada visible. Variantes probadas: 60 (forma de la comparacion con shifts, orden de las escrituras previas al bucle, indexado frente a aritmetica de punteros, orden del cierre de la lista). */
#ifdef NON_MATCHING
void func_8003B354(ModeloDibujo* modelo, ContextoDibujo* escena, u8* vista)
{
    PedidoModelo pedido;
    s16 actual;
    u16 cuenta;
    u16 anterior;
    EntradaVisible* entrada;

    D_800695C4 = D_8006D1C8;
    D_800695DA = 0;
    escena->b4 = 0;
    escena->b6 = 1;
    escena->b5 = 1;
    func_8003753C((u8*)modelo + 0x94);
    D_80076188 = func_80010204(modelo, D_80076188, &escena->b4, vista);
    if (D_800695DA != 0) {
        func_8003C1C8(vista);
    }
    D_80069688 = escena->objeto->w26;
    actual = -1;
    if (!(D_8006D9A8[0] & 0x300)) {
        actual = D_80069698->w26;
        if (actual != (s16)escena->objeto->w26 && actual != -1) {
            pedido.profundidad = 0;
            pedido.grupo = 0;
            pedido.modelo = actual;
            func_8003B26C(&pedido, escena, vista);
            D_8006A940[0].modelo = actual;
        }
    }
    cuenta = D_80069588;
    pedido.grupo = 1;
    escena->desplazamiento = -0x80;
    pedido.profundidad = 1;
    if ((cuenta << 16) > 0x10000) {
        do {
            if (pedido.profundidad == (s16)cuenta) {
                pedido.grupo++;
                cuenta = D_80069588;
            }
            entrada = &D_8006A940[pedido.profundidad];
            if (!(entrada->bandera & 1) && entrada->modelo != actual) {
                pedido.modelo = entrada->modelo;
                func_8003B26C(&pedido, escena, vista);
            }
            pedido.profundidad++;
        } while (pedido.profundidad < D_80069588);
    }
    anterior = D_80069688;
    if (actual != D_80069688) {
        entrada = &D_8006A940[D_80069588];
        D_80069588 += 1;
        entrada->bandera = 0;
        entrada->modelo = anterior;
    }
    escena->b4 = 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B354);
#endif

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B5AC);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003BDD0);

void func_8003C014(ObjetoEscena* entidad, ModeloDibujo* lista, VistaDibujo* vista, void* estado)
{
    vista->w0C = D_8006969C;
    if (entidad->w3C & 2) {
        vista->w0E = entidad->w3E;
    } else {
        vista->w0E = D_800694B0;
    }
    if (entidad->flags0C & 0x02000000) {
        vista->s4 = entidad->w28 - 0x80;
        if (D_800694B0 < vista->w0E) {
            vista->w0E = D_800694B0;
        }
        if (entidad->w2C == 9 || (entidad->flags0C & 0x20000000)) {
            D_80069600 = 1;
            vista->w0C = 0x3FFF;
            vista->w0E = 0x3FFF;
        }
    }
    if (lista != NULL) {
        do {
            if ((lista->banderas & 6) && lista->visible != 0) {
                if (entidad->flags08 & 0x40) {
                    lista->modo = 0x40000000;
                } else {
                    lista->modo = 0;
                }
                if (entidad->flags0C & 0x02000000) {
                    D_800695DA = 0;
                    D_800695C4 = D_8006D1C8;
                    D_80076188 = func_80010204(lista, D_80076188, vista, estado);
                } else {
                    D_80076188 = func_80010258(lista, D_80076188, vista, estado);
                }
            }
            lista = lista->siguiente;
        } while (lista != NULL);
    }
}

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003C1C8);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003CA5C);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D0D4);

s32 func_8003D7C4(void)
{
    s32 z[3];
    s32 mayor;

    gte_stsz3c(z);
    mayor = z[0];
    if (mayor < z[1]) {
        mayor = z[1];
    }
    if (mayor < z[2]) {
        mayor = z[2];
    }
    return mayor >> 2;
}

s32 func_8003D814(void)
{
    s32 z[4];
    s32 mayor;

    gte_stsz4c(z);
    mayor = z[0];
    if (mayor < z[1]) {
        mayor = z[1];
    }
    if (mayor < z[2]) {
        mayor = z[2];
    }
    if (mayor < z[3]) {
        mayor = z[3];
    }
    return mayor >> 2;
}

void func_8003D880(ContextoDibujo* ctx)
{
    s32 n;
    s32 m;

    if (ctx->indice < ctx->profundidad) {
        ctx->indice = 0;
    } else {
        ctx->indice = ctx->indice - ctx->profundidad;
    }
    n = ctx->indice;
    if (n < 0x200) {
        ctx->destino = ctx->ot0 + n;
    } else if (n < 0x400) {
        m = n - 0x200;
        ctx->indice = m;
        ctx->destino = ctx->ot1 + (m >> 1);
    } else {
        m = n - 0x400;
        ctx->indice = m;
        ctx->destino = ctx->ot2 + (m >> 5);
    }
}

void func_8003D904(u8* dest, u8* a, u8* b)
{
    ((s16*)dest)[0] = (((s16*)a)[0] + ((s16*)b)[0]) >> 1;
    ((s16*)dest)[1] = (((s16*)a)[1] + ((s16*)b)[1]) >> 1;
    ((s16*)dest)[2] = (((s16*)a)[2] + ((s16*)b)[2]) >> 1;
    dest[6] = (a[6] + b[6]) >> 1;
    dest[7] = (a[7] + b[7]) >> 1;
    ((s32*)dest)[2] = ((s32*)a)[2];
}

void func_8003D988(u8* dest, u8* a, u8* b)
{
    ((s16*)dest)[0] = (((s16*)a)[0] + ((s16*)b)[0]) >> 1;
    ((s16*)dest)[1] = (((s16*)a)[1] + ((s16*)b)[1]) >> 1;
    ((s16*)dest)[2] = (((s16*)a)[2] + ((s16*)b)[2]) >> 1;
    dest[6] = (a[6] + b[6]) >> 1;
    dest[7] = (a[7] + b[7]) >> 1;
    dest[8] = (a[8] + b[8]) >> 1;
    dest[9] = (a[9] + b[9]) >> 1;
    dest[10] = (a[10] + b[10]) >> 1;
}

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003DA4C);

s32 func_8003DD70(VerticeCaja* v, LimitesPantalla* lim)
{
    u16 min;
    u16 max;

    if (v[0].x > v[1].x) {
        max = v[0].x;
        min = v[1].x;
    } else {
        min = v[0].x;
        max = v[1].x;
    }
    if ((s16)max < v[2].x) {
        max = v[2].x;
    } else if (v[2].x < (s16)min) {
        min = v[2].x;
    }
    if ((s16)max < v[3].x) {
        max = v[3].x;
    } else if (v[3].x < (s16)min) {
        min = v[3].x;
    }
    if ((s16)min > lim->x || (s16)max < -lim->x) {
        return 1;
    }
    if (v[0].y > v[1].y) {
        max = v[0].y;
        min = v[1].y;
    } else {
        min = v[0].y;
        max = v[1].y;
    }
    if ((s16)max < v[2].y) {
        max = v[2].y;
    } else if (v[2].y < (s16)min) {
        min = v[2].y;
    }
    if ((s16)max < v[3].y) {
        max = v[3].y;
    } else if (v[3].y < (s16)min) {
        min = v[3].y;
    }
    if ((s16)min > lim->y || (s16)max < -lim->y) {
        return 1;
    }
    return 0;
}

void func_8003DF10(s32 limite)
{
    s32 anillo;
    u32 reinicio;
    s32 libre;

    anillo = D_8006954C;
    reinicio = D_80069614;
    while (1) {
        libre = D_80069610 - limite;
        if (libre < 0) {
            libre -= 0x400;
            libre += anillo;
        }
        if (libre >= 0x800) {
            return;
        }
        if ((s16)D_800695A6 >= 4) {
            D_80069610 = reinicio;
        }
    }
}
