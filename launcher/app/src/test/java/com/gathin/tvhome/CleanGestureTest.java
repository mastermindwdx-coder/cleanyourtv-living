package com.gathin.tvhome;

import org.junit.Test;
import static org.junit.Assert.*;

public class CleanGestureTest {
    @Test public void thirdPressOnlyAndCooldown() {
        HomePressSequence s=new HomePressSequence();
        assertFalse(s.press(1000));assertFalse(s.press(1200));assertTrue(s.press(1400));
        assertFalse(s.press(1700));assertEquals(0,s.count);
        assertFalse(s.press(3000));assertFalse(s.press(3200));assertTrue(s.press(3400));
    }
    @Test public void duplicateBroadcastCannotCountAsAnotherPress() {
        HomePressSequence s=new HomePressSequence();s.press(1000);s.press(1030);
        assertEquals(1,s.count);assertFalse(s.press(1200));assertTrue(s.press(1400));
    }
    @Test public void pauseOrAnotherKeyCancelsSequence() {
        HomePressSequence s=new HomePressSequence();s.press(1000);s.press(1200);
        assertFalse(s.press(2000));assertEquals(1,s.count);
        s.reset();assertFalse(s.press(2200));assertFalse(s.press(2400));
    }
    @Test public void captureWindowExpires() {
        HomePressSequence s=new HomePressSequence();s.press(1000);
        assertTrue(s.activeAt(1700));assertFalse(s.activeAt(1701));
    }
    @Test public void tapAndDuplicateDownProduceOnePulse() {
        NavigationPulse n=new NavigationPulse();assertTrue(n.down(22,1000,1000,0));
        assertFalse(n.down(22,1000,1005,0));assertFalse(n.down(22,1000,1200,1));
        n.up(22);assertNull(n.repeat(1700));assertFalse(n.active());
    }
    @Test public void heldDirectionHasBoundedRepeat() {
        NavigationPulse n=new NavigationPulse();n.down(22,1000,1000,0);
        assertNull(n.repeat(1649));assertEquals(Integer.valueOf(22),n.repeat(1650));
        assertNull(n.repeat(1700));assertEquals(Integer.valueOf(22),n.repeat(1800));
        assertNull(n.repeat(6001));assertFalse(n.active());assertFalse(n.down(22,1000,6100,20));
    }
    @Test public void switchingDirectionAndLeavingHomeCancelOldPulses() {
        NavigationPulse n=new NavigationPulse();n.down(22,1000,1000,0);n.down(21,1200,1200,0);n.up(22);
        assertEquals(Integer.valueOf(21),n.repeat(1850));n.reset();assertNull(n.repeat(2100));
    }
}
