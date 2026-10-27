package com.gathin.tvhome;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.SystemClock;
import android.provider.Settings;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.Arrays;
import java.util.UUID;

/** A shell receipt is not a viewing test. This state never executes a system change. */
final class CleanState {
    static final String SAVER = "com.xiaomi.mitv.hyper.screensaver";
    static final long REQUEST_TTL = 120000;
    static SharedPreferences prefs(Context c) { return c.getSharedPreferences("clean", Context.MODE_PRIVATE); }
    private static int boot(Context c) { return Settings.Global.getInt(c.getContentResolver(), "boot_count", -1); }
    static Integer saver(Context c) {
        try { c.getPackageManager().getApplicationInfo(SAVER, 0); return c.getPackageManager().getApplicationEnabledSetting(SAVER); }
        catch (PackageManager.NameNotFoundException | SecurityException e) { return null; }
    }
    static String bootAd(Context c) {
        try { return Settings.System.getString(c.getContentResolver(), "boot_ad"); }
        catch (RuntimeException e) { return null; }
    }
    static boolean disabled(Integer state) { return state != null && state >= 2 && state <= 4; }
    static boolean connected(Context c) {
        long age = SystemClock.elapsedRealtime() - prefs(c).getLong("heartbeat", -100000);
        return age >= 0 && age <= 15000 && prefs(c).getInt("heartbeat_boot", -2) == boot(c);
    }
    static synchronized boolean request(Context c, String action) throws JSONException {
        require(Arrays.asList("disable_saver", "restore").contains(action));
        if (!connected(c) || pending(c) != null) return false;
        JSONObject r = new JSONObject().put("id", UUID.randomUUID().toString()).put("action", action)
                .put("created", SystemClock.elapsedRealtime()).put("wallTime", System.currentTimeMillis())
                .put("boot", boot(c)).put("claimed", false);
        boolean saved = prefs(c).edit().putString("request", r.toString()).commit();
        if (!saved) prefs(c).edit().remove("request").apply();
        return saved;
    }
    static synchronized JSONObject pending(Context c) {
        JSONObject r;
        try { r = new JSONObject(prefs(c).getString("request", "")); }
        catch (JSONException e) { return null; }
        long age = SystemClock.elapsedRealtime() - r.optLong("created", -REQUEST_TTL);
        long wallAge = System.currentTimeMillis() - r.optLong("wallTime", 0);
        if (age < 0 || age > REQUEST_TTL || wallAge < 0 || wallAge > REQUEST_TTL || r.optInt("boot", -2) != boot(c)) {
            prefs(c).edit().remove("request").putString("result", "expired").putLong("result_at", System.currentTimeMillis()).commit();
            return null;
        }
        return r;
    }
    static synchronized JSONObject exchange(Context c, String command, JSONObject data) throws JSONException {
        SharedPreferences p = prefs(c);
        switch (command) {
            case "poll":
                p.edit().putLong("heartbeat", SystemClock.elapsedRealtime()).putInt("heartbeat_boot", boot(c)).commit();
                JSONObject pending = pending(c);
                return new JSONObject().put("protocol", 1).put("request", pending == null ? JSONObject.NULL : pending);
            case "claim":
                JSONObject request = pending(c);
                boolean ok = request != null && !request.optBoolean("claimed") && request.optString("id").equals(data.optString("id"));
                if (ok) require(p.edit().putString("request", request.put("claimed", true).toString()).commit());
                return new JSONObject().put("claimed", ok);
            case "receipt":
                JSONObject current = pending(c);
                String id = data.optString("id"), result = data.optString("result");
                require(Arrays.asList("applied", "restored", "unchanged", "conflict", "failed", "unsupported", "ready").contains(result));
                require(id.isEmpty() || (current != null && id.equals(current.optString("id")) && current.optBoolean("claimed")));
                String journal = data.optString("journal");
                SharedPreferences.Editor edit = p.edit().putLong("heartbeat", SystemClock.elapsedRealtime())
                        .putInt("heartbeat_boot", boot(c)).putBoolean("can_restore", data.optBoolean("canRestore"))
                        .putString("journal", journal.substring(0, Math.min(40, journal.length())));
                if (!id.isEmpty()) edit.remove("request").putString("result", result).putLong("result_at", System.currentTimeMillis());
                require(edit.commit());
                return new JSONObject().put("accepted", true);
            default: throw new IllegalArgumentException("Unknown command");
        }
    }
    static void require(boolean valid) { if (!valid) throw new IllegalArgumentException("Invalid request"); }
    static boolean canRestore(Context c) { return prefs(c).getBoolean("can_restore", false); }
    static String verification(Context c, String key) { return prefs(c).getString("test_" + key, "untested"); }
    static void verify(Context c, String key, String result) {
        require(Arrays.asList("home", "wake", "hdmi", "idle").contains(key));
        require(Arrays.asList("passed", "failed", "untested").contains(result));
        prefs(c).edit().putString("test_" + key, result).putLong("test_at_" + key, System.currentTimeMillis()).apply();
    }
}
