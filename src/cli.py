from netflix_reco.data_loader import load_netflix_df
from netflix_reco.recommender import Recommender
from netflix_reco.db import init_db, log_query, add_review, add_like
from netflix_reco.stats import review_stats_for_title, user_profile, query_history
from netflix_reco.sound import beep


HELP = """
Команды:
  query <текст>               - рекомендация TOP-5
  weak <текст>                - TOP-5 "слабых" (минимальное совпадение)
  find <название>             - поиск по названию
  range year 2015 2020        - фильтр по годам
  range min 80 120            - фильмы по длительности (минуты)
  review <title> | <text>     - отзыв (оценка спросит отдельно)
  stats <title>               - статистика по отзывам
  profile                     - ваш профиль по лайкам
  history                     - история ваших запросов
  like <точное название>      - лайкнуть (для обучения)
  help                        - помощь
  exit                        - выход
"""


def main():
    init_db()
    df = load_netflix_df()
    rec = Recommender(df)

    user_id = "cli_user"  # для персонализации (в Telegram будет chat_id)

    print("Netflix Recommender (имитация нейросети).")
    print(HELP)

    while True:
        cmd = input("\n> ").strip()
        if not cmd:
            continue
        if cmd == "exit":
            break
        if cmd == "help":
            print(HELP)
            continue

        if cmd.startswith("query "):
            q = cmd[len("query "):]
            log_query(user_id, q)
            prof = user_profile(user_id)
            top = rec.recommend(q, top_n=5, mode="best", user_profile=prof)
            beep()
            for _, row in top.iterrows():
                print("-" * 60)
                print(rec.format_item(row))
            continue

        if cmd.startswith("weak "):
            q = cmd[len("weak "):]
            log_query(user_id, q)
            prof = user_profile(user_id)
            top = rec.recommend(q, top_n=5, mode="weak", user_profile=prof)
            for _, row in top.iterrows():
                print("-" * 60)
                print(rec.format_item(row))
            continue

        if cmd.startswith("find "):
            t = cmd[len("find "):]
            found = rec.find_by_title(t, limit=10)
            if found.empty:
                print("Ничего не найдено.")
            else:
                for _, row in found.iterrows():
                    print(f"- {row['title']} ({row['type']}, {row['release_year']}) | {row['duration']} | {row['listed_in']}")
            continue

        if cmd.startswith("range "):
            parts = cmd.split()
            # range year 2015 2020
            # range min 80 120
            try:
                kind = parts[1]
                a = int(parts[2])
                b = int(parts[3])
            except Exception:
                print("Пример: range year 2015 2020  ИЛИ  range min 80 120")
                continue

            if kind == "year":
                res = rec.filter_by_ranges(year_from=a, year_to=b, limit=20)
            elif kind == "min":
                res = rec.filter_by_ranges(min_minutes=a, max_minutes=b, only_type="Movie", limit=20)
            else:
                print("kind должен быть year или min")
                continue

            for _, row in res.iterrows():
                print(f"- {row['title']} ({row['type']}, {row['release_year']}) | {row['duration']} | {row['listed_in']}")
            continue

        if cmd.startswith("review "):
            payload = cmd[len("review "):]
            if "|" not in payload:
                print("Формат: review <title> | <text>")
                continue
            title, text = [x.strip() for x in payload.split("|", 1)]
            rating_s = input("Оценка 1-5 (Enter если без оценки): ").strip()
            rating = int(rating_s) if rating_s else None
            add_review(user_id, title, rating, text)
            print("Отзыв сохранён.")
            continue

        if cmd.startswith("stats "):
            title = cmd[len("stats "):].strip()
            st = review_stats_for_title(title)
            print(st)
            continue

        if cmd == "profile":
            print(user_profile(user_id))
            continue

        if cmd == "history":
            print(query_history(user_id, limit=20))
            continue

        if cmd.startswith("like "):
            title = cmd[len("like "):].strip()
            found = rec.find_by_title(title, limit=1)
            if found.empty:
                print("Не нашёл точное совпадение. Попробуйте find <часть названия>.")
                continue
            row = found.iloc[0]
            add_like(
                user_id=user_id,
                show_id=row["show_id"],
                title=row["title"],
                item_type=row["type"],
                genres_csv=row["listed_in"],
            )
            print(f"Лайк сохранён: {row['title']}. Это влияет на будущие рекомендации (обучение).")
            continue

        print("Неизвестная команда. Напишите help.")


if __name__ == "__main__":
    main()