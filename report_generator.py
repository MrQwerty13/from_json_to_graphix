import io
import json
import subprocess
from typing import Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def call_ollama(prompt: str, model: str = "tinyllama") -> Optional[str]:
    """Attempt to call local Ollama CLI to generate text. Returns None on failure."""
    try:
        # Use ollama CLI if available: `ollama generate --model <model> --prompt '<prompt>'`
        proc = subprocess.run(
            ["ollama", "generate", "--model", model, "--prompt", prompt],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        return None


def build_prompt_from_summary(summary: str) -> str:
    return (
        "You are an analytics assistant. Given the data summary below, write a concise PDF-style conclusion "
        "pointing out key findings and suggested next steps. Keep it 3-8 short paragraphs.\n\n" + summary
    )


def _prompt_for_graph_explanation(desc: str, stats_text: str) -> str:
    return (
        "You are an analytics assistant. Given the following graph description and statistics, write a clear, concise explanation "
        "(2-4 short sentences) describing what the graph shows, notable patterns, and a possible interpretation.\n\n"
        f"Graph description: {desc}\nStatistics: {stats_text}\n"
    )


def generate_conclusion_and_pdf(summary_text: str, out_path: str, graph_infos=None, try_ollama: bool = True) -> str:
    """Generate conclusion text and a PDF that includes graphs and explanations.

    graph_infos: list of dicts with keys 'path', 'desc', 'type', 'column', 'stats'
    Returns the overall conclusion text.
    """
    graph_infos = graph_infos or []

    # First, get an overall conclusion
    text = None
    if try_ollama:
        prompt = build_prompt_from_summary(summary_text)
        text = call_ollama(prompt)

    if not text:
        text = "Conclusion:\n" + summary_text + "\n\nSuggested next steps: review anomalies, visualize further, and validate with domain experts."

    # For each graph, get an explanation
    explanations = []
    for g in graph_infos:
        stats_text = ""
        try:
            stats_text = json.dumps(g.get("stats", {}), default=str)
        except Exception:
            stats_text = str(g.get("stats", {}))

        exp = None
        if try_ollama:
            p = _prompt_for_graph_explanation(g.get("desc", ""), stats_text)
            exp = call_ollama(p)
        if not exp:
            # Fallback: simple templated explanation
            if g.get("type") in ("hist", "box", "scatter"):
                st = g.get("stats", {})
                exp = f"{g.get('desc')}. Count={st.get('count', 'N/A')}, mean={st.get('mean', 'N/A')}, median={st.get('median', 'N/A')}."
            elif g.get("type") == "bar":
                top = g.get("stats", {}).get("top", {})
                top_items = ", ".join([f"{k}:{v}" for k, v in list(top.items())[:5]])
                exp = f"{g.get('desc')}. Top values: {top_items}."
            else:
                exp = g.get("desc", "Graph") + "."

        explanations.append(exp)

    # Build PDF with images and explanations
    c = canvas.Canvas(out_path, pagesize=letter)
    width, height = letter
    margin = 40
    y = height - margin

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Analysis Report")
    y -= 28

    c.setFont("Helvetica", 11)
    for line in text.split("\n"):
        if y < margin + 60:
            c.showPage(); c.setFont("Helvetica", 11); y = height - margin
        c.drawString(margin, y, line[:1000])
        y -= 14

    # Add graphs with explanations
    for idx, g in enumerate(graph_infos):
        img_path = g.get("path")
        desc = g.get("desc", "")
        expl = explanations[idx] if idx < len(explanations) else ""

        if y < margin + 180:
            c.showPage(); y = height - margin

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, desc[:200])
        y -= 16

        # Draw image if present
        try:
            iw = width - margin * 2
            ih = 160
            c.drawImage(img_path, margin, y - ih, width=iw, height=ih, preserveAspectRatio=True)
            y -= ih + 6
        except Exception:
            # leave space if image can't be drawn
            y -= 6

        c.setFont("Helvetica", 10)
        for line in expl.split("\n"):
            if y < margin + 40:
                c.showPage(); c.setFont("Helvetica", 10); y = height - margin
            c.drawString(margin, y, line[:1000])
            y -= 12

        y -= 8

    c.save()
    return text
