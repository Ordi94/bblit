# Cabeceras del SDK Psy-Q

Cabeceras de la biblioteca de tiempo de ejecucion de PlayStation, copiadas sin modificar
para compilar el codigo C del juego (`#include "psyq/LIBGPU.H"`, etc.). Los nombres conservan
las mayusculas con que vienen en el SDK.

## Procedencia

Son las del mismo SDK que trae el compilador de referencia (GCC 2.8.1 de Psy-Q 4.4), para que
prototipos y estructuras correspondan a lo que compilo el juego.

| Dato | Valor |
|---|---|
| Version del SDK | Psy-Q Runtime Library 4.4 (`$PSLibId: Run-time Library Release 4.4$`) |
| Archivo de origen | `Runtime Library 4.4.7z`, carpeta `psx/include/` |
| Origen publico | `https://archive.org/download/ps1_sdks/Runtime%20Library%204.4.7z` |
| SHA-256 del paquete | `75d20b9d31372ff0629482f30ee27edd726eaa57d8be39fa0d93e583144063f7` (registrado en `config/toolchain.lock.json`) |
| Fecha de incorporacion | 2026-10-25 |

Se incluye todo el directorio de cabeceras del paquete salvo `MCGUI.H` (interfaz de tarjeta de
memoria con dialogos, que el juego no usa). Hay seis cabeceras que el paquete 4.4 no trae en
esa ruta y que se conservan de Psy-Q 4.7 (`$PSLibId: Run-time Library Release 4.7$`):
`ERRNO.H`, `FCNTL.H`, `FILE.H`, `IOCTL.H` y `TYPES.H` en la
raiz (en 4.4 solo existen dentro de `SYS/`) y `pad.h`. El contenido pertenece a su autor
original y se conserva por interoperabilidad; no se edita: cualquier ajuste va en cabeceras
propias del proyecto.

## Diferencias con 4.7

Comparacion con las cabeceras de Psy-Q 4.7 (que estuvieron aqui antes), ignorando saltos de
linea. Numero de lineas distintas entre ambas versiones, contando cada lado:

Solo cambia la linea de version (`$PSLibId`, 2 lineas): `ABS.H`, `ASM.H`, `ASSERT.H`, `CTYPE.H`,
`FS.H`, `GTEMAC.H`, `GTENOM.H`, `GTEREG.H`, `GTEREG_S.H`, `INLINE_A.H`, `INLINE_C.H`,
`INLINE_O.H`, `INLINE_S.H`, `KERNEL.H`, `LIBAPI.H`, `LIBCD.H`, `LIBCOMB.H`, `LIBGTE.H`,
`LIBGUN.H`, `LIBHMD.H`, `LIBMATH.H`, `LIBMCRD.H`, `LIBMCX.H`, `LIBPAD.H`, `LIBSIO.H`,
`LIBSND.H`, `MALLOC.H`, `QSORT.H`, `R3000.H`, `RAND.H`, `ROMIO.H`, `SETJMP.H`, `STDARG.H`,
`STDDEF.H`, `STRING.H`, `SYS/ERRNO.H`, `SYS/FCNTL.H`, `SYS/FILE.H`, `SYS/IOCTL.H`,
`SYS/TYPES.H`.

Cambia contenido (lineas distintas sin contar la de version):

| Cabecera | Lineas distintas |
|---|---|
| `LIBSN.H` (en 4.7 se llama `Libsn.h`) | 54 |
| `STRINGS.H` | 28 |
| `LIBGPU.H` | 16 |
| `Libds.h` (en 4.7 se llama `LIBDS.H`) | 15 |
| `LIBPRESS.H` | 10 |
| `CONVERT.H` | 8 |
| `LIMITS.H` | 8 |
| `MEMORY.H` | 8 |
| `STDIO.H` | 6 |
| `STDLIB.H` | 3 |
| `LIBETC.H` | 2 |
| `LIBGS.H` | 1 |
| `LIBSPU.H` | 1 |
| `LIBTAP.H` | 1 |

