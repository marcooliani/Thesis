package it.univr.mining.event;

public class PlcScalarEvent extends PlcEvent {

    private final String field;
    private final String previousTrend;
    private final String currentTrend;
    private final String initialValue;
    private final String finalValue;

    public PlcScalarEvent(String field, String previousTrend, String currentTrend, String initialValue, String finalValue) {
        this.field = field;
        this.previousTrend = previousTrend;
        this.currentTrend = currentTrend;
        this.initialValue = initialValue;
        this.finalValue = finalValue;
    }

    public void appendToString(StringBuffer buffer) {
        buffer.append("s ").
                append(sourceOf(field)).
                append(" ").
                append(field).
                append(" [").
                append(previousTrend).
                append("->").
                append(currentTrend).
                append("] (").
                append(initialValue).
                append("-").
                append(finalValue).
                append("), ");
    }

    @Override
    public void appendToCSV(StringBuffer buffer) {
        buffer.append(",s,").
                append(sourceOf(field)).
                append(",").
                append(field).
                append(" [").
                append(previousTrend).
                append("->").
                append(currentTrend).
                append("]");
    }
}
