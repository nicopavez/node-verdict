from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = chr(0x2014)
SUFFIXES = {".py", ".md", ".toml", ".txt", ".json", ".csv", ".yml", ".yaml", ".ts", ".tsx", ".css", ".mjs"}
SKIP_DIRS = {".git", "node_modules", ".next", "out", "__pycache__", ".pytest_cache"}


def test_no_em_dashes_anywhere():
    # House rule for everything written in this repo, including the web demo.
    bad = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts) or "egg-info" in str(rel) or not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if EM_DASH in path.read_text(encoding="utf-8", errors="ignore"):
            bad.append(str(rel))
    assert bad == []
