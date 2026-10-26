// Descubre funciones que el analisis no alcanza porque solo se invocan mediante tablas de punteros.
//
// Sin argumentos. Recorre el bloque CODE buscando prologos de funcion que quedaron fuera de todo
// cuerpo ya conocido. Un prologo es un ajuste de pila (addiu sp, sp, -N con N multiplo de 8) y
// se acepta unicamente si la instruccion anterior termina una rutina: el retorno jr ra con su
// ranura de retardo, o relleno de nops. Esa condicion descarta tablas de datos cuyas palabras
// casualmente se parecen a un prologo.
//
// Despues se revisan los huecos que quedan entre funciones: un hueco que contiene un retorno
// jr ra y cuyo primer contenido no nulo se desensambla hasta ese retorno es una rutina sin marco
// de pila (callbacks vacios, accesores) y tambien se crea.
//
// Tambien se corrigen los cuerpos partidos: una funcion que nadie invoca y que empieza justo
// despues de un fragmento de codigo suelto no es una funcion real, sino la continuacion de una
// rutina que arranca en ese fragmento (por ejemplo, un manejador de interrupcion cuya primera
// instruccion no es un ajuste de pila). Se funden en una sola funcion que arranca en el fragmento.
//
// Cada ronda crea las funciones y relanza el analisis para que se descubran las rutinas que
// ellas invocan; termina cuando una ronda no aporta nada o tras un maximo de rondas.
// @category BBLIT

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

import java.util.ArrayList;
import java.util.List;

public class DescubrirFunciones extends GhidraScript {

    private static final int MAX_RONDAS = 4;
    private static final int RETORNO = 0x03E00008; // jr ra
    private static final int MAX_MARCO_PILA = 0x400;
    private static final int MAX_RUTINA_SIN_MARCO = 0x40;
    private static final int MAX_FRAGMENTO = 0x100;
    private static final int MAX_NOPS_SEGUIDOS = 3;

    @Override
    protected void run() throws Exception {
        MemoryBlock codigo = currentProgram.getMemory().getBlock("CODE");
        if (codigo == null) {
            throw new IllegalStateException("el programa no tiene bloque CODE: no se cargo con el cargador PSX");
        }
        int total = 0;
        for (int ronda = 1; ronda <= MAX_RONDAS; ronda++) {
            int nuevas = descubrir(codigo);
            println("BBLIT descubiertas ronda=" + ronda + " nuevas=" + nuevas);
            total += nuevas;
            if (nuevas == 0) {
                break;
            }
            analyzeChanges(currentProgram);
        }
        println("BBLIT descubiertas total=" + total);
    }

    private int descubrir(MemoryBlock codigo) throws Exception {
        Memory memoria = currentProgram.getMemory();
        int unidas = unirFragmentos(codigo);
        List<Address> candidatas = new ArrayList<>();
        Address inicio = codigo.getStart();
        long palabras = codigo.getSize() / 4;
        for (long i = 2; i < palabras; i++) {
            Address direccion = inicio.add(i * 4);
            int instruccion = memoria.getInt(direccion);
            if (!esAjusteDePila(instruccion) || getFunctionContaining(direccion) != null) {
                continue;
            }
            int previa = memoria.getInt(direccion.subtract(4));
            int anterior = memoria.getInt(direccion.subtract(8));
            if (anterior == RETORNO || previa == 0) {
                candidatas.add(direccion);
            }
        }
        int creadas = 0;
        for (Address direccion : candidatas) {
            if (getFunctionContaining(direccion) != null) {
                continue;
            }
            disassemble(direccion);
            if (createFunction(direccion, null) != null) {
                creadas++;
            }
        }
        return unidas + creadas + descubrirSinMarco(codigo);
    }

    /** Funde en una sola funcion los fragmentos sueltos que preceden a funciones que nadie invoca. */
    private int unirFragmentos(MemoryBlock codigo) throws Exception {
        Memory memoria = currentProgram.getMemory();
        List<Function> sinLlamadas = new ArrayList<>();
        for (Function funcion : currentProgram.getFunctionManager().getFunctions(true)) {
            Address entrada = funcion.getEntryPoint();
            if (codigo.contains(entrada) && !tieneLlamadas(entrada)) {
                sinLlamadas.add(funcion);
            }
        }
        int unidas = 0;
        for (Function funcion : sinLlamadas) {
            Address entrada = funcion.getEntryPoint();
            Address inicio = inicioDeFragmento(memoria, entrada, codigo);
            if (inicio == null) {
                continue;
            }
            String nombre = funcion.getName();
            removeFunction(funcion);
            disassemble(inicio);
            Function fundida = createFunction(inicio, null);
            if (fundida != null && fundida.getBody().contains(entrada)) {
                unidas++;
            } else {
                if (fundida != null) {
                    removeFunction(fundida);
                }
                disassemble(entrada);
                createFunction(entrada, nombre);
            }
        }
        return unidas;
    }

