"""The summaries at the top of the Linear A and Semitic roots indexes: prose written in `summaries/<name>.md`, its
numbers filled in from the data at every build, so a summary never states a count the data has left behind.

A template is Markdown with `{field}` slots; `fields_*` give every slot its value, and a slot no function fills is an
error, never an empty gap. Counts print with a thousands comma.
"""
from __future__ import annotations

import json
import string
from collections import Counter
from pathlib import Path

from .counts import translation_counts
from .model import Model

TEMPLATES = Path(__file__).with_name("summaries")
# the folder whose index carries each summary
FOLDERS = {"linear-a": "wiki/linear-a", "semitic-roots": "wiki/semitic-roots"}


def _num(value: int) -> str:
    return f"{value:,}"


def fields_linear_a(model: Model) -> dict[str, str]:
    lexicon = list(model.lexicon.values())
    tiers = Counter(e.get("confidence") for e in lexicon)
    layers = Counter(e.get("language_layer") for e in lexicon)
    field_counts = Counter(e.get("semantic_field") for e in lexicon)
    complete, _ = translation_counts({k: t["raw"] for k, t in model.translations.items()})
    summary = model.sign_values["resolution_summary"]
    values = summary["total"] + summary["proposed"]["phonemic_count"] + summary["proposed"]["logogram_count"]
    out = {
        "lexicon": len(lexicon), "records": len(model.corpus),
        "sites": len({r.get("site") for r in model.corpus.values() if r.get("site")}),
        "semitic": layers["Semitic"], "hurrian": layers["Hurrian"], "egyptian": layers["Middle Egyptian"],
        "aegean": layers["Aegean"], "with_root": sum(1 for e in lexicon if e.get("proto_semitic")),
        "confirmed": tiers["CONFIRMED"], "probable": tiers["PROBABLE"], "candidate": tiers["CANDIDATE"],
        "speculative": tiers["SPECULATIVE"],
        "personal_names": field_counts["personal_name"], "commodities": field_counts["commodity"],
        "administrative": field_counts["administrative"], "personnel": field_counts["personnel"],
        "ritual": field_counts["ritual"], "toponyms": field_counts["toponym"], "divine": field_counts["divine"],
        "translations": len(model.translations), "complete": complete, "names": len(model.onomasticon),
        "sign_values": values, "unread": len(model.unread),
        # an unread word no witness shows damaged: its surface_damage names no attestation
        "unread_intact": sum(1 for u in model.unread.values() if not u.get("surface_damage")),
    }
    return {k: _num(v) for k, v in out.items()}


# the languages a roots summary names, as the reflexes label them, and the slot each fills
ROOT_LANGUAGES = {"Arabic": "arabic", "Hebrew": "hebrew", "Akkadian": "akkadian", "Syrian Aramaic": "syriac",
                  "Geez": "geez", "Ugaritic": "ugaritic"}


def fields_roots(roots_data: Path, model: Model) -> dict[str, str]:
    roots = json.loads((roots_data / "semitic_roots.json").read_text(encoding="utf-8"))["roots"]
    reflexes = [x for r in roots for x in r.get("reflexes") or []]
    languages = Counter(x.get("lang") for x in reflexes)
    cites = [c.get("siglum") for x in reflexes for c in x.get("cite") or []]
    basis = Counter((r.get("basis") or {}).get("ps") for r in roots)
    out = {
        "roots": len(roots), "reflexes": len(reflexes), "languages": len(languages), "citations": len(cites),
        "works": len(set(cites)), "sed": basis["sed"] + basis["sed_edited"], "project": basis["project"],
        "with_root": sum(1 for e in model.lexicon.values() if e.get("proto_semitic")),
        **{slot: languages[lang] for lang, slot in ROOT_LANGUAGES.items()},
    }
    return {k: _num(v) for k, v in out.items()}


def template(name: str) -> str:
    """A template's prose: the file without its first-line comment."""
    lines = (TEMPLATES / f"{name}.md").read_text(encoding="utf-8").split("\n")
    while lines and (lines[0].startswith("<!--") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip("\n")


def fill(text: str, fields: dict[str, str]) -> str:
    """`text` with every slot filled; KeyError naming a slot no field fills."""
    slots = {name for _, name, _, _ in string.Formatter().parse(text) if name}
    missing = sorted(slots - set(fields))
    if missing:
        raise KeyError(f"summary slots with no value: {', '.join(missing)}")
    return text.format_map(fields)


def bodies(model: Model, roots_data: Path) -> dict[str, str]:
    """Folder (as a page path, `wiki/…`) -> its summary, for each template whose data is in the checkout."""
    out = {FOLDERS["linear-a"]: fill(template("linear-a"), fields_linear_a(model))}
    if (roots_data / "semitic_roots.json").exists():
        out[FOLDERS["semitic-roots"]] = fill(template("semitic-roots"), fields_roots(roots_data, model))
    return out
