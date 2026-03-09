#!/usr/bin/env python3
"""
N5問題集とタイピング練習お題から日本語文を抽出し、
ローマ字変換してJSONデータを生成するスクリプト
"""
import json
import re

try:
    import pykakasi
    kks = pykakasi.kakasi()
    HAS_PYKAKASI = True
except ImportError:
    HAS_PYKAKASI = False
    print("pykakasi not installed. Run: pip install pykakasi")
    print("Using manual romaji for sample sentences.")


def has_kanji(s: str) -> bool:
    """文字列に漢字が含まれるか"""
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def _escape(s: str) -> str:
    """XSS対策のエスケープ"""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_furigana_html(text: str) -> str:
    """日本語文を振り仮名付きHTML（rubyタグ）に変換。漢字部分のみ振り仮名を表示。"""
    if not HAS_PYKAKASI or not text.strip():
        return text
    result = kks.convert(text)
    parts = []
    for item in result:
        orig = item.get("orig", "")
        hira = item.get("hira", orig)
        if not orig:
            continue
        kanji_part = "".join(c for c in orig if has_kanji(c))
        non_kanji_part = "".join(c for c in orig if not has_kanji(c))
        if not kanji_part:
            parts.append(_escape(orig))
        else:
            kanji_reading = hira[: len(hira) - len(non_kanji_part)] if non_kanji_part else hira
            kanji_reading = kanji_reading.replace("にっぽん", "にほん")
            parts.append(f"<ruby>{_escape(kanji_part)}<rt>{_escape(kanji_reading)}</rt></ruby>")
            if non_kanji_part:
                parts.append(_escape(non_kanji_part))
    html = "".join(parts)
    html = _fix_furigana_hito_nin(html)
    html = _fix_furigana_okane(html)
    html = _fix_furigana_common_errors(html)
    return html


def _fix_furigana_common_errors(html: str) -> str:
    """pykakasiの誤変換を修正"""
    # 買い物（かいもの）: 買物<rt>かいも</rt>い → 買<rt>か</rt>い物<rt>もの</rt>
    html = re.sub(
        r"<ruby>買物<rt>かいも</rt></ruby>い",
        "<ruby>買<rt>か</rt></ruby>い<ruby>物<rt>もの</rt></ruby>",
        html,
    )
    # 今日（きょう）: 今日は＝today のとき。こんにちはは挨拶で今日はと書かないことが多い
    html = re.sub(
        r"<ruby>今日<rt>こんにち</rt></ruby>は",
        "<ruby>今日<rt>きょう</rt></ruby>は",
        html,
    )
    # 知り合い（しりあい）: 知合<rt>しり</rt>りい → 知<rt>し</rt>り合<rt>あ</rt>い
    html = re.sub(
        r"<ruby>知合<rt>しり</rt></ruby>りいと",
        "<ruby>知<rt>し</rt></ruby>り<ruby>合<rt>あ</rt></ruby>いと",
        html,
    )
    # 時刻の時（じ）: 7時、11時など数字の後の時はじ。ときは「時」が「とき」の意味のときのみ
    html = re.sub(r"([0-9]+)<ruby>時<rt>とき</rt></ruby>", r"\1<ruby>時<rt>じ</rt></ruby>", html)
    return html


def _fix_furigana_okane(html: str) -> str:
    """お金（おかね）の金はかね。金曜日・銀行などの金はきんのまま。"""
    return re.sub(
        r"お<ruby>金<rt>きん</rt></ruby>",
        "お<ruby>金<rt>かね</rt></ruby>",
        html,
    )


def _fix_furigana_hito_nin(html: str) -> str:
    """人の読み: 助数詞（数字の後）はにん、それ以外（人）はひと"""
    # 数字の直後の人（4人、3人など）はにん、それ以外はひと
    return re.sub(
        r"(?<![0-9])<ruby>人<rt>にん</rt></ruby>",
        "<ruby>人<rt>ひと</rt></ruby>",
        html,
    )


