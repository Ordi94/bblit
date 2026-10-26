#include "common.h"
#include "globales.h"
#include "gte.h"
#include "geometria.h"
#include "menus.h"

/*
 * Estado del fundido de pantalla. Todas son variables de 2 bytes que el original escribe con
 * lui at (de ahi g = 8 para este archivo) y carga con lui + desplazamiento, sin $gp.
 * D_80069566: progreso del fundido (0 a 0x1000); D_80069668: nivel complementario que usa el
 * dibujo de la capa de oscurecimiento; D_80069686: paso por cuadro; D_8006966A (globales.h): fase.
 */
extern s16 D_80069566;
extern s16 D_80069668;
extern u16 D_80069686;

/*
 * Anillo de marcas de tiempo de los cuadros (mismos datos que usa la presentacion): D_80069610 lo
 * reescribe el retorno de llamada de VSync, D_800695A6 cuenta los VSync desde el ultimo dibujo y
 * D_8006954C es la longitud del anillo.
 */
extern s32 D_8006954C;
extern u32 D_80069610;
extern u32 D_80069614;
extern vu16 D_800695A6;

/*
 * Cursor de escritura de primitivas GPU: direccion de la siguiente primitiva libre del cuadro. Se
 * compara con signo contra los limites de la escena, por eso es s32 y no un puntero. D_8006958C y
 * D_80069680 son el limite del buffer y su inicio.
 */
extern s32 D_80076188;
extern s32 D_8006958C;
extern s32 D_80069680;

/* Camara: D_8006D934 es la mitad alta de D_8006D928 (+0xC); el original la direcciona con su propio lui. */
extern s32 D_8006D934[3];
extern s16 D_80069402;
extern s16 D_80069416;
extern s32 D_800693F0;
extern u16 D_800694E2;

/*
 * Dos bytes del banco B (D_8006AA70[0x19] detiene el paso del fundido y D_8006AA70[0xC] es el estado
 * de pausa): el original los direcciona con su propio lui, como simbolos distintos del banco.
 */
extern u8 D_8006AA89;
extern u8 D_8006AA7C;

/* Contadores y banderas del cuadro de dibujo, y tablas de modelos y de salas visibles. */
extern s16 D_800695A2;
extern s16 D_800695A4;
extern s16 D_80069532;
extern s16 D_800695DA;
extern s16 D_80069530;
extern s16 D_80069588;
extern s16 D_80069688;
extern s32 D_80076098;
extern s32 D_8007609C;
extern u16 D_800695F2;
extern u16 D_800695F4;
extern u16 D_8006969C;
extern u16 D_800694B0;
extern u8 D_80069600;
extern void* D_800694D8;
extern void* D_800695C4;
extern ModeloDibujo* D_8006B568[];
extern ObjetoEscena* D_8006AD80[];
extern EntradaCola D_8006D1C8[];
extern EntradaVisible D_8006A940[];

/* Rutinas de otros archivos y del overlay (func_80010204 y func_80010258 dibujan un modelo). */
extern void func_80039CD0(s32 cursor);
extern void func_8001CE64(void* pila);
extern ColorYDesplazamiento* func_8001DF28(void* objeto, void* vista);
extern s32 func_8003760C(void* geometria, void* vista, void* vista_siguiente);
extern void func_8003753C(void* vista);
extern s32 func_80010204(void* modelo, s32 cursor, void* estado, void* vista);
extern s32 func_80010258(void* modelo, s32 cursor, void* estado, void* vista);
extern s32 func_80012AE4(s32 cursor, EstadoDibujo* estado, s32 color);
extern s32 func_80012AB0(s32 cursor, EstadoDibujo* estado);

/* Rutinas de este archivo que se llaman antes de definirse. */
extern void func_8003DF10(s32 cursor);
extern /* Mayor profundidad de los tres vertices proyectados (SZ1..SZ3), dividida entre cuatro. */
s32 func_8003D7C4(void);
extern /* Igual que func_8003D7C4 para cuatro vertices (SZ0..SZ3). */
s32 func_8003D814(void);
extern void func_8003D880(VistaDibujo* ctx);
extern void func_8003D904(Vertice12* dest, Vertice12* a, Vertice12* b);
extern void func_8003D988(Vertice12* dest, Vertice12* a, Vertice12* b);
extern void func_8003DA4C(Vertice12* a, Vertice12* b, Vertice12* c, VistaDibujo* ctx);
extern s32 func_8003DD70(VerticeCaja* v, LimitesPantalla* lim);
extern void func_8003CA5C(VistaDibujo* vista, s8 nivel, Vertice12* trabajo);
extern void func_8003D0D4(VistaDibujo* vista, s8 nivel, Vertice12* trabajo);
extern void func_8003C1C8(VistaDibujo* vista);
extern s32 func_8003BDD0(ModeloDibujo* modelo);
extern void func_8003C014(ObjetoEscena* entidad, ModeloDibujo* lista, EstadoDibujo* estado, VistaDibujo* vista);

/* Estado principal (solo el telon de pantalla) y copias de la camara que deja el dibujo por cuadro. */
#define PANT ((EstadoPantalla*)0x80010000)
#define COPIAS ((CopiasCamara*)&D_8006D928)

void func_8003AA38(void)
{
}

void func_8003AA40(void)
{
}

void func_8003AA48(void)
{
}

/*
 * Inicia un fundido que parte de nivel 0 con el complemento a 0x1000 (func_8003AA7C lo inicia en
 * sentido contrario). modo se guarda como fase de D_8006966A; duracion es el paso por cuadro.
 */
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

/*
 * Un paso del fundido ascendente. El nivel se compara con signo (lh) pero la aritmetica carga sin
 * signo (lhu): por eso el valor actual pasa por un u16 local y la comparacion lee la variable.
 */
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

/*
 * Actualiza el fundido del cuadro. Las fases piden iniciar el fundido (bits 4 y 8), avanzar un paso
 * (bits 1 y 2, salvo que el banco B lo detenga) o terminar (bits 0x10 y 0x20, que limpian la fase).
 * Sin fase activa, la pausa mantiene la capa a 0xE00.
 */
