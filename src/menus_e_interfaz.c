#include "common.h"
#include "globales.h"
#include "gte.h"
#include "geometria.h"
#include "menus.h"

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

/* D_8006D934 es la mitad alta de la camara (D_8006D928 + 0xC): el original la direcciona con su propio lui. */
extern s32 D_8006D934[3];
extern s16 D_80069402;
extern s16 D_80069416;
extern s32 D_800693F0;

extern s32 D_8006958C;
extern s32 D_80069680;
extern void func_8003DF10(s32 cursor);
extern s32 func_8003D7C4(void);
extern void func_8003D880(VistaDibujo* ctx);

extern ModeloDibujo* D_8006B568[];
extern u16 D_8006969C;
extern u16 D_800694B0;
extern u8 D_80069600;
extern s32 func_80010258(void* modelo, s32 cursor, void* vista, void* estado);
extern s16 D_800695DA;
extern void* D_800695C4;
extern EntradaCola D_8006D1C8[];
extern EntradaVisible D_8006A940[];
extern s16 D_80069588;
extern s16 D_80069688;
extern u16 D_800694E2;
extern void func_8001CE64(void* pila);
extern ColorYDesplazamiento* func_8001DF28(void* objeto, void* vista);
extern s32 func_8003760C(void* geometria, void* vista, void* vista_siguiente);
extern void func_8003753C(void* vista);
extern s32 func_80010204(void* modelo, s32 cursor, void* estado, void* vista);
extern void func_8003C1C8(VistaDibujo* vista);
extern s16 D_80069530;
extern s32 D_80076098;
extern s32 D_8007609C;
extern void func_8003CA5C(VistaDibujo* vista, s32 cero, Vertice12* trabajo);
extern void func_8003D0D4(VistaDibujo* vista, s32 cero, Vertice12* trabajo);


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

/* Pendiente: puntuacion 1245 con la configuracion versionada (g = 8 del archivo). El cursor de primitivas se carga antes que en el original y los registros t0/t1/a1/v1 se reparten distinto; la estructura de las dos primitivas de 6 palabras coincide. Variantes probadas: 14 (orden de las 6 escrituras, 720 permutaciones del primer bloque, macro sobre D_80076188, estructura de paquete). */
#ifdef NON_MATCHING
s32 func_8003AE08(u32* puntos, EscenaDibujo* ctx)
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

void func_8003B26C(PedidoModelo* pedido, EscenaDibujo* escena, VistaDibujo* vista)
{
    ModeloDibujo* modelo;

    modelo = D_8006B568[pedido->modelo];
    if (func_8003760C(modelo->geometria, vista, (u8*)vista + 0x20) != 0) {
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
void func_8003B354(ModeloDibujo* modelo, EscenaDibujo* escena, VistaDibujo* vista)
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
    VISTA_W0C(vista) = D_8006969C;
    if (entidad->w3C & 2) {
        VISTA_W0E(vista) = entidad->w3E;
    } else {
        VISTA_W0E(vista) = D_800694B0;
    }
    if (entidad->flags0C & 0x02000000) {
        vista->s4 = entidad->w28 - 0x80;
        if (D_800694B0 < VISTA_W0E(vista)) {
            VISTA_W0E(vista) = D_800694B0;
        }
        if (entidad->w2C == 9 || (entidad->flags0C & 0x20000000)) {
            D_80069600 = 1;
            VISTA_W0C(vista) = 0x3FFF;
            VISTA_W0E(vista) = 0x3FFF;
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

/*
 * Copia al vertice de trabajo la posicion y la profundidad del vertice de la tabla del objeto
 * que indica el elemento i de la definicion. El indice se relee en cada acceso: las escrituras
 * al vertice de trabajo pueden solapar la definicion.
 */
#define CARGAR_VERTICE(v, i) \
    do { \
        VERT_XY(v) = tabla[def->s[i]].xy; \
        (v)->z = tabla[def->s[i]].z; \
    } while (0)

/* Pendiente: puntuacion 80 con la configuracion versionada (g = 8 del archivo). El despacho por tabla, los seis casos, las cuatro colas y el bucle coinciden con el original y la tabla de saltos migrada es identica (las 21 entradas); solo difiere el orden de dos movimientos de argumentos antes de cada llamada (el original carga a2 antes que a0). Variantes probadas: 40 (orden de las asignaciones iniciales, bucle for frente a do/while, signo del codigo, forma del tercer argumento, prototipos). */
#ifdef NON_MATCHING
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
                vista->clut = def->u[3];
                vista->tpage = def->u[5];
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
                vista->clut = def->u[3];
                vista->tpage = def->u[5];
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
                vista->clut = def->u[3];
                vista->tpage = def->u[5];
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
                vista->clut = def->u[3];
                vista->tpage = def->u[5];
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
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003C1C8);
#endif

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

/* Pendiente: puntuacion 65 con la configuracion versionada (g = 8 del archivo). Solo difiere el orden de dos instrucciones en la rama de textura con color por vertice: el original carga el cursor de primitivas antes del almacen del codigo (el li del codigo queda en el hueco del salto) y el compilador deja el almacen primero. Variantes probadas: 8 (orden de las dos sentencias, variable intermedia para el codigo, condicion de la rama). */
#ifdef NON_MATCHING
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
            if (ctx->cursor > D_8006958C) {
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
            ft3->clut = ctx->clut;
            ft3->tpage = ctx->tpage;
            gte_stsxy3_g3(ft3);
            ctx->indice = func_8003D7C4();
            func_8003D880(ctx);
            ft3->tag = (*ctx->destino & 0xFFFFFF) | 0x07000000;
            *ctx->destino = (u32)ft3 & 0xFFFFFF;
            ctx->cursor = ctx->cursor + 0x20;
            if (ctx->cursor > D_8006958C) {
                ctx->cursor = D_80069680;
            }
        }
    } else {
        a->codigo = 0x34;
        gt3 = (PoligonoGT3*)ctx->cursor;
        gt3->c0 = *(u32*)&a->r;
        gt3->c1 = *(u32*)&b->r;
        gt3->c2 = *(u32*)&c->r;
        gt3->uv0 = *(u16*)&a->u;
        gt3->uv1 = *(u16*)&b->u;
        gt3->uv2 = *(u16*)&c->u;
        gte_stflg(&ctx->bandera);
        if (ctx->bandera >= 0) {
            gt3->clut = ctx->clut;
            gt3->tpage = ctx->tpage;
            gte_stsxy3_gt3(gt3);
            ctx->indice = func_8003D7C4();
            func_8003D880(ctx);
            gt3->tag = (*ctx->destino & 0xFFFFFF) | 0x09000000;
            *ctx->destino = (u32)gt3 & 0xFFFFFF;
            ctx->cursor = ctx->cursor + 0x28;
            if (ctx->cursor > D_8006958C) {
                ctx->cursor = D_80069680;
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003DA4C);
#endif

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
