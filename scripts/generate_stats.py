"""
GitHub Profile Stats Generator - Gotham Theme
Unifies:
1. Awesome GitHub Stats (with Icon.CLOCK and exact rank circle placement)
2. Streak Card (from tmp/card.php with official fire icon and ring mask)
3. Monthly Contribution Graph (from tmp/profile-details-card.ts)
4. Top Languages (with official GitHub Linguist colors)
Styled cleanly in Gotham palette using Segoe UI.
Zero external dependencies - runs on standard Python 3.
"""

import os
import json
import datetime
from pathlib import Path
import urllib.request
import urllib.error

# --- Gotham Palette Colors ---
BG_COLOR = "#000B0B"        # Solid midnight background
BORDER_COLOR = "#00573F"    # Gotham Forest Green solid border & dividers
ACCENT_GREEN = "#00A375"    # Gotham Emerald (Primary accent & headers)
TEXT_LIGHT = "#E0F2F1"      # Metric numbers
TEXT_MUTED = "#80CBC4"      # Labels & descriptions
TEXT_DIM = "#4E7A6B"        # Subtitles / dates

# Official GitHub Linguist Colors
OFFICIAL_LANG_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "C++": "#F34B7D",
    "C": "#555555",
    "HTML": "#E34C26",
    "HTML/CSS": "#E34C26",
    "CSS": "#563D7C",
    "Jupyter Notebook": "#DA5B0B",
    "Java": "#B07219",
    "Rust": "#DEA584",
    "Go": "#00ADD8",
    "Shell": "#89E051",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "R": "#198CE7",
}

def load_env():
    """Load key-value pairs from .env if present without external dependencies."""
    env_path = Path(".env")
    if env_path.is_file():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

