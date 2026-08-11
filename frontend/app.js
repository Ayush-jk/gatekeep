const INSTANCES = ["http://localhost:9001", "http://localhost:9002", "http://localhost:9003"];

let chart = null;

function initChart() {
    const ctx = document.getElementById("live-chart");
    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Allowed",
                    data: [],
                    borderColor: "#cf8659",
                    backgroundColor: "rgba(226,161,122,0.15)",
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                },
                {
                    label: "Blocked",
                    data: [],
                    borderColor: "#c56b5c",
                    backgroundColor: "rgba(197,107,92,0.1)",
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                },
            ],
        },
        options: {
            animation: false,
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            plugins: { legend: { position: "bottom" } },
        },
    });
}

function resetStats() {
    document.getElementById("stat-sent").textContent = "0";
    document.getElementById("stat-allowed").textContent = "0";
    document.getElementById("stat-permit").textContent = "-";
    document.getElementById("instance-breakdown").innerHTML = "";
}

function renderBreakdown(perInstance) {
    const el = document.getElementById("instance-breakdown");
    el.innerHTML = "";
    for (const [url, count] of Object.entries(perInstance)) {
        const row = document.createElement("div");
        row.className = "breakdown-row";
        row.innerHTML = `<span>${url.replace("http://", "")}</span><span>${count}</span>`;
        el.appendChild(row);
    }
}

async function simulate() {
    const algorithm = document.getElementById("algorithm").value;
    const rate = parseFloat(document.getElementById("rate").value);
    const duration = parseFloat(document.getElementById("duration").value);
    const limit = parseInt(document.getElementById("limit").value);
    const window_seconds = parseFloat(document.getElementById("window").value);

    const button = document.getElementById("simulate-btn");
    button.disabled = true;
    button.textContent = "Running...";

    chart.data.labels = [];
    chart.data.datasets[0].data = [];
    chart.data.datasets[1].data = [];
    chart.update();
    resetStats();

    const key = `dash:${algorithm}:${Date.now()}`;
    const total = Math.round(rate * duration);
    const interval = 1000 / rate;

    let sent = 0;
    let allowed = 0;
    const perInstance = {};
    INSTANCES.forEach((u) => (perInstance[u] = 0));

    for (let i = 0; i < total; i++) {
        const instance = INSTANCES[i % INSTANCES.length];

        fetch(`${instance}/check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, algorithm, limit, window_seconds }),
        })
            .then((r) => r.json())
            .then((body) => {
                sent++;
                if (body.allowed) {
                    allowed++;
                    perInstance[instance]++;
                }

                chart.data.labels.push(sent);
                chart.data.datasets[0].data.push(allowed);
                chart.data.datasets[1].data.push(sent - allowed);
                chart.update("none");

                document.getElementById("stat-sent").textContent = sent;
                document.getElementById("stat-allowed").textContent = allowed;

                if (sent === total) {
                    const overPermit = ((allowed - limit) / limit) * 100;
                    const sign = overPermit >= 0 ? "+" : "";
                    document.getElementById("stat-permit").textContent = `${sign}${overPermit.toFixed(1)}%`;
                    renderBreakdown(perInstance);
                    button.disabled = false;
                    button.textContent = "Simulate Load";
                }
            })
            .catch(() => {
                sent++;
            });

        await new Promise((resolve) => setTimeout(resolve, interval));
    }
}

document.getElementById("simulate-btn").addEventListener("click", simulate);
initChart();