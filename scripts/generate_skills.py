"""
Skills Card Generator - Gotham Theme
Generates a clean, self-hosted unified SVG card (assets/skills.svg)
displaying categorized technical skills, frameworks, libraries, and tools
with official icons from assets/icons/ and labeled names in Segoe UI.

Categorization Principles:
- Languages: Formal programming, markup, and stylesheet languages.
- Frameworks & Runtimes: Architectural scaffolds exercising Inversion of Control
  (FastAPI, Express.js, Tailwind CSS) and execution engines (Node.js).
- Libraries & Machine Learning: Call-on-demand component, numerical, ML, and
  automation libraries (React, NumPy, Scikit-Learn, Selenium).
- Databases & Cloud: Data persistence engines and cloud platforms.
- Tools & Platforms: Version control, containerization, operating systems, and IDEs.
"""

import re
import os
import html
import xml.etree.ElementTree as ET
from pathlib import Path

# --- Gotham Palette Colors ---
BG_COLOR = "#000B0B"        # Solid midnight background
BORDER_COLOR = "#00573F"    # Gotham Forest Green solid border & dividers
ACCENT_GREEN = "#00A375"    # Gotham Emerald (Headers & active accents)
PILL_BG = "#001414"         # Subtle dark surface for skill badge
PILL_BORDER = "#004D38"     # Subtle border for skill badge
TEXT_LIGHT = "#E0F2F1"      # Skill name text
TEXT_MUTED = "#80CBC4"      # Secondary descriptions / subtitles
TEXT_DIM = "#4E7A6B"        # Section labels / counts

SKILL_CATEGORIES = [
    {
        "title": "Languages",
        "skills": [
            {"name": "Python", "file": "Python-Dark.svg"},
            {"name": "TypeScript", "file": "TypeScript.svg"},
            {"name": "JavaScript", "file": "JavaScript.svg"},
            {"name": "C++", "file": "CPP.svg"},
            {"name": "R", "file": "R-Dark.svg"},
            {"name": "HTML5", "file": "HTML.svg"},
            {"name": "CSS3", "file": "CSS.svg"},
            {"name": "Markdown", "file": "Markdown-Dark.svg"},
        ]
    },
    {
        "title": "Frameworks & Runtimes",
        "skills": [
            {"name": "Express.js", "file": "ExpressJS-Dark.svg"},
            {"name": "FastAPI", "file": "FastAPI.svg"},
            {"name": "Tailwind CSS", "file": "TailwindCSS-Dark.svg"},
            {"name": "Node.js", "file": "NodeJS-Dark.svg"},
        ]
    },
    {
        "title": "Libraries",
        "skills": [
            {"name": "React", "file": "React-Dark.svg"},
            {"name": "Selenium", "file": "Selenium.svg"},
        ]
    },
    {
        "title": "Machine Learning",
        "skills": [
            {"name": "Scikit-Learn", "file": "ScikitLearn-Dark.svg"},
            {"name": "NumPy", "file": "NumPy.svg"},
        ]
    },
    {
        "title": "Databases & Cloud",
        "skills": [
            {"name": "MongoDB", "file": "MongoDB.svg"},
            {"name": "PostgreSQL", "file": "PostgreSQL-Dark.svg"},
            {"name": "Google Cloud", "file": "GCP-Dark.svg"},
        ]
    },
    {
        "title": "Tools & Platforms",
        "skills": [
            {"name": "Docker", "file": "Docker.svg"},
            {"name": "Linux", "file": "Linux-Dark.svg"},
            {"name": "Git", "file": "Git.svg"},
            {"name": "GitHub", "file": "Github-Dark.svg"},
            {"name": "Anaconda", "file": "Anaconda-Dark.svg"},
            {"name": "VS Code", "file": "VSCode-Dark.svg"},
            {"name": "Vim", "file": "VIM-Dark.svg"},
        ]
    }
]

def escape_xml(s: str) -> str:
    """Escape XML special characters: &, <, >, \", '"""
    return html.escape(s, quote=True)

