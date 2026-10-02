from collections import Counter
from .db import get_conn


def review_stats_for_title(title: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT rating FROM reviews WHERE title = ?",
            (title,)
        ).fetchall()

    ratings = [r[0] for r in rows if r[0] is not None]
    return {
        "title": title,
        "reviews_count": len(rows),
        "avg_rating": (sum(ratings) / len(ratings)) if ratings else None
    }


def top_reviewed(limit: int = 10) -> list[tuple[str, int]]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT title, COUNT(*) as c
            FROM reviews
            GROUP BY title
            ORDER BY c DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [(t, c) for (t, c) in rows]


def query_history(user_id: str, limit: int = 20) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT query
            FROM query_log
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
    return [r[0] for r in rows]


def user_profile(user_id: str) -> dict:
    """
    “Профиль” пользователя по лайкам: любимые жанры/тип.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT item_type, genres
            FROM likes
            WHERE user_id = ?
        """, (user_id,)).fetchall()

    type_counter = Counter()
    genre_counter = Counter()
    for item_type, genres_csv in rows:
        type_counter[item_type] += 1
        for g in genres_csv.split(","):
            g = g.strip()
            if g:
                genre_counter[g] += 1

    return {
        "likes_count": len(rows),
        "top_types": type_counter.most_common(5),
        "top_genres": genre_counter.most_common(10),
    }