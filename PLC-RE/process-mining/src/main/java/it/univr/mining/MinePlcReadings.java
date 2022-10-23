package it.univr.mining;

import it.univr.mining.event.LogEntry;
import it.univr.mining.event.PlcBooleanEvent;
import it.univr.mining.event.PlcScalarEvent;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.*;
import java.util.*;

public class MinePlcReadings {

    private enum Type {NEGLIGEABLE, BOOLEAN, SCALAR, NOT_RESOLVED}
    private enum Trend {ASCENDING, DESCENDING, STABLE}

    private final String fileName;
    private List<String> headers;
    private List<CSVRecord> records;
    private Type[] types;

    private List<Integer> interesting;
    private List<LogEntry> log;

    public static void main(String[] argv) throws IOException {
        MinePlcReadings main = new MinePlcReadings("data/PLC_Dataset_TS.csv");
        main.readData();
        main.process();
        main.computeEvents();
        main.printEvents("data/PLC1_PLC2_PLC3_Dataset.txt");
    }

    public MinePlcReadings(String fileName){
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

    private void process() {
        int size = headers.size();
        Set<String>[] values = new Set[size];
        for (int i=0; i<size; i++){
            values[i] = new HashSet<>();
        }
        for(CSVRecord record: records){
            for (int i=0; i<size; i++){
                String value = record.get(i);
                if (value.compareTo("N/A")!=0)
                    values[i].add(record.get(i));
            }
        }
        types = new Type[size];
        for (int i=0; i<size; i++){
            types[i] = resolveType(values[i]);
        }

        System.err.println("Variables whose type is not resolved:");
        for (int i=0; i<size; i++){
            if (types[i] == Type.NOT_RESOLVED)
                System.out.println("* " + i +": " + headers.get(i));
        }

        interesting = new LinkedList<>();
        for (int i=0; i<size; i++){
            if(types[i] != Type.NEGLIGEABLE) interesting.add(i);
        }
    }

    private Type resolveType(Set<String> values){
        if (values.size()==1) return Type.NEGLIGEABLE;
        if (values.size()==2) {
            if (values.contains("1.0") && values.contains("0.0"))
                return Type.BOOLEAN;
            else if (values.contains("1") && values.contains("0"))
                return Type.BOOLEAN;
        }
        try {
            for (String content : values)
                Double.valueOf(content);
            return Type.SCALAR;
        }
        catch(NumberFormatException e){
            return Type.NOT_RESOLVED;
        }
    }



    private Trend computeTrend(String previous, String current){
        double old = Double.parseDouble(previous);
        double next = Double.parseDouble(current);
        if (next==old) return Trend.STABLE;
        if (next>old) return Trend.ASCENDING;
        return Trend.DESCENDING;
    }

    private void computeEvents(){
        log = new LinkedList<>();
        Map<Integer,String> previousValue = new HashMap<>();
        Map<Integer,Trend> previousTrend = new HashMap<>();
        Map<Integer,String> startingTrend = new HashMap<>();

        for(CSVRecord record: records){
            for(int i: interesting){
                if (record.get("TimeStamp").compareTo("N/A")==0)
                    continue;
                LogEntry entry = new LogEntry(record.get("TimeStamp"));
                String current = record.get(i);
                String previous = previousValue.get(i);
                if ((previous!= null) && previous.compareTo(current) !=0) {
                    if (types[i] == Type.BOOLEAN)
                        entry.add(new PlcBooleanEvent(headers.get(i), previous, current));
                    if (types[i] == Type.SCALAR) {
                        Trend was = previousTrend.get(i);
                        Trend is = computeTrend(previous, current);
                        if ((was != null) && was != is) {
                            String initial = startingTrend.get(i);
                            entry.add(new PlcScalarEvent(headers.get(i), was.toString(), is.toString(), initial, current));
                            startingTrend.put(i, current);
                        }
                        previousTrend.put(i, is);
                    }
                }
                if (previous==null && (types[i]==Type.SCALAR))
                    startingTrend.put(i, current);
                previousValue.put(i, current);
                if(entry.notEmpty()) log.add(entry);
            }
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
