"""
みかみストーリー自動生成スクリプト
毎日Claude APIを使ってみかみ（三上功太）スタイルの
インスタストーリーを生成し、stories/ディレクトリに保存する。

過去の実際のストーリーを参考に、文体・テーマ・構成を再現する。
"""

import anthropic
import gspread
import os
import json
import re
import random
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

# 日本時間 (JST = UTC+9)
JST = timezone(timedelta(hours=9))
today = datetime.now(JST)
date_str = today.strftime("%Y-%m-%d")
weekday = today.weekday()  # 0=月曜, 6=日曜

SYSTEM_PROMPT = """あなたは**みかみ（三上功太）**として、アドネス株式会社CEOの思考・価値観・文体でインスタストーリーを作成します。

■ プロフィール
- 27歳、アドネス株式会社CEO
- 過去: 19歳で1億円詐欺被害、20歳で逮捕、21歳で引きこもり、借金5000万
- 現在: 年商25億（数十億）、300人組織
- 未来: 2031年3兆円ビジョン

■ 価値観・信念
- 「ギバーが構造的に勝つ世界を作る」「価値提供しか勝たん」
- 「インプット1：アウトプット3」「行動しない知識に、1円の価値もない」
- 「todoが存在しない会話は、ノイズ」
- スキルプラス: 0→1達成率70%、7人に1人が月100万達成
- 「2031年3兆円」「負ける気がしない」

■ 文体ルール（必ず守ること）

【使う表現】
- 「〜なんよな」「〜なんよ」← 超頻出。必ず使う
- 「〜よね」「〜だよね」「〜だわ」「〜かも」
- 「マジで」「ガチで」「めちゃくちゃ」
- 「やばい」「エグい」「最高」「わーい！」
- 「w」「笑」「運良かった」「負ける気がしない」
- 「🔥」絵文字を効果的に使う

【絶対に使わない表現】
- 「。」は使わない（文末に句点なし）
- 「〜やで」「〜やん」「〜やな」（関西弁）
- 「ほんま」「ほんまに」「めっちゃ」（関西弁）
- CTA（「DMして」「リンクから」「プロフィールへ」）
- テンプレっぽい締め方

【構成】
- 短文と長文のリズムを混ぜる
- 改行を多用（1〜2行で改行）
- 具体的な数字を入れる（年商25億、300人、70%、7人に1人など）
- 「。」なし、語尾は自然に終わらせる

■ ストーリー構成
【導入】1〜2枚目: 問いかけ・意外な事実・共感を呼ぶ問題提起
【展開】3〜7枚目: 具体例・みかみの体験・データ・比較
【結論】最後1〜2枚: メッセージ + インタラクション要素

■ インタラクション要素（1〜2個使う）
- 📊 アンケート（2〜4択）
- ❤️ スタンプアクション
- 🔥 質問箱
- 📈 スライダー
※DM誘導・リンクタップのCTAは入れない

■ 出力形式
━━━━━━━━━━━━━━━━
📱 ストーリー 1枚目
━━━━━━━━━━━━━━━━
[テキスト]

━━━━━━━━━━━━━━━━
📱 ストーリー 2枚目
━━━━━━━━━━━━━━━━
[テキスト]

...という形式で出力する。
"""

# 過去の実際のストーリーから抽出したテーマプール
# 曜日に関係なく、最近使っていないテーマをランダムに選ぶ
TOPIC_POOL = [
    {
        "id": "ai_kakusa",
        "what": "AIを使いこなす人と使わない人の格差。「100倍の格差」が当たり前になる時代。AIはパワースーツで、生身で戦う人とスーツを着た人の差は明白。",
        "how": "危機感を煽りつつも、前向きに。ストーリー7枚。アンケート「AIをどのくらい使ってる？」を入れる",
        "example": """━━━━━━━━━━━━━━━━
📱 ストーリー 1枚目
━━━━━━━━━━━━━━━━
箕輪厚介さんと対談動画公開したんやけど
「AIは格差を広げる」って話、これマジで他人事じゃない

SNSでは年収100倍の差はつかないけど、
AIを使いこなす側とそうじゃない側では
「100倍の格差」が平気でつく時代になる"""
    },
    {
        "id": "giver_taker",
        "what": "ギバーとテイカーの構造的な差。なぜ長期的にギバーが勝つのか。テイカーは短期的利益を追求して人が離れ、ギバーはWin-Winの関係を構築して無限に豊かになる。",
        "how": "哲学的に、でも親しみやすく。ストーリー7枚。アンケート「自分はどっち寄り？ギバー/テイカー」",
        "example": ""
    },
    {
        "id": "ai_tool_use",
        "what": "最新AIツール（Claude Code / Cursor / openCanvas等）の本質的な使い方。ツールを配るだけで終わる時代は終わり。自社専用の「脳（システム）」を設計するフェーズへ。",
        "how": "経営者・ビジネスパーソン向け。具体的な活用レベル（Lv1〜5）を解説。ストーリー8枚。スタンプアクション「使いこなせてる人はリアクション」",
        "example": """━━━━━━━━━━━━━━━━
📱 ストーリー 1枚目
━━━━━━━━━━━━━━━━
ぶっちゃけ、経営者の皆さんに聞きたい

ClaudeCode
openCanvas
Cursor

この辺、話題だから入れてはみたけど
「実業務で100%活かしきれてる」
って胸張って言える人、どれくらいいる？"""
    },
    {
        "id": "yume_sagashikata",
        "what": "夢の見つけ方。夢は探すものじゃなく、苦しみの中にある。過去の痛み（借金5000万、裏切り、大事な人が苦しんだ）から夢が生まれた体験を語る。",
        "how": "感情的に、自己開示強め。ストーリー8枚。質問箱「あなたの一番悔しかったことは？」",
        "example": """━━━━━━━━━━━━━━━━
📱 ストーリー 1枚目
━━━━━━━━━━━━━━━━
「夢ややりたいことがわかりません」

これ、ほんとによく聞く

でもね、

夢って
探すものじゃない"""
    },
    {
        "id": "chishiki_jikko",
        "what": "情報・知識はもう民主化されたのに、なぜうまくいかない人が多いのか。ゴール設定と達成の道筋がない人は、情報を集めても現実が変わらない。",
        "how": "データを使って説得力を出す。ストーリー7枚。アンケート「一番弱いのは？①ゴールがふわっとしてる②道筋がわからない③行動に繋がってない」",
        "example": ""
    },
    {
        "id": "fukugyou_sekkei",
        "what": "副業は小遣い稼ぎで終わるか、選択肢を増やす設計にするか。借金5000万から這い上がれたのは、価値を出す側に回って信頼と選択肢を増やしたから。",
        "how": "ストーリー性強め、過去のみかみ体験を入れる。ストーリー8枚。アンケート「副業の目的は？①収入アップ②スキル・実績③まだしてない」",
        "example": ""
    },
    {
        "id": "ishiki_mukesaki",
        "what": "同じ24時間なのに伸びる人と伸びない人の差。差は時間の量じゃなく「意識を向ける場所」。ゴールとやるべき1つに意識を向け続けた人が変わる。",
        "how": "研究データを引用しつつ、日常に落とし込む。ストーリー7枚。アンケート「今1番意識が向いてるのは？①ゴール・TODO②数字・成果③他人・SNS・できてない自分」",
        "example": ""
    },
    {
        "id": "kachiteikyo_bougyo",
        "what": "価値提供は最大の自己防衛。自分の役に立ってる人を切るクライアントはいない。価値出してない人ほど真っ先に外される。詐欺被害・逮捕・借金5000万から這い上がった体験と繋げる。",
        "how": "危機感と希望をセットで。ストーリー7枚。アンケート「価値提供力で一番弱いのは？①実績不足②また頼みたいと思わせる習慣③言語化できてない」",
        "example": ""
    },
    {
        "id": "gyaku_sanshikou",
        "what": "稼げない人の逆算は100%間違ってる。ルートを知らないやつが地図を書いてるようなもん。東大に半年で受かったのも、成功者の思考を「純算（パクり）」して脳死でToDoをこなしたから。",
        "how": "刺激的なコピーで掴む。ストーリー7枚。スタンプアクション「逆算できてる人はリアクション」",
        "example": ""
    },
    {
        "id": "mujun_game",
        "what": "仕事をゲーム感覚で楽しんでる人と毎日しんどい人の違い。「矛盾をどれだけ潰してきたか」の差。やりたいこと・言ってること・役割のズレが放置されるとしんどい。",
        "how": "ゲームの比喩を使って親しみやすく。ストーリー7枚。アンケート「一番大きい矛盾は？①時間②お金③人」",
        "example": ""
    },
    {
        "id": "rakushitai_honshitsu",
        "what": "「楽したい」って思ってる自分を責めてない？その感情の正体は「もっと自由に生きたい」という願望。やりたくないことを我慢して続けることは努力じゃなく消耗。",
        "how": "共感から入り、リフレームを促す。ストーリー6枚。スタンプアクション「楽したいと思ってる人リアクション」",
        "example": ""
    },
    {
        "id": "komyu_honshitsu",
        "what": "コミュ力＝喋りの上手さという誤解。全ての会話は「共感（感情の共有）」と「解決（ロジカル）」のグラデーション。相手が今何を求めてるかを見極めてブレンドする人が最強。",
        "how": "具体的な事例を使って解説。ストーリー8枚。質問箱「コミュニケーションで悩んでることは？」",
        "example": ""
    },
    {
        "id": "new_season",
        "what": "新しいシーズン（新生活・新月・新しい挑戦）のマインドセット。4月・新年・新月など節目に合わせた気づき。仕組みを作らないと元に戻る、具体的なToDoだけが人生を変える。",
        "how": "エネルギッシュに、前向きに。ストーリー7枚。スライダー「今の気合い度は？」",
        "example": ""
    },
    {
        "id": "ai_mainichi",
        "what": "毎日AIの情報をスタッフに共有している。AIと24時間向き合ってる？ただのチャット相手じゃなく、思考の壁打ち相手として使い倒す人が人生イージーモードになる。",
        "how": "日常的に、気軽に。ストーリー8枚。質問箱「最近AIを使って何した？面白い活用教えて」",
        "example": ""
    },
    {
        "id": "addness_member",
        "what": "アドネスのメンバー・組織の熱量について。深夜0時過ぎても土日も本気で議論してる300人。年商25億は自分一人の実績じゃなく、300人の信頼の総量。",
        "how": "温かく、リアルに。ストーリー7枚。スタンプアクション「こういう仲間がいる人リアクション」",
        "example": ""
    },
    {
        "id": "skillplus_data",
        "what": "スキルプラス生4000人のデータが示す、達成者と未達成者の決定的な違い。0→1達成率70%、月100万達成者7人に1人。特許取得のサクセスラーニングで再現性を作った。",
        "how": "データドリブン、具体的数字多め。ストーリー8枚。アンケート「今のステージは？①まだ0→1前②0→1達成した③月50万超えてる」",
        "example": ""
    },
]

USED_TOPICS_FILE = "stories/.used_topics.json"


def load_used_topics() -> list:
    """最近使ったトピックIDを読み込む"""
    if not os.path.exists(USED_TOPICS_FILE):
        return []
    with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_used_topics(used: list):
    """使ったトピックIDを保存（直近8個まで保持）"""
    os.makedirs("stories", exist_ok=True)
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(used[-8:], f, ensure_ascii=False, indent=2)


def select_topic(used_ids: list) -> dict:
    """最近使っていないトピックを選ぶ"""
    unused = [t for t in TOPIC_POOL if t["id"] not in used_ids]
    if not unused:
        # 全部使ったらリセット
        unused = TOPIC_POOL
    return random.choice(unused)


def generate_story(topic: dict) -> str:
    """Claude APIでストーリーを生成する"""
    client = anthropic.Anthropic()

    example_section = ""
    if topic.get("example"):
        example_section = f"""
【過去の実際のストーリー例（参考）】
{topic['example']}

上記のような文体・テンポ・構成を参考にしてください。
"""

    slide_count = random.randint(5, 10)

    user_message = f"""今日のインスタストーリーを作成してください。

【何を言うか】：{topic['what']}

【どう言うか】：{topic['how']}
{example_section}
注意事項：
- ストーリーは必ず{slide_count}枚構成にする
- 「。」は使わない
- 「〜なんよな」「〜なんよ」を自然に使う
- 関西弁は使わない
- CTAフレーズは入れない
- みかみの実体験（借金5000万、逮捕、年商25億、300人組織）を自然に織り交ぜる"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    return message.content[0].text


def parse_slides(content: str) -> list[str]:
    """生成されたストーリーテキストをスライド単位に分割する"""
    # 「📱 ストーリー N枚目」の区切りで分割
    parts = re.split(r'━+\s*\n📱 ストーリー \d+枚目\s*\n━+', content)
    slides = [s.strip() for s in parts if s.strip()]
    return slides


SPREADSHEET_ID = "12opzsgUNQhi9iQQJr8Ub1fkP4P9XBbpv51aEH4I6mWA"


def write_to_spreadsheet(date_str: str, slides: list[str], topic_id: str):
    """Google SheetsのA列の日付に一致する行のG列以降にスライドを書き込む"""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not creds_json:
        print("GOOGLE_SERVICE_ACCOUNT_JSON が未設定のためスプシ転記をスキップ")
        return

    creds_data = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.sheet1

    # 日付を M/D 形式に変換（スプシの形式に合わせる）
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_short = f"{date_obj.month}/{date_obj.day}"

    # A列を取得して10行目以降で日付が一致する行を探す
    a_col = sheet.col_values(1)
    target_row = None
    for i in range(9, len(a_col)):  # 10行目(index=9)以降
        if a_col[i] == date_short:
            target_row = i + 1  # gspreadは1-indexed
            break

    if target_row is None:
        print(f"日付 {date_short} に一致する行が見つからないためスキップ")
        return

    # G列(7列目)以降にスライドを書き込む
    for i, slide in enumerate(slides):
        sheet.update_cell(target_row, 7 + i, slide)

    print(f"{target_row}行目のG列以降に転記しました: {len(slides)}枚のスライド")


def save_story(content: str, date_str: str, topic_id: str) -> str:
    """ストーリーをファイルに保存する"""
    os.makedirs("stories", exist_ok=True)
    file_path = f"stories/{date_str}.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# みかみストーリー - {date_str}\n")
        f.write(f"<!-- topic: {topic_id} -->\n\n")
        f.write(content)

    return file_path


def main():
    import sys
    no_spreadsheet = "--no-spreadsheet" in sys.argv

    print(f"みかみストーリー生成開始: {date_str} ({['月','火','水','木','金','土','日'][weekday]}曜日)")

    # トピック選択
    used_ids = load_used_topics()
    topic = select_topic(used_ids)
    print(f"テーマ: [{topic['id']}] {topic['what'][:40]}...")

    # ストーリー生成
    print("Claude APIでストーリーを生成中...")
    story = generate_story(topic)

    # スライド分割
    slides = parse_slides(story)
    print(f"スライド数: {len(slides)}枚")

    # GitHubリポジトリに保存
    file_path = save_story(story, date_str, topic["id"])
    print(f"ストーリーを保存しました: {file_path}")

    # スプレッドシートへの転記（--no-spreadsheet オプションがない場合のみ）
    if no_spreadsheet:
        print("スプシ転記をスキップ（確認後に「② スプシに転記」ワークフローを実行してください）")
    else:
        write_to_spreadsheet(date_str, slides, topic["id"])

    # 使用済みトピックを更新
    used_ids.append(topic["id"])
    save_used_topics(used_ids)

    print("\n--- 生成されたストーリー ---")
    print(story)


if __name__ == "__main__":
    main()
