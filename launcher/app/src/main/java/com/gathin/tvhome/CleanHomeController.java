package com.gathin.tvhome;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.usage.UsageEvents;
import android.app.usage.UsageStatsManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.os.UserManager;
import android.util.Log;
import android.view.KeyCharacterMap;
import android.view.KeyEvent;
import android.view.ViewConfiguration;
import android.view.accessibility.AccessibilityEvent;
import android.widget.Toast;
import java.util.HashSet;
import java.util.Set;

/** Local MFTR0 guard. No polling of apps, no HDMI takeover, no masking or power-mode changes. */
final class CleanHomeController {
    private static final String TAG = "CleanHome";
    private static CleanHomeController running;
    private static boolean mainResumed;
    private AccessibilityService service;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Set<ComponentName> homes = new HashSet<>();
    private final Set<ComponentName> activities = new HashSet<>();
    private final HomePressSequence presses = new HomePressSequence();
    private final NavigationPulse navigation = new NavigationPulse();
    private ComponentName front;
    private boolean screenOff, down, held, stockNavigation, registered;
    private long suppressBroadcastUntil, lastLaunch = Long.MIN_VALUE / 2;
    private final Runnable expiry = () -> { if (!presses.activeAt(now())) presses.reset(); filter(); };
    private final Runnable homeHold = () -> {
        held = true; presses.reset(); filter();
        service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_RECENTS);
    };
    private final Runnable settle = () -> { probeFront(); filter(); takeOver(); };
    private final Runnable navigationRepeat = new Runnable() {
        @Override public void run() {
            if (!stockNavigation || screenOff) { navigation.reset(); return; }
            Integer code = navigation.repeat(now());
            if (code != null) pulse(code);
            if (navigation.active()) handler.postDelayed(this, NavigationPulse.REPEAT_MS);
        }
    };
    private final BroadcastReceiver signals = new BroadcastReceiver() {
        @Override public void onReceive(Context c, Intent i) {
            String action = i.getAction();
            if (Intent.ACTION_SCREEN_OFF.equals(action)) {
                screenOff = true; mainResumed = false; front = null; cancelGesture();
                handler.removeCallbacks(settle); filter();
            } else if (Intent.ACTION_SCREEN_ON.equals(action) || Intent.ACTION_USER_UNLOCKED.equals(action)) {
                screenOff = !interactive();
                handler.removeCallbacks(settle); handler.postDelayed(settle, 1500);
            } else if (Intent.ACTION_CLOSE_SYSTEM_DIALOGS.equals(action) && "homekey".equals(i.getStringExtra("reason"))) {
                if (screenOff || !unlocked() || down || now() < suppressBroadcastUntil) return;
                shortHome("broadcast");
            }
        }
    };

    CleanHomeController(AccessibilityService service) { this.service = service; }
    private long now() { return SystemClock.uptimeMillis(); }
    private boolean unlocked() { return service.getSystemService(UserManager.class).isUserUnlocked(); }
    private boolean interactive() {
        PowerManager p = service.getSystemService(PowerManager.class);
        return p != null && p.isInteractive();
    }
    void connect() {
        running = this;
        Intent home = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).setPackage("com.mitv.tvhome");
        for (ResolveInfo r : service.getPackageManager().queryIntentActivities(home, PackageManager.MATCH_DISABLED_COMPONENTS))
            homes.add(new ComponentName(r.activityInfo.packageName, r.activityInfo.name));
        screenOff = !interactive();
        AccessibilityServiceInfo info = service.getServiceInfo();
        if (info != null) { info.eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED; info.notificationTimeout = 0; service.setServiceInfo(info); }
        IntentFilter intents = new IntentFilter(Intent.ACTION_SCREEN_ON);
        intents.addAction(Intent.ACTION_SCREEN_OFF); intents.addAction(Intent.ACTION_USER_UNLOCKED);
        intents.addAction(Intent.ACTION_CLOSE_SYSTEM_DIALOGS);
        if (Build.VERSION.SDK_INT >= 33) service.registerReceiver(signals, intents, Context.RECEIVER_EXPORTED);
        else registerLegacySignals(intents);
        registered = true;
        probeFront(); filter();
        handler.postDelayed(settle, 1500);
        Log.i(TAG, "bound stock=" + CleanHomeMode.stock(service));
    }
    @android.annotation.SuppressLint("UnspecifiedRegisterReceiverFlag")
    private void registerLegacySignals(IntentFilter intents) {
        // Called only below API 33. The pinned AndroidX core predates its receiver-flags helper.
        service.registerReceiver(signals, intents);
    }
    void destroy() {
        if (running == this) running = null;
        handler.removeCallbacksAndMessages(null);
        if (registered) service.unregisterReceiver(signals);
        registered = false;
    }
    static void resumed(Context c, boolean value) {
        mainResumed = value;
        if (running == null) return;
        if (value) running.front = new ComponentName(c, MainActivity.class);
        else if (new ComponentName(c, MainActivity.class).equals(running.front)) running.front = null;
        running.filter();
    }
    static boolean bound() { return running != null; }
    private void probeFront() {
        if (screenOff || !unlocked()) return;
        if (mainResumed) { front = new ComponentName(service, MainActivity.class); return; }
        UsageStatsManager usage = service.getSystemService(UsageStatsManager.class);
        if (usage == null) return;
        try {
            long end = System.currentTimeMillis();
            UsageEvents events = usage.queryEvents(end - 24 * 60 * 60 * 1000L, end);
            UsageEvents.Event e = new UsageEvents.Event();
            while (events.hasNextEvent()) {
                events.getNextEvent(e);
                if (e.getEventType() == UsageEvents.Event.ACTIVITY_RESUMED && e.getPackageName() != null && e.getClassName() != null)
                    front = new ComponentName(e.getPackageName(), e.getClassName());
            }
        } catch (RuntimeException e) { Log.w(TAG, "foreground unavailable", e); }
    }
    private boolean stockFront() { return homes.contains(front); }
    private boolean ourFront() { return mainResumed || (front != null && service.getPackageName().equals(front.getPackageName())); }
    private void filter() {
        stockNavigation = !screenOff && CleanHomeMode.active(service) && CleanHomeMode.stock(service) && stockFront();
        if (!stockNavigation) stopNavigation();
        boolean wanted = !screenOff && CleanHomeMode.active(service)
                && (ourFront() || stockNavigation || presses.activeAt(now()));
        AccessibilityServiceInfo info = service.getServiceInfo();
        if (info == null) return;
        int flag = AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS;
        int flags = wanted ? info.flags | flag : info.flags & ~flag;
        if (flags != info.flags) { info.flags = flags; service.setServiceInfo(info); }
    }
    void window(AccessibilityEvent e) {
        if (e.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED || e.getPackageName() == null || e.getClassName() == null) return;
        ComponentName candidate = new ComponentName(e.getPackageName().toString(), e.getClassName().toString());
        if (!activities.contains(candidate)) {
            try { service.getPackageManager().getActivityInfo(candidate, 0); activities.add(candidate); }
            catch (PackageManager.NameNotFoundException ignored) { return; }
        }
        front = candidate;
        if (!service.getPackageName().equals(front.getPackageName())) mainResumed = false;
        if (!stockFront() && !ourFront()) { presses.reset(); stopNavigation(); }
        filter(); takeOver();
    }
    private void takeOver() {
        if (CleanHomeMode.active(service) && !CleanHomeMode.stock(service) && !screenOff && unlocked() && stockFront()) openHome();
    }
    private boolean openHome() {
        if (!CleanHomeMode.active(service) || screenOff || !unlocked()) return false;
        if (now() - lastLaunch < 400) return true;
        try {
            // Normal task, never CATEGORY_HOME: the firmware retains the original Home owner.
            service.startActivity(new Intent(service, MainActivity.class).setAction(Intent.ACTION_MAIN)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED));
            lastLaunch = now(); return true;
        } catch (RuntimeException e) { Log.w(TAG, "Home launch refused", e); return false; }
    }
    private boolean stockHome() {
        suppressBroadcastUntil = now() + 300;
        return service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_HOME);
    }
    private void shortHome(String source) {
        boolean toggle = presses.press(now());
        handler.removeCallbacks(expiry);
        Log.i(TAG, "Home source=" + source + " count=" + presses.count + " toggle=" + toggle);
        if (toggle) {
            boolean before = CleanHomeMode.stock(service), next = !before;
            if (!CleanHomeMode.chooseStock(service, next)) { toast(R.string.clean_mode_failed); return; }
            handler.removeCallbacks(settle);
            boolean opened = next ? stockHome() : openHome();
            if (!opened) { CleanHomeMode.chooseStock(service, before); toast(R.string.clean_mode_failed); }
            else { toast(next ? R.string.clean_mode_stock_toast : R.string.clean_mode_aerial_toast); Log.i(TAG, "mode=" + (next ? "stock" : "clean")); }
        } else {
            handler.postDelayed(expiry, HomePressSequence.MAX_GAP_MS + 10);
            if (CleanHomeMode.stock(service)) stockHome(); else openHome();
        }
        filter();
    }
    private void toast(int id) { Toast.makeText(service, id, Toast.LENGTH_LONG).show(); }
    private void cancelGesture() {
        presses.reset(); down = false; held = false;
        handler.removeCallbacks(homeHold); handler.removeCallbacks(expiry); stopNavigation();
    }
    boolean key(KeyEvent e) {
        if (!CleanHomeMode.active(service) || screenOff) return false;
        int code = e.getKeyCode();
        if (code != KeyEvent.KEYCODE_HOME) {
            // No Binder lookup in this path: acknowledge before the system's 500 ms filter timeout.
            if (e.getAction() == KeyEvent.ACTION_DOWN && presses.count > 0) { presses.reset(); handler.post(this::filter); }
            if (stockNavigation && direction(code)) return navigationKey(e);
            return false;
        }
        if (e.getDeviceId() == KeyCharacterMap.VIRTUAL_KEYBOARD) return false;
        stopNavigation();
        if (e.getAction() == KeyEvent.ACTION_DOWN && e.getRepeatCount() == 0) {
            down = true; held = false;
            handler.removeCallbacks(homeHold); handler.postDelayed(homeHold, ViewConfiguration.getLongPressTimeout());
        } else if (e.getAction() == KeyEvent.ACTION_UP) {
            handler.removeCallbacks(homeHold);
            if (!down) return false;
            down = false;
            if (e.isCanceled() || held) { presses.reset(); filter(); return true; }
            suppressBroadcastUntil = now() + 100;
            handler.post(() -> shortHome("key"));
        }
        return true;
    }
    private boolean direction(int code) { return code >= KeyEvent.KEYCODE_DPAD_UP && code <= KeyEvent.KEYCODE_DPAD_RIGHT; }
    private void stopNavigation() { navigation.reset(); handler.removeCallbacks(navigationRepeat); }
    private boolean navigationKey(KeyEvent e) {
        if (e.getDeviceId() == KeyCharacterMap.VIRTUAL_KEYBOARD) return false;
        if (e.getAction() == KeyEvent.ACTION_DOWN && navigation.down(e.getKeyCode(), e.getDownTime(), now(), e.getRepeatCount())) {
            int code = e.getKeyCode(); handler.removeCallbacks(navigationRepeat);
            handler.post(() -> pulse(code)); handler.postDelayed(navigationRepeat, NavigationPulse.FIRST_REPEAT_MS);
        } else if (e.getAction() == KeyEvent.ACTION_UP) {
            navigation.up(e.getKeyCode()); if (!navigation.active()) handler.removeCallbacks(navigationRepeat);
        }
        return true;
    }
    private void pulse(int code) {
        if (Build.VERSION.SDK_INT < 33 || screenOff || !stockNavigation) return;
        int action;
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_UP: action = AccessibilityService.GLOBAL_ACTION_DPAD_UP; break;
            case KeyEvent.KEYCODE_DPAD_DOWN: action = AccessibilityService.GLOBAL_ACTION_DPAD_DOWN; break;
            case KeyEvent.KEYCODE_DPAD_LEFT: action = AccessibilityService.GLOBAL_ACTION_DPAD_LEFT; break;
            default: action = AccessibilityService.GLOBAL_ACTION_DPAD_RIGHT;
        }
        service.performGlobalAction(action);
    }
}
