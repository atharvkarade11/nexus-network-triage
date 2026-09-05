from pathlib import Path
import re


RUNBOOK_DIR = Path("data/runbooks")


def load_runbooks():
    """Load all markdown runbooks from the runbook directory."""
    runbooks = []

    if not RUNBOOK_DIR.exists():
        return runbooks

    for file_path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")

        runbooks.append({
            "id": file_path.stem,
            "title": extract_title(content, file_path.stem),
            "content": content,
            "source": str(file_path)
        })

    return runbooks


def extract_title(content, fallback):
    """Extract the first markdown heading."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)

    if match:
        return match.group(1).strip()

    return fallback


def tokenize(text):
    """Convert text into normalized keywords."""
    return set(
        re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    )


def search_runbooks(query, top_k=3):
    """
    Retrieve the most relevant runbooks using simple keyword scoring.

    This is intentionally deterministic and does not use Gemini.
    """

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for runbook in load_runbooks():
        document_tokens = tokenize(
            runbook["title"] + " " + runbook["content"]
        )

        matched_tokens = query_tokens.intersection(document_tokens)

        if not matched_tokens:
            continue

        score = len(matched_tokens) / max(len(query_tokens), 1)

        results.append({
            "runbook_id": runbook["id"],
            "title": runbook["title"],
            "source": runbook["source"],
            "score": round(score, 3),
            "matched_terms": sorted(matched_tokens),
            "content": runbook["content"]
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:top_k]


if __name__ == "__main__":
    results = search_runbooks("network link failure")

    for result in results:
        print(
            f"{result['runbook_id']} | "
            f"{result['title']} | "
            f"score={result['score']}"
        )