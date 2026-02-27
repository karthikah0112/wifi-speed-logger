"""
WiFi Speed Logger
-----------------
Runs internet speed tests at a set interval, logs results to CSV,
and generates an HTML dashboard with interactive charts.

Requirements:
    pip install speedtest-cli matplotlib pandas

Usage:
    python speed_logger.py                  # run once
    python speed_logger.py --interval 30    # run every 30 minutes
    python speed_logger.py --dashboard      # generate dashboard only
    python speed_logger.py --demo           # generate demo data + dashboard
"""

import csv
import os
import sys
import time
import argparse
import json
from datetime import datetime


LOG_FILE = "speed_log.csv"
DASHBOARD_FILE = "dashboard.html"
FIELDNAMES = ["timestamp", "download_mbps", "upload_mbps", "ping_ms", "isp", "server"]


# ─────────────────────────────────────────────
# CSV Logging
# ─────────────────────────────────────────────

def init_csv():
    """Create CSV with headers if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        print(f"[+] Created log file: {LOG_FILE}")


def append_result(result: dict):
    """Append a speed test result to the CSV."""
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(result)


def read_all_results() -> list:
    """Read all results from the CSV."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────
# Speed Test
# ─────────────────────────────────────────────

def run_speed_test() -> dict:
    """Run a speed test and return results as a dict."""
    try:
        import speedtest
        print("[*] Running speed test... (this may take 15-30 seconds)")
        st = speedtest.Speedtest()
        st.get_best_server()
        st.download()
        st.upload()
        res = st.results.dict()

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "download_mbps": round(res["download"] / 1_000_000, 2),
            "upload_mbps": round(res["upload"] / 1_000_000, 2),
            "ping_ms": round(res["ping"], 2),
            "isp": res.get("client", {}).get("isp", "Unknown"),
            "server": res.get("server", {}).get("name", "Unknown"),
        }
    except ImportError:
        print("[!] speedtest-cli not installed. Run: pip install speedtest-cli")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Speed test failed: {e}")
        return None


# ─────────────────────────────────────────────
# Demo Data Generator
# ─────────────────────────────────────────────

def generate_demo_data(n=48):
    """Generate realistic-looking demo data for testing."""
    import random
    from datetime import timedelta

    print(f"[+] Generating {n} demo data points...")
    init_csv()

    base_time = datetime.now()
    isps = ["Virgin Media", "BT", "Sky Broadband"]
    servers = ["London", "Manchester", "Birmingham"]

    for i in range(n):
        ts = base_time - timedelta(hours=(n - i) * 0.5)
        # simulate realistic variation with occasional dips
        download = round(random.gauss(85, 12), 2)
        upload = round(random.gauss(18, 4), 2)
        ping = round(random.gauss(14, 5), 2)

        # occasional bad periods
        if random.random() < 0.1:
            download = round(random.uniform(5, 30), 2)
            ping = round(random.uniform(80, 200), 2)

        result = {
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "download_mbps": max(0.5, download),
            "upload_mbps": max(0.5, upload),
            "ping_ms": max(1, ping),
            "isp": random.choice(isps),
            "server": random.choice(servers),
        }
        append_result(result)

    print(f"[+] Demo data written to {LOG_FILE}")


# ─────────────────────────────────────────────
# Dashboard Generator
# ─────────────────────────────────────────────