def fetch_all_time_stats(token, username):
    """Fetch all-time stats across all active years, plus trailing 1-year calendar for the activity graph."""
    query_base = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        location
        createdAt
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            name
            stargazerCount
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
        pullRequests {
          totalCount
        }
        issues {
          totalCount
        }
        repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
          totalCount
        }
        pastYearCalendar: contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
          contributionYears
        }
      }
    }
    """
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Gotham-Stats-Generator"
    }
    payload = json.dumps({"query": query_base, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        if "errors" in res_data:
            raise RuntimeError(f"GraphQL Errors: {res_data['errors']}")
        base_user = res_data["data"]["user"]

    years = base_user["pastYearCalendar"].get("contributionYears", [])
    
    total_commits = 0
    all_time_contributions = 0
    all_calendar_weeks = []
    
    if years:
        year_fields = []
        for y in years:
            year_fields.append(f"""
            y_{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") {{
              totalCommitContributions
              restrictedContributionsCount
              contributionCalendar {{
                totalContributions
                weeks {{
                  contributionDays {{
                    contributionCount
                    date
                  }}
                }}
              }}
            }}
            """)
        query_years = f"""
        query($login: String!) {{
          user(login: $login) {{
            {"".join(year_fields)}
          }}
        }}
        """
        payload_years = json.dumps({"query": query_years, "variables": {"login": username}}).encode("utf-8")
        req_years = urllib.request.Request(url, data=payload_years, headers=headers)
        with urllib.request.urlopen(req_years) as resp_years:
            res_years = json.loads(resp_years.read().decode("utf-8"))
            if "errors" in res_years:
                raise RuntimeError(f"GraphQL Years Errors: {res_years['errors']}")
            years_data = res_years["data"]["user"]

        for y in sorted(years):
            yd = years_data.get(f"y_{y}", {})
            commits_in_year = yd.get("totalCommitContributions", 0) + yd.get("restrictedContributionsCount", 0)
            total_commits += commits_in_year
            total_contribs_year = yd.get("contributionCalendar", {}).get("totalContributions", 0)
            all_time_contributions += total_contribs_year
            all_calendar_weeks.extend(yd.get("contributionCalendar", {}).get("weeks", []))
    else:
        py_cal = base_user["pastYearCalendar"]["contributionCalendar"]
        total_commits = base_user["pastYearCalendar"].get("totalCommitContributions", 0)
        all_time_contributions = py_cal.get("totalContributions", 0)
        all_calendar_weeks = py_cal.get("weeks", [])

    return base_user, total_commits, all_time_contributions, all_calendar_weeks

def calculate_streaks(weeks):
    """Calculate current and longest contribution streaks across calendar days up to today."""
    today_str = datetime.date.today().isoformat()
    days_dict = {}
    for w in weeks:
        for d in w.get("contributionDays", []):
            date_str = d["date"]
            # Exclude future placeholder days returned by GitHub API
            if date_str <= today_str:
                days_dict[date_str] = max(days_dict.get(date_str, 0), d.get("contributionCount", 0))
    
    if not days_dict:
        return 0, "", 0, ""

    days = sorted(days_dict.items(), key=lambda x: x[0])
    
    longest_streak = 0
    longest_range = ""
    temp_streak = 0
    temp_start = ""
    
    for date_str, count in days:
        if count > 0:
            if temp_streak == 0:
                temp_start = date_str
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
                longest_range = f"{temp_start} – {date_str}"
        else:
            temp_streak = 0
            temp_start = ""
            
    # For current streak: check up to today (or yesterday if today is 0)
    check_days = days
    if check_days and check_days[-1][1] == 0:
        check_days = days[:-1]

    cur_streak = 0
    cur_start = ""
    cur_end = ""
    for date_str, count in reversed(check_days):
        if count > 0:
            if cur_streak == 0:
                cur_end = date_str
                cur_start = date_str
            else:
                cur_start = date_str
            cur_streak += 1
        else:
            break
                
    current_streak = cur_streak
    current_range = f"{cur_start} – {cur_end}" if cur_streak > 0 else "No active streak"
    
    def format_range(range_str):
        if "–" not in range_str:
            return range_str
        parts = [p.strip() for p in range_str.split("–")]
        if len(parts) != 2:
            return range_str
        try:
            d1 = datetime.datetime.strptime(parts[0], "%Y-%m-%d")
            d2 = datetime.datetime.strptime(parts[1], "%Y-%m-%d")
            return f"{d1.strftime('%b %d')} &#8211; {d2.strftime('%b %d')}"
        except Exception:
            return range_str

    return current_streak, format_range(current_range), longest_streak, format_range(longest_range)

def aggregate_monthly_contributions(weeks):
    """Aggregate daily contributions into monthly totals over the last 12-13 months up to today."""
    today_str = datetime.date.today().isoformat()
    month_map = {}
    for w in weeks:
        for d in w.get("contributionDays", []):
            date_str = d["date"]
            if date_str <= today_str:
                month_key = date_str[:7] # YYYY-MM
                month_map[month_key] = month_map.get(month_key, 0) + d["contributionCount"]
            
    sorted_months = sorted(month_map.items())[-13:]
    return sorted_months

def aggregate_languages(repos):
    """Aggregate language size across repositories with official colors."""
    lang_map = {}
    lang_colors = {}
    for repo in repos.get("nodes", []):
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"].get("color")
            lang_map[name] = lang_map.get(name, 0) + size
            if color and name not in lang_colors:
                lang_colors[name] = color
            
    total_size = sum(lang_map.values()) or 1
    sorted_langs = sorted(lang_map.items(), key=lambda x: x[1], reverse=True)[:5]
    
    result = []
    for lang, size in sorted_langs:
        pct = round((size / total_size) * 100, 1)
        color = lang_colors.get(lang) or OFFICIAL_LANG_COLORS.get(lang, ACCENT_GREEN)
        result.append({
            "name": lang,
            "percent": pct,
            "color": color
        })
    return result

RANK_DEGREES = [
    {"rank": "OMG", "points": 1000000, "count_slice": False},
    {"rank": "S++", "points": 300000, "count_slice": True},
    {"rank": "S+", "points": 70000, "count_slice": True},
    {"rank": "S", "points": 28000, "count_slice": True},
    {"rank": "S-", "points": 21000, "count_slice": True},
    {"rank": "A++", "points": 14000, "count_slice": True},
    {"rank": "A+", "points": 1500, "count_slice": True},
    {"rank": "A", "points": 500, "count_slice": True},
    {"rank": "B+", "points": 200, "count_slice": True},
    {"rank": "B", "points": 0, "count_slice": True},
]

def calculate_rank_and_progress(commits, prs, issues, stars, contributed_to):
    """Calculate user rank and circle progress using AwesomeGithubStats algorithm."""
    score = (commits * 1.0) + (prs * 1.0) + (issues * 1.0) + (stars * 3.5) + (contributed_to * 10.0)
    
    level = "B"
    for rd in RANK_DEGREES:
        if score >= rd["points"]:
            level = rd["rank"]
            break

    slices = sum(1 for rd in RANK_DEGREES if rd.get("count_slice", True))
    slices_after = sum(1 for rd in RANK_DEGREES if rd.get("count_slice", True) and rd["points"] > score)
    slice_min_size = (100.0 / slices) * (slices - slices_after)
    
    next_ranks = [rd for rd in RANK_DEGREES if rd["points"] > score]
    if not next_ranks:
        progress_bar = 100.0
    else:
        next_rank = min(next_ranks, key=lambda x: x["points"])
        cur_points = next((rd["points"] for rd in RANK_DEGREES if rd["rank"] == level), 0)
        rank_size = max(1, next_rank["points"] - cur_points)
        points_in_rank = score - cur_points
        pct_in_rank = max(0.0, min(1.0, points_in_rank / rank_size))
        slice_size = 100.0 / slices
        progress_bar = slice_min_size + (slice_size * pct_in_rank)
        
    progress_bar = max(0.0, min(100.0, progress_bar))
    circle_progress = round(progress_bar * 360.0 / 100.0, 2)
    return level, circle_progress

def get_stats():
    """Retrieve all-time stats from GitHub API if token is present; otherwise use preview snapshot values."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    username = "thatengineerguy21"
    
    if token:
        try:
            print("[INFO] Fetching all-time data via GitHub GraphQL API...")
            base_user, total_commits, all_time_contributions, all_weeks = fetch_all_time_stats(token, username)
            name = base_user.get("name") or username
            
            repos = base_user.get("repositories", {})
            stars = sum(r.get("stargazerCount", 0) for r in repos.get("nodes", []))
            
            total_prs = base_user.get("pullRequests", {}).get("totalCount", 0)
            total_issues = base_user.get("issues", {}).get("totalCount", 0)
            contributed_to = base_user.get("repositoriesContributedTo", {}).get("totalCount", 0)
            
            # All-time streak calculation across all calendar years
            cur_streak, cur_range, longest_streak, longest_range = calculate_streaks(all_weeks)
            
            # Trailing 1-year calendar strictly for the Activity Graph
            past_year_weeks = base_user["pastYearCalendar"]["contributionCalendar"].get("weeks", [])
            monthly_contribs = aggregate_monthly_contributions(past_year_weeks)
            
            languages = aggregate_languages(repos)
            rank, rank_progress = calculate_rank_and_progress(total_commits, total_prs, total_issues, stars, contributed_to)
            
            # Format account creation date for Total Contributions subtitle
            created_at_raw = base_user.get("createdAt", "")
            try:
                created_dt = datetime.datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                created_range = f"{created_dt.strftime('%b %d, %Y')} &#8211; Present"
            except Exception:
                created_range = "Sep 30, 2021 &#8211; Present"
            
            return {
                "name": name,
                "login": username,
                "stars": stars,
                "commits": total_commits,
                "prs": total_prs,
                "issues": total_issues,
                "contributed_to": contributed_to,
                "total_contributions": all_time_contributions,
                "created_at_range": created_range,
                "current_streak": cur_streak,
                "current_streak_range": cur_range,
                "longest_streak": longest_streak,
                "longest_streak_range": longest_range,
                "monthly_contributions": monthly_contribs,
                "languages": languages,
                "rank": rank,
                "rank_progress": rank_progress,
                "source": "live"
            }
        except Exception as e:
            print(f"[WARN] Live fetch failed ({e}), using preview snapshot values.")

    # High-fidelity preview values based on profile history
    return {
        "name": "Vedant Chaudhari",
        "login": "thatengineerguy21",
        "stars": 1,
        "commits": 727,
        "prs": 65,
        "issues": 7,
        "contributed_to": 7,
        "total_contributions": 836,
        "created_at_range": "Sep 30, 2021 &#8211; Present",
        "current_streak": 6,
        "current_streak_range": "Sep 03 &#8211; Sep 08",
        "longest_streak": 38,
        "longest_streak_range": "Apr 11 &#8211; May 18",
        "monthly_contributions": [
            ("2025-09", 8),
            ("2025-10", 0),
            ("2025-11", 43),
            ("2025-12", 1),
            ("2026-01", 42),
            ("2026-02", 41),
            ("2026-03", 97),
            ("2026-04", 121),
            ("2026-05", 57),
            ("2026-06", 60),
            ("2026-07", 28),
            ("2026-08", 209),
            ("2026-09", 38)
        ],
        "languages": [
            {"name": "Python", "percent": 41.2, "color": OFFICIAL_LANG_COLORS["Python"]},
            {"name": "TypeScript", "percent": 24.5, "color": OFFICIAL_LANG_COLORS["TypeScript"]},
            {"name": "JavaScript", "percent": 18.3, "color": OFFICIAL_LANG_COLORS["JavaScript"]},
            {"name": "C++", "percent": 10.4, "color": OFFICIAL_LANG_COLORS["C++"]},
            {"name": "HTML/CSS", "percent": 5.6, "color": OFFICIAL_LANG_COLORS["HTML/CSS"]}
        ],
        "rank": "A",
        "rank_progress": 134.9,
        "source": "preview"
    }

