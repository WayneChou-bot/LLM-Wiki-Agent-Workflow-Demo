from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import html
import math
import os
from pathlib import Path
import re

import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled in the UI
    genai = None
    types = None


ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
SYNTHESIS_DIR = WIKI_DIR / "syntheses"
CONCEPTS_DIR = WIKI_DIR / "concepts"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
TEMPLATES_DIR = ROOT / "templates"


def render_template(name: str, **fields: str) -> str:
    """Load templates/<name> and substitute {{key}} placeholders with fields."""
    text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    for key, value in fields.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


@dataclass(frozen=True)
class AgentProfile:
    label: str
    icon: str
    folder: str
    index_heading: str
    lens: str
    page_title: str
    focus_terms: tuple[str, ...]


AGENTS = {
    "Programming Agent": AgentProfile(
        label="Programming Agent",
        icon="Code",
        folder="programming",
        index_heading="Programming",
        lens="implementation patterns, architecture, integration constraints, and maintainability",
        page_title="Agent Workflow Architecture",
        focus_terms=("architecture", "implementation", "model", "API", "Streamlit", "workflow"),
    ),
    "UI Design Agent": AgentProfile(
        label="UI Design Agent",
        icon="Layout",
        folder="ui-design",
        index_heading="UI Design",
        lens="screen structure, interaction controls, user journeys, and usability risks",
        page_title="LLM Wiki Demo Interface Patterns",
        focus_terms=("interface", "user", "screen", "controls", "demo", "workflow"),
    ),
    "Project Manager Agent": AgentProfile(
        label="Project Manager Agent",
        icon="Milestones",
        folder="project-management",
        index_heading="Project Management",
        lens="goals, scope, roadmap, dependencies, risks, and decisions",
        page_title="LLM Wiki Demo Roadmap",
        focus_terms=("goal", "scope", "roadmap", "risk", "dependencies", "demo"),
    ),
    "Personal Knowledge Agent": AgentProfile(
        label="Personal Knowledge Agent",
        icon="Library",
        folder="personal",
        index_heading="Personal Knowledge",
        lens="learning loops, reflection, review habits, and personal knowledge accumulation",
        page_title="Personal Knowledge Operating Loop",
        focus_terms=("learning", "knowledge", "reflection", "review", "habit", "wiki"),
    ),
}


def slugify(text: str) -> str:
    # `\w` matches Unicode letters (including CJK) and digits in Python 3 strs.
    # Length capped to 80 chars so CJK-heavy slugs do not exceed FS filename limits
    # (UTF-8 CJK = 3 bytes/char -> 240 bytes, well within the typical 255-byte cap).
    slug = re.sub(r"[^\w-]+", "-", text.strip().lower()).strip("-")
    if not slug:
        return "untitled"
    return slug[:80]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def list_markdown_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(path for path in folder.rglob("*.md") if path.is_file())


def wiki_content_pages() -> list[Path]:
    return [path for path in list_markdown_files(WIKI_DIR) if path.name not in {"index.md", "log.md"}]


def system_pages() -> list[Path]:
    return [path for path in [INDEX_FILE, LOG_FILE] if path.exists()]


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip().strip('"')
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def extract_summary(markdown: str) -> str:
    in_summary = False
    for line in markdown.splitlines():
        if line.strip() == "## Summary":
            in_summary = True
            continue
        if in_summary and line.startswith("## "):
            break
        if in_summary and line.strip():
            return line.strip().lstrip("- ").strip()
    return "Compiled wiki page."


def extract_sentences(markdown: str, terms: tuple[str, ...], limit: int = 5) -> list[str]:
    body = re.sub(r"---.*?---", "", markdown, flags=re.DOTALL)
    candidates = re.split(r"(?<=[.!?。])\s+|\n\n+", body)
    matches: list[str] = []
    lowered_terms = tuple(term.lower() for term in terms)
    for candidate in candidates:
        cleaned = " ".join(candidate.replace("#", "").split())
        if len(cleaned) < 40:
            continue
        if any(term in cleaned.lower() for term in lowered_terms):
            matches.append(cleaned)
    if not matches:
        matches = [" ".join(part.replace("#", "").split()) for part in candidates if len(part.strip()) > 40]
    return matches[:limit]


