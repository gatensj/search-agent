# search-agent — Phases 1 & 2

A sandboxed research agent (Claude Agent SDK) you can drive from your terminal
or your iPhone via Telegram. The agent can only WebSearch and WebFetch — no
shell, no file writes — with hard per-task caps on turns and spend.

## Phase 1 — laptop CLI

```bash
# inside your project directory / venv (Python 3.10+ required)
pip install -r requirements.txt
cp .env.example .env        # then edit it: paste your ANTHROPIC_API_KEY

python cli.py "list yoga studios in Center City Philadelphia and today's class times"
```

You'll see `[agent] …` progress lines as it works, then the final answer with
turn count and actual dollar cost.

**Before anything else:** set a monthly spend limit on your API key in the
platform console. The code also caps each task at $0.50 (`AGENT_MAX_BUDGET_USD`)
and 25 turns, but belt-and-suspenders.

## Phase 2 — Telegram bot (laptop first, then droplet)

1. In Telegram, message **@BotFather** → `/newbot` → follow prompts → copy the
   token into `.env` as `TELEGRAM_BOT_TOKEN`.
2. `python bot.py`, then send `/start` to your bot from your phone. It replies
   with your **chat id**.
3. Put that number in `.env` as `TELEGRAM_ALLOWED_CHAT_ID`, restart the bot.
   From now on only your account can give it tasks.
4. Text it a research task. It acknowledges, shows "typing…", and messages you
   the result (auto-split if long).

### Droplet deployment

```bash
# on the droplet (Ubuntu)
sudo apt update && sudo apt install -y python3-venv
git clone <your repo> search-agent && cd search-agent   # or rsync the folder
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env                        # keys + chat id

# install as a service (edit YOUR_USER in searchagent.service first)
sudo cp searchagent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now searchagent
journalctl -u searchagent -f                             # watch logs
```

The bot uses long-polling (outbound HTTPS only), so no ports to open and no
webhook/TLS setup needed. Works on the cheapest droplet.

## How it behaves

- If your request is too vague, the agent replies starting with `QUESTION:`
  instead of guessing — answer it in a follow-up message (each message is a
  fresh task for now; conversational memory is Phase 3).
- It's instructed to cite sources and flag stale-looking data, and to admit
  when a site blocked it rather than invent prices/schedules.
- One task at a time; a second message while busy gets a "hang on".

## Knobs (`.env`)

| var | default | meaning |
|---|---|---|
| `AGENT_MODEL` | `sonnet` | try `haiku` for cheap routine checks |
| `AGENT_MAX_TURNS` | `25` | search/fetch loop ceiling per task |
| `AGENT_MAX_BUDGET_USD` | `0.50` | hard dollar cap per task |

## Phase 3 preview (not built yet)

Scheduled SAM.gov / Grants.gov / PHLContracts polling with dedupe (SQLite),
relevance scoring, and unprompted "new opportunity" pings to your phone.
