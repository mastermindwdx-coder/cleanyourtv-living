package org.cleantv.companion;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.ComponentName;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaDrm;
import android.net.*;
import android.os.Build;
import android.view.View;
import android.widget.*;
import javax.net.ssl.HttpsURLConnection;
import java.net.URL;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Independent media/network companion. No desktop bridge or account connection. */
public class MainActivity extends Activity {
    private static final String CLASH="com.github.metacubex.clash.meta";
    private static final String SMART="org.smarttube.stable";
    private static final String SMART_LOCAL="org.cleantv.smarttube";
    private final ExecutorService io=Executors.newFixedThreadPool(2);
    private LinearLayout root,body;
    private TextView notice;
    private String page="home";
    private final int ink=Color.rgb(236,245,239),muted=Color.rgb(157,181,171),green=Color.rgb(166,229,202);

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        // Remove only this app's retired desktop-bridge state; other apps are untouched.
        boolean cleared=getSharedPreferences("personal",MODE_PRIVATE).edit().clear().commit();
        try{java.security.KeyStore ks=java.security.KeyStore.getInstance("AndroidKeyStore");ks.load(null);if(ks.containsAlias("tv-pairing"))ks.deleteEntry("tv-pairing");android.util.Log.i("TVCompanion","LegacyPairingRemoved prefs="+cleared+" key="+!ks.containsAlias("tv-pairing"));}catch(Exception e){android.util.Log.w("TVCompanion","Retired pairing key cleanup unavailable");}
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        String target=getIntent().getStringExtra("page");show(target==null?"home":target);
    }
    @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);String target=i.getStringExtra("page");show(target==null?"home":target);}
    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}
    @Override public void onBackPressed(){if(!page.equals("home"))show("home");else super.onBackPressed();}
    private int dp(float x){return Math.round(x*getResources().getDisplayMetrics().density);}
    private TextView text(String s,int size,int color){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(6),0,dp(6));return t;}
    private GradientDrawable bg(int c,int stroke){GradientDrawable g=new GradientDrawable();g.setColor(c);g.setCornerRadius(dp(10));if(stroke!=0)g.setStroke(dp(2),stroke);return g;}
    private Button button(String s,Runnable run){
        Button b=new Button(this);b.setText(s);b.setTextSize(17);b.setTextColor(ink);b.setAllCaps(false);b.setMinHeight(dp(48));b.setPadding(dp(16),dp(6),dp(16),dp(6));
        b.setBackground(bg(Color.rgb(32,58,48),0));b.setOnFocusChangeListener((v,f)->{b.setBackground(bg(f?Color.rgb(62,93,76):Color.rgb(32,58,48),f?green:0));});
        b.setOnClickListener(v->run.run());LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(52));lp.setMargins(0,dp(5),0,dp(5));b.setLayoutParams(lp);return b;
    }
    private void rowButtons(LinearLayout parent,String[] labels,Runnable[] acts){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);parent.addView(row);for(int i=0;i<labels.length;i++){Button b=button(labels[i],acts[i]);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(50),1);lp.setMargins(0,dp(4),dp(10),dp(4));row.addView(b,lp);}}
    private void show(String target){
        page=(target.equals("network")||target.equals("device"))?target:"home";root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(38),dp(20),dp(38),dp(20));root.setBackgroundColor(Color.rgb(13,26,22));setContentView(root);
        TextView title=text("电视扩展",30,ink);title.setTypeface(null,Typeface.BOLD);root.addView(title);
        root.addView(text("影音 · 个人网络     /     实验版 0.1.3",13,muted));
        rowButtons(root,new String[]{"首页","网络","设备检测"},new Runnable[]{()->show("home"),()->show("network"),()->show("device")});
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(0,dp(14),0,dp(18));scroll.addView(body);
        notice=text("",14,green);body.addView(notice);
        if(page.equals("network"))network();else if(page.equals("device"))device();else home();
    }
    private void home(){
        body.addView(text("把应用与工具放在一起",24,ink));
        body.addView(text("所有账号和网络配置由你自己管理。按 Home 可返回原有桌面。",16,muted));
        rowButtons(body,new String[]{"SmartTube 中文版","Netflix"},new Runnable[]{()->launch(installed(SMART_LOCAL)?SMART_LOCAL:SMART),()->launch("com.netflix.ninja")});
        body.addView(button("个人网络设置",()->show("network")));
        body.addView(text("Netflix："+(installed("com.netflix.ninja")?"已安装，播放能力需在应用中核对":"尚未安装，设备认证与兼容性待核对"),16,muted));
    }
    private boolean installed(String pkg){try{getPackageManager().getPackageInfo(pkg,0);return true;}catch(Exception e){return false;}}
    private void launch(String pkg){Intent i=getPackageManager().getLeanbackLaunchIntentForPackage(pkg);if(i==null)i=getPackageManager().getLaunchIntentForPackage(pkg);if(i==null){notice.setText("应用尚未安装或没有可用入口："+pkg);return;}try{startActivity(i);}catch(Exception e){notice.setText("当前设备无法打开该应用");}}
    private String netStatus(){ConnectivityManager cm=(ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);Network n=cm.getActiveNetwork();NetworkCapabilities c=cm.getNetworkCapabilities(n);if(c==null)return "没有活动网络";return "网络已连接 · "+(c.hasTransport(NetworkCapabilities.TRANSPORT_VPN)?"VPN 已启用":"未检测到活动 VPN")+"\nVPN 状态不代表影音网站已经可播放。";}
    private void network(){
        body.addView(text("个人网络",25,ink));body.addView(text(netStatus(),17,green));
        body.addView(text("沿用个人 Clash / Mihomo 配置。订阅、节点与账号只保存在你的设备，未内置在安装包中。",16,muted));
        rowButtons(body,new String[]{"打开 Clash Meta","连接","断开"},new Runnable[]{()->launch(CLASH),()->controlNetwork("START_CLASH"),()->controlNetwork("STOP_CLASH")});
        body.addView(button("刷新连接状态",()->show("network")));
        body.addView(button("检测 YouTube / Netflix 连通性",this::checkSites));
        body.addView(text("网络配置需保留局域网直连；应用分流与唤醒重连应在网络客户端中设置和验证。",15,muted));
    }
    private void controlNetwork(String action){if(!installed(CLASH)){notice.setText("请先安装并配置 Clash Meta for Android");return;}try{Intent i=new Intent(CLASH+".action."+action);i.setComponent(new ComponentName(CLASH,"com.github.kr328.clash.ExternalControlActivity"));startActivity(i);}catch(Exception e){notice.setText("客户端不支持此控制入口，请打开客户端操作");}}
    private void checkSites(){notice.setText("正在检测 HTTPS 连接…");io.execute(()->{StringBuilder b=new StringBuilder();for(String host:new String[]{"www.youtube.com","www.netflix.com"}){HttpsURLConnection c=null;try{c=(HttpsURLConnection)new URL("https://"+host+"/").openConnection();c.setConnectTimeout(8000);c.setReadTimeout(8000);c.setRequestMethod("HEAD");int code=c.getResponseCode();b.append(host).append("：HTTP ").append(code).append("\n");}catch(Exception e){b.append(host).append("：未连通\n");}finally{if(c!=null)c.disconnect();}}b.append("此检测仅验证网络响应，不代表登录、片库或播放授权通过。");runOnUiThread(()->notice.setText(b.toString()));});}
    private void device(){
        body.addView(text("设备兼容性",25,ink));StringBuilder s=new StringBuilder("系统：Android "+Build.VERSION.RELEASE+"\n应用架构："+String.join(", ",Build.SUPPORTED_ABIS)+"\n");
        try(MediaDrm drm=new MediaDrm(UUID.fromString("edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"))){s.append("Widevine：").append(drm.getPropertyString("securityLevel")).append("\n");}catch(Exception e){s.append("Widevine：未能读取\n");}
        s.append("YouTube 官方版：").append(installed("com.google.android.youtube.tv")?"已安装":"未安装").append("\nSmartTube 中文版：").append(installed(SMART_LOCAL)?"已安装":"未安装").append("\nSmartTube 原版：").append(installed(SMART)?"已安装":"未安装").append("\nNetflix：").append(installed("com.netflix.ninja")?"已安装":"未安装").append("\nClash Meta：").append(installed(CLASH)?"已安装":"未安装");
        body.addView(text(s.toString(),18,ink));body.addView(text("DRM 等级与安装状态都不等于 Netflix 认证或实际 4K 播放通过。不会读取设备唯一 DRM 标识。",16,muted));
    }
}
