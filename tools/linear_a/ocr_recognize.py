#!/usr/bin/env python3
"""OCR sign recognition for Linear A inscriptions.

Wraps a separate YOLOv8+ViT pipeline project (set LINEAR_A_OCR_DIR to its checkout, which holds
models/detector_best.pt and models/classifier_best.pt) via subprocess, enriches output with phonetic readings from
sign_values.json, and optionally compares against existing corpus transcriptions.

Accepts inscription IDs (resolved via the manifest `inscription_image.py build` writes) or raw
image file paths.

Coverage: 85/~340 signs; 57/85 have confirmed phonetic readings.
Limitations: synthetic-only training, train=val overlap inflating mAP,
4 null-accuracy classes (AB16/65/79/87), gendered livestock variant confusion.

Examples:
  ocr_recognize.py HT87 --json
  ocr_recognize.py HT87 --kind facsimile --json
  ocr_recognize.py /path/to/tablet.png --json
  ocr_recognize.py HT86a HT87 HT88 --json
  ocr_recognize.py --batch ids.txt --json
  ocr_recognize.py HT87 --visualize --output-dir ./vis/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.normalization import normalize_id
from ..paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

SIGN_VALUES_PATH = LINEAR_A_DATA / "sign_values.json"
SIGN_REGISTRY_PATH = LINEAR_A_DATA / "sign-registry.json"
CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
MANIFEST_PATH = CACHE / "linear-a" / "inscription_images.json"

DEFAULT_OCR_DIR = Path(os.environ["LINEAR_A_OCR_DIR"]) if os.environ.get("LINEAR_A_OCR_DIR") else None

DISCLAIMER = (
    "OCR output requires human adjudication before updating the decipherment "
    "model. No automatic promotion of OCR-derived readings."
)


def load_json(path: Path) -> dict:
    return json.loads(require(path, path.name).read_text(encoding="utf-8"))


def build_ab_to_reading_map() -> dict[str, dict]:
    """Two-layer reading lookup: sign_values.json (primary) then sign-registry.json (fallback).

    Also adds OCR variant aliases: logogram keys like *22F get an alias at AB22f
    so the OCR model's class labels resolve directly.
    """
    readings = {}

    sv = load_json(SIGN_VALUES_PATH)
    for reading_name, entry in sv.get("signs", {}).items():
        ab = entry.get("ab_number", "")
        primary = entry.get("primary", {})
        c = primary.get("consonant") or ""
        v = primary.get("vowel") or ""
        value = f"{c}{v}" if (c or v) else reading_name
        readings[ab] = {
            "value": value,
            "source": "sign_values.json",
            "confidence": primary.get("confidence", 0),
        }

    for logo_key, logo_entry in sv.get("logograms", {}).items():
        if logo_key.startswith("_"):
            continue
        commodity = logo_entry.get("commodity", "")
        gloss = logo_entry.get("gloss", "")
        label = f"{commodity}({gloss})" if commodity and gloss else commodity or gloss or logo_key
        readings[logo_key] = {
            "value": label,
            "source": "sign_values.json/logograms",
            "confidence": 0.8,
        }

    reg = load_json(SIGN_REGISTRY_PATH)
    for sign in reg.get("signs", []):
        ab = sign.get("ab_number", "")
        if ab in readings:
            continue
        for r in sign.get("readings", []):
            if r.get("is_primary"):
                readings[ab] = {
                    "value": r.get("value", ab),
                    "source": "sign-registry.json",
                    "confidence": {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}.get(
                        r.get("confidence", ""), 0.5
                    ),
                }
                break

    # OCR variant aliases: *22F → AB22f, *21M → AB21m, *131C → AB131c
    star_re = re.compile(r"^\*(\d+)([A-Za-z]+)$")
    aliases = {}
    for key, entry in readings.items():
        if not key:
            continue
        m = star_re.match(key)
        if m:
            ocr_label = f"AB{m.group(1)}{m.group(2).lower()}"
            if ocr_label not in readings:
                aliases[ocr_label] = entry
    readings.update(aliases)

    return readings


def build_glyph_to_ab_map() -> dict[str, str]:
    """Build Unicode glyph → AB number mapping from sign-registry.json."""
    reg = load_json(SIGN_REGISTRY_PATH)
    glyph_map = {}
    for sign in reg.get("signs", []):
        glyph = sign.get("unicode_glyph") or sign.get("rendering", {}).get("unicode_glyph")
        if glyph and sign.get("ab_number"):
            glyph_map[glyph] = sign["ab_number"]
    return glyph_map


def resolve_targets(raw_targets: list[str], kind: str) -> list[dict]:
    """Resolve inscription IDs or file paths to image paths.

    Returns list of dicts with keys: inscription_id (or None), image_path, kind.
    """
    targets = []
    manifest = None
    norm_index: dict[str, list[str]] = {}

    for target in raw_targets:
        path = Path(target)
        if path.exists() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}:
            targets.append({
                "inscription_id": None,
                "image_path": str(path.resolve()),
                "kind": "raw_path",
            })
            continue

        if manifest is None:
            if not MANIFEST_PATH.exists():
                raise SystemExit(
                    f"Inscription image manifest not found at {MANIFEST_PATH}.\n"
                    f"Build it with: uv run tools/linear_a/inscription_image.py build"
                )
            manifest = load_json(MANIFEST_PATH)
            for key in manifest.get("records", {}):
                norm_index.setdefault(normalize_id(key), []).append(key)

        matches = norm_index.get(normalize_id(target), [])
        if not matches:
            raise SystemExit(f"Unknown inscription ID: {target}")

        record = manifest["records"][matches[0]]
        files = []
        if kind in ("any", "facsimile"):
            files.extend(record.get("facsimiles", []))
        if kind in ("any", "image"):
            files.extend(record.get("images", []))

        existing = [f for f in files if f.get("exists")]
        if not existing:
            all_paths = [f.get("absolute_path", f.get("relative_path", "?")) for f in files]
            raise SystemExit(
                f"No existing {kind} images found for {matches[0]}.\n"
                f"Referenced paths: {', '.join(all_paths) if all_paths else 'none'}"
            )

        for f in existing:
            targets.append({
                "inscription_id": matches[0],
                "image_path": f["absolute_path"],
                "kind": f.get("kind", kind),
            })

    return targets


def run_ocr_inference(
    image_path: str,
    ocr_dir: Path,
    conf_threshold: float,
    top_k: int,
    visualize: bool,
    output_dir: str | None,
) -> dict:
    """Shell out to the OCR project's inference.py and return parsed results."""
    inference_script = ocr_dir / "scripts" / "inference.py"
    if not inference_script.exists():
        raise SystemExit(f"OCR inference script not found: {inference_script}")

    detector = ocr_dir / "models" / "detector_best.pt"
    classifier = ocr_dir / "models" / "classifier_best.pt"
    for model_path in (detector, classifier):
        if not model_path.exists():
            raise SystemExit(
                f"OCR model not found: {model_path}\n"
                f"Train models first — see {ocr_dir}/README.md"
            )

    tmp_dir = CACHE / "linear-a" / "ocr-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", dir=tmp_dir) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "uv", "run", "--project", str(ocr_dir),
            "python", str(inference_script),
            image_path,
            "--mode", "full",
            "--conf-threshold", str(conf_threshold),
            "--top-k", str(top_k),
            "--output", tmp_path,
        ]
        if visualize:
            cmd.append("--visualize")
            if output_dir:
                cmd.extend(["--output-dir", output_dir])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(ocr_dir),
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise SystemExit(f"OCR inference failed (exit {result.returncode}):\n{stderr}")

        raw = Path(tmp_path).read_text(encoding="utf-8")
        if not raw.strip():
            return {"error": "OCR produced empty output", "signs": []}

        data = json.loads(raw)
        if isinstance(data, list):
            return data[0] if data else {"error": "No results", "signs": []}
        return data

    except subprocess.TimeoutExpired:
        raise SystemExit("OCR inference timed out after 300 seconds.")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"OCR output was not valid JSON: {exc}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def enrich_ocr_result(ocr: dict, reading_map: dict[str, dict]) -> dict:
    """Map AB numbers to phonetic readings."""
    sign_sequence = ocr.get("sign_sequence", [])
    phonetic_signs = []

    for ab in sign_sequence:
        if ab in reading_map:
            r = reading_map[ab]
            phonetic_signs.append({
                "ab_number": ab,
                "reading": r["value"],
                "source": r["source"],
            })
        else:
            phonetic_signs.append({
                "ab_number": ab,
                "reading": f"*{ab}",
                "source": "unread",
            })

    phonetic_transcription = "-".join(s["reading"] for s in phonetic_signs)

    return {
        "sign_sequence": sign_sequence,
        "ab_transcription": ocr.get("transcription", "-".join(sign_sequence)),
        "phonetic_signs": phonetic_signs,
        "phonetic_transcription": phonetic_transcription,
        "n_signs_detected": ocr.get("n_signs_detected", len(sign_sequence)),
        "per_sign_details": ocr.get("signs", []),
    }


