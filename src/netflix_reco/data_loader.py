import requests
import pandas as pd
from .config import DATA_DIR, NETFLIX_CSV_PATH, NETFLIX_URL


def ensure_data_downloaded() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if NETFLIX_CSV_PATH.exists():
        return

    r = requests.get(NETFLIX_URL, timeout=60)
    r.raise_for_status()
    NETFLIX_CSV_PATH.write_bytes(r.content)


def load_netflix_df() -> pd.DataFrame:
    ensure_data_downloaded()
    df = pd.read_csv(NETFLIX_CSV_PATH)

    # нормализация пустых
    for col in ["director", "cast", "country", "date_added", "rating", "duration", "listed_in", "description"]:
        if col in df.columns:
            df[col] = df[col].fillna("")

    # type: Movie / TV Show
    df["type"] = df["type"].fillna("")
    df["title"] = df["title"].fillna("")
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce").fillna(0).astype(int)

    return df