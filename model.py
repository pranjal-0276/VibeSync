import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote_plus
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
class SongRecommender:
    def __init__(self, dataset_path: str = "data/songs.csv") -> None:
        self.dataset_path = Path(dataset_path)
        self.df = self._load_dataset()
        self.kmeans = None
        self.mood_classifier = None
        self.mood_map = {
            "sad": "low_energy",
            "happy": "high_energy",
            "angry": "high_energy",
            "calm": "low_energy",
            "stressed": "low_energy",
            "excited": "high_energy",
            "relaxed": "low_energy",
            "romantic": "mid_energy",
            "tired": "low_energy",
            "motivated": "high_energy",
        }
        self._train_models()

    def _load_dataset(self) -> pd.DataFrame:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")

        df = pd.read_csv(self.dataset_path)

        required_columns = [
            "song_name",
            "artist",
            "energy",
            "tempo",
            "valence",
            "danceability",
        ]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if "weather_label" not in df.columns:
            df["weather_label"] = "Any"

        numeric_columns = ["energy", "tempo", "valence", "danceability"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=numeric_columns).reset_index(drop=True)
        return df

    def _train_models(self) -> None:
        """Train K-Means clusters and a simple mood -> cluster classifier."""
        features = self.df[["energy", "tempo", "valence", "danceability"]].to_numpy()

        self.kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        self.df["cluster"] = self.kmeans.fit_predict(features)

        mood_training_data = self._build_mood_training_data()
        mood_features = np.array([item["features"] for item in mood_training_data])
        mood_labels = np.array([item["cluster"] for item in mood_training_data])

        self.mood_classifier = LogisticRegression(max_iter=300, random_state=42)
        self.mood_classifier.fit(mood_features, mood_labels)

    def _mood_to_feature_vector(self, mood_text: str) -> np.ndarray:
        """
        Convert mood text into a simple numeric feature vector:
        [energy_hint, valence_hint]
        """
        mood = mood_text.lower().strip()

        energy = 0.5
        valence = 0.5

        if re.search(r"\b(sad|down|upset|lonely|heartbroken)\b", mood):
            energy, valence = 0.2, 0.2
        elif re.search(r"\b(happy|joy|great|good|awesome)\b", mood):
            energy, valence = 0.8, 0.85
        elif re.search(r"\b(angry|mad|furious)\b", mood):
            energy, valence = 0.9, 0.25
        elif re.search(r"\b(calm|relaxed|peaceful)\b", mood):
            energy, valence = 0.3, 0.65
        elif re.search(r"\b(tired|sleepy|exhausted)\b", mood):
            energy, valence = 0.15, 0.4
        elif re.search(r"\b(excited|pumped|motivated)\b", mood):
            energy, valence = 0.9, 0.8

        return np.array([energy, valence], dtype=float)

    def _build_mood_training_data(self) -> List[Dict]:
        seed_examples = [
            "sad",
            "happy",
            "angry",
            "calm",
            "tired",
            "excited",
            "relaxed",
            "stressed",
            "motivated",
            "romantic",
        ]

        items = []
        for mood_word in seed_examples:
            mood_vec = self._mood_to_feature_vector(mood_word)
            expanded_vec = np.array(
                [
                    mood_vec[0],
                    70 + mood_vec[0] * 80,  
                    mood_vec[1],
                    0.3 + mood_vec[0] * 0.6,  
                ],
                dtype=float,
            )
            cluster_label = int(self.kmeans.predict([expanded_vec])[0])
            items.append({"features": mood_vec, "cluster": cluster_label})

        return items

    def _normalize_weather(self, weather: str) -> str:
        if not weather:
            return "Any"
        return weather.strip().capitalize()

    def _needs_mood_improvement(self, mood_text: str) -> bool:
        mood = mood_text.lower().strip()
        low_moods = {"sad", "down", "upset", "stressed", "angry", "tired", "lonely"}
        return any(word in mood for word in low_moods)

    def _build_spotify_link(self, song_name: str, artist: str) -> str:
        query = quote_plus(f"{song_name} {artist}")
        return f"https://open.spotify.com/search/{query}"

    def recommend_songs(self, mood: str, weather: str, top_n: int = 5) -> List[Dict]:
        if not mood:
            mood = "neutral"

        mood_vec = self._mood_to_feature_vector(mood)
        predicted_cluster = int(self.mood_classifier.predict([mood_vec])[0])
        normalized_weather = self._normalize_weather(weather)
        candidates = self.df[self.df["cluster"] == predicted_cluster].copy()

        if normalized_weather and normalized_weather != "Any":
            weather_filtered = candidates[
                (candidates["weather_label"].str.lower() == normalized_weather.lower())
                | (candidates["weather_label"].str.lower() == "any")
            ]
            if not weather_filtered.empty:
                candidates = weather_filtered

        if self._needs_mood_improvement(mood):
            candidates = candidates.sort_values(by="valence", ascending=True)
        else:
            candidates = candidates.sort_values(
                by=["valence", "energy"], ascending=[False, False]
            )

        if candidates.empty:
            candidates = self.df.copy().sort_values(by="valence", ascending=False)

        results = candidates.head(top_n)[["song_name", "artist", "weather_label", "cluster"]]
        recommendations = results.to_dict(orient="records")

        for item in recommendations:
            item["spotify_link"] = self._build_spotify_link(
                item["song_name"], item["artist"]
            )

        return recommendations

    def get_ml_insights(self) -> Dict:
        cluster_counts = (
            self.df["cluster"]
            .value_counts()
            .sort_index()
            .rename_axis("cluster")
            .reset_index(name="count")
        )

        cluster_feature_means = (
            self.df.groupby("cluster")[["energy", "valence", "danceability", "tempo"]]
            .mean()
            .reset_index()
        )

        cluster_distribution = [
            {"cluster": int(row["cluster"]), "count": int(row["count"])}
            for _, row in cluster_counts.iterrows()
        ]

        cluster_feature_rows = []
        for _, row in cluster_feature_means.iterrows():
            cluster_feature_rows.append(
                {
                    "cluster": int(row["cluster"]),
                    "energy": float(row["energy"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "tempo": float(row["tempo"]),
                }
            )

        return {
            "cluster_distribution": cluster_distribution,
            "cluster_feature_means": cluster_feature_rows,
        }
