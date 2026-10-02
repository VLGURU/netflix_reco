import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from netflix_reco.data_loader import load_netflix_df
from netflix_reco.recommender import Recommender
from netflix_reco.db import init_db, log_query, add_like, add_review
from netflix_reco.stats import user_profile, user_profile as profile_stats, review_stats_for_title
from netflix_reco.sound import beep

load_dotenv()

init_db()
df = load_netflix_df()
rec = Recommender(df)


def uid(update: Update) -> str:
    return str(update.effective_chat.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я рекомендую фильмы/сериалы из датасета Netflix.\n"
        "Пиши запрос текстом (например: 'комедия новый фильм 2018-2022 80-120 мин').\n\n"
        "Команды:\n"
        "/find <название>\n"
        "/weak <запрос>\n"
        "/like <точное название>\n"
        "/review <title> | <text> | <1-5>\n"
        "/stats <title>\n"
        "/profile"
    )


async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Формат: /find <название>")
        return
    found = rec.find_by_title(text, limit=10)
    if found.empty:
        await update.message.reply_text("Ничего не нашлось.")
        return
    msg = "\n".join([f"- {r['title']} ({r['type']}, {r['release_year']}) | {r['duration']} | {r['listed_in']}"
                     for _, r in found.iterrows()])
    await update.message.reply_text(msg[:3500])


async def weak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).strip()
    if not q:
        await update.message.reply_text("Формат: /weak <запрос>")
        return
    user_id = uid(update)
    log_query(user_id, q)
    prof = user_profile(user_id)
    top = rec.recommend(q, top_n=5, mode="weak", user_profile=prof)
    parts = []
    for _, row in top.iterrows():
        parts.append(rec.format_item(row))
        parts.append("-" * 30)
    await update.message.reply_text("\n".join(parts)[:3500])


async def like_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = " ".join(context.args).strip()
    if not title:
        await update.message.reply_text("Формат: /like <точное название>")
        return

    found = rec.find_by_title(title, limit=1)
    if found.empty:
        await update.message.reply_text("Не нашёл. Сначала попробуйте /find <часть названия>.")
        return

    row = found.iloc[0]
    add_like(
        user_id=uid(update),
        show_id=row["show_id"],
        title=row["title"],
        item_type=row["type"],
        genres_csv=row["listed_in"],
    )
    await update.message.reply_text("Лайк сохранён. Будущие рекомендации будут лучше под вас (обучение).")


async def review_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = " ".join(context.args).strip()
    if "|" not in payload:
        await update.message.reply_text("Формат: /review <title> | <text> | <1-5 (необязательно)>")
        return
    parts = [p.strip() for p in payload.split("|")]
    title = parts[0]
    text = parts[1] if len(parts) > 1 else ""
    rating = None
    if len(parts) > 2 and parts[2]:
        try:
            rating = int(parts[2])
        except ValueError:
            rating = None

    add_review(uid(update), title, rating, text)
    await update.message.reply_text("Отзыв сохранён.")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = " ".join(context.args).strip()
    if not title:
        await update.message.reply_text("Формат: /stats <title>")
        return
    st = review_stats_for_title(title)
    await update.message.reply_text(str(st))


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = profile_stats(uid(update))
    await update.message.reply_text(str(st))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q:
        return
    user_id = uid(update)
    log_query(user_id, q)
    prof = user_profile(user_id)
    top = rec.recommend(q, top_n=5, mode="best", user_profile=prof)

    beep()
    parts = []
    for _, row in top.iterrows():
        parts.append(rec.format_item(row))
        parts.append("-" * 30)
    await update.message.reply_text("\n".join(parts)[:3500])


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Нет TELEGRAM_BOT_TOKEN. Создайте .env и добавьте токен.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find_cmd))
    app.add_handler(CommandHandler("weak", weak_cmd))
    app.add_handler(CommandHandler("like", like_cmd))
    app.add_handler(CommandHandler("review", review_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling()


if __name__ == "__main__":
    main()