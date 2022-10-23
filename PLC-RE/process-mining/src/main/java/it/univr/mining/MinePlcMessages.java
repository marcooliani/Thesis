package it.univr.mining;

import it.univr.mining.event.LogEntry;
import it.univr.mining.event.PlcMessageEvent;
import it.univr.mining.modbus.ModbusMessage;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.*;
import java.util.*;

public class MinePlcMessages {

    private final String fileName;
    private List<String> headers;
    private List<CSVRecord> records;

    private List<Integer> interesting;
    private List<LogEntry> log;

    public static void main(String[] argv) throws IOException {
        MinePlcMessages main = new MinePlcMessages("data/CleanCaptureWrite.csv");
        main.readData();
        //main.process();
        main.computeEvents();
        main.printEvents("data/CleanCaptureWrite.txt");
    }

    public MinePlcMessages(String fileName){
        this.fileName = fileName;
    }

    public void readData() throws IOException {
        CSVFormat format = CSVFormat.Builder.create().
                setDelimiter(',').
                setQuote('"').
                setRecordSeparator("\r\n").
                setIgnoreEmptyLines(true).
                setAllowDuplicateHeaderNames(true).
                setHeader().build();

        Reader in = new FileReader(fileName);
        CSVParser parser = new CSVParser(in, format);
        headers = parser.getHeaderNames();
        records = parser.getRecords();
        in.close();
    }

    private void computeEvents(){
        log = new LinkedList<>();
        Map<String,String> previousCommand = new HashMap<>();
        for(CSVRecord record: records){
            ModbusMessage message = new ModbusMessage(record);
            if (!message.isCommand())
                continue;
            LogEntry entry = new LogEntry(message.time());
            String directionAndRegister = message.direction() + message.register();
            String current = message.data();
            String previous = previousCommand.get(directionAndRegister);
            if ((previous!=null) && (previous.compareTo(current)!=0)){
                PlcMessageEvent event = new PlcMessageEvent(message.source(), message.destination(), message.register(), current);
                entry.add(event);
            }
            previousCommand.put(directionAndRegister, current);
            if (entry.notEmpty())
                log.add(entry);
        }
    }

    private void printEvents(String fileName) throws FileNotFoundException {
        StringBuffer buffer = new StringBuffer(1000);
        for(LogEntry entry: log)
            entry.appendTo(buffer);
        //System.out.println(buffer);
        PrintWriter out = new PrintWriter(new File(fileName));
        out.write(buffer.toString());
        out.close();
    }

}