def load_and_sanitize_icon(icon_name, filename):
    """Load an icon from assets/icons, extract its inner SVG elements, and namespace IDs to prevent collisions."""
    assets_dir = Path("assets")
    candidates = [
        assets_dir / "icons" / filename,
        assets_dir / filename
    ]
    icon_path = None
    for c in candidates:
        if c.is_file():
            icon_path = c
            break

    if not icon_path:
        raise FileNotFoundError(f"Could not find icon file {filename} in assets/icons or assets")

    with open(icon_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Extract viewBox
    vb_match = re.search(r'<svg[^>]*viewBox=["\']([^"\']*)["\']', content)
    viewbox = vb_match.group(1) if vb_match else "0 0 256 256"

    # Extract inner SVG body between <svg...> and </svg>
    body_match = re.search(r'<svg[^>]*>(.*)</svg>', content, re.DOTALL)
    inner_body = body_match.group(1) if body_match else content

    # Namespace all IDs and references to prevent collisions between icons
    safe_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', icon_name.lower()) + "_ico_"
    
    # Find all IDs defined
    id_matches = re.findall(r'id=["\']([^"\']+)["\']', inner_body)
    for orig_id in id_matches:
        new_id = safe_prefix + orig_id
        inner_body = re.sub(f'id=["\']{re.escape(orig_id)}["\']', f'id="{new_id}"', inner_body)
        inner_body = re.sub(rf'url\(#{re.escape(orig_id)}\)', f'url(#{new_id})', inner_body)
        inner_body = re.sub(f'href=["\']#{re.escape(orig_id)}["\']', f'href="#{new_id}"', inner_body)

    return viewbox, inner_body

def generate_skills_svg():
    """Build the Gotham-themed categorized skills card with strict XML entity escaping."""
    card_width = 890
    margin_x = 25
    content_width = card_width - (margin_x * 2) # 840px
    
    start_y = 80
    cur_y = start_y
    pill_h = 36
    gap_x = 10
    gap_y = 10
    category_gap = 22

    category_svgs = []
    
    for cat_idx, cat in enumerate(SKILL_CATEGORIES):
        cat_title = cat["title"]
        escaped_cat_title = escape_xml(cat_title.upper())
        skills = cat["skills"]
        
        cat_markup = []
        
        # Section Divider (except before first category)
        if cat_idx > 0:
            cat_markup.append(f'<line x1="{margin_x}" y1="{cur_y - 12}" x2="{card_width - margin_x}" y2="{cur_y - 12}" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.5"/>')
        
        # Category Header (XML-escaped)
        cat_markup.append(f'<text class="category-title" x="{margin_x}" y="{cur_y + 4}">{escaped_cat_title}</text>')
        cur_y += 18
        
        # Lay out pills with auto-wrapping
        cur_x = margin_x
        row_y = cur_y
        
        for skill in skills:
            name = skill["name"]
            escaped_name = escape_xml(name)
            fname = skill["file"]
            viewbox, icon_body = load_and_sanitize_icon(name, fname)
            
            # Compute pill width based on text length
            text_w = len(name) * 7.4
            pill_w = max(78, int(36 + text_w + 12))
            
            # Wrap to next row if exceeding content width
            if cur_x + pill_w > margin_x + content_width and cur_x > margin_x:
                cur_x = margin_x
                row_y += pill_h + gap_y
            
            pill_svg = f"""
    <!-- Skill: {escaped_name} -->
    <g class="skill-pill-group" transform="translate({cur_x}, {row_y})">
      <rect width="{pill_w}" height="{pill_h}" rx="6" fill="{PILL_BG}" stroke="{PILL_BORDER}" stroke-width="1" class="skill-pill-bg" />
      <g transform="translate(6, 6)">
        <svg width="24" height="24" viewBox="{viewbox}">
          {icon_body}
        </svg>
      </g>
      <text x="36" y="22" class="skill-pill-text">{escaped_name}</text>
    </g>"""
            cat_markup.append(pill_svg)
            cur_x += pill_w + gap_x
            
        cur_y = row_y + pill_h + category_gap
        category_svgs.append("\n".join(cat_markup))

    total_height = cur_y + 6

    # Assemble complete SVG
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="{total_height}" viewBox="0 0 {card_width} {total_height}" fill="none" role="img" aria-label="Technical Skills and Tools for Vedant Chaudhari">
  <style>
    .card-header {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 22px;
      font-weight: 700;
      fill: {ACCENT_GREEN};
    }}

    .card-subtitle {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 12px;
      fill: {TEXT_MUTED};
    }}

    .category-title {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 11px;
      font-weight: 700;
      fill: {ACCENT_GREEN};
      letter-spacing: 0.8px;
    }}

    .skill-pill-bg {{
      transition: stroke 0.2s ease, fill 0.2s ease;
    }}

    .skill-pill-group:hover .skill-pill-bg {{
      stroke: {ACCENT_GREEN};
      fill: #00221A;
    }}

    .skill-pill-text {{
      font-family: 'Segoe UI', Ubuntu, -apple-system, sans-serif;
      font-size: 12px;
      font-weight: 600;
      fill: {TEXT_LIGHT};
    }}
  </style>

  <!-- Solid Clean Gotham Outer Border -->
  <rect x="0.5" y="0.5" width="{card_width - 1}" height="{total_height - 1}" rx="6" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1" />

  <!-- Card Title & Subtitle -->
  <text class="card-header" x="{margin_x}" y="35">Languages &amp; Technologies</text>
  <text class="card-subtitle" x="{margin_x}" y="54">Technical stack, frameworks, libraries, machine learning, databases &amp; developer tools</text>

  <!-- Top Divider -->
  <line x1="{margin_x}" y1="65" x2="{card_width - margin_x}" y2="65" stroke="{BORDER_COLOR}" stroke-width="1" stroke-opacity="0.7"/>

  <!-- Categorized Skills Sections -->
  {"".join(category_svgs)}
</svg>"""

    # Strict XML Validation
    try:
        ET.fromstring(svg)
    except ET.ParseError as e:
        raise ValueError(f"Generated SVG has invalid XML syntax: {e}")

    return svg

def main():
    print("[INFO] Generating self-hosted Gotham skills card...")
    svg_content = generate_skills_svg()
    
    output_dir = Path("assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "skills.svg"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"[SUCCESS] Generated {output_file} ({len(svg_content)} bytes)")
    print("[SUCCESS] XML Validation passed with 0 errors.")

if __name__ == "__main__":
    main()
