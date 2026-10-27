package com.gathin.tvhome;

/** Port of the local Aerial Clean gesture: three short presses, never synthetic repeats. */
final class HomePressSequence {
    static final long MAX_GAP_MS = 700, WINDOW_MS = 2000, COOLDOWN_MS = 800, DEBOUNCE_MS = 80;
    int count;
    private long firstAt, lastAt = Long.MIN_VALUE / 2, cooldownUntil;
    boolean activeAt(long now) {
        return count > 0 && now - lastAt >= 0 && now - lastAt <= MAX_GAP_MS
                && now - firstAt >= 0 && now - firstAt <= WINDOW_MS;
    }
    boolean press(long now) {
        if (now < cooldownUntil || (now - lastAt >= 0 && now - lastAt < DEBOUNCE_MS)) return false;
        if (!activeAt(now)) { count = 0; firstAt = now; }
        lastAt = now;
        if (++count < 3) return false;
        reset(); cooldownUntil = now + COOLDOWN_MS;
        return true;
    }
    void reset() { count = 0; firstAt = 0; lastAt = Long.MIN_VALUE / 2; }
}
