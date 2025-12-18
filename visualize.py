"""Generate an interactive weekly timetable HTML from a CSV.

CSV format (same as timetable/main.py):
<Subject_name>,<subject_code>,<Credits>,<Course_code_1>,<Course_time_1>,<Course_code_2>,<Course_time_2>,...
Time format: "CS:10:15-12:00" where day is one of H, K, SZ, CS, P.

Usage:
  python -m timetable.visualize --csv timetable.csv --out timetable.html

Open the generated HTML in a browser.
- Toggle subjects to show/hide.
- Click a class to select/deselect (overlaps are allowed).
- Export the final selected schedule to a PNG.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from timetable.main import load_timetable_from_csv
from timetable.models import DAYS_OF_WEEK


DAY_LABELS: Dict[str, str] = {
    "H": "H",
    "K": "K",
    "SZE": "SZE",
    "CS": "CS",
    "P": "P",
}


@dataclass(frozen=True)
class CourseDto:
    id: str
    subject_code: str
    subject_name: str
    subject_credits: int
    course_code: str
    day: str
    start_min: int
    end_min: int
    time_str: str


def _course_to_dto(subject, course, index: int) -> CourseDto:
    ct = course.get_time()
    course_id = f"{subject.code}__{course.code}__{index}"
    return CourseDto(
        id=course_id,
        subject_code=subject.code,
        subject_name=subject.name,
        subject_credits=int(subject.credits),
        course_code=course.code,
        day=ct.day,
        start_min=ct.start_time.to_minutes(),
        end_min=ct.end_time.to_minutes(),
        time_str=str(ct),
    )


def _compute_time_bounds(courses: List[CourseDto]) -> Tuple[int, int]:
    if not courses:
        return 8 * 60, 20 * 60

    min_start = min(c.start_min for c in courses)
    max_end = max(c.end_min for c in courses)

    # Pad to nearest hour to keep the grid clean.
    min_start = (min_start // 60) * 60
    max_end = ((max_end + 59) // 60) * 60

    # Reasonable clamp.
    min_start = max(6 * 60, min_start)
    max_end = min(22 * 60, max_end)
    if max_end <= min_start:
        max_end = min_start + 60
    return min_start, max_end


def _palette() -> List[str]:
    # A small set of pleasant colors (no external deps). Kept stable across runs.
    return [
        "#4E79A7",
        "#F28E2B",
        "#E15759",
        "#76B7B2",
        "#59A14F",
        "#EDC948",
        "#B07AA1",
        "#FF9DA7",
        "#9C755F",
        "#BAB0AC",
    ]


def _build_payload(csv_path: str) -> Dict[str, Any]:
    timetable = load_timetable_from_csv(csv_path)

    courses: List[CourseDto] = []
    for subject in timetable.subjects:
        for idx, course in enumerate(subject.courses):
            courses.append(_course_to_dto(subject, course, idx))

    # Sort for deterministic rendering.
    courses.sort(key=lambda c: (DAYS_OF_WEEK.index(c.day), c.start_min, c.end_min, c.subject_code, c.course_code))

    subjects: Dict[str, Dict[str, Any]] = {}
    pal = _palette()
    for i, subject in enumerate(timetable.subjects):
        subjects[subject.code] = {
            "code": subject.code,
            "name": subject.name,
            "credits": int(subject.credits),
            "color": pal[i % len(pal)],
        }

    start_min, end_min = _compute_time_bounds(courses)

    return {
        "meta": {
            "csv": os.path.basename(csv_path),
            "startMin": start_min,
            "endMin": end_min,
            "days": [{"key": d, "label": DAY_LABELS.get(d, d)} for d in DAYS_OF_WEEK],
        },
        "subjects": subjects,
        "courses": [
            {
                "id": c.id,
                "subjectCode": c.subject_code,
                "subjectName": c.subject_name,
                "subjectCredits": c.subject_credits,
                "courseCode": c.course_code,
                "day": c.day,
                "startMin": c.start_min,
                "endMin": c.end_min,
                "timeStr": c.time_str,
            }
            for c in courses
        ],
    }


def _html_template(payload_json: str) -> str:
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Timetable</title>
  <style>
    :root {
      --bg: #0b0e14;
      --panel: #111827;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: rgba(255,255,255,0.12);
      --danger: #ef4444;
    }

    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      height: 100vh;
    }

    .sidebar {
      border-right: 1px solid var(--border);
      background: #111827;
      padding: 16px;
      overflow: auto;
    }

    .main {
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
    }

    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      background: rgba(17,24,39,0.65);
      backdrop-filter: blur(8px);
    }

    .toolbar .title { font-weight: 600; }
    .toolbar .meta { color: var(--muted); font-size: 12px; }

    .btn {
      padding: 8px 12px;
      background: rgba(255,255,255,0.06);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      cursor: pointer;
    }
    .btn:hover { border-color: rgba(96,165,250,0.55); }

    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      margin: 0 0 12px 0;
    }

    .subject {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 10px;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: 10px;
      background: rgba(255,255,255,0.03);
    }

    .swatch {
      width: 14px;
      height: 14px;
      border-radius: 4px;
      margin-top: 3px;
      border: 1px solid rgba(255,255,255,0.25);
    }

    .subject label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
    }

    .subject .name { font-weight: 600; }
    .subject .code { color: var(--muted); font-size: 12px; }

    .canvas-wrap { position: relative; overflow: auto; padding: 16px; }

    canvas {
      display: block;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--border);
      border-radius: 12px;
    }

    #tooltip {
      position: absolute;
      pointer-events: none;
      background: rgba(17,24,39,0.92);
      color: #e5e7eb;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 8px;
      padding: 8px 10px;
      font: 12px system-ui, -apple-system, Segoe UI, Roboto, Arial;
      box-shadow: 0 10px 30px rgba(0,0,0,0.35);
      display: none;
      max-width: 280px;
      z-index: 5;
      white-space: pre-line;
    }

    .statusbar {
      padding: 10px 16px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
    }

    .statusbar .danger { color: var(--danger); }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <p class="hint">Toggle subjects to show/hide. Click a class block to select/deselect; overlaps are allowed. Export saves your selected schedule as a PNG.</p>
      <div id="subjectList"></div>
    </aside>

    <section class="main">
      <div class="toolbar">
        <div>
          <div class="title">Weekly timetable</div>
          <div class="meta" id="metaLine"></div>
        </div>
        <div style="flex:1"></div>
        <button class="btn" id="clearBtn">Clear selection</button>
        <button class="btn" id="exportBtn">Export PNG</button>
      </div>

      <div class="canvas-wrap">
        <canvas id="tt" width="1100" height="720"></canvas>
        <div id="tooltip"></div>
      </div>

      <div class="statusbar">
        <span id="statusText">Ready.</span>
      </div>
    </section>
  </div>

<script>
  const DATA = __PAYLOAD_JSON__;

  const DAYS = DATA.meta.days.map(d => d.key);
  const START_MIN = DATA.meta.startMin;
  const END_MIN = DATA.meta.endMin;

  const subjects = DATA.subjects; // keyed by subjectCode
  const courses = DATA.courses.slice();

  // UI state
  const visibleSubjects = new Set(Object.keys(subjects));
  const selectedCourseIds = new Set();

  // Canvas layout
  const canvas = document.getElementById('tt');
  let ctx = canvas.getContext('2d');
  const tooltip = document.getElementById('tooltip');

  const layout = {
    pad: 18,
    headerH: 36,
    timeColW: 70,
    dayColW: 190,
    rowMinStep: 30, // 30-min grid
    blockPad: 6,
    corner: 10,
  };

  // Precompute hitboxes per render
  let hitboxes = []; // {id, x,y,w,h}
  let hoverId = null;

  function minuteToY(minute) {
    const usableH = canvas.height - layout.pad*2 - layout.headerH;
    const total = END_MIN - START_MIN;
    const t = (minute - START_MIN) / total;
    return layout.pad + layout.headerH + t * usableH;
  }

  function yToMinute(y) {
    const usableH = canvas.height - layout.pad*2 - layout.headerH;
    const total = END_MIN - START_MIN;
    const t = (y - (layout.pad + layout.headerH)) / usableH;
    return START_MIN + t * total;
  }

  function formatTime(min) {
    const h = Math.floor(min / 60);
    const m = min % 60;
    return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
  }

  function overlaps(a, b) {
    return a.day === b.day && a.startMin < b.endMin && b.startMin < a.endMin;
  }

  function subjectColor(code) {
    return subjects[code]?.color || '#6b7280';
  }

  function setStatus(text, isDanger=false) {
    const el = document.getElementById('statusText');
    el.textContent = text;
    el.className = isDanger ? 'danger' : '';
  }

  function buildSidebar() {
    const wrap = document.getElementById('subjectList');
    wrap.innerHTML = '';

    Object.values(subjects).forEach(sub => {
      const div = document.createElement('div');
      div.className = 'subject';

      const sw = document.createElement('div');
      sw.className = 'swatch';
      sw.style.background = sub.color;
      div.appendChild(sw);

      const box = document.createElement('div');
      const label = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = true;
      cb.addEventListener('change', () => {
        if (cb.checked) visibleSubjects.add(sub.code);
        else visibleSubjects.delete(sub.code);
        render();
      });
      const text = document.createElement('div');
      text.innerHTML = `<div class="name">${escapeHtml(sub.name)}</div><div class="code">${escapeHtml(sub.code)} · ${sub.credits} credits</div>`;
      label.appendChild(cb);
      label.appendChild(text);
      box.appendChild(label);
      div.appendChild(box);

      wrap.appendChild(div);
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }

  function truncateText(ctxRef, text, maxWidth) {
    let t = String(text);
    if (ctxRef.measureText(t).width <= maxWidth) return t;
    while (t.length > 0 && ctxRef.measureText(t + '...').width > maxWidth) {
      t = t.slice(0, -1);
    }
    return t.length ? t + '...' : '...';
  }

  function roundRect(x,y,w,h,r) {
    const rr = Math.min(r, w/2, h/2);
    ctx.beginPath();
    ctx.moveTo(x+rr, y);
    ctx.arcTo(x+w, y, x+w, y+h, rr);
    ctx.arcTo(x+w, y+h, x, y+h, rr);
    ctx.arcTo(x, y+h, x, y, rr);
    ctx.arcTo(x, y, x+w, y, rr);
    ctx.closePath();
  }

  function drawGrid() {
    ctx.clearRect(0,0,canvas.width,canvas.height);

    // Background
    ctx.fillStyle = 'rgba(255,255,255,0.015)';
    ctx.fillRect(0,0,canvas.width,canvas.height);

    const x0 = layout.pad + layout.timeColW;
    const y0 = layout.pad + layout.headerH;
    const x1 = canvas.width - layout.pad;
    const y1 = canvas.height - layout.pad;

    // Header background
    ctx.fillStyle = 'rgba(255,255,255,0.03)';
    ctx.fillRect(layout.pad, layout.pad, canvas.width - 2*layout.pad, layout.headerH);

    // Day headers
    ctx.font = '600 13px system-ui, -apple-system, Segoe UI, Roboto, Arial';
    ctx.fillStyle = 'rgba(229,231,235,0.95)';
    ctx.textBaseline = 'middle';

    for (let di=0; di<DAYS.length; di++) {
      const x = x0 + di * layout.dayColW;
      const label = DATA.meta.days[di].label;
      ctx.fillText(label, x + 10, layout.pad + layout.headerH/2);

      // Column separators
      ctx.strokeStyle = 'rgba(255,255,255,0.10)';
      ctx.beginPath();
      ctx.moveTo(x, layout.pad);
      ctx.lineTo(x, y1);
      ctx.stroke();
    }

    // Right border
    ctx.strokeStyle = 'rgba(255,255,255,0.10)';
    ctx.beginPath();
    ctx.moveTo(x1, layout.pad);
    ctx.lineTo(x1, y1);
    ctx.stroke();

    // Horizontal time grid
    const step = layout.rowMinStep;
    const firstLine = Math.ceil(START_MIN / step) * step;
    ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
    ctx.fillStyle = 'rgba(156,163,175,0.95)';
    ctx.textAlign = 'right';

    for (let t = firstLine; t <= END_MIN; t += step) {
      const y = minuteToY(t);
      const isHour = (t % 60) === 0;
      ctx.strokeStyle = isHour ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)';
      ctx.beginPath();
      ctx.moveTo(layout.pad, y);
      ctx.lineTo(x1, y);
      ctx.stroke();

      if (isHour) {
        ctx.fillText(formatTime(t), layout.pad + layout.timeColW - 10, y);
      }
    }

    // Time separator
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.beginPath();
    ctx.moveTo(x0, layout.pad);
    ctx.lineTo(x0, y1);
    ctx.stroke();

    ctx.textAlign = 'left';
  }

  function computeDayLanes(dayCourses) {
    // Simple interval partitioning: assigns each course to a lane so overlaps get side-by-side.
    // Returns [{course, lane, laneCount}]
    const lanes = []; // each lane holds last endMin
    const placed = [];

    const sorted = dayCourses.slice().sort((a,b) => a.startMin - b.startMin || a.endMin - b.endMin);
    for (const c of sorted) {
      let laneIndex = -1;
      for (let i=0;i<lanes.length;i++) {
        if (c.startMin >= lanes[i]) { laneIndex = i; break; }
      }
      if (laneIndex === -1) {
        lanes.push(c.endMin);
        laneIndex = lanes.length - 1;
      } else {
        lanes[laneIndex] = c.endMin;
      }
      placed.push({course: c, lane: laneIndex});
    }

    const laneCount = lanes.length || 1;
    return placed.map(p => ({...p, laneCount}));
  }

  function drawCourses({exportMode=false} = {}) {
    hitboxes = [];

    const x0 = layout.pad + layout.timeColW;
    const yBottom = canvas.height - layout.pad;

    for (let di=0; di<DAYS.length; di++) {
      const day = DAYS[di];
      const dayX = x0 + di * layout.dayColW;
      const dayW = layout.dayColW;

      let dayCourses = courses.filter(c => c.day === day && visibleSubjects.has(c.subjectCode));
      if (exportMode) {
        dayCourses = dayCourses.filter(c => selectedCourseIds.has(c.id));
      }

      const placed = computeDayLanes(dayCourses);

      for (const p of placed) {
        const c = p.course;
        const yStart = minuteToY(c.startMin);
        const yEnd = minuteToY(c.endMin);
        const h = Math.max(16, yEnd - yStart);

        const laneGap = 6;
        const usableW = dayW - 2*layout.blockPad;
        const laneW = (usableW - laneGap*(p.laneCount-1)) / p.laneCount;
        const x = dayX + layout.blockPad + p.lane * (laneW + laneGap);
        const y = Math.min(yBottom - 10, yStart + 1);
        const w = Math.max(30, laneW);

        const isSelected = selectedCourseIds.has(c.id);
        const fill = subjectColor(c.subjectCode);

        // Draw block
        ctx.save();
        ctx.globalAlpha = isSelected ? 0.95 : 0.28;
        ctx.fillStyle = fill;
        roundRect(x, y, w, h, layout.corner);
        ctx.fill();

        // Border
        ctx.globalAlpha = 1;
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.strokeStyle = isSelected ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.25)';
        if (!isSelected && !exportMode) {
          ctx.setLineDash([6,4]);
        }
        roundRect(x, y, w, h, layout.corner);
        ctx.stroke();
        ctx.restore();

        // Text
        ctx.save();
        ctx.fillStyle = 'rgba(17,24,39,0.92)';
        ctx.globalAlpha = isSelected ? 0.85 : 0.65;
        const pad = 9;
        const maxTextW = Math.max(12, w - pad * 2);

        ctx.font = '700 12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        const line1Full = `(${c.courseCode}) ${c.subjectName}`;
        const line1 = truncateText(ctx, line1Full, maxTextW);
        ctx.fillText(line1, x+pad, y+16);

        ctx.font = '600 12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        const line2 = truncateText(ctx, `(${c.subjectCode})`, maxTextW);
        ctx.fillText(line2, x+pad, y+32);

        ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        const line3Full = `${formatTime(c.startMin)}–${formatTime(c.endMin)}`;
        const line3Width = ctx.measureText(line3Full).width;
        const twoLineY1 = y + 44;
        const twoLineY2 = y + 58;
        const canTwoLine = twoLineY2 <= y + h - 6;

        if (line3Width <= maxTextW || !canTwoLine) {
          const line3 = truncateText(ctx, line3Full, maxTextW);
          ctx.fillText(line3, x+pad, y+48);
        } else {
          ctx.fillText(formatTime(c.startMin), x+pad, twoLineY1);
          ctx.fillText(formatTime(c.endMin), x+pad, twoLineY2);
        }
        ctx.restore();

        if (!exportMode) {
          hitboxes.push({id: c.id, x, y, w, h});
        }
      }
    }
  }

  function render() {
    drawGrid();
    drawCourses();

    const selectedCount = selectedCourseIds.size;
    setStatus(`Selected classes: ${selectedCount}.`);
  }

  function findCourseById(id) {
    return courses.find(c => c.id === id);
  }

  function toggleSelection(id) {
    const course = findCourseById(id);
    if (!course) return;

    if (selectedCourseIds.has(id)) {
      selectedCourseIds.delete(id);
      setStatus(`Deselected ${course.subjectCode} / ${course.courseCode}.`);
      render();
      return;
    }

    selectedCourseIds.add(id);

    setStatus(`Selected ${course.subjectCode} / ${course.courseCode}.`);

    render();
  }

  function courseAtPoint(x, y) {
    // Top-most block wins (last drawn). hitboxes is in draw order; reverse scan.
    for (let i=hitboxes.length-1; i>=0; i--) {
      const b = hitboxes[i];
      if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) {
        return b.id;
      }
    }
    return null;
  }

  function setTooltip(id, clientX, clientY) {
    if (!id) {
      tooltip.style.display = 'none';
      hoverId = null;
      return;
    }
    if (hoverId === id && tooltip.style.display === 'block') return;

    const c = findCourseById(id);
    if (!c) {
      tooltip.style.display = 'none';
      hoverId = null;
      return;
    }

    hoverId = id;
    const subj = subjects[c.subjectCode];
    const titleLine = `(${c.courseCode}) ${c.subjectName}`;
    const codeLine = `(${c.subjectCode})`;
    const timeLine = `${formatTime(c.startMin)}–${formatTime(c.endMin)}`;
    const subjCredits = subj ? ` · ${subj.credits} credits` : '';

    tooltip.innerHTML = `${escapeHtml(titleLine)}\n${escapeHtml(codeLine)}${escapeHtml(subjCredits)}\n${escapeHtml(timeLine)}`;
    tooltip.style.display = 'block';

    const wrapRect = canvas.parentElement.getBoundingClientRect();
    const tipRect = tooltip.getBoundingClientRect();
    const padding = 10;
    let x = clientX - wrapRect.left + 12;
    let y = clientY - wrapRect.top + 12;

    if (x + tipRect.width + padding > wrapRect.width) {
      x = wrapRect.width - tipRect.width - padding;
    }
    if (y + tipRect.height + padding > wrapRect.height) {
      y = wrapRect.height - tipRect.height - padding;
    }

    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  }

  canvas.addEventListener('click', (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const id = courseAtPoint(x, y);
    if (id) toggleSelection(id);
  });

  canvas.addEventListener('mousemove', (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const id = courseAtPoint(x, y);
    setTooltip(id, ev.clientX, ev.clientY);
  });

  canvas.addEventListener('mouseleave', () => {
    setTooltip(null, 0, 0);
  });

  document.getElementById('clearBtn').addEventListener('click', () => {
    selectedCourseIds.clear();
    setStatus('Cleared selection.');
    render();
  });

  document.getElementById('exportBtn').addEventListener('click', () => {
    if (selectedCourseIds.size === 0) {
      setStatus('Nothing selected to export.', true);
      return;
    }

    // Render export image on an offscreen canvas with only selected courses.
    const off = document.createElement('canvas');
    off.width = canvas.width;
    off.height = canvas.height;
    const offCtx = off.getContext('2d');

    const saved = ctx;
    ctx = offCtx;
    drawGrid();
    drawCourses({exportMode:true});
    ctx = saved;

    const url = off.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `timetable_${DATA.meta.csv.replace(/[^a-z0-9_-]+/gi,'_')}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    setStatus('Exported PNG.');
  });

  // Basic metadata
  document.getElementById('metaLine').textContent = `${DATA.meta.csv} · ${formatTime(START_MIN)}–${formatTime(END_MIN)}`;

  // Initial build
  buildSidebar();
  render();
</script>
</body>
</html>
"""

    return template.replace("__PAYLOAD_JSON__", payload_json)


def generate_html(csv_path: str, out_path: str) -> None:
    payload = _build_payload(csv_path)
    payload_json = json.dumps(payload, ensure_ascii=False)
    html = _html_template(payload_json)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate interactive timetable HTML from CSV")
    parser.add_argument("--csv", required=True, help="Path to timetable CSV")
    parser.add_argument("--out", required=True, help="Output HTML path")
    args = parser.parse_args(argv)

    generate_html(args.csv, args.out)
    print(f"Wrote {args.out}")
    print("Open it in a browser. Use 'Export PNG' to save the selected schedule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
