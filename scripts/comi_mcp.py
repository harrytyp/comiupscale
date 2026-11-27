#!/usr/bin/env python3
"""MCP-Server fuer COMI: steuert das Spiel ueber den JEV-Kommando-FIFO.

Protokoll: JSON-RPC 2.0 ueber stdin/stdout, ein Objekt pro Zeile (kein Content-Length-Header).
Die Engine liest den FIFO einmal pro Frame, deshalb wird nach jedem Kommando kurz gewartet.

Start des Spiels uebernimmt dieses Skript, damit FIFO und Prozess zusammenpassen.
"""
import json
import os
import subprocess
import sys
import time

RUN_DIR = "/opt/data/projects/comi-hd/work/probe/konform/run"
BINARY = "/opt/data/local/comi-hd-repo/scummvm/fork/build-linux/scummvm"
INI = "/opt/data/local/comi-hd-repo/release/linux/scummvm_video.ini"
FIFO = "/opt/data/tmp/comi_mcp.fifo"

_proc = None
_writer = None


def _log(msg):
    print("[comi-mcp] " + msg, file=sys.stderr, flush=True)


def _tools():
    return [
        {
            "name": "comi_start",
            "description": "Startet das Spiel mit FIFO-Steuerung.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {"type": "integer", "description": "Raum, in dem gestartet wird"},
                    "seconds": {"type": "integer", "description": "Laufzeit bis zum Beenden"},
                },
            },
        },
        {
            "name": "comi_send",
            "description": "Schickt ein Rohkommando an die Engine (click x y, gclick, rclick, inv, close, useobj N, dump).",
            "inputSchema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
        {
            "name": "comi_click",
            "description": "Klickt an Spielkoordinaten.",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                "required": ["x", "y"],
            },
        },
        {
            "name": "comi_replay",
            "description": "Spielt eine aufgezeichnete Befehlsfolge aus scripts/replay/<name>.txt ab.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        {
            "name": "comi_status",
            "description": "Liest die letzten Zeilen des Engine-Logs und den Cursorzustand.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "comi_stop",
            "description": "Beendet das Spiel.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def _send(command, wait=0.6):
    global _writer
    if _writer is None:
        return {"ok": False, "error": "Spiel laeuft nicht (comi_start fehlt)"}
    _writer.write((command + "\n").encode())
    _writer.flush()
    time.sleep(wait)
    return {"ok": True, "sent": command}


def _start(room=87, seconds=300):
    global _proc, _writer
    if _proc and _proc.poll() is None:
        return {"ok": True, "already_running": True, "pid": _proc.pid}
    if os.path.exists(FIFO):
        os.unlink(FIFO)
    os.mkfifo(FIFO)
    env = dict(os.environ)
    env.update(
        {
            "JEV_CMD_FIFO": FIFO,
            "HD_STATE_LOG": "1",
            "HD_CAPTURE_ROOM": str(room),
            "HD_EXIT_AFTER": str(seconds),
        }
    )
    _proc = subprocess.Popen(
        [BINARY, "--config=" + INI, "--path=game", "--boot-param=" + str(room), "comi"],
        cwd=RUN_DIR,
        env=env,
        stdout=open("/opt/data/tmp/comi_mcp_engine.log", "wb"),
        stderr=subprocess.STDOUT,
    )
    _writer = open(FIFO, "wb", buffering=0)
    time.sleep(6)
    return {"ok": True, "pid": _proc.pid, "fifo": FIFO, "log": "/opt/data/tmp/comi_mcp_engine.log"}


def _replay(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay", name + ".txt")
    if not os.path.exists(path):
        return {"ok": False, "error": "keine Aufzeichnung: " + path}
    steps = []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pause, command = parts
        try:
            pause = float(pause)
        except ValueError:
            continue
        steps.append((pause, command))
    done = []
    for pause, command in steps:
        time.sleep(pause)
        if command.startswith("#"):
            continue
        if command == "wait":
            done.append("wait")
            continue
        if command.startswith("shot "):
            done.append("shot " + command[5:])
            continue
        result = _send(command, wait=0)
        done.append(command + (" ok" if result.get("ok") else " fehlt"))
    return {"ok": True, "steps": done}


def _status():
    log = "/opt/data/tmp/comi_mcp_engine.log"
    tail = []
    if os.path.exists(log):
        with open(log, "rb") as f:
            tail = f.read().decode("utf-8", "replace").splitlines()[-5:]
    state = []
    p = os.path.join(RUN_DIR, "hd_state.log")
    if os.path.exists(p):
        with open(p, "rb") as f:
            state = [
                l
                for l in f.read().decode("utf-8", "replace").splitlines()
                if "CURSOR_ITEM" in l or "CURSOR_HD" in l
            ][-5:]
    running = bool(_proc and _proc.poll() is None)
    return {"ok": True, "running": running, "engine_log": tail, "cursor": state}


def _stop():
    global _proc, _writer
    if _writer:
        try:
            _writer.close()
        except Exception:
            pass
        _writer = None
    if _proc and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(10)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None
    return {"ok": True}


def _call(name, args):
    if name == "comi_start":
        return _start(args.get("room", 87), args.get("seconds", 300))
    if name == "comi_send":
        return _send(args["command"])
    if name == "comi_click":
        return _send("click %d %d" % (args["x"], args["y"]))
    if name == "comi_replay":
        return _replay(args["name"])
    if name == "comi_status":
        return _status()
    if name == "comi_stop":
        return _stop()
    return {"ok": False, "error": "unbekanntes Werkzeug: " + name}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "comi-control", "version": "1.0"},
            }
        elif method == "tools/list":
            result = {"tools": _tools()}
        elif method == "tools/call":
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(_call(params.get("name"), params.get("arguments") or {})),
                    }
                ]
            }
        elif method == "notifications/initialized":
            continue
        else:
            out = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unbekannt"}}
            print(json.dumps(out), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)


if __name__ == "__main__":
    _log("bereit")
    main()
