package com.gathin.tvhome;

/** One complete system D-pad pulse per physical tap; controlled repeats for a held key. */
final class NavigationPulse {
    static final long FIRST_REPEAT_MS = 650, REPEAT_MS = 150, MAX_HOLD_MS = 5000;
    private Integer key;
    private long startedAt, downAt, lastPulseAt;
    boolean down(int code, long physicalDownTime, long now, int repeatCount) {
        if (repeatCount != 0 || (key != null && key == code && downAt == physicalDownTime)) return false;
        key = code; downAt = physicalDownTime; startedAt = now; lastPulseAt = now;
        return true;
    }
    void up(int code) { if (key != null && key == code) reset(); }
    void reset() { key = null; }
    boolean active() { return key != null; }
    Integer repeat(long now) {
        if (key == null) return null;
        if (now - startedAt < 0 || now - startedAt > MAX_HOLD_MS) { reset(); return null; }
        if (now - startedAt < FIRST_REPEAT_MS || now - lastPulseAt < REPEAT_MS) return null;
        lastPulseAt = now; return key;
    }
}
