import json,os,re,zipfile,shutil
cfg=json.load(open('config.json')); T=cfg.get('type','kotlin'); PKG=cfg['pkg']; NAME=cfg['name']
if not os.path.exists('project.zip') and os.path.isdir('parts'):
    with open('project.zip','wb') as o:
        for f in sorted(os.listdir('parts')):
            with open('parts/'+f,'rb') as i: shutil.copyfileobj(i,o)
    shutil.rmtree('parts')
zipfile.ZipFile('project.zip').extractall('proj')
root='proj'
while True:
    it=[i for i in os.listdir(root) if i!='__MACOSX']
    if len(it)==1 and os.path.isdir(os.path.join(root,it[0])): root=os.path.join(root,it[0])
    else: break
has_icon=os.path.exists('icons.zip')
def wr(p,s):
    os.makedirs(os.path.dirname(p) or '.',exist_ok=True); open(p,'w',encoding='utf-8').write(s)
def esc(s): return s.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;')
def done(r): wr('rootdir',r); print('type=',T,'root=',r)

FS_JAVA = """package com.ktfs;
import android.app.*;import android.content.*;import android.content.pm.ActivityInfo;import android.database.Cursor;import android.net.Uri;import android.os.*;import android.view.*;
public class FsInit extends ContentProvider {
  static final Handler H = new Handler(Looper.getMainLooper());
  public boolean onCreate() {
    Application a = (Application) getContext().getApplicationContext();
    a.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
      public void onActivityCreated(Activity x, Bundle b) { go(x); }
      public void onActivityResumed(Activity x) { go(x); }
      public void onActivityStarted(Activity x) {}
      public void onActivityPaused(Activity x) {}
      public void onActivityStopped(Activity x) {}
      public void onActivitySaveInstanceState(Activity x, Bundle b) {}
      public void onActivityDestroyed(Activity x) {}
    });
    return true;
  }
  static void go(final Activity x) {
    try {
      x.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
      final Window w = x.getWindow();
      w.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
      if (Build.VERSION.SDK_INT >= 28) {
        WindowManager.LayoutParams p = w.getAttributes();
        p.layoutInDisplayCutoutMode = Build.VERSION.SDK_INT >= 30 ? 3 : 1;
        w.setAttributes(p);
      }
      w.setStatusBarColor(0); w.setNavigationBarColor(0);
      View d = w.getDecorView();
      d.setSystemUiVisibility(0x1706);
      d.setOnSystemUiVisibilityChangeListener(new View.OnSystemUiVisibilityChangeListener() {
        public void onSystemUiVisibilityChange(int v) { H.postDelayed(new Runnable() { public void run() { go(x); } }, 400); }
      });
      if (Build.VERSION.SDK_INT >= 30) {
        w.setDecorFitsSystemWindows(false);
        WindowInsetsController c = w.getInsetsController();
        if (c != null) { c.hide(WindowInsets.Type.systemBars()); c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE); }
      }
    } catch (Throwable t) {}
  }
  public Cursor query(Uri u, String[] a, String b, String[] c, String d) { return null; }
  public String getType(Uri u) { return null; }
  public Uri insert(Uri u, ContentValues v) { return null; }
  public int delete(Uri u, String a, String[] b) { return 0; }
  public int update(Uri u, ContentValues v, String a, String[] b) { return 0; }
}
"""

def fs(mp, jroot):
    """Force landscape + immersive fullscreen + cutout for any Android project."""
    wr(os.path.join(jroot,'com/ktfs/FsInit.java'), FS_JAVA)
    m=open(mp,encoding='utf-8').read()
    def act(mo):
        t=re.sub(r'\sandroid:screenOrientation="[^"]*"','',mo.group(0))
        return t.replace('<activity','<activity android:screenOrientation="sensorLandscape"',1)
    m=re.sub(r'<activity\b[^>]*>',act,m,flags=re.S)
    m=re.sub(r'<activity\b[^>]*?(/?)>',lambda mo:mo.group(0),m,flags=re.S)
    prov='<provider android:name="com.ktfs.FsInit" android:authorities="%s.ktfs" android:exported="false" android:initOrder="1000"/>'%PKG
    if 'com.ktfs.FsInit' not in m: m=m.replace('</application>',prov+'\n</application>',1)
    open(mp,'w',encoding='utf-8').write(m)

