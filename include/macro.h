#ifndef MACRO_H
#define MACRO_H

/*
 * Macros del ensamblador incluido en los archivos C.
 *
 * La primera sentencia carga una sola vez las macros de etiquetas (glabel, endlabel,
 * nonmatching...) que usan los archivos de asm/nonmatchings/. Se carga aqui y no en cada
 * INCLUDE_ASM porque el ensamblador rechaza redefinir una macro.
 */
__asm__(".include \"macro.inc\"\n");

/*
 * INCLUDE_ASM(carpeta, funcion)
 *
 * Inserta en .text el ensamblador original de una funcion que todavia no esta
 * descompilada. FOLDER es una cadena literal con la carpeta (relativa a la raiz del
 * repositorio) y NAME el nombre de la funcion sin comillas ni extension.
 *
 * Los .set noat/noreorder son necesarios porque el ensamblador original usa $at y rellena
 * a mano los huecos de salto; al terminar se restauran los valores que espera la salida del
 * compilador.
 */
#define INCLUDE_ASM(FOLDER, NAME) \
    __asm__( \
        ".section .text\n" \
        "    .set noat\n" \
        "    .set noreorder\n" \
        "    .include \"" FOLDER "/" #NAME ".s\"\n" \
        "    .set reorder\n" \
        "    .set at\n")

/*
 * INCLUDE_RODATA(carpeta, simbolo)
 *
 * Inserta en .rodata el dato de solo lectura (cadena, tabla de punteros o de saltos) original
 * de un simbolo que ninguna funcion del archivo referencia directamente: los que si
 * referencia una funcion viajan dentro del .s de esa funcion. FOLDER es la carpeta literal y
 * NAME el nombre del simbolo; el .s ya trae su propia directiva de seccion, y al terminar se
 * vuelve a .text, que es lo que espera la salida del compilador.
 */
#define INCLUDE_RODATA(FOLDER, NAME) \
    __asm__( \
        ".section .rodata\n" \
        "    .include \"" FOLDER "/" #NAME ".s\"\n" \
        ".section .text\n")

#endif