void func_8003ABB4(void)
{
    u8 fase;

    fase = D_8006966A;
    if (D_8006966A != 0) {
        if (fase & 4) {
            func_8003AA50(1, 0x100);
        } else if (fase & 8) {
            func_8003AA7C(2, 0x100);
        } else if (D_8006AA89 == 0) {
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
    } else if (D_8006AA7C != 0) {
        D_80069668 = 0xE00;
    } else {
        D_80069668 = 0;
    }
}

void func_8003ACA8(ObjetoCamara* objeto, void* sin_uso, MATRIX* m)
{
    VECTOR v;

    v.vx = 0;
    v.vy = 0;
    v.vz = 0x3E8;
    D_8006D928.flags80 |= 0x100;
    GsGetLw(objeto->coord, m);
    D_8006D928.vpx = m->t[0];
    D_8006D928.vpy = m->t[1];
    D_8006D928.vpz = m->t[2];
    ApplyMatrixLV(m, &v, &v);
    D_8006D928.x = D_8006D928.vpx + v.vx;
    D_8006D928.y = D_8006D928.vpy + v.vy;
    D_8006D928.z = D_8006D928.vpz + v.vz;
    GEO_CARGAR_W(&D_8006D928);
    GEO_RESTAR_W(D_8006D934);
    GEO_GUARDAR_W_T4(&v);
    D_80069402 = ratan2(v.vx, v.vz);
    D_800693F0 = SquareRoot0(v.vx * v.vx + v.vz * v.vz) + 1;
    D_80069416 = D_80069402;
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 990 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere el reparto de registros (la tabla de ordenacion y el cursor intercambian v1 y a1, y las constantes 1, 0x80000000 y 0x05000000 caen en t0/a3/a2 en lugar de t1/t0/a3) y la posicion de la carga del cursor en el segundo paquete. Variantes probadas: 40 (720 permutaciones de las escrituras del primer paquete, cursor volatile, macros, estructura de paquete). */
s32 func_8003AE08(u32* puntos, EscenaDibujo* ctx)
{
    u32* tabla;
    s32 actual;
    s32 siguiente;

    func_80039CD0(D_80076188);
    tabla = (u32*)D_8006AEA0[D_8006967C].org;
    actual = D_80076188;
    ((u32*)actual)[0] = *tabla | 0x05000000;
    ((u32*)actual)[1] = 1;
    ((u32*)actual)[2] = 0x80000000;
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

#ifdef NON_MATCHING
/* Pendiente: puntuacion 1680 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y flujo; difiere el reparto de registros (el desplazamiento de la textura cae en a0 y la plantilla en v1, en lugar de a2 y a0) y la posicion del almacen de la profundidad, que el original deja justo antes de indexar la lista de ordenacion. Variantes probadas: 160 (forma de la plantilla, orden de declaracion de los locales, acumulacion del color). */
void func_8003AF8C(SpriteDibujo* sprite, EscenaDibujo* ctx, VistaDibujo* vista)
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
        ctx->estado.s4 = 0;
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
        ctx->estado.s4 = (ctx->objeto->iD4 >> 2) - ctx->estado.s6;
    }
    if ((ctx->objeto->flags04 & 2) && color != 0 && ctx->estado.s4 >= 0) {
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
        if (ctx->estado.s4 < 0x200) {
            orden = (u32*)D_8006AE20[D_8006967C].org;
        } else {
            if (ctx->estado.s4 < 0x400) {
                n = (s16)((u16)ctx->estado.s4 - 0x200) >> 1;
                orden = (u32*)D_8006AE60[D_8006967C].org;
            } else {
                n = (s16)((u16)ctx->estado.s4 - 0x400) >> 5;
                orden = (u32*)D_8006AEA0[D_8006967C].org;
            }
            ctx->estado.s4 = n;
        }
        ranura = orden + ctx->estado.s4;
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

void func_8003B26C(PedidoModelo* pedido, EscenaDibujo* escena, VistaDibujo* vista)
{
    ModeloDibujo* modelo;

    modelo = D_8006B568[pedido->modelo];
    if (func_8003760C(modelo->geometria, vista, (u8*)vista + 0x20) != 0) {
        func_8003753C(vista);
        escena->estado.b0 = (u8)pedido->grupo;
        escena->estado.b1 = modelo->estado;
        escena->estado.b2 = (u8)pedido->profundidad + 1;
        D_800695DA = 0;
        D_800695C4 = D_8006D1C8;
        D_80076188 = func_80010204(modelo, D_80076188, &escena->estado, vista);
        if (D_800695DA != 0) {
            func_8003C1C8(vista);
        }
    }
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 485 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; solo difiere el reparto de v0/v1/a0 en la comparacion del numero de salas (la constante 0x10000 se carga antes del almacen de la profundidad) y en el puntero de la entrada visible. Variantes probadas: 60 (forma de la comparacion con shifts, orden de las escrituras previas al bucle, indexado frente a aritmetica de punteros, orden del cierre de la lista). */
void func_8003B354(ModeloDibujo* modelo, EscenaDibujo* escena, VistaDibujo* vista)
{
    PedidoModelo pedido;
    s16 actual;
    u16 cuenta;
    u16 anterior;
    EntradaVisible* entrada;

    D_800695C4 = D_8006D1C8;
    D_800695DA = 0;
    escena->estado.b0 = 0;
    escena->estado.b2 = 1;
    escena->estado.b1 = 1;
    func_8003753C((u8*)modelo + 0x94);
    D_80076188 = func_80010204(modelo, D_80076188, &escena->estado, vista);
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
    escena->estado.s6 = -0x80;
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
    escena->estado.b0 = 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B354);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 160 con la configuracion versionada (g = 8 del archivo). Misma estructura de bloques y mismo bucle de objetos; difieren el reparto v0/v1 del nivel del fundido (el compilador reutiliza el registro en lugar de releer el nivel guardado) y el orden de dos movimientos de argumentos antes de func_8003AE08. El almacen volatil de D_800694E2 y el campo w8 volatil del estado reproducen las cargas y almacenes del original. Variantes probadas: 80 (900 permutaciones de las escrituras del prologo, forma del calculo del color, variable del objeto, copias de la camara, acceso por direccion literal). */
void func_8003B5AC(ObjetoEscena* lista)
{
    EscenaDibujo* esc;
    VistaDibujo* vista = (VistaDibujo*)0x1F800038;
    ModeloDibujo* modelo;
    ObjetoEscena* obj;
    s32 color;
    s32 k;
    s32 rr;
    s32 gg;
    s32 bb;
    s32 px;
    s32 py;
    s32 pz;
    s32 qx;
    s32 qy;
    s32 qz;
    s8 hecho;
    u16 nivel;
    s32 cero;
    s32 cero2;

    func_8003ABB4();
    esc = (EscenaDibujo*)0x1F800000;
    cero = 0;
    cero2 = cero;
    D_800695A2 = 0;
    D_800695A4 = 0;
    D_80069600 = 0;
    D_80069532 = 0;
    __asm__ volatile ("ctc2 %0, $24\n\tctc2 %1, $25" : : "r"(cero), "r"(cero2));
    esc->cuenta_a = &D_800695A2;
    esc->cuenta_b = &D_800695A4;
    esc->inicio = D_80069680;
    esc->limite = D_8006958C;
    esc->ot0 = (u32*)D_8006AE20[D_8006967C].org;
    esc->ot1 = (u32*)D_8006AE60[D_8006967C].org;
    esc->ot2 = (u32*)D_8006AEA0[D_8006967C].org;
    esc->objeto = lista;
    D_8006D928.flags80 &= 0xFCFF;
    if (PANT->b76 != 0) {
        ((GsBOXF*)vista)->x = -0x100;
        ((GsBOXF*)vista)->y = -0x78;
        ((GsBOXF*)vista)->w = 0x200;
        ((GsBOXF*)vista)->attribute = 0;
        ((GsBOXF*)vista)->b = 0;
        ((GsBOXF*)vista)->g = 0;
        ((GsBOXF*)vista)->r = 0;
        if ((s8)PANT->b76 > 0) {
            D_8006D928.flags80 = D_8006D928.flags80 | 0x8000;
            ((GsBOXF*)vista)->h = PANT->b76;
            GsSortBoxFill((GsBOXF*)0x1F800038, &D_8006AE20[D_8006967C], 0x60);
            ((GsBOXF*)vista)->y = 0x78 - ((GsBOXF*)vista)->h;
            GsSortBoxFill((GsBOXF*)0x1F800038, &D_8006AE20[D_8006967C], 0x60);
            if (PANT->b76 < 0x1E) {
                PANT->b76 += 2;
            }
        } else {
            D_8006D928.flags80 = D_8006D928.flags80 & 0x7CFF;
            ((GsBOXF*)vista)->h = -(s8)PANT->b76;
            GsSortBoxFill((GsBOXF*)0x1F800038, &D_8006AE20[D_8006967C], 0x60);
            ((GsBOXF*)vista)->y = 0x78 - ((GsBOXF*)vista)->h;
            GsSortBoxFill((GsBOXF*)0x1F800038, &D_8006AE20[D_8006967C], 0x60);
            PANT->b76 += 2;
        }
    }
    if (D_8006966A != 0) {
        if ((u8)D_8006966A & 0x40) {
            nivel = 0x1000 - D_80069668;
        } else {
            nivel = D_80069668;
        }
        esc->estado.w8 = nivel;
        *(volatile u16*)&D_800694E2 = nivel;
        k = (s16)esc->estado.w8 / 16 - 1;
        if (k < 0) {
            color = 0;
        } else {
            rr = (k * D_800694E8) / 255;
            gg = (k * D_800694E1) / 255;
            bb = (k * D_800694E0) / 255;
            color = (s16)rr + ((s32)(gg << 16) >> 8) + (bb << 16);
        }
        D_80076188 = func_80012AE4(D_80076188, &esc->estado, color);
        D_80076188 = func_80012AB0(D_80076188, &esc->estado);
    } else if (D_8006AA7C != 0) {
        color = 0;
        esc->estado.w8 = 0x833;
        D_80076188 = func_80012AE4(D_80076188, &esc->estado, color);
        D_80076188 = func_80012AB0(D_80076188, &esc->estado);
    } else {
        esc->estado.w8 = D_80069668;
    }
    if (esc->objeto != NULL) {
        do {
            if (!(esc->objeto->flags04 & 2)) {
                esc->objeto = esc->objeto->sig;
                continue;
            }
            if (esc->objeto->w2C == 7) {
                esc->estado.s4 = -0x80;
                esc->estado.w0C = D_8006969C;
                esc->estado.w0E = D_800694B0;
                esc->estado.w10 = D_800695F2;
                esc->estado.w12 = D_800695F4;
                esc->estado.s6 = esc->objeto->w28 - 0x80;
                func_8003B354(esc->objeto->modelos, esc, vista);
                esc->objeto = esc->objeto->sig;
                continue;
            }
            esc->estado.s6 = esc->objeto->w28;
            if (esc->objeto->flags14 & 0x10) {
                esc->estado.s6 = (s16)esc->objeto->w28 >> 1;
                esc->estado.s6 = esc->estado.s6 + esc->objeto->p70->w28;
            }
            if ((D_80069698 != 0 && (s16)esc->objeto->w26 != (s16)D_80069698->w26) || D_800694D8 != 0) {
                esc->estado.s6 = (s16)esc->objeto->w28 >> 1;
            }
            esc->estado.s6 = esc->estado.s6 - 0x80;
            if (esc->objeto->w3A != 0) {
                if (D_80069532 < 0x28) {
                    if ((Objeto*)esc->objeto != D_80069698 || (D_8006D928.flags80 & 0x20) == 0) {
                        D_8006AD80[D_80069532++] = esc->objeto;
                    }
                } else {
                    for (;;) {
                    }
                }
            }
            modelo = esc->objeto->modelos;
            hecho = 0;
            if (modelo != NULL) {
                do {
                    if (modelo->banderas & 6) {
                        if (modelo->visible != 0) {
                            if (esc->objeto->flags08 & 0x40) {
                                modelo->modo = 0x40000000;
                            } else {
                                modelo->modo = 0;
                            }
                            D_800695DA = 0;
                            D_800695C4 = D_8006D1C8;
                            func_8003753C((u8*)modelo + 0x94);
                            hecho = func_8003BDD0(modelo);
                        }
                    } else if ((modelo->banderas & 0x11) && !(modelo->banderas & 0x8000)) {
                        func_8003AF8C((SpriteDibujo*)modelo, esc, vista);
                    } else if (modelo->banderas & 0x20) {
                        func_8003AE08((u32*)modelo, esc);
                    } else if (modelo->banderas & 0x40) {
                        obj = esc->objeto;
                        if ((obj->h50 | obj->h52 | obj->h54 | obj->h48 | obj->h4A | obj->h4C) != 0) {
                            obj->flags18 = obj->flags18 | 0x1000;
                            if (esc->objeto->flags0C & 0x100) {
                                D_8006D928.flags80 = D_8006D928.flags80 | 0x200;
                            }
                            func_8003ACA8((ObjetoCamara*)modelo, (void*)esc, (MATRIX*)vista);
                            if (esc->objeto->flags0C & 0x10000000) {
                                px = D_8006D928.vpx;
                                py = D_8006D928.vpy;
                                pz = D_8006D928.vpz;
                                qx = D_8006D928.x;
                                qy = D_8006D928.y;
                                qz = D_8006D928.z;
                                COPIAS->c68 = px;
                                COPIAS->c94 = px;
                                COPIAS->cB4 = px;
                                COPIAS->c6C = py;
                                COPIAS->c98 = py;
                                COPIAS->cB8 = py;
                                COPIAS->c70 = pz;
                                COPIAS->c9C = pz;
                                COPIAS->cBC = pz;
                                COPIAS->cA4 = qx;
                                COPIAS->cA8 = qy;
                                COPIAS->cAC = qz;
                            }
                        }
                    }
                    modelo = modelo->siguiente;
                } while (modelo != NULL);
            }
            if (hecho != 0) {
                esc->estado.b0 = 0;
                esc->estado.b2 = 1;
                esc->estado.b1 = 1;
                func_8003C014(esc->objeto, esc->objeto->modelos, &esc->estado, vista);
            }
            esc->objeto = esc->objeto->sig;
        } while (esc->objeto != NULL);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B5AC);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 5924 con la configuracion versionada (g = 8 del archivo). Escrita a mano: carga las seis palabras de los tres vertices siguientes con lw mientras el GTE proyecta los actuales, usa mtc2 desde registros s0-s5, un rtpt sin nop previos y tres promedios con t4-t9 fijos; el compilador no reparte los registros ni ordena las cargas como el original. Variantes probadas: 3 (estructura con macros de ensamblador en linea, con y sin retardos, desenrollado manual). */
/* Salida de la proyeccion: x e y empaquetados y z con signo en 8 bytes (D_8006B668). */
typedef struct SalidaVertice {
    u32 xy;
    s16 z;
    s16 pad06;
} SalidaVertice;

extern SalidaVertice D_8006B668[];

/*
 * Promedio de dos coordenadas empaquetadas (x en la mitad baja, y en la alta): la mascara
 * 0xFFFEFFFE evita el arrastre entre mitades y el bit 15 se conserva fuera del desplazamiento.
 */
#define MEDIA_XY(a, b) ((((s32)((a) & 0xFFFEFFFE) >> 1) | ((a) & 0x8000)) + (((s32)((b) & 0xFFFEFFFE) >> 1) | ((b) & 0x8000)))

#define GUARDAR_VERTICE(sxy, zv, indice)     {         SalidaVertice* sal;         if ((s16)(indice) & 0x8000) {             sal = &D_8006B668[(indice) & 0x7FFF];             (sxy) = MEDIA_XY(sxy, sal->xy);             (zv) = ((zv) >> 1) + ((s32)(sal->z << 16) >> 17);         } else {             sal = &D_8006B668[(s16)(indice)];         }         sal->xy = (sxy);         sal->z = (zv);         cuenta = cuenta - 1;         if (cuenta == 0) {             return 1;         }     }

s32 func_8003BDD0(ModeloDibujo* obj)
{
    DatosVertices* datos;
    u32* p;
    u32 w0;
    u32 w1;
    u32 w2;
    u32 w3;
    u32 w4;
    u32 w5;
    u32 i0;
    u32 i1;
    u32 i2;
    s32 sxy0;
    s32 sxy1;
    s32 sxy2;
    s32 z0;
    s32 z1;
    s32 z2;
    s32 cuenta;

    datos = obj->vertices;
    cuenta = datos->cuenta;
    if (cuenta == 0) {
        return 0;
    }
    p = datos->vertices;
    w0 = p[0];
    w1 = p[1];
    w2 = p[2];
    w3 = p[3];
    w4 = p[4];
    w5 = p[5];
    do {
        __asm__ volatile ("mtc2 %0, $0
	mtc2 %1, $1
	mtc2 %2, $2
	mtc2 %3, $3
	mtc2 %4, $4
	mtc2 %5, $5"
                          : : "r"(w0), "r"(w1), "r"(w2), "r"(w3), "r"(w4), "r"(w5));
        i0 = (s32)w1 >> 16;
        i1 = w3 >> 16;
        i2 = w5 >> 16;
        gte_rtpt();
        p += 6;
        w0 = p[0];
        w1 = p[-4];
        w2 = p[-3];
        w3 = p[-2];
        w4 = p[-1];
        w5 = p[0];
        __asm__ volatile ("mfc2 %0, $12
	mfc2 %1, $17
	mfc2 %2, $13
	mfc2 %3, $18
	mfc2 %4, $14
	mfc2 %5, $19"
                          : "=r"(sxy0), "=r"(z0), "=r"(sxy1), "=r"(z1), "=r"(sxy2), "=r"(z2));
        GUARDAR_VERTICE(sxy0, z0, i0)
        GUARDAR_VERTICE(sxy1, z1, i1)
        GUARDAR_VERTICE(sxy2, z2, i2)
    } while (cuenta > 0);
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003BDD0);
#endif

void func_8003C014(ObjetoEscena* entidad, ModeloDibujo* lista, EstadoDibujo* estado, VistaDibujo* vista)
{
    estado->w0C = D_8006969C;
    if (entidad->w3C & 2) {
        estado->w0E = entidad->w3E;
    } else {
        estado->w0E = D_800694B0;
    }
    if (entidad->flags0C & 0x02000000) {
        estado->s4 = entidad->w28 - 0x80;
        if (D_800694B0 < estado->w0E) {
            estado->w0E = D_800694B0;
        }
        if (entidad->w2C == 9 || (entidad->flags0C & 0x20000000)) {
            D_80069600 = 1;
            estado->w0C = 0x3FFF;
            estado->w0E = 0x3FFF;
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
                    D_80076188 = func_80010204(lista, D_80076188, estado, vista);
                } else {
                    D_80076188 = func_80010258(lista, D_80076188, estado, vista);
                }
            }
            lista = lista->siguiente;
        } while (lista != NULL);
    }
}

/*
 * Copia al vertice de trabajo la posicion y la profundidad del vertice de la tabla del objeto
 * que indica el elemento i de la definicion. El indice se relee en cada acceso: las escrituras
 * al vertice de trabajo pueden solapar la definicion. La macro es un bloque simple: un
 * do { } while (0) deja en el RTL una etiqueta y un salto por cada uso, parte el bloque basico y
 * el planificador reparte distinto los movimientos de argumentos de la llamada final.
 */
#define CARGAR_VERTICE(v, i) \
    { \
        VERT_XY(v) = tabla[def->s[i]].xy; \
        (v)->z = tabla[def->s[i]].z; \
    }

void func_8003C1C8(VistaDibujo* base)
{
    VistaDibujo* vista;
    EntradaCola* e;
    PoligonoDef* def;
    VerticeObjeto* tabla;
    Vertice12* w;
    u32 c;
    s32 cod;
    s32 i;

    if (D_80069530 != 0) {
        vista = base;
        base = (VistaDibujo*)vista->trabajo;
        vista->b1 = D_80069530;
        vista->s4 = D_80076098 / 2;
        vista->s6 = D_8007609C / 2;
        w = (Vertice12*)base;
        vista->ot0 = (u32*)D_8006AE20[D_8006967C].org;
        vista->ot1 = (u32*)D_8006AE60[D_8006967C].org;
        vista->ot2 = (u32*)D_8006AEA0[D_8006967C].org;
        vista->cursor = D_80076188;
        e = D_8006D1C8;
        for (i = 0; i < D_800695DA; e++, i++) {
            switch ((s16)(e->tipo - 8)) {
            case 0:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 8;
                vista->w8 = e->w2;
                CARGAR_VERTICE(&w[0], 8);
                CARGAR_VERTICE(&w[1], 9);
                CARGAR_VERTICE(&w[2], 10);
                cod = e->codigo;
                vista->b2 = cod;
                VERT_COLOR(&w[0]) = *(u32*)e->rgb0;
                VERT_COLOR(&w[1]) = e->color1;
                VERT_COLOR(&w[2]) = e->color2;
                func_8003CA5C(vista, 0, (Vertice12*)base);
                break;
            case 4:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 0xC;
                vista->w8 = e->w2;
                CARGAR_VERTICE(&w[0], 10);
                CARGAR_VERTICE(&w[1], 11);
                CARGAR_VERTICE(&w[2], 12);
                CARGAR_VERTICE(&w[3], 13);
                cod = e->codigo;
                vista->b2 = cod;
                VERT_COLOR(&w[0]) = *(u32*)e->rgb0;
                VERT_COLOR(&w[1]) = e->color1;
                VERT_COLOR(&w[2]) = e->color2;
                VERT_COLOR(&w[3]) = e->color3;
                func_8003D0D4(vista, 0, (Vertice12*)base);
                break;
            case 8:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 0x10;
                vista->w8 = e->w2;
                vista->plantilla.clut = def->u[3];
                vista->plantilla.tpage = def->u[5];
                CARGAR_VERTICE(&w[0], 10);
                CARGAR_VERTICE(&w[1], 11);
                CARGAR_VERTICE(&w[2], 7);
                VERT_UV(&w[0]) = def->u[2];
                VERT_UV(&w[1]) = def->u[4];
                VERT_UV(&w[2]) = def->u[6];
                cod = e->codigo;
                vista->b2 = cod;
                c = *(u32*)e->rgb0;
                VERT_COLOR(&w[0]) = VERT_COLOR(&w[1]) = VERT_COLOR(&w[2]) = c;
                func_8003CA5C(vista, 0, (Vertice12*)base);
                break;
            case 12:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 0x14;
                vista->w8 = e->w2;
                vista->plantilla.clut = def->u[3];
                vista->plantilla.tpage = def->u[5];
                CARGAR_VERTICE(&w[0], 10);
                CARGAR_VERTICE(&w[1], 11);
                CARGAR_VERTICE(&w[2], 12);
                CARGAR_VERTICE(&w[3], 13);
                VERT_UV(&w[0]) = def->u[2];
                VERT_UV(&w[1]) = def->u[4];
                VERT_UV(&w[2]) = def->u[6];
                VERT_UV(&w[3]) = def->u[7];
                cod = e->codigo;
                vista->b2 = cod;
                c = *(u32*)e->rgb0;
                VERT_COLOR(&w[0]) = VERT_COLOR(&w[1]) = VERT_COLOR(&w[2]) = VERT_COLOR(&w[3]) = c;
                func_8003D0D4(vista, 0, (Vertice12*)base);
                break;
            case 16:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 0x18;
                vista->w8 = e->w2;
                vista->plantilla.clut = def->u[3];
                vista->plantilla.tpage = def->u[5];
                CARGAR_VERTICE(&w[0], 14);
                CARGAR_VERTICE(&w[1], 15);
                CARGAR_VERTICE(&w[2], 7);
                VERT_UV(&w[0]) = def->u[2];
                VERT_UV(&w[1]) = def->u[4];
                VERT_UV(&w[2]) = def->u[6];
                cod = e->codigo;
                vista->b2 = cod;
                VERT_COLOR(&w[0]) = *(u32*)e->rgb0;
                VERT_COLOR(&w[1]) = e->color1;
                VERT_COLOR(&w[2]) = e->color2;
                func_8003CA5C(vista, 0, (Vertice12*)base);
                break;
            case 20:
                def = e->def;
                tabla = e->tabla;
                vista->tipo = 0x1C;
                vista->w8 = e->w2;
                vista->plantilla.clut = def->u[3];
                vista->plantilla.tpage = def->u[5];
                CARGAR_VERTICE(&w[0], 16);
                CARGAR_VERTICE(&w[1], 17);
                CARGAR_VERTICE(&w[2], 18);
                CARGAR_VERTICE(&w[3], 19);
                VERT_UV(&w[0]) = def->u[2];
                VERT_UV(&w[1]) = def->u[4];
                VERT_UV(&w[2]) = def->u[6];
                VERT_UV(&w[3]) = def->u[7];
                cod = e->codigo;
                vista->b2 = cod;
                VERT_COLOR(&w[0]) = *(u32*)e->rgb0;
                VERT_COLOR(&w[1]) = e->color1;
                VERT_COLOR(&w[2]) = e->color2;
                VERT_COLOR(&w[3]) = e->color3;
                func_8003D0D4(vista, 0, (Vertice12*)base);
                break;
            default:
                break;
            }
        }
        D_80076188 = vista->cursor;
    }
}

#define PRIM(T) ((T*)ctx->cursor)
#define PALABRA(x) (*(u32*)&(x))

void func_8003CA5C(VistaDibujo* ctx, s8 nivel, Vertice12* base)
{
    Vertice12* v;
    Vertice12* t;
    PoligonoGT4* pl;

    v = base;
    base = (Vertice12*)((u8*)base + 0x30);
    t = base;
    if (nivel != 0) {
        gte_ldv3(&v[0], &v[1], &v[2]);
        gte_rtpt();
        pl = &ctx->plantilla;
        pl->uv0 = VERT_UV(&v[0]);
        pl->uv1 = VERT_UV(&v[1]);
        pl->uv2 = VERT_UV(&v[2]);
        gte_stflg(&ctx->bandera);
        gte_stsxy3_gt3(pl);
        pl->xy3 = pl->xy2;
        if (func_8003DD70((VerticeCaja*)pl, (LimitesPantalla*)ctx) == 0) {
            if (ctx->bandera >= 0 || ctx->b1 == nivel) {
                ctx->indice = func_8003D7C4();
                func_8003D880(ctx);
                func_8003DF10(ctx->cursor);
                v[0].codigo = (u8)ctx->b2;
                if (ctx->tipo == 8) {
                    PRIM(PoligonoG3)->tag = pl->tag;
                    PRIM(PoligonoG3)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoG3)->xy0 = pl->xy0;
                    PRIM(PoligonoG3)->c1 = VERT_COLOR(&v[1]);
                    PRIM(PoligonoG3)->xy1 = pl->xy1;
                    PRIM(PoligonoG3)->c2 = VERT_COLOR(&v[2]);
                    PRIM(PoligonoG3)->xy2 = pl->xy2;
                    PRIM(PoligonoG3)->tag = (*ctx->destino & 0xFFFFFF) | 0x06000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x1C;
                } else if (ctx->tipo == 0x10) {
                    PRIM(PoligonoFT3)->tag = pl->tag;
                    PRIM(PoligonoFT3)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoFT3)->xy0 = pl->xy0;
                    PALABRA(PRIM(PoligonoFT3)->uv0) = PALABRA(pl->uv0);
                    PRIM(PoligonoFT3)->xy1 = pl->xy1;
                    PALABRA(PRIM(PoligonoFT3)->uv1) = PALABRA(pl->uv1);
                    PRIM(PoligonoFT3)->xy2 = pl->xy2;
                    PALABRA(PRIM(PoligonoFT3)->uv2) = PALABRA(pl->uv2);
                    PRIM(PoligonoFT3)->tag = (*ctx->destino & 0xFFFFFF) | 0x07000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x20;
                } else {
                    PRIM(PoligonoGT3)->tag = pl->tag;
                    PRIM(PoligonoGT3)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoGT3)->xy0 = pl->xy0;
                    PALABRA(PRIM(PoligonoGT3)->uv0) = PALABRA(pl->uv0);
                    PRIM(PoligonoGT3)->c1 = VERT_COLOR(&v[1]);
                    PRIM(PoligonoGT3)->xy1 = pl->xy1;
                    PALABRA(PRIM(PoligonoGT3)->uv1) = PALABRA(pl->uv1);
                    PRIM(PoligonoGT3)->c2 = VERT_COLOR(&v[2]);
                    PRIM(PoligonoGT3)->xy2 = pl->xy2;
                    PALABRA(PRIM(PoligonoGT3)->uv2) = PALABRA(pl->uv2);
                    PRIM(PoligonoGT3)->tag = (*ctx->destino & 0xFFFFFF) | 0x09000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x28;
                }
                if (CURSOR_RELEIDO(ctx) > D_8006958C) {
                    ctx->cursor = D_80069680;
                }
                return;
            }
        } else {
            return;
        }
    }
    *(Copia12*)&t[0] = *(Copia12*)&v[0];
    nivel = nivel + 1;
    if (ctx->tipo == 0x10) {
        func_8003D904(&t[1], &v[0], &v[1]);
        func_8003D904(&t[2], &v[0], &v[2]);
    } else {
        func_8003D988(&t[1], &v[0], &v[1]);
        func_8003D988(&t[2], &v[0], &v[2]);
    }
    func_8003CA5C(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[0], &v[1], &t[1], ctx);
    *(Copia12*)&t[0] = *(Copia12*)&v[1];
    if (ctx->tipo == 0x10) {
        func_8003D904(&t[1], &v[1], &v[2]);
        func_8003D904(&t[2], &v[1], &v[0]);
    } else {
        func_8003D988(&t[1], &v[1], &v[2]);
        func_8003D988(&t[2], &v[1], &v[0]);
    }
    func_8003CA5C(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[1], &v[2], &t[1], ctx);
    *(Copia12*)&t[0] = *(Copia12*)&v[2];
    if (ctx->tipo == 0x10) {
        func_8003D904(&t[1], &v[2], &v[0]);
        func_8003D904(&t[2], &v[2], &v[1]);
    } else {
        func_8003D988(&t[1], &v[2], &v[0]);
        func_8003D988(&t[2], &v[2], &v[1]);
    }
    func_8003CA5C(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[0], &v[2], &t[1], ctx);
    if (ctx->tipo == 0x10) {
        func_8003D904(&t[0], &v[0], &v[1]);
        func_8003D904(&t[1], &v[1], &v[2]);
        func_8003D904(&t[2], &v[0], &v[2]);
    } else {
        func_8003D988(&t[0], &v[0], &v[1]);
        func_8003D988(&t[1], &v[1], &v[2]);
        func_8003D988(&t[2], &v[0], &v[2]);
    }
    func_8003CA5C(ctx, nivel, (Vertice12*)base);
}