def setkey(txt,sec,key,val):
    line='%s=%s'%(key,val)
    mo=re.search(r'^\[%s\]\s*$'%re.escape(sec),txt,re.M)
    if not mo: return txt.rstrip('\n')+'\n\n[%s]\n\n%s\n'%(sec,line)
    end=re.search(r'^\[',txt[mo.end():],re.M); e=mo.end()+(end.start() if end else len(txt)-mo.end())
    body=txt[mo.end():e]
    if re.search(r'^%s='%re.escape(key),body,re.M): body=re.sub(r'^%s=.*$'%re.escape(key),line,body,flags=re.M)
    else: body='\n'+line+body
    return txt[:mo.end()]+body+txt[e:]

def gfs(best):
    pg=os.path.join(best,'project.godot'); t=open(pg,encoding='utf-8').read()
    t=setkey(t,'display','window/handheld/orientation','4')
    t=setkey(t,'display','window/size/mode','3')
    open(pg,'w',encoding='utf-8').write(t)
    pc=os.path.join(best,'export_presets.cfg'); c=open(pc,encoding='utf-8').read()
    if 'screen/immersive_mode=' in c: c=c.replace('screen/immersive_mode=false','screen/immersive_mode=true')
    else: c=re.sub(r'(\[preset\.\d+\.options\]\s*\n)',lambda mo:mo.group(1)+'screen/immersive_mode=true\n',c)
    open(pc,'w',encoding='utf-8').write(c)


def kotlin():
    app=None
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d not in('build','.gradle')]
        for f in fn:
            if f in('build.gradle','build.gradle.kts'):
                t=open(os.path.join(dp,f),errors='ignore').read()
                if 'com.android.application' in t and re.search(r'\bandroid\s*\{',t):
                    app=(dp,os.path.join(dp,f),t); break
        if app: break
    if not app: raise SystemExit('Android app module not found')
    dp,g,t=app
    pat=r'applicationId\s*=?\s*["\'][^"\']*["\']'
    new='applicationId = "%s"'%PKG
    if re.search(pat,t): t=re.sub(pat,lambda m:new,t)
    else: t=re.sub(r'defaultConfig\s*\{',lambda m:'defaultConfig {\n '+new,t,1)
    open(g,'w').write(t)
    mp=os.path.join(dp,'src/main/AndroidManifest.xml')
    m=open(mp,encoding='utf-8').read()
    def fix(mo):
        tag=mo.group(0)
        rm='label|icon|roundIcon' if has_icon else 'label'
        tag=re.sub(r'\sandroid:(%s)="[^"]*"'%rm,'',tag)
        add=' android:label="%s"'%esc(NAME)+(' android:icon="@mipmap/ic_launcher"' if has_icon else '')
        return tag.replace('<application','<application'+add,1)
    m=re.sub(r'<application[^>]*>',fix,m,1,flags=re.S)
    open(mp,'w',encoding='utf-8').write(m)
    if has_icon:
        res=os.path.join(dp,'src/main/res')
        if os.path.isdir(res):
            for d in os.listdir(res):
                if d.startswith('mipmap'):
                    for f in os.listdir(os.path.join(res,d)):
                        if f.startswith('ic_launcher'): os.remove(os.path.join(res,d,f))
        zipfile.ZipFile('icons.zip').extractall(res)
    fs(mp,os.path.join(dp,'src/main/java'))
    done(root)

