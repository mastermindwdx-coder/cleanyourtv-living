package com.gathin.tvhome;
import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.FrameLayout;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(sdk=28,qualifiers="zh-rCN")
public class LocalHomeUiTest {
    @Test public void chineseAddCardContainsEveryRequiredView() {
        Context c=RuntimeEnvironment.getApplication();
        View card=LayoutInflater.from(c).inflate(R.layout.row_app_library,new FrameLayout(c),false);
        assertNotNull(card.findViewById(R.id.btnLibrary));
        assertNotNull(card.findViewById(R.id.name));
        assertTrue(card.findViewById(R.id.btnLibrary).isFocusable());
    }
    @Test public void removeAndReAddSurviveFreshReads() {
        Context c=RuntimeEnvironment.getApplication();String pkg="test.wallpaper.app";
        assertTrue(LibraryApps.save(c,pkg,false));assertTrue(LibraryApps.loadRemoved(c).contains(pkg));
        assertFalse(LibraryApps.visible(true,false,false,LibraryApps.loadRemoved(c).contains(pkg)));
        assertTrue(LibraryApps.save(c,pkg,true));assertFalse(LibraryApps.loadRemoved(c).contains(pkg));
        assertTrue(LibraryApps.load(c).contains(pkg));
    }
    @Test public void wallpaperSlotsAreIndependentAndCanBeDisabled() {
        Context c=RuntimeEnvironment.getApplication();VideoWallpaper.choose(c,"home","lake.mp4");
        VideoWallpaper.choose(c,"clock","forest.mp4");VideoWallpaper.choose(c,"home","");
        assertEquals("",VideoWallpaper.choice(c,"home"));assertEquals("forest.mp4",VideoWallpaper.choice(c,"clock"));
    }
}