void func_8003D0D4(VistaDibujo* ctx, s8 nivel, Vertice12* base)
{
    Vertice12* v;
    Vertice12* t;
    PoligonoGT4* pl;

    v = base;
    base = (Vertice12*)((u8*)base + 0x30);
    t = base;
    if (nivel != 0) {
        gte_ldv3(&v[0], &v[1], &v[2]);
        gte_rtpt();
        pl = &ctx->plantilla;
        pl->uv0 = VERT_UV(&v[0]);
        pl->uv1 = VERT_UV(&v[1]);
        pl->uv2 = VERT_UV(&v[2]);
        pl->uv3 = VERT_UV(&v[3]);
        gte_stflg(&ctx->bandera);
        gte_stsxy3_gt3(pl);
        gte_ldv0(&v[3]);
        gte_rtps();
        gte_stflg(&ctx->bandera2);
        ctx->bandera = ctx->bandera | ctx->bandera2;
        gte_stsxy(&pl->xy3);
        if (func_8003DD70((VerticeCaja*)pl, (LimitesPantalla*)ctx) == 0) {
            if (ctx->bandera >= 0 || ctx->b1 == nivel) {
                ctx->indice = func_8003D814();
                func_8003D880(ctx);
                func_8003DF10(ctx->cursor);
                v[0].codigo = (u8)ctx->b2;
                if (ctx->tipo == 0xC) {
                    PRIM(PoligonoG4)->tag = pl->tag;
                    PRIM(PoligonoG4)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoG4)->xy0 = pl->xy0;
                    PRIM(PoligonoG4)->c1 = VERT_COLOR(&v[1]);
                    PRIM(PoligonoG4)->xy1 = pl->xy1;
                    PRIM(PoligonoG4)->c2 = VERT_COLOR(&v[2]);
                    PRIM(PoligonoG4)->xy2 = pl->xy2;
                    PRIM(PoligonoG4)->c3 = VERT_COLOR(&v[3]);
                    PRIM(PoligonoG4)->xy3 = pl->xy3;
                    PRIM(PoligonoG4)->tag = (*ctx->destino & 0xFFFFFF) | 0x08000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x24;
                } else if (ctx->tipo == 0x14) {
                    PRIM(PoligonoFT4)->tag = pl->tag;
                    PRIM(PoligonoFT4)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoFT4)->xy0 = pl->xy0;
                    PALABRA(PRIM(PoligonoFT4)->uv0) = PALABRA(pl->uv0);
                    PRIM(PoligonoFT4)->xy1 = pl->xy1;
                    PALABRA(PRIM(PoligonoFT4)->uv1) = PALABRA(pl->uv1);
                    PRIM(PoligonoFT4)->xy2 = pl->xy2;
                    PALABRA(PRIM(PoligonoFT4)->uv2) = PALABRA(pl->uv2);
                    PRIM(PoligonoFT4)->xy3 = pl->xy3;
                    PALABRA(PRIM(PoligonoFT4)->uv3) = PALABRA(pl->uv3);
                    PRIM(PoligonoFT4)->tag = (*ctx->destino & 0xFFFFFF) | 0x09000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x28;
                } else {
                    PRIM(PoligonoGT4)->tag = pl->tag;
                    PRIM(PoligonoGT4)->c0 = VERT_COLOR(&v[0]);
                    PRIM(PoligonoGT4)->xy0 = pl->xy0;
                    PALABRA(PRIM(PoligonoGT4)->uv0) = PALABRA(pl->uv0);
                    PRIM(PoligonoGT4)->c1 = VERT_COLOR(&v[1]);
                    PRIM(PoligonoGT4)->xy1 = pl->xy1;
                    PALABRA(PRIM(PoligonoGT4)->uv1) = PALABRA(pl->uv1);
                    PRIM(PoligonoGT4)->c2 = VERT_COLOR(&v[2]);
                    PRIM(PoligonoGT4)->xy2 = pl->xy2;
                    PALABRA(PRIM(PoligonoGT4)->uv2) = PALABRA(pl->uv2);
                    PRIM(PoligonoGT4)->c3 = VERT_COLOR(&v[3]);
                    PRIM(PoligonoGT4)->xy3 = pl->xy3;
                    PALABRA(PRIM(PoligonoGT4)->uv3) = PALABRA(pl->uv3);
                    PRIM(PoligonoGT4)->tag = (*ctx->destino & 0xFFFFFF) | 0x0C000000;
                    *ctx->destino = (u32)ctx->cursor & 0xFFFFFF;
                    ctx->cursor = ctx->cursor + 0x34;
                }
                if (CURSOR_RELEIDO(ctx) > D_8006958C) {
                    *(s32*)&ctx->cursor = D_80069680;
                }
                return;
            }
        } else {
            return;
        }
    }
    *(Copia12*)&t[0] = *(Copia12*)&v[0];
    nivel = nivel + 1;
    if (ctx->tipo == 0x14) {
        func_8003D904(&t[1], &v[0], &v[1]);
        func_8003D904(&t[2], &v[0], &v[2]);
        func_8003D904(&t[3], &v[0], &v[3]);
    } else {
        func_8003D988(&t[1], &v[0], &v[1]);
        func_8003D988(&t[2], &v[0], &v[2]);
        func_8003D988(&t[3], &v[0], &v[3]);
    }
    func_8003D0D4(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[0], &v[1], &t[1], ctx);
    *(Copia12*)&t[0] = *(Copia12*)&v[1];
    if (ctx->tipo == 0x14) {
        func_8003D904(&t[2], &v[1], &v[3]);
    } else {
        func_8003D988(&t[2], &v[1], &v[3]);
    }
    func_8003D0D4(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[1], &v[3], &t[2], ctx);
    *(Copia12*)&t[0] = *(Copia12*)&v[3];
    if (ctx->tipo == 0x14) {
        func_8003D904(&t[1], &v[3], &v[2]);
    } else {
        func_8003D988(&t[1], &v[3], &v[2]);
    }
    func_8003D0D4(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[3], &v[2], &t[1], ctx);
    *(Copia12*)&t[0] = *(Copia12*)&v[2];
    if (ctx->tipo == 0x14) {
        func_8003D904(&t[2], &v[0], &v[2]);
    } else {
        func_8003D988(&t[2], &v[0], &v[2]);
    }
    func_8003D0D4(ctx, nivel, (Vertice12*)base);
    func_8003DA4C(&v[2], &v[0], &t[2], ctx);
}

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

