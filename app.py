from flask import Flask, jsonify, render_template, request

from model import SongRecommender

app = Flask(__name__)
recommender = SongRecommender()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    """
    API endpoint:
    Input JSON: {"mood": "...", "weather": "..."}
    Output JSON: {"recommendations": [...]}
    """
    data = request.get_json(silent=True) or {}
    mood = data.get("mood", "").strip()
    weather = data.get("weather", "Any").strip()

    recommendations = recommender.recommend_songs(mood=mood, weather=weather, top_n=5)
    return jsonify({"recommendations": recommendations})


@app.route("/insights", methods=["GET"])
def insights():
    """Return lightweight ML insights for frontend charts."""
    return jsonify(recommender.get_ml_insights())


if __name__ == "__main__":
    # debug=True for local development.
    app.run(debug=True)
