package it.univr.mining.modbus;

import org.apache.commons.csv.CSVRecord;

public class ModbusMessage {
    
    private static final String SOURCE = "Source";
    private static final String DESTINATION = "Destination";
    private static final String PROTOCOL = "Protocol";
    private static final String FUNCTION_CODE = "Function Code";
    private static final String REGISTER = "Reference Number";
    private static final String INFO = "Info";
    private static final String DATA = "Data";
    private static final String TIME = "Time";

    private final CSVRecord record;
    private String directionChace = null;

    public ModbusMessage(CSVRecord record){
        this.record = record;
    }

    public String source(){
        return record.get(SOURCE);
    }

    public String destination(){
        return record.get(DESTINATION);
    }

    public String data(){
        return record.get(DATA);
    }

    public String time() { return record.get(TIME); }

    public String register() { return record.get(REGISTER); }

    public boolean isCommand(){
        if (record.get(PROTOCOL).compareTo("Modbus/TCP")!=0) return false;
        if (record.get(INFO).contains("Response")) return false;
        if (record.get(FUNCTION_CODE).startsWith("Write")) return true;
        return false;
    }

    public String direction() {
        if (directionChace == null)
            directionChace = source() + "->" + destination();
        return directionChace;
    }


}
