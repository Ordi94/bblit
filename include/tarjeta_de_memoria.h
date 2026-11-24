#ifndef TARJETA_DE_MEMORIA_H
#define TARJETA_DE_MEMORIA_H

#include "common.h"

/*
 * Desplazamiento en bytes del grupo `ranura` dentro del directorio leido de la tarjeta (D_800697B0), 120 bytes por
 * indice. SondearTarjeta lo suma a la posicion de la entrada en cada acceso del recorrido que limpia los nombres.
 *
 * Es una funcion en linea y no la expresion `ranura * 120` repetida: el producto llega ya calculado en un registro
 * a la suma de la direccion y queda como segundo sumando, como en el original. La definicion vive en la cabecera
 * porque el particionador solo admite en los `.c` definiciones con un tipo de retorno de una palabra.
 */
static __inline__ s32 DesplazamientoRanura(s32 ranura)
{
    return ranura * 120;
}

#endif