    private boolean tieneLlamadas(Address entrada) {
        for (Reference referencia : getReferencesTo(entrada)) {
            if (referencia.getReferenceType().isCall()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Devuelve el primer word no nulo del fragmento suelto que termina en la entrada, o null si
     * no hay fragmento (la entrada sigue a otra funcion, a relleno o a un retorno).
     */
    private Address inicioDeFragmento(Memory memoria, Address entrada, MemoryBlock codigo) throws Exception {
        Address inicio = null;
        int nulasSeguidas = 0;
        for (int distancia = 4; distancia <= MAX_FRAGMENTO; distancia += 4) {
            Address candidata = entrada.subtract(distancia);
            if (!codigo.contains(candidata) || getFunctionContaining(candidata) != null) {
                break;
            }
            int palabra = memoria.getInt(candidata);
            nulasSeguidas = palabra == 0 ? nulasSeguidas + 1 : 0;
            if (nulasSeguidas >= MAX_NOPS_SEGUIDOS) {
                break;
            }
            if (palabra == RETORNO) {
                return distancia > 8 ? entrada.subtract(distancia - 8) : null;
            }
            if (palabra != 0) {
                inicio = candidata;
            }
            if (distancia == MAX_FRAGMENTO) {
                return null;
            }
        }
        return inicio;
    }

    /** Crea las rutinas sin marco de pila que quedan sueltas entre funciones ya conocidas. */
    private int descubrirSinMarco(MemoryBlock codigo) throws Exception {
        Memory memoria = currentProgram.getMemory();
        int creadas = 0;
        long fin = codigo.getEnd().getOffset();
        long cursor = codigo.getStart().getOffset();
        boolean inicioDeHueco = true;
        while (cursor <= fin) {
            Address direccion = toAddr(cursor);
            Function contenedora = getFunctionContaining(direccion);
            if (contenedora != null) {
                cursor = contenedora.getBody().getMaxAddress().getOffset() + 1;
                inicioDeHueco = true;
                continue;
            }
            if (memoria.getInt(direccion) == 0) {
                cursor += 4;
                inicioDeHueco = true;
                continue;
            }
            if (inicioDeHueco) {
                creadas += crearSiHayRetorno(memoria, direccion, codigo);
            }
            inicioDeHueco = false;
            cursor += 4;
        }
        return creadas;
    }

    /** Intenta crear una rutina corta en la direccion; devuelve 1 si la crea y 0 si no. */
    private int crearSiHayRetorno(Memory memoria, Address direccion, MemoryBlock codigo) throws Exception {
        int distancia = distanciaARetorno(memoria, direccion, codigo);
        if (distancia < 0) {
            return 0;
        }
        disassemble(direccion);
        Function funcion = createFunction(direccion, null);
        if (funcion == null) {
            return 0;
        }
        if (!funcion.getBody().contains(direccion.add(distancia))) {
            removeFunction(funcion);
            return 0;
        }
        return 1;
    }

    /**
     * Devuelve los bytes hasta el primer retorno jr ra si aparece antes de cualquier funcion
     * conocida y dentro del limite de una rutina corta; -1 si no hay.
     */
    private int distanciaARetorno(Memory memoria, Address inicio, MemoryBlock codigo) throws Exception {
        for (int desplazamiento = 0; desplazamiento <= MAX_RUTINA_SIN_MARCO; desplazamiento += 4) {
            Address actual = inicio.add(desplazamiento);
            if (actual.compareTo(codigo.getEnd()) > 0 || getFunctionContaining(actual) != null) {
                return -1;
            }
            if (memoria.getInt(actual) == RETORNO) {
                return desplazamiento;
            }
        }
        return -1;
    }

    /** Reconoce addiu sp, sp, -N: opcode 0x09, rs = rt = 29 e inmediato negativo multiplo de 8. */
    private static boolean esAjusteDePila(int instruccion) {
        if ((instruccion & 0xFFFF0000) != 0x27BD0000) {
            return false;
        }
        int inmediato = (short) (instruccion & 0xFFFF);
        return inmediato < 0 && inmediato >= -MAX_MARCO_PILA && (inmediato & 7) == 0;
    }
}