Las cabeceras `LIBGPU.H`, `LIBETC.H`, `LIBGS.H`, `LIBSPU.H`, `LIBTAP.H` y `LIBPRESS.H` son las
que mas importan al codigo del juego: ante un desajuste de prototipo o estructura al
decompilar, empezar por ellas. Las librerias del ejecutable son una mezcla de 4.0 a 4.6, asi
que `LIBGTE.H`, `LIBGS.H` o `LIBCD.H` pueden exigir una version distinta en casos puntuales.

## Integridad

SHA-256 de cada archivo (verificables con `sha256sum -c` desde esta carpeta); las seis
cabeceras conservadas de 4.7 se listan al final.

```
7aa807921a32a11ba3aab586379bf51d455caec3e32cce1bec3f970697da4e4b  ABS.H
559b54643e04b5aa7c19462d7342bd06595c8f14a99ff5257b0d50864d0a6533  ASM.H
30a303a12e88dedd134d2ec51c49ea8200b49ba2b610b764f17c1a11e337da7e  ASSERT.H
988f2865f319a8a7d90433dae3755cfb9cbd647ed887cad97d7e204cf47ef907  CONVERT.H
5d54885ef8e837b59bd55cf4dd402eac873f1b60e470d9f04b9d3421b4399c10  CTYPE.H
f5e3d5c49bca8f7332cfa01117372e32d5ba4cac75778db69853d67e067c2c23  ERRNO.H
b45382190640ed51effba910703a570441535bab87b04b4bd1dd09e426086c4c  FCNTL.H
503ba54ebcd3864500e79a007363e09b799cfa785950542186665b26b1370056  FILE.H
31d44269dfa37b56ac0b2e5709613cd5a7d3be4bfd2ffc962c7aa44d920d6f64  FS.H
ba0dec314f45c8433b99903f3ddcca27becf950d931443a3efde143e30969f5c  GTEMAC.H
b7c128c0565b55a5c8bb327b003a795d2298f947bc6f4d76fffc18603c4903fd  GTENOM.H
c5b6906a70ea4feb0ae5c1db01cdec6d484387139d3ce91e047314205463381f  GTEREG.H
c654ee51dcf2768901625aaaea6a7d5241b66c1864de49fb13aac26866f96199  GTEREG_S.H
02d0d966ca2f27b2752bd60b06efec2a397db5f9da3066a79b0d6d4dd32e3da4  INLINE_A.H
31258710f1c878d6baa2a8ef1b31083004f962544f2c21f366c84adcf8944788  INLINE_C.H
988fa1444abc41e8522039327b2aae9162bdcb25fcd32de5bfbab748c9549f4a  INLINE_O.H
b6c327950ddcea5859e89501af1a670ee1a2a2873994f37020aa304c26719dfa  INLINE_S.H
40ed180687f44afe82b7aed36cbd12734c66b7f657a811b65c50e5c630c30222  IOCTL.H
da9de21685a487f6cdd5618d8410de5da0553af20e445d04a0b1aceabdeea3c3  KERNEL.H
1ade0adb2de28ffd97d3b423a9ffce7816804f31f5f535318703adc87583ac14  LIBAPI.H
e7cbf5ccd53263d16d38065ddaf5616f50f8fcd4b937aa13258cfe1350cbf441  LIBCD.H
b1f7bee83f9475c813f9c03150d0820cddb324ef9089c4f63b1de2ce83e06800  LIBCOMB.H
aa7c00aa9436562f9226461fdde85e38942d8326388ec0f6e9919eee8fd1e0af  LIBETC.H
570c094691dbddcce8aab8e50e0e87552464cb43ab07c5f2a33a8dd4899b822c  LIBGPU.H
ecfe480335b3e7df68ae84534a124f6b0a9fb026cb8dddd218e154fcd175cd09  LIBGS.H
962d71bae892290e5a1014390e43c2d300321411e5a2ff42eb1c7f52b2f41858  LIBGTE.H
18a8acd39c6c82e71d23b227851cf347bb8e2f31babbbc8db76241795c291c30  LIBGUN.H
9375788ac4be249a967f6e97014ab1cef1c6c71705426673b285b562e85f4d70  LIBHMD.H
b2a95aee6396e61310423019dd55fb17599098a2b9a0ab3a64443f676723e9f9  LIBMATH.H
88cf82163ef32f4006f4c6c374acab30a26d9a406d134f238bc36a336b6c00c9  LIBMCRD.H
50f8b52c4e3dc29d07ecaa0f368e3719878bd11e980d744d4372d9aaccdafdb8  LIBMCX.H
4247394714393e9e14b5407ddede0eb4acbcbd5a089e67f937d44264921a68f5  LIBPAD.H
c21bdafb267dbaa6ab05d4e2ab670e5a418f9c04035427e8f994ff7a4d9a0afc  LIBPRESS.H
e97c0c46fed83f8323aa25b6ffd5fe31e3871d3779aad3b276e4eb2f3b6af35e  LIBSIO.H
a56ea71fc07dac1ecaabbe21b51b38fd73b07f99294eac79c3f2131151e3f102  LIBSN.H
7c250163482de185dc270de35e655973c0aef9ffb8ce4ca2bb7a51b9a02cc81f  LIBSND.H
afa62b2ed8a1761bcf7179336c2485ba150871207daa0ef6f589e9dbbcffefb8  LIBSPU.H
f16eafb37b460f2a98c3320b946a0bcabd24b018e5216695dd006801df4ecd1a  LIBTAP.H
dffe6eceadb336fcddadaeeb93b0a7c20bb243b636e15497241229f0c428bc35  LIMITS.H
b587d64a79d0074185538ef333faac0f4d8395103f5c5458e498c9f4baca3cee  Libds.h
cc155bd6c982890028a73695a3d6aa090163995ab0631061e394c6723660a49f  MALLOC.H
18d17710a1b9422b2d4aad6f3c32b2cc651789bf71c62f510177ef0731a2fc84  MEMORY.H
87905a8b1004b19cc330d125e4649d684c33ec2e702e1038622fadfa67ddca98  QSORT.H
b944926518f17a78dbf8c860e2373e48367c929841c61d18937d786d8e73a2d9  R3000.H
db2629d50e0937028fbc9c895716aa696fc5da5f06d4d904224734431272609f  RAND.H
8ae711e64aa73cbf9c0cbdbb11b28b0154ae098b1c0f83dbd6625f9a414660a3  ROMIO.H
1717282cb690ac437f019235e3d6534f925c5105496b3f4a404b1c40d8635ede  SETJMP.H
6a789dc19c78c4fe69d02c608363489746db2b7096442bd8a2bafb9641315f02  STDARG.H
5e038138414f79b9e57a6d754081cd2d37d81132fa7380dc8f67e045e9c5d7a5  STDDEF.H
04b1c83ac8b0bb134d31d69b77e0f289b701e46037e1a4acfa8afc91ae2559be  STDIO.H
b49a68255ff5eb434bd30300f1cca7c671bcd30147b36bc4583824e04d757637  STDLIB.H
db5aff4d39561f18e01ad7aec5cceef08db55c6ff453eefad512100713909c94  STRING.H
11eaf36bd95d0647c51716d61831db6239242557030be7ee175cc14d09386088  STRINGS.H
cc0e99ca42949096bfe55c8a687c4b7f35e65fee007390f6db4bd72932f7010a  SYS/ERRNO.H
b36088a65c989762019114cafb5749a12677eca28df8bc853e731b63015595d0  SYS/FCNTL.H
78a58a6b95a29d9183b08016d508ca5d40f0331cdbf3d9205811e8bcdd4f4135  SYS/FILE.H
d2c410f30b00fed1142544b3e36c6b99d93ac137ecaa5c3c5d854bc175572908  SYS/IOCTL.H
815a444d268dfeed62804d44e30b23130ab378f4f29a6fff04e1d9eddebf19b7  SYS/TYPES.H
3ace26359cb16e7101f4e0927091a681e8602134224ed64f8328fed432a1e76b  TYPES.H
822a4f97af7a5046b0be99e721f1c3bede0d2900fb46d3640fa61dcf8260815c  pad.h
```

Cabeceras conservadas de 4.7: ERRNO.H, FCNTL.H, FILE.H, IOCTL.H, TYPES.H, pad.h (raiz).
