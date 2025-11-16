from fastapi import FastAPI, Depends, Query
from fastapi.responses import HTMLResponse


from app.models import (
    SearchRequest, SearchResponse, AddressObject, AddressObject2,
    ReverseResponse,
    CompareRequest, CompareResponse
)
from app.dependencies import get_geocoder
from geocoder.algorithm import GeocoderAlgorithm

app = FastAPI(
    title="Geocoder API",
    description="API для геокодирования, обратного геокодирования и оценки сходства",
    version="1.0.0",
)


@app.on_event("startup")
def preload_geocoder():
  _ = get_geocoder()

# 1) Топ-N адресов
@app.post("/search", response_model=SearchResponse)
def search_addresses(
    request: SearchRequest,
    geocoder: GeocoderAlgorithm = Depends(get_geocoder)
):
    results = geocoder.search(
        query=request.query,
        top_n=request.top_n,
        weights=request.weights.dict() if request.weights else None,
        # algorithms=request.algorithms,
    )
    objects = [AddressObject(**r) for r in results]

    return SearchResponse(
        searched_address=request.query,
        objects=objects
    )

# 2) Обратное геокодирование
@app.get("/reverse", response_model=ReverseResponse)
def reverse_geocode(
    lat: float = Query(...),
    lon: float = Query(...),
    geocoder: GeocoderAlgorithm = Depends(get_geocoder),
):
    results = geocoder.reverse(lat=lat, lon=lon)
    objects = [AddressObject2(**r) for r in results] if results else []

    return ReverseResponse(
        query_point_lat=lat,
        query_point_lon=lon,
        objects=objects
    )


