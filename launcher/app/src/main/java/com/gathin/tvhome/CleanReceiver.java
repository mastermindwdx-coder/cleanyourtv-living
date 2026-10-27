package com.gathin.tvhome;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.util.Base64;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;

/** Protected by DUMP in the manifest: only an authorised shell can exchange state/receipts. */
public final class CleanReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c, Intent intent) {
        try {
            String payload = intent.getStringExtra("payload");
            if (payload == null) payload = "e30=";
            CleanState.require(payload.length() <= 8192);
            JSONObject data = new JSONObject(new String(Base64.decode(payload, Base64.DEFAULT), StandardCharsets.UTF_8));
            String command = intent.getStringExtra("command");
            if (command == null) command = "";
            SharedPreferences p = CleanHomeMode.prefs(c);
            String[] keys = {"enabled", "keep_adb", "clean_restore_hold"};
            JSONObject reply;
            switch (command) {
                case "home_mode":
                    reply = new JSONObject().put("mode", CleanHomeMode.stock(c) ? "stock" : "clean")
                            .put("enabled", CleanHomeMode.active(c)).put("bound", CleanHomeController.bound()); break;
                case "guard_state":
                    reply = new JSONObject();
                    for (String key : keys) reply.put(key, p.contains(key) ? p.getBoolean(key, false) : JSONObject.NULL);
                    break;
                case "guard_hold":
                    CleanState.require(p.edit().putBoolean("clean_restore_hold", true).putBoolean("keep_adb", false).commit());
                    reply = new JSONObject().put("held", true); break;
                case "guard_restore":
                    CleanState.require(data.length() == keys.length);
                    SharedPreferences.Editor edit = p.edit();
                    for (String key : keys) {
                        CleanState.require(data.has(key));
                        if (data.isNull(key)) edit.remove(key); else edit.putBoolean(key, data.getBoolean(key));
                    }
                    CleanState.require(edit.commit());
                    reply = new JSONObject().put("restored", true); break;
                default: reply = CleanState.exchange(c, command, data);
            }
            setResultCode(0);
            setResultData(Base64.encodeToString(reply.toString().getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
        } catch (Exception e) { setResultCode(1); setResultData("invalid_request"); }
    }
}
