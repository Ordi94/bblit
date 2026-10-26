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

/* Modelo de la tabla D_8006B568: solo se leen +0x10 (geometria) y +0xB5 (byte de estado). */
typedef struct ModeloDibujo {
    u8 pad00[0x10];
    void* geometria;
    u8 pad14[0xB5 - 0x14];
    u8 estado;
} ModeloDibujo;


extern ModeloDibujo* D_8006B568[];
extern s16 D_800695DA;
extern void* D_800695C4;
extern u8 D_8006D1C8[];
extern EntradaVisible D_8006A940[];
extern s16 D_80069588;
extern s16 D_80069688;
extern s32 func_8003760C(void* geometria, void* vista, void* vista_siguiente);
extern void func_8003753C(void* vista);
extern s32 func_80010204(void* modelo, s32 cursor, void* estado, void* vista);
extern void func_8003C1C8(void* vista);

/*
 * Contexto de dibujo de la escena. +4..+6: bytes de estado que se pasan al dibujador de modelos
 * (func_8003B26C y func_8003B354); +8: paso de profundidad (func_8003D880); +0xA: desplazamiento
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
    s16 paso;
    s16 desplazamiento;
    s32 indice;
    u8 pad10[0x1C - 0x10];
    u32* ot0;
    u32* ot1;
    u32* ot2;
    u32* destino;
    s32 inicio;
    s32 limite;
    Objeto* objeto;
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

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003AF8C);

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

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003C014);

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

    if (ctx->indice < ctx->paso) {
        ctx->indice = 0;
    } else {
        ctx->indice = ctx->indice - ctx->paso;
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

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003DD70);

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
