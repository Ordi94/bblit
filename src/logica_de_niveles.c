#include "common.h"
#include "gte.h"
#include "motor.h"
#include "niveles.h"

/*
 * Rutinas que esta logica invoca. Los argumentos que el original pasa sin recortar (lh del campo
 * en lugar de lhu o andi) se declaran de 32 bits: con un prototipo estrecho el llamador los
 * recortaria.
 */
extern void func_80020210(Objeto* o, s32 paso, s32 amplitud);
extern void func_80020240(Objeto* o);
extern u8 func_80020A90(Objeto* o, Movimiento* d, Objeto** apoyo);
extern ApoyoHallado* func_80020354(Objeto* o, VECTOR* pos, void* trabajo, u32 mascara);
extern Objeto* func_800171E4(Objeto* a, VECTOR* p, u32 mascara, u32 excluir, ConsultaVolumen* o);
extern Objeto* func_80017478(Objeto* a, SVECTOR* v, void* w, u32 mascara);
extern s32 func_80018664(Objeto* a, Objeto* b, void* w);
extern Objeto* func_80016C0C(Objeto* a, u32 mascara, ConsultaVolumen* o);
extern s32 func_8001F268(Objeto* o, BloqueTrabajo* b, s32 id, s32 arg, void* w);
extern void func_8001CBB8(Objeto* o, Movimiento* d, ResultadoBaldosa* r, void* w);
extern void func_8001D414(s16 accion);
extern void func_8001D994(Objeto* o);
extern void func_8001E1A4(Objeto* o, ConsultaPlano* c);
extern void func_8001CFCC(GsCOORDINATE2* n);
extern s32 func_8003F06C(void* a0, s32 a1, s32 a2, s32 a3);
extern void func_8003AA7C(u8 modo, u16 duracion);
extern void func_80032894(void);
extern s32 BugsRand(void);
extern s32 TestLogicCond(void* o, void* item);
extern void RunLogicAction(void* o, void* item);

/*
 * Estado compartido con el resto de la logica: botones y ejes del mando, rumbo de la camara,
 * inercia, esquinas de la caja del objeto y bloques de contacto del cuadro.
 */
extern u16 D_8001000C;
extern u16 D_80010012;
extern u16 D_80010014;
extern s16 D_800694F4;
extern s32 D_80069D30[3];
extern s32 D_80069D40[3];
extern s32 D_80069D48;
extern SVECTOR D_80069D60[4];
extern s32 D_80069D80[3];
extern s32 D_8006AC30[3];
extern u8 D_8006AC3C[6];
extern s32 D_8006AC44[3];
extern s32 D_8006ACE0[3];
extern u8 D_8006ACEC[6];
extern s32 D_8006ACF4[3];
extern s32 D_8006AD30[3];
extern s32 D_8006AD70[3];
extern s32 D_8006AD74;

/*
 * Datos pequenos que el original direcciona con desplazamiento($gp): cada uno se define en este
 * archivo (definicion tentativa) para que se emita relativo a $gp.
 */
Objeto* D_80069388;
s32 D_8006938C;
u8 D_80069390[8];
s32 D_80069398;
s32 D_800693AC;
s32 D_800693B0;
s16 D_800693B8;
s32 D_800693BC;
s32 D_800693C0;
s32 D_800693C4;
s32 D_800693C8;
s32 D_800693CC;
u32 D_800693D4;
s16* D_800693DC;

