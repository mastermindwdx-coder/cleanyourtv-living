package com.gathin.tvhome;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Independent Home/idle choices. A document is copied locally; no enduring provider access is needed. */
public final class VideoWallpaperActivity extends Activity {
    private LinearLayout rows;
    private String pendingSlot = "home";
    private boolean busy;
    @Override protected void attachBaseContext(Context base) { super.attachBaseContext(LauncherLocale.wrap(base)); }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (state != null) pendingSlot = state.getString("slot", "home");
        rows = new LinearLayout(this); rows.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(42); rows.setPadding(pad, pad, pad, pad); rows.setBackgroundColor(0xff151820);
        setContentView(rows);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        refresh();
    }
    @Override protected void onSaveInstanceState(Bundle out) { out.putString("slot", pendingSlot); super.onSaveInstanceState(out); }
    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private TextView text(String label, int size) {
        TextView t = new TextView(this); t.setText(label); t.setTextSize(size); t.setTextColor(0xffeeeeee);
        t.setPadding(dp(18), dp(16), dp(18), dp(16)); return t;
    }
    private void refresh() {
        rows.removeAllViews(); rows.addView(text(getString(R.string.video_wallpaper_title), 28));
        rows.addView(text(getString(R.string.video_wallpaper_hint), 17));
        for (String slot : new String[]{"home", "clock"}) {
            String name = VideoWallpaper.choice(this, slot);
            TextView button = text(getString(slot.equals("home") ? R.string.video_wallpaper_home : R.string.video_wallpaper_clock)
                    + "  ·  " + (name.isEmpty() ? getString(R.string.video_wallpaper_off) : name), 20);
            button.setBackgroundResource(R.drawable.add_app_card); button.setFocusable(true); button.setClickable(true);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2); lp.topMargin = dp(18);
            rows.addView(button, lp); button.setOnClickListener(v -> { if (!busy) pick(slot); });
        }
        TextView preview=text(getString(R.string.video_wallpaper_preview),20);
        preview.setBackgroundResource(R.drawable.add_app_card); preview.setFocusable(true); preview.setClickable(true);
        LinearLayout.LayoutParams previewLp=new LinearLayout.LayoutParams(-1,-2);previewLp.topMargin=dp(18);
        rows.addView(preview,previewLp);
        preview.setOnClickListener(v -> startActivity(new Intent(this,ClockActivity.class)));
        rows.getChildAt(pendingSlot.equals("clock") ? 3 : 2).requestFocus();
    }
    private void pick(String slot) {
        pendingSlot = slot;
        File[] raw = VideoWallpaper.directory(this).listFiles(f -> f.isFile() && VideoWallpaper.validName(f.getName()));
        List<File> files = new ArrayList<>(); if (raw != null) files.addAll(Arrays.asList(raw));
        files.sort((a,b) -> a.getName().compareToIgnoreCase(b.getName()));
        List<String> labels = new ArrayList<>(); labels.add(getString(R.string.video_wallpaper_off));
        for (File f : files) labels.add(f.getName()); labels.add(getString(R.string.video_wallpaper_import));
        new AlertDialog.Builder(this).setTitle(slot.equals("home") ? R.string.video_wallpaper_home : R.string.video_wallpaper_clock)
                .setItems(labels.toArray(new String[0]), (dialog, which) -> {
                    if (which == 0) { VideoWallpaper.choose(this,slot,""); refresh(); }
                    else if (which <= files.size()) verifyAndUse(files.get(which - 1),slot,false);
                    else {
                        Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("video/*").addCategory(Intent.CATEGORY_OPENABLE);
                        try { startActivityForResult(pick,1); }
                        catch (android.content.ActivityNotFoundException e) { Toast.makeText(this,R.string.video_wallpaper_no_picker,Toast.LENGTH_LONG).show(); }
                    }
                }).show();
    }
    private void verifyAndUse(File file, String slot, boolean imported) {
        busy=true;Toast.makeText(this,R.string.video_wallpaper_loading,Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            boolean valid=VideoWallpaper.verified4k(file);
            if (!valid && imported) file.delete();
            runOnUiThread(() -> {
                busy=false; if (isFinishing() || isDestroyed()) return;
                if (valid) VideoWallpaper.choose(this,slot,file.getName());
                Toast.makeText(this,valid?R.string.video_wallpaper_done:R.string.video_wallpaper_invalid,Toast.LENGTH_LONG).show(); refresh();
            });
        },"verify-4k-wallpaper").start();
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if (request!=1 || result!=RESULT_OK || data==null || data.getData()==null) return;
        busy=true;String slot=pendingSlot;
        File dir=VideoWallpaper.directory(this); dir.mkdirs();
        File target=new File(dir,"wallpaper-"+System.currentTimeMillis()+".mp4");
        android.net.Uri uri=data.getData();
        new Thread(() -> {
            try (InputStream input=getContentResolver().openInputStream(uri);FileOutputStream output=new FileOutputStream(target)) {
                if (input==null) throw new java.io.IOException("No input");
                byte[] buffer=new byte[65536];long bytes=0;int n;
                while((n=input.read(buffer))!=-1) { bytes+=n;if(bytes>1024L*1024*1024)throw new java.io.IOException("Video exceeds 1 GiB");output.write(buffer,0,n); }
                runOnUiThread(() -> { if(isFinishing()||isDestroyed()){busy=false;return;} verifyAndUse(target,slot,true); });
            } catch(Exception e) {
                target.delete();runOnUiThread(() -> {busy=false;if(!isFinishing())Toast.makeText(this,R.string.video_wallpaper_error,Toast.LENGTH_LONG).show();});
            }
        },"import-4k-wallpaper").start();
    }
}
