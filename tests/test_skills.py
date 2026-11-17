"""בדיקות למבנה הסקילים ולניסוח."""
import re
import shlex

import pytest

from engine import cli

SKILLS = ["irish-funds-basics", "irish-funds-finder", "portfolio-builder", "portfolio-templates", "portfolio-checkup",
          "funds-performance"]
FORBIDDEN = ["תשואה מובטחת", "מומלץ לקנות", "כדאי לקנות", "כדאי למכור", "בלי סיכון", "ללא סיכון",
             "רווח בטוח", "רווח מובטח", "המלצת קנייה"]


def _read(root, name):
    return (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_exactly_the_expected_skills_exist(root):
    found = sorted(p.name for p in (root / "skills").iterdir() if p.is_dir())
    assert found == sorted(SKILLS)


@pytest.mark.parametrize("name", SKILLS)
def test_frontmatter_is_valid(root, name):
    text = _read(root, name)
    m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", text)
    assert m, "חסר frontmatter תקין"
    assert m.group(1) == name
    assert 60 <= len(m.group(2)) <= 1024
    assert "להשתמש כש" in m.group(2), "התיאור צריך להגיד מתי להשתמש בסקיל"


@pytest.mark.parametrize("name", SKILLS)
def test_skill_points_to_disclaimer_and_sets_first_rule(root, name):
    text = _read(root, name)
    assert "DISCLAIMER.md" in text
    assert "## הכלל הראשון" in text


@pytest.mark.parametrize("name", SKILLS)
def test_fund_numbers_in_skill_exist_in_data(root, data, name):
    numbers = {f["tase_number"] for f in data["funds"]["funds"]}
    numbers |= {r["tase_number"] for r in data["funds"]["non_irish_references"]}
    for number in re.findall(r"\b[15]\d{6}\b", _read(root, name)):
        assert number in numbers, f"מספר נייר {number} לא נמצא בדאטה"


def test_fees_quoted_in_finder_skill_match_data(root, data):
    by_num = {f["tase_number"]: f for f in data["funds"]["funds"]}
    text = _read(root, "irish-funds-finder")
    assert f"דמי ניהול {by_num['1159250']['fee_pct']:.2f} אחוז" in text
    assert f"דמי ניהול {by_num['1183441']['fee_pct']:.2f} אחוז" in text
    assert f"{by_num['1183441']['extra_fee_pct']:.2f} אחוז" in text


def test_templates_skill_documents_every_option_in_data(root, data):
    """כל גרסה שקיימת בדאטה מתועדת בסקיל, עם מספר הנייר הנכון."""
    text = _read(root, "portfolio-templates")
    tri = data["portfolios"]["templates"][2]
    for spec in tri["options"].values():
        for key in spec["choices"]:
            assert f"`{key}`" in text, key
            if key in tri["funds"]:
                assert tri["funds"][key] in text
    for t in data["portfolios"]["templates"]:
        assert f"תיק {t['number']}: " in text
        assert f"--template {t['id']}" in text
    assert "שליש לכל אחת" in text


def test_fund_count_quoted_in_skills_matches_data(root, data):
    count = str(len(data["funds"]["funds"]))
    assert f"{count} קרנות" in _read(root, "irish-funds-basics")
    assert f"{count} קרנות" in _read(root, "irish-funds-finder")


def test_skills_never_quote_returns_from_memory(root):
    """אף סקיל חוץ מסקיל הביצועים לא מכיל מספרי תשואה, והוא עצמו מחייב נתונים טריים."""
    perf = _read(root, "funds-performance")
    assert "לא מצטטים תשואות מהזיכרון" in perf and "מביאים את המספרים מחדש" in perf
    assert "תשואות עבר אינן מבטיחות" in perf
    for name in ["portfolio-builder", "portfolio-templates", "portfolio-checkup", "irish-funds-basics"]:
        assert "funds-performance" in _read(root, name)


def test_caps_in_builder_skill_match_data(root, data):
    text = _read(root, "portfolio-builder")
    caps = {(c["question"], c["option"]): c["max_equity_pct"] for c in data["questionnaire"]["caps"]}
    assert caps == {("horizon", "lt3"): 30, ("horizon", "3to5"): 50, ("drop", "sell_all"): 50}
    assert "עד 30 אחוז מניות" in text and "עד 50 אחוז מניות" in text


def test_no_forbidden_phrases_anywhere(root):
    files = list((root / "skills").rglob("*.md")) + list(root.glob("*.md")) + list((root / "docs").glob("*.html"))
    files += list((root / "data").glob("*.json"))
    assert len(files) > 12
    for path in files:
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN:
            assert phrase not in text, f"{path.name}: ניסוח אסור '{phrase}'"


def test_disclaimer_file_says_what_it_must(root):
    text = (root / "DISCLAIMER.md").read_text(encoding="utf-8")
    for needle in ["אינו ייעוץ השקעות", "אינו שיווק השקעות", "תשואות עבר", "רישיון"]:
        assert needle in text


def test_cli_commands_quoted_in_docs_actually_run(root, capsys):
    """כל פקודת engine.cli שמופיעה בסקילים וב-README חייבת לרוץ בלי שגיאה."""
    example = str(root / "examples" / "answers-balanced.json")
    commands = set()
    for path in list((root / "skills").rglob("*.md")) + [root / "README.md"]:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("python3 -m engine.cli ") and " quiz" not in line:
                commands.add(line)
    assert len(commands) >= 8
    for command in sorted(commands):
        argv = shlex.split(command)[3:]
        argv = [example if a in ("answers.json", "examples/answers-balanced.json") else a for a in argv]
        assert cli.main(argv) == 0, command
    assert "אינו ייעוץ השקעות" in capsys.readouterr().out


def test_cli_returns_error_code_on_bad_input(capsys):
    assert cli.main(["checkup", "--holdings", "{}"]) == 1
    assert cli.main(["checkup", "--holdings", "not json"]) == 1
    assert "שגיאה" in capsys.readouterr().err


def test_readme_lists_every_skill_and_live_pages(root):
    text = (root / "README.md").read_text(encoding="utf-8")
    for name in SKILLS:
        assert f"`{name}`" in text
    for page in ["tik.html", "kranot.html", "dmei-nihul.html"]:
        assert page in text
