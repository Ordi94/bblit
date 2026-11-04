# psx-decomp-kit

Herramientas para descompilar juegos de PlayStation 1 hasta obtener C que, compilado con el
compilador original del SDK, reproduce el ejecutable byte a byte: particion con splat,
compilacion, comparacion funcion a funcion, medicion de progreso y busqueda de formas de C.

El kit es el paquete Python `psxdecomp` (Python 3.13 o superior, licencia MIT).

## Que no es

- No incluye binarios del SDK, del compilador ni del juego: cada proyecto los descarga o los
  aporta por su cuenta y declara donde estan.
- No contiene datos de ningun juego. Todo lo que depende del proyecto (nombre del ejecutable,
  rutas, zonas de memoria, convenciones de los comentarios) se declara en el manifiesto
  `psxdecomp.toml` de la raiz del proyecto consumidor.

## Instalacion

Desde la raiz del repositorio que lo contiene, dentro del entorno virtual del proyecto:

```
python -m pip install -e ./kit
```

El kit no tiene dependencias de ejecucion: solo usa la biblioteca estandar.

## Manifiesto

`python -m psxdecomp.cli comprobar [ruta]` carga y valida el `psxdecomp.toml` de la
carpeta indicada (por omision la actual) e imprime el resumen. Las secciones son `[proyecto]`,
`[rutas]`, `[zonas]`, `[convenciones]` y `[plugins]`; toda clave desconocida es un error.

## Pruebas

```
python -m pytest
```

Ejecutado desde `kit/`, exige cobertura del 100 % (lineas y ramas) del paquete.

## Capas del cargador

| Modulo | Responsabilidad |
|---|---|
| `dominio` | Secciones inmutables del manifiesto y su construccion desde tablas ya leidas; no toca disco. |
| `validacion` | Validadores primitivos de datos externos (listas de admitidos, cotas); no toca disco. |
| `confinamiento` | Unica regla que consulta el disco: ninguna ruta del proyecto sale de su raiz. |
| `lectura` | Lectura del archivo, analisis TOML y comprobacion de confinamiento. |
| `cli` | Linea de ordenes (`comprobar`). |
| `proyecto` | Fachada: reexporta `Proyecto`, `cargar_proyecto` y `ManifiestoError`. |
