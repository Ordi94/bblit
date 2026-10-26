# Identificación del compilador

El ejecutable `SLUS_008.38` no contiene ninguna cadena de versión de GCC. La versión se
determina de forma empírica: se toman funciones hoja del juego, se escribe C equivalente y se
compara el resultado de cada compilador con el código original mediante `asm-differ`.

## Candidatos

Las bibliotecas Sony embebidas (`bios.c 1.86` de marzo de 1997, `sys.c 1.140` de enero de
1998) acotan el SDK a la serie 4.x. Se evaluaron los dos compiladores de esa serie que se
ejecutan de forma nativa en Windows de 64 bits:

| Compilador | Procede de | Versión interna | ASPSX asociado |
|---|---|---|---|
| GCC 2.7.2 | `psyq-4.1` (diciembre de 1997) | `cygnus-2.7.2-970404 SN32.3.7.0004` | 2.67 |
| GCC 2.8.1 | `psyq-4.4` (octubre de 1998) | `2.8.1 SN32 BUILD 4.0.0010` | 2.79 (binario del SDK); el proyecto emula la 2.80 con `maspsx` |

Los paquetes 4.6 y 4.7 traen GCC 2.95.2 (octubre de 1999) y quedan fuera: son posteriores a la
fecha del juego (mayo de 1999).

## Método

1. `splat` genera el ensamblador de cada función en `asm/nonmatchings/<archivo>/<función>.s`
   (o en `asm/matchings/` si ya está en C). Cada uno se ensambla con `mipsel-none-elf-as` a un
   objeto ELF (el objetivo); `python tools/build.py diff <función>` automatiza este paso.
2. `m2c --target mipsel-gcc-c` produce un borrador en C de la función; se reescribe a mano.
3. El C se compila con `CC1PSX.EXE -quiet -O2 -G<g>` (y `-O1` cuando `-O2` no coincide). El
   umbral `-G` se declara por archivo en `config/opciones_compilacion.toml`: los archivos cuyo
   original usa datos pequenos (`desplazamiento($gp)` o almacenes simbolicos a variables de
   `0x80069xxx`) se compilan con el `-G8` del original; `-G0` queda solo para los archivos donde
   aun no se ha demostrado que haga falta otro valor. La cabecera `gp0 = 0` del ejecutable no
   significa que el programa no use `$gp`: es el valor inicial, y el arranque lo fija en
   `0x80069320`. Ver «Datos pequenos y `$gp`» en `docs/DESCOMPILACION.md`.
4. La salida de ensamblador pasa por `maspsx --aspsx-version=<versión>` y por GNU `as`
   (`-EL -march=r3000 -mips1`; `maspsx` fuerza `-G0` en `as` y recibe el `-G` real aparte) para
   producir un objeto ELF con los mismos reubicables que el original.
5. `asm-differ -o --file candidato.o --ref-file objetivo.o <función> --format=json` compara
   ambos. El campo `current_score` vale 0 solo si las instrucciones y los símbolos
   coinciden por completo.

`maspsx` recibe la versión de ASPSX del SDK al que corresponde cada compilador. En la función
que coincide se comprobó que el resultado no depende de esa versión (2.67, 2.79 y 2.86 dan la
misma puntuación); ver «Versión de ASPSX» para la que se fija y por qué.

Las rutas de los componentes salen de `python -m tools.toolchain ruta <componente> <alias>`
(por ejemplo `ruta psyq-4.4 cc1psx`).

## Funciones evaluadas

Todas son funciones hoja del propio juego (no de las bibliotecas Sony) elegidas del
desensamblado; los nombres siguen la convención `func_80XXXXXX`.

| Función | Descripción | Forma |
|---|---|---|
| `func_8002FA38` | Compara un byte de un registro con una entrada de tabla (igualdad) | 10 instrucciones, sin ramas |
| `func_8002FB18` | Igual que la anterior con comparación «mayor que» | 8 instrucciones, sin ramas |
| `func_80030D60` | Comprueba que un valor leído de una estructura global esté en un rango | 17 instrucciones, 2 ramas |
| `func_80036204` | Recorre una reserva de ranuras con paso variable y libera la primera marcada | 19 instrucciones, bucle |
| `func_8002F990` | Operación aritmética sobre un registro de 16 bits dividido en dos bytes | 26 instrucciones, 4 ramas |

## Resultados

Puntuación de `asm-differ` (0 es coincidencia exacta; cuanto mayor, más distinto).

| Función | GCC 2.7.2 `-O2` | GCC 2.7.2 `-O1` | GCC 2.8.1 `-O2` | GCC 2.8.1 `-O1` | Veredicto 2.7.2 | Veredicto 2.8.1 |
|---|---|---|---|---|---|---|
| `func_8002FA38` | 0 | 60 | 0 | 330 | coincide en `-O2` | coincide en `-O2` |
| `func_8002FB18` | 0 | 60 | 0 | 330 | coincide en `-O2` | coincide en `-O2` |
| `func_80030D60` | 505 | 755 | 505 | 755 | no coincide | no coincide |
| `func_80036204` | 420 | 430 | **0** | 10 | no coincide | **coincide en `-O2`** |
| `func_8002F990` | 705 | 1095 | 350 | 880 | no coincide | no coincide |