def gen(kind):
    g='gen'; native=(kind=='cpp')
    wr(g+'/settings.gradle',"pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositories { google(); mavenCentral() } }\nrootProject.name = 'app'\ninclude ':app'\n")
    wr(g+'/build.gradle',"plugins { id 'com.android.application' version '8.3.2' apply false }\n")
    wr(g+'/gradle.properties',"android.useAndroidX=true\norg.gradle.jvmargs=-Xmx3g\n")
    ext1="\n    externalNativeBuild { cmake { cppFlags '-std=c++17' } }\n    ndk { abiFilters 'arm64-v8a','armeabi-v7a' }" if native else ""
    ext2="\n  externalNativeBuild { cmake { path 'src/main/cpp/CMakeLists.txt' } }" if native else ""
    wr(g+'/app/build.gradle',"plugins { id 'com.android.application' }\nandroid {\n  namespace '%s'\n  compileSdk 34\n  defaultConfig { applicationId '%s'; minSdk 24; targetSdk 34; versionCode 1; versionName '1.0'%s }%s\n  compileOptions { sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }\n}\n"%(PKG,PKG,ext1,ext2))
    icon=' android:icon="@mipmap/ic_launcher"' if has_icon else ''
    wr(g+'/app/src/main/AndroidManifest.xml','<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n<uses-permission android:name="android.permission.INTERNET"/>\n<application android:label="%s"%s android:theme="@android:style/Theme.Material.Light.NoActionBar" android:usesCleartextTraffic="true">\n<activity android:name=".MainActivity" android:exported="true" android:configChanges="orientation|screenSize|keyboardHidden"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>\n</application></manifest>\n'%(esc(NAME),icon))
    if has_icon:
        zipfile.ZipFile('icons.zip').extractall(g+'/app/src/main/res')
    jd=g+'/app/src/main/java/'+PKG.replace('.','/')
    if kind=='html':
        best=None
        for dp,dn,fn in os.walk(root):
            if any(f.lower()=='index.html' for f in fn) and (best is None or len(dp)<len(best)): best=dp
        extra=None
        if best is None:
            for dp,dn,fn in os.walk(root):
                h=[f for f in fn if f.lower().endswith(('.html','.htm'))]
                if h: best=dp; extra=h[0]; break
        if best is None: raise SystemExit('HTML files not found in project')
        shutil.copytree(best,g+'/app/src/main/assets')
        if extra: shutil.copy(os.path.join(best,extra),g+'/app/src/main/assets/index.html')
        wr(jd+'/MainActivity.java','package %s;\nimport android.app.Activity;import android.os.Bundle;import android.webkit.*;\npublic class MainActivity extends Activity{\n WebView w;\n protected void onCreate(Bundle b){super.onCreate(b);w=new WebView(this);WebSettings s=w.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(true);s.setMediaPlaybackRequiresUserGesture(false);w.setWebViewClient(new WebViewClient());w.setWebChromeClient(new WebChromeClient());setContentView(w);w.loadUrl("file:///android_asset/index.html");}\n @Override public void onBackPressed(){if(w.canGoBack())w.goBack();else super.onBackPressed();}\n}\n'%PKG)
    else:
        n=0
        for dp,dn,fn in os.walk(root):
            for f in fn:
                if f.lower().endswith(('.cpp','.cc','.cxx','.h','.hpp','.hh','.inc')):
                    rel=os.path.relpath(os.path.join(dp,f),root); d=g+'/app/src/main/cpp/user/'+rel
                    os.makedirs(os.path.dirname(d),exist_ok=True); shutil.copy(os.path.join(dp,f),d)
                    if f.lower().endswith(('.cpp','.cc','.cxx')): n+=1
        if n==0: raise SystemExit('No .cpp files found in project')
        cm=g+'/app/src/main/cpp/'
        wr(cm+'CMakeLists.txt','cmake_minimum_required(VERSION 3.18.1)\nproject(native)\nset(CMAKE_CXX_STANDARD 17)\nfile(GLOB_RECURSE USER_SRC ${CMAKE_CURRENT_SOURCE_DIR}/user/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/user/*.cc ${CMAKE_CURRENT_SOURCE_DIR}/user/*.cxx)\nadd_library(native SHARED bridge.cpp ${USER_SRC})\nset_source_files_properties(${USER_SRC} PROPERTIES COMPILE_DEFINITIONS main=user_main)\ntarget_include_directories(native PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/user)\ntarget_link_libraries(native log)\n')
        wr(cm+'bridge.cpp','''#include <jni.h>
#include <unistd.h>
#include <thread>
#include <string>
#include <cstdio>
#include <iostream>
int user_main() __attribute__((weak));
int user_main(int, char**) __attribute__((weak));
static jbyteArray run(JNIEnv* e, jobject) {
  int p[2]; pipe(p); int so = dup(1), se = dup(2);
  dup2(p[1], 1); dup2(p[1], 2); close(p[1]);
  std::string out;
  std::thread rd([&]{ char b[4096]; ssize_t n; while ((n = read(p[0], b, sizeof b)) > 0) out.append(b, n); });
  int rc = 0;
  int (*f2)(int, char**) = user_main;
  int (*f0)() = user_main;
  char a0[] = "app"; char* av[] = {a0, nullptr};
  if (f2) rc = f2(1, av); else if (f0) rc = f0();
  fflush(nullptr); std::cout.flush(); std::cerr.flush();
  dup2(so, 1); dup2(se, 2); close(so); close(se);
  rd.join(); close(p[0]);
  out += "\\n[exit " + std::to_string(rc) + "]";
  jbyteArray r = e->NewByteArray((jsize)out.size());
  e->SetByteArrayRegion(r, 0, (jsize)out.size(), (const jbyte*)out.data());
  return r;
}
JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void*) {
  JNIEnv* e; if (vm->GetEnv((void**)&e, JNI_VERSION_1_6) != JNI_OK) return -1;
  jclass c = e->FindClass("%s");
  JNINativeMethod m[] = {{"run", "()[B", (void*)run}};
  e->RegisterNatives(c, m, 1);
  return JNI_VERSION_1_6;
}
'''%(PKG.replace('.','/')+'/MainActivity'))
        wr(jd+'/MainActivity.java','package %s;\nimport android.app.Activity;import android.os.Bundle;import android.widget.*;import android.graphics.Typeface;\npublic class MainActivity extends Activity{\n static{System.loadLibrary("native");}\n native byte[] run();\n protected void onCreate(Bundle b){super.onCreate(b);final TextView t=new TextView(this);t.setTypeface(Typeface.MONOSPACE);t.setTextSize(13);t.setPadding(32,64,32,32);t.setTextIsSelectable(true);t.setText("...");ScrollView s=new ScrollView(this);s.addView(t);setContentView(s);\n  new Thread(new Runnable(){public void run(){final String r;String x;try{x=new String(MainActivity.this.run(),"UTF-8");}catch(Throwable e){x="error: "+e;}r=x;runOnUiThread(new Runnable(){public void run(){t.setText(r);}});}}).start();}\n}\n'%PKG)
    fs(g+'/app/src/main/AndroidManifest.xml',g+'/app/src/main/java')
    done(g)

