import numpy as np
import pandas as pd
from .scorer import WeightedScorer
from .preprocess import parse_genres, parse_duration_to_minutes


class Recommender:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True)
        self.scorer = WeightedScorer(self.df)

    def find_by_title(self, title: str, limit: int = 10) -> pd.DataFrame:
        t = (title or "").strip().lower()
        mask = self.df["title"].str.lower().str.contains(t, na=False)
        return self.df[mask].head(limit)

    def recommend(
        self,
        query: str,
        top_n: int = 5,
        mode: str = "best",   # best / weak
        user_profile: dict | None = None
    ) -> pd.DataFrame:
        scores, max_score = self.scorer.score_all(query, user_profile=user_profile)

        res = self.df.copy()
        res["score"] = scores
        res["compatibility_pct"] = (res["score"] / max_score * 100.0).clip(0, 100)

        res = res.sort_values("score", ascending=(mode != "best"))
        return res.head(top_n)

    def filter_by_ranges(
        self,
        year_from: int | None = None,
        year_to: int | None = None,
        min_minutes: int | None = None,
        max_minutes: int | None = None,
        only_type: str | None = None,  # "Movie" / "TV Show"
        limit: int = 50
    ) -> pd.DataFrame:
        df = self.df.copy()

        if only_type:
            df = df[df["type"] == only_type]

        if year_from is not None and year_to is not None:
            df = df[(df["release_year"] >= year_from) & (df["release_year"] <= year_to)]

        if min_minutes is not None and max_minutes is not None:
            mins = df["duration"].apply(parse_duration_to_minutes)
            df = df[mins.notna()]
            mins = df["duration"].apply(parse_duration_to_minutes)
            df = df[(mins >= min_minutes) & (mins <= max_minutes)]

        return df.head(limit)

    @staticmethod
    def format_item(row) -> str:
        genres = ", ".join(parse_genres(row.get("listed_in", ""))[:5])
        return (
            f"{row.get('title')} ({row.get('type')}, {row.get('release_year')})\n"
            f"Жанры: {genres}\n"
            f"Длительность: {row.get('duration')} | Рейтинг: {row.get('rating')}\n"
            f"Совместимость: {row.get('compatibility_pct'):.1f}% | Баллы: {row.get('score'):.1f}\n"
            f"Описание: {str(row.get('description',''))[:180]}..."
        )