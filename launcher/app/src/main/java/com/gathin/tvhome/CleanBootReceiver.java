package com.gathin.tvhome;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class CleanBootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c, Intent i) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction()) || Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(i.getAction()))
            if (CleanHomeMode.active(c)) GuardKeep.ensureHomeKey(c);
    }
}