Las dos primeras no discriminan: son tan simples que ambos compiladores producen el mismo
código. `func_80036204` sí discrimina. Con tres formulaciones distintas del mismo bucle
(`while`, `for`, `do/while` con guarda) GCC 2.8.1 `-O2` produce exactamente el código original
y GCC 2.7.2 produce siempre la misma variante distinta (puntuación 420): 2.7.2 calcula antes
del bucle una dirección derivada del puntero (`addiu v1, a0, 4`) y accede al campo con
desplazamiento 0, mientras que el original y 2.8.1 mantienen el puntero base y acceden con
desplazamiento 4.

### Código C de las funciones que coinciden

```c
extern unsigned char D_8006AA70[];

int func_8002FA38(void *a0, unsigned char *a1)
{
    return D_8006AA70[a1[2]] == a1[1];
}

int func_8002FB18(void *a0, unsigned char *a1)
{
    return D_8006AA70[a1[2]] > a1[1];
}

struct Ranura {
    int dato;
    unsigned int marca;
};

/* Devuelve la primera ranura marcada y la libera. */
struct Ranura *func_80036204(unsigned char *base, int paso, int total)
{
    unsigned char *p;
    unsigned char *fin;

    p = base;
    fin = p + total;
    while (p < fin) {
        if (((struct Ranura *)p)->marca & 1) {
            ((struct Ranura *)p)->marca = 0;
            ((struct Ranura *)p)->dato = 0;
            return (struct Ranura *)p;
        }
        p = base + paso;
        base = p;
    }
    return 0;
}
```

### Diferencias observadas en las funciones que no coinciden

- `func_80030D60`: en el original el desplazamiento aritmético se escribe sobre el registro
  `a0` (el primer argumento, que la función no usa) y el valor 1 se produce con una rama
  (`beqz` con el `li` en el hueco de retardo); GCC, con cualquiera de las dos versiones,
  reutiliza el registro del dato (`v1`) y convierte la rama en un `xori`. Indica que el C
  original combina las condiciones de otra forma (o usa una variable intermedia con otro
  tipo) y la misma versión de GCC produce el resultado.
- `func_8002F990`: el original lee los dos bytes con una única instrucción `lui` (los dos
  símbolos comparten la parte alta de la dirección) y GCC genera dos `lui` cuando son
  variables externas distintas. No hace falta una estructura `extern`: un puntero constante a
  `0x80010000` (`Est* e = (Est*)0x80010000;` con `e->r[7]` y `e->r[0xFC]`) reproduce el `lui` único
  con `-G0` y con `-G8`. Lo que falta es la copia del valor que conserva el original (`move a2, v1`
  en el hueco de retardo del primer salto), que ni 2.7.2 ni 2.8.1 reproducen con el C probado: la
  mejor formulación mide 25 palabras frente a 26.

## Conclusión

Regla de cabeceras: las del proyecto en `include/psyq/` deben ser las del SDK 4.4, la misma
versión que el compilador identificado; las del SDK 4.7 solo sirven de consulta.

El proyecto compila con **GCC 2.8.1 de Psy-Q (`CC1PSX.EXE` build 4.0.0010, el de Psy-Q 4.4)**
con las opciones **`-O2` y el `-G` original de cada archivo (8 donde el codigo usa datos
pequenos; `-G0` solo donde se ha demostrado necesario)**. Para el ensamblador se usa `maspsx --aspsx-version=2.80` (ver «Versión de ASPSX»). Es la única
combinación que reproduce exactamente una función no trivial del juego: GCC 2.7.2 no lo logra
con ninguna de las formulaciones probadas, y `-O1` no coincide en ninguna de las funciones
evaluadas (puntuaciones de 10 a 1095).

Limitaciones de la evidencia: una sola función hoja no trivial discrimina entre versiones, y
el resto de funciones evaluadas queda por afinar al descompilar. Conviene repetir la
comprobación con funciones de otros subsistemas en cuanto haya más C escrito. Los nombres de
símbolos de datos de la salida de `splat` (`D_8001013C`, `D_80010047`) provienen de
direcciones sueltas; mientras no se agrupen en estructuras, algunas diferencias de
`asm-differ` en símbolos y en la parte alta de las direcciones no son errores del C.

## Versión de ASPSX

`ASPSX.EXE` del SDK 4.4 es la 2.79 (`SDevTC ASPSX version 2.79` en el propio ejecutable) y no existe un binario 2.80 en la
cadena de construcción: el proyecto no ejecuta `ASPSX.EXE`, sino `maspsx`, y `--aspsx-version` solo selecciona el
comportamiento que `maspsx` imita. Desde la 2.80 el ensamblador reescribe `addiu rX,$gp,desplazamiento` (`gp_allow_la`);
la 2.79 deja `lui` + `addiu`. El original usa esa forma, así que la versión que lo reproduce es la 2.80.

- **Fijada:** `VERSION_ASPSX = "2.80"` en `tools/reconstruccion/compilacion.py`. Cambiarla no exige tocar
  `config/toolchain.lock.json` (el hash de `maspsx` no cambia). Para volver a evaluarla se edita la constante y se
  ejecuta `clean`, `split`, `build`, `verify`, comparando la puntuación de `diff` de todas las funciones en C.
- **Medida (2026-10-26, 370 funciones definidas en C):** `verify` sigue dando el SHA-256 original con 2.79 y con 2.80;
  solo cambia `func_80040240` (puntuación 130 a 25, coincide en bytes). Ninguna otra función cambia de puntuación,
  porque `gp_allow_la` solo actúa donde el C declara el dato pequeño en el propio archivo.
