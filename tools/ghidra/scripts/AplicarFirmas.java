// Aplica firmas de librerias Psy-Q de versiones adicionales sobre un programa ya analizado.
//
// Argumentos del script: <version> [<version> ...]   (por ejemplo: 4.6.0 4.0.0)
//
// El ejecutable enlaza objetos de librerias de epocas distintas del SDK: el cargador detecta una
// sola version y solo reconoce lo que coincide con ella. Cada pasada adicional carga el indice de
// firmas de otra version y nombra unicamente las funciones que siguen sin nombre propio, de modo
// que una version posterior nunca pisa una identificacion previa.
// @category BBLIT

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.app.util.importer.MessageLog;
import psx.PsxAnalyzer;
import psx.PsxLoader;

public class AplicarFirmas extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String[] versiones = getScriptArgs();
        MemoryBlock codigo = currentProgram.getMemory().getBlock("CODE");
        if (codigo == null) {
            throw new IllegalStateException("el programa no tiene bloque CODE: no se cargo con el cargador PSX");
        }
        AddressSet segmento = new AddressSet(codigo.getStart(), codigo.getEnd());
        for (String version : versiones) {
            PsxLoader.setProgramPsyqVersion(currentProgram, version);
            MessageLog registro = new MessageLog();
            PsxAnalyzer analizador = new PsxAnalyzer();
            analizador.added(currentProgram, segmento, monitor, registro);
            println("BBLIT firmas_aplicadas version=" + version);
        }
    }
}
