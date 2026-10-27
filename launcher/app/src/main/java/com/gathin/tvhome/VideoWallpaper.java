package com.gathin.tvhome;

import android.content.Context;
import android.media.MediaMetadataRetriever;
import android.media.MediaPlayer;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.Toast;
import java.io.File;
import java.util.Locale;

/** Local, muted video on its own Surface: no Internet, no UI-resolution video texture, no wake lock. */
final class VideoWallpaper implements SurfaceHolder.Callback {
    private final Context context;
    private final FrameLayout root;
    private final View fallback, shade;
    private final SurfaceView surface;
    private final String slot;
    private MediaPlayer player;
    private boolean active, failed;
    private File file;
    static File directory(Context c) { return new File(c.getExternalFilesDir(null), "dynamic-wallpapers"); }
    static boolean validName(String name) {
        return name != null && !name.isEmpty() && name.length() <= 160 && !name.contains("/")
                && !name.contains("\\") && !name.contains("..") && name.toLowerCase(Locale.ROOT).endsWith(".mp4");
    }
    static boolean is4k(int width, int height, int rotation) {
        return width >= 3840 && height >= 2160 && width <= 4096 && height <= 2304
                && width >= height && rotation % 180 == 0;
    }
    static boolean verified4k(File file) {
        MediaMetadataRetriever reader = new MediaMetadataRetriever();
        try {
            reader.setDataSource(file.getPath());
            String rotation = reader.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION);
            return is4k(Integer.parseInt(reader.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)),
                    Integer.parseInt(reader.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)),
                    rotation == null ? 0 : Integer.parseInt(rotation));
        } catch (RuntimeException e) { return false; }
        finally { try { reader.release(); } catch (Exception ignored) { } }
    }
    static String choice(Context c, String slot) { return c.getSharedPreferences("video_wallpaper", 0).getString(slot, ""); }
    static void choose(Context c, String slot, String name) {
        if (!(slot.equals("home") || slot.equals("clock")) || !(name.isEmpty() || validName(name)))
            throw new IllegalArgumentException("Invalid wallpaper choice");
        c.getSharedPreferences("video_wallpaper", 0).edit().putString(slot, name).apply();
    }
    VideoWallpaper(Context c, FrameLayout root, View fallback, String slot, float dim) {
        context = c; this.root = root; this.fallback = fallback; this.slot = slot;
        surface = new SurfaceView(c);
        surface.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        surface.setFocusable(false); surface.setVisibility(View.GONE);
        surface.getHolder().addCallback(this);
        root.addView(surface, 0, new FrameLayout.LayoutParams(-1, -1));
        shade = new View(c); shade.setBackgroundColor(((int)(255 * dim)) << 24);
        shade.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        shade.setVisibility(View.GONE);
        root.addView(shade, 1, new FrameLayout.LayoutParams(-1, -1));
    }
    boolean selected() { return active && file != null && !failed; }
    void start() {
        stop(); active = true; failed = false;
        String name = choice(context, slot);
        File selected = validName(name) ? new File(directory(context), name) : null;
        if (selected == null || !selected.isFile()) return;
        file = selected; surface.setVisibility(View.VISIBLE);
        if (surface.getHolder().getSurface().isValid()) open();
    }
    void stop() {
        active = false; release(); file = null;
        surface.setVisibility(View.GONE); shade.setVisibility(View.GONE); fallback.setVisibility(View.VISIBLE);
    }
    void close() { stop(); surface.getHolder().removeCallback(this); root.removeView(surface); root.removeView(shade); }
    private void release() {
        MediaPlayer old = player; player = null;
        if (old != null) {
            old.setOnPreparedListener(null); old.setOnErrorListener(null); old.setOnInfoListener(null); old.release();
            Log.i("TvHome.Video", slot + " released");
        }
    }
    private void fail() {
        failed = true; release(); surface.setVisibility(View.GONE); shade.setVisibility(View.GONE);
        fallback.setVisibility(View.VISIBLE);
        Toast.makeText(context, R.string.video_wallpaper_error, Toast.LENGTH_LONG).show();
    }
    private void open() {
        if (!active || failed || file == null || player != null) return;
        try {
            MediaPlayer next = new MediaPlayer(); player = next;
            next.setDataSource(file.getPath()); next.setDisplay(surface.getHolder()); next.setScreenOnWhilePlaying(false);
            next.setVolume(0f, 0f); next.setLooping(true);
            next.setOnPreparedListener(p -> {
                if (player != p || !active) return;
                if (!is4k(p.getVideoWidth(), p.getVideoHeight(), 0)) { fail(); return; }
                surface.getHolder().setFixedSize(p.getVideoWidth(), p.getVideoHeight());
                p.setVideoScalingMode(MediaPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING); p.start();
                Log.i("TvHome.Video", slot + " playing " + p.getVideoWidth() + "x" + p.getVideoHeight());
            });
            next.setOnInfoListener((p, what, extra) -> {
                if (player == p && active && what == MediaPlayer.MEDIA_INFO_VIDEO_RENDERING_START) {
                    fallback.setVisibility(View.INVISIBLE); shade.setVisibility(View.VISIBLE);
                }
                return false;
            });
            next.setOnErrorListener((p, what, extra) -> { if (player == p && active) fail(); return true; });
            next.prepareAsync();
        } catch (Exception e) { Log.w("TvHome.Video", "Cannot start local wallpaper", e); fail(); }
    }
    @Override public void surfaceCreated(SurfaceHolder holder) { open(); }
    @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) { }
    @Override public void surfaceDestroyed(SurfaceHolder holder) { release(); }
}
