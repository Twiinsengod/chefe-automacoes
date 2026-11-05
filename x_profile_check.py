#!/usr/bin/env python3
"""Checagem do perfil do X: snapshot + diff. Somente leitura, nunca publica."""
import argparse, json, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = {"name": "Nome", "description": "Bio", "url": "Link", "location": "Localização",
          "pinned_tweet_id": "Post fixado", "followers_count": "Seguidores",
          "following_count": "Seguindo", "post_count": "Posts"}


def normalize(raw):
    """Converte a resposta da API v2 (users/by/username) em um snapshot plano."""
    u = raw.get("data", raw)
    urls = (u.get("entities") or {}).get("url", {}).get("urls", [])
    link = urls[0].get("expanded_url") if urls else u.get("url")
    pm = u.get("public_metrics", {})
    pinned_missing = any("pinned_tweet_id" in (e.get("detail") or "") for e in raw.get("errors", []))
    return {"username": u.get("username"), "name": u.get("name"), "description": u.get("description"),
            "url": link, "location": u.get("location"), "pinned_tweet_id": u.get("pinned_tweet_id"),
            "pinned_missing": pinned_missing,
            "followers_count": pm.get("followers_count"), "following_count": pm.get("following_count"),
            "post_count": pm.get("post_count")}


def diff(old, new):
    return [(k, old.get(k), new.get(k)) for k in FIELDS if old.get(k) != new.get(k)]


def fetch(username, token):
    q = "user.fields=description,url,entities,location,pinned_tweet_id,public_metrics&expansions=pinned_tweet_id"
    req = urllib.request.Request(f"https://api.x.com/2/users/by/username/{username}?{q}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def report(new, changes, had_previous):
    out = [f"Checagem do perfil @{new['username']}"]
    if not had_previous:
        out.append("Primeiro snapshot salvo; nada para comparar ainda.")
    elif not changes:
        out.append("Nenhuma mudança desde o último snapshot.")
    for k, a, b in changes:
        if isinstance(a, int) and isinstance(b, int):
            out.append(f"- {FIELDS[k]}: {a} → {b} ({b - a:+d})")
        else:
            out.append(f"- {FIELDS[k]} mudou:\n    antes: {a}\n    agora: {b}")
    if new.get("pinned_missing"):
        out.append("⚠️ O post fixado não foi encontrado pela API (pode ter sido apagado ou estar indisponível).")
    if new.get("url") and new.get("pinned_tweet_id") and new["pinned_tweet_id"] in new["url"]:
        out.append("ℹ️ O link da bio aponta para o próprio post fixado.")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--username", default="_Fcruz")
    p.add_argument("--from-json", help="arquivo JSON da API (modo offline)")
    p.add_argument("--snapshots", default="snapshots")
    a = p.parse_args(argv)
    if a.from_json:
        raw = json.load(open(a.from_json, encoding="utf-8"))
    else:
        token = os.environ.get("X_BEARER_TOKEN")
        if not token:
            sys.exit("Defina X_BEARER_TOKEN ou use --from-json.")
        raw = fetch(a.username, token)
    new = normalize(raw)
    d = Path(a.snapshots); d.mkdir(exist_ok=True)
    prev = sorted(d.glob(f"{new['username']}_*.json"))
    old = json.load(open(prev[-1], encoding="utf-8")) if prev else None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (d / f"{new['username']}_{ts}.json").write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    print(report(new, diff(old, new) if old else [], old is not None))


if __name__ == "__main__":
    main()
