#!/usr/bin/env python3
"""
助詞練習.md の全文から「助詞」練習セットを生成する。

- 各文節末の助詞を <mark> で囲み、アプリ側で空欄として表示する
- 振り仮名は md の 漢字《よみ》 表記をそのまま使う。数字＋助数詞は NUMBER_READINGS で読みを固定
- 出力: sentences_particles.json と index.html の埋め込みJSON（id="sentences-json-particles"）
"""
import json
import re
from pathlib import Path

from build_kana80 import esc, reading_to_romaji

HERE = Path(__file__).resolve().parent
SRC = HERE / "助詞練習.md"
OUT_JSON = HERE / "sentences_particles.json"
HTML = HERE / "index.html"

# 長いものから順に照合する
PARTICLES = ["くらい", "から", "まで", "など", "だけ", "が", "は", "を", "に", "で", "へ", "と", "や", "の", "も", "か", "ね", "よ"]
# 語末が助詞と同じ形でも助詞ではない語
NOT_PARTICLE_WORDS = {"とても", "くだもの", "この", "その", "あの", "どの"}

NUMBER_READINGS = {
    "1時": "いちじ", "3時": "さんじ", "7時": "しちじ", "9時": "くじ", "10時": "じゅうじ", "12時": "じゅうにじ",
    "1時間": "いちじかん", "15分": "じゅうごふん", "100円": "ひゃくえん", "100人": "ひゃくにん",
}

RUBY_RE = re.compile(r"([0-9]+(?:時間|時|分|円|人))《[^》]*》|([一-龥々A-Za-z]+)《([^》]+)》")


def parse_token(token: str):
    """文節を [(表示, よみ or None), ...] に分解"""
    parts, pos = [], 0
    for m in RUBY_RE.finditer(token):
        if m.start() > pos:
            parts.append((token[pos:m.start()], None))
        if m.group(1):
            base = m.group(1)
            if base not in NUMBER_READINGS:
                raise SystemExit(f"数字の読みが未登録: {base}")
            parts.append((base, NUMBER_READINGS[base]))
        else:
            parts.append((m.group(2), m.group(3)))
        pos = m.end()
    if pos < len(token):
        parts.append((token[pos:], None))
    return parts


def split_particles(tail: str, word_text: str):
    """文節末のかな部分 tail から助詞を後ろから切り出す。戻り値: (本体, [助詞...])"""
    if word_text in NOT_PARTICLE_WORDS:
        return tail, []
    found = []
    # 「3時までです」のように助詞の後ろに です が付く形
    m = re.search(r"(まで|から)(です)$", tail)
    if m:
        return tail[:m.start()], [m.group(1), "です"]
    for p in PARTICLES:
        if tail.endswith(p) and len(tail) >= len(p):
            found.insert(0, p)
            tail = tail[:-len(p)]
            break
    # 「ノートなどが」のように2つ重なる形
    if found and tail.endswith("など"):
        found.insert(0, "など")
        tail = tail[:-2]
    return tail, found


def build(line: str):
    furi_tokens, plain_tokens, reading_tokens, particles = [], [], [], []
    for token in line.split():
        parts = parse_token(token)
        word_text = "".join(t for t, _ in parts)
        # 助詞は必ず文節末のルビ無し部分にある
        last_text, last_rd = parts[-1]
        head_parts, tail = (parts[:-1], last_text) if last_rd is None else (parts, "")
        body, found = split_particles(tail, word_text)
        if found and found[-1] == "です":  # 「までです」の です は助詞ではない
            marked = found[:-1]
            after = "です"
        else:
            marked, after = found, ""
        furi = "".join(f"<ruby>{esc(t)}<rt>{esc(r)}</rt></ruby>" if r else esc(t) for t, r in head_parts) + esc(body)
        plain = "".join(esc(t) for t, _ in head_parts) + esc(body)
        for p in marked:
            furi += f"<mark>{esc(p)}</mark>"
            plain += f"<mark>{esc(p)}</mark>"
        furi += esc(after)
        plain += esc(after)
        furi_tokens.append(furi)
        plain_tokens.append(plain)
        reading_tokens.append("".join(r or t for t, r in parts))
        particles += marked
    ja = re.sub(r"</?mark>", "", " ".join(plain_tokens))
    reading = " ".join(reading_tokens)
    return {
        "ja": ja,
        "category": "助詞",
        "group": "助詞練習",
        "furigana": " ".join(furi_tokens),
        "ja_html": " ".join(plain_tokens),
        "romaji": reading_to_romaji(reading),
        "particles": particles,
    }


def main():
    lines = [l.strip() for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    data = [build(l) for l in lines]
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    marker = '<script type="application/json" id="sentences-json-particles">'
    start = html.find(marker)
    if start == -1:
        raise SystemExit("index.html に sentences-json-particles がありません")
    end = html.find("</script>", start)
    embedded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    HTML.write_text(html[:start + len(marker)] + "\n" + embedded + "\n" + html[end:], encoding="utf-8")

    print(f"{len(data)} 文")
    for d in data:
        print(re.sub(r"<mark>(.*?)</mark>", r"［\1］", d["ja_html"]), "|", d["romaji"])


if __name__ == "__main__":
    main()
