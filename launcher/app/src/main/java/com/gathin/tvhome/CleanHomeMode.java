package com.gathin.tvhome;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.ContentObserver;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;

/** Explicit local opt-in and mode survive Direct Boot. The installer scopes this to the tested TV. */
final class CleanHomeMode {
    private static ContentObserver adbObserver;
    static SharedPreferences prefs(Context c) {
        return c.createDeviceProtectedStorageContext().getSharedPreferences("clean_home", Context.MODE_PRIVATE);
    }
    static boolean held(Context c) { return prefs(c).getBoolean("clean_restore_hold", false); }
    static boolean active(Context c) { return prefs(c).getBoolean("enabled", false) && !held(c); }
    static boolean stock(Context c) { return prefs(c).getBoolean("stock", false); }
    static boolean chooseStock(Context c, boolean stock) { return prefs(c).edit().putBoolean("stock", stock).commit(); }

    // Carry the previously selected maintenance preference, without changing standby or probing ports.
    static void watchAdb(Context c) {
        if (!active(c) || !prefs(c).getBoolean("keep_adb", false)) return;
        if (adbObserver == null) {
            adbObserver = new ContentObserver(new Handler(Looper.getMainLooper())) {
                @Override public void onChange(boolean selfChange) { ensureAdb(c); }
            };
            c.getContentResolver().registerContentObserver(Settings.Global.getUriFor(Settings.Global.ADB_ENABLED), false, adbObserver);
        }
        ensureAdb(c);
    }
    private static void ensureAdb(Context c) {
        if (!active(c) || !prefs(c).getBoolean("keep_adb", false)) return;
        if (c.checkSelfPermission(android.Manifest.permission.WRITE_SECURE_SETTINGS) != PackageManager.PERMISSION_GRANTED) return;
        try {
            if (Settings.Global.getInt(c.getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 0)
                Settings.Global.putInt(c.getContentResolver(), Settings.Global.ADB_ENABLED, 1);
        } catch (RuntimeException ignored) { }
    }
}