def generate_dashboard():
    """Generate a self-contained HTML dashboard from the CSV data."""
    rows = read_all_results()
    if not rows:
        print("[!] No data found. Run a speed test first or use --demo")
        return

    # Compute stats
    downloads = [float(r["download_mbps"]) for r in rows]
    uploads = [float(r["upload_mbps"]) for r in rows]
    pings = [float(r["ping_ms"]) for r in rows]
    timestamps = [r["timestamp"] for r in rows]

    def stats(values):
        avg = sum(values) / len(values)
        return {
            "avg": round(avg, 1),
            "max": round(max(values), 1),
            "min": round(min(values), 1),
            "latest": round(values[-1], 1),
        }

    dl_stats = stats(downloads)
    ul_stats = stats(uploads)
    ping_stats = stats(pings)

    # Pass data as JSON to the HTML
    chart_data = json.dumps({
        "labels": timestamps,
        "download": downloads,
        "upload": uploads,
        "ping": pings,
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WiFi Speed Logger</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --border: #1e2d40;
    --accent-dl: #00e5ff;
    --accent-ul: #b44aff;
    --accent-ping: #ff6b35;
    --text: #e2e8f0;
    --muted: #64748b;
    --good: #22c55e;
    --warn: #f59e0b;
    --bad: #ef4444;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Space Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* Background grid */
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }}

  .container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    position: relative;
    z-index: 1;
  }}

  /* Header */
  header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
    gap: 1rem;
  }}

  .logo {{
    display: flex;
    flex-direction: column;
  }}

  .logo-label {{
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    color: var(--accent-dl);
    text-transform: uppercase;
    margin-bottom: 0.3rem;
  }}

  h1 {{
    font-family: 'Syne', sans-serif;
    font-size: clamp(1.8rem, 4vw, 2.8rem);
    font-weight: 800;
    background: linear-gradient(90deg, var(--accent-dl), var(--accent-ul));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
  }}

  .header-meta {{
    text-align: right;
    font-size: 0.7rem;
    color: var(--muted);
    line-height: 1.8;
  }}

  .header-meta span {{
    color: var(--text);
  }}

  /* Stat Cards */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }}

  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
  }}

  .stat-card:hover {{
    transform: translateY(-2px);
    border-color: var(--card-accent);
  }}

  .stat-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--card-accent);
  }}

  .stat-card.dl {{ --card-accent: var(--accent-dl); }}
  .stat-card.ul {{ --card-accent: var(--accent-ul); }}
  .stat-card.ping {{ --card-accent: var(--accent-ping); }}

  .stat-label {{
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 0.75rem;
  }}

  .stat-value {{
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--card-accent);
    line-height: 1;
    margin-bottom: 0.75rem;
  }}

  .stat-unit {{
    font-size: 0.8rem;
    color: var(--muted);
    font-family: 'Space Mono', monospace;
  }}

  .stat-sub {{
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
  }}

  .stat-sub-item {{
    font-size: 0.65rem;
    color: var(--muted);
  }}

  .stat-sub-item span {{
    color: var(--text);
  }}

  /* Chart area */
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
  }}

  .chart-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}

  .chart-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: 0.05em;
  }}

  .legend {{
    display: flex;
    gap: 1.25rem;
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.65rem;
    color: var(--muted);
  }}

  .legend-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
  }}

  canvas {{
    max-height: 280px;
  }}

  /* Table */
  .table-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
  }}

  .table-header {{
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--border);
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
  }}

  .table-wrap {{ overflow-x: auto; }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.72rem;
  }}

  thead th {{
    padding: 0.6rem 1.5rem;
    text-align: left;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-size: 0.6rem;
    border-bottom: 1px solid var(--border);
  }}

  tbody tr {{
    border-bottom: 1px solid rgba(30,45,64,0.5);
    transition: background 0.15s;
  }}

  tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
  tbody tr:last-child {{ border-bottom: none; }}

  td {{
    padding: 0.65rem 1.5rem;
    color: var(--text);
  }}

  .badge {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 700;
  }}

  .badge-good {{ background: rgba(34,197,94,0.15); color: var(--good); }}
  .badge-warn {{ background: rgba(245,158,11,0.15); color: var(--warn); }}
  .badge-bad  {{ background: rgba(239,68,68,0.15);  color: var(--bad);  }}

  footer {{
    text-align: center;
    padding: 2rem 0 1rem;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 0.1em;
  }}

  footer a {{ color: var(--accent-dl); text-decoration: none; }}