def page_link(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def relative_link(from_path: Path, to_path: Path) -> str:
    """Relative markdown link from from_path's directory to to_path."""
    rel = os.path.relpath(to_path, from_path.parent)
    return rel.replace(os.sep, "/")


def existing_pages_for_prompt(new_target: Path) -> list[dict]:
    """All other compiled wiki pages with metadata, paths relative to new_target."""
    items: list[dict] = []
    new_resolved = new_target.resolve() if new_target.exists() else new_target
    for path in wiki_content_pages():
        try:
            if path.resolve() == new_resolved:
                continue
        except FileNotFoundError:
            pass
        text = read_text(path)
        items.append(
            {
                "title": extract_title(text, path.stem.replace("-", " ").title()),
                "summary": extract_summary(text),
                "rel_path": relative_link(new_target, path),
            }
        )
    return items


def _refresh_related_pages_section(path: Path, new_block: str) -> None:
    """In-place rewrite of the `## Related Pages` block in a markdown page."""
    text = read_text(path)
    pattern = re.compile(r"(## Related Pages\n\n)(.*?)(?=\n## )", re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub(lambda m: f"{m.group(1)}{new_block}\n\n", text)
    elif "## Source\n" in text:
        new_text = text.replace(
            "## Source\n",
            f"## Related Pages\n\n{new_block}\n\n## Source\n",
            1,
        )
    else:
        new_text = text.rstrip() + f"\n\n## Related Pages\n\n{new_block}\n"
    if new_text != text:
        write_text(path, new_text)


def _refresh_siblings_related_pages(written_target: Path, source_title: str) -> None:
    """After writing `written_target`, refresh every sibling page that shares this source.

    Karpathy-style maintenance: ingesting a new perspective updates the Related
    Pages section of every existing sibling so cross-references stay symmetric.
    """
    siblings = related_same_source(written_target, source_title)
    for sibling_meta in siblings:
        sibling_path = (written_target.parent / sibling_meta["rel_path"]).resolve()
        if not sibling_path.exists():
            continue
        sibling_related = related_same_source(sibling_path, source_title)
        if sibling_related:
            block = "\n".join(
                f"- [{item['title']}]({item['rel_path']}) — {item['summary']}"
                for item in sibling_related
            )
        else:
            block = "- (no other agent perspectives on this source yet)"
        _refresh_related_pages_section(sibling_path, block)


def related_same_source(new_target: Path, source_title: str) -> list[dict]:
    """Existing wiki pages compiled from the same raw source as new_target."""
    items: list[dict] = []
    new_resolved = new_target.resolve() if new_target.exists() else new_target
    needle_a = f'sources: "{source_title}"'
    needle_b = f'sources: {source_title}'
    for path in wiki_content_pages():
        try:
            if path.resolve() == new_resolved:
                continue
        except FileNotFoundError:
            pass
        text = read_text(path)
        if needle_a in text or needle_b in text:
            items.append(
                {
                    "title": extract_title(text, path.stem.replace("-", " ").title()),
                    "summary": extract_summary(text),
                    "rel_path": relative_link(new_target, path),
                }
            )
    return items


def create_raw_source(title: str, body: str, source: str = "manual paste") -> Path:
    today = date.today().isoformat()
    clean_title = title.strip() or "Untitled Source"
    target = RAW_DIR / f"{slugify(clean_title)}.md"
    content = f"""---
title: {clean_title}
source: {source}
collected: {today}
published: Unknown
---

# {clean_title}

{body.strip()}
"""
    write_text(target, content)
    append_log("source", f"Added raw source: {clean_title}", [f"Created: {page_link(target)}"])
    return target


def fetch_url_as_markdown(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, plain-text body). Stdlib only, no deps."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 LLM-Wiki-Demo"})
    with urllib.request.urlopen(req, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw_html = response.read().decode(charset, errors="replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1).strip()) if title_match else url
    title = " ".join(title.split())[:200]
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", raw_html, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.IGNORECASE)
    body = re.sub(r"</(p|div|h[1-6]|li|ul|ol|tr|td|th|article|section|header|footer|blockquote)[^>]*>",
                  "\n\n", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", "", body)
    body = html.unescape(body)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return title, body.strip()


def append_log(kind: str, message: str, items: list[str] | None = None) -> None:
    today = date.today().isoformat()
    lines = [f"\n## [{today}] {kind} | {message}"]
    for item in items or []:
        lines.append(f"\n- {item}")
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write("".join(lines) + "\n")


def get_gemini_api_key() -> str:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        secret_key = ""
    return str(secret_key).strip()


def call_gemini(prompt: str, api_key: str, model: str) -> str:
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed. Run `pip install -r requirements.txt` in the conda environment.")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.25, top_p=0.9),
    )
    return (getattr(response, "text", "") or "").strip()


def strip_markdown_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_markdown_links(markdown: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown)


def resolve_local_link(source: Path, link: str) -> Path | None:
    if re.match(r"^[a-z]+://", link) or link.startswith("#"):
        return None
    clean = link.split("#", 1)[0].strip()
    if not clean:
        return None
    return (source.parent / clean).resolve()


def rebuild_index() -> None:
    sections = {
        "Programming": WIKI_DIR / "programming",
        "UI Design": WIKI_DIR / "ui-design",
        "Project Management": WIKI_DIR / "project-management",
        "Personal Knowledge": WIKI_DIR / "personal",
        "Concepts": CONCEPTS_DIR,
        "Syntheses": SYNTHESIS_DIR,
    }
    lines = [
        "# Knowledge Base Index",
        "",
        "This index is maintained by the demo app. It lists compiled wiki pages by agent domain.",
        "",
    ]
    for heading, folder in sections.items():
        lines.append(f"## {heading}")
        lines.append("")
        pages = list_markdown_files(folder)
        if not pages:
            lines.append("No pages yet.")
            lines.append("")
            continue
        for path in pages:
            text = read_text(path)
            title = extract_title(text, path.stem.replace("-", " ").title())
            # Links are relative to index.md, which lives at wiki/index.md,
            # so Obsidian / standard Markdown resolves them correctly.
            rel = path.relative_to(WIKI_DIR).as_posix()
            lines.append(f"- [{title}]({rel}) - {extract_summary(text)}")
        lines.append("")
    write_text(INDEX_FILE, "\n".join(lines).strip() + "\n")


def build_agent_page(agent: AgentProfile, raw_path: Path) -> tuple[Path, str]:
    raw = read_text(raw_path)
    source_title = extract_title(raw, raw_path.stem.replace("-", " ").title())
    today = date.today().isoformat()
    # Page is named after the source so every new raw source adds a new page
    # instead of overwriting the previous one. Re-ingesting the same source
    # by the same agent still updates the same file (slug is deterministic).
    page_title = source_title
    target = WIKI_DIR / agent.folder / f"{slugify(source_title)}.md"
    findings = extract_sentences(raw, agent.focus_terms)
    key_points = "\n".join(f"- {item}" for item in findings[:4])
    implications = {
        "programming": [
            "Keep the app file-based first so Obsidian remains a first-class viewer.",
            "Defer model API integration until the ingest and query loop is easy to explain.",
            "Treat `AGENTS.md` as the behavioral contract for future automation.",
        ],
        "ui-design": [
            "Expose the workflow as a small number of stable tabs.",
            "Keep raw sources, compiled pages, and operations visually separate.",
            "Show durable markdown output immediately after every operation.",
        ],
        "project-management": [
            "Use the demo to prove the smallest useful loop before adding infrastructure.",
            "Separate phase one workflow validation from phase two LLM API integration.",
            "Track risks in the wiki so decisions survive beyond the live demo.",
        ],
        "personal": [
            "Make each useful answer eligible for archival as a synthesis page.",
            "Use the log as a lightweight reflection trail.",
            "Prefer repeated small ingests over large, unreviewed knowledge dumps.",
        ],
    }[agent.folder]
    implication_lines = "\n".join(f"- {item}" for item in implications)
    source_rel = page_link(raw_path)
    related_items = related_same_source(target, source_title)
    if related_items:
        related_lines = "\n".join(
            f"- [{item['title']}]({item['rel_path']}) — {item['summary']}"
            for item in related_items
        )
    else:
        related_lines = (
            "- (no other agent perspectives on this source yet — re-ingest with "
            "another agent to grow the cross-references)"
        )
    summary_line = f"From the {agent.label} lens, `{source_title}` is most useful for {agent.lens}."
    content = render_template(
        "article.md",
        title=page_title,
        agent=agent.label,
        date=today,
        sources=source_title,
        raw=source_rel,
        summary=summary_line,
        key_points=key_points,
        implications=implication_lines,
        related_pages=related_lines,
        source_link=f"../../{source_rel}",
    )
    write_text(target, content)
    _refresh_siblings_related_pages(target, source_title)
    rebuild_index()
    append_log("ingest", f"{agent.label} processed {source_title}", [f"Updated: {page_link(target)}"])
    return target, content


def build_gemini_agent_page(agent: AgentProfile, raw_path: Path, api_key: str, model: str) -> tuple[Path, str]:
    raw = read_text(raw_path)
    source_title = extract_title(raw, raw_path.stem.replace("-", " ").title())
    today = date.today().isoformat()
    # Page filename follows the source so each ingest grows the wiki instead of
    # overwriting a fixed-name page.
    page_title = source_title
    target = WIKI_DIR / agent.folder / f"{slugify(source_title)}.md"
    related_items = existing_pages_for_prompt(target)
    if related_items:
        related_block_for_prompt = "\n".join(
            f"- [{item['title']}]({item['rel_path']}) — {item['summary']}"
            for item in related_items
        )
    else:
        related_block_for_prompt = "(no other wiki pages exist yet)"
    # Render the article template with deterministic fields filled in; body
    # placeholders ({{summary}}, {{key_points}}, etc.) are left for Gemini.
    shape_for_prompt = render_template(
        "article.md",
        title=page_title,
        agent=agent.label,
        date=today,
        sources=source_title,
        raw=page_link(raw_path),
        source_link=f"../../{page_link(raw_path)}",
    )
    prompt = f"""
You are the {agent.label} maintaining a Karpathy-style LLM Wiki.

Your job is to ingest one raw source into a durable markdown wiki page.

Agent lens:
{agent.lens}

Rules:
- Write Traditional Chinese for explanations, but keep technical terms in English when natural.
- Produce exactly one complete markdown file.
- Do not wrap the answer in code fences.
- Use this exact page title: {page_title}
- Preserve source attribution.
- Focus on durable knowledge, not a temporary chat summary.
- Include practical implications for a Streamlit LLM Wiki demo.
- Do not invent facts not supported by the source.

Cross-referencing (this is what makes the wiki compound — take it seriously):
- The list below is the complete set of other wiki pages that already exist, with the exact relative paths you must use.
- If this source meaningfully relates to any of them (same topic, complementary perspective, contradiction, prerequisite, or deeper detail), add a markdown link inline in the body where it reads naturally, AND list it under `## Related Pages` with a one-line note explaining the relationship.
- Use the relative paths EXACTLY as shown. Do not invent paths or add anchors.
- If no existing page is related, write `- (no related pages yet)` under `## Related Pages`.

Existing wiki pages you may cross-link to:
{related_block_for_prompt}

Required markdown shape (this is loaded from templates/article.md — keep the structure exactly, replace every {{{{...}}}} placeholder with substantive content based on the raw source, keep all other lines as-is):
{shape_for_prompt}

Raw source:
{raw}
"""
    content = strip_markdown_fence(call_gemini(prompt, api_key, model))
    if not content.startswith("---"):
        content = f"""---
title: "{page_title}"
agent: "{agent.label}"
updated: "{today}"
sources: "{source_title}"
raw: "{page_link(raw_path)}"
---

{content}
"""
    write_text(target, content)
    _refresh_siblings_related_pages(target, source_title)
    rebuild_index()
    append_log("ingest", f"{agent.label} used Gemini to process {source_title}", [f"Updated: {page_link(target)}"])
    return target, content


def search_wiki(query: str, limit: int = 6) -> list[Path]:
    # English tokens (start with a letter).
    english_terms = {w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", query)}
    # CJK has no word boundary, so use bigrams as a pragmatic stand-in for proper
    # segmentation. Covers CJK Unified Ideographs + Extension A.
    cjk_terms: set[str] = set()
    for chunk in re.findall(r"[\u3400-\u9fff]+", query):
        if len(chunk) == 1:
            cjk_terms.add(chunk)
        else:
            for i in range(len(chunk) - 1):
                cjk_terms.add(chunk[i:i + 2])
    terms = english_terms | cjk_terms
    pages = wiki_content_pages()
    if not terms:
        return pages[:limit]
    scored: list[tuple[int, Path]] = []
    for path in pages:
        text = read_text(path).lower()
        score = sum(text.count(term) for term in terms)
        if score:
            scored.append((score, path))
    if not scored:
        return pages[:limit]
    return [path for _, path in sorted(scored, reverse=True)[:limit]]


def build_answer(query: str, pages: list[Path]) -> str:
    if not pages:
        return "The wiki does not have enough compiled pages yet. Run an ingest first."
    bullets = []
    for path in pages[:4]:
        text = read_text(path)
        title = extract_title(text, path.stem.replace("-", " ").title())
        bullets.append(f"- [{title}]({page_link(path)}): {extract_summary(text)}")
    return "\n".join(
        [
            f"Based on the current wiki, the answer to `{query}` is:",
            "",
            "The demo should stay centered on the durable workflow: raw sources become maintained wiki pages, agent perspectives create different kinds of structure, and useful answers can be archived back into the knowledge base.",
            "",
            "Relevant wiki pages:",
            *bullets,
        ]
    )


def build_gemini_answer(query: str, pages: list[Path], api_key: str, model: str) -> str:
    if not pages:
        return "The wiki does not have enough compiled pages yet. Run an ingest first."
    context = "\n\n".join(f"## {page_link(path)}\n{read_text(path)}" for path in pages[:6])
    prompt = f"""
You are answering from a local LLM Wiki.

Rules:
- Answer in Traditional Chinese.
- Prefer the wiki context over general knowledge.
- Cite relevant wiki pages using markdown links with the exact paths provided.
- Be practical and concise.
- If the wiki is insufficient, say what source should be ingested next.

Question:
{query}

Wiki context:
{context}
"""
    return strip_markdown_fence(call_gemini(prompt, api_key, model))


def archive_answer(query: str, answer: str, pages: list[Path]) -> Path:
    today = date.today().isoformat()
    title = query.strip().rstrip("?？") or "Archived Wiki Answer"
    target = SYNTHESIS_DIR / f"{slugify(title)[:70]}.md"
    source_links = "\n".join(
        f"- [{extract_title(read_text(path), path.stem)}](../{path.relative_to(WIKI_DIR).as_posix()})"
        for path in pages
    )
    content = render_template(
        "synthesis.md",
        title=title,
        date=today,
        sources="wiki query",
        question=query,
        answer=answer,
        source_pages=source_links or "- No source pages found.",
    )
    write_text(target, content)
    rebuild_index()
    append_log("query", f"Archived: {title}", [f"Created: {page_link(target)}"])
    return target


def find_pages_mentioning(term: str, exclude: Path | None = None) -> list[Path]:
    """Wiki content pages whose body contains `term` (case-insensitive)."""
    needle = term.lower().strip()
    if not needle:
        return []
    items: list[Path] = []
    for path in wiki_content_pages():
        if exclude is not None:
            try:
                if path.resolve() == exclude.resolve():
                    continue
            except FileNotFoundError:
                pass
        if needle in read_text(path).lower():
            items.append(path)
    return items


def _concept_excerpts(name: str, pages: list[Path], limit: int = 6) -> str:
    needle = name.lower()
    excerpts: list[str] = []
    for path in pages[:limit]:
        text = read_text(path)
        for chunk in re.split(r"(?<=[.!?。])\s+|\n\n+", text):
            if needle in chunk.lower() and len(chunk.strip()) > 40:
                cleaned = " ".join(chunk.replace("#", "").split())[:280]
                title = extract_title(text, path.stem)
                excerpts.append(f"- **{title}**: {cleaned}")
                break
    return "\n".join(excerpts) or "- (no concrete excerpts found yet)"


def _other_concepts_block(target: Path) -> str:
    others: list[str] = []
    for path in list_markdown_files(CONCEPTS_DIR):
        try:
            if path.resolve() == target.resolve():
                continue
        except FileNotFoundError:
            pass
        title = extract_title(read_text(path), path.stem)
        others.append(f"- [{title}]({relative_link(target, path)})")
    return "\n".join(others) or "- (no other concept pages yet)"


def build_concept_page(concept_name: str) -> tuple[Path, str]:
    today = date.today().isoformat()
    name = concept_name.strip()
    if not name:
        raise ValueError("Concept name is required")
    target = CONCEPTS_DIR / f"{slugify(name)}.md"
    matching = find_pages_mentioning(name, exclude=target)
    if matching:
        source_links = "\n".join(
            f"- [{extract_title(read_text(p), p.stem)}]({relative_link(target, p)}) — {extract_summary(read_text(p))}"
            for p in matching
        )
    else:
        source_links = "- (no wiki pages mention this concept yet)"
    insights = _concept_excerpts(name, matching)
    related_concepts = _other_concepts_block(target)
    summary = (
        f"`{name}` appears in {len(matching)} wiki page(s). This concept page collects "
        "what those pages say about it across agent perspectives."
    )
    content = render_template(
        "concept.md",
        title=name,
        date=today,
        sources=f"{len(matching)} wiki pages",
        summary=summary,
        insights=insights,
        source_pages=source_links,
        related_concepts=related_concepts,
    )
    write_text(target, content)
    rebuild_index()
    append_log("concept", f"Compiled concept: {name}", [f"Updated: {page_link(target)}"])
    return target, content


def build_gemini_concept_page(concept_name: str, api_key: str, model: str) -> tuple[Path, str]:
    today = date.today().isoformat()
    name = concept_name.strip()
    if not name:
        raise ValueError("Concept name is required")
    target = CONCEPTS_DIR / f"{slugify(name)}.md"
    matching = find_pages_mentioning(name, exclude=target)
    if not matching:
        return build_concept_page(concept_name)
    pages_context_parts: list[str] = []
    page_list_for_links: list[str] = []
    for path in matching[:8]:
        rel = relative_link(target, path)
        title = extract_title(read_text(path), path.stem)
        pages_context_parts.append(f"\n\n=== {title} (path: {rel}) ===\n{read_text(path)}")
        page_list_for_links.append(f"- {title} -> {rel}")
    pages_context = "".join(pages_context_parts)
    page_list_block = "\n".join(page_list_for_links)
    shape = render_template(
        "concept.md",
        title=name,
        date=today,
        sources=f"{len(matching)} wiki pages",
    )
    prompt = f"""
You are compiling a "concept page" for a Karpathy-style LLM Wiki.

The concept is: {name}

The concept page should synthesize what the existing wiki pages say about this concept — a unified view, not a list of disconnected quotes. It is the place a reader goes to learn about this concept across all sources and agent perspectives.

Rules:
- Write Traditional Chinese for explanations, but keep technical terms in English when natural.
- Produce exactly one complete markdown file.
- Do not wrap the answer in code fences.
- Use the page shape provided (templates/concept.md). Replace every {{{{...}}}} placeholder with substantive content.
- The "Source Pages" section MUST list every page below with its exact relative path; the "Related Concepts" section can be left as "- (none yet)" or filled if relevant.
- Cite source pages inline in the body using the exact relative paths shown.
- Do not invent facts not supported by these pages.

Existing wiki pages that mention "{name}" (use these exact paths in citations):
{page_list_block}

Required markdown shape (from templates/concept.md — keep structure exactly, replace placeholders):
{shape}

Full content of the matching wiki pages:
{pages_context}
"""
    content = strip_markdown_fence(call_gemini(prompt, api_key, model))
    if not content.startswith("---"):
        content = render_template(
            "concept.md",
            title=name,
            date=today,
            sources=f"{len(matching)} wiki pages",
            summary=content,
            insights="(see body)",
            source_pages="\n".join(
                f"- [{extract_title(read_text(p), p.stem)}]({relative_link(target, p)})"
                for p in matching
            ),
            related_concepts=_other_concepts_block(target),
        )
    write_text(target, content)
    rebuild_index()
    append_log("concept", f"Compiled (Gemini) concept: {name}", [f"Updated: {page_link(target)}"])
    return target, content


def last_log_message_for(kind: str) -> str | None:
    if not LOG_FILE.exists():
        return None
    pattern = re.compile(rf"^## \[[^\]]+\] {re.escape(kind)} \| (.+)$")
    last = None
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            last = m.group(1).strip()
    return last


def _wiki_inbound_links() -> dict[str, set[str]]:
    """For each wiki content page, the set of other wiki content pages that link to it.

    Index and log do not count as inbound sources (they auto-list everything).
    """
    pages = wiki_content_pages()
    inbound: dict[str, set[str]] = {page_link(p): set() for p in pages}
    for source in pages:
        source_id = page_link(source)
        for _, link in parse_markdown_links(read_text(source)):
            target = resolve_local_link(source, link)
            if target is None:
                continue
            try:
                rel = target.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if rel in inbound and rel != source_id:
                inbound[rel].add(source_id)
    return inbound


def lint_wiki(log_on_change: bool = True) -> list[str]:
    issues: list[str] = []
    if not INDEX_FILE.exists():
        issues.append("Missing wiki/index.md")
    if not LOG_FILE.exists():
        issues.append("Missing wiki/log.md")
    index_text = read_text(INDEX_FILE) if INDEX_FILE.exists() else ""
    for path in wiki_content_pages():
        if path.stat().st_size == 0:
            issues.append(f"Empty page: {page_link(path)}")
        rel_in_index = path.relative_to(WIKI_DIR).as_posix()
        if rel_in_index not in index_text:
            issues.append(f"Index missing page: {page_link(path)}")
        for label, link in parse_markdown_links(read_text(path)):
            target = resolve_local_link(path, link)
            if target and not target.exists():
                issues.append(f"Broken link in {page_link(path)}: {label} -> {link}")
    # Orphan check: pages with no inbound link from any OTHER wiki content page.
    # (index.md / log.md are excluded as sources — they would mask every orphan.)
    inbound = _wiki_inbound_links()
    for page in wiki_content_pages():
        pid = page_link(page)
        if not inbound.get(pid):
            issues.append(
                f"Orphan: {pid} (no inbound links — re-ingest with another agent "
                "or compile a concept page that references it)"
            )
    # Only log a lint outcome when explicitly requested AND it changed since last lint.
    # Default callers (Maintain tab on every render) pass log_on_change=False to keep
    # the page side-effect-free; the explicit "Run lint + record" button passes True.
    if log_on_change:
        summary = f"{len(issues)} issue(s) found" if issues else "0 issues found, 0 auto-fixed"
        if last_log_message_for("lint") != summary:
            details = [f"Issue: {issue}" for issue in issues[:5]] if issues else None
            append_log("lint", summary, details)
    return issues


def collect_graph() -> tuple[dict[str, str], list[tuple[str, str]]]:
    nodes: dict[str, str] = {"raw/": "raw-root", "wiki/": "wiki-root"}
    edges: set[tuple[str, str]] = set()
    for raw_path in list_markdown_files(RAW_DIR):
        raw_id = page_link(raw_path)
        nodes[raw_id] = "raw"
        edges.add(("raw/", raw_id))
    for agent in AGENTS.values():
        nodes[agent.index_heading] = "agent"
        edges.add(("wiki/", agent.index_heading))
    nodes["Concepts"] = "concepts-root"
    edges.add(("wiki/", "Concepts"))
    for page in wiki_content_pages():
        page_id = page_link(page)
        rel_parts = page.relative_to(WIKI_DIR).parts
        is_concept = bool(rel_parts) and rel_parts[0] == "concepts"
        nodes[page_id] = "concept" if is_concept else "page"
        if is_concept:
            edges.add(("Concepts", page_id))
        for agent in AGENTS.values():
            if rel_parts and rel_parts[0] == agent.folder:
                edges.add((agent.index_heading, page_id))
        text = read_text(page)
        raw_match = re.search(r'^raw:\s*"([^"]+)"', text, flags=re.MULTILINE)
        if raw_match:
            raw_id = raw_match.group(1)
            nodes[raw_id] = "raw"
            edges.add((raw_id, page_id))
        for _, link in parse_markdown_links(text):
            target = resolve_local_link(page, link)
            if target and ROOT in target.parents and target.suffix == ".md":
                target_id = page_link(target)
                nodes[target_id] = "page" if target_id.startswith("wiki/") else "raw"
                edges.add((page_id, target_id))
    return nodes, sorted(edges)


def render_svg_graph(nodes: dict[str, str], edges: list[tuple[str, str]]) -> str:
    width, height = 1120, 620
    center_x, center_y = width / 2, height / 2
    ordered = sorted(nodes)
    positions: dict[str, tuple[float, float]] = {}
    ring = [node for node in ordered if node not in {"raw/", "wiki/"}]
    for index, node in enumerate(ring):
        angle = (2 * math.pi * index / max(len(ring), 1)) - math.pi / 2
        radius = 245
        positions[node] = (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
    positions["raw/"] = (center_x - 170, center_y)
    positions["wiki/"] = (center_x + 170, center_y)
    colors = {
        "raw-root": "#58a6ff",
        "wiki-root": "#3fb950",
        "concepts-root": "#ff7b72",
        "raw": "#79c0ff",
        "agent": "#f2cc60",
        "page": "#d2a8ff",
        "concept": "#ff9e64",
    }
    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="620" role="img" aria-label="LLM Wiki graph">',
        '<rect width="100%" height="100%" rx="8" fill="#111418"/>',
    ]
    for source, target in edges:
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#3d444d" stroke-width="1.2"/>')
    for node, kind in nodes.items():
        x, y = positions[node]
        color = colors.get(kind, "#c9d1d9")
        r = 14 if node in {"raw/", "wiki/"} else 8
        label = html.escape(node)
        short = label if len(label) <= 36 else label[:33] + "..."
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#f0f3f6" stroke-width="1"/>')
        lines.append(f'<text x="{x + 13:.1f}" y="{y + 4:.1f}" fill="#f0f3f6" font-size="12" font-family="Segoe UI, sans-serif">{short}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def ensure_structure() -> None:
    for folder in [RAW_DIR, WIKI_DIR, SYNTHESIS_DIR, CONCEPTS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        rebuild_index()
    if not LOG_FILE.exists():
        write_text(LOG_FILE, "# Wiki Log\n")


def configure_page() -> None:
    st.set_page_config(page_title="LLM Wiki Agent Demo", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
        }
        .demo-note {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin-bottom: 1rem;
        }
        .flow-row {
            display: grid;
            grid-template-columns: repeat(5, minmax(110px, 1fr));
            gap: 0.75rem;
            margin: 1rem 0 1.25rem 0;
        }
        .flow-step, .knowledge-card {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 8px;
            padding: 0.9rem;
        }
        .flow-step strong {
            display: block;
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }
        .flow-step span, .knowledge-card span {
            color: rgba(180, 180, 180, 0.95);
            font-size: 0.9rem;
        }
        .knowledge-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 0.85rem;
            margin: 1rem 0;
        }
        .knowledge-card h4 {
            margin: 0 0 0.45rem 0;
            font-size: 1.05rem;
        }
        .tag {
            display: inline-block;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 999px;
            padding: 0.15rem 0.5rem;
            font-size: 0.78rem;
            margin-bottom: 0.45rem;
            font-weight: 600;
        }
        .tag-programming { background: rgba(88, 166, 255, 0.18); border-color: #58a6ff; color: #b6dcff; }
        .tag-ui-design { background: rgba(210, 168, 255, 0.18); border-color: #d2a8ff; color: #ead2ff; }
        .tag-project-management { background: rgba(63, 185, 80, 0.18); border-color: #3fb950; color: #b6f0c4; }
        .tag-personal { background: rgba(242, 204, 96, 0.18); border-color: #f2cc60; color: #ffe7a8; }
        .tag-concepts { background: rgba(255, 158, 100, 0.18); border-color: #ff9e64; color: #ffd4b8; }
        .tag-syntheses { background: rgba(248, 113, 113, 0.18); border-color: #f87171; color: #ffc6c6; }
        .source-group {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            background: rgba(255, 255, 255, 0.015);
        }
        .source-group .source-title {
            margin: 0 0 0.7rem 0;
            font-size: 1.05rem;
            font-weight: 700;
        }
        .source-group .lens-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.6rem;
        }
        .lens-card {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 7px;
            padding: 0.65rem 0.8rem;
            background: rgba(255, 255, 255, 0.02);
        }
        .lens-card .lens-summary {
            color: rgba(200, 200, 200, 0.85);
            font-size: 0.85rem;
            line-height: 1.4;
        }
        @media (max-width: 760px) {
            .flow-row {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, str, str]:
    st.sidebar.header("Gemini")
    api_key = st.sidebar.text_input(
        "API key",
        value=get_gemini_api_key(),
        type="password",
        help="Use GEMINI_API_KEY or paste a temporary key here. The app does not write the key to disk.",
    )
    model = st.sidebar.text_input("Model", value="gemini-2.5-flash")
    use_gemini = st.sidebar.toggle("Use Gemini for agent work", value=True)
    if use_gemini and not api_key:
        st.sidebar.warning("No API key found. The app will use local demo mode.")
    return use_gemini and bool(api_key), api_key, model


def render_sources() -> None:
    st.subheader("Input Materials")
    st.markdown(
        """
        <div class="demo-note">
        Think of these as raw materials: articles, notes, transcripts, meeting records, or documents.
        The agent reads them, but does not rewrite them.
        </div>
        """,
        unsafe_allow_html=True,
    )
    sources = list_markdown_files(RAW_DIR)
    col_a, col_b = st.columns([0.36, 0.64])
    with col_a:
        selected = st.radio("Choose an input", sources, format_func=lambda path: extract_title(read_text(path), path.name), label_visibility="collapsed")
        with st.expander("Add pasted source"):
            title = st.text_input("Title", placeholder="Example: Agent workflow notes")
            body = st.text_area("Content", height=220, placeholder="Paste an article, meeting notes, transcript, or rough notes here.")
            if st.button("Save to raw/", use_container_width=True):
                if body.strip():
                    target = create_raw_source(title, body)
                    st.success(f"Created {page_link(target)}")
                    st.rerun()
                else:
                    st.warning("Paste some content first.")
        with st.expander("Fetch from URL"):
            url = st.text_input("URL", placeholder="https://example.com/article")
            if st.button("Fetch and save to raw/", use_container_width=True, key="fetch_url_btn"):
                clean_url = url.strip()
                if not clean_url:
                    st.warning("Paste a URL first.")
                elif not re.match(r"^https?://", clean_url):
                    st.warning("URL must start with http:// or https://")
                else:
                    try:
                        with st.spinner("Fetching..."):
                            fetched_title, fetched_body = fetch_url_as_markdown(clean_url)
                        target = create_raw_source(fetched_title, fetched_body, source=clean_url)
                        st.success(f"Created {page_link(target)}")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Fetch failed: {error}")
    with col_b:
        if sources:
            st.markdown(read_text(selected))


def render_ingest(use_gemini: bool, api_key: str, model: str) -> None:
    st.subheader("Agent Workbench")
    st.markdown(
        """
        <div class="demo-note">
        Pick one input and choose how the AI should read it. Each agent turns the same material into a different kind of knowledge.
        </div>
        """,
        unsafe_allow_html=True,
    )
    sources = list_markdown_files(RAW_DIR)
    col_a, col_b = st.columns([0.38, 0.62])
    with col_a:
        agent_name = st.selectbox("Perspective", list(AGENTS.keys()))
        raw_path = st.selectbox("Input material", sources, format_func=lambda path: extract_title(read_text(path), path.name))
        run = st.button("Create one knowledge page", type="primary", use_container_width=True)
        run_all = st.button("Create pages from all perspectives", use_container_width=True)
    with col_b:
        profile = AGENTS[agent_name]
        st.markdown(f"**{profile.icon}**")
        st.write(f"Focus: {profile.lens}.")
        if run or run_all:
            try:
                profiles = list(AGENTS.values()) if run_all else [profile]
                results: list[tuple[Path, str]] = []
                progress = st.progress(0)
                for index, active_profile in enumerate(profiles, start=1):
                    if use_gemini:
                        target, content = build_gemini_agent_page(active_profile, raw_path, api_key, model)
                    else:
                        target, content = build_agent_page(active_profile, raw_path)
                    results.append((target, content))
                    progress.progress(index / len(profiles))
                st.success(f"Updated {len(results)} wiki page(s)")
                for target, content in results:
                    with st.expander(page_link(target), expanded=len(results) == 1):
                        st.markdown(content)
            except Exception as error:
                st.error(f"Gemini ingest failed: {error}")


def render_showcase() -> None:
    st.subheader("Showcase")
    # Lead with the Wikipedia analogy so both product and engineering folks
    # land on the same mental model in under 10 seconds.
    st.markdown(
        """
        <div class="demo-note" style="font-size: 1.02rem; line-height: 1.55;">
        <strong>Think of this as your personal Wikipedia.</strong>
        You feed in raw materials (articles, notes, transcripts, URLs).
        LLM agents read each one and write Wikipedia-style pages from different angles.
        Over time you accumulate a structured knowledge base you can ask questions of.
        <br/><br/>
        <strong>What this is NOT:</strong>
        not ChatGPT (useful answers get saved as durable files, not lost in chat history);
        not RAG (sources are compiled into an evolving wiki, not just chunked-and-retrieved on demand);
        not a static notes app (the LLM maintains cross-references, concept pages, and structure as the wiki grows).
        <br/><br/>
        <em>Karpathy-inspired teaching demo with a multi-agent twist —
        <a href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" target="_blank">see the original gist</a>.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Raw materials fed in", len(list_markdown_files(RAW_DIR)))
    col_b.metric("Agent lenses available", len(AGENTS))
    col_c.metric("Wiki pages compiled", len(wiki_content_pages()))
    col_d.metric("Cross-references in graph", len(collect_graph()[1]))

    st.markdown(
        """
        <div class="flow-row">
            <div class="flow-step"><strong>1. Feed materials</strong><span>Articles, notes, URLs → raw/</span></div>
            <div class="flow-step"><strong>2. Run agents</strong><span>Each lens writes a wiki page</span></div>
            <div class="flow-step"><strong>3. Browse knowledge</strong><span>Pages grouped by source</span></div>
            <div class="flow-step"><strong>4. Compile concepts</strong><span>Cross-source synthesis pages</span></div>
            <div class="flow-step"><strong>5. Ask + archive</strong><span>Q&amp;A saved back to wiki</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([0.55, 0.45])
    with col_left:
        st.markdown("### Suggested live demo path")
        st.write("1. **Inputs** → pick a seed source, or paste a URL to fetch one")
        st.write("2. **Agents** → click *Create pages from all perspectives*")
        st.write("3. **Knowledge** → see one source compiled into multiple lens views")
        st.write("4. **Concepts** → type a topic word, get a cross-source synthesis")
        st.write("5. **Map** → watch the graph fill in as the wiki grows")
        st.write("6. **Ask** → ask a question; useful answers archive back to wiki")
        st.write("7. **Maintain** → see lint clean, or what is still orphaned")
    with col_right:
        st.markdown("### For the engineers in the room")
        st.write("- Real markdown files under `wiki/` — open the folder as an Obsidian vault")
        st.write("- `templates/*.md` define the page schema (article / concept / synthesis)")
        st.write("- `AGENTS.md` is the agent contract (Codex / Claude Code compatible)")
        st.write("- Lint flags orphans and broken links; ingest auto-syncs sibling cross-refs")
        st.write("- Gemini-mode prompts include relative paths so the model cross-links correctly")
        st.write("- Pure stdlib URL fetcher; no scraping deps")


def _extract_source_title_from_frontmatter(text: str) -> str | None:
    m = re.search(r'^sources:\s*"?([^"\n]+)"?', text, flags=re.MULTILINE)
    if not m:
        return None
    value = m.group(1).strip().strip('"')
    return value or None


def _agent_label_from_frontmatter(text: str) -> str | None:
    m = re.search(r'^agent:\s*"?([^"\n]+)"?', text, flags=re.MULTILINE)
    if not m:
        return None
    value = m.group(1).strip().strip('"')
    return value or None


def render_wiki() -> None:
    st.subheader("Knowledge Library")
    st.markdown(
        """
        <div class="demo-note">
        Each <strong>source</strong> you fed in is shown as a group below. Inside the group
        are the <strong>lens cards</strong> — one per agent perspective that has compiled
        this source. So "same source, multiple views" is visible at a glance.
        Concept pages (cross-source syntheses) and saved Q&amp;A appear in their own sections.
        </div>
        """,
        unsafe_allow_html=True,
    )
    pages = wiki_content_pages()
    if not pages:
        st.info("No knowledge pages yet. Go to Agents → Create one knowledge page (or all four).")
        return

    by_source: dict[str, list[Path]] = {}
    concept_pages: list[Path] = []
    synthesis_pages: list[Path] = []
    for path in pages:
        text = read_text(path)
        if "type: concept" in text:
            concept_pages.append(path)
            continue
        if "type: synthesis" in text:
            synthesis_pages.append(path)
            continue
        source_title = _extract_source_title_from_frontmatter(text) or "Unknown source"
        by_source.setdefault(source_title, []).append(path)

    if by_source:
        st.markdown("### Sources × agent lenses")
        for source_title, agent_pages in by_source.items():
            agent_pages_sorted = sorted(agent_pages, key=lambda p: page_link(p))
            blocks = [
                f'<div class="source-group">',
                f'<div class="source-title">📄 {html.escape(source_title)} <span style="opacity:0.6; font-weight:400;">— {len(agent_pages_sorted)} lens view(s)</span></div>',
                '<div class="lens-grid">',
            ]
            for path in agent_pages_sorted:
                text = read_text(path)
                domain = path.relative_to(WIKI_DIR).parts[0]
                domain_label = _agent_label_from_frontmatter(text) or domain.replace("-", " ").title()
                summary = extract_summary(text)
                tag_class = f"tag tag-{domain}"
                blocks.append(
                    '<div class="lens-card">'
                    f'<div class="{tag_class}">{html.escape(domain_label)}</div>'
                    f'<div class="lens-summary">{html.escape(summary)}</div>'
                    '</div>'
                )
            blocks.append("</div></div>")
            st.markdown("\n".join(blocks), unsafe_allow_html=True)

    if concept_pages:
        st.markdown("### Concept pages (cross-source synthesis)")
        cards = ['<div class="knowledge-grid">']
        for path in concept_pages:
            text = read_text(path)
            title = extract_title(text, path.stem.replace("-", " ").title())
            summary = extract_summary(text)
            cards.append(
                '<div class="knowledge-card">'
                '<div class="tag tag-concepts">Concept</div>'
                f'<h4>{html.escape(title)}</h4>'
                f'<span>{html.escape(summary)}</span>'
                '</div>'
            )
        cards.append("</div>")
        st.markdown("\n".join(cards), unsafe_allow_html=True)

    if synthesis_pages:
        st.markdown("### Saved Q&A (synthesis pages)")
        cards = ['<div class="knowledge-grid">']
        for path in synthesis_pages:
            text = read_text(path)
            title = extract_title(text, path.stem.replace("-", " ").title())
            summary = extract_summary(text)
            cards.append(
                '<div class="knowledge-card">'
                '<div class="tag tag-syntheses">Q&amp;A</div>'
                f'<h4>{html.escape(title)}</h4>'
                f'<span>{html.escape(summary)}</span>'
                '</div>'
            )
        cards.append("</div>")
        st.markdown("\n".join(cards), unsafe_allow_html=True)

    st.markdown("### Open a page")
    selected = st.selectbox(
        "Open a knowledge page",
        pages,
        format_func=lambda path: f"{(_extract_source_title_from_frontmatter(read_text(path)) or path.stem)} — {(_agent_label_from_frontmatter(read_text(path)) or path.relative_to(WIKI_DIR).parts[0].replace('-', ' ').title())}",
        label_visibility="collapsed",
    )
    st.markdown(read_text(selected))

    with st.expander("System pages: index and log"):
        for page in system_pages():
            st.markdown(f"### {page_link(page)}")
            st.markdown(read_text(page))


def render_concepts(use_gemini: bool, api_key: str, model: str) -> None:
    st.subheader("Concept Pages")
    st.markdown(
        """
        <div class="demo-note">
        A concept page synthesizes what the wiki knows about a topic across every agent perspective.
        It is the <em>compounding</em> layer — agent pages capture one source x one lens; concept pages weave them together.
        </div>
        """,
        unsafe_allow_html=True,
    )
    existing = list_markdown_files(CONCEPTS_DIR)
    col_a, col_b = st.columns([0.4, 0.6])
    with col_a:
        st.markdown("### Compile a concept")
        name = st.text_input("Concept name", placeholder="e.g. ingest, agent workflow, deliberate practice")
        run = st.button("Compile concept page", type="primary", use_container_width=True, key="compile_concept_btn")
        if run:
            if not name.strip():
                st.warning("Concept name required.")
            else:
                try:
                    with st.spinner("Compiling..."):
                        if use_gemini:
                            target, content = build_gemini_concept_page(name, api_key, model)
                        else:
                            target, content = build_concept_page(name)
                    st.success(f"Created {page_link(target)}")
                    with st.expander(page_link(target), expanded=True):
                        st.markdown(content)
                except Exception as error:
                    st.error(f"Concept compile failed: {error}")
    with col_b:
        st.markdown("### Existing concept pages")
        if not existing:
            st.info("No concept pages yet. Compile one on the left.")
        else:
            selected = st.selectbox(
                "Open a concept",
                existing,
                format_func=lambda p: extract_title(read_text(p), p.stem),
                key="concept_view_select",
            )
            st.markdown(read_text(selected))


def render_graph() -> None:
    st.subheader("Knowledge Map")
    st.markdown(
        """
        <div class="demo-note">
        The graph shows how raw sources feed into agent-compiled wiki pages, how pages link back to sources,
        and how concept pages stitch related ideas together across domains. The denser the graph, the more
        navigable the wiki becomes.
        </div>
        """,
        unsafe_allow_html=True,
    )
    nodes, edges = collect_graph()
    st.markdown(render_svg_graph(nodes, edges), unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Nodes", len(nodes))
    col_b.metric("Links", len(edges))
    col_c.metric("Compiled pages", len(wiki_content_pages()))
    with st.expander("What to look for"):
        st.write("- Raw nodes (blue) are your source material.")
        st.write("- Agent root nodes (yellow) show which lens compiled which pages.")
        st.write("- Page nodes (purple) are agent-compiled knowledge pages.")
        st.write("- Concept nodes (orange) are cross-source synthesis pages.")
        st.write("- More cross-links mean the wiki is becoming easier to navigate and query.")


def render_ask(use_gemini: bool, api_key: str, model: str) -> None:
    st.subheader("Ask The Wiki")
    st.write("Ask reads the compiled wiki first. Useful answers can be archived back into the wiki as synthesis pages.")
    query = st.text_input("Question", value="What should be the next step for this LLM App demo?")
    pages = search_wiki(query)
    answer = ""
    if query:
        try:
            answer = build_gemini_answer(query, pages, api_key, model) if use_gemini else build_answer(query, pages)
        except Exception as error:
            st.error(f"Gemini query failed: {error}")
            answer = build_answer(query, pages)
    st.markdown(answer)
    if st.button("Save answer to synthesis", use_container_width=True):
        target = archive_answer(query, answer, pages)
        st.success(f"Archived {page_link(target)}")


def render_health() -> None:
    st.subheader("Maintenance")
    st.markdown(
        """
        <div class="demo-note">
        Read-only health view by default — opening this tab does not modify any files
        or write to the log. Use the action buttons below to explicitly rebuild
        the index or record a lint entry.
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Read-only lint: computes issues but does not append to log or touch index.
    issues = lint_wiki(log_on_change=False)
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Raw sources", len(list_markdown_files(RAW_DIR)))
    col_b.metric("Wiki pages", len(wiki_content_pages()))
    col_c.metric("Graph links", len(collect_graph()[1]))
    col_d.metric("Issues (read-only)", len(issues))

    st.markdown("### Actions")
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        if st.button("Rebuild index", use_container_width=True, key="rebuild_index_btn"):
            rebuild_index()
            append_log("rebuild", "Rebuilt wiki/index.md from current pages")
            st.success("Index rebuilt.")
            st.rerun()
    with bcol2:
        if st.button("Run lint + record to log", use_container_width=True, key="run_lint_btn"):
            fresh_issues = lint_wiki(log_on_change=True)
            st.success(f"Lint complete: {len(fresh_issues)} issue(s) recorded.")
            st.rerun()

    if issues:
        st.warning("Issues found (no log written — click the button above to record)")
        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.success("No issues found")

    st.markdown("### Maintenance checklist")
    st.write("- Every generated page should appear in `wiki/index.md`.")
    st.write("- Local markdown links should point to existing files.")
    st.write("- `wiki/log.md` should record ingest, query archive, and lint operations.")
    st.write("- Orphan pages can be resolved by ingesting another agent on the same source, or by compiling a concept page that references them.")
    st.markdown("### Log")
    st.markdown(read_text(LOG_FILE))


def main() -> None:
    ensure_structure()
    configure_page()
    use_gemini, api_key, model = render_sidebar()
    st.title("LLM Wiki Agent Workflow Demo")
    st.caption("A local markdown wiki where agent perspectives compile raw sources into durable knowledge.")

    tabs = st.tabs(["Showcase", "Inputs", "Agents", "Knowledge", "Concepts", "Map", "Ask", "Maintain"])
    with tabs[0]:
        render_showcase()
    with tabs[1]:
        render_sources()
    with tabs[2]:
        render_ingest(use_gemini, api_key, model)
    with tabs[3]:
        render_wiki()
    with tabs[4]:
        render_concepts(use_gemini, api_key, model)
    with tabs[5]:
        render_graph()
    with tabs[6]:
        render_ask(use_gemini, api_key, model)
    with tabs[7]:
        render_health()


if __name__ == "__main__":
    main()
