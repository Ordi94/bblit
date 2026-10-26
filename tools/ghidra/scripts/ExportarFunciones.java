// Exporta del programa analizado las tablas que consume la capa Python y el C de Ghidra.
//
// Argumentos del script: <carpeta_salida> [decompilar=si|no] [segundos_por_funcion]
//
// Archivos producidos (UTF-8 sin BOM, fin de linea LF):
//   funciones.csv    funciones del segmento de codigo del ejecutable con su origen de libreria
//   strings.csv      cadenas ASCII terminadas en cero
//   xrefs_datos.csv  direcciones de datos referenciadas desde codigo y quien las usa
//   decomp/          un .c por funcion con la salida del decompilador
//
// El origen de libreria se deduce de los indices de firmas que trae la extension del cargador
// PSX para la version de Psy-Q que el propio cargador detecto en el binario: una funcion es de
// libreria cuando su nombre figura como etiqueta de alguna firma de esa version.
// @category BBLIT

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import generic.jar.ResourceFile;
import ghidra.framework.Application;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ExportarFunciones extends GhidraScript {

    private static final long RAM_MIN = 0x80000000L;
    private static final long RAM_MAX = 0x80200000L;
    private static final int LONGITUD_MINIMA_CADENA = 5;
    private static final String NL = "\n";
    private static final Pattern NOMBRE_LOCAL = Pattern.compile("^([A-Z0-9_]+)_OBJ_[0-9A-F]+$");

    private Address inicioCodigo;
    private Address finCodigo;
    private final Map<String, Set<String>> origenPorEtiqueta = new HashMap<>();
    private final Map<String, String> origenPorObjeto = new HashMap<>();

    @Override
    protected void run() throws Exception {
        String[] argumentos = getScriptArgs();
        if (argumentos.length < 1) {
            throw new IllegalArgumentException("falta la carpeta de salida");
        }
        Path salida = new File(argumentos[0]).toPath();
        boolean decompilar = argumentos.length < 2 || !"no".equals(argumentos[1]);
        int segundos = argumentos.length > 2 ? Integer.parseInt(argumentos[2]) : 60;

        MemoryBlock codigo = currentProgram.getMemory().getBlock("CODE");
        if (codigo == null) {
            throw new IllegalStateException("el programa no tiene bloque CODE: no se cargo con el cargador PSX");
        }
        inicioCodigo = codigo.getStart();
        finCodigo = codigo.getEnd();
        println("BBLIT base=0x" + inicioCodigo.toString().toUpperCase());
        println("BBLIT fin=0x" + finCodigo.toString().toUpperCase());

        cargarIndiceFirmas();
        Files.createDirectories(salida);
        List<Function> funciones = funcionesDelSegmento();
        exportarFunciones(salida.resolve("funciones.csv"), funciones);
        exportarCadenas(salida.resolve("strings.csv"), codigo);
        exportarXrefs(salida.resolve("xrefs_datos.csv"), funciones);
        if (decompilar) {
            exportarDecompilacion(salida.resolve("decomp"), funciones, segundos);
        }
        println("BBLIT exportadas=" + funciones.size());
    }

    // ---- indice de firmas ---------------------------------------------------------------

    private void cargarIndiceFirmas() throws IOException {
        ResourceFile raiz = Application.getModuleDataSubDirectory("ghidra_psx_ldr", "psyq");
        for (ResourceFile version : raiz.listFiles()) {
            if (!version.isDirectory() || !version.getName().matches("[0-9]+")) {
                continue;
            }
            for (ResourceFile archivo : version.listFiles()) {
                if (archivo.getName().endsWith(".json")) {
                    indexarArchivo(archivo);
                }
            }
        }
        println("BBLIT firmas_etiquetas=" + origenPorEtiqueta.size());
    }

    private void indexarArchivo(ResourceFile archivo) throws IOException {
        String libreria = archivo.getName().replaceFirst("[.]json$", "");
        JsonArray objetos;
        try (InputStream entrada = archivo.getInputStream()) {
            objetos = JsonParser.parseString(
                new String(entrada.readAllBytes(), StandardCharsets.UTF_8)).getAsJsonArray();
        }
        for (JsonElement elemento : objetos) {
            JsonObject objeto = elemento.getAsJsonObject();
            String nombreObjeto = objeto.get("name").getAsString();
            String origen = libreria + "/" + nombreObjeto;
            origenPorObjeto.putIfAbsent(nombreObjeto, origen);
            indexarEtiquetas(objeto, "labels", origen);
            indexarEtiquetas(objeto, "xbss", origen);
        }
    }

    private void indexarEtiquetas(JsonObject objeto, String clave, String origen) {
        if (!objeto.has(clave)) {
            return;
        }
        for (JsonElement etiqueta : objeto.getAsJsonArray(clave)) {
            String nombre = etiqueta.getAsJsonObject().get("name").getAsString();
            origenPorEtiqueta.computeIfAbsent(nombre, k -> new TreeSet<>()).add(origen);
        }
    }

    /** Devuelve el origen de libreria o cadena vacia si el nombre no lo proporciona una firma. */
    private String origenDe(String nombre) {
        Matcher local = NOMBRE_LOCAL.matcher(nombre);
        if (local.matches()) {
            String origen = origenPorObjeto.get(local.group(1) + ".OBJ");
            return origen != null ? origen : local.group(1) + ".OBJ";
        }
        Set<String> origenes = origenPorEtiqueta.get(nombre);
        return origenes == null ? "" : String.join("|", origenes);
    }

    // ---- funciones ----------------------------------------------------------------------

    private List<Function> funcionesDelSegmento() {
        List<Function> resultado = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            Address entrada = f.getEntryPoint();
            boolean dentro = entrada.compareTo(inicioCodigo) >= 0 && entrada.compareTo(finCodigo) <= 0;
            // Un cuerpo de menos de una instruccion es una etiqueta de firma sobre datos, no codigo.
            if (dentro && f.getBody().getNumAddresses() >= 4) {
                resultado.add(f);
            }
        }
        return resultado;
    }

    private int llamadores(Function f) {
        Set<Address> origenes = new TreeSet<>();
        for (Reference r : getReferencesTo(f.getEntryPoint())) {
            if (r.getReferenceType().isCall()) {
                origenes.add(r.getFromAddress());
            }
        }
        return origenes.size();
    }

    private void exportarFunciones(Path destino, List<Function> funciones) throws IOException {
        Listing listado = currentProgram.getListing();
        StringBuilder sb = new StringBuilder(
            "direccion,nombre,tamano,es_libreria,libreria_origen,numero_de_llamadores,nombre_oficial,comentario\n");
        for (Function f : funciones) {
            String nombre = f.getName();
            String origen = origenDe(nombre);
            boolean libreria = !origen.isEmpty();
            boolean oficial = libreria && !NOMBRE_LOCAL.matcher(nombre).matches();
            String comentario = listado.getComment(CodeUnit.PLATE_COMMENT, f.getEntryPoint());
            long minimo = f.getBody().getMinAddress().getOffset();
            long maximo = f.getBody().getMaxAddress().getOffset();
            sb.append(String.format("0x%08X", f.getEntryPoint().getOffset())).append(',')
              .append(csv(nombre)).append(',')
              .append(maximo - minimo + 1).append(',')
              .append(libreria ? 1 : 0).append(',')
              .append(csv(origen)).append(',')
              .append(llamadores(f)).append(',')
              .append(oficial ? 1 : 0).append(',')
              .append(csv(comentario == null ? "" : comentario)).append('\n');
        }
        escribir(destino, sb);
    }

    // ---- cadenas ------------------------------------------------------------------------

    private void exportarCadenas(Path destino, MemoryBlock bloque) throws Exception {
        Memory memoria = currentProgram.getMemory();
        long inicio = bloque.getStart().getOffset();
        int tamano = (int) bloque.getSize();
        byte[] datos = new byte[tamano];
        memoria.getBytes(bloque.getStart(), datos);
        StringBuilder sb = new StringBuilder("direccion,longitud,texto\n");
        int desde = -1;
        for (int i = 0; i <= tamano; i++) {
            int b = i < tamano ? datos[i] & 0xFF : 0;
            boolean imprimible = (b >= 0x20 && b <= 0x7E) || b == 0x0A || b == 0x09 || b == 0x0D;
            if (imprimible) {
                if (desde < 0) {
                    desde = i;
                }
                continue;
            }
            if (b == 0 && desde >= 0 && i - desde >= LONGITUD_MINIMA_CADENA) {
                String texto = new String(datos, desde, i - desde, StandardCharsets.US_ASCII);
                sb.append(String.format("0x%08X", inicio + desde)).append(',')
                  .append(i - desde).append(',').append(csv(texto)).append('\n');
            }
            desde = -1;
        }
        escribir(destino, sb);
    }

    // ---- referencias a datos -------------------------------------------------------------

    private void exportarXrefs(Path destino, List<Function> funciones) throws IOException {
        Listing listado = currentProgram.getListing();
        Map<Long, Set<Long>> usos = new TreeMap<>();
        Map<Long, int[]> accesos = new HashMap<>();
        for (Function f : funciones) {
            long entrada = f.getEntryPoint().getOffset();
            for (Instruction i : listado.getInstructions(f.getBody(), true)) {
                for (Reference r : i.getReferencesFrom()) {
                    Address a = r.getToAddress();
                    long destinoRef = a.getOffset();
                    if (!a.isMemoryAddress() || destinoRef < RAM_MIN || destinoRef >= RAM_MAX
                        || r.getReferenceType().isCall() || r.getReferenceType().isFlow()) {
                        continue;
                    }
                    if (getFunctionContaining(a) != null) {
                        continue;
                    }
                    usos.computeIfAbsent(destinoRef, k -> new TreeSet<>()).add(entrada);
                    int[] contadores = accesos.computeIfAbsent(destinoRef, k -> new int[2]);
                    if (r.getReferenceType().isRead()) {
                        contadores[0]++;
                    }
                    if (r.getReferenceType().isWrite()) {
                        contadores[1]++;
                    }
                }
            }
        }
        StringBuilder sb = new StringBuilder(
            "direccion_dato,tamano,funciones_que_lo_usan,lecturas,escrituras" + NL);
        for (Map.Entry<Long, Set<Long>> e : usos.entrySet()) {
            Data dato = listado.getDataAt(toAddr(e.getKey()));
            int tamano = dato != null && dato.isDefined() ? dato.getLength() : 0;
            List<String> lista = new ArrayList<>();
            for (Long f : e.getValue()) {
                lista.add(String.format("0x%08X", f));
            }
            int[] contadores = accesos.get(e.getKey());
            sb.append(String.format("0x%08X", e.getKey())).append(',').append(tamano).append(',')
              .append(csv(String.join(";", lista))).append(',')
              .append(contadores[0]).append(',').append(contadores[1]).append(NL);
        }
        escribir(destino, sb);
    }

    // ---- decompilacion ---------------------------------------------------------------------

    private void exportarDecompilacion(Path carpeta, List<Function> funciones, int segundos) throws IOException {
        Files.createDirectories(carpeta);
        DecompInterface decompilador = new DecompInterface();
        decompilador.openProgram(currentProgram);
        int correctas = 0;
        int fallidas = 0;
        try {
            for (Function f : funciones) {
                DecompileResults resultado = decompilador.decompileFunction(f, segundos, monitor);
                String nombreArchivo = String.format("%08X_%s.c", f.getEntryPoint().getOffset(),
                    f.getName().replaceAll("[^A-Za-z0-9_]", "_"));
                String cuerpo;
                if (resultado != null && resultado.decompileCompleted()
                    && resultado.getDecompiledFunction() != null) {
                    cuerpo = resultado.getDecompiledFunction().getC();
                    correctas++;
                } else {
                    String motivo = resultado == null ? "sin resultado" : resultado.getErrorMessage();
                    cuerpo = "/* La decompilacion no se completo: " + motivo + " */\n";
                    fallidas++;
                }
                Files.writeString(carpeta.resolve(nombreArchivo), cuerpo, StandardCharsets.UTF_8);
            }
        } finally {
            decompilador.dispose();
        }
        println("BBLIT decompiladas=" + correctas + " fallidas=" + fallidas);
    }

    // ---- utilidades -------------------------------------------------------------------------

    private static String csv(String valor) {
        if (valor.indexOf(',') >= 0 || valor.indexOf('"') >= 0 || valor.indexOf('\n') >= 0
            || valor.indexOf('\r') >= 0) {
            return '"' + valor.replace("\"", "\"\"") + '"';
        }
        return valor;
    }

    private static void escribir(Path destino, StringBuilder contenido) throws IOException {
        Files.writeString(destino, contenido.toString(), StandardCharsets.UTF_8);
    }
}
