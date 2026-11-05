#!/usr/bin/env python3
"""Checagem do perfil do X: snapshot + diff. Somente leitura, nunca publica."""
import argparse, json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = {"name": "Nome", "description": "Bio", "url": "Link", "location": "Localização",
          "pinned_tweet_id": "Post fixado", "pinned_text": "Texto do post fixado",
          "followers_count": "Seguidores", "following_count": "Seguindo", "post_count": "Posts"}


def included_tweets(raw):
    includes = raw.get("includes") or {}
    return list(includes.get("tweets") or []) + list(includes.get("posts") or [])


def find_included_tweet(raw, tweet_id):
    if not tweet_id:
        return None
    want = str(tweet_id)
    for tweet in included_tweets(raw):
        if str(tweet.get("id")) == want:
            return tweet
    return None


def tweet_text(tweet):
    """Texto completo: note_tweet (posts longos) tem prioridade sobre o text truncado."""
    if not tweet:
        return None
    note = tweet.get("note_tweet") or {}
    if isinstance(note, dict) and note.get("text"):
        return note["text"]
    return tweet.get("text")


def normalize(raw):
    """Converte a resposta da API v2 (users/by/username) em um snapshot plano."""
    u = raw.get("data", raw)
    urls = (u.get("entities") or {}).get("url", {}).get("urls", [])
    link = urls[0].get("expanded_url") if urls else u.get("url")
    pm = u.get("public_metrics", {})
    pinned_id = u.get("pinned_tweet_id")
    pinned = find_included_tweet(raw, pinned_id)
    api_missing = any(
        "pinned_tweet_id" in (e.get("detail") or "") or e.get("parameter") == "pinned_tweet_id"
        for e in raw.get("errors", [])
    )
    # O expansion às vezes devolve resource-not-found mesmo com o post em includes.
    pinned_missing = bool(pinned_id) and pinned is None and api_missing
    return {"username": u.get("username"), "name": u.get("name"), "description": u.get("description"),
            "url": link, "location": u.get("location"), "pinned_tweet_id": pinned_id,
            "pinned_text": tweet_text(pinned), "pinned_created_at": (pinned or {}).get("created_at"),
            "pinned_missing": pinned_missing,
            "followers_count": pm.get("followers_count"), "following_count": pm.get("following_count"),
            "post_count": pm.get("post_count")}


def diff(old, new):
    return [(k, old.get(k), new.get(k)) for k in FIELDS if old.get(k) != new.get(k)]


def fetch(username, token):
    q = ("user.fields=description,url,entities,location,pinned_tweet_id,public_metrics"
         "&expansions=pinned_tweet_id&tweet.fields=id,text,created_at,note_tweet,author_id")
    req = urllib.request.Request(f"https://api.x.com/2/users/by/username/{username}?{q}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = json.load(r)
    pinned_id = (raw.get("data") or {}).get("pinned_tweet_id")
    if pinned_id and find_included_tweet(raw, pinned_id) is None:
        attached = fetch_tweet(pinned_id, token)
        if attached:
            raw.setdefault("includes", {}).setdefault("tweets", []).append(attached)
            raw["errors"] = [e for e in raw.get("errors", [])
                             if "pinned_tweet_id" not in (e.get("detail") or "")
                             and e.get("parameter") != "pinned_tweet_id"]
    return raw


def fetch_tweet(tweet_id, token):
    """O expansion pinned_tweet_id omite posts longos (note tweet) com resource-not-found."""
    q = "tweet.fields=id,text,created_at,note_tweet,author_id"
    req = urllib.request.Request(f"https://api.x.com/2/tweets/{tweet_id}?{q}",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except urllib.error.URLError:
        return None
    return body.get("data")


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
