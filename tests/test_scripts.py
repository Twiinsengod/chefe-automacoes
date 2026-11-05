import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import x_profile_check as pc, x_best_hours as bh


def test_diff_detects_changes():
    old = {"name": "A", "description": "x", "followers_count": 10}
    new = {"name": "A", "description": "y", "followers_count": 12}
    assert pc.diff(old, new) == [("description", "x", "y"), ("followers_count", 10, 12)]


def test_diff_no_changes():
    s = {"name": "A", "followers_count": 1}
    assert pc.diff(s, dict(s)) == []


def test_normalize_uses_expanded_url_and_flags_missing_pin():
    raw = {"data": {"username": "u", "name": "N", "pinned_tweet_id": "9",
                    "entities": {"url": {"urls": [{"expanded_url": "https://x.com/u/status/9"}]}},
                    "public_metrics": {"followers_count": 5}},
           "errors": [{"detail": "Could not find post with pinned_tweet_id: [9]."}]}
    s = pc.normalize(raw)
    assert s["url"] == "https://x.com/u/status/9" and s["pinned_missing"] and s["followers_count"] == 5


def test_pinned_note_tweet_resolved_from_includes():
    import json
    raw = json.loads((pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "fcruz_profile.json").read_text(encoding="utf-8"))
    short = "texto truncado da API"
    note = raw["includes"]["tweets"][0]["note_tweet"]["text"]
    raw["includes"]["tweets"][0]["text"] = short
    raw["errors"] = [{"detail": "Could not find post with pinned_tweet_id: [2117934197864075507].",
                      "parameter": "pinned_tweet_id", "resource_id": "2117934197864075507"}]
    s = pc.normalize(raw)
    assert s["pinned_missing"] is False
    assert s["pinned_tweet_id"] == "2117934197864075507"
    assert s["pinned_created_at"] == "2026-11-04T10:57:16.000Z"
    assert s["pinned_text"] == note
    assert s["pinned_text"].startswith("Olá  👋")
    assert "Me segue que eu te mostro como tô aprendendo." in s["pinned_text"]
    assert len(s["pinned_text"]) > len(short)


def test_snapshot_cycle(tmp_path, capsys):
    import json
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"data": {"username": "u", "name": "A", "public_metrics": {"followers_count": 1}}}))
    pc.main(["--from-json", str(f), "--snapshots", str(tmp_path / "s")])
    f.write_text(json.dumps({"data": {"username": "u", "name": "B", "public_metrics": {"followers_count": 3}}}))
    pc.main(["--from-json", str(f), "--snapshots", str(tmp_path / "s")])
    out = capsys.readouterr().out
    assert "Seguidores: 1 → 3 (+2)" in out and "agora: B" in out


def test_hour_aggregation_in_sao_paulo():
    posts = [  # 15:00Z = 12h em São Paulo (UTC-3)
        {"created_at": "2026-11-04T15:00:00.000Z", "public_metrics": {"like_count": 2, "impression_count": 10}},
        {"created_at": "2026-11-04T15:30:00.000Z", "public_metrics": {"like_count": 4, "reply_count": 2, "impression_count": 30}},
        {"created_at": "2026-11-04T02:00:00.000Z", "public_metrics": {"like_count": 1}},  # 23h do dia 3
    ]
    agg = bh.aggregate(posts, "hour")
    assert agg[12] == (2, 4.0, 20.0) and agg[23][0] == 1
    wd = bh.aggregate(posts, "weekday")
    assert wd[2][0] == 2 and wd[1][0] == 1  # qua e ter


def test_ranking_puts_low_sample_last():
    agg = {1: (1, 100.0, 0), 2: (5, 2.0, 0)}
    assert [b for b, _ in bh.ranking(agg, 5)] == [2, 1]
