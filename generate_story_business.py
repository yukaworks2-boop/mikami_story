"""
三上ビジネス インスタストーリー自動生成スクリプト
毎日Claude APIを使ってAIノウハウ系ストーリーを生成し、stories_business/に保存する。
"""

import anthropic
import os
import json
import re
import random
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
today = datetime.now(JST)
date_str = today.strftime("%Y-%m-%d")
weekday = today.weekday()

SYSTEM_PROMPT = """三上ビジネス インスタストーリー用プロンプト

■ System Role & Identity

あなたは**みかみ（三上功太）**として、AIノウハウ・活用法に特化したインスタストーリーを作成します。
このアカウントは「三上ビジネス」として、経営者・副業・起業家向けにAIの実践的な使い方を発信します。

■ 文体ルール（重要）

一人称
- 必ず「僕」を使う（「俺」は絶対に使わない）

みかみ特有の口調
- 「〜なんよな」「〜なんよ」← 超頻出
- 「〜よね」「〜だよね」
- 「マジで」「ガチで」「めちゃくちゃ」
- 「やばい」「エグい」「最高」
- 「w」「笑」

禁止事項
- 「。」は使わない
- 「〜やで」「〜やん」「〜やな」「〜や」（関西弁）
- 「めっちゃ」（関西弁強すぎる時）
- 「ほんま」「ほんまに」
- CTAフレーズ（「DMして」「リンクから」「プロフィールへ」）
- 関西弁全般

■ コンテンツ方針

テーマ：AIノウハウ・活用法に特化
- 具体的な使い方・実践例を中心に
- 難しそうに見えることをシンプルに伝える
- 「触ってみたら分かった」系のリアルな体験談
- AIツール比較・使い分け
- AI×ビジネスの実績・数字
- 初心者でもできる入り口から解説

文章構成
- 短文と長文のリズム: 短い衝撃 → 詳細説明
- 改行を効果的に使う
- 数字を入れる（具体性と説得力）

■ Story Structure

連続ストーリーの基本構成（5〜7枚）
【導入】1-2枚目: 驚き・問いかけ・共感を呼ぶ問題提起
【展開】3-5枚目: 具体的なやり方・実績・比較
【結論】6-7枚目: まとめ・行動を促す・アンケートorスタンプ

■ Output Format

━━━━━━━━━━━━━━━━
📱 ストーリー 1枚目
━━━━━━━━━━━━━━━━
[ここに1枚目のテキスト]

━━━━━━━━━━━━━━━━
📱 ストーリー 2枚目
━━━━━━━━━━━━━━━━
[ここに2枚目のテキスト]

という形式で出力する。
"""

TOPIC_POOL = [
    {
        "id": "claude_vs_chatgpt",
        "what": "Claude CodeとChatGPTの本質的な違い。ChatGPTは「返答する」、Claude Codeは「達成するために動く」。使い分けが分かると仕事の質が変わる。",
        "how": "初心者でも分かるように比較形式で。5〜6枚。アンケート「今どっちをメインで使ってる？」",
    },
    {
        "id": "ai_prompt_kotsu",
        "what": "AIに上手く指示するコツ。ほとんどの人が「質問」してるけど「依頼」に変えるだけで精度が爆上がりする。背景・目的・アウトプット形式を入れるだけ。",
        "how": "Before/After形式で分かりやすく。5〜6枚。スタンプアクション「試してみた人リアクション」",
    },
    {
        "id": "ai_gyoumu_jidoka",
        "what": "AIで自動化できる業務リスト。SNS投稿・資料作成・メール返信・議事録・リサーチ。「人がやらなくていい仕事」はほぼ全部AIに渡せる時代。",
        "how": "具体的な業務名と時間削減効果を入れる。6枚。アンケート「今どの業務を自動化したい？」",
    },
    {
        "id": "claude_code_hajimekata",
        "what": "Claude Codeの始め方。難しそうに見えるけど、最初の一歩はめちゃくちゃシンプル。インストールから最初の指示まで5分でできる。",
        "how": "ステップ形式で。初心者向けに優しく。6枚。スタンプアクション「やってみた人リアクション」",
    },
    {
        "id": "ai_eigyo_jidoka",
        "what": "AIで営業を自動化した実例。リード獲得・アプローチ・フォローアップまでAIが動く仕組み。人間がやることは判断だけ。",
        "how": "実績数字を入れて説得力を出す。6〜7枚。アンケート「営業の自動化に興味ある？」",
    },
    {
        "id": "ai_sns_jidoka",
        "what": "SNS投稿をAIで自動化する方法。ネタ出し・文章生成・スケジュール投稿まで全部仕組み化できる。毎日投稿が1日15分で回る。",
        "how": "具体的なフローを説明。5〜6枚。スタンプアクション「これ欲しい人リアクション」",
    },
    {
        "id": "ai_uriage_5000man",
        "what": "Claude Code使ってAI導入支援で初月5000万作った話。やったのは営業リード獲得自動化・SNS投稿自動化・スライド作成自動化の3つだけ。",
        "how": "実体験ベースでリアルに。6枚。アンケート「どれが一番やってみたい？」",
    },
    {
        "id": "ai_cowork_nyuumon",
        "what": "Claude Coworkから始めるAI活用入門。コード不要・専門知識不要。普通の言葉で話しかけるだけでなんでも動く。パソコン苦手でも大丈夫。",
        "how": "とにかく敷居を下げる。具体的な使用例を入れる。5〜6枚。スタンプアクション「触ってみた人リアクション」",
    },
    {
        "id": "ai_kakusa_2026",
        "what": "2026年のAI格差。使える人と使えない人の差は今年が決定的。まだ触ってない人がほとんどだから今動いた人が圧倒的に勝てる。",
        "how": "危機感と希望をセットで。前向きに。6枚。アンケート「今のAI活用レベルは？」",
    },
    {
        "id": "ai_shigoto_kawaru",
        "what": "AIで変わる仕事の話。なくなる仕事・残る仕事より「AIを使う側に回る人」と「使われる側になる人」の差の方が重要。",
        "how": "具体的な職種例を入れつつ。6〜7枚。アンケート「今の仕事でAIを使ってる？」",
    },
    {
        "id": "ai_prompt_template",
        "what": "すぐ使えるAIプロンプトテンプレート3選。①議事録要約②SNS投稿生成③メール返信。コピペするだけで業務が10倍速くなる。",
        "how": "テンプレートをそのまま見せる。実用的に。6枚。スタンプアクション「保存した人リアクション」",
    },
    {
        "id": "ai_keiei_katsuyo",
        "what": "経営者がAIを使うべき3つの理由。判断スピードが上がる・情報整理が秒で終わる・アイデアの壁打ち相手になる。AIは経営者の思考を拡張するツール。",
        "how": "経営者目線で。具体的な活用シーンを入れる。6枚。アンケート「一番使いたいのは？」",
    },
    {
        "id": "ai_mae_kyouyu",
        "what": "Claude Codeを組織に入れて分かった。一番詰まるのは「前提共有」だった。1人なら秒で終わる作業が、コラボする瞬間前提を揃えるだけで半日消える。",
        "how": "リアルな組織導入体験として。6枚。アンケート「チームでAI使ってる？」",
    },
    {
        "id": "ai_slide_jidoka",
        "what": "スライド作成をAIで自動化する方法。構成・デザイン・文章生成まで全部AI。20枚のスライドが1時間で完成する時代。",
        "how": "実演イメージで。具体的な時間短縮効果を入れる。5〜6枚。スタンプアクション「やってみたい人リアクション」",
    },
    {
        "id": "ai_ceo_tsukurikata",
        "what": "AI社員（CEO）の作り方。役割・ルール・目標を設定するだけで24時間動いてくれるAIが完成する。オーナーは判断だけすればいい。",
        "how": "ステップ形式で。ワクワク感を出す。7枚。アンケート「どんなAI社員が欲しい？」",
    },
]

USED_TOPICS_FILE = "stories_business/.used_topics.json"


def load_used_topics() -> list:
    if not os.path.exists(USED_TOPICS_FILE):
        return []
    with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_used_topics(used: list):
    os.makedirs("stories_business", exist_ok=True)
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(used[-8:], f, ensure_ascii=False, indent=2)


def select_topic(used_ids: list) -> dict:
    unused = [t for t in TOPIC_POOL if t["id"] not in used_ids]
    if not unused:
        unused = TOPIC_POOL
    return random.choice(unused)


def generate_story(topic: dict) -> str:
    client = anthropic.Anthropic()

    slide_count = random.randint(5, 7)

    user_message = f"""今日のインスタストーリーを作成してください。

【何を言うか】：{topic['what']}

【どう言うか】：{topic['how']}

注意事項：
- ストーリーは必ず{slide_count}枚構成にする
- 「。」は使わない
- 「〜なんよな」「〜なんよ」を自然に使う
- 関西弁は使わない
- CTAフレーズは入れない
- AIの具体的な活用シーンや数字を入れてリアリティを出す"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    return message.content[0].text


def save_story(content: str, date_str: str, topic_id: str) -> str:
    os.makedirs("stories_business", exist_ok=True)
    file_path = f"stories_business/{date_str}.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# 三上ビジネス ストーリー - {date_str}\n")
        f.write(f"<!-- topic: {topic_id} -->\n\n")
        f.write(content)

    return file_path


def main():
    import sys
    no_spreadsheet = "--no-spreadsheet" in sys.argv

    print(f"三上ビジネス ストーリー生成開始: {date_str}")

    used_ids = load_used_topics()
    topic = select_topic(used_ids)
    print(f"テーマ: [{topic['id']}] {topic['what'][:40]}...")

    print("Claude APIでストーリーを生成中...")
    story = generate_story(topic)

    file_path = save_story(story, date_str, topic["id"])
    print(f"ストーリーを保存しました: {file_path}")

    if no_spreadsheet:
        print("スプシ転記をスキップ（確認後に「④ ビジネス スプシに転記」ワークフローを実行してください）")

    used_ids.append(topic["id"])
    save_used_topics(used_ids)

    print("\n--- 生成されたストーリー ---")
    print(story)


if __name__ == "__main__":
    main()
