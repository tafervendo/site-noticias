#!/usr/bin/env python3
"""Avisa o Bing (e quem usa o IndexNow: Yandex, Seznam, Naver) das matérias novas, logo após publicar."""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CFG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
BASE = CFG["url"].rstrip("/")
CHAVE = CFG.get("indexnow_chave", "")


def main():
    if not re.fullmatch(r"[a-f0-9]{32}", CHAVE):
        return
    resumos = json.loads((RAIZ / "data" / "resumos.json").read_text(encoding="utf-8"))
    desde = datetime.now(timezone.utc) - timedelta(hours=3)
    urls = [f'{BASE}/noticia/{r["slug"]}.html' for r in resumos.values()
            if r.get("slug") and datetime.fromisoformat(r["criado"]) >= desde]
    if not urls:
        print("IndexNow: nenhuma matéria nova.")
        return
    urls += [f"{BASE}/", f"{BASE}/arquivo.html"]
    corpo = json.dumps({"host": BASE.split("//")[1], "key": CHAVE, "keyLocation": f"{BASE}/{CHAVE}.txt",
                        "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=corpo, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"IndexNow: {len(urls)} endereços avisados (resposta {r.status}).")
    except Exception as e:  # aviso não pode derrubar a atualização
        print(f"IndexNow: aviso não enviado ({e}).")


if __name__ == "__main__":
    main()
