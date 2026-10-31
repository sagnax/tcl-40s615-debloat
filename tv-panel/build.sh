#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PANEL_SDK="${ANDROID_SDK_ROOT:-$PWD/../.tools/android-sdk}"
PANEL_BT="${PANEL_BUILD_TOOLS:-$PANEL_SDK/build-tools/35.0.0}"
PANEL_JAR="${PANEL_ANDROID_JAR:-$PANEL_SDK/platforms/android-30/android.jar}"
# Layout dos ZIPs oficiais quando extraídos diretamente, sem sdkmanager.
if [ -z "${PANEL_BUILD_TOOLS:-}" ] && [ ! -d "$PANEL_BT" ]; then
    PANEL_BT="$PANEL_SDK/build-tools/android-15"
fi
if [ -z "${PANEL_ANDROID_JAR:-}" ] && [ ! -f "$PANEL_JAR" ]; then
    PANEL_JAR="$PANEL_SDK/platforms/android-11/android.jar"
fi
if [ ! -x "$PANEL_BT/aapt2" ] || [ ! -f "$PANEL_JAR" ]; then
    echo 'SDK não encontrado. Defina ANDROID_SDK_ROOT com Platform 30 e Build Tools 35.0.0.' >&2
    exit 1
fi
for tool in java javac keytool jar python3; do command -v "$tool" >/dev/null; done
python3 - <<'PY_CLEAN'
from pathlib import Path
import shutil
for name in ("classes", "dex", "generated"):
    folder = Path("build") / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
PY_CLEAN
"$PANEL_BT/aapt2" compile --dir res -o build/resources.zip
"$PANEL_BT/aapt2" link -o build/base.apk -I "$PANEL_JAR" --manifest AndroidManifest.xml --java build/generated build/resources.zip
find src build/generated -name '*.java' -print > build/sources.txt
javac --release 8 -encoding UTF-8 -classpath "$PANEL_JAR" -d build/classes @build/sources.txt
jar cf build/classes.jar -C build/classes .
"$PANEL_BT/d8" --lib "$PANEL_JAR" --min-api 26 --output build/dex build/classes.jar
python3 - <<'PY'
from zipfile import ZipFile,ZIP_DEFLATED
from pathlib import Path
with ZipFile('build/base.apk') as base, ZipFile('build/unsigned.apk','w',ZIP_DEFLATED) as apk:
    for item in base.infolist():
        apk.writestr(item,base.read(item.filename))
    for dex in Path('build/dex').glob('*.dex'):
        apk.write(dex,dex.name)
PY
"$PANEL_BT/zipalign" -f 4 build/unsigned.apk build/aligned.apk
# Local development key. Keep it to allow future updates to this installation.
if [ ! -f build/panel-dev.jks ]; then
    keytool -genkeypair -keystore build/panel-dev.jks -storepass android -keypass android -alias panel -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Painel da TV Local' >/dev/null 2>&1
fi
"$PANEL_BT/apksigner" sign --ks build/panel-dev.jks --ks-pass pass:android --out build/painel-tv.apk build/aligned.apk
"$PANEL_BT/apksigner" verify build/painel-tv.apk
ls -lh build/painel-tv.apk
