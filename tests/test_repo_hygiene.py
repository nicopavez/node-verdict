from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = chr(0x2014)
SUFFIXES = {".py", ".md", ".toml", ".txt", ".json", ".csv", ".yml", ".yaml"}


def test_no_em_dashes_anywhere():
    # House rule for everything written in this repo.
    bad = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or "egg-info" in str(path) or not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if EM_DASH in path.read_text(encoding="utf-8", errors="ignore"):
            bad.append(str(path.relative_to(ROOT)))
    assert bad == []