</style>
</head>
<body>
<div class="container">

  <header>
    <div class="logo">
      <div class="logo-label">// network monitor</div>
      <h1>WiFi Speed Logger</h1>
    </div>
    <div class="header-meta">
      <div>Total records: <span>{len(rows)}</span></div>
      <div>Latest test: <span>{timestamps[-1]}</span></div>
      <div>First test: <span>{timestamps[0]}</span></div>
    </div>
  </header>

  <!-- Stat Cards -->
  <div class="stats-grid">
    <div class="stat-card dl">
      <div class="stat-label">↓ Download</div>
      <div class="stat-value">{dl_stats['latest']}<span class="stat-unit"> Mbps</span></div>
      <div class="stat-sub">
        <div class="stat-sub-item">avg <span>{dl_stats['avg']}</span></div>
        <div class="stat-sub-item">max <span>{dl_stats['max']}</span></div>
        <div class="stat-sub-item">min <span>{dl_stats['min']}</span></div>
      </div>
    </div>
    <div class="stat-card ul">
      <div class="stat-label">↑ Upload</div>
      <div class="stat-value">{ul_stats['latest']}<span class="stat-unit"> Mbps</span></div>
      <div class="stat-sub">
        <div class="stat-sub-item">avg <span>{ul_stats['avg']}</span></div>
        <div class="stat-sub-item">max <span>{ul_stats['max']}</span></div>
        <div class="stat-sub-item">min <span>{ul_stats['min']}</span></div>
      </div>
    </div>
    <div class="stat-card ping">
      <div class="stat-label">◎ Ping</div>
      <div class="stat-value">{ping_stats['latest']}<span class="stat-unit"> ms</span></div>
      <div class="stat-sub">
        <div class="stat-sub-item">avg <span>{ping_stats['avg']}</span></div>
        <div class="stat-sub-item">max <span>{ping_stats['max']}</span></div>
        <div class="stat-sub-item">min <span>{ping_stats['min']}</span></div>
      </div>
    </div>
  </div>

  <!-- Speed Chart -->
  <div class="chart-card">
    <div class="chart-header">
      <div class="chart-title">Download & Upload Speed</div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#00e5ff"></div>Download</div>
        <div class="legend-item"><div class="legend-dot" style="background:#b44aff"></div>Upload</div>
      </div>
    </div>
    <canvas id="speedChart"></canvas>
  </div>

  <!-- Ping Chart -->
  <div class="chart-card">
    <div class="chart-header">
      <div class="chart-title">Ping Latency</div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#ff6b35"></div>Ping (ms)</div>
      </div>
    </div>
    <canvas id="pingChart"></canvas>
  </div>

  <!-- Recent Results Table -->
  <div class="table-card">
    <div class="table-header">Recent Results</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Download</th>
            <th>Upload</th>
            <th>Ping</th>
            <th>ISP</th>
            <th>Server</th>
            <th>Quality</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

  <footer>
    WiFi Speed Logger &mdash; Built with Python &amp; Chart.js &mdash;
    <a href="https://github.com/yourusername/wifi-speed-logger" target="_blank">GitHub</a>
  </footer>
</div>

<script>
const DATA = {chart_data};

// Shorten labels for display
const shortLabels = DATA.labels.map(l => {{
  const d = new Date(l);
  return d.toLocaleString('en-GB', {{month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}});
}});

const chartDefaults = {{
  responsive: true,
  maintainAspectRatio: true,
  interaction: {{ mode: 'index', intersect: false }},
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: '#111827',
      borderColor: '#1e2d40',
      borderWidth: 1,
      titleColor: '#64748b',
      bodyColor: '#e2e8f0',
      padding: 10,
      titleFont: {{ family: 'Space Mono', size: 10 }},
      bodyFont: {{ family: 'Space Mono', size: 11 }},
    }}
  }},
  scales: {{
    x: {{
      ticks: {{
        color: '#64748b',
        font: {{ family: 'Space Mono', size: 9 }},
        maxTicksLimit: 10,
        maxRotation: 30,
      }},
      grid: {{ color: 'rgba(30,45,64,0.6)' }},
    }},
    y: {{
      ticks: {{ color: '#64748b', font: {{ family: 'Space Mono', size: 9 }} }},
      grid: {{ color: 'rgba(30,45,64,0.6)' }},
    }}
  }}
}};