def furigana_to_reading(furigana_html: str) -> str:
    """振り仮名HTMLから読み（ひらがな・カタカナ）を抽出。ローマ字の正とする。"""
    # <ruby>漢字<rt>読み</rt></ruby> → 読み に置換。その他のテキストはそのまま。
    reading = re.sub(r"<ruby[^>]*>.*?<rt>([^<]+)</rt>.*?</ruby>", r"\1", furigana_html)
    # 残りのHTMLタグを除去
    reading = re.sub(r"<[^>]+>", "", reading)
    # HTMLエンティティを復元（&amp; → & など）
    reading = reading.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return reading.strip()


def reading_to_romaji(reading: str) -> str:
    """ひらがな・カタカナの読みをローマ字に変換。振り仮名と一致させる。"""
    if not HAS_PYKAKASI or not reading.strip():
        return ""
    result = kks.convert(reading)
    romaji_parts = []
    for item in result:
        r = item.get("hepburn", "")
        if r:
            romaji_parts.append(r)
    romaji = " ".join(romaji_parts).strip()
    romaji = re.sub(r"(\d+)\s*tokini", r"\1 ji ni", romaji, flags=re.I)
    romaji = re.sub(r"(\d+)\s*toki", r"\1 ji", romaji, flags=re.I)
    romaji = _fix_number_readings(romaji)
    romaji = _fix_romaji_kyou(romaji)
    romaji = _fix_romaji_nihon(romaji)
    return romaji


def to_romaji(text: str) -> str:
    """日本語をローマ字に変換（ヘボン式）"""
    if not HAS_PYKAKASI:
        return ""
    text = text.strip()
    if not text:
        return ""
    result = kks.convert(text)
    romaji_parts = []
    for item in result:
        r = item.get('hepburn', '')
        if r:
            romaji_parts.append(r)
    romaji = " ".join(romaji_parts).strip()
    # 入力形式のローマ字表示（は=ha, を=wo, へ=he）のまま保持。読み方変換は行わない。
    # 時（じ）の修正: 7時→7ji, 8時→8ji
    romaji = re.sub(r'(\d+)\s*tokini', r'\1 ji ni', romaji, flags=re.I)
    romaji = re.sub(r'(\d+)\s*toki', r'\1 ji', romaji, flags=re.I)
    romaji = _fix_number_readings(romaji)
    romaji = _fix_romaji_kyou(romaji)
    romaji = _fix_romaji_nihon(romaji)
    return romaji


def _fix_romaji_kyou(romaji: str) -> str:
    """今日は（きょうは）: 今日＝today のとき。こんにちはは挨拶なので文脈で今日はならきょうは"""
    romaji = re.sub(r'\bkonnichiha\b', 'kyou ha', romaji, flags=re.I)
    romaji = re.sub(r'\bkonnichi\s+ha\b', 'kyou ha', romaji, flags=re.I)
    return romaji


def _fix_romaji_nihon(romaji: str) -> str:
    """日本（にほん）: pykakasiはにっぽん→nipponと出力することがある。nihonに統一"""
    romaji = re.sub(r'\bnippon\b', 'nihon', romaji, flags=re.I)
    return romaji


