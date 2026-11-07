#!/usr/bin/env python3
"""
把印尼版计算器打包成可离线使用的安卓 APK（不用 Gradle，也不需要联网）。

做的事：
  1. 把 indonesia.html 变成单文件：内嵌 Excel 模板，去掉在线字体（用手机系统字体）
  2. 加一小段脚本，把“复制摘要”“下载 Excel”和手机的字体大小接到安卓系统（android/MainActivity.java 的 Bridge）
  3. 用 SDK 的 aapt2、javac、d8、zipalign、apksigner 打包并签名

准备：JDK 17+，Android SDK（platforms;android-35 和 build-tools;35.0.0），并先运行 scripts/build_xlsx.py
运行（在仓库根目录）：
  JAVA_HOME=... ANDROID_HOME=... python3 scripts/build_apk.py
输出：
  dist/hemat-listrik-kincir.apk

签名用标准调试密钥 ~/.android/debug.keystore，没有就自动创建。
以后更新要用同一把密钥，否则手机要先卸载旧版，页面里保存的数字也会丢。正式分发前要换成发布密钥。
"""
import base64
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_artifact import XLSX, XLSX_SLOT, inline_assets  # noqa: E402

ROOT =Path(__file__).resolve().parent.parent
ANDROID = ROOT / "android"
OUT = ROOT / "dist" / "hemat-listrik-kincir.apk"
PLATFORM, BUILD_TOOLS = "android-35", "35.0.0"
MIN_API = "26"
KEYSTORE = Path.home() / ".android" / "debug.keystore"

BRIDGE = """<script>
(function(){
  // The phone's large-text setting scales the whole page evenly; beyond 130% the layout stops making sense.
  document.documentElement.style.fontSize=(16*Math.max(0.9,Math.min(1.3,HematAndroid.fontScale())))+"px";
  window.claude={use:function(n){return Promise.resolve(n==="downloads"?{save:function(r){
    var d=r.data,b="";for(var i=0;i<d.length;i++)b+=String.fromCharCode(d[i]);
    return HematAndroid.save(r.filename,btoa(b))?Promise.resolve({status:"saved"}):Promise.reject({code:"unavailable"});
  }}:null);}};
  Object.defineProperty(navigator,"clipboard",{value:{writeText:function(t){HematAndroid.copy(t);return Promise.resolve();}}});
})();
</script>
"""


def page() -> str:
    html = (ROOT / "indonesia.html").read_text(encoding="utf-8")
    html = re.sub(r'\s*<link [^>]*fonts\.(googleapis|gstatic)\.com[^>]*>', "", html)
    html = inline_assets(html)
    if not XLSX.exists():
        raise SystemExit("缺少 Excel 模板，请先运行 python3 scripts/build_xlsx.py")
    html = html.replace(XLSX_SLOT, base64.b64encode(XLSX.read_bytes()).decode())
    if "assets/" in html.split("<script>")[0] or "<script>" not in html:
        raise SystemExit("页面没有打包完整，请检查 indonesia.html")
    return html.replace("<script>", BRIDGE + "<script>", 1)


def run(*cmd, env=None):
    subprocess.run([str(c) for c in cmd], check=True, env=env)


def main():
    java_home, sdk = os.environ.get("JAVA_HOME"), os.environ.get("ANDROID_HOME")
    if not java_home or not sdk:
        raise SystemExit("请设置 JAVA_HOME 和 ANDROID_HOME")
    env = dict(os.environ, PATH=f"{java_home}/bin:{os.environ['PATH']}")
    tools = Path(sdk) / "build-tools" / BUILD_TOOLS
    android_jar = Path(sdk) / "platforms" / PLATFORM / "android.jar"

    if not KEYSTORE.exists():
        KEYSTORE.parent.mkdir(exist_ok=True)
        run(f"{java_home}/bin/keytool", "-genkeypair", "-keystore", KEYSTORE, "-storepass", "android", "-keypass", "android",
            "-alias", "androiddebugkey", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-dname", "CN=Android Debug,O=Android,C=US")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        assets = tmp / "assets"
        classes = tmp / "classes"
        assets.mkdir()
        classes.mkdir()
        (assets / "index.html").write_text(page(), encoding="utf-8")

        run(tools / "aapt2", "compile", "--dir", ANDROID / "res", "-o", tmp / "res.zip")
        run(tools / "aapt2", "link", "-I", android_jar, "--manifest", ANDROID / "AndroidManifest.xml",
            "-A", assets, "-o", tmp / "base.apk", tmp / "res.zip")

        run(f"{java_home}/bin/javac", "-source", "8", "-target", "8", "-nowarn", "-Xlint:-options", "-classpath", android_jar,
            "-d", classes, ANDROID / "MainActivity.java", env=env)
        run(tools / "d8", "--release", "--lib", android_jar, "--min-api", MIN_API, "--output", tmp,
            *sorted(classes.rglob("*.class")), env=env)

        with zipfile.ZipFile(tmp / "base.apk", "a", zipfile.ZIP_DEFLATED) as apk:
            apk.write(tmp / "classes.dex", "classes.dex")

        run(tools / "zipalign", "-f", "-p", "4", tmp / "base.apk", tmp / "aligned.apk")
        OUT.parent.mkdir(exist_ok=True)
        run(tools / "apksigner", "sign", "--ks", KEYSTORE, "--ks-pass", "pass:android", "--key-pass", "pass:android",
            "--out", OUT, tmp / "aligned.apk", env=env)
    idsig = OUT.with_name(OUT.name + ".idsig")
    if idsig.exists():
        idsig.unlink()
    print(f"OK -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
