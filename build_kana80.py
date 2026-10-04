#!/usr/bin/env python3
"""
try! JLPT N5 本文（N5_book_all.md）から、ひらがな・カタカナが
なるべく均等に出る基本文を 80 文選び、練習セット「かな均等80」を生成する。

- 振り仮名は本文の 漢字《よみ》／｜漢字《よみ》 表記をそのまま使う（推測変換しない）
- カタカナは本文に自然に出てくるものだけを数える（ひらがな文を変換しない）
- 出力: sentences_kana80.json と index.html の埋め込みJSON（id="sentences-json-kana80"）
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent / "try!JLPT" / "N5" / "N5_book_all.md"
OUT_JSON = HERE / "sentences_kana80.json"
HTML = HERE / "index.html"
TARGET_COUNT = 80
MAX_KANA = 16  # 初級 = 読み 16 拍以内
MIN_KANA = 6

# ---------- 初級フィルタ ----------
# JLPT N5 の漢字（約100字）。これ以外の漢字を含む文は除外
N5_KANJI = set("日一国人年大十二本中長出三時行見月後前生五間上東四今金九入学高円子外八六下来気小七山話女北午百書"
               "先名川千水半男西電校語土木聞食車何南万毎白天母火右読友左休父雨"
               # 初級の基本語彙でよく使う漢字（好き・店・家・買う・飲む など）
               "好店家買飲帰会早近多少明新古安色赤青道駅町週曜春夏秋冬朝晩夜昼飯物犬花海空口目耳手足"
               "肉魚茶歩走起寝着住写真言思持使作")
# 丁寧形の文末だけ（普通体の会話文は除外）
POLITE_END = re.compile(r"(です|ます|ません|ました|ませんか|ますか|ですか|でした|ましたか|でしたか|ませんでした|ましょう|ましょうか|ください|ですね|ですよ|ますよ)$")
# 初級より先の文法
ADVANCED_GRAMMAR = ["たり", "てから", "ながら", "あとで", "まえに", "でしょう", "かった", "ないでくだ", "ている", "ています",
                    "ていま", "なければ", "けど", "ので"]
# 人名（本の登場人物）と人称代名詞
PERSON_NAMES = ["佐藤", "山田", "鈴木", "田中", "高橋", "伊藤", "渡辺", "小林", "林", "木村", "山本", "西川", "中村",
                "佐々木", "大山", "吉田", "加藤", "リン", "スミス", "ファウジ", "キム", "ワン", "チン", "タン", "ジョーンズ"]
PRONOUNS = ["私", "わたし", "わたくし", "あなた", "彼", "かのじょ", "ぼく", "僕", "みんな", "だれ", "誰", "自分"]


def is_beginner(ja: str, reading: str) -> bool:
    kanji = re.findall("[" + KANJI + "]", ja)
    if any(k not in N5_KANJI for k in kanji):
        return False
    if not POLITE_END.search(ja):
        return False
    if any(g in reading for g in ADVANCED_GRAMMAR):
        return False
    if any(n in ja for n in PERSON_NAMES) or any(w in ja for w in PRONOUNS):
        return False
    # 「〜さん」は家族（お母さん等）以外は人名とみなして除外
    if re.search(r"(?<![母父兄姉])(?<=[" + KANJI + r"ァ-ヶー])さん", ja):
        return False
    return True

HIRA = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
            "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ")
KATA = [chr(ord(c) + 0x60) for c in HIRA]

# 選定から外す文（文脈依存の断片・問題文の指示など）
EXCLUDE = {
    "したり しました",
    "イタリアの です",
    "先生 時計は",
    "夕方から バイト",
    "だいじょうぶ",
    "お元気で",
    "はい カシオのです",
    "すぐ 使いますから",
    "レストランの 前に 下の 文が ありました",
    "男の人はこのあとすぐ何をしますか",
    "じょうぶなのを ください",
}

KANJI = r"一-龥々〆ヶ"
RUBY_RE = re.compile(r"｜([^｜《》]+)《([^》]+)》|([" + KANJI + r"]+)《([^》]+)》")


# ---------- 本文の解析 ----------

def clean_line(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^(>\s*)+", "", s)
    s = re.sub(r"^[①-⑳]\s*", "", s)
    s = re.sub(r"^[1-9]\s+", "", s)
    s = re.sub(r"^[0-9０-９]+[.．]\s*", "", s)
    # 話者ラベル（例: 店員《てんいん》：）
    s = re.sub(r"^[^：:「」。、\s　]{1,20}[：:]", "", s)
    return s.strip()


def parse_ruby(s: str):
    """本文を [(表示, よみ or None), ...] に分解"""
    parts = []
    pos = 0
    for m in RUBY_RE.finditer(s):
        if m.start() > pos:
            parts.append((s[pos:m.start()], None))
        base = m.group(1) or m.group(3)
        reading = m.group(2) or m.group(4)
        parts.append((base, reading))
        pos = m.end()
    if pos < len(s):
        parts.append((s[pos:], None))
    return parts


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def normalize_spaces(s: str) -> str:
    s = s.replace("　", " ").replace("、", " ")
    s = re.sub(r"[。？！?!]", "", s)
    return re.sub(r" +", " ", s).strip()


def build_entry(raw: str):
    s = raw.replace("｜", "｜")  # 全角縦棒はそのまま
    parts = parse_ruby(s)
    ja, furi, reading = "", "", ""
    for text, rd in parts:
        if rd is None:
            ja += text
            furi += esc(text)
            reading += text
        else:
            ja += text
            furi += f"<ruby>{esc(text)}<rt>{esc(rd)}</rt></ruby>"
            reading += rd
    ja, furi, reading = (normalize_spaces(x) for x in (ja, furi, reading))
    return ja, furi, reading


# ---------- かな → ローマ字 ----------

BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "wo", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o", "ゔ": "vu",
}
YOON = {}
for head, cons in [("き", "ky"), ("し", "sh"), ("ち", "ch"), ("に", "ny"), ("ひ", "hy"),
                   ("み", "my"), ("り", "ry"), ("ぎ", "gy"), ("じ", "j"), ("び", "by"), ("ぴ", "py")]:
    for small, v in [("ゃ", "a"), ("ゅ", "u"), ("ょ", "o")]:
        YOON[head + small] = cons + v
YOON["てぃ"] = "thi"  # パーティー など


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def word_to_romaji(word: str) -> str:
    w = kata_to_hira(word)
    out = ""
    i = 0
    sokuon = False
    while i < len(w):
        pair = w[i:i + 2]
        ch = w[i]
        if pair in YOON:
            r = YOON[pair]
            i += 2
        elif ch == "っ":
            sokuon = True
            i += 1
            continue
        elif ch == "ー":
            vowels = [c for c in out if c in "aeiou"]
            r = vowels[-1] if vowels else ""
            i += 1
        elif ch in BASE:
            r = BASE[ch]
            i += 1
        else:
            raise ValueError(f"未対応の文字: {ch!r} in {word}")
        if sokuon:
            r = ("t" + r) if r.startswith("ch") else (r[0] + r)
            sokuon = False
        out += r
    return out


def reading_to_romaji(reading: str) -> str:
    return " ".join(word_to_romaji(w) for w in reading.split(" "))


# ---------- 候補の抽出 ----------

def is_supported(reading: str) -> bool:
    try:
        reading_to_romaji(reading)
    except ValueError:
        return False
    # ん＋母音（きんえん等）はアプリ側の分割表示がずれるので除外
    if re.search(r"[んン][あいうえおやゆよアイウエオヤユヨ]", reading):
        return False
    # 拗音以外の小書き母音（ファ・ティ等）は表示分割が未対応のため除外
    if re.search(r"[ぁぃぅぇぉァィゥェォ]", reading):
        return False
    return True


def extract_candidates():
    cands = {}
    for line in BOOK.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        line_s = clean_line(line)
        # 1行に複数文あれば文ごとに分ける（文末記号の無い末尾は捨てる）
        for s in re.findall(r"[^。？]+[。？]", line_s):
            s = s.strip()
            add_candidate(cands, s)
    return list(cands.values())


def add_candidate(cands, s):
    if re.search(r"[฀-๿a-zA-Zａ-ｚＡ-Ｚ0-9０-９（）()＿_□…\[\]／/〜～「」『』・＊★→]", s):
        return
    ja, furi, reading = build_entry(s)
    if re.search("[" + KANJI + "]", reading):  # 読みの無い漢字が残る
        return
    if not is_supported(reading):
        return
    n = len(reading.replace(" ", ""))
    if not (MIN_KANA <= n <= MAX_KANA):
        return
    if not is_beginner(ja, reading):
        return
    if ja in EXCLUDE or ja.endswith("は"):  # 「〜さんは」等の言いさしは除外
        return
    # 問題の指示文・絵や設問を参照する文は除外
    if "下の" in ja or re.search(r"(ぶん|しつもん|もんだい)を", reading):
        return
    cands.setdefault(ja, {"ja": ja, "furigana": furi, "reading": reading})


# ---------- 均等化の選定 ----------

TARGETS = HIRA + KATA


def units(reading: str) -> Counter:
    return Counter(c for c in reading if c in TARGETS)


def bigrams(reading: str) -> set:
    r = reading.replace(" ", "")
    return {r[i:i + 2] for i in range(len(r) - 1)}


def too_similar(cand, chosen, limit=0.35) -> bool:
    """ほぼ同じ文（男の人/女の人が ボールペンを 買います 等）を二重に選ばない"""
    for w in cand["_kw"]:  # 同じカタカナ語は2文まで
        if sum(w in c["_kw"] for c in chosen if c is not cand) >= 2:
            return True
    a = cand["_bg"]
    for c in chosen:
        if c is cand:
            continue
        b = c["_bg"]
        if a and b and len(a & b) / len(a | b) > limit:
            return True
    return False


# 文字ごとの効用 f(c) = Σ_{k=1..c} 1/k^1.5（出現回数に対して強く逓減。少ない文字を増やすほど得点が高い）
_F = [0.0]
for _k in range(1, 2000):
    _F.append(_F[-1] + 1.0 / (_k ** 1.5))

LENGTH_PENALTY = 0.02


def delta(counts: Counter, add: Counter, remove: Counter) -> float:
    d = 0.0
    for ch in set(add) | set(remove):
        c0 = counts[ch]
        c1 = c0 + add.get(ch, 0) - remove.get(ch, 0)
        d += _F[c1] - _F[c0]
    return d


def select(cands):
    for c in cands:
        c["_u"] = units(c["reading"])
        c["_len"] = len(c["reading"].replace(" ", ""))
        c["_bg"] = bigrams(c["reading"])
        c["_kw"] = set(re.findall(r"[ァ-ヶー]{2,}", c["ja"]))
    available = sorted({ch for c in cands for ch in c["_u"]})
    empty = Counter()

    chosen, counts, pool = [], Counter(), cands[:]
    while len(chosen) < TARGET_COUNT:
        best = max((c for c in pool if not too_similar(c, chosen)),
                   key=lambda c: delta(counts, c["_u"], empty) - LENGTH_PENALTY * c["_len"])
        pool.remove(best)
        chosen.append(best)
        counts += best["_u"]

    # 1文ずつの入れ替えによる局所改善（差分計算）
    improved = True
    while improved:
        improved = False
        for i in range(len(chosen)):
            out = chosen[i]
            others = chosen[:i] + chosen[i + 1:]
            best_d, best_c = 1e-9, None
            for cand in pool:
                d = delta(counts, cand["_u"], out["_u"]) - LENGTH_PENALTY * (cand["_len"] - out["_len"])
                if d > best_d and not too_similar(cand, others):
                    best_d, best_c = d, cand
            if best_c is not None:
                counts = counts - out["_u"] + best_c["_u"]
                pool.remove(best_c)
                pool.append(out)
                chosen[i] = best_c
                improved = True
    return chosen, available


def main():
    cands = extract_candidates()
    chosen, available = select(cands)
    counts = Counter()
    for c in chosen:
        counts += c["_u"]

    data = [{
        "ja": c["ja"],
        "category": "かな均等80",
        "group": "try! JLPT N5 本文",
        "furigana": c["furigana"],
        "romaji": reading_to_romaji(c["reading"]),
    } for c in chosen]
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    marker = '<script type="application/json" id="sentences-json-kana80">'
    start = html.find(marker)
    if start == -1:
        print("（index.html から かな均等80 は外しているため、JSONのみ出力）")
    else:
        end = html.find("</script>", start)
        embedded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        HTML.write_text(html[:start + len(marker)] + "\n" + embedded + "\n" + html[end:], encoding="utf-8")

    # レポート
    print(f"候補 {len(cands)} 文 → {len(chosen)} 文を選定")
    for label, chars in (("ひらがな", HIRA), ("カタカナ", KATA)):
        present = [ch for ch in chars if ch in available]
        missing = [ch for ch in chars if ch not in available]
        vals = [counts[ch] for ch in present]
        print(f"\n[{label}] 候補に有る {len(present)}/{len(chars)} 字  最小 {min(vals)} / 最大 {max(vals)}"
              f" / 中央値 {sorted(vals)[len(vals) // 2]}")
        print("  候補に無い:", "".join(missing) or "なし")
        print("  " + " ".join(f"{ch}{counts[ch]}" for ch in present))


if __name__ == "__main__":
    main()
