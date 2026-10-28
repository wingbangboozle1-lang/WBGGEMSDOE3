"""The README must carry the verbatim user prompt from PROJECT_PROMPT.md (no silent drift)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _prompt_body() -> str:
    text = (ROOT / "PROJECT_PROMPT.md").read_text(encoding="utf-8")
    assert "\n---\n" in text, "PROJECT_PROMPT.md must separate its header from the verbatim prompt"
    return text.split("\n---\n", 1)[1].strip("\n") + "\n"


def test_readme_embeds_verbatim_prompt():
    body = _prompt_body()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert body in readme, "README verbatim prompt differs from PROJECT_PROMPT.md"


def test_readme_no_longer_labels_paraphrase_as_verbatim():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Standing brief — verbatim (user, 2026-10-28)" not in readme


def test_readme_states_current_decision_and_verification_link():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "knowledge/verification-2026-10-28.md" in readme
    assert "SUBMIT A UNIQUE FILE" in readme
