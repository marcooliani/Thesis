package it.univr.mining.event;

import java.util.LinkedList;
import java.util.List;

public class LogEntry {

    private final String timestamp;
    private List<PlcEvent> events;

    public LogEntry(String timestamp){
        this.timestamp = timestamp;
        events = new LinkedList<>();
    }

    public void add(PlcEvent event){
        events.add(event);
    }

    public void appendTo(StringBuffer buffer){
        buffer.append(timestamp).append(": ");
        for (PlcEvent event: events)
            event.appendToString(buffer);
        buffer.append("\n");
    }

    public boolean notEmpty() {
        return (events.size() != 0);
    }
}
