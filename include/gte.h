#ifndef GTE_H
#define GTE_H

/*
 * Comandos del coprocesador GTE para el flujo de compilacion del proyecto.
 *
 * Las macros de comando de psyq/INLINE_C.H (gte_rtv0, gte_rtpt...) emiten "nop; nop; .word
 * 0x....": la palabra es una ficha que el programa DMPSX del SDK sustituye despues por la
 * instruccion real. Este flujo (cc1 -> maspsx -> as) no ejecuta DMPSX y el objeto conserva la
 * ficha, que no coincide con el original. Aqui se redefinen todos los comandos con el
 * mnemonico que ensambla gte_macros.inc (cargado por macro.h), que produce la misma palabra
 * que el ejecutable (por ejemplo rtv0 -> 0x4A486012). Los dos nop forman parte del comando:
 * el original los trae.
 *
 * Uso: incluir este archivo en lugar de psyq/INLINE_C.H. Las macros de carga y lectura de
 * registros (gte_ldv0, gte_stsxy...) son ensamblador directo (lwc2, swc2, mtc2, ctc2...) y
 * se usan tal cual. Para los compuestos de psyq/GTEMAC.H, incluirlos despues de este archivo:
 * sus macros se expanden en el punto de uso y ya llaman a los comandos redefinidos.
 *
 * gte_rt no tiene mnemonico en gte_macros.inc: usarlo es un error de compilacion a
 * proposito, para que no salga una ficha sin sustituir.
 */
#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/INLINE_C.H"

#undef gte_rtps
#define gte_rtps() __asm__ volatile ("nop; nop; rtps")

#undef gte_rtpt
#define gte_rtpt() __asm__ volatile ("nop; nop; rtpt")

#undef gte_rtv0
#define gte_rtv0() __asm__ volatile ("nop; nop; rtv0")

#undef gte_rtv1
#define gte_rtv1() __asm__ volatile ("nop; nop; rtv1")

#undef gte_rtv2
#define gte_rtv2() __asm__ volatile ("nop; nop; rtv2")

#undef gte_rtir
#define gte_rtir() __asm__ volatile ("nop; nop; rtir12")

#undef gte_rtir_sf0
#define gte_rtir_sf0() __asm__ volatile ("nop; nop; rtir0")

#undef gte_rtv0tr
#define gte_rtv0tr() __asm__ volatile ("nop; nop; rtv0tr")

#undef gte_rtv1tr
#define gte_rtv1tr() __asm__ volatile ("nop; nop; rtv1tr")

#undef gte_rtv2tr
#define gte_rtv2tr() __asm__ volatile ("nop; nop; rtv2tr")

#undef gte_rtirtr
#define gte_rtirtr() __asm__ volatile ("nop; nop; rtirtr")

#undef gte_rtv0bk
#define gte_rtv0bk() __asm__ volatile ("nop; nop; rtv0bk")

#undef gte_rtv1bk
#define gte_rtv1bk() __asm__ volatile ("nop; nop; rtv1bk")

#undef gte_rtv2bk
#define gte_rtv2bk() __asm__ volatile ("nop; nop; rtv2bk")

#undef gte_rtirbk
#define gte_rtirbk() __asm__ volatile ("nop; nop; rtirbk")

#undef gte_ll
#define gte_ll() __asm__ volatile ("nop; nop; ll")

#undef gte_llv0
#define gte_llv0() __asm__ volatile ("nop; nop; llv0")

#undef gte_llv1
#define gte_llv1() __asm__ volatile ("nop; nop; llv1")

#undef gte_llv2
#define gte_llv2() __asm__ volatile ("nop; nop; llv2")

#undef gte_llir
#define gte_llir() __asm__ volatile ("nop; nop; llvir")

#undef gte_llv0tr
#define gte_llv0tr() __asm__ volatile ("nop; nop; llv0tr")

#undef gte_llv1tr
#define gte_llv1tr() __asm__ volatile ("nop; nop; llv1tr")

#undef gte_llv2tr
#define gte_llv2tr() __asm__ volatile ("nop; nop; llv2tr")

#undef gte_llirtr
#define gte_llirtr() __asm__ volatile ("nop; nop; llirtr")

#undef gte_llv0bk
#define gte_llv0bk() __asm__ volatile ("nop; nop; llv0bk")