def parse_corpus_signs(transcription: str, glyph_map: dict[str, str]) -> list[str]:
    """Extract AB-number sign tokens from a corpus transcription.

    Corpus transcriptions use Unicode Linear A glyphs (U+10600-U+1077F).
    This maps each glyph to its AB number via the glyph_map, skipping
    word dividers, numerals, fractions, and line breaks.
    """
    if not transcription:
        return []
    signs = []
    for char in transcription:
        cp = ord(char)
        if char in glyph_map:
            signs.append(glyph_map[char])
        elif 0x10600 <= cp <= 0x1077F:
            signs.append(f"U+{cp:04X}")
        # Skip: word dividers (U+10100-U+1013F), numerals (U+10107-U+10133),
        # fractions (U+10140-U+1018E), line breaks, dashes, spaces
    return signs


def compare_transcriptions(ocr_signs: list[str], corpus_signs: list[str]) -> dict:
    """Left-to-right alignment of OCR vs corpus AB-number signs. Advisory only."""
    if not ocr_signs or not corpus_signs:
        return {
            "comparable": False,
            "reason": "one or both transcriptions empty",
            "agreements": 0,
            "disagreements": 0,
            "agreement_ratio": None,
            "alignment": [],
        }

    alignment = []
    max_len = max(len(ocr_signs), len(corpus_signs))
    agreements = 0
    disagreements = 0

    for i in range(max_len):
        ocr_sign = ocr_signs[i] if i < len(ocr_signs) else None
        corpus_sign = corpus_signs[i] if i < len(corpus_signs) else None
        match = bool(ocr_sign and corpus_sign and ocr_sign == corpus_sign)
        if match:
            agreements += 1
        else:
            disagreements += 1
        alignment.append({
            "position": i,
            "ocr": ocr_sign,
            "corpus": corpus_sign,
            "match": match,
        })

    total = agreements + disagreements
    return {
        "comparable": True,
        "agreements": agreements,
        "disagreements": disagreements,
        "agreement_ratio": round(agreements / total, 3) if total else None,
        "alignment": alignment,
    }


