package it.univr.mining.event;

public class PlcBooleanEvent extends PlcEvent{

    private final String field;
    private final String previous;
    private final String current;

    public PlcBooleanEvent(String field, String previous, String current) {
        this.field = field;
        this.previous = previous;
        this.current = current;
    }

    public void appendToString(StringBuffer buffer) {
        buffer.append("s ").
                append(sourceOf(field)).
                append(" ").
                append(field).
                append(" [").
                append(previous).
                append("->").
                append(current).
                append("], ");
    }

    @Override
    public void appendToCSV(StringBuffer buffer) {
        buffer.append(",s,").
                append(sourceOf(field)).
                append(",").
                append(field).
                append(" [").
                append(previous).
                append("->").
                append(current).
                append("], ");
    }
}