def godot():
    best=None
    for dp,dn,fn in os.walk(root):
        if 'project.godot' in fn and (best is None or len(dp)<len(best)): best=dp
    if not best: raise SystemExit('project.godot not found')
    pc=os.path.join(best,'export_presets.cfg'); pname='Android'
    if os.path.exists(pc) and 'platform="Android"' in open(pc).read():
        txt=open(pc).read()
        m=re.search(r'name="([^"]*)"\s*\nplatform="Android"',txt)
        if m: pname=m.group(1)
    else:
        extra='\n' if os.path.exists(pc) else ''
        old=open(pc).read() if os.path.exists(pc) else ''
        open(pc,'w').write(old+extra+'[preset.99]\n\nname="Android"\nplatform="Android"\nrunnable=true\ndedicated_server=false\ncustom_features=""\nexport_filter="all_resources"\ninclude_filter=""\nexclude_filter=""\nexport_path=""\n\n[preset.99.options]\n\ncustom_template/debug=""\ncustom_template/release=""\ngradle_build/use_gradle_build=false\narchitectures/arm64-v8a=true\narchitectures/armeabi-v7a=false\narchitectures/x86=false\narchitectures/x86_64=false\nversion/code=1\nversion/name="1.0"\npackage/unique_name="%s"\npackage/name="%s"\npackage/signed=true\nscreen/immersive_mode=true\npermissions/internet=true\n'%(PKG,esc(NAME)))
    gfs(best); wr('presetname',pname); done(best)

{'kotlin':kotlin,'html':lambda:gen('html'),'cpp':lambda:gen('cpp'),'godot':godot}[T]()