def process_target(
    target: dict,
    reading_map: dict[str, dict],
    glyph_map: dict[str, str],
    corpus: dict | None,
    ocr_dir: Path,
    conf_threshold: float,
    top_k: int,
    visualize: bool,
    output_dir: str | None,
    no_comparison: bool,
) -> dict:
    """Process a single target through OCR + enrichment + comparison."""
    inscription_id = target.get("inscription_id")
    image_path = target["image_path"]

    ocr_raw = run_ocr_inference(
        image_path, ocr_dir, conf_threshold, top_k, visualize, output_dir
    )

    if "error" in ocr_raw and not ocr_raw.get("signs"):
        return {
            "inscription_id": inscription_id,
            "image_path": image_path,
            "image_kind": target.get("kind"),
            "error": ocr_raw["error"],
            "adjudication_required": True,
        }

    enriched = enrich_ocr_result(ocr_raw, reading_map)

    result = {
        "inscription_id": inscription_id,
        "image_path": image_path,
        "image_kind": target.get("kind"),
        "ocr": enriched,
        "adjudication_required": True,
    }

    if inscription_id and corpus and not no_comparison:
        corpus_entry = corpus.get(inscription_id, {})
        corpus_transcription = corpus_entry.get("transcription", "")
        corpus_signs = parse_corpus_signs(corpus_transcription, glyph_map)
        ocr_ab_signs = enriched.get("sign_sequence", [])
        comparison = compare_transcriptions(ocr_ab_signs, corpus_signs)
        result["corpus"] = {
            "transcription": corpus_transcription,
            "signs": corpus_signs,
            "site": corpus_entry.get("site"),
        }
        result["comparison"] = comparison

    return result


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(
        description="OCR sign recognition for Linear A inscriptions.",
        epilog="All output requires human adjudication before updating the decipherment model.",
    )
    parser.add_argument(
        "targets", nargs="*",
        help="Inscription IDs (e.g. HT87) or image file paths",
    )
    parser.add_argument(
        "--kind", choices=["image", "facsimile", "any"], default="facsimile",
        help="Image type for ID resolution (default: facsimile)",
    )
    parser.add_argument(
        "--conf-threshold", type=float, default=0.3,
        help="Detection confidence threshold (default: 0.3)",
    )
    parser.add_argument(
        "--top-k", type=int, default=3,
        help="Top-K predictions per sign (default: 3)",
    )
    parser.add_argument("--visualize", action="store_true", help="Save annotated images")
    parser.add_argument("--output-dir", help="Directory for visualizations")
    parser.add_argument("--json", action="store_true", help="Print structured JSON to stdout")
    parser.add_argument("--no-comparison", action="store_true", help="Skip corpus comparison")
    parser.add_argument("--batch", help="Read IDs from file, one per line")

    args = parser.parse_args()

    raw_targets = list(args.targets or [])
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            raise SystemExit(f"Batch file not found: {args.batch}")
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                raw_targets.append(line)

    if not raw_targets:
        parser.print_help()
        return 1

    ocr_dir = DEFAULT_OCR_DIR
    if ocr_dir is None or not ocr_dir.exists():
        raise SystemExit(
            f"OCR project directory not found: {ocr_dir or '(LINEAR_A_OCR_DIR is not set)'}\n"
            f"Set LINEAR_A_OCR_DIR to the OCR pipeline's checkout."
        )

    targets = resolve_targets(raw_targets, args.kind)
    reading_map = build_ab_to_reading_map()
    glyph_map = build_glyph_to_ab_map()
    corpus = load_json(CORPUS_PATH) if not args.no_comparison else None

    results = []
    for target in targets:
        result = process_target(
            target, reading_map, glyph_map, corpus, ocr_dir,
            args.conf_threshold, args.top_k,
            args.visualize, args.output_dir,
            args.no_comparison,
        )
        results.append(result)

    output = {
        "disclaimer": DISCLAIMER,
        "ocr_project": str(ocr_dir),
        "results": results,
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(DISCLAIMER)
        print()
        for r in results:
            iid = r.get("inscription_id") or "raw image"
            print(f"--- {iid} ({r.get('image_kind', '')}) ---")
            if "error" in r:
                print(f"  Error: {r['error']}")
                continue
            ocr = r.get("ocr", {})
            print(f"  Signs detected: {ocr.get('n_signs_detected', 0)}")
            print(f"  AB transcription: {ocr.get('ab_transcription', '')}")
            print(f"  Phonetic: {ocr.get('phonetic_transcription', '')}")
            if "corpus" in r:
                print(f"  Corpus: {r['corpus'].get('transcription', '')}")
            if "comparison" in r and r["comparison"].get("comparable"):
                comp = r["comparison"]
                print(f"  Agreement: {comp['agreements']}/{comp['agreements'] + comp['disagreements']} ({comp.get('agreement_ratio', '?')})")
            print("  [!] Adjudication required")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
