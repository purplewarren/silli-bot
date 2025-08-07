# bot/puller.py
import os
import asyncio
import json
from datetime import datetime
from loguru import logger
import aiohttp

from .models import EventRecord, PwaSessionReport
from .storage import Storage
from .families import FamiliesStore
from .handlers import convert_pwa_to_bot_format  # reuse same converter

RELAY_PULL_URL = os.getenv("RELAY_PULL_URL", "https://silli-auto-ingest-relay.silli-tg-bot.workers.dev/pull")
RELAY_SECRET   = os.getenv("RELAY_SECRET")
PULL_INTERVAL  = int(os.getenv("RELAY_PULL_INTERVAL_S", "15"))
ADMIN_CHAT_ID  = os.getenv("ADMIN_CHAT_ID")  # optional: notify on repeated failures



storage = Storage()
families = FamiliesStore()

async def pull_for_chat(sess: aiohttp.ClientSession, bot, chat_id: int, limit: int = 5) -> int:
    params = {"chat_id": str(chat_id), "limit": str(limit)}
    headers = {"X-Auth": RELAY_SECRET} if RELAY_SECRET else {}
    
    async with sess.get(RELAY_PULL_URL, params=params, headers=headers, timeout=20) as r:
        if r.status != 200:
            txt = await r.text()
            logger.warning(f"Relay pull failed for {chat_id}: {r.status} {txt}")
            return -1
        data = await r.json()

    items = data.get("items", [])
    count = 0
    for item in items:
        report_raw = item.get("data") or {}
        try:
            converted = convert_pwa_to_bot_format(report_raw)
            report = PwaSessionReport(**converted)

            # ---- Replay guard: skip if we already ingested this session ----
            existing = storage.get_events(report.family_id)
            if any(e.session_id == report.session_id and e.event == "ingest_session_report" for e in existing):
                logger.info(f"Skip duplicate session {report.session_id} for {report.family_id}")
                continue

            # Prefer long score
            long_score = None
            if isinstance(report.score, dict):
                long_score = report.score.get("long") or report.score.get("mid") or report.score.get("short")

            event = EventRecord(
                ts=datetime.now(),
                family_id=report.family_id,
                session_id=report.session_id,
                phase=report.mode,
                actor="parent",
                event="ingest_session_report",
                labels=report.badges,
                features=report.features_summary,
                score=int(long_score) if isinstance(long_score, (int, float)) else None,
                suggestion_id=None,
            )
            storage.append_event(event)

            # Enhanced session confirmation message
            short_id = report.session_id.split("_")[-1] if "_" in report.session_id else report.session_id[-8:]
            duration_min = int(report.duration_s // 60)
            duration_sec = int(report.duration_s % 60)
            
            await bot.send_message(
                chat_id=int(chat_id),
                text=(
                    f"✅ Session received: #{short_id}\n"
                    f"⏱ {duration_min:02d}:{duration_sec:02d} min\n"
                    f"Score: {long_score}/100\n"
                    f"Badges: {', '.join(report.badges) if report.badges else '—'}\n"
                    f"Use /list to view more."
                ),
            )
            count += 1
        except Exception as e:
            logger.error(f"Error processing pulled session for chat {chat_id}: {e}")
    return count

async def start_pull_loop(bot):
    logger.info("Starting relay pull loop…")
    consecutive_failures = 0
    while True:
        try:
            roster = families.list()
            if not roster:
                await asyncio.sleep(PULL_INTERVAL)
                continue

            total = 0
            async with aiohttp.ClientSession() as sess:
                for i, chat_id in enumerate(roster):
                    n = await pull_for_chat(sess, bot, chat_id, limit=5)
                    if n >= 0:
                        total += n
                        consecutive_failures = 0  # success resets failures
                    else:
                        consecutive_failures += 1
                    # gentle spacing between chats
                    await asyncio.sleep(0.75)

            if total:
                logger.info(f"Ingested {total} session(s) from relay")

            # Escalate after repeated failures
            if ADMIN_CHAT_ID and consecutive_failures >= 3:
                try:
                    await bot.send_message(int(ADMIN_CHAT_ID),
                        f"⚠️ Relay pull is failing repeatedly (count={consecutive_failures}). Check Worker/KV/secret.")
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")

        except Exception as e:
            logger.error(f"Pull loop error: {e}")
            consecutive_failures += 1

        await asyncio.sleep(PULL_INTERVAL) 