// Speed Chart
new Chart(document.getElementById('speedChart'), {{
  type: 'line',
  data: {{
    labels: shortLabels,
    datasets: [
      {{
        label: 'Download (Mbps)',
        data: DATA.download,
        borderColor: '#00e5ff',
        backgroundColor: 'rgba(0,229,255,0.06)',
        borderWidth: 2,
        pointRadius: DATA.download.length > 30 ? 0 : 3,
        pointHoverRadius: 5,
        tension: 0.3,
        fill: true,
      }},
      {{
        label: 'Upload (Mbps)',
        data: DATA.upload,
        borderColor: '#b44aff',
        backgroundColor: 'rgba(180,74,255,0.06)',
        borderWidth: 2,
        pointRadius: DATA.upload.length > 30 ? 0 : 3,
        pointHoverRadius: 5,
        tension: 0.3,
        fill: true,
      }}
    ]
  }},
  options: {{ ...chartDefaults }}
}});

// Ping Chart
new Chart(document.getElementById('pingChart'), {{
  type: 'line',
  data: {{
    labels: shortLabels,
    datasets: [{{
      label: 'Ping (ms)',
      data: DATA.ping,
      borderColor: '#ff6b35',
      backgroundColor: 'rgba(255,107,53,0.06)',
      borderWidth: 2,
      pointRadius: DATA.ping.length > 30 ? 0 : 3,
      pointHoverRadius: 5,
      tension: 0.3,
      fill: true,
    }}]
  }},
  options: {{ ...chartDefaults }}
}});

// Table (last 20 results, newest first)
const tbody = document.getElementById('tableBody');
const recent = [...DATA.labels.map((l,i) => ({{
  ts: l, dl: DATA.download[i], ul: DATA.upload[i], ping: DATA.ping[i]
}}))].reverse().slice(0, 20);

recent.forEach(r => {{
  let quality, cls;
  if (r.dl >= 50 && r.ping <= 20) {{ quality = 'Excellent'; cls = 'badge-good'; }}
  else if (r.dl >= 20 && r.ping <= 50) {{ quality = 'Good'; cls = 'badge-good'; }}
  else if (r.dl >= 5 && r.ping <= 100) {{ quality = 'Fair'; cls = 'badge-warn'; }}
  else {{ quality = 'Poor'; cls = 'badge-bad'; }}

  tbody.innerHTML += `<tr>
    <td>${{r.ts}}</td>
    <td style="color:#00e5ff">${{r.dl}} Mbps</td>
    <td style="color:#b44aff">${{r.ul}} Mbps</td>
    <td style="color:#ff6b35">${{r.ping}} ms</td>
    <td>—</td>
    <td>—</td>
    <td><span class="badge ${{cls}}">${{quality}}</span></td>
  </tr>`;
}});
</script>
</body>
</html>"""

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[+] Dashboard saved to: {DASHBOARD_FILE}")
    print(f"    Open it in your browser to view your speed history.")


# ─────────────────────────────────────────────
# Main Loop
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WiFi Speed Logger — track and visualize your internet speed"
    )
    parser.add_argument("--interval", type=int, default=0,
                        help="Minutes between tests (0 = run once)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate dashboard from existing data")
    parser.add_argument("--demo", action="store_true",
                        help="Generate demo data and dashboard")
    args = parser.parse_args()

    if args.demo:
        generate_demo_data()
        generate_dashboard()
        return

    if args.dashboard:
        generate_dashboard()
        return

    init_csv()

    if args.interval > 0:
        print(f"[*] Running speed tests every {args.interval} minute(s). Press Ctrl+C to stop.")
        while True:
            result = run_speed_test()
            if result:
                append_result(result)
                print(f"[+] {result['timestamp']} | "
                      f"↓ {result['download_mbps']} Mbps | "
                      f"↑ {result['upload_mbps']} Mbps | "
                      f"ping {result['ping_ms']} ms")
                generate_dashboard()
            try:
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n[*] Stopped.")
                break
    else:
        result = run_speed_test()
        if result:
            append_result(result)
            print(f"[+] {result['timestamp']} | "
                  f"↓ {result['download_mbps']} Mbps | "
                  f"↑ {result['upload_mbps']} Mbps | "
                  f"ping {result['ping_ms']} ms")
            generate_dashboard()


if __name__ == "__main__":
    main()
