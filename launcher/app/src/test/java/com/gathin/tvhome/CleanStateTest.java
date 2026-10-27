package com.gathin.tvhome;

import android.content.Context;
import android.provider.Settings;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowSystemClock;
import java.time.Duration;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=28)
public class CleanStateTest {
    private Context c;
    @Before public void reset() {
        c=RuntimeEnvironment.getApplication();CleanState.prefs(c).edit().clear().commit();
        CleanHomeMode.prefs(c).edit().clear().commit();
    }
    @Test public void standaloneApkCannotSubmitSystemMutation() throws Exception {
        assertFalse(CleanState.connected(c));assertFalse(CleanState.request(c,"disable_saver"));assertNull(CleanState.pending(c));
    }
    @Test public void doubleClickAndDuplicateClaimCannotApplyTwice() throws Exception {
        CleanState.exchange(c,"poll",new JSONObject());assertTrue(CleanState.request(c,"disable_saver"));
        String id=CleanState.pending(c).getString("id");assertFalse(CleanState.request(c,"restore"));
        JSONObject claim=new JSONObject().put("id",id);
        assertTrue(CleanState.exchange(c,"claim",claim).getBoolean("claimed"));
        assertFalse(CleanState.exchange(c,"claim",claim).getBoolean("claimed"));
    }
    @Test public void receiptRequiresMatchingClaimAndDoesNotMarkViewingPassed() throws Exception {
        CleanState.exchange(c,"poll",new JSONObject());CleanState.request(c,"disable_saver");
        String id=CleanState.pending(c).getString("id");
        JSONObject receipt=new JSONObject().put("id",id).put("result","applied").put("canRestore",true);
        assertThrows(IllegalArgumentException.class,()->CleanState.exchange(c,"receipt",receipt));
        CleanState.exchange(c,"receipt",new JSONObject().put("result","ready"));assertNotNull(CleanState.pending(c));
        CleanState.exchange(c,"claim",new JSONObject().put("id",id));CleanState.exchange(c,"receipt",receipt);
        assertNull(CleanState.pending(c));assertTrue(CleanState.canRestore(c));assertEquals("untested",CleanState.verification(c,"idle"));
    }
    @Test public void wrongReceiptCannotConsumeRequest() throws Exception {
        CleanState.exchange(c,"poll",new JSONObject());CleanState.request(c,"disable_saver");
        assertThrows(IllegalArgumentException.class,()->CleanState.exchange(c,"receipt",new JSONObject().put("id","wrong").put("result","applied")));
        assertNotNull(CleanState.pending(c));
    }
    @Test public void staleRequestExpiresInsteadOfRunningOnReconnect() throws Exception {
        CleanState.exchange(c,"poll",new JSONObject());CleanState.request(c,"disable_saver");
        ShadowSystemClock.advanceBy(Duration.ofMillis(CleanState.REQUEST_TTL+1));
        assertNull(CleanState.pending(c));assertFalse(CleanState.connected(c));
    }
    @Test public void rebootInvalidatesPendingAndHeartbeat() throws Exception {
        Settings.Global.putInt(c.getContentResolver(),"boot_count",10);
        CleanState.exchange(c,"poll",new JSONObject());CleanState.request(c,"disable_saver");
        Settings.Global.putInt(c.getContentResolver(),"boot_count",11);
        assertNull(CleanState.pending(c));assertFalse(CleanState.connected(c));
    }
    @Test public void unknownActionAndFalseBootNamespaceRejected() {
        assertThrows(IllegalArgumentException.class,()->CleanState.request(c,"disable_stock_home"));
        Settings.System.putString(c.getContentResolver(),"boot_ad","1");
        Settings.Global.putString(c.getContentResolver(),"boot_ad","0");assertEquals("1",CleanState.bootAd(c));
    }
    @Test public void manualViewingAndModePersistSeparatelyFromGuardHold() {
        CleanState.verify(c,"home","passed");assertEquals("passed",CleanState.verification(c,"home"));
        assertFalse(CleanHomeMode.active(c));assertFalse(CleanHomeMode.stock(c));
        CleanHomeMode.prefs(c).edit().putBoolean("enabled",true).commit();assertTrue(CleanHomeMode.active(c));
        assertTrue(CleanHomeMode.chooseStock(c,true));assertTrue(CleanHomeMode.stock(c));
        CleanHomeMode.prefs(c).edit().putBoolean("clean_restore_hold",true).commit();
        assertFalse(CleanHomeMode.active(c));assertTrue(CleanHomeMode.stock(c));
    }
}
