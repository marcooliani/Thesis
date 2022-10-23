package it.univr.mining.event;

public class PlcMessageEvent extends PlcEvent{


    private final String source;
    private final String destination;
    private final String register;
    private final String data;


    public PlcMessageEvent(String source, String destination, String register, String data) {
        this.source = source;
        this.destination = destination;
        this.register = register;
        this.data = data;
    }

    @Override
    public void appendToString(StringBuffer buffer) {
        buffer.append("m ").
                append(sourceOf(source)).
                append(" ").
                append(source).
                append(" -> ").
                append(destination).
                append(" [").
                append(register).
                append("=").
                append(data).
                append("], ");
    }

    @Override
    public void appendToCSV(StringBuffer buffer) {
        buffer.append(",m,").
                append(sourceOf(source)).
                append(",").
                append(source).
                append(" -> ").
                append(destination).
                append(" [").
                append(register).
                append("=").
                append(data).
                append("], ");
    }
}
