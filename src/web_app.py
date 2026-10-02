from flask import Flask, request, render_template
from netflix_reco.data_loader import load_netflix_df
from netflix_reco.recommender import Recommender
from netflix_reco.db import init_db, log_query
from netflix_reco.stats import user_profile

app = Flask(__name__)

init_db()
df = load_netflix_df()
rec = Recommender(df)

USER_ID = "web_user"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/search")
def search():
    q = request.args.get("q", "").strip()
    mode = request.args.get("mode", "best")
    if not q:
        return render_template("index.html", error="Введите запрос")

    log_query(USER_ID, q)
    prof = user_profile(USER_ID)
    top = rec.recommend(q, top_n=5, mode=mode, user_profile=prof)
    items = [row.to_dict() for _, row in top.iterrows()]
    return render_template("results.html", q=q, items=items, mode=mode)


if __name__ == "__main__":
    app.run(debug=True)