#ifdef NON_MATCHING
/* Pendiente: puntuacion en curso con la configuracion versionada (g = 8 del archivo). */
void func_80020B90(Objeto* o)
{
    ScratchJugador* sc;
    void* w;
    s32* p;
    u16 i;
    s16 k;
    s16 vel;
    s16 pasos;
    s16 ang2;
    s16 tilt16;
    s32 ang;
    s32 d;
    s32 tilt;
    s32 dd;
    s16 d16;
    s32 omitir;
    s32 y32;
    u16 y16;
    s32 pj;
    s16 vj;
    s16 ok;
    s16 dd16;
    Objeto* pp;
    s32 ex;
    s32 mx;
    s32 ez;
    s32 mz;
    s16* ptr16;
    u16 u5;
    s16 u6;
    s32 k0;
    s32 k1;
    s16 delta;
    s32 vs;
    u16 hw;
    s32 sum;
    s32 cuad;
    s16 rr;
    s32 ss;
    VECTOR* pos;

    sc = (ScratchJugador*)0x1F800000;
    w = (void*)0x1F800148;
    p = (s32*)0x1F800000;
    i = 0;
    do {
        *p = 0;
        i++;
        p++;
    } while (i < 0x52);
    D_800693D4 = o->flags14;
    o->flags14 &= 0xFFF9BFFF;
    if (D_8001004F == 0 && ((D_8006D9A8[0] & 0x100) || (s32)o->flags14 < 0)) {
        D_80069D30[2] = 0;
        D_80069D30[0] = 0;
        D_80069D40[2] = 0;
        D_80069398 = 0x800;
        D_80069D40[0] = 0;
        if (!(D_8006D9A8[0] & 0x200)) {
            D_8001000A &= 0x800;
        }
    }
    if (D_80069608 & 2) {
        o->flags04 &= ~2;
        o->flags18 |= 0x100;
        o->flags14 |= 0x80000000;
    }
    if (o->u78.p == NULL) {
        o->param.giro.u.z = 0;
        o->param.giro.u.x = 0;
        D_800693BC = 0;
        D_80069690 = 0;
        D_80069388 = 0;
        GEO_CERO_W(D_80069D80);
        GEO_CERO_WH(&D_80069390);
        sc->sec = o->secuencias;
        if (sc->sec != NULL) {
            while (sc->sec != NULL && sc->sec->id != 2) {
                sc->sec = sc->sec->sig;
            }
        }
        if (sc->sec == NULL) {
            sc->sec = o->secuencias;
            if (sc->sec != NULL) {
                while (sc->sec != NULL && sc->sec->id != 1) {
                    sc->sec = sc->sec->sig;
                }
            }
        }
        o->w17E = 0;
        o->p180 = sc->sec;
        sc->paso_vigente = sc->sec->desplazamiento;
        sc->reg = (RegistroEstado*)o->bloque;
        while (sc->reg != NULL && sc->reg->id != sc->paso_vigente) {
            sc->reg = sc->reg->sig;
        }
        sc->trans = (Transicion*)o->apoyos;
        while (sc->trans != NULL && sc->trans->id != sc->reg->w0A) {
            sc->trans = sc->trans->sig;
        }
        o->registro184 = (RegistroAnim*)sc->reg;
        D_800693F6 = 0;
        D_800693B0 = 0;
        D_800693C8 = 0;
        D_800693C0 = 0;
        o->nodo188 = (NodoSecuencia*)sc->trans;
        D_80069398 = 0x800;
        D_800693B8 = -1;
        o->flags14 = 0;
        o->w17C = sc->sec->id;
        D_80069D30[2] = 0;
        D_80069D30[0] = 0;
        D_80069D40[2] = 0;
        D_80069D40[0] = 0;
        APOYO(o)->escala.vz = 0x1000;
        APOYO(o)->escala.vy = 0x1000;
        APOYO(o)->escala.vx = 0x1000;
        func_80032894();
        o->flags18 = 0;
        o->flags14 = 0;
    }
    sc->sec = o->secuencias;
    while (sc->sec != NULL && sc->sec->id != o->w17C) {
        sc->sec = sc->sec->sig;
    }
    sc->paso_vigente = ((u16*)&sc->sec->desplazamiento)[o->w17E];
    o->p180 = sc->sec;
    if (sc->paso_vigente == 0xFFF0 || o->w17E >= 5) {
        o->w17C = 1;
        sc->sec = o->secuencias;
        while (sc->sec != NULL && sc->sec->id != 1) {
            sc->sec = sc->sec->sig;
        }
        o->flags14 &= 0xFDFFFFDF;
        o->w17E = 0;
        o->p180 = sc->sec;
        sc->paso_vigente = sc->sec->desplazamiento;
        sc->reg = (RegistroEstado*)o->bloque;
        while (sc->reg != NULL && sc->reg->id != sc->paso_vigente) {
            sc->reg = sc->reg->sig;
        }
        sc->trans = (Transicion*)o->apoyos;
        while (sc->trans != NULL && sc->trans->id != sc->reg->w0A) {
            sc->trans = sc->trans->sig;
        }
        o->registro184 = (RegistroAnim*)sc->reg;
        o->nodo188 = (NodoSecuencia*)sc->trans;
        D_80069584 = (u16)o->trabajo.i14;
        o->trabajo.i14 = 0;
        o->p180 = sc->sec;
        if (o->p70 != NULL && (o->p70->flags08 & 4) && (o->flags14 & 2)) {
            o->coord.super = NULL;
            o->coord.param = (GsCOORD2PARAM*)&o->param;
            o->param.giro.u.y = APOYO(o)->giro.u.y;
            o->p70->p6C = NULL;
            o->p70 = NULL;
            o->flags14 &= ~4;
        }
    } else {
        sc->reg = (RegistroEstado*)o->bloque;
        while (sc->reg != NULL && sc->reg->id != sc->paso_vigente) {
            sc->reg = sc->reg->sig;
        }
        sc->trans = (Transicion*)o->apoyos;
        while (sc->trans != NULL && sc->trans->id != sc->reg->w0A) {
            sc->trans = sc->trans->sig;
        }
        o->registro184 = (RegistroAnim*)sc->reg;
    }
    if (sc->reg->flags10 & 0x1000) {
        o->flags18 |= 2;
    } else {
        o->flags18 &= ~2;
    }
    if (sc->reg->flags10 & 0x2000) {
        o->flags18 |= 4;
        if (D_80069698->w1B4 != 0) {
            D_8006965A = 5;
            D_8006965B = 0x50;
            D_8006965E = 0;
        }
    } else {
        o->flags18 &= ~4;
    }
    if (sc->reg->flags10 >= 0) {
        if (!(o->flags14 & 0x80000000) || D_8001004F != 0) {
            if ((sc->reg->flags0C & 2) && (!(o->flags14 & 0x80000000) || D_8001004F != 0)) {
                if ((o->flags14 & 0x209) == 0) {
                    D_800694F4 = ratan2(D_8006D928.x - D_8006D928.vpx, D_8006D928.z - D_8006D928.vpz);
                }
                if ((s16)D_80010012 != 0 || D_80010014 != 0) {
                    vel = ((s16)SquareRoot0((s16)D_80010012 * (s16)D_80010012 + (s16)D_80010014 * (s16)D_80010014) - D_8006952C) * (0x80 / D_8006952C);
                    if (vel > 0x80) {
                        vel = 0x80;
                    }
                    if (sc->reg->flags10 & 0x04000000) {
                        if (vel < 0x78) {
                            o->w17E = 0;
                        } else {
                            o->w17E = 1;
                        }
                    }
                    if (sc->reg->flags10 & 0x08000000) {
                        pasos = vel;
                        if ((sc->reg->flags10 & 0x04000000) && pasos < 0x78) {
                            pasos = pasos * 0x1111 >> 12;
                        }
                        D_800693AC += pasos;
                        o->trabajo.b05 = 5 - D_800693AC / 32;
                        D_800693AC = D_800693AC % 32;
                    }
                    vel = (u32)(sc->reg->s14 * D_80069694 * vel) >> 7;
                    if (vel == 0) {
                        vel = 1;
                    }
                    if (o->coord.super != NULL) {
                        sc->tmp_sv.vz = 0x3E8;
                        sc->tmp_sv.vx = 0;
                        sc->tmp_sv.vy = 0;
                        sc->cursor = &o->coord;
                        if (sc->cursor != NULL) {
                            do {
                                ApplyMatrixSV(&sc->cursor->coord, &sc->tmp_sv, &sc->tmp_sv);
                            } while ((sc->cursor = sc->cursor->super) != NULL);
                        }
                        sc->tmp = ratan2((s16)sc->tmp_sv.vx, (s16)sc->tmp_sv.vz);
                        o->param.giro.u.y = sc->tmp;
                        ang = D_800694F4 + ratan2((s16)D_80010012, (s16)D_80010014);
                        sc->tmp = sc->tmp - ang % 0x1000;
                        if (sc->tmp > 0x800) {
                            sc->tmp -= 0x1000;
                        }
                        if (sc->tmp < -0x800) {
                            sc->tmp += 0x1000;
                        }
                        D_800693B8 = -(u16)sc->tmp;
                        if (sc->tmp < 0) {
                            sc->tmp = -sc->tmp;
                        }
                        sc->tmp = 0x800 - sc->tmp;
                        d = sc->tmp * vel;
                    } else {
                        sc->tmp = vel;
                        ang2 = ratan2((s16)D_80010012, (s16)D_80010014);
                        if (!(sc->reg->flags0C & 0x8000)) {
                            ang2 = (u16)D_800694F4 + ang2;
                        }
                        if (ang2 > 0x800) {
                            ang2 -= 0x1000;
                        }
                        if (ang2 < -0x800) {
                            ang2 += 0x1000;
                        }
                        if ((s16)o->param.giro.u.y > 0x800) {
                            o->param.giro.u.y -= 0x1000;
                        }
                        if ((s16)o->param.giro.u.y < -0x800) {
                            o->param.giro.u.y += 0x1000;
                        }
                        ang2 = ang2 - o->param.giro.u.y;
                        if (ang2 > 0x800) {
                            ang2 -= 0x1000;
                        }
                        if (ang2 < -0x800) {
                            ang2 += 0x1000;
                        }
                        o->param.giro.u.z = ang2 >> 3;
                        D_800693B8 = ang2;
                        if (ang2 < 0) {
                            ang2 = -ang2;
                        }
                        d = sc->tmp * (s16)(0x800 - ang2);
                    }
                    sc->vel.z = sc->vel.z + (d >> 11);
                }
                if (sc->reg->flags0C & 0x100000) {
                    sc->vel.z += sc->reg->s14 * D_80069694;
                }
            } else {
                D_800693C8 = 0;
                if (sc->reg->flags0C & 0x100000) {
                    sc->vel.z += sc->reg->s14 * D_80069694;
                }
                tilt = (s16)o->param.giro.u.z >> 2;
                if (tilt == 0) {
                    o->param.giro.u.z = 0;
                } else {
                    o->param.giro.u.z = -tilt;
                }
            }
            if ((s16)D_800693B8 != -1) {
                tilt = (s16)D_800693B8 >> 2;
                if (tilt != 0) {
                    vel = tilt;
                    D_800693B8 = D_800693B8 - tilt;
                } else {
                    vel = D_800693B8;
                    D_800693B8 = -1;
                }
                ((ParametrosObjeto*)o->coord.param)->giro.u.y += vel;
            }
        }
        if (sc->reg->flags10 & 0x10) {
            if (o->coord.super != NULL) {
                sc->tmp_v.vx = D_8006D928.vpx - o->param.trans.vx;
                sc->tmp_v.vz = D_8006D928.vpz - o->param.trans.vz;
                ang = ratan2(sc->tmp_v.vx, sc->tmp_v.vz);
                sc->tmp = (s16)o->param.giro.u.y - ang % 0x1000;
                if (sc->tmp > 0x800) {
                    sc->tmp -= 0x1000;
                }
                if (sc->tmp < -0x800) {
                    sc->tmp += 0x1000;
                }
                ((ParametrosObjeto*)o->coord.param)->giro.u.y -= (u16)sc->tmp;
            } else {
                sc->tmp_v.vx = D_8006D928.vpx - o->param.trans.vx;
                sc->tmp_v.vz = D_8006D928.vpz - o->param.trans.vz;
                o->param.giro.u.y = ratan2(sc->tmp_v.vx, sc->tmp_v.vz);
            }
        }
        if (!(o->flags14 & 2)) {
            o->param.giro.u.z = 0;
        }
        if ((sc->reg->flags0C & 0x10) && !(sc->reg->flags10 & 0x40000000) && !(D_8001000C & 0x40) && !(o->flags14 & 8)) {
            if (o->h108 > 0x600 && o->h108 < 0x800) {
                o->h108 = 0x800;
            }
        }
        if ((sc->reg->flags0C & 0xC00) && ((s16)D_80010012 != 0 || D_80010014 != 0)) {
            vel = SquareRoot0((s16)D_80010012 * (s16)D_80010012 + (s16)D_80010014 * (s16)D_80010014);
            if (vel > 0x7F) {
                vel = 0x7F;
            }
            if (sc->reg->flags0C & 0x400) {
                vel = -vel;
            }
            sc->vel.y = sc->vel.y + ((u32)(sc->reg->s14 * D_80069694 * vel) >> 7);
        }
        if (sc->reg->flags0C & 0x200) {
            if (o->p70 != NULL) {
                APOYO(o)->trans.vz = 0;
                APOYO(o)->trans.vx = 0;
                sc->res_peldano = func_80020A90(o, (Movimiento*)&sc->vel, (Objeto**)w);
                if (sc->res_peldano != 0) {
                    if (sc->res_peldano == 2) {
                        if (sc->reg->flags0C & 0x400) {
                            sc->vel.y = 0;
                        }
                    } else if (sc->res_peldano == 1) {
                        o->coord.super = NULL;
                        o->coord.param = (GsCOORD2PARAM*)&o->param;
                        o->param.giro.u.y = APOYO(o)->giro.u.y;
                        o->p70->p6C = NULL;
                        o->p70 = NULL;
                        o->flags14 &= ~4;
                        o->w17E = o->w17E + 1;
                    }
                }
            }
        }
        RotMatrix((SVECTOR*)&o->param.giro, &sc->m);
        gte_SetRotMatrix(&sc->m);
        gte_ldv0(&sc->vel);
        gte_rtv0();
        gte_stlvnl(&sc->desp);
        sc->desp.x += o->empuje.vx;
        sc->desp.y += o->empuje.vy;
        sc->desp.z += o->empuje.vz;
        o->empuje.vz = 0;
        o->empuje.vy = 0;
        o->empuje.vx = 0;
        sc->resp.x = sc->desp.x;
        sc->resp.y = sc->desp.y;
        sc->resp.z = sc->desp.z;
        if ((s32)o->flags14 >= 0 || D_8001004F != 0) {
            if (o->flags14 & 2) {
                sc->tmp_v.vz = 0;
                sc->tmp_v.vy = 0;
                sc->tmp_v.vx = 0;
                sc->punto.vx = sc->desp.x + o->param.trans.vx;
                sc->punto.vy = sc->desp.y + o->param.trans.vy;
                sc->punto.vz = sc->desp.z + o->param.trans.vz;
                sc->res.grupo = o->w26;
                func_8001C134((s32*)&sc->punto, &sc->res, w);
                if (sc->res.flags & 0x20) {
                    omitir = 0;
                    if (!(o->flags14 & 0x10000000)) {
                        D_80069D30[0] = sc->desp.x >> 2;
                        D_80069D30[2] = sc->desp.z >> 2;
                        o->flags14 |= 0x10000000;
                    }
                    sc->punto.vx = o->param.trans.vx + 0xA0;
                    y32 = o->param.trans.vy;
                    sc->punto.vy = y32;
                    sc->res.grupo = -1;
                    sc->punto.vz = o->param.trans.vz;
                    func_8001C134((s32*)&sc->punto, &sc->res, w);
                    if (!(sc->res.flags & 0xC) && (sc->res.flags & 0x20)) {
                        sc->tmp = sc->res.suelo - o->param.trans.vy;
                        if (sc->tmp >= -0x64 && sc->tmp < 0xC8) {
                            sc->tmp_v.vx += ((sc->res.suelo - (s16)y32) * 3000) >> 12;
                        }
                    }
                    sc->punto.vx = o->param.trans.vx - 0xA0;
                    sc->punto.vy = o->param.trans.vy;
                    sc->res.grupo = -1;
                    sc->punto.vz = o->param.trans.vz;
                    func_8001C134((s32*)&sc->punto, &sc->res, w);
                    if (!(sc->res.flags & 0xC) && (sc->res.flags & 0x20)) {
                        sc->tmp = sc->res.suelo - o->param.trans.vy;
                        if (sc->tmp >= -0x64 && sc->tmp < 0xC8) {
                            sc->tmp_v.vx += (((s16)y32 - sc->res.suelo) * 3000) >> 12;
                        }
                    }
                    sc->punto.vx = o->param.trans.vx;
                    sc->punto.vy = o->param.trans.vy;
                    sc->res.grupo = -1;
                    sc->punto.vz = o->param.trans.vz + 0xA0;
                    func_8001C134((s32*)&sc->punto, &sc->res, w);
                    if (!(sc->res.flags & 0xC) && (sc->res.flags & 0x20)) {
                        sc->tmp = sc->res.suelo - o->param.trans.vy;
                        if (sc->tmp >= -0x64 && sc->tmp < 0xC8) {
                            sc->tmp_v.vz += ((sc->res.suelo - (s16)y32) * 3000) >> 12;
                        }
                    }
                    sc->punto.vx = o->param.trans.vx;
                    sc->punto.vy = o->param.trans.vy;
                    sc->res.grupo = -1;
                    sc->punto.vz = o->param.trans.vz - 0xA0;
                    func_8001C134((s32*)&sc->punto, &sc->res, w);
                    if (!(sc->res.flags & 0xC) && (sc->res.flags & 0x20)) {
                        sc->tmp = sc->res.suelo - o->param.trans.vy;
                        if (sc->tmp >= -0x64 && sc->tmp < 0xC8) {
                            sc->tmp_v.vz += (((s16)y32 - sc->res.suelo) * 3000) >> 12;
                        }
                    }
                    dd = (sc->tmp_v.vx - D_80069D40[0]) << 12 >> 16;
                    if (dd != 0 && omitir == 0) {
                        D_80069D40[0] += dd;
                    } else {
                        D_80069D40[0] = sc->tmp_v.vx;
                    }
                    dd = (sc->tmp_v.vz - D_80069D40[2]) << 12 >> 16;
                    if (dd != 0 && omitir == 0) {
                        D_80069D40[2] += dd;
                    } else {
                        D_80069D48 = sc->tmp_v.vz;
                    }
                } else if (o->flags14 & 0x10000000) {
                    o->flags14 &= 0xEFFFFFFF;
                }
            } else if ((o->flags14 & 0x10) && o->p70 != NULL && (o->p70->flags0C & 0x800000)) {
                if (!(o->flags14 & 0x10000000)) {
                    if ((D_80069D30[0] | D_80069D30[2]) == 0) {
                        D_80069D30[0] = sc->desp.x;
                        D_80069D30[2] = sc->desp.z;
                    }
                    o->flags14 |= 0x10000000;
                }
                y16 = o->param.trans.vy;
                ((ParametrosObjeto*)o->coord.param)->trans.vx += 0xA0;
                sc->acum.nodo = &o->coord;
                func_8001CE64(&sc->acum);
                sc->tmp_v.vx += ((sc->acum.acc.vy - (s16)y16) * 3000) >> 12;
                ((ParametrosObjeto*)o->coord.param)->trans.vx -= 0x140;
                sc->acum.nodo = &o->coord;
                func_8001CE64(&sc->acum);
                ((ParametrosObjeto*)o->coord.param)->trans.vx += 0xA0;
                sc->tmp_v.vx += (((s16)y16 - sc->acum.acc.vy) * 3000) >> 12;
                ((ParametrosObjeto*)o->coord.param)->trans.vz += 0xA0;
                sc->acum.nodo = &o->coord;
                func_8001CE64(&sc->acum);
                sc->tmp_v.vz += ((sc->acum.acc.vy - (s16)y16) * 3000) >> 12;
                ((ParametrosObjeto*)o->coord.param)->trans.vz -= 0x140;
                sc->acum.nodo = &o->coord;
                func_8001CE64(&sc->acum);
                ((ParametrosObjeto*)o->coord.param)->trans.vz += 0xA0;
                sc->tmp_v.vz += (((s16)y16 - sc->acum.acc.vy) * 3000) >> 12;
                if (((sc->tmp_v.vx - D_80069D40[0]) << 12 >> 16) != 0) {
                    D_80069D40[0] += (sc->tmp_v.vx - D_80069D40[0]) << 12 >> 16;
                } else {
                    D_80069D40[0] = sc->tmp_v.vx;
                }
                if (((sc->tmp_v.vz - D_80069D40[2]) << 12 >> 16) != 0) {
                    D_80069D40[2] += (sc->tmp_v.vz - D_80069D40[2]) << 12 >> 16;
                } else {
                    D_80069D40[2] = sc->tmp_v.vz;
                }
            }
        }
        if (!(o->flags14 & 0x201)) {
            if (o->flags14 & 0x10000000) {
                d16 = (u16)sc->desp.x - (u16)D_80069D30[0];
                if (d16 != 0) {
                    if (d16 < 0) {
                        D_80069D30[0] = D_80069D30[0] - 1;
                    } else {
                        D_80069D30[0] = D_80069D30[0] + 1;
                    }
                } else {
                    D_80069D30[0] = sc->desp.x;
                }
                d16 = (u16)sc->desp.z - (u16)D_80069D30[2];
                if (d16 != 0) {
                    if (d16 < 0) {
                        D_80069D30[2] = D_80069D30[2] - 1;
                    } else {
                        D_80069D30[2] = D_80069D30[2] + 1;
                    }
                } else {
                    D_80069D30[2] = sc->desp.z;
                }
            } else {
                dd = D_80069D40[0] << 14 >> 16;
                if (dd != 0) {
                    D_80069D40[0] -= dd;
                } else {
                    D_80069D40[0] = 0;
                }
                dd = D_80069D40[2] << 14 >> 16;
                if (dd != 0) {
                    D_80069D40[2] -= dd;
                } else {
                    D_80069D40[2] = 0;
                }
                dd = (sc->desp.x - D_80069D30[0]) * D_80069398 * 16 >> 16;
                if (dd != 0 || D_80069398 != 0x800) {
                    D_80069D30[0] += dd;
                } else {
                    D_80069D30[0] = sc->desp.x;
                }
                dd = (sc->desp.z - D_80069D30[2]) * D_80069398 * 16 >> 16;
                if (dd != 0 || D_80069398 != 0x800) {
                    D_80069D30[2] += dd;
                } else {
                    D_80069D30[2] = sc->desp.z;
                }
            }
            sc->desp.x = D_80069D30[0];
            sc->desp.z = D_80069D30[2];
            sc->desp.x += D_80069D40[0];
            sc->desp.z += D_80069D40[2];
        } else {
            D_80069D40[0] = sc->desp.x;
            D_80069D40[2] = sc->desp.z;
        }
        if (D_80069398 >= 0x800) {
            D_80069398 = 0x800;
        } else {
            D_80069398 = D_80069398 + 0x10;
        }
        if ((sc->reg->flags0C & 0x10) && ((o->flags14 & 0x209) == 0 || (o->flags14 & 0x400))) {
            if (o->p70 != NULL) {
                if (o->p70->flags08 & 4) {
                    func_80020210(o, sc->reg->s18, sc->reg->s16);
                    o->coord.param = (GsCOORD2PARAM*)&o->param;
                    o->flags14 &= ~4;
                    o->coord.super = NULL;
                    o->param.giro.u.y = APOYO(o)->giro.u.y + o->p70->param.giro.u.y;
                    o->p70->p6C = NULL;
                    o->p70 = NULL;
                } else if (o->p70->flags08 & 8) {
                    sc->tmp = sc->reg->s18;
                    if ((o->p70->flags08 & 0x8000) || (o->p70->w2C == 0xE && o->p70->registro184 != NULL && (((RegistroEstado*)o->p70->registro184)->flags10 & 0x10000000))) {
                        if (o->p70->w2C == 5) {
                            vj = o->p70->s1E;
                        } else {
                            vj = *(s16*)&o->p70->w196;
                        }
                        if (vj == 0) {
                            vj = sc->reg->s18 * 0x145 >> 9;
                        }
                        sc->tmp = vj;
                    }
                    sc->rel.vy = 0;
                    sc->rel.vx = o->param.trans.vx - o->p70->param.trans.vx;
                    sc->rel.vz = o->param.trans.vz - o->p70->param.trans.vz;
                    GEO_CARGAR_W(&o->p70->param.trans);
                    GEO_GUARDAR_W_T1(&sc->punto);
                    sc->punto.vy = o->param.trans.vy;
                    sc->res.grupo = o->w26;
                    func_80019474(&sc->punto, &sc->rel, &sc->res, w);
                    o->param.trans.vx = o->p70->param.trans.vx + sc->rel.vx;
                    o->param.trans.vz = o->p70->param.trans.vz + sc->rel.vz;
                    sc->resp_apoyo[0] = (u32)o->p70;
                    sc->resp_apoyo[1] = (u32)o->coord.super;
                    sc->resp_apoyo[2] = (u32)o->coord.param;
                    o->coord.super = NULL;
                    o->coord.param = (GsCOORD2PARAM*)&o->param;
                    o->p70->p6C = NULL;
                    o->p70 = NULL;
                    o->flags14 &= ~0x15;
                    pj = sc->tmp;
                    goto llamar_salto;
                }
            } else {
                if (o->flags14 & 0x80) {
                    o->param.giro.u.x = 0;
                    RotMatrix((SVECTOR*)&o->param.giro, &o->coord.coord);
                    RotMatrix((SVECTOR*)&o->param.giro, &sc->m);
                    gte_SetRotMatrix(&sc->m);
                    gte_ldv0(&sc->vel);
                    gte_rtv0();
                    gte_stlvnl(&sc->desp);
                    o->flags14 = (o->flags14 & ~0x84) | 2;
                }
                pj = sc->reg->s18;
llamar_salto:
                func_80020210(o, pj, sc->reg->s16);
            }
        }
        if ((o->flags14 & 1) && (o->flags14 & 0x600) != 0x200 && ((s32)o->flags14 >= 0 || D_8001004F != 0)) {
            func_80020240(o);
        }
        if (sc->reg->flags0C & 0x810000) {
            o->flags14 |= 0x40;
        } else {
            o->flags14 &= ~0x40;
        }
        if (sc->reg->flags0C & 0x800000) {
            sc->tocado = func_80016C0C(o, 0x80, (ConsultaVolumen*)w);
            if (sc->tocado != NULL) {
                ok = 1;
                if (sc->tocado->w2C == 0xE) {
                    if (sc->tocado->registro184 == NULL || !(((RegistroEstado*)sc->tocado->registro184)->flags0C & 0x4000)) {
                        ok = 0;
                    }
                }
                if (ok != 0) {
                    sc->tocado->flags14 |= 0x04000000;
                    sc->tocado->w38 = 1;
                    sc->tocado->i34 = 1;
                    o->i34 = sc->tocado->w1C;
                }
            }
        }
        if ((sc->reg->flags0C & 0x10000) && o->i68 != 0) {
            sc->tocado = func_800171E4(o, &o->objetivo, 0x80, 0, (ConsultaVolumen*)w);
            if (sc->tocado != NULL) {
                ok = 1;
                if (sc->tocado->w2C == 0xE) {
                    if (sc->tocado->registro184 == NULL || !(((RegistroEstado*)sc->tocado->registro184)->flags0C & 0x4000)) {
                        ok = 0;
                    }
                }
                if (ok != 0) {
                    if (o->p6C != NULL) {
                        sc->tocado->flags14 |= 0x06000000;
                        if (o->p6C->registro184 != NULL) {
                            sc->tocado->w38 = ((RegistroEstado*)o->p6C->registro184)->s16;
                        } else {
                            sc->tocado->w38 = 1;
                        }
                        sc->tocado->i34 = o->p6C->w1C;
                    } else {
                        sc->tocado->flags14 |= 0x04000000;
                        sc->tocado->w38 = 1;
                        sc->tocado->i34 = 1;
                    }
                    o->i34 = sc->tocado->w1C;
                }
            }
        }
        if (((sc->reg->flags0C & 0x40) || (sc->reg->flags10 & 0x40000)) && o->i68 != 0 && o->p6C != NULL) {
            pp = o->p6C;
            pp->flags14 &= ~0x806;
            if (sc->reg->flags10 & 0x40000) {
                pp->flags14 |= 0x80000;
            } else {
                pp->flags14 |= 0x1000;
            }
            sc->punto.vx = o->param.trans.vx;
            sc->punto.vy = o->param.trans.vy;
            sc->punto.vz = o->param.trans.vz;
            dd16 = (u16)o->objetivo.vx - (u16)o->param.trans.vx;
            sc->tmp_sv.vx = dd16;
            sc->rel.vx = (s16)dd16;
            dd16 = (u16)o->objetivo.vz - (u16)o->param.trans.vz;
            sc->tmp_sv.vz = dd16;
            sc->rel.vy = (s16)dd16;
            dd16 = (u16)o->objetivo.vy - (u16)o->param.trans.vy;
            sc->tmp_sv.vy = dd16;
            sc->rel.vz = (s16)dd16;
            func_80017478(o, &sc->tmp_sv, w, 0x20100);
            sc->tmp_v.vy = 0;
            sc->tmp_v.vx = (s16)sc->tmp_sv.vx;
            sc->tmp_v.vz = (s16)sc->tmp_sv.vz;
            sc->res.grupo = o->w26;
            func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
            pp->param.trans.vx = o->param.trans.vx + sc->tmp_v.vx;
            pp->param.trans.vy = o->objetivo.vy;
            pp->coord.super = NULL;
            pp->coord.param = (GsCOORD2PARAM*)&pp->param;
            pp->param.trans.vz = o->param.trans.vz + sc->tmp_v.vz;
            pp->w26 = o->w26;
            pp->p70 = NULL;
            pp->param.giro.u.y = o->param.giro.u.y;
            o->p6C = NULL;
            func_8001CFCC(&pp->coord);
            o->min.vx = -0x46;
            o->min.vz = -0x28;
            o->max.vx = 0x46;
            o->max.vz = 0x28;
            o->w2E = 0x50;
            o->alcance2 = 0x1900;
        }
        if ((sc->reg->flags0C & 0x200) && (D_8001000A & 8)) {
            if (o->p70 != NULL && !(o->p70->flags08 & 0x400000)) {
                *(s32*)&o->p70->trabajo = *(s32*)&o->p70->trabajo + 4;
            }
        }
        if (sc->reg->flags0C & 0x100) {
            if ((o->flags14 & 0x10208) && o->p70 == NULL) {
                sc->punto.vx = o->param.trans.vx;
                sc->punto.vy = o->param.trans.vy;
                sc->punto.vz = o->param.trans.vz;
                sc->apoyo_hallado = func_80020354(o, &sc->punto, w, 0x400004);
                if (sc->apoyo_hallado != NULL) {
                    o->coord.param = (GsCOORD2PARAM*)APOYO(o);
                    APOYO(o)->trans.vx = 0;
                    o->p70 = sc->apoyo_hallado->objeto;
                    APOYO(o)->trans.vz = 0;
                    APOYO(o)->trans.vy = sc->apoyo_hallado->h0A;
                    sc->tmp = (s16)o->param.giro.u.y - (s16)o->p70->param.giro.u.y;
                    if (sc->tmp < 0) {
                        sc->tmp = sc->tmp - 0x1000;
                    }
                    APOYO(o)->giro.u.z = 0;
                    APOYO(o)->giro.u.y = 0;
                    APOYO(o)->giro.u.x = 0;
                    o->coord.super = &sc->apoyo_hallado->objeto->coord;
                    func_8001CFCC(&o->coord);
                    sc->acum.nodo = &o->coord;
                    func_8001CE64(&sc->acum);
                    o->param.trans.vx = sc->acum.acc.vx;
                    o->param.trans.vy = sc->acum.acc.vy;
                    o->param.trans.vz = sc->acum.acc.vz;
                    sc->desp.z = 0;
                    sc->desp.y = 0;
                    sc->desp.x = 0;
                    o->flags14 = (o->flags14 | 4) & ~0x209;
                }
            }
        }
        GEO_CARGAR_W(&sc->desp);
        GEO_GUARDAR_W_T1(&sc->resp);
        if (o->coord.super != NULL) {
            if (o->flags14 & 0x10) {
                if ((s32)o->p70->flags08 < 0 || (o->p70->flags0C & 0x400000)) {
                    APOYO(o)->trans.vy = o->p70->max.vy - o->coord.super->param->trans.vy + 4;
                } else {
                    APOYO(o)->trans.vy = o->p70->max.vy + 4;
                }
            }
            sc->tmp_sv.vz = 0;
            sc->tmp_sv.vy = 0;
            sc->tmp_sv.vx = 0;
            sc->paso_x = 0;
            sc->paso_y = 0;
            sc->paso_z = 0x1000;
            func_8001CFCC(&o->coord);
            sc->cursor = &o->coord;
            if (sc->cursor != NULL) {
                do {
                    gte_SetRotMatrix(&sc->cursor->coord);
                    gte_ldv0(&sc->tmp_sv);
                    gte_rtv0();
                    gte_stlvnl(&sc->tmp_v);
                    ApplyMatrixSV(&sc->cursor->coord, (SVECTOR*)&sc->paso_x, (SVECTOR*)&sc->paso_x);
                    sc->tmp_v.vx += sc->cursor->coord.t[0];
                    sc->tmp_v.vy += sc->cursor->coord.t[1];
                    sc->tmp_v.vz += sc->cursor->coord.t[2];
                    sc->tmp_sv.vx = sc->tmp_v.vx;
                    sc->tmp_sv.vy = sc->tmp_v.vy;
                    sc->tmp_sv.vz = sc->tmp_v.vz;
                } while ((sc->cursor = sc->cursor->super) != NULL);
            }
            sc->rel.vx = sc->tmp_v.vx - o->param.trans.vx;
            sc->rel.vy = sc->tmp_v.vy - o->param.trans.vy;
            sc->rel.vz = sc->tmp_v.vz - o->param.trans.vz;
            GEO_CARGAR_W(&o->param.trans);
            GEO_GUARDAR_W_T1(&sc->punto);
            GEO_CARGAR_W(&sc->rel);
            GEO_GUARDAR_H_T1(&sc->tmp_sv);
            sc->res.grupo = o->w26;
            func_80019474(&sc->punto, &sc->rel, &sc->res, w);
            sc->desp.x += sc->rel.vx - (s16)sc->tmp_sv.vx;
            sc->desp.z += sc->rel.vz - (s16)sc->tmp_sv.vz;
            o->param.giro.u.y = ratan2(sc->paso_x, (s16)sc->paso_z);
        }
        if (o->p6C != NULL) {
            sc->tocado = o->p6C;
            if (((o->p6C->flags08 & 0x2000) || o->p6C->w2C == 0x22) && !(sc->reg->flags0C & 0x40)) {
                if (!(sc->reg->flags10 & 0x40000)) {
                    D_80069D60[2].vx = o->min.vx;
                    D_80069D60[0].vx = o->min.vx;
                    D_80069D60[3].vx = o->max.vx;
                    D_80069D60[1].vx = o->max.vx;
                    D_80069D60[1].vz = o->max.vz;
                    D_80069D60[0].vz = o->max.vz;
                    D_80069D60[3].vy = 0;
                    D_80069D60[2].vy = 0;
                    D_80069D60[1].vy = 0;
                    D_80069D60[0].vy = 0;
                    D_80069D60[3].vz = o->min.vz;
                    D_80069D60[2].vz = o->min.vz;
                    gte_SetRotMatrix(&sc->m);
                    k = 0;
                    D_800693DC = (s16*)D_80069D60;
                    do {
                        gte_ldv0(D_800693DC);
                        gte_rtv0();
                        gte_stsv(D_800693DC);
                        k++;
                        D_800693DC += 4;
                    } while (k < 4);
                    mx = 0;
                    ex = 0;
                    ez = 0;
                    mz = 0;
                    k = 0;
                    D_800693DC = (s16*)D_80069D60;
                    do {
                        if (D_800693DC[0] < ex) {
                            ex = D_800693DC[0];
                        } else if (mx < D_800693DC[0]) {
                            mx = D_800693DC[0];
                        }
                        if (D_800693DC[2] < ez) {
                            ez = D_800693DC[2];
                        } else if (mz < D_800693DC[2]) {
                            mz = D_800693DC[2];
                        }
                        k++;
                        D_800693DC += 4;
                    } while (k < 4);
                    D_80069D60[3].vz = 0;
                    D_80069D60[2].vz = 0;
                    D_80069D60[1].vz = 0;
                    D_80069D60[0].vz = 0;
                    D_80069D60[3].vy = 0;
                    D_80069D60[2].vy = 0;
                    D_80069D60[1].vy = 0;
                    D_80069D60[0].vy = 0;
                    D_80069D60[0].vx = (u16)sc->desp.x + ex;
                    D_80069D60[1].vx = (u16)sc->desp.x + mx;
                    D_80069D60[2].vz = (u16)sc->desp.z + ez;
                    D_80069D60[3].vz = (u16)sc->desp.z + mz;
                    sc->punto.vx = o->param.trans.vx;
                    k = 0;
                    D_800693DC = (s16*)D_80069D60;
                    sc->punto.vy = o->param.trans.vy - 0x64;
                    sc->punto.vz = o->param.trans.vz;
                    do {
                        sc->punto.vy = o->param.trans.vy;
                        GEO_CARGAR_H(D_800693DC);
                        GEO_GUARDAR_W_T1(&sc->tmp_v);
                        sc->res.grupo = o->w26;
                        sc->punto.vy = o->param.trans.vy - 0x64;
                        func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
                        k++;
                        ptr16 = D_800693DC;
                        D_800693DC += 4;
                        sc->desp.x += sc->tmp_v.vx - ptr16[0];
                        sc->desp.z += sc->tmp_v.vz - ptr16[2];
                        sc->resp.x += sc->tmp_v.vx - ptr16[0];
                        sc->resp.z += sc->tmp_v.vz - ptr16[2];
                    } while (k < 4);
                }
            }
        }
        sc->tmp = sc->desp.x + sc->desp.z;
        sc->punto.vx = o->param.trans.vx;
        sc->punto.vy = o->param.trans.vy;
        sc->tmp_v.vz = 0;
        sc->tmp_v.vy = 0;
        sc->tmp_v.vx = sc->desp.x;
        sc->punto.vz = o->param.trans.vz;
        sc->res.grupo = o->w26;
        func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
        u5 = sc->tmp_v.vx;
        sc->punto.vx = o->param.trans.vx;
        sc->punto.vy = o->param.trans.vy;
        sc->tmp_v.vy = 0;
        sc->tmp_v.vx = 0;
        sc->tmp_v.vz = sc->desp.z;
        sc->punto.vz = o->param.trans.vz;
        sc->res.grupo = o->w26;
        func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
        sc->desp.x = (s16)u5;
        sc->desp.z = sc->tmp_v.vz;
        if (!(o->flags14 & 0x81000000) || D_8001004F != 0 || (D_80069608 & 2)) {
            func_8001CBB8(o, (Movimiento*)&sc->desp, &sc->res, w);
        }
        if (sc->tmp != sc->desp.x + sc->desp.z) {
            o->flags14 |= 0x100000;
        }
        if (sc->reg->flags0C & 0x200) {
            GEO_CARGAR_W(&sc->resp);
            GEO_GUARDAR_W_T1(&sc->desp);
            if ((o->p70 != NULL && (o->p70->flags08 & 4)) || o->p6C != NULL) {
                if ((o->flags14 & 0x100000) || (s16)sc->res.grupo == -1) {
                    o->coord.super = NULL;
                    o->coord.param = (GsCOORD2PARAM*)&o->param;
                    o->p70->p6C = NULL;
                    o->p70 = NULL;
                    o->flags14 = (o->flags14 & ~0x17) | 0x200;
                }
            }
        }
        sc->resp.x = sc->desp.x;
        sc->resp.y = sc->desp.y;
        sc->resp.z = sc->desp.z;
        sc->paso_x = (u16)sc->desp.x;
        sc->paso_y = (u16)sc->desp.y;
        sc->paso_z = (u16)sc->desp.z;
        sc->tocado = func_80017478(o, (SVECTOR*)&sc->paso_x, w, 0x9A690A);
        if (sc->tocado != NULL) {
            if (!(sc->reg->flags0C & 0x20)) {
                D_80069388 = sc->tocado;
            }
            sc->punto.vx = o->param.trans.vx;
            sc->punto.vy = o->param.trans.vy;
            sc->tmp_v.vz = 0;
            sc->tmp_v.vy = 0;
            sc->tmp_v.vx = sc->paso_x;
            sc->punto.vz = o->param.trans.vz;
            sc->res.grupo = o->w26;
            func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
            u5 = sc->tmp_v.vx;
            sc->punto.vx = o->param.trans.vx;
            sc->punto.vy = o->param.trans.vy;
            sc->tmp_v.vy = 0;
            sc->tmp_v.vx = 0;
            sc->tmp_v.vz = (s16)sc->paso_z;
            sc->punto.vz = o->param.trans.vz;
            sc->res.grupo = o->w26;
            func_80019474(&sc->punto, &sc->tmp_v, &sc->res, w);
            sc->paso_x = u5;
            sc->paso_z = sc->tmp_v.vz;
            if (sc->tocado->flags08 & 8) {
                if (!(o->flags14 & 0x1000010) && (!(o->flags14 & 1) || (o->flags14 & 8)) && (s16)sc->paso_y >= -0x63) {
                    o->p70 = sc->tocado;
                    sc->paso_x = (u16)o->param.trans.vx + (u16)sc->desp.x - (u16)sc->tocado->param.trans.vx;
                    sc->paso_y = (u16)o->param.trans.vy - (u16)o->p70->param.trans.vy;
                    sc->paso_z = (u16)o->param.trans.vz + (u16)sc->desp.z - (u16)o->p70->param.trans.vz;
                    sc->ang_x = 0x1000 - o->p70->param.giro.u.x;
                    sc->ang_y = 0x1000 - o->p70->param.giro.u.y;
                    sc->ang_z = 0x1000 - o->p70->param.giro.u.z;
                    GEO_IDENTIDAD(&sc->m);
                    RotMatrixX((s16)sc->ang_x, &sc->m);
                    RotMatrixY((s16)sc->ang_y, &sc->m);
                    RotMatrixZ((s16)sc->ang_z, &sc->m);
                    gte_SetRotMatrix(&sc->m);
                    gte_ldv0(&sc->paso_x);
                    gte_rtv0();
                    gte_stlvnl(&APOYO(o)->trans);
                    APOYO(o)->trans.vy = o->p70->max.vy + 4;
                    sc->desp.y = 0;
                    o->param.trans.vy = o->p70->max.vy + o->p70->param.trans.vy + 4;
                    o->coord.param = (GsCOORD2PARAM*)APOYO(o);
                    APOYO(o)->escala.vx = 0x1000;
                    APOYO(o)->escala.vy = 0x1000;
                    APOYO(o)->escala.vz = 0x1000;
                    APOYO(o)->giro.u.y = o->param.giro.u.y - o->p70->param.giro.u.y;
                    if ((s32)o->p70->flags08 < 0 || (o->p70->flags0C & 0x400000)) {
                        if (o->p70->flags0C & 0x400000) {
                            o->coord.super = (GsCOORDINATE2*)sc->tocado->i68;
                        } else {
                            o->coord.super = *(GsCOORDINATE2**)((u8*)o->p70->u78.p + 0x10);
                        }
                        APOYO(o)->trans.vx -= o->coord.super->param->trans.vx;
                        APOYO(o)->trans.vy -= o->coord.super->param->trans.vy;
                        APOYO(o)->trans.vz -= o->coord.super->param->trans.vz;
                    } else {
                        o->coord.super = &o->p70->coord;
                    }
                    sc->tocado->p6C = o;
                    func_8001CFCC(&o->coord);
                    o->h10A = 0;
                    if (!(o->flags14 & 0x10000) && (o->flags14 & 0x208) && (D_800693D4 & 0x208)) {
                        sc->tocado->flags14 |= 0x80;
                    }
                    if (!(o->flags14 & 0x03000000) && (sc->tocado->flags14 & 0x80) && sc->tocado->w2C == 0xE && sc->tocado->registro184 != NULL) {
                        if (((RegistroEstado*)sc->tocado->registro184)->flags10 & 0x8000) {
                            sc->tocado->flags14 |= 0x04000000;
                            sc->tocado->w38 = 1;
                            sc->tocado->i34 = 1;
                            o->i34 = sc->tocado->w1C;
                        }
                        if (((RegistroEstado*)sc->tocado->registro184)->flags10 & 0x10000000) {
                            o->flags18 |= 0x40;
                        }
                    }
                    o->flags14 |= 0x14;
                    if (!(o->flags18 & 0x40)) {
                        o->flags14 &= ~0x209;
                    }
                    o->flags14 &= ~2;
                    if ((sc->tocado->flags14 & 0x80) && sc->tocado->w2C == 0xE && sc->tocado->registro184 != NULL && (((RegistroEstado*)sc->tocado->registro184)->flags10 & 0x8000)) {
                        sc->tocado->flags14 |= 0x04000000;
                        sc->tocado->w38 = 1;
                        sc->tocado->i34 = 1;
                        o->i34 = sc->tocado->w1C;
                    }
                    if ((sc->tocado->flags0C & 0x800000) && !(o->flags14 & 0x10000000)) {
                        if ((D_80069D30[0] | D_80069D30[2]) == 0) {
                            D_80069D30[0] = sc->desp.x;
                            D_80069D30[2] = sc->desp.z;
                        }
                        o->flags14 |= 0x10000000;
                    }
                }
            }
            if ((sc->tocado->flags08 & 0x4000) && !(o->flags14 & 0x11)) {
                sc->tmp_sv.vy = -0x32;
                sc->tmp_sv.vx = 0;
                sc->tmp_sv.vz = 0x96;
                RotMatrix((SVECTOR*)&o->param.giro, &sc->m);
                ApplyMatrix(&sc->m, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
                sc->tmp_v.vx += o->param.trans.vx;
                sc->tmp_v.vy += o->param.trans.vy;
                sc->tmp_v.vz += o->param.trans.vz;
                sc->tocado2 = func_800171E4(o, (VECTOR*)&sc->tmp_v, 0x4000, 0x02000000, (ConsultaVolumen*)w);
                if (sc->tocado == sc->tocado2 && sc->vel.z != 0) {
                    o->flags14 |= 0x20000;
                }
                if (sc->reg->flags0C & 0x04000000) {
                    if (sc->tocado == sc->tocado2 && sc->vel.z != 0) {
                        sc->tocado->empuje.vx = sc->desp.x;
                        sc->tocado->empuje.vz = sc->desp.z;
                        o->flags14 |= 0x4000;
                        sc->tocado->flags14 |= 0x8000;
                        sc->tocado->p70 = o;
                        goto fin_choque;
                    }
                }
                sc->tocado->flags14 |= 0x8000;
                goto copia_paso;
            } else if (o->p6C == NULL && (sc->tocado->flags08 & 0x2802) && o->p70 != sc->tocado) {
                o->flags14 |= 0x40000;
                sc->tocado->flags14 |= 0x8000;
                if (!(o->flags14 & 0x10000) && (o->flags14 & 0x208) && (s16)sc->paso_y >= -0x63) {
                    sc->tocado->flags14 |= 0x80;
                }
                if (!(o->flags14 & 0x03000000) && (sc->tocado->flags14 & 0x80) && sc->tocado->w2C == 0xE && sc->tocado->registro184 != NULL) {
                    goto marcar_estado;
                }
                if (!(sc->tocado->flags08 & 0x02000000) && !(sc->reg->flags0C & 0x40) && (s16)sc->paso_y < -0x1E) {
                    goto copia_paso;
                }
            } else if ((sc->tocado->flags08 & 0x20100) && o->p6C != sc->tocado && o->p70 != sc->tocado) {
                sc->tocado->flags14 |= 0x8000;
                if (!(o->flags14 & 0x10000) && (o->flags14 & 0x208) && (s16)sc->paso_y >= -0x63) {
                    sc->tocado->flags14 |= 0x80;
                }
                if (!(o->flags14 & 0x03000000) && (sc->tocado->flags14 & 0x80) && sc->tocado->w2C == 0xE && sc->tocado->registro184 != NULL) {
marcar_estado:
                    if (((RegistroEstado*)sc->tocado->registro184)->flags10 & 0x8000) {
                        sc->tocado->flags14 |= 0x04000000;
                        sc->tocado->w38 = 1;
                        sc->tocado->i34 = 1;
                        o->i34 = sc->tocado->w1C;
                    }
                    if (((RegistroEstado*)sc->tocado->registro184)->flags10 & 0x10000000) {
                        o->flags18 |= 0x40;
                    }
                } else if (!(o->flags14 & 0x10) && (sc->tocado->flags08 & 8) && (s16)sc->paso_y >= -0x63) {
                    sc->desp.y += (s16)sc->paso_y;
                } else if (!(sc->tocado->flags08 & 0x02000000) && (s16)sc->paso_y < -0x1E) {
copia_paso:
                    sc->desp.x = sc->paso_x;
                    sc->desp.z = (s16)sc->paso_z;
                }
            }
        } else {
            sc->desp.x = sc->resp.x;
            sc->desp.y = sc->resp.y;
            sc->desp.z = sc->resp.z;
        }
fin_choque:
        if (sc->tocado != NULL && (sc->tocado->flags08 & 0x900000)) {
            if (!(o->flags14 & 1) || (o->flags14 & 8)) {
                sc->tocado->flags14 |= 0x8000;
                D_8006965A = 5;
                D_8006965B = 0x50;
                D_8006965E = 0;
                if (o->flags14 & 0x10) {
                    o->param.giro.u.z = 0;
                    o->coord.super = NULL;
                    o->coord.param = (GsCOORD2PARAM*)&o->param;
                    o->p70->p6C = NULL;
                    o->p70 = NULL;
                    o->flags14 = (o->flags14 & ~0x214) | 2;
                    func_8001CFCC(&o->coord);
                }
                sc->tmp_sv.vx = (u16)o->param.trans.vx - (u16)sc->tocado->param.trans.vx;
                sc->tmp_sv.vy = (u16)o->param.trans.vy - (u16)sc->tocado->param.trans.vy;
                sc->tmp_sv.vz = (u16)o->param.trans.vz - (u16)sc->tocado->param.trans.vz;
                if (sc->tocado->flags08 & 0x100000) {
                    u5 = SquareRoot0((s16)sc->tmp_sv.vx * (s16)sc->tmp_sv.vx + (s16)sc->tmp_sv.vz * (s16)sc->tmp_sv.vz);
                    u6 = (s16)u5;
                } else if (sc->tocado->flags08 & 0x800000) {
                    u5 = 0;
                    u6 = 0;
                }
                if (sc->tocado->w2E >= (s16)u5) {
                    if (!(o->flags14 & 0x400)) {
                        D_800693C4 = (BugsRand() & 7) + 7;
                        D_8006938C = 0;
                        D_800693B0 = -(s16)(u16)sc->tmp_sv.vy >> 4;
                        if (D_800693B0 < 5 || (sc->tocado->flags08 & 0x800000)) {
                            D_800693B0 = 0;
                        }
                        D_8006938C = 0x400;
                        D_800693CC = 0x400;
                        o->flags14 = (o->flags14 | 0x404) & ~0x209;
                        if (o->p6C != NULL) {
                            o->p6C->flags14 &= ~0x800;
                            o->p6C->flags14 |= 0x1000;
                            o->p6C->coord.super = NULL;
                            o->p6C->coord.param = (GsCOORD2PARAM*)&o->p6C->param;
                            func_8001CFCC(&o->p6C->coord);
                            o->p6C->p70 = NULL;
                            o->p6C = NULL;
                        }
                    }
                    if (D_800693B0 != 0) {
                        if (D_800693CC < 0x800) {
                            sc->desp.y += rsin(D_800693CC) * D_800693B0 >> 12;
                            D_800693CC += 0x40;
                        } else {
                            D_800693B0 = 0;
                            D_800693CC = 0;
                        }
                    } else {
                        if (sc->tocado->flags08 & 0x100000) {
                            sc->tmp = 0x50;
                        } else if (sc->tocado->flags08 & 0x800000) {
                            sc->tmp = 0x78;
                        }
                        k1 = (u6 << 12) / sc->tocado->w2E;
                        k0 = -((s16)(u16)sc->tmp_sv.vy << 12) / -sc->tocado->max.vy + k1;
                        k0 = -(((sc->tmp - (k0 * sc->tmp >> 12)) * rsin(D_800693CC)) >> 12);
                        delta = k0;
                        if (D_800693CC < 0x400) {
                            D_800693CC += 0x40;
                        } else {
                            delta = k0 + (D_800693C4 * rsin(D_8006938C) >> 12);
                        }
                        if (sc->tocado->max.vy + 0xA < (s16)(u16)sc->tmp_sv.vy + delta) {
                            sc->desp.y += delta;
                        }
                        D_8006938C += 0x64;
                        if (D_8006938C > 0x1000) {
                            D_800693C4 = (BugsRand() & 7) + 9;
                            D_8006938C -= 0x1000;
                        }
                    }
                } else {
                    goto sin_rebote;
                }
            } else {
                goto sin_rebote;
            }
        } else {
sin_rebote:
            if (o->flags14 & 0x400) {
                o->flags14 = (o->flags14 & ~0x404) | 0x200;
            }
        }
        if (sc->tocado != NULL && (sc->tocado->flags08 & 0x80000)) {
            sc->tmp_sv.vx = (u16)o->param.trans.vx - (u16)sc->tocado->param.trans.vx;
            sc->tmp_sv.vz = (u16)o->param.trans.vz - (u16)sc->tocado->param.trans.vz;
            sc->tmp_sv.vz = ((s16)(0x1000 - (SquareRoot0((s16)sc->tmp_sv.vx * (s16)sc->tmp_sv.vx + (s16)sc->tmp_sv.vz * (s16)sc->tmp_sv.vz) << 12) / sc->tocado->max.vz) * *(s16*)&sc->tocado->w196) >> 12;
            sc->tmp_sv.vy = 0;
            sc->tmp_sv.vx = 0;
            ApplyMatrix(&sc->tocado->coord.coord, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
            sc->desp.x += sc->tmp_v.vx;
            sc->desp.z += sc->tmp_v.vz;
        }
        if (sc->reg->flags0C & 0x200) {
            APOYO(o)->trans.vy += sc->desp.y;
            func_8001CFCC(&o->coord);
            sc->acum.nodo = &o->coord;
            func_8001CE64(&sc->acum);
            GEO_CARGAR_W(&sc->acum.acc);
            GEO_GUARDAR_W_T1(&o->param.trans);
        } else if (o->coord.super != NULL) {
            sc->tmp_sv.vz = 0;
            sc->tmp_sv.vx = 0;
            sc->tmp_sv.vy = -o->p70->param.giro.u.y;
            RotMatrix(&sc->tmp_sv, &sc->m);
            ApplyMatrixLV(&sc->m, (VECTOR*)&sc->desp, (VECTOR*)&sc->desp);
            GEO_CARGAR_W(&sc->desp);
            GEO_SUMAR_W(&APOYO(o)->trans);
            func_8001CFCC(&o->coord);
            sc->acum.nodo = &o->coord;
            func_8001CE64(&sc->acum);
            GEO_CARGAR_W(&sc->acum.acc);
            GEO_GUARDAR_W_T1(&o->param.trans);
            func_8001CFCC(&o->coord);
        } else if (sc->reg->flags0C & 0x8000) {
            GEO_CARGAR_W(&sc->desp);
            GEO_SUMAR_W(&o->param.trans);
            TransMatrix(&o->coord.coord, (VECTOR*)&o->coord.param->trans);
        } else {
            GEO_CARGAR_W(&sc->desp);
            GEO_SUMAR_W(&o->param.trans);
            func_8001CF50(o);
        }
        if (o->flags14 & 0x10) {
            if (o->p70 == NULL || !(o->p70->flags08 & 8)) {
                o->flags14 = (o->flags14 & ~0x214) | 2;
            }
            if (o->flags14 & 0x10) {
                if (func_80018664(o, o->p70, w) == 0 || (o->flags14 & 2)) {
                    sc->rel.vy = 0;
                    sc->rel.vx = o->param.trans.vx - o->p70->param.trans.vx;
                    sc->rel.vz = o->param.trans.vz - o->p70->param.trans.vz;
                    GEO_CARGAR_W(&o->p70->param.trans);
                    GEO_GUARDAR_W_T1(&sc->punto);
                    sc->punto.vy = o->param.trans.vy;
                    sc->res.grupo = o->w26;
                    func_80019474(&sc->punto, &sc->rel, &sc->res, w);
                    o->param.trans.vx = o->p70->param.trans.vx + sc->rel.vx;
                    o->coord.param = (GsCOORD2PARAM*)&o->param;
                    o->param.giro.u.z = 0;
                    o->coord.super = NULL;
                    o->param.trans.vz = o->p70->param.trans.vz + sc->rel.vz;
                    o->p70->p6C = NULL;
                    o->p70 = NULL;
                    o->flags14 = (o->flags14 & ~0x214) | 2;
                    func_8001CFCC(&o->coord);
                } else {
                    o->p70->flags14 |= 0x8000;
                }
            }
        }
        if (sc->tocado == NULL && (sc->desp.x | sc->desp.y | sc->desp.z) == 0) {
            sc->tmp_sv.vy = -0x32;
            sc->tmp_sv.vx = 0;
            sc->tmp_sv.vz = 0x64;
            RotMatrix((SVECTOR*)&o->param.giro, &sc->m);
            ApplyMatrix(&sc->m, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
            sc->tmp_v.vx += o->param.trans.vx;
            sc->tmp_v.vy += o->param.trans.vy;
            sc->tmp_v.vz += o->param.trans.vz;
            sc->tocado = func_800171E4(o, (VECTOR*)&sc->tmp_v, 0x2802, 0x02000000, (ConsultaVolumen*)w);
            if (sc->tocado != NULL) {
                o->flags14 |= 0x40000;
                D_80069388 = sc->tocado;
                sc->tocado->flags14 |= 0x8000;
            }
        }
        if (!(D_800693D4 & 0x200) && (D_800693D4 & 0x12) && (o->flags14 & 0x200)) {
            o->flags18 |= 0x200;
        }
        if (sc->trans != NULL && sc->reg->w0A != 0) {
            sc->trans = (Transicion*)o->apoyos;
            while (sc->trans != NULL && sc->trans->id != sc->reg->w0A) {
                sc->trans = sc->trans->sig;
            }
            sc->estado_sig = 0xFFF3;
            sc->cand = sc->trans;
            if (sc->cand != NULL) {
                do {
                    if (sc->cand->id != sc->reg->w0A) {
                        break;
                    }
                    if (sc->cand->m1C != 0 && (o->p6C == NULL || !(o->p6C->flags08 & sc->cand->m1C))) {
                        continue;
                    }
                    if (sc->cand->m20 != 0 && (o->p70 == NULL || !(o->p70->flags08 & sc->cand->m20))) {
                        if (!(sc->cand->m20 & 0x8000)) {
                            continue;
                        }
                        if (o->p70 != NULL && o->p70->w2C == 0xE && o->p70->registro184 != NULL) {
                            vs = ((RegistroEstado*)o->p70->registro184)->flags10 & 0x10000000;
                        } else {
                            vs = o->flags18 & 0x40;
                        }
                        if (vs == 0) {
                            continue;
                        }
                    }
                    if (sc->cand->m24 != 0) {
                        if (sc->cand->w18 & 2) {
                            if (o->flags14 & sc->cand->m24) {
                                continue;
                            }
                        } else if (!(o->flags14 & sc->cand->m24)) {
                            continue;
                        }
                    }
                    if (sc->cand->m28 != 0) {
                        if (sc->cand->w18 & 1) {
                            if (o->flags18 & sc->cand->m28) {
                                continue;
                            }
                        } else if (!(o->flags18 & sc->cand->m28)) {
                            continue;
                        }
                    }
                    if ((sc->cand->w8 == 0 || (sc->cand->w8 & D_8001000A)) && ((sc->cand->w6 == (D_8001000A & sc->cand->w6)) || sc->cand->w6 == 0xFFF1) && TestLogicCond(o, sc->cand->item)) {
                        RunLogicAction(o, sc->cand->item);
                        if (sc->cand->wA != 0xFFF3) {
                            sc->estado_sig = sc->cand->wA;
                        }
                        break;
                    }
                } while ((sc->cand = sc->cand->sig) != NULL);
            }
            if (sc->cand != NULL) {
                if (sc->cand->wC != 0 && o->p6C != NULL) {
                    if (sc->cand->wC == 0xD3) {
                        o->p6C->flags14 |= 0x100;
                        o->p6C->p70 = NULL;
                        o->p6C = NULL;
                    } else {
                        o->p6C->w17E = sc->cand->wC;
                        o->p6C->trabajo.i14 = 0;
                        o->p6C->w17C = 0;
                    }
                }
            }
            if (sc->estado_sig != 0xFFF3) {
                o->w17E = 0;
                if (sc->sec->id == 5 || sc->sec->id == 0x12) {
                    if (o->flags14 & 0x200) {
                        o->flags14 &= ~0x200;
                        sc->estado_sig = 7;
                    }
                }
                sc->sec = o->secuencias;
                while (sc->sec != NULL && sc->sec->id != sc->estado_sig) {
                    sc->sec = sc->sec->sig;
                }
                sc->paso_vigente = sc->sec->desplazamiento;
                sc->reg = (RegistroEstado*)o->bloque;
                while (sc->reg != NULL && sc->reg->id != sc->paso_vigente) {
                    sc->reg = sc->reg->sig;
                }
                sc->trans = (Transicion*)o->apoyos;
                while (sc->trans != NULL && sc->trans->id != sc->reg->w0A) {
                    sc->trans = sc->trans->sig;
                }
                o->w17C = sc->estado_sig;
                hw = (u16)o->trabajo.i14;
                o->p180 = sc->sec;
                o->registro184 = (RegistroAnim*)sc->reg;
                o->trabajo.i14 = 0;
                o->i68 = 0;
                o->nodo188 = (NodoSecuencia*)sc->trans;
                D_80069584 = hw;
                if (sc->reg->flags10 & 0x800) {
                    o->flags14 &= ~0x209;
                }
            }
        }
        GEO_CERO_WH(&sc->tmp_sv);
        if (o->p6C == NULL && (sc->reg->flags0C & 0x20) && o->i68 != 0 && D_80069388 != NULL) {
            sc->tocado = D_80069388;
            if ((sc->tocado->flags08 & 0x2802) && o->p70 != sc->tocado) {
                if (sc->tocado->flags08 & 0x2000) {
                    sc->tmp_sv.vx = 0;
                    sc->tmp_sv.vy = -0x32;
                    sc->tmp_sv.vz = 0x64;
                    RotMatrix((SVECTOR*)&o->param.giro, &sc->m);
                    ApplyMatrix(&sc->m, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
                    sc->tmp_v.vx += o->param.trans.vx;
                    sc->tmp_v.vy += o->param.trans.vy;
                    sc->tmp_v.vz += o->param.trans.vz;
                    sc->tocado = func_800171E4(o, (VECTOR*)&sc->tmp_v, 0x2802, 0x02000000, (ConsultaVolumen*)w);
                    if (sc->tocado == NULL) {
                        sc->tmp_sv.vx = -0x64;
                        sc->tmp_sv.vy = -0x32;
                        sc->tmp_sv.vz = 0x64;
                        ApplyMatrix(&sc->m, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
                        sc->tmp_v.vx += o->param.trans.vx;
                        sc->tmp_v.vy += o->param.trans.vy;
                        sc->tmp_v.vz += o->param.trans.vz;
                        sc->tocado = func_800171E4(o, (VECTOR*)&sc->tmp_v, 0x2802, 0x02000000, (ConsultaVolumen*)w);
                        if (sc->tocado == NULL) {
                            sc->tmp_sv.vx = 0x64;
                            sc->tmp_sv.vy = -0x32;
                            sc->tmp_sv.vz = 0x64;
                            ApplyMatrix(&sc->m, &sc->tmp_sv, (VECTOR*)&sc->tmp_v);
                            sc->tmp_v.vx += o->param.trans.vx;
                            sc->tmp_v.vy += o->param.trans.vy;
                            sc->tmp_v.vz += o->param.trans.vz;
                            sc->tocado = func_800171E4(o, (VECTOR*)&sc->tmp_v, 0x2802, 0x02000000, (ConsultaVolumen*)w);
                        }
                    }
                }
                if (sc->tocado != NULL) {
                    if (sc->tocado->p70 != NULL && sc->tocado->p70->p6C == sc->tocado) {
                        sc->tocado->p70->p6C = NULL;
                        sc->tocado->p70 = NULL;
                    }
                    o->p6C = sc->tocado;
                    sc->tocado->flags14 &= 0xFFF7EFED;
                    sc->tocado->flags14 |= 0x800;
                    sc->tocado->coord.super = (GsCOORDINATE2*)o->i68;
                    sc->tocado->coord.param = (GsCOORD2PARAM*)PORTADO(sc->tocado);
                    D_80069388 = NULL;
                    GEO_CERO_W(&PORTADO(sc->tocado)->trans);
                    GEO_CERO_WH(&PORTADO(sc->tocado)->giro);
                    PORTADO(sc->tocado)->escala.vz = 0x1000;
                    PORTADO(sc->tocado)->escala.vy = 0x1000;
                    PORTADO(sc->tocado)->escala.vx = 0x1000;
                    sc->tocado->p70 = o;
                    func_8001CFCC(&sc->tocado->coord);
                }
            }
        }
        if (sc->reg->flags0C & 0x2000) {
            o->flags14 = (o->flags14 | 0x10000) & ~0x209;
        } else {
            o->flags14 = o->flags14 & 0xFFFEFFFF;
        }
    } else {
        sc->acum.nodo = &o->coord;
        func_8001CE64(&sc->acum);
        o->param.trans.vx = sc->acum.acc.vx;
        o->param.trans.vy = sc->acum.acc.vy;
        o->param.trans.vz = sc->acum.acc.vz;
    }
    if (o->trabajo.i14 != sc->reg->s06) {
        func_8001F268(o, &o->trabajo, sc->reg->s06, sc->reg->s08, w);
    } else if (!(sc->reg->s08 & 0x8000) || sc->vel.z != 0) {
        if (func_8001F268(o, &o->trabajo, 0, 0, w) == 0x100) {
            if (sc->sec != NULL && sc->sec->id == 1) {
                o->w17E = BugsRand() & 3;
            }
            if (D_80010000 == 3) {
                func_8003F06C(o, 0x4A, 2, D_8006967C);
            }
            o->w17E = o->w17E + 1;
            o->trabajo.i14 = 0;
            if (o->flags14 & 0x01000000) {
                func_8001D994(o);
            }
        } else if ((sc->reg->flags0C & 0x80) && (o->flags14 & 0x12)) {
            if (D_80010000 == 3) {
                func_8003F06C(o, 0x4A, 2, D_8006967C);
            }
            o->trabajo.i14 = 0;
            o->w17E = o->w17E + 1;
        }
    }
    func_8001D414(sc->reg->id);
    if (sc->reg->flags10 & 0x2000) {
        sc->tocado = o->p6C;
        if (o->p6C != NULL) {
            o->min.vx = (u16)sc->tocado->min.vx;
            o->min.vy = (u16)sc->tocado->min.vy;
            o->min.vz = (u16)sc->tocado->min.vz;
            o->max.vx = (u16)sc->tocado->max.vx;
            o->max.vy = (u16)sc->tocado->max.vy;
            o->max.vz = (u16)sc->tocado->max.vz;
            o->w2E = o->p6C->w2E;
            o->alcance2 = o->p6C->alcance2;
        }
    } else {
        sc->tocado = o->p6C;
        if (o->p6C != NULL) {
            if ((sc->tocado->flags08 & 0x2000) && !(sc->reg->flags0C & 0x40)) {
                o->max.vx = 0x46;
                o->min.vx = -0x46;
                o->min.vz = -0x28;
                sum = (u16)sc->tocado->max.vz + ((u16)sc->tocado->s20 + 0x5A);
                o->max.vz = sum;
                cuad = o->min.vx * o->min.vx + o->min.vz * o->min.vz;
                rr = 0x46 * 0x46 + sum * sum;
                if (rr < cuad) {
                    rr = cuad;
                }
                ss = rr;
                o->w2E = SquareRoot0(ss);
                o->alcance2 = ss;
            } else {
                goto caja_defecto;
            }
        } else {
caja_defecto:
            o->min.vx = -0x46;
            o->min.vz = -0x28;
            o->max.vx = 0x46;
            o->max.vz = 0x28;
            o->w2E = 0x50;
            o->alcance2 = 0x1900;
        }
    }
    pos = &o->param.trans;
    if ((o->flags14 & 0x01000000) && !((u8)D_8006966A & 2) && (s16)((u16)o->trabajo.w00 - (u16)o->trabajo.h02) * o->trabajo.b05 < 9) {
        D_800694E0 = 0;
        D_800694E1 = 0;
        D_800694E8 = 0;
        func_8003AA7C(2, 0x200);
        pos = &o->param.trans;
    }
    GEO_CARGAR_W(pos);
    GEO_GUARDAR_W_T1(&sc->punto);
    sc->res.grupo = o->w26;
    func_8001C134((s32*)&sc->punto, &sc->res, w);
    if (sc->res.flags & 4) {
        GEO_CERO_W(&sc->desp);
        GEO_CARGAR_W(D_8006AD70);
        GEO_GUARDAR_W_T1(pos);
        func_8001CBB8(o, (Movimiento*)&sc->desp, &sc->res, w);
        o->param.trans.vy = o->param.trans.vy + sc->desp.y;
        D_8006AD74 = o->param.trans.vy;
    } else {
        D_8006AD70[0] = o->param.trans.vx;
        D_8006AD70[1] = o->param.trans.vy;
        D_8006AD70[2] = o->param.trans.vz;
    }
    if (o->p6C != NULL) {
        o->p6C->w26 = o->w26;
    }
    o->flags14 &= 0x7FEDEFFF;
    o->flags18 &= ~0x241;
    if ((o->flags14 & 0x16) || o->p70 != NULL) {
        o->flags14 &= ~0x200;
    }
    if (D_80069690 != 0) {
        if (D_80069690 < 0x1E) {
            o->flags14 &= 0xFDFFFFDF;
        }
        D_80069690 = D_80069690 - 1;
    }
    if (!(o->flags14 & 0x01000000)) {
        func_8001E1A4(o, (ConsultaPlano*)w);
    }
    o->w1B4 = sc->desp.x | sc->desp.y | sc->desp.z;
    if (o->p70 != NULL && !(o->p70->flags08 & 8)) {
        o->w1B4 = (sc->desp.x | sc->desp.y | sc->desp.z) + 1;
    }
    if (o->p6C != NULL && D_80069558 != NULL) {
        o->p6C->w26 = *D_80069558;
    }
    D_8006AC30[0] = D_8006ACE0[0];
    D_8006AC30[2] = D_8006ACE0[2];
    GEO_CARGAR_WH(D_8006ACEC);
    GEO_GUARDAR_WH(D_8006AC3C);
    GEO_CARGAR_W(D_8006ACF4);
    GEO_GUARDAR_W_T1(D_8006AC44);
    D_8006ACE0[0] = 0;
    D_8006ACE0[2] = 0x1388;
    if ((o->flags14 & 0x0100021F) == 2) {
        D_8006AD30[0] = o->param.trans.vx;
        D_8006AD30[1] = o->param.trans.vy;
        D_8006AD30[2] = o->param.trans.vz;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles", func_80020B90);
#endif
