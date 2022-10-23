package it.univr.mining;

import java.io.*;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Comparator;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;

public class MergeLogs {

    public static void main(String[] args) throws IOException {
        List<Entry> list1 = readEntries("data/PLC1_PLC2_PLC3_Dataset.txt");
        if (missDate(list1)) patchDate(list1, "2022-03-23");
        List<Entry> list2 = readEntries("data/CleanCaptureWrite.txt");
        list1.addAll(list2);
        list1.sort(new EntryComparator());
        printStringTo(list1, "data/MergeEvents.txt");
        printCsvTo(list1, "data/MergeEvents.csv");
    }



    private static boolean missDate(List<Entry> list) {
        Entry first = list.get(0);
        return ! (first.getTimeStamp().contains(" "));
    }

    private static void patchDate(List<Entry> list, String date) {
        for(Entry e: list){
            e.patchDate(date);
        }
    }

    private static List<Entry> readEntries(String fileName) throws IOException {
        LinkedList<Entry> result = new LinkedList<>();
        BufferedReader in = new BufferedReader(new FileReader(new File(fileName)));
        String line = null;
        while ((line=in.readLine())!=null){
            Entry entry = new Entry(line);
            result.add(entry);
        }
        return result;
    }

    private static void printStringTo(List<Entry> events, String fileName) throws FileNotFoundException {
        StringBuffer buffer = new StringBuffer(1000);
        for (Entry e: events)
            e.appendToString(buffer);
        PrintWriter out = new PrintWriter(new File(fileName));
        out.write(buffer.toString());
        out.close();
    }

    private static void printCsvTo(List<Entry> events, String fileName) throws FileNotFoundException {
        StringBuffer buffer = new StringBuffer(1000);
        for (Entry e: events)
            e.appendToCSV(buffer);
        PrintWriter out = new PrintWriter(new File(fileName));
        out.write(buffer.toString());
        out.close();
    }
}

class Entry{

    private String timeStamp;
    private String content;
    private static final String SPLIT = ": ";
    private static final String FORMAT = "yyyy-MM-dd HH:mm:ss.SSS";
    private static final SimpleDateFormat formatter = new SimpleDateFormat(FORMAT);
    private Date dateCache;

    public Entry(String line) {
        int split = line.indexOf(SPLIT);
        timeStamp = line.substring(0, split);
        content = line.substring(split+SPLIT.length());
    }

    public String getTimeStamp(){
        return timeStamp;
    }

    public String toString(){
        return timeStamp.substring(0,FORMAT.length()) + SPLIT + content;
    }

    public void patchDate(String date) {
        timeStamp = date + " " + timeStamp;
    }

    public Date toDate() throws ParseException {
        if (dateCache==null)
            dateCache = formatter.parse(timeStamp.substring(0,FORMAT.length()));
        return dateCache;
    }

    public void appendToString(StringBuffer buffer) {
        buffer.append(timeStamp.substring(0,FORMAT.length()) ).
                append(": ").
                append(content).
                append("\n");
    }

    public void appendToCSV(StringBuffer buffer) {
        buffer.append(timeStamp.substring(0,FORMAT.length()) ).
                append(",").
                append(removeInterval(content.
                        replaceFirst(" ", ",").
                        replaceFirst(" ", ",")
                )).
                append("\n");
    }

    private String removeInterval(String old) {
        String regex = "\\([\\d.]+-[\\d.]+\\), ";
        return old.replaceFirst(regex, ", ");
    }
}

class EntryComparator implements Comparator<Entry> {

    @Override
    public int compare(Entry e1, Entry e2) {
        try {
            if (e1.toDate().before(e2.toDate()))
                return -1;
            else
                return 1;
        }
        catch (ParseException e){
            throw new InternalError(e);
        }
    }

    @Override
    public boolean equals(Object obj) {
        return false;
    }
}