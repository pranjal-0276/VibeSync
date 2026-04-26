const moodSelect = document.getElementById("moodSelect");
const weatherSelect = document.getElementById("weatherSelect");
const recommendBtn = document.getElementById("recommendBtn");
const resultsList = document.getElementById("resultsList");
const statusText = document.getElementById("statusText");
const clusterChartCanvas = document.getElementById("clusterChart");
const featureChartCanvas = document.getElementById("featureChart");

let clusterChart = null;
let featureChart = null;

async function getRecommendations() {
    const mood = moodSelect.value.trim();
    const weather = weatherSelect.value;

    if (!mood) {
        statusText.textContent = "Please select your mood first.";
        resultsList.innerHTML = "";
        return;
    }

    statusText.textContent = "Finding songs for you...";
    resultsList.innerHTML = "";

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ mood, weather })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        const recommendations = data.recommendations || [];

        if (recommendations.length === 0) {
            statusText.textContent = "No songs found. Try another mood or weather.";
            return;
        }

        statusText.textContent = "Top 5 song recommendations:";
        recommendations.forEach((song) => {
            const item = document.createElement("li");
            item.className = "song-card";
            item.innerHTML = `
                <div class="song-head">
                    <strong>${song.song_name}</strong>
                    <span class="chip">${song.weather_label}</span>
                </div>
                <div class="song-meta">Artist: ${song.artist}</div>
                <a class="spotify-link" href="${song.spotify_link}" target="_blank" rel="noopener noreferrer">
                    Open on Spotify
                </a>
            `;
            resultsList.appendChild(item);
        });
    } catch (error) {
        statusText.textContent = "Something went wrong. Please try again.";
        console.error(error);
    }
}

recommendBtn.addEventListener("click", getRecommendations);

async function loadInsights() {
    try {
        const response = await fetch("/insights");
        if (!response.ok) {
            throw new Error(`Insights error: ${response.status}`);
        }

        const data = await response.json();
        renderClusterChart(data.cluster_distribution || []);
        renderFeatureChart(data.cluster_feature_means || []);
    } catch (error) {
        console.error("Could not load ML insights:", error);
    }
}

function renderClusterChart(clusterDistribution) {
    const labels = clusterDistribution.map((item) => `Cluster ${item.cluster}`);
    const counts = clusterDistribution.map((item) => item.count);

    if (clusterChart) {
        clusterChart.destroy();
    }

    clusterChart = new Chart(clusterChartCanvas, {
        type: "doughnut",
        data: {
            labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: ["#22d3ee", "#a855f7", "#4ade80", "#f59e0b"],
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: "#e2e8f0"
                    }
                }
            }
        }
    });
}

function renderFeatureChart(clusterFeatureMeans) {
    const labels = clusterFeatureMeans.map((item) => `Cluster ${item.cluster}`);
    const energy = clusterFeatureMeans.map((item) => Number(item.energy.toFixed(2)));
    const valence = clusterFeatureMeans.map((item) => Number(item.valence.toFixed(2)));
    const danceability = clusterFeatureMeans.map((item) => Number(item.danceability.toFixed(2)));

    if (featureChart) {
        featureChart.destroy();
    }

    featureChart = new Chart(featureChartCanvas, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Energy",
                    data: energy,
                    backgroundColor: "#38bdf8"
                },
                {
                    label: "Valence",
                    data: valence,
                    backgroundColor: "#4ade80"
                },
                {
                    label: "Danceability",
                    data: danceability,
                    backgroundColor: "#f472b6"
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    ticks: {
                        color: "#cbd5e1"
                    },
                    grid: {
                        color: "rgba(203, 213, 225, 0.15)"
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        color: "#cbd5e1"
                    },
                    grid: {
                        color: "rgba(203, 213, 225, 0.15)"
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#e2e8f0"
                    }
                }
            }
        }
    });
}

loadInsights();
