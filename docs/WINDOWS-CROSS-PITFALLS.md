# Windows-Cross-Build — die Fallen und warum sie zu sind

Jeder Fehler hier sieht gleich aus: `Checking for SDL... no`, `Error 1` oder `expected int or
identifier, got -`. Die Ursache ist jedes Mal eine andere. Diese Datei ist die Reihenfolge, in der
man sie abarbeitet, damit niemand sie neu suchen muss.

## 1. Zuerst das Log behalten

`configure` und `make` schreiben ihre vollständige Ausgabe nach
`scummvm/fork/build-windows/configure.log` und `build-windows/make.log`. Ein `| tail -5` im Skript
verschluckt genau die Zeile, die den Grund nennt — bei fünf verschiedenen Fehlern war das der
Fall.

Der eigentliche Grund steht fast immer in **`config.log`**, nicht in `configure.log`. Dort ist der
Test-Compile mit Compiler-Aufruf und Fehlerausgabe protokolliert; `configure.log` sagt nur „no".

## 2. Prüfen, welcher Compiler läuft

Steht im `config.log` ein `g++` ohne `x86_64-w64-mingw32-`-Präfix, war es der Host-Compiler.
Symptom: `unrecognized command-line option '-mwindows'`. `configure` wählt den Cross-Compiler nicht
zuverlässig selbst, deshalb setzt `_build-scummvm-windows.sh` `CC` und `CXX` explizit.

## 3. SDL2 liegt NICHT im mingw-prefix

Es baut nach `build/install/sdl2-mingw`. Alle vier Stellen müssen stimmen:

- `PKG_CONFIG_PATH` (sonst „Checking for SDL... no")
- `CPPFLAGS` mit `-I…/include/SDL2` (sonst scheitert der Test-Compile)
- `LDFLAGS` mit `-L…/lib` (sonst scheitert der Test-Link)
- `--with-sdl-prefix` in den Configure-Argumenten

## 4. pkg-config für Cross-Builds

`configure` benennt das Werkzeug um: bei einem Host ungleich Build-Host sucht es
`x86_64-w64-mingw32-pkg-config` (Zeile ~3973). Das gibt es nicht, Ergebnis: `pkg-config... no` und
danach `SDL... no`. Lösung: ein Wrapper im Shim-Verzeichnis

```sh
#!/bin/sh
exec pkg-config "$@"
```

plus `PKG_CONFIG_LIBDIR` auf die beiden Prefixe, damit pkg-config nicht in die Host-Bibliotheken
greift.

## 5. Zeilenenden

`Makefile.common` und `dists/scummvm.rc` hatten CRLF. GNU make unter Linux verzeiht das, macOS und
MSYS2 nicht:

- `Makefile.common`: die Fortsetzung `\` + CR bricht die `sed`-Zeile ab
  (`unterminated 's' command`)
- `dists/scummvm.rc`: `llvm-rc` meldet `expected int or identifier, got -`

`.gitattributes` hält `.rc`, `.rh`, `.manifest`, `.sh` auf LF und `.bat` auf CRLF.

## 6. `sed`-Regeln nicht mit `-` entschärfen

`-$(QUIET)sed …` ruft auf manchen Hosts ein Programm namens `-sed` auf (Error 127), weil der
Fehler-Ignorier-Strich vor der Variablen expansionsteht. Tragfähig ist `{ … ; } || :`.

Der Trenner `:` in `s:…:…:` kollidiert außerdem mit dem Doppelpunkt in `[[:space:]]`. `|` als
Trenner funktioniert überall.

## 7. Nicht-ASCII im VERSIONINFO-Block

`llvm-rc` verweigert `\xA9` in einem Nicht-Unicode-String:

```
Non-ASCII 8-bit codepoint (169) can't occur in a non-Unicode string
```

Deshalb steht dort `Copyright (C)` statt `Copyright ©`.

## 8. macOS: falscher Preprocessor für Ressourcen

`llvm-windres` nimmt auf macOS Apples `/usr/bin/clang`, der für Darwin vorverarbeitet. `llvm-rc`
kann die Ausgabe nicht lesen (`expected int or identifier, got -`). Der Preprocessor muss deshalb
explizit auf den MinGW-clang zeigen:

```sh
make WINDRES="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-windres \
  --preprocessor=$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc --preprocessor-arg=-E"
```

Als **Make-Variable**, nicht als Umgebungsvariable: `config.mk` schreibt
`WINDRES := x86_64-w64-mingw32-windres` und überschreibt eine exportierte Variable.

## 9. Der Weg über den fertigen Stand

`config.log` und `make.log` liegen nach einem Lauf im Klon. Wer einen neuen Fehler sieht: erst
`config.log` nach dem letzten Test-Compile lesen, dann `make.log` nach der Zeile vor `Error 1`.
Alles andere ist Raten.
