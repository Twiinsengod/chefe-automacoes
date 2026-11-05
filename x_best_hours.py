#!/usr/bin/env python3
"""Melhores horários para postar no X, a partir dos posts do usuário."""
import argparse, json
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def engagement(m):
    return sum(m.get(k, 0) for k in ("like_count", "reply_count", "retweet_count", "quote_count", "bookmark_count"))


def aggregate(posts, key):
    """key: 'hour' ou 'weekday'. Retorna {bucket: (n, média de engajamento, média de impressões)}."""
    acc = defaultdict(lambda: [0, 0, 0])
    for p in posts:
        dt = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(TZ)
        b = dt.hour if key == "hour" else dt.weekday()
        m = p.get("public_metrics", {})
        a = acc[b]; a[0] += 1; a[1] += engagement(m); a[2] += m.get("impression_count", 0)
    return {b: (n, e / n, i / n) for b, (n, e, i) in acc.items()}


def ranking(agg, min_n):
    return sorted(agg.items(), key=lambda kv: (kv[1][0] >= min_n, kv[1][1], kv[1][0]), reverse=True)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("posts_json")
    p.add_argument("--min-amostra", type=int, default=5)
    p.add_argument("--sem-respostas", action="store_true", help="ignora respostas")
    a = p.parse_args(argv)
    raw = json.load(open(a.posts_json, encoding="utf-8"))
    posts = raw.get("data", raw)
    if a.sem_respostas:
        posts = [x for x in posts if not x.get("in_reply_to_user_id")]
    print(f"Base: {len(posts)} posts (horário de Brasília). Engajamento = curtidas+respostas+reposts+citações+salvos.")
    print(f"Faixas com menos de {a.min_amostra} posts são HIPÓTESE, não fato.\n")
    for key, label, fmt in (("hour", "Por hora do dia", lambda h: f"{h:02d}h"),
                            ("weekday", "Por dia da semana", lambda d: DIAS[d])):
        print(label + ":")
        for i, (b, (n, e, imp)) in enumerate(ranking(aggregate(posts, key), a.min_amostra), 1):
            tag = "fato (amostra ok)" if n >= a.min_amostra else "hipótese (amostra pequena)"
            print(f" {i:2d}. {fmt(b)}: {e:.2f} engaj./post, {imp:.0f} impressões/post, n={n} — {tag}")
        print()


if __name__ == "__main__":
    main()
