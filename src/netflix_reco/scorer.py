import re
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import Weights
from .preprocess import normalize_text, parse_genres, parse_duration_to_minutes


GENRE_KEYWORDS_RU_TO_EN = {
    "комедия": ["Comedies", "Stand-Up Comedy", "TV Comedies"],
    "драма": ["Dramas", "TV Dramas"],
    "ужасы": ["Horror Movies"],
    "триллер": ["Thrillers", "TV Thrillers"],
    "детектив": ["Crime TV Shows", "Crime Movies", "Docuseries"],
    "документал": ["Documentaries", "Docuseries"],
    "семейн": ["Children & Family Movies", "Kids' TV", "Family Movies"],
    "аниме": ["Anime Features", "Anime Series"],
    "боевик": ["Action & Adventure"],
    "романтик": ["Romantic Movies", "Romantic TV Shows"],
    "фантаст": ["Sci-Fi & Fantasy", "TV Sci-Fi & Fantasy"],
}

TYPE_KEYWORDS = {
    "movie": ["фильм", "кино", "movie", "film"],
    "tv show": ["сериал", "тв", "show", "series", "tv"],
}

FAMILY_RATINGS = {"G", "PG", "TV-G", "TV-PG", "TV-Y", "TV-Y7"}


@dataclass
class QueryParsed:
    q: str
    want_type: str | None
    want_genres: list[str]
    year_from: int | None
    year_to: int | None
    min_minutes: int | None
    max_minutes: int | None
    wants_family: bool
    wants_new: bool
    wants_old: bool
    wants_long: bool
    wants_short: bool


def parse_query(query: str) -> QueryParsed:
    q = normalize_text(query)

    # тип
    want_type = None
    for t, keys in TYPE_KEYWORDS.items():
        if any(k in q for k in keys):
            want_type = "Movie" if t == "movie" else "TV Show"
            break

    # жанры по ключевым словам
    want_genres = []
    for ru_part, en_list in GENRE_KEYWORDS_RU_TO_EN.items():
        if ru_part in q:
            want_genres.extend(en_list)

    # диапазон лет: "2015-2020" или "от 2015 до 2020"
    year_from = year_to = None
    m = re.search(r"(\d{4})\s*[-–]\s*(\d{4})", q)
    if not m:
        m = re.search(r"от\s*(\d{4})\s*до\s*(\d{4})", q)
    if m:
        year_from, year_to = int(m.group(1)), int(m.group(2))

    # диапазон минут: "80-120 мин"
    min_minutes = max_minutes = None
    md = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*мин", q)
    if md:
        min_minutes, max_minutes = int(md.group(1)), int(md.group(2))

    wants_family = ("семейн" in q) or ("дет" in q and "для" in q)
    wants_new = "нов" in q or "свеж" in q
    wants_old = "стар" in q or "классик" in q
    wants_long = "длин" in q
    wants_short = "корот" in q

    return QueryParsed(
        q=q,
        want_type=want_type,
        want_genres=want_genres,
        year_from=year_from,
        year_to=year_to,
        min_minutes=min_minutes,
        max_minutes=max_minutes,
        wants_family=wants_family,
        wants_new=wants_new,
        wants_old=wants_old,
        wants_long=wants_long,
        wants_short=wants_short,
    )


class WeightedScorer:
    def __init__(self, df, weights: Weights = Weights()):
        self.df = df.copy()
        self.w = weights

        # TF-IDF по объединённому тексту
        texts = []
        for _, row in self.df.iterrows():
            combined = " ".join([
                str(row.get("title", "")),
                str(row.get("listed_in", "")),
                str(row.get("description", "")),
                str(row.get("cast", "")),
                str(row.get("director", "")),
            ])
            texts.append(normalize_text(combined))

        self.vectorizer = TfidfVectorizer(max_features=30000)
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def _dynamic_max_score(self, qp: QueryParsed) -> int:
        mx = 0
        if qp.want_type:
            mx += self.w.type_match
        if qp.want_genres:
            mx += self.w.genre_match * len(set(qp.want_genres))
        if qp.year_from is not None and qp.year_to is not None:
            mx += self.w.year_match
        if qp.min_minutes is not None and qp.max_minutes is not None:
            mx += self.w.duration_match
        if qp.wants_family:
            mx += self.w.rating_family_match
        if qp.wants_new or qp.wants_old or qp.wants_long or qp.wants_short:
            mx += self.w.keyword_match
        # всегда добавляем “умную часть”
        mx += self.w.tfidf_similarity
        return max(mx, 1)

    def score_all(self, query: str, user_profile: dict | None = None) -> tuple[np.ndarray, int]:
        qp = parse_query(query)
        max_score = self._dynamic_max_score(qp)

        q_vec = self.vectorizer.transform([qp.q])
        sims = cosine_similarity(q_vec, self.tfidf_matrix).ravel()  # 0..1

        scores = np.zeros(len(self.df), dtype=float)

        for i, (_, row) in enumerate(self.df.iterrows()):
            s = 0

            # type match
            if qp.want_type and row.get("type") == qp.want_type:
                s += self.w.type_match

            # genre match
            item_genres = parse_genres(row.get("listed_in", ""))
            if qp.want_genres and item_genres:
                for want_g in set(qp.want_genres):
                    if want_g in item_genres:
                        s += self.w.genre_match

            # year range
            y = int(row.get("release_year", 0))
            if qp.year_from is not None and qp.year_to is not None:
                if qp.year_from <= y <= qp.year_to:
                    s += self.w.year_match

            # duration range (movies)
            mins = parse_duration_to_minutes(row.get("duration", ""))
            if qp.min_minutes is not None and qp.max_minutes is not None and mins is not None:
                if qp.min_minutes <= mins <= qp.max_minutes:
                    s += self.w.duration_match

            # “новый/старый/длинный/короткий” (через признаки)
            if qp.wants_new and y >= 2018:
                s += self.w.keyword_match
            if qp.wants_old and y != 0 and y <= 2005:
                s += self.w.keyword_match
            if qp.wants_long and mins is not None and mins >= 130:
                s += self.w.keyword_match
            if qp.wants_short and mins is not None and mins <= 85:
                s += self.w.keyword_match

            # family rating
            if qp.wants_family:
                rating = str(row.get("rating", "")).strip()
                if rating in FAMILY_RATINGS:
                    s += self.w.rating_family_match

            # TF-IDF similarity
            s += float(sims[i] * self.w.tfidf_similarity)

            # персонализация: если есть профиль пользователя
            if user_profile:
                # любимый тип
                if user_profile.get("top_types"):
                    fav_types = {t for t, _ in user_profile["top_types"]}
                    if row.get("type") in fav_types:
                        s += self.w.user_type_boost

                # любимые жанры
                if user_profile.get("top_genres"):
                    fav_genres = {g for g, _ in user_profile["top_genres"]}
                    if any(g in fav_genres for g in item_genres):
                        s += self.w.user_genre_boost

            scores[i] = s

        return scores, max_score