#undef gte_llv1bk
#define gte_llv1bk() __asm__ volatile ("nop; nop; llv1bk")

#undef gte_llv2bk
#define gte_llv2bk() __asm__ volatile ("nop; nop; llv2bk")

#undef gte_llirbk
#define gte_llirbk() __asm__ volatile ("nop; nop; llirbk")

#undef gte_lc
#define gte_lc() __asm__ volatile ("nop; nop; lc")

#undef gte_lcv0
#define gte_lcv0() __asm__ volatile ("nop; nop; lcv0")

#undef gte_lcv1
#define gte_lcv1() __asm__ volatile ("nop; nop; lcv1")

#undef gte_lcv2
#define gte_lcv2() __asm__ volatile ("nop; nop; lcv2")

#undef gte_lcir
#define gte_lcir() __asm__ volatile ("nop; nop; lcvir")

#undef gte_lcv0tr
#define gte_lcv0tr() __asm__ volatile ("nop; nop; lcv0tr")

#undef gte_lcv1tr
#define gte_lcv1tr() __asm__ volatile ("nop; nop; lcv1tr")

#undef gte_lcv2tr
#define gte_lcv2tr() __asm__ volatile ("nop; nop; lcv2tr")

#undef gte_lcirtr
#define gte_lcirtr() __asm__ volatile ("nop; nop; lcirtr")

#undef gte_lcv0bk
#define gte_lcv0bk() __asm__ volatile ("nop; nop; lev0bk")

#undef gte_lcv1bk
#define gte_lcv1bk() __asm__ volatile ("nop; nop; lev1bk")

#undef gte_lcv2bk
#define gte_lcv2bk() __asm__ volatile ("nop; nop; lev2bk")

#undef gte_lcirbk
#define gte_lcirbk() __asm__ volatile ("nop; nop; leirbk")

#undef gte_dpcl
#define gte_dpcl() __asm__ volatile ("nop; nop; dpcl")

#undef gte_dpcs
#define gte_dpcs() __asm__ volatile ("nop; nop; dpcs")

#undef gte_dpct
#define gte_dpct() __asm__ volatile ("nop; nop; dpct")

#undef gte_intpl
#define gte_intpl() __asm__ volatile ("nop; nop; intpl")

#undef gte_sqr12
#define gte_sqr12() __asm__ volatile ("nop; nop; sqr 1")

#undef gte_sqr0
#define gte_sqr0() __asm__ volatile ("nop; nop; sqr 0")

#undef gte_ncs
#define gte_ncs() __asm__ volatile ("nop; nop; ncs")

#undef gte_nct
#define gte_nct() __asm__ volatile ("nop; nop; nct")

#undef gte_ncds
#define gte_ncds() __asm__ volatile ("nop; nop; ncds")

#undef gte_ncdt
#define gte_ncdt() __asm__ volatile ("nop; nop; ncdt")

#undef gte_nccs
#define gte_nccs() __asm__ volatile ("nop; nop; nccs")

#undef gte_ncct
#define gte_ncct() __asm__ volatile ("nop; nop; ncct")

#undef gte_cdp
#define gte_cdp() __asm__ volatile ("nop; nop; cdp")

#undef gte_cc
#define gte_cc() __asm__ volatile ("nop; nop; cc")

#undef gte_nclip
#define gte_nclip() __asm__ volatile ("nop; nop; nclip")

#undef gte_avsz3
#define gte_avsz3() __asm__ volatile ("nop; nop; avsz3")

#undef gte_avsz4
#define gte_avsz4() __asm__ volatile ("nop; nop; avsz4")

#undef gte_op12
#define gte_op12() __asm__ volatile ("nop; nop; op12")

#undef gte_op0
#define gte_op0() __asm__ volatile ("nop; nop; op0")

#undef gte_gpf12
#define gte_gpf12() __asm__ volatile ("nop; nop; gpf12")

#undef gte_gpf0
#define gte_gpf0() __asm__ volatile ("nop; nop; gpf0")

#undef gte_gpl12
#define gte_gpl12() __asm__ volatile ("nop; nop; gpl12")

#undef gte_gpl0
#define gte_gpl0() __asm__ volatile ("nop; nop; gpl0")

#undef gte_rt
#define gte_rt() gte_rt_sin_mnemonico_en_gte_macros_inc

#endif
