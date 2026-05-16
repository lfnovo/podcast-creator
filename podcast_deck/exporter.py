"""Deck HTML exporter."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
from pathlib import Path

from .schema import DeckDocument, DeckSlide, parse_deck
from .timeline import SlideCue

DEFAULT_TOKENS_CSS = """
:root {
  --deck-bg: #0b1220;
  --deck-fg: #f8fafc;
  --deck-accent: #38bdf8;
  --deck-muted: #94a3b8;
  --deck-gap: 1rem;
  --deck-radius: 12px;
  --deck-font-size: 18px;
}
""".strip()

DEFAULT_THEME_CSS = """
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--deck-bg);
  color: var(--deck-fg);
}
.deck-root {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.deck-frame {
  width: min(1200px, 100%);
  aspect-ratio: 16 / 9;
  border-radius: var(--deck-radius);
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: linear-gradient(160deg, rgba(56, 189, 248, 0.1), rgba(15, 23, 42, 0.92));
  overflow: hidden;
  position: relative;
}
.deck-slide {
  position: absolute;
  inset: 0;
  padding: 52px;
  display: none;
  flex-direction: column;
  gap: var(--deck-gap);
}
.deck-slide.is-active { display: flex; }
.deck-slide h1 {
  margin: 0;
  font-size: 2rem;
}
.deck-card {
  font-size: var(--deck-font-size);
  line-height: 1.5;
  padding: 14px 16px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.52);
  border: 1px solid rgba(148, 163, 184, 0.28);
}
.deck-progress {
  position: absolute;
  right: 16px;
  bottom: 12px;
  font-size: 13px;
  color: var(--deck-muted);
}
.deck-debug-highlight {
  outline: 2px dashed #f59e0b;
  outline-offset: 2px;
}
""".strip()

DEFAULT_PRINT_CSS = """
@media print {
  html, body {
    background: #fff !important;
    color: #111 !important;
  }
  .deck-root { padding: 0; }
  .deck-frame {
    width: 100%;
    aspect-ratio: auto;
    border: none;
    background: transparent;
  }
  .deck-slide {
    display: block !important;
    position: relative;
    page-break-after: always;
    min-height: 100vh;
    background: #fff;
    color: #111;
  }
  .deck-progress { display: none; }
}
""".strip()

DEFAULT_RUNTIME_JS = """
(function () {
  const slides = Array.from(document.querySelectorAll('.deck-slide'));
  const progress = document.getElementById('deck-progress');
  let current = 0;

  function render(index) {
    current = Math.max(0, Math.min(index, slides.length - 1));
    slides.forEach((slide, i) => {
      slide.classList.toggle('is-active', i === current);
      slide.setAttribute('aria-hidden', i === current ? 'false' : 'true');
    });
    if (progress) {
      progress.textContent = `${current + 1} / ${slides.length}`;
      progress.setAttribute('aria-live', 'polite');
    }
  }

  function go(delta) {
    render(current + delta);
  }

  window.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight') { go(1); }
    else if (event.key === 'ArrowLeft') { go(-1); }
    else if (event.key === 'Home') { render(0); }
    else if (event.key === 'End') { render(slides.length - 1); }
  });

  render(0);
})();
""".strip()

DEFAULT_DEBUG_JS = """
(function () {
  const params = new URLSearchParams(window.location.search);
  if (params.get('debug') !== '1') return;

  let last = null;
  document.addEventListener('mousemove', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (last && last !== target) last.classList.remove('deck-debug-highlight');
    target.classList.add('deck-debug-highlight');
    last = target;
  });

  document.addEventListener('contextmenu', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    event.preventDefault();
    const styles = window.getComputedStyle(target);
    const snippet = [
      `color: ${styles.color};`,
      `background: ${styles.background};`,
      `font-size: ${styles.fontSize};`,
      `margin: ${styles.margin};`,
      `padding: ${styles.padding};`,
    ].join('\\n');
    try {
      await navigator.clipboard.writeText(snippet);
      console.info('[deck debug] copied computed CSS');
    } catch (error) {
      console.warn('[deck debug] copy failed', error);
    }
  });
})();
""".strip()

DECK_DEBUG_MARKERS = (
    "[deck debug] copied computed CSS",
    "navigator.clipboard.writeText",
    "URLSearchParams(window.location.search)",
)


@dataclass(slots=True)
class DeckBuildOptions:
    debug_script_enabled: bool = False
    aspect_ratio: str = "16:9"
    title_fallback: str = "Podcast Deck"
    audio_src: str | None = None
    timeline_cues: list[SlideCue] | None = None
    audio_autoplay: bool = False


def _read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_slide(slide: DeckSlide, index: int) -> str:
    lines = slide.normalized_content_lines()
    body = "\n".join(
        f"<div class=\"deck-card\">{html.escape(line)}</div>" for line in lines
    )
    return (
        f"<section class=\"deck-slide\" data-slide-id=\"{html.escape(slide.id)}\" "
        f"data-slide-index=\"{index}\" aria-hidden=\"true\">{body}</section>"
    )


def _build_timeline_js(cues: list[SlideCue]) -> str:
    payload = [
        {"slideId": cue.slide_id, "startSec": cue.start_sec, "endSec": cue.end_sec}
        for cue in cues
    ]
    cues_json = json.dumps(payload, ensure_ascii=False)
    return f"""
