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
 * El __asm__ va dentro de una funcion de relleno llamada __maspsx_include_asm_hack_<NAME>:
 * con un umbral de datos pequenos (-G) mayor que cero el compilador emite todos los cuerpos de
 * funcion al final del archivo, DESPUES de cualquier __asm__ de nivel superior, y un archivo que
 * mezcla C e INCLUDE_ASM saldria con las funciones en otro orden que el original. Dentro de una
 * funcion, el ensamblador incluido sigue el mismo orden de emision que las funciones en C, con
 * cualquier -G. maspsx reconoce el prefijo del nombre y conserva solo las lineas marcadas con
 * "# maspsx-keep" (el resto del relleno, prologo y epilogo, se descarta).
 *
 * Los .set noat/noreorder son necesarios porque el ensamblador original usa $at y rellena
 * a mano los huecos de salto; al terminar se restauran los valores que espera la salida del
 * compilador.
 */
#define INCLUDE_ASM(FOLDER, NAME) \
    void __maspsx_include_asm_hack_##NAME() \
    { \
        __asm__( \
            ".text # maspsx-keep\n" \
            "\t.align\t2 # maspsx-keep\n" \
            "\t.set noreorder # maspsx-keep\n" \
            "\t.set noat # maspsx-keep\n" \
            ".include \"" FOLDER "/" #NAME ".s\" # maspsx-keep\n" \
            "\t.set reorder # maspsx-keep\n" \
            "\t.set at # maspsx-keep\n"); \
    }

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