/*
 * Elige la lista de ordenacion para la profundidad indice - w8: las 0x200 primeras entradas van a la
 * lista de resolucion completa, las 0x200 siguientes a la de media resolucion y el resto a la de un
 * treintaidosavo. Deja en indice el desplazamiento dentro de la lista y en destino la ranura.
 */
void func_8003D880(VistaDibujo* ctx)
{
    s32 n;
    s32 m;

    if (ctx->indice < ctx->w8) {
        ctx->indice = 0;
    } else {
        ctx->indice = ctx->indice - ctx->w8;
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

void func_8003D904(Vertice12* dest, Vertice12* a, Vertice12* b)
{
    dest->x = (a->x + b->x) >> 1;
    dest->y = (a->y + b->y) >> 1;
    dest->z = (a->z + b->z) >> 1;
    dest->u = (a->u + b->u) >> 1;
    dest->v = (a->v + b->v) >> 1;
    VERT_COLOR(dest) = VERT_COLOR(a);
}

void func_8003D988(Vertice12* dest, Vertice12* a, Vertice12* b)
{
    dest->x = (a->x + b->x) >> 1;
    dest->y = (a->y + b->y) >> 1;
    dest->z = (a->z + b->z) >> 1;
    dest->u = (a->u + b->u) >> 1;
    dest->v = (a->v + b->v) >> 1;
    dest->r = (a->r + b->r) >> 1;
    dest->g = (a->g + b->g) >> 1;
    dest->b = (a->b + b->b) >> 1;
}

void func_8003DA4C(Vertice12* a, Vertice12* b, Vertice12* c, VistaDibujo* ctx)
{
    PoligonoG3* g3;
    PoligonoFT3* ft3;
    PoligonoGT3* gt3;

    func_8003DF10(ctx->cursor);
    gte_ldv3(a, b, c);
    gte_rtpt();
    if (ctx->tipo == 8 || ctx->tipo == 12) {
        g3 = (PoligonoG3*)ctx->cursor;
        a->codigo = 0x30;
        g3->c0 = *(u32*)&a->r;
        g3->c1 = *(u32*)&b->r;
        g3->c2 = *(u32*)&c->r;
        gte_stflg(&ctx->bandera);
        if (ctx->bandera >= 0) {
            gte_stsxy3_g3(g3);
            ctx->indice = func_8003D7C4();
            func_8003D880(ctx);
            g3->tag = (*ctx->destino & 0xFFFFFF) | 0x06000000;
            *ctx->destino = (u32)g3 & 0xFFFFFF;
            ctx->cursor = ctx->cursor + 0x1C;
            if (CURSOR_RELEIDO(ctx) > D_8006958C) {
                ctx->cursor = D_80069680;
            }
        }
    } else if (ctx->tipo == 16 || ctx->tipo == 20) {
        ft3 = (PoligonoFT3*)ctx->cursor;
        a->codigo = 0x24;
        ft3->c0 = *(u32*)&a->r;
        ft3->uv0 = *(u16*)&a->u;
        ft3->uv1 = *(u16*)&b->u;
        ft3->uv2 = *(u16*)&c->u;
        gte_stflg(&ctx->bandera);
        if (ctx->bandera >= 0) {
            ft3->clut = ctx->plantilla.clut;
            ft3->tpage = ctx->plantilla.tpage;
            gte_stsxy3_g3(ft3);
            ctx->indice = func_8003D7C4();
            func_8003D880(ctx);
            ft3->tag = (*ctx->destino & 0xFFFFFF) | 0x07000000;
            *ctx->destino = (u32)ft3 & 0xFFFFFF;
            ctx->cursor = ctx->cursor + 0x20;
            if (CURSOR_RELEIDO(ctx) > D_8006958C) {
                ctx->cursor = D_80069680;
            }
        }
    } else {
        gt3 = (PoligonoGT3*)ctx->cursor;
        a->codigo = 0x34;
        gt3->c0 = *(u32*)&a->r;
        gt3->c1 = *(u32*)&b->r;
        gt3->c2 = *(u32*)&c->r;
        gt3->uv0 = *(u16*)&a->u;
        gt3->uv1 = *(u16*)&b->u;
        gt3->uv2 = *(u16*)&c->u;
        gte_stflg(&ctx->bandera);
        if (ctx->bandera >= 0) {
            gt3->clut = ctx->plantilla.clut;
            gt3->tpage = ctx->plantilla.tpage;
            gte_stsxy3_gt3(gt3);
            ctx->indice = func_8003D7C4();
            func_8003D880(ctx);
            gt3->tag = (*ctx->destino & 0xFFFFFF) | 0x09000000;
            *ctx->destino = (u32)gt3 & 0xFFFFFF;
            ctx->cursor = ctx->cursor + 0x28;
            if (CURSOR_RELEIDO(ctx) > D_8006958C) {
                ctx->cursor = D_80069680;
            }
        }
    }
}

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

/*
 * Espera a que quede espacio en el anillo de primitivas del cuadro: mientras la distancia al
 * limite sea menor que 0x800, reinicia la marca cuando han pasado cuatro VSync. El ajuste del anillo
 * se hace en dos sentencias: en una sola el compilador calcula antes del bucle la constante
 * combinada de la longitud y 0x400.
 */
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
