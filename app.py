import logging, math
from flask import Flask, render_template, request, url_for, redirect

from railway_app_v2.fetchers.erail import ErailFetcher
from railway_app_v2.fetchers.overpass import OverpassFetcher

app = Flask(__name__, static_folder='../static', template_folder='../templates')
logging.basicConfig(level=logging.INFO)

PAGE_SIZE = 10


@app.route("/")
def home():
    return redirect(url_for("trains"))

@app.route("/trains")
def trains():
    erail = ErailFetcher()
    all_trains = erail.fetch("VN", 100) or []
    all_trains = sorted(all_trains, key=lambda t: getattr(t, "eta_at_crossing", None) or 9e18)
    next_train = all_trains[0] if all_trains else None

    page = max(1, int(request.args.get("page", 1)))
    total_pages = max(1, math.ceil(len(all_trains) / PAGE_SIZE))
    page = min(page, total_pages)
    start, end = (page - 1) * PAGE_SIZE, (page - 1) * PAGE_SIZE + PAGE_SIZE
    page_trains = all_trains[start:end]

    def build_pages(current, total_pages, window=1):
        pages = []
        for p in range(1, total_pages + 1):
            if p == 1 or p == total_pages or abs(p - current) <= window:
                pages.append(p)
            elif pages and pages[-1] != "...":
                pages.append("...")
        return pages

    pages = build_pages(page, total_pages)
    return render_template("index.html",
                           trains=page_trains, next_train=next_train,
                           page=page, total_pages=total_pages, pages=pages)

@app.route("/crossings")
def crossings():
    data = OverpassFetcher.fetch_crossings()
    show_all = request.args.get("all") == "1"
    show_list = data["crossings"] if show_all else data["crossings"][:5]
    
    return render_template("crossings.html",
                           station=data["station"],
                           crossings=show_list,
                           total=data["total"],
                           showing=len(show_list),
                           show_all=show_all)

@app.route("/help")
def help_page():
    return render_template("help.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)