def _fix_number_readings(romaji: str) -> str:
    """数字＋助数詞を日本語の発音に合わせて修正"""
    # 数字＋時＋助詞: pykakasiが「7じに」「11じに」をjiniと一語で出力する場合。先に処理
    romaji = re.sub(r'\b11\s+jini\b', 'juuichiji ni', romaji, flags=re.I)
    romaji = re.sub(r'\b7\s+jini\b', 'shichiji ni', romaji, flags=re.I)
    romaji = re.sub(r'\b7\s+jide\b', 'shichiji de', romaji, flags=re.I)
    # 人（にん）: 1人→ひとり, 2人→ふたり, 4人→よにん（よんにんではない）
    romaji = re.sub(r'\b1\s*nin\b', 'hitori', romaji, flags=re.I)
    romaji = re.sub(r'\b2\s*nin\b', 'futari', romaji, flags=re.I)
    romaji = re.sub(r'\b4\s*nin\b', 'yonin', romaji, flags=re.I)
    romaji = re.sub(r'\byonnin\b', 'yonin', romaji, flags=re.I)
    # 14人, 24人など: じゅうよにん, にじゅうよにん
    romaji = re.sub(r'\b14\s*nin\b', 'juuyonin', romaji, flags=re.I)
    romaji = re.sub(r'\b24\s*nin\b', 'nijuuyonin', romaji, flags=re.I)
    # 時（じ）: 4時→よじ, 7時→しちじ, 9時→くじ, 14時→じゅうよじ, 17時→じゅうしちじ
    romaji = re.sub(r'\b17\s*ji\b', 'juushichiji', romaji, flags=re.I)
    romaji = re.sub(r'\b7\s*ji\b', 'shichiji', romaji, flags=re.I)
    romaji = re.sub(r'\b14\s*ji\b', 'juuyoji', romaji, flags=re.I)
    romaji = re.sub(r'\b24\s*ji\b', 'nijuuyoji', romaji, flags=re.I)
    romaji = re.sub(r'\bjuuyonji\b', 'juuyoji', romaji, flags=re.I)
    romaji = re.sub(r'\bjuunanaji\b', 'juushichiji', romaji, flags=re.I)
    romaji = re.sub(r'\bnanaji\b', 'shichiji', romaji, flags=re.I)
    # お金（おかね）: o kin → o kane
    romaji = re.sub(r'\bo\s+kin\b', 'o kane', romaji, flags=re.I)
    romaji = re.sub(r'\bokin\b', 'okane', romaji, flags=re.I)
    return romaji


def extract_from_typing_practice():
    """n5-typing-practice.md から文を抽出"""
    candidates = [
        "../../../20260131/n5-typing-practice.md",
        "../../20260131/n5-typing-practice.md",
        "20260131/n5-typing-practice.md",
    ]
    content = None
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                break
        except FileNotFoundError:
            continue
    if not content:
        return []

    sentences = []
    current_category = None
    current_group = None

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # カテゴリ見出し
        if line.startswith("## カテゴリ"):
            current_category = line.replace("## ", "").strip()
            continue
        if line.startswith("### グループ"):
            current_group = line.replace("### ", "").strip()
            continue
        # 番号付き文の形式: "1. 私は　毎朝7時に　起きます"
        match = re.match(r"^\d+\.\s+(.+)$", line)
        if match:
            text = match.group(1).strip()
            # 全角スペースを半角に変換（ローマ字ではスペース区切り）
            text_normalized = text.replace("　", " ")
            if len(text_normalized) >= 3:  # 短すぎる文は除外
                sentences.append({
                    "ja": text_normalized,
                    "category": current_category or "基本",
                    "group": current_group or "その他"
                })

    return sentences


def extract_from_test_questions():
    """n5-test-20questions.md から読解文を抽出"""
    candidates = ["../../../20260201/n5-test-20questions.md", "../../20260201/n5-test-20questions.md"]
    content = None
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                break
        except FileNotFoundError:
            continue
    if not content:
        return []

    sentences = []
    in_reading = False
    buffer = []

    for line in content.split("\n"):
        line = line.strip()
        if "読解" in line:
            in_reading = True
            continue
        if in_reading and line.startswith("**しつもん："):
            in_reading = False
            continue
        if in_reading and line.startswith("わたしは") or line.startswith("きのう") or line.startswith("となり") or line.startswith("しごとが"):
            # 読解文の本文
            text = line.replace("**", "").strip()
            if "。" in text:
                parts = text.split("。")
                for p in parts:
                    p = p.strip()
                    if len(p) > 10:
                        p = p + "。"
                        sentences.append({
                            "ja": p.replace("　", " "),
                            "category": "読解",
                            "group": "読解問題"
                        })
            elif len(text) > 15:
                sentences.append({
                    "ja": text.replace("　", " ")
                    if "。" in text else text.replace("　", " ") + "。",
                    "category": "読解",
                    "group": "読解問題"
                })

    return sentences


# 1行程度に収まる最大文字数（超える文は除外してレイアウト崩れを防ぐ）
MAX_SENTENCE_LENGTH = 40


def extract_reading_passages():
    """読解問題から短文のみ抽出（長文はレイアウト崩れのため除外）"""
    passages = [
        "先週 デパートに かいものに いきました。",
        "けさ シャワーを あびました。",
        "わたしの へやは この アパートの 2かいです。",
        "新しい くるまですね。",
        "さとうさんは ギターを じょうずに ひきます。",
        "あの ホテルは ゆうめいです。",
        "テーブルに おさらと はしを ならべて ください。",
        "この まちには ゆうめいな たてものが あります。",
        "その えいがは おもしろくなかったです。",
    ]

    return [{"ja": p.replace("　", " "), "category": "読解", "group": "読解問題"} for p in passages]


def main():
    all_sentences = []

    # タイピング練習から
    typing_sentences = extract_from_typing_practice()
    all_sentences.extend(typing_sentences[:80])  # 最初の80文

    # 読解文を追加
    reading = extract_reading_passages()
    all_sentences.extend(reading)

    # 重複除去と長文除外（レイアウト崩れ防止）
    seen = set()
    unique = []
    for s in all_sentences:
        key = s["ja"]
        if key not in seen and len(key) <= MAX_SENTENCE_LENGTH:
            seen.add(key)
            unique.append(s)

    # 振り仮名HTMLを先に生成し、その読みを正としてローマ字を生成（日本語表示と一致させる）
    for item in unique:
        ja_clean = item["ja"].replace("。", "").strip()
        item["ja"] = ja_clean
        item["furigana"] = to_furigana_html(ja_clean).replace("。", "")
        reading = furigana_to_reading(item["furigana"])
        item["romaji"] = reading_to_romaji(reading).replace(".", "").replace("。", "").strip()

    # ローマ字が空の場合はスキップ（pykakasiがない場合）
    if HAS_PYKAKASI:
        output = unique
    else:
        # サンプル用に手動でローマ字を追加
        manual_romaji = {
            "私は 毎朝7時に 起きます": "watashi wa maiasa 7 ji ni okimasu",
            "毎晩 11時に 寝ます": "maiban 11 ji ni nemasu",
            "朝ごはんを 食べます": "asagohan wo tabemasu",
            "コーヒーを 飲みます": "koohii wo nomimasu",
            "学校に 行きます": "gakkou ni ikimasu",
        }
        output = []
        for item in unique[:20]:
            if item["ja"] in manual_romaji:
                item["romaji"] = manual_romaji[item["ja"]]
                output.append(item)

    # JSON出力
    output_path = "sentences.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(output)} sentences to {output_path}")

    # index.html の埋め込みJSONを更新（ja, romaji, furigana のみ）
    embed = [{"ja": s["ja"], "romaji": s["romaji"], "furigana": s.get("furigana", s["ja"])} for s in output]
    embed_json = json.dumps(embed, ensure_ascii=False)
    html_path = "index.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        start_marker = '<script type="application/json" id="sentences-json">'
        end_marker = "</script>"
        start = html.find(start_marker)
        if start >= 0:
            content_start = start + len(start_marker)
            end = html.find(end_marker, content_start)
            if end >= 0:
                new_html = html[:content_start] + "\n" + embed_json + "\n  " + html[end:]
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(new_html)
                print(f"Updated embedded JSON in {html_path}")
            else:
                print("Warning: Could not find closing script tag")
        else:
            print("Warning: Could not find sentences-json in index.html")
    except Exception as e:
        print(f"Warning: Could not update index.html: {e}")
    if output:
        print("Sample:", output[0])


if __name__ == "__main__":
    main()
