from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.sqlite3"

NETFLIX_URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2021/2021-04-20/netflix_titles.csv"
NETFLIX_CSV_PATH = DATA_DIR / "netflix_titles.csv"


@dataclass
class Weights:
    # “взвешенный перебор” — основные коэффициенты
    type_match: int = 35
    genre_match: int = 50
    keyword_match: int = 20
    year_match: int = 20
    duration_match: int = 20
    rating_family_match: int = 15
    tfidf_similarity: int = 40

    # персонализация (обучение по лайкам)
    user_genre_boost: int = 25
    user_type_boost: int = 10