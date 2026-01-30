import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

if not load_dotenv():
    load_dotenv(".env.example")

if "SLACK_BOT_TOKEN" not in os.environ or "SLACK_APP_TOKEN" not in os.environ:
    raise RuntimeError(
        "Missing SLACK_BOT_TOKEN/SLACK_APP_TOKEN. "
        "Create a .env file (copy from .env.example) or set env vars."
    )

BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

COMMAND_NAME = os.getenv("COMMAND_NAME", "/unreacted")
LOOKBACK_LIMIT = int(os.getenv("LOOKBACK_LIMIT", "200"))

app = App(token=BOT_TOKEN)

def has_user_reaction(msg: dict, user_id: str) -> bool:
    """
    msg["reactions"] の users に user_id が含まれるか
    """
    reactions = msg.get("reactions", []) or []
    for r in reactions:
        users = r.get("users", []) or []
        if user_id in users:
            return True
    return False

@app.command(COMMAND_NAME)
def cmd_unreacted(ack, body, client, respond, logger):
    ack()

    channel_id = body["channel_id"]

    # Botの user_id を取得
    requester_id = body["user_id"]
    mention_token = f"<@{requester_id}>"

    # チャンネルの最新メッセージを取得
    hist = client.conversations_history(channel=channel_id, limit=LOOKBACK_LIMIT)
    messages = hist.get("messages", []) or []

    targets = []
    for m in messages:
        text = m.get("text", "") or ""

        # Botへのメンションが含まれているか
        if mention_token not in text:
            continue

        # 自分がリアクション済みならスキップ
        if has_user_reaction(m, requester_id):
            continue

        # パーマリンク生成
        try:
            link = client.chat_getPermalink(channel=channel_id, message_ts=m["ts"])["permalink"]
        except Exception as e:
            logger.warning(f"chat_getPermalink failed: {e}")
            link = "(permalink failed)"

        user = m.get("user", "unknown")
        snippet = text.replace("\n", " ")
        if len(snippet) > 90:
            snippet = snippet[:90] + "…"

        targets.append(f"• <@{user}>: <{link}|link>  {snippet}")

    if not targets:
        respond("未反応メンションは見つからなかった")
        return

    header = "*未反応メンション一覧（リアクション未押し）*"
    respond(header + "\n" + "\n".join(targets))


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()

