#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/tests
javac --release 8 -encoding UTF-8 -d build/tests src/br/com/tcl/painel/Snapshot.java src/br/com/tcl/painel/StopPolicy.java src/br/com/tcl/painel/LocalAdb.java tests/br/com/tcl/painel/PanelTests.java tests/br/com/tcl/painel/AdbTests.java
java -cp build/tests br.com.tcl.painel.PanelTests
java -cp build/tests br.com.tcl.painel.AdbTests
