package com.gathin.tvhome;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/** Native remote UI; no Compose, networking or shell execution added to the launcher. */
public final class CleanActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final List<Runnable> refreshers = new ArrayList<>();
    private LinearLayout content;
    private TextView footer;
    private final TextView[] tabs = new TextView[3];
    private int tab;
    private final Runnable tick = new Runnable() {
        @Override public void run() { refresh(); handler.postDelayed(this, 3000); }
    };
    @Override protected void attachBaseContext(Context base) { super.attachBaseContext(LauncherLocale.wrap(base)); }
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        LinearLayout root = column(); root.setPadding(dp(28), dp(18), dp(28), dp(14)); root.setBackgroundColor(Color.rgb(16,20,25));
        LinearLayout title = row();
        TextView heading = text(getString(R.string.clean_title) + " · CleanYourTV", 25, Color.WHITE); heading.setTypeface(null, Typeface.BOLD);
        title.addView(heading, new LinearLayout.LayoutParams(0, -2, 1));
        title.addView(button(R.string.clean_back, this::finish)); root.addView(title);
        LinearLayout choices = row(); choices.setPadding(0,dp(12),0,dp(10));
        int[] labels = {R.string.clean_tab_check, R.string.clean_tab_verify, R.string.clean_tab_restore};
        for (int i=0;i<3;i++) { final int index=i; tabs[i]=button(labels[i],()->show(index)); choices.addView(tabs[i]); }
        root.addView(choices);
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(false);
        content = column(); scroll.addView(content); root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        footer = text("",12,Color.LTGRAY); footer.setPadding(0,dp(8),0,0); root.addView(footer);
        setContentView(root); show(0); tabs[0].requestFocus();
    }
    @Override protected void onResume() { super.onResume(); handler.post(tick); }
    @Override protected void onPause() { handler.removeCallbacks(tick); super.onPause(); }
    private int dp(int x) { return Math.round(x*getResources().getDisplayMetrics().density); }
    private LinearLayout column() { LinearLayout x=new LinearLayout(this); x.setOrientation(LinearLayout.VERTICAL); return x; }
    private LinearLayout row() { LinearLayout x=new LinearLayout(this); x.setGravity(Gravity.CENTER_VERTICAL); return x; }
    private TextView text(String value,int size,int color) { TextView x=new TextView(this); x.setText(value); x.setTextSize(size); x.setTextColor(color); return x; }
    private GradientDrawable shape(int color) { GradientDrawable d=new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(9)); return d; }
    private TextView button(int label,Runnable action) {
        TextView b=text(getString(label),15,Color.WHITE); b.setFocusable(true); b.setClickable(true); b.setGravity(Gravity.CENTER);
        b.setPadding(dp(14),dp(10),dp(14),dp(10));
        StateListDrawable bg=new StateListDrawable();
        bg.addState(new int[]{android.R.attr.state_focused},shape(Color.rgb(30,104,179)));
        bg.addState(new int[]{android.R.attr.state_selected},shape(Color.rgb(41,68,93)));
        bg.addState(new int[]{},shape(Color.rgb(38,46,56))); b.setBackground(bg);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-2,-2); lp.setMargins(0,0,dp(8),dp(6)); b.setLayoutParams(lp);
        b.setOnClickListener(v->action.run()); return b;
    }
    private TextView card(int title,int detail) {
        LinearLayout box=column(); box.setPadding(dp(14),dp(10),dp(14),dp(10)); box.setBackground(shape(Color.rgb(29,36,45)));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2); lp.bottomMargin=dp(8); content.addView(box,lp);
        TextView h=text(getString(title),18,Color.WHITE); h.setTypeface(null,Typeface.BOLD); box.addView(h);
        TextView status=text("",15,Color.rgb(150,205,245)); box.addView(status);
        box.addView(text(getString(detail),13,Color.LTGRAY)); return status;
    }
    private void show(int index) {
        tab=index; content.removeAllViews(); refreshers.clear();
        for(int i=0;i<3;i++) tabs[i].setSelected(i==index);
        if(index==0) {
            TextView saver=card(R.string.clean_saver,R.string.clean_saver_detail);
            TextView boot=card(R.string.clean_boot,R.string.clean_boot_detail);
            TextView home=card(R.string.clean_home,R.string.clean_mode_hint);
            TextView push=card(R.string.clean_push,R.string.clean_push_detail); push.setText(R.string.clean_untested);
            TextView disable=button(R.string.clean_disable,()->confirm("disable_saver")); content.addView(disable);
            refreshers.add(()->{
                Integer state=CleanState.saver(this);
                saver.setText(state==null?R.string.clean_unsupported:CleanState.disabled(state)?R.string.clean_disabled:R.string.clean_available);
                boot.setText("0".equals(CleanState.bootAd(this))?R.string.clean_setting_off:R.string.clean_untested);
                home.setText(!CleanHomeMode.active(this)?R.string.clean_home_setup:CleanHomeMode.stock(this)?R.string.clean_mode_stock:R.string.clean_mode_aerial);
                disable.setEnabled(state!=null&&!CleanState.disabled(state)&&CleanState.connected(this)&&CleanState.pending(this)==null);
                disable.setAlpha(disable.isEnabled()?1f:0.45f);
            });
        } else if(index==1) {
            content.addView(text(getString(R.string.clean_verify_detail),14,Color.LTGRAY));
            String[] keys={"home","wake","hdmi","idle"};
            int[] labels={R.string.clean_test_home,R.string.clean_test_wake,R.string.clean_test_hdmi,R.string.clean_test_idle};
            for(int i=0;i<keys.length;i++) {
                String key=keys[i];
                LinearLayout box=column(); box.setPadding(0,dp(10),0,0); content.addView(box);
                box.addView(text(getString(labels[i]),17,Color.WHITE));
                LinearLayout buttons=row(); box.addView(buttons);
                String[] values={"passed","failed","untested"}; int[] names={R.string.clean_passed,R.string.clean_failed,R.string.clean_untested};
                for(int j=0;j<3;j++) {
                    String value=values[j]; TextView b=button(names[j],()->{CleanState.verify(this,key,value);refresh();}); buttons.addView(b);
                    refreshers.add(()->b.setSelected(value.equals(CleanState.verification(this,key))));
                }
            }
        } else {
            TextView status=card(R.string.clean_restore_title,R.string.clean_restore_detail);
            TextView restore=button(R.string.clean_restore,()->confirm("restore")); content.addView(restore);
            content.addView(text(getString(R.string.clean_helper_detail),15,Color.LTGRAY));
            TextView attribution=text(getString(R.string.clean_attribution),13,Color.LTGRAY); attribution.setPadding(0,dp(18),0,0); content.addView(attribution);
            refreshers.add(()->{
                status.setText(CleanState.canRestore(this)?R.string.clean_restore_available:R.string.clean_no_changes);
                restore.setEnabled(CleanState.connected(this)&&CleanState.canRestore(this)&&CleanState.pending(this)==null);
                restore.setAlpha(restore.isEnabled()?1f:0.45f);
            });
        }
        refresh();
    }
    private void refresh() {
        for(Runnable r:refreshers) r.run();
        String state=getString(CleanState.connected(this)?R.string.clean_connected:R.string.clean_disconnected);
        if(CleanState.pending(this)!=null) state=getString(R.string.clean_pending);
        String result=CleanState.prefs(this).getString("result","");
        int label;
        switch(result) {
            case "applied":label=R.string.clean_applied;break; case "restored":label=R.string.clean_restored;break;
            case "unchanged":label=R.string.clean_unchanged;break; case "conflict":label=R.string.clean_conflict;break;
            case "expired":label=R.string.clean_expired;break; case "failed":label=R.string.clean_action_failed;break;
            default:label=0;
        }
        footer.setText(state+(label==0?"":" · "+getString(label))+"\n"+getString(R.string.clean_checked_at,DateFormat.getTimeInstance().format(new Date())));
    }
    private void confirm(String action) {
        new AlertDialog.Builder(this).setTitle(R.string.clean_title)
                .setMessage(action.equals("restore")?R.string.clean_confirm_restore:R.string.clean_confirm_disable)
                .setPositiveButton(R.string.clean_confirm,(d,w)->{
                    try { if(!CleanState.request(this,action)) throw new IllegalStateException(); }
                    catch(Exception e){Toast.makeText(this,R.string.clean_action_failed,Toast.LENGTH_LONG).show();}
                    refresh();
                }).setNegativeButton(R.string.clean_cancel,null).show();
    }
}
