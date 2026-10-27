package com.gathin.tvhome;
import org.junit.Test;
import static org.junit.Assert.*;
public class VideoWallpaperTest {
    @Test public void requiresLandscape4kRatherThanFilenameClaim() {
        assertTrue(VideoWallpaper.is4k(3840,2160,0));
        assertTrue(VideoWallpaper.is4k(4096,2160,180));
        assertFalse(VideoWallpaper.is4k(1920,1080,0));
        assertFalse(VideoWallpaper.is4k(2160,3840,0));
        assertFalse(VideoWallpaper.is4k(3840,2160,90));
        assertFalse(VideoWallpaper.is4k(7680,4320,0));
    }
    @Test public void localSelectionCannotEscapeWallpaperDirectory() {
        assertTrue(VideoWallpaper.validName("山海 4K.mp4"));
        assertFalse(VideoWallpaper.validName("../private.mp4"));
        assertFalse(VideoWallpaper.validName("C:\\private.mp4"));
        assertFalse(VideoWallpaper.validName("https://host/video.mp4"));
        assertFalse(VideoWallpaper.validName("picture.jpg"));
    }
}