def generate_smooth_path(points, base_y):
    """Generate smooth cubic bezier SVG path through given (x, y) coordinates."""
    if not points:
        return "", ""
    line_parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = p2[1] - (p3[1] - p1[1]) / 6.0
        line_parts.append(f"C {cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    line_d = " ".join(line_parts)
    area_d = f"M {points[0][0]:.1f} {base_y:.1f} L {points[0][0]:.1f} {points[0][1]:.1f} " + " ".join(line_parts[1:]) + f" L {points[-1][0]:.1f} {base_y:.1f} Z"
    return line_d, area_d

def generate_svg(stats):
    """Render the clean unified Gotham-themed SVG (890x480)."""
    
    # 1. Monthly Graph Path & Axes
    monthly_data = stats.get("monthly_contributions", [])
    chart_x_start = 35
    chart_x_end = 815
    chart_base_y = 345
    chart_top_y = 265
    chart_h = chart_base_y - chart_top_y
    
    max_count = max([c for _, c in monthly_data] + [10])
    # round max_count up to a clean multiple
    y_axis_max = ((max_count + 19) // 20) * 20
    
    points = []
    x_step = (chart_x_end - chart_x_start) / max(1, len(monthly_data) - 1)
    for i, (m_key, count) in enumerate(monthly_data):
        px = chart_x_start + (i * x_step)
        py = chart_base_y - (count / y_axis_max) * chart_h
        points.append((px, py))
        
    line_d, area_d = generate_smooth_path(points, chart_base_y)
    
    # X-Axis Ticks (YY/MM)
    x_ticks_svg = ""
    for i, (m_key, _) in enumerate(monthly_data):
        if i % 2 == 0:
            px = chart_x_start + (i * x_step)
            # format YYYY-MM to YY/MM
            label = m_key[2:].replace("-", "/")
            x_ticks_svg += f'<text x="{px:.1f}" y="{chart_base_y + 16}" text-anchor="middle" font-size="10" fill="{TEXT_MUTED}">{label}</text>\n    '
            x_ticks_svg += f'<line x1="{px:.1f}" y1="{chart_base_y}" x2="{px:.1f}" y2="{chart_base_y + 4}" stroke="{BORDER_COLOR}" stroke-width="1"/>\n    '
            
    # Y-Axis Ticks on Right
    y_ticks_svg = f"""
    <line x1="{chart_x_end}" y1="{chart_base_y}" x2="{chart_x_end + 4}" y2="{chart_base_y}" stroke="{BORDER_COLOR}" stroke-width="1"/>
    <text x="{chart_x_end + 8}" y="{chart_base_y + 3}" font-size="10" fill="{TEXT_MUTED}">0</text>
    <line x1="{chart_x_end}" y1="{chart_top_y + chart_h/2}" x2="{chart_x_end + 4}" y2="{chart_top_y + chart_h/2}" stroke="{BORDER_COLOR}" stroke-width="1"/>
    <text x="{chart_x_end + 8}" y="{chart_top_y + chart_h/2 + 3}" font-size="10" fill="{TEXT_MUTED}">{y_axis_max // 2}</text>
    <line x1="{chart_x_end}" y1="{chart_top_y}" x2="{chart_x_end + 4}" y2="{chart_top_y}" stroke="{BORDER_COLOR}" stroke-width="1"/>
    <text x="{chart_x_end + 8}" y="{chart_top_y + 3}" font-size="10" fill="{TEXT_MUTED}">{y_axis_max}</text>
    """

    # 2. Language Bar Segments & Legend
    total_bar_w = 840
    lang_rects_svg = ""
    cur_x = 25
    for idx, lang in enumerate(stats["languages"]):
        seg_w = max(4, int(total_bar_w * (lang["percent"] / 100)))
        lang_rects_svg += f'<rect class="lang-seg" x="{cur_x}" y="418" width="{seg_w}" height="8" fill="{lang["color"]}" rx="4" />\n    '
        cur_x += seg_w + 2

    legend_svg = ""
    legend_x = [25, 200, 385, 570, 735]
    for idx, lang in enumerate(stats["languages"]):
        x_pos = legend_x[idx] if idx < len(legend_x) else 25 + (idx * 160)
        legend_svg += f"""
      <g class="stagger" style="animation-delay: {600 + idx * 100}ms;">
        <circle cx="{x_pos}" cy="450" r="4.5" fill="{lang['color']}" />
        <text class="font-stat bold" x="{x_pos + 12}" y="454">{lang['name']}</text>
        <text class="font-stat" x="{x_pos + 12 + len(lang['name']) * 9 + 6}" y="454" fill="{TEXT_MUTED}">{lang['percent']}%</text>
      </g>"""

    rank = stats.get("rank", "A+")
    rank_progress = stats.get("rank_progress", 154.57)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="890" height="480" viewBox="0 0 890 480" fill="none" role="img" aria-label="GitHub Profile Statistics for {stats['name']}">
  <defs>
    <!-- Mask for fire icon resting on top of streak ring (tmp/card.php) -->
    <mask id="mask_out_ring_behind_fire">
      <rect width="890" height="480" fill="white"/>
      <ellipse cx="667" cy="42" rx="14" ry="18" fill="black"/>
    </mask>

    <!-- Clip path for smooth monthly chart reveal wipe -->
    <clipPath id="chart_reveal_clip">
      <rect class="chart-wipe" x="30" y="255" width="815" height="110" />
    </clipPath>
  </defs>

  <style>
    .header {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 24px;
      font-weight: 700;
      fill: {ACCENT_GREEN};
      animation: fadeIn 0.6s ease-in-out forwards;
    }}

    .section-header {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 14px;
      font-weight: 700;
      fill: {ACCENT_GREEN};
      animation: fadeIn 0.6s ease-in-out forwards;
    }}

    .caption {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 11px;
      fill: {TEXT_MUTED};
    }}

    .font-stat {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 13px;
      fill: {TEXT_MUTED};
    }}

    .bold {{
      font-weight: 600;
      fill: {TEXT_MUTED};
    }}

    .val {{
      font-weight: 700;
      fill: {TEXT_LIGHT};
    }}

    .icon {{
      fill: {ACCENT_GREEN};
    }}

    /* Staggered Fade-in */
    .stagger {{
      opacity: 0;
      animation: fadeIn 0.4s ease-in-out forwards;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    /* Ranking Circle Animations (AwesomeGithubStats) */
    .rank-circle-rim {{
      stroke: {BORDER_COLOR};
      fill: none;
      stroke-width: 6;
      opacity: 0.2;
    }}

    .rank-circle {{
      stroke: {ACCENT_GREEN};
      stroke-dasharray: 0, 20000;
      fill: none;
      stroke-width: 6;
      opacity: 0;
      stroke-linecap: round;
      animation: rankAnimation 3s ease-in-out 0.6s forwards, fadeIn 0.3s ease-in-out 0.6s forwards;
    }}

    @keyframes rankAnimation {{
      from {{ stroke-dasharray: 0, 2000; }}
      to {{ stroke-dasharray: {rank_progress}, 2000; }}
    }}

    .rank-text {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 46px;
      font-weight: 800;
      stroke-width: 1.5;
      stroke: {ACCENT_GREEN};
      fill: {ACCENT_GREEN};
      animation: stroke 4.5s alternate forwards;
    }}

    @keyframes stroke {{
      0% {{
        fill: rgba(0, 163, 117, 0);
        stroke: {ACCENT_GREEN};
        stroke-dashoffset: 25%;
        stroke-dasharray: 0 50%;
        stroke-width: 2;
      }}
      70% {{
        fill: rgba(0, 163, 117, 0);
        stroke: {ACCENT_GREEN};
      }}
      80% {{
        fill: rgba(0, 163, 117, 0);
        stroke: {ACCENT_GREEN};
        stroke-width: 3;
      }}
      100% {{
        fill: {ACCENT_GREEN};
        stroke: {ACCENT_GREEN};
        stroke-dashoffset: -25%;
        stroke-dasharray: 50% 0;
        stroke-width: 0;
      }}
    }}

    /* Streak Animations */
    @keyframes currstreak {{
      0% {{ font-size: 3px; opacity: 0.2; }}
      80% {{ font-size: 34px; opacity: 1; }}
      100% {{ font-size: 28px; opacity: 1; }}
    }}

    /* Chart Wipe-in Animation */
    .chart-wipe {{
      animation: chartWipeAnim 1.4s cubic-bezier(0.16, 1, 0.3, 1) 0.5s forwards;
    }}

    @keyframes chartWipeAnim {{
      from {{ width: 0; }}
      to {{ width: 815px; }}
    }}

    .lang-seg {{
      animation: fadeIn 0.8s ease-in-out 0.5s forwards;
    }}
  </style>

  <!-- Solid Clean Gotham Outer Border -->
  <rect x="0.5" y="0.5" width="889" height="479" rx="6" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1" />

  <!-- ==================== SECTION 1: TOP (OVERVIEW + STREAKS) ==================== -->
  <!-- Name Header -->
  <text class="header" x="25" y="38">{stats['name']}</text>

  <!-- Overview Stats Rows -->
  <g transform="translate(0, 56)">
    <!-- Row 1: Total Stars -->
    <g class="stagger" style="animation-delay: 200ms;" transform="translate(25, 0)">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">
        <path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25zm0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z"/>
      </svg>
      <text class="font-stat bold" x="25" y="12.5">Total Stars:</text>
      <text class="font-stat val" x="170" y="12.5">{stats['stars']}</text>
    </g>

    <!-- Row 2: Total Commits (Icon.CLOCK from AwesomeGithubStats) -->
    <g class="stagger" style="animation-delay: 300ms;" transform="translate(25, 30)">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">
        <path fill-rule="evenodd" d="M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z"/>
      </svg>
      <text class="font-stat bold" x="25" y="12.5">Total Commits:</text>
      <text class="font-stat val" x="170" y="12.5">{stats['commits']:,}</text>
    </g>

    <!-- Row 3: Total PRs -->
    <g class="stagger" style="animation-delay: 400ms;" transform="translate(25, 60)">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">
        <path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
      </svg>
      <text class="font-stat bold" x="25" y="12.5">Total PRs:</text>
      <text class="font-stat val" x="170" y="12.5">{stats['prs']}</text>
    </g>

    <!-- Row 4: Total Issues -->
    <g class="stagger" style="animation-delay: 500ms;" transform="translate(25, 90)">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">
        <path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z"/>
      </svg>
      <text class="font-stat bold" x="25" y="12.5">Total Issues:</text>
      <text class="font-stat val" x="170" y="12.5">{stats['issues']}</text>
    </g>

    <!-- Row 5: Contributed To -->
    <g class="stagger" style="animation-delay: 600ms;" transform="translate(25, 120)">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">
        <path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"/>
      </svg>
      <text class="font-stat bold" x="25" y="12.5">Contributed to:</text>
      <text class="font-stat val" x="170" y="12.5">{stats['contributed_to']}</text>
    </g>

    <!-- EXACT RANK CIRCLE (Directly extracted from AwesomeGithubStats UserStatsCard.cs) -->
    <g data-testid="rank-circle" transform="translate(365, 58)">
      <circle class="rank-circle-rim" cx="-10" cy="8" r="60"/>
      <circle class="rank-circle" cx="-10" cy="8" r="60" transform="rotate(-90 -10 8)" />
      <g class="rank-text">
        <text x="-10" y="7" dy=".35em" text-anchor="middle">{rank}</text>
      </g>
    </g>
  </g>

  <!-- Vertical Divider 1 -->
  <line x1="445" y1="20" x2="445" y2="210" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.7"/>

  <!-- Streak Section (Directly extracted from tmp/card.php) -->
  <g transform="translate(0, 0)">
    <!-- Vertical divider between streak columns -->
    <line x1="593" y1="30" x2="593" y2="200" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.5"/>
    <line x1="741" y1="30" x2="741" y2="200" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.5"/>

    <!-- Column 1: Total Contributions -->
    <g transform="translate(519, 58)">
      <text x="0" y="32" text-anchor="middle" fill="{ACCENT_GREEN}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="28px" class="stagger" style="animation-delay: 400ms;">
        {stats['total_contributions']:,}
      </text>
    </g>
    <g transform="translate(519, 98)">
      <text x="0" y="32" text-anchor="middle" fill="{TEXT_MUTED}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="400" font-size="14px" class="stagger" style="animation-delay: 500ms;">
        Total Contributions
      </text>
    </g>
    <g transform="translate(519, 130)">
      <text x="0" y="32" text-anchor="middle" fill="{TEXT_DIM}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="400" font-size="12px" class="stagger" style="animation-delay: 600ms;">
        {stats.get('created_at_range', 'Sep 30, 2021 &#8211; Present')}
      </text>
    </g>

    <!-- Column 2: Current Streak (with official fire icon & ring) -->
    <!-- Current Streak label -->
    <g transform="translate(667, 122)">
      <text x="0" y="32" text-anchor="middle" fill="{ACCENT_GREEN}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14px" class="stagger" style="animation-delay: 700ms;">
        Current Streak
      </text>
    </g>
    <!-- Current Streak range -->
    <g transform="translate(667, 158)">
      <text x="0" y="21" text-anchor="middle" fill="{TEXT_MUTED}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="400" font-size="12px" class="stagger" style="animation-delay: 700ms;">
        {stats['current_streak_range']}
      </text>
    </g>

    <!-- Ring around number with mask for fire icon -->
    <g mask="url(#mask_out_ring_behind_fire)">
      <circle cx="667" cy="81" r="40" fill="none" stroke="{ACCENT_GREEN}" stroke-width="5" class="stagger" style="animation-delay: 300ms;"/>
    </g>

    <!-- Official Fire icon -->
    <g transform="translate(667, 29.5)" stroke-opacity="0" class="stagger" style="animation-delay: 450ms;">
      <path d="M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z" fill="none"/>
      <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="{ACCENT_GREEN}" stroke-opacity="0"/>
    </g>

    <!-- Current Streak big number (Centered inside ring) -->
    <g transform="translate(667, 58)">
      <text x="0" y="32" text-anchor="middle" fill="{ACCENT_GREEN}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="28px" style="animation: currstreak 0.6s linear forwards;">
        {stats['current_streak']}
      </text>
    </g>

    <!-- Column 3: Longest Streak -->
    <g transform="translate(815, 58)">
      <text x="0" y="32" text-anchor="middle" fill="{ACCENT_GREEN}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="28px" class="stagger" style="animation-delay: 800ms;">
        {stats['longest_streak']}
      </text>
    </g>
    <g transform="translate(815, 98)">
      <text x="0" y="32" text-anchor="middle" fill="{TEXT_MUTED}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="400" font-size="14px" class="stagger" style="animation-delay: 900ms;">
        Longest Streak
      </text>
    </g>
    <g transform="translate(815, 130)">
      <text x="0" y="32" text-anchor="middle" fill="{TEXT_DIM}" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="400" font-size="12px" class="stagger" style="animation-delay: 1000ms;">
        {stats['longest_streak_range']}
      </text>
    </g>
  </g>

  <!-- ==================== SECTION 2: MONTHLY ACTIVITY GRAPH ==================== -->
  <!-- Horizontal Divider 1 -->
  <line x1="25" y1="225" x2="865" y2="225" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.7"/>

  <!-- Graph Header & Caption -->
  <text class="section-header" x="25" y="248">Activity</text>
  <text class="caption" x="865" y="248" text-anchor="end">contributions in the last year</text>

  <!-- Clipped Area & Curve Line -->
  <g clip-path="url(#chart_reveal_clip)">
    <!-- Area Fill -->
    <path d="{area_d}" fill="{ACCENT_GREEN}" fill-opacity="0.35" />
    <!-- Top Curve Stroke -->
    <path d="{line_d}" fill="none" stroke="{ACCENT_GREEN}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
  </g>

  <!-- X-Axis Baseline & Ticks -->
  <line x1="{chart_x_start}" y1="{chart_base_y}" x2="{chart_x_end}" y2="{chart_base_y}" stroke="{BORDER_COLOR}" stroke-width="1"/>
  {x_ticks_svg}

  <!-- Y-Axis Ticks -->
  {y_ticks_svg}

  <!-- ==================== SECTION 3: TOP LANGUAGES ==================== -->
  <!-- Horizontal Divider 2 -->
  <line x1="25" y1="385" x2="865" y2="385" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.7"/>

  <text class="section-header" x="25" y="407">Top Languages</text>

  <!-- Segmented Language Bar (Official Linguist Colors) -->
  <g>
    {lang_rects_svg}
  </g>

  <!-- Language Legend -->
  <g>
    {legend_svg}
  </g>
</svg>"""
    return svg

def main():
    load_env()
    stats = get_stats()
    svg_content = generate_svg(stats)
    
    output_dir = Path("assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "github-stats.svg"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"[SUCCESS] Generated {output_file} (Mode: {stats['source']})")

if __name__ == "__main__":
    main()
