package it.univr.mining.event;

public abstract class PlcEvent {

    public abstract void appendToString(StringBuffer buffer);

    public abstract void appendToCSV(StringBuffer buffer);

    protected String sourceOf(String event){
        if (event.contains("_"))
            return event.split("_")[0];
        else
            return event.split(" ")[0];
    }
}