# 3) Сравнение двух адресов
@app.post("/compare", response_model=CompareResponse)
def compare_addresses(
    request: CompareRequest,
    geocoder: GeocoderAlgorithm = Depends(get_geocoder)
):
    c1 = geocoder.get_best_candidate(request.address_1, request.weights, request.algorithms)
    c2 = geocoder.get_best_candidate(request.address_2, request.weights, request.algorithms)

    if not c1 or not c2:
        return CompareResponse(
            address_1=request.address_1,
            address_2=request.address_2,
            distance_m=None,
            similarity=None,
            point_1=AddressObject(**c1) if c1 else None,
            point_2=AddressObject(**c2) if c2 else None,
        )

    d = geocoder.haversine_distance_m(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
    similarity = max(0.0, 1.0 - d / 1000.0)

    return CompareResponse(
        address_1=request.address_1,
        address_2=request.address_2,
        distance_m=d,
        similarity=similarity,
        point_1=AddressObject(**c1),
        point_2=AddressObject(**c2),
    )

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Geocoder API Panel</title>
  <style>
    :root {
      --bg: #020617;
      --bg-elevated: #02081b;
      --bg-card: #020b24;
      --accent: #3b82f6;
      --accent-soft: rgba(59,130,246,0.12);
      --accent-strong: rgba(59,130,246,0.35);
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: #1e293b;
      --error: #fb7185;
      --success: #4ade80;
      --radius-lg: 26px;
      --radius-md: 16px;
    }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      padding: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
      font-size: 18px;
      background: radial-gradient(circle at top left, #1e3a8a 0, #020617 45%, #020617 100%);
      color: var(--text);
      min-height: 100vh;
    }

    .shell {
      max-width: 1440px;
      margin: 40px auto 60px;
      padding: 0 32px;
    }

    .card {
      background: linear-gradient(135deg, rgba(15,23,42,0.98), rgba(15,23,42,0.94));
      border-radius: var(--radius-lg);
      padding: 36px 40px 40px;
      border: 1px solid rgba(148,163,184,0.25);
      box-shadow:
        0 24px 60px rgba(15,23,42,0.9),
        0 0 0 1px rgba(15,23,42,0.9);
      min-height: 900px;
      backdrop-filter: blur(22px);
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      margin-bottom: 24px;
    }

    .title-block h1 {
      margin: 0 0 6px;
      font-size: 34px;
      letter-spacing: 0.03em;
    }

    .title-block p {
      margin: 0;
      font-size: 18px;
      color: var(--muted);
    }

    .badge {
      padding: 6px 14px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.4);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--muted);
      background: radial-gradient(circle at top left, rgba(96,165,250,0.32), rgba(15,23,42,0.95));
    }

    /* Tabs */

    .tabs {
      display: flex;
      gap: 10px;
      margin: 10px 0 26px;
      padding: 4px;
      border-radius: 999px;
      background: rgba(15,23,42,0.95);
      border: 1px solid rgba(30,64,175,0.9);
      box-shadow: inset 0 0 0 1px rgba(15,23,42,0.7);
    }

    .tab-btn {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--muted);
      font-size: 17px;
      padding: 10px 16px;
      border-radius: 999px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.16s ease;
    }

    .tab-icon {
      font-size: 20px;
    }

    .tab-btn.active {
      background: radial-gradient(circle at top left, rgba(59,130,246,0.55), rgba(37,99,235,0.85));
      color: #eff6ff;
      box-shadow:
        0 10px 24px rgba(37,99,235,0.75),
        0 0 0 1px rgba(191,219,254,0.5);
    }

    .tab-btn:hover:not(.active) {
      background: rgba(15,23,42,0.96);
      color: #e5e7eb;
    }

    /* Layout grid */

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.1fr);
      gap: 28px;
      align-items: flex-start;
    }

    @media (max-width: 1100px) {
      .grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }

    /* Panels */

    .panel {
      border-radius: var(--radius-md);
      border: 1px solid rgba(31,41,55,0.95);
      background: radial-gradient(circle at top left, rgba(15,23,42,1), rgba(15,23,42,0.94));
      padding: 18px 22px 22px;
    }

    .panel-title {
      font-size: 18px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
      color: #e5e7eb;
    }

    .panel-dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: radial-gradient(circle at center, #4ade80, #16a34a);
      box-shadow: 0 0 15px rgba(34,197,94,0.9);
    }

    .form-row {
      display: flex;
      gap: 14px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .form-col {
      flex: 1;
      min-width: 0;
    }

    label {
      display: block;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      margin-bottom: 4px;
    }

    input, select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 13px;
      border: 1px solid rgba(55,65,81,0.95);
      background: rgba(15,23,42,0.98);
      color: var(--text);
      font-size: 17px;
      outline: none;
      transition: border 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
    }

    input::placeholder {
      color: rgba(156,163,175,0.8);
    }

    input:focus, select:focus {
      border-color: rgba(59,130,246,0.95);
      box-shadow:
        0 0 0 1px rgba(59,130,246,0.85),
        0 0 0 12px rgba(37,99,235,0.25);
      background: rgba(15,23,42,1);
    }

    .small-input {
      max-width: 150px;
    }

    /* Buttons */

    .btn-primary {
      border-radius: 16px;
      background: radial-gradient(circle at top left, #60a5fa, #2563eb);
      color: #eff6ff;
      border: none;
      padding: 12px 26px;
      font-size: 17px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-top: 10px;
      box-shadow:
        0 14px 30px rgba(37,99,235,0.75),
        0 0 0 1px rgba(191,219,254,0.5);
      transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
    }

    .btn-primary:hover {
      transform: translateY(-1px);
      filter: brightness(1.06);
      box-shadow:
        0 18px 40px rgba(37,99,235,0.9),
        0 0 0 1px rgba(191,219,254,0.65);
    }

    .btn-primary:active {
      transform: translateY(0);
      box-shadow:
        0 10px 22px rgba(37,99,235,0.7),
        0 0 0 1px rgba(191,219,254,0.5);
    }

    .btn-icon {
      font-size: 20px;
    }

    /* Chips */

    .chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 6px;
    }

    .chip {
      font-size: 14px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(15,23,42,0.95);
      border: 1px solid rgba(55,65,81,1);
      color: var(--muted);
    }

    .chip strong {
      color: #e5e7eb;
      font-weight: 500;
    }

    /* Results */

    .results {
      border-radius: var(--radius-md);
      border: 1px solid rgba(31,41,55,0.96);
      background: radial-gradient(circle at top right, rgba(15,23,42,1), rgba(15,23,42,0.94));
      padding: 18px 20px 22px;
      min-height: 720px;
      max-height: 980px;
      overflow-y: auto;
      font-size: 16px;
    }

    .placeholder {
      color: var(--muted);
      font-size: 16px;
      padding: 6px 2px;
    }

    .result-card {
      border-radius: 14px;
      border: 1px solid rgba(55,65,81,1);
      background: rgba(15,23,42,0.98);
      padding: 10px 12px;
      margin-bottom: 10px;
    }

    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 4px;
    }

    .result-title {
      font-size: 16px;
      font-weight: 500;
    }

    .score-pill {
      font-size: 13px;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #bfdbfe;
      border: 1px solid rgba(59,130,246,0.9);
    }

    .sub {
      font-size: 15px;
      color: var(--muted);
      margin-bottom: 2px;
    }

    .coords {
      font-size: 14px;
      color: #9ca3af;
    }

    .badge-distance {
      font-size: 13px;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(8,47,73,0.95);
      border: 1px solid rgba(56,189,248,0.95);
      color: #e0f2fe;
      margin-left: 6px;
    }

    .status {
      font-size: 15px;
      margin-top: 6px;
      min-height: 20px;
    }

    .status.error {
      color: var(--error);
    }

    .status.ok {
      color: var(--success);
    }

    .hidden {
      display: none;
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="card">
      <div class="header">
        <div class="title-block">
          <h1>Geocoder API panel</h1>
          <p>Поиск адресов, обратное геокодирование и сравнение двух адресов.</p>
        </div>
        <div class="badge">Команда им. Э.А. Кулиева</div>
      </div>

      <div class="tabs">
        <button class="tab-btn active" data-target="tab-search">
          <span class="tab-icon">🔎</span>
          <span>Поиск адреса</span>
        </button>
        <button class="tab-btn" data-target="tab-reverse">
          <span class="tab-icon">📍</span>
          <span>Обратное геокодирование</span>
        </button>
        <button class="tab-btn" data-target="tab-compare">
          <span class="tab-icon">⚖️</span>
          <span>Сравнение адресов</span>
        </button>
      </div>

      <!-- SEARCH TAB -->
      <div id="tab-search" class="grid">
        <div class="panel">
          <div class="panel-title">
            <span class="panel-dot"></span>
            <span>Поиск похожих адресов</span>
          </div>
          <form id="search-form">
            <div class="form-row">
              <div class="form-col">
                <label for="search-query">Адрес</label>
                <input id="search-query" placeholder="город Москва, улица Ленина дом 3" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-col small-input">
                <label for="search-top">TOP N</label>
                <input id="search-top" type="number" value="5" min="1" max="50" />
              </div>
              <div class="form-col">
                <label>Веса алгоритмов</label>
                <div class="form-row">
                  <div class="form-col">
                    <input id="w-dl" type="number" step="0.1" value="1.0" />
                    <div class="chips">
                      <span class="chip"><strong>DL</strong> · Damerau–Levenshtein</span>
                    </div>
                  </div>
                  <div class="form-col">
                    <input id="w-bm25" type="number" step="0.1" value="1.0" />
                    <div class="chips">
                      <span class="chip"><strong>BM25</strong> · текстовый поиск</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <button class="btn-primary" type="submit">
              <span class="btn-icon">🚀</span>
              <span>Найти адреса</span>
            </button>
            <div id="search-status" class="status"></div>
          </form>
        </div>

        <div class="results" id="search-results">
          <div class="placeholder">
            Введите строку адреса и нажмите «Найти адреса».
          </div>
        </div>
      </div>

      <!-- REVERSE TAB -->
      <div id="tab-reverse" class="grid hidden">
        <div class="panel">
          <div class="panel-title">
            <span class="panel-dot"></span>
            <span>Адрес по координатам</span>
          </div>
          <form id="reverse-form">
            <div class="form-row">
              <div class="form-col">
                <label for="rev-lat">Широта (lat)</label>
                <input id="rev-lat" placeholder="55.751244" />
              </div>
              <div class="form-col">
                <label for="rev-lon">Долгота (lon)</label>
                <input id="rev-lon" placeholder="37.618423" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-col small-input">
                <label for="rev-top">TOP N</label>
                <input id="rev-top" type="number" value="3" min="1" max="50" />
              </div>
              <div class="form-col small-input">
                <label for="rev-radius">Радиус, м</label>
                <input id="rev-radius" type="number" value="300" min="0" />
              </div>
            </div>
            <button class="btn-primary" type="submit">
              <span class="btn-icon">📡</span>
              <span>Найти адреса</span>
            </button>
            <div id="reverse-status" class="status"></div>
          </form>
        </div>

        <div class="results" id="reverse-results">
          <div class="placeholder">
            Введите координаты и нажмите «Найти адреса».
          </div>
        </div>
      </div>

      <!-- COMPARE TAB -->
      <div id="tab-compare" class="grid hidden">
        <div class="panel">
          <div class="panel-title">
            <span class="panel-dot"></span>
            <span>Сравнение двух адресов</span>
          </div>
          <form id="compare-form">
            <div class="form-row">
              <div class="form-col">
                <label for="cmp-a1">Адрес 1</label>
                <input id="cmp-a1" placeholder="город Москва, улица Ленина дом 3" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-col">
                <label for="cmp-a2">Адрес 2</label>
                <input id="cmp-a2" placeholder="город Москва, улица Ленина дом 5" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-col">
                <label>Веса алгоритмов</label>
                <div class="form-row">
                  <div class="form-col">
                    <input id="cmp-w-dl" type="number" step="0.1" value="1.0" />
                    <div class="chips">
                      <span class="chip"><strong>DL</strong></span>
                    </div>
                  </div>
                  <div class="form-col">
                    <input id="cmp-w-bm25" type="number" step="0.1" value="1.0" />
                    <div class="chips">
                      <span class="chip"><strong>BM25</strong></span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <button class="btn-primary" type="submit">
              <span class="btn-icon">📏</span>
              <span>Оценить сходство</span>
            </button>
            <div id="compare-status" class="status"></div>
          </form>
        </div>

        <div class="results" id="compare-results">
          <div class="placeholder">
            Введите два адреса и нажмите «Оценить сходство».
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Переключение вкладок
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabSearch = document.getElementById("tab-search");
    const tabReverse = document.getElementById("tab-reverse");
    const tabCompare = document.getElementById("tab-compare");
    const tabsMap = {
      "tab-search": tabSearch,
      "tab-reverse": tabReverse,
      "tab-compare": tabCompare
    };

    tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        tabButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const target = btn.dataset.target;
        Object.keys(tabsMap).forEach(id => {
          if (id === target) tabsMap[id].classList.remove("hidden");
          else tabsMap[id].classList.add("hidden");
        });
      });
    });

    // /search
    const searchForm = document.getElementById("search-form");
    const searchStatus = document.getElementById("search-status");
    const searchResults = document.getElementById("search-results");

    searchForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      searchStatus.textContent = "";
      searchStatus.className = "status";

      const query = document.getElementById("search-query").value.trim();
      const topN = parseInt(document.getElementById("search-top").value || "5", 10);
      const wDl = parseFloat(document.getElementById("w-dl").value || "1");
      const wBm25 = parseFloat(document.getElementById("w-bm25").value || "1");

      if (!query) {
        searchStatus.textContent = "Введите строку адреса.";
        searchStatus.classList.add("error");
        return;
      }

      const payload = {
        query: query,
        top_n: topN,
        weights: { dl: wDl, bm25: wBm25 },
        algorithms: []
      };

      try {
        searchStatus.textContent = "Выполняется поиск…";
        const res = await fetch("/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.text();
          searchStatus.textContent = "Ошибка: " + res.status;
          searchStatus.classList.add("error");
          console.error(err);
          return;
        }

        const data = await res.json();
        renderSearchResults(data);
        searchStatus.textContent = "Готово.";
        searchStatus.classList.add("ok");
      } catch (err) {
        console.error(err);
        searchStatus.textContent = "Ошибка сети.";
        searchStatus.classList.add("error");
      }
    });

    function renderSearchResults(data) {
      if (!data || !data.objects || data.objects.length === 0) {
        searchResults.innerHTML = '<div class="placeholder">Ничего не найдено.</div>';
        return;
      }
      let html = "";
      data.objects.forEach((obj, i) => {
        html += `
          <div class="result-card">
            <div class="result-header">
              <div class="result-title">#${i + 1} · ${obj.street}</div>
              ${obj.score !== null && obj.score !== undefined
                ? `<span class="score-pill">score: ${obj.score.toFixed(3)}</span>`
                : ""}
            </div>
            <div class="sub">${obj.locality || ""} ${obj.number || ""}</div>
            <div class="coords">lat: ${obj.lat}, lon: ${obj.lon}</div>
          </div>
        `;
      });
      searchResults.innerHTML = html;
    }

    // /reverse
    const reverseForm = document.getElementById("reverse-form");
    const reverseStatus = document.getElementById("reverse-status");
    const reverseResults = document.getElementById("reverse-results");

    reverseForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      reverseStatus.textContent = "";
      reverseStatus.className = "status";

      const lat = document.getElementById("rev-lat").value.trim();
      const lon = document.getElementById("rev-lon").value.trim();
      const topN = parseInt(document.getElementById("rev-top").value || "3", 10);
      const radius = parseFloat(document.getElementById("rev-radius").value || "0");

      if (!lat || !lon) {
        reverseStatus.textContent = "Введите lat и lon.";
        reverseStatus.classList.add("error");
        return;
      }

      const params = new URLSearchParams({
        lat: lat,
        lon: lon,
        top_n: String(topN),
        radius_m: String(radius),
      });

      try {
        reverseStatus.textContent = "Ищем ближайшие адреса…";
        const res = await fetch(`/reverse?${params.toString()}`, {
          method: "GET"
        });

        if (!res.ok) {
          const err = await res.text();
          reverseStatus.textContent = "Ошибка: " + res.status;
          reverseStatus.classList.add("error");
          console.error(err);
          return;
        }

        const data = await res.json();
        renderReverseResults(data);
        reverseStatus.textContent = "Готово.";
        reverseStatus.classList.add("ok");
      } catch (err) {
        console.error(err);
        reverseStatus.textContent = "Ошибка сети.";
        reverseStatus.classList.add("error");
      }
    });

    function renderReverseResults(data) {
      const objects = data && data.objects ? data.objects : [];
      if (!objects.length) {
        reverseResults.innerHTML = '<div class="placeholder">Ничего не найдено в указанном радиусе.</div>';
        return;
      }
      let html = "";
      objects.forEach((obj, i) => {
        html += `
          <div class="result-card">
            <div class="result-header">
              <div class="result-title">#${i + 1} · ${obj.street}</div>
              ${obj.distance_m !== null && obj.distance_m !== undefined
                ? `<span class="badge-distance">${obj.distance_m.toFixed(1)} м</span>`
                : ""}
            </div>
            <div class="sub">${obj.locality || ""} ${obj.number || ""}</div>
            <div class="coords">lat: ${obj.lat}, lon: ${obj.lon}</div>
          </div>
        `;
      });
      reverseResults.innerHTML = html;
    }

    // /compare
    const compareForm = document.getElementById("compare-form");
    const compareStatus = document.getElementById("compare-status");
    const compareResults = document.getElementById("compare-results");

    compareForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      compareStatus.textContent = "";
      compareStatus.className = "status";

      const a1 = document.getElementById("cmp-a1").value.trim();
      const a2 = document.getElementById("cmp-a2").value.trim();
      const wDl = parseFloat(document.getElementById("cmp-w-dl").value || "1");
      const wBm25 = parseFloat(document.getElementById("cmp-w-bm25").value || "1");

      if (!a1 || !a2) {
        compareStatus.textContent = "Введите оба адреса.";
        compareStatus.classList.add("error");
        return;
      }

      const payload = {
        address_1: a1,
        address_2: a2,
        weights: { dl: wDl, bm25: wBm25 },
        algorithms: []
      };

      try {
        compareStatus.textContent = "Сравниваем адреса…";
        const res = await fetch("/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.text();
          compareStatus.textContent = "Ошибка: " + res.status;
          compareStatus.classList.add("error");
          console.error(err);
          return;
        }

        const data = await res.json();
        renderCompareResults(data);
        compareStatus.textContent = "Готово.";
        compareStatus.classList.add("ok");
      } catch (err) {
        console.error(err);
        compareStatus.textContent = "Ошибка сети.";
        compareStatus.classList.add("error");
      }
    });

    function renderCompareResults(data) {
      if (!data) {
        compareResults.innerHTML = '<div class="placeholder">Нет данных.</div>';
        return;
      }

      let html = "";

      if (data.point_1) {
        html += `
          <div class="result-card">
            <div class="result-header">
              <div class="result-title">Адрес 1 · ${data.point_1.street}</div>
            </div>
            <div class="coords">lat: ${data.point_1.lat}, lon: ${data.point_1.lon}</div>
          </div>
        `;
      }

      if (data.point_2) {
        html += `
          <div class="result-card">
            <div class="result-header">
              <div class="result-title">Адрес 2 · ${data.point_2.street}</div>
            </div>
            <div class="coords">lat: ${data.point_2.lat}, lon: ${data.point_2.lon}</div>
          </div>
        `;
      }

      if (data.distance_m !== null && data.distance_m !== undefined) {
        html += `
          <div class="result-card">
            <div class="result-header">
              <div class="result-title">Расстояние между адресами</div>
            </div>
            <div class="sub">
              ${data.distance_m.toFixed(1)} м
              ${data.similarity !== null && data.similarity !== undefined
                ? `<span class="badge-distance">similarity: ${(data.similarity * 100).toFixed(1)}%</span>`
                : ""}
            </div>
          </div>
        `;
      }

      if (!html) {
        html = '<div class="placeholder">Не удалось сопоставить адреса.</div>';
      }

      compareResults.innerHTML = html;
    }
  </script>
</body>
</html>

    """
