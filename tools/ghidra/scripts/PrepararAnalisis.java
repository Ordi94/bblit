// Prepara el programa recien importado antes del auto-analisis.
//
// Argumentos del script: <archivo_semilla>
//   archivo_semilla: texto con una direccion hexadecimal por linea (las lineas que empiezan
//                    por '#' o estan vacias se ignoran); puede ser "ninguno" para no sembrar.
//
// Sembrar las funciones antes del analisis evita que el detector automatico parta mal las
// rutinas de libreria y garantiza que las firmas se comparen contra entradas reales. Solo se
// aceptan direcciones con bytes reales del ejecutable: el resto de la RAM esta vacia al cargar.
// @category BBLIT

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;

import java.io.BufferedReader;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public class PrepararAnalisis extends GhidraScript {

    private static final String SIN_VALOR = "ninguno";

    @Override
    protected void run() throws Exception {
        String[] argumentos = getScriptArgs();
        String semilla = argumentos.length > 0 ? argumentos[0] : SIN_VALOR;

        MemoryBlock codigo = currentProgram.getMemory().getBlock("CODE");
        if (codigo == null) {
            throw new IllegalStateException("el programa no tiene bloque CODE: no se cargo con el cargador PSX");
        }
        println("BBLIT base=0x" + codigo.getStart().toString().toUpperCase());
        println("BBLIT fin=0x" + codigo.getEnd().toString().toUpperCase());
        for (Address punto : currentProgram.getSymbolTable().getExternalEntryPointIterator()) {
            println("BBLIT entrada=0x" + punto.toString().toUpperCase());
        }

        if (!SIN_VALOR.equals(semilla)) {
            sembrar(new File(semilla));
        }
    }

    private boolean direccionInicializada(Address direccion) {
        MemoryBlock bloque = currentProgram.getMemory().getBlock(direccion);
        return bloque != null && bloque.isInitialized();
    }

    private void sembrar(File archivo) throws Exception {
        int creadas = 0;
        int existentes = 0;
        int rechazadas = 0;
        try (BufferedReader lector = Files.newBufferedReader(archivo.toPath(), StandardCharsets.UTF_8)) {
            String linea;
            while ((linea = lector.readLine()) != null) {
                linea = linea.trim();
                if (linea.isEmpty() || linea.startsWith("#")) {
                    continue;
                }
                Address direccion = toAddr(Long.parseUnsignedLong(linea.replaceFirst("^0[xX]", ""), 16));
                if (direccion == null || !direccionInicializada(direccion)) {
                    rechazadas++;
                    continue;
                }
                if (getFunctionAt(direccion) != null) {
                    existentes++;
                    continue;
                }
                disassemble(direccion);
                Function funcion = createFunction(direccion, null);
                if (funcion == null) {
                    rechazadas++;
                } else {
                    creadas++;
                }
            }
        }
        println("BBLIT semilla creadas=" + creadas + " existentes=" + existentes + " rechazadas=" + rechazadas);
    }
}