(function () {{
  const audio = document.getElementById('deck-audio');
  if (!audio) return;
  const cues = {cues_json};
  if (!Array.isArray(cues) || cues.length === 0) return;

  const slideNodes = Array.from(document.querySelectorAll('.deck-slide'));
  const progress = document.getElementById('deck-progress');
  function activateBySlideId(slideId) {{
    let activeIndex = 0;
    slideNodes.forEach((node, idx) => {{
      const isActive = node.getAttribute('data-slide-id') === slideId;
      if (isActive) activeIndex = idx;
      node.classList.toggle('is-active', isActive);
      node.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    }});
    if (progress) {{
      progress.textContent = `${{activeIndex + 1}} / ${{slideNodes.length}}`;
      progress.setAttribute('aria-live', 'polite');
    }}
  }}

  function onTimeUpdate() {{
    const t = Number(audio.currentTime || 0);
    for (const cue of cues) {{
      if (t >= cue.startSec && t < cue.endSec + 0.001) {{
        activateBySlideId(cue.slideId);
        return;
      }}
    }}
  }}

  audio.addEventListener('timeupdate', onTimeUpdate);
}})();
""".strip()


def _build_html(document: DeckDocument, options: DeckBuildOptions) -> str:
    slide_markup = "\n".join(
        _render_slide(slide, index) for index, slide in enumerate(document.slides)
    )
    runtime_js = DEFAULT_RUNTIME_JS
    debug_js = DEFAULT_DEBUG_JS if options.debug_script_enabled else ""
    timeline_js = (
        _build_timeline_js(options.timeline_cues)
        if options.timeline_cues
        else ""
    )
    title = document.meta.title or options.title_fallback
    aspect_style = "16 / 9" if options.aspect_ratio == "16:9" else "4 / 3"
    audio_markup = ""
    if options.audio_src:
        audio_markup = (
            f"<audio id=\"deck-audio\" controls "
            f"{'autoplay' if options.audio_autoplay else ''} "
            f"src=\"{html.escape(options.audio_src)}\"></audio>"
        )

    return f"""<!doctype html>
<html lang="{html.escape(document.meta.lang)}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{DEFAULT_TOKENS_CSS}</style>
  <style>.deck-frame {{ aspect-ratio: {aspect_style}; }}</style>
  <style>{DEFAULT_THEME_CSS}</style>
  <style>{DEFAULT_PRINT_CSS}</style>
</head>
<body>
  <main class="deck-root">
    <div class="deck-frame">
      {slide_markup}
      <div id="deck-progress" class="deck-progress">1 / {len(document.slides)}</div>
    </div>
  </main>
  {audio_markup}
  <script>{runtime_js}</script>
  {"<script>" + timeline_js + "</script>" if timeline_js else ""}
  {"<script>" + debug_js + "</script>" if debug_js else ""}
</body>
</html>
"""


def export_deck(
    input_path: Path, output_path: Path, options: DeckBuildOptions | None = None
) -> Path:
    """Export deck JSON as a single HTML file."""
    build_options = options or DeckBuildOptions()
    data = _read_json_file(input_path)
    document = parse_deck(data)
    html_text = _build_html(document, build_options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path
