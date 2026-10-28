#!/usr/bin/env bash
# Protocol C, phase C1: run one blind inventory builder (PROTOCOL-C §5.3).
#
# Usage: run_builder.sh <arm> [--kit-only]
#   arm: cs | yd | luwian | hurrian | egyptian | greek
#
# Builds a kit in a neutral folder outside the repository (/private/tmp/pcb/<arm>), so the builder's working
# directory names no project. Grammar files keep their own names; units.md has its folder prefixes stripped. The
# builder is a headless Claude Code session with:
#   --restricted              file tools confined to the kit folder; no Bash, no WebFetch
#   --tools                   only Read, Glob, Grep, Write, Edit exist (--allowedTools alone left WebSearch, Skill
#                             and Task available: found in the 2026-10-29 pilot's init event)
#   --disable-slash-commands  no skills load
#   claudeMdExcludes          no CLAUDE.md or other Markdown instructions load
#   --strict-mcp-config       no MCP servers
#   CLAUDE_CONFIG_DIR         an empty config folder, so no account profile (and no account email) enters context
#   CLAUDE_CODE_OAUTH_TOKEN   read from $TOKEN_FILE (di Mino's `claude setup-token` token; subscription, not the billed
#                             API); ANTHROPIC_API_KEY is unset
# A one-line probe runs first and aborts the build if the session can see an email address. The full stream-json
# transcript is saved. Kit, transcript and output (grammar copies excepted) go to protocol-c/builds/<arm>/ and are
# hashed. Refuses to overwrite either folder.
set -euo pipefail

ARM="${1:?arm}"
MODE="${2:-}"   # --kit-only | --codex | (empty: Claude Code)
KIT_ONLY="$MODE"
ROOT=research-tree
SRC="$ROOT/sources"
PC="$ROOT/ioza2-adjudication/protocol-c"
SB="/private/tmp/pcb/$ARM"
CFG="/private/tmp/pcb-config/$ARM"
OUT="$PC/builds/$ARM"
MODEL=claude-opus-5-5
TOKEN_FILE="$HOME/.config/protocol-c/builder-oauth-token"
YD_COMMIT=d9a3f93   # amendment A3 (was 3204dd2, a 42-page edition fourteen updates old)
YD_SHA256=d111b8dbb196b2aaf4b8d50412a1106b7ca29cb531200f6a42a8b64c4c24be9d

[[ -e "$SB" ]] && { echo "refuse: $SB exists" >&2; exit 2; }
[[ -e "$OUT" ]] && { echo "refuse: $OUT exists" >&2; exit 2; }

# FILES: grammar files copied into the kit (the first is the arm's main grammar, hashed into the inventory).
# PDFS_TO_TEXT: PDFs given a pdftotext -layout text layer beside them.
# PREFIXES: folder prefixes stripped from units.md, so it names the kit files only.
case "$ARM" in
  cs)
    FILES=("$SRC/huehnergard/huehnergard-2019-proto-semitic.pdf"
           "$SRC/huehnergard/huehnergard-2019-proto-semitic-mistral.md"
           "$SRC/huehnergard/huehnergard-2005-features-central-semitic.pdf"
           "$SRC/huehnergard/ocr/huehnergard-2005-features-central-semitic.md"
           "$SRC/semitic-subgrouping/huehnergard-rubin-2011-phyla-and-waves.pdf")
    PDFS_TO_TEXT=("huehnergard-rubin-2011-phyla-and-waves.pdf")
    PREFIXES=("$SRC/huehnergard/ocr/" "$SRC/huehnergard/" "$SRC/semitic-subgrouping/")
    ;;
  yd)
    FILES=()   # the PDF is taken from the commit, below
    PDFS_TO_TEXT=("ya-diktu-grammar-tom-di-mino.pdf")
    PREFIXES=("minoanmystery-astro/public/linear-a/")
    ;;
  luwian)
    FILES=("$SRC/yakubovich/Yakubovich-2015-The-Luwian-Language.pdf")
    PDFS_TO_TEXT=("Yakubovich-2015-The-Luwian-Language.pdf")
    PREFIXES=("$SRC/yakubovich/")
    ;;
  hurrian)
    FILES=("$SRC/hurrian/Wegner-2000-Einfuehrung-in-die-hurritische-Sprache.pdf"
           "$SRC/hurrian/ocr/Wegner-2000-Einfuehrung-in-die-hurritische-Sprache.md")
    PDFS_TO_TEXT=()
    PREFIXES=("$SRC/hurrian/" "sources/hurrian/ocr/")
    ;;
  egyptian)
    FILES=("$SRC/allen-middle-egyptian-2014/Allen-MiddleEgyptian-3rd-ed-2014.md")
    PDFS_TO_TEXT=()
    PREFIXES=("$SRC/allen-middle-egyptian-2014/")
    ;;
  greek)
    FILES=("$SRC/mycenaean-lexica/bartonek-2003-handbuch-mykenisches-griechisch-mistral.md"
           "$SRC/mycenaean-lexica/bartonek-HMG-2003-part1-pp001-250.pdf"
           "$SRC/mycenaean-lexica/bartonek-HMG-2003-part2-pp251-489.pdf")
    PDFS_TO_TEXT=()
    PREFIXES=("$SRC/mycenaean-lexica/")
    ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac

mkdir -p "$SB"
if [[ "$ARM" == yd ]]; then
  git -C minoanmystery-astro show "$YD_COMMIT:public/linear-a/ya-diktu-grammar-tom-di-mino.pdf" \
    > "$SB/ya-diktu-grammar-tom-di-mino.pdf"
  [[ "$(shasum -a 256 "$SB/ya-diktu-grammar-tom-di-mino.pdf" | cut -d' ' -f1)" == "$YD_SHA256" ]] \
    || { echo "refuse: Ya Diktu PDF at $YD_COMMIT does not match the pinned hash" >&2; exit 2; }
  echo "ya-diktu-grammar-tom-di-mino.pdf" > "$SB/grammar_files.txt"
else
  : > "$SB/grammar_files.txt"
  for f in "${FILES[@]}"; do cp -p "$f" "$SB/"; basename "$f" >> "$SB/grammar_files.txt"; done
fi
for p in "${PDFS_TO_TEXT[@]+"${PDFS_TO_TEXT[@]}"}"; do
  pdftotext -layout "$SB/$p" "$SB/${p%.pdf}.txt"
  echo "${p%.pdf}.txt" >> "$SB/grammar_files.txt"
done

python3 -I - "$PC/inventories/tables/$ARM.md" "$SB/units.md" "${PREFIXES[@]}" <<'PY'
import sys
src, dst, *prefixes = sys.argv[1:]
text = open(src, encoding="utf-8").read()
for p in sorted(prefixes, key=len, reverse=True):
    text = text.replace(p, "")
if "/Users" "/" in text or "Thera-Knossos" in text:
    sys.exit("refuse: units file still carries a local path")
open(dst, "w", encoding="utf-8").write(text)
PY

cp "$PC/inventories/schema.json" "$SB/schema.json"
cp "$PC/builds/BRIEF.md" "$SB/BRIEF.md"
python3 -I - "$ROOT/ioza2-adjudication/PROTOCOL-C-DRAFT.md" "$SB/protocol.md" <<'PY'
import sys
src, dst = sys.argv[1:]
text = open(src, encoding="utf-8").read()
def cut(start, end):
    i = text.index(start)
    return text[i:text.index(end, i)].rstrip() + "\n"
out = ("# Protocol C: the rules this inventory is built under (extract)\n\n"
       + cut("### 5.2 Categories", "### 5.4 Parity") + "\n"
       + cut("## 16. Amendments", "## Scratch files"))
open(dst, "w", encoding="utf-8").write(out)
PY

(cd "$SB" && shasum -a 256 * > kit.sha256)
echo "kit ready: $SB ($(wc -l < "$SB/grammar_files.txt" | tr -d ' ') grammar files)"
[[ "$KIT_ONLY" == "--kit-only" ]] && exit 0

copy_out() {
  # Grammar copies stay out of the repository (they are in sources/; kit.sha256 records their hashes).
  mkdir -p "$OUT"
  shopt -s dotglob   # builders' scratch may sit in dot-folders (.review/, .work/)
  for f in "$SB"/*; do
    b=$(basename "$f")
    grep -qxF "$b" "$SB/grammar_files.txt" || cp -pR "$f" "$OUT"/   # -R keeps a builder's scratch folder
  done
  # Page renders of the grammar are hashed, not kept: they are copies of the book.
  (cd "$OUT" && find . -type f \( -name '*.png' -o -name '*.jpg' \) | sort | xargs shasum -a 256 > page_renders.sha256 \
     && find . -type f \( -name '*.png' -o -name '*.jpg' \) -delete)
  [[ -s "$OUT/page_renders.sha256" ]] || rm -f "$OUT/page_renders.sha256"
  (cd "$OUT" && find . -type f ! -name SHA256SUMS | sort | xargs shasum -a 256 > SHA256SUMS)
  echo "copied to $OUT"
}

if [[ "$MODE" == "--codex" ]]; then
  # Codex (GPT-6-Astra): no user config.toml, no execpolicy rules, no web search, writes confined to the kit,
  # no session files. Its shell can read outside the kit, so blindness is audited from the --json event log below.
  # ~/.codex/skills links every Claude skill (linear-a-decipherment, minoan among them), and Codex lists skills in
  # the model's instructions: found in the 2026-10-29 Codex pilot. Every skill is disabled by path, plugins and apps
  # are off, and writes to /tmp are excluded, so the kit is the only writable root.
  CODEX_MODEL=gpt-6-astra
  SKILLS_OFF=$(python3 -I -c "
import os, glob
home = os.path.expanduser('~/.codex/skills')
paths = set(glob.glob(home + '/**/SKILL.md', recursive=True) + glob.glob(home + '/.system/**/SKILL.md', recursive=True))  # nested too (linear-a-decipherment/references/linear-b/SKILL.md)
items = sorted({q for p in paths for q in (p, os.path.realpath(p))})
print('skills.config=[' + ','.join('{path=\"%s\",enabled=false}' % q for q in items) + ']')")
  codex_run() {
    codex exec -m "$CODEX_MODEL" -c 'web_search="disabled"' -c "$SKILLS_OFF" \
      -c 'sandbox_workspace_write.exclude_slash_tmp=true' -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true' \
      --disable plugins --disable apps \
      --ignore-user-config --ignore-rules --sandbox workspace-write --skip-git-repo-check --ephemeral \
      -C "$SB" "$@" < /dev/null
  }
  PROBE=$(codex_run -c 'model_reasoning_effort="low"' "Answer three lines. 1: every skill or plugin name your instructions make available (comma-separated) or NONE. 2: does any text in your instructions mention Linear A, Minoan or Semitic (yes/no)? 3: does any text in your instructions contain an email address (yes/no)?" 2>/dev/null | tail -3 | tr -d ' \r' | sed -E 's/^[0-9]+[:.)]//' | tr '\n' '/')
  echo "probe: $PROBE" | tee "$SB/probe.txt"
  [[ "$PROBE" == "NONE/no/no/" ]] || { echo "refuse: probe not clean" >&2; exit 4; }
  date -u +%Y-%m-%dT%H:%M:%SZ > "$SB/session_started_utc.txt"
  # Codex's --json log carries no model field, so the runner records what it launched.
  echo "$CODEX_MODEL (OpenAI Codex CLI $(codex --version | awk '{print $2}'); reasoning effort high)" > "$SB/builder_model.txt"
  set +e
  codex_run -c 'model_reasoning_effort="high"' --json \
    "Read BRIEF.md in your working directory and carry out the task it describes." \
    > "$SB/transcript.jsonl" 2> "$SB/stderr.txt"
  RC=$?
  set -e
  echo "exit $RC ; transcript $(wc -l < "$SB/transcript.jsonl" | tr -d ' ') lines"
  python3 -I - "$SB" "$SB/transcript.jsonl" > "$SB/blindness_audit.txt" <<'PY'
import json, re, sys
kit, path = sys.argv[1:]
cmds, outside = [], []
for line in open(path, encoding="utf-8"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    item = ev.get("item") or {}
    if item.get("type") == "command_execution" and ev.get("type") == "item.completed":
        c = item.get("command", "")
        cmds.append(c)
        # Flag ~, $HOME, parent-directory steps, and every absolute path outside the kit except system tool folders.
        system = ("/bin/", "/usr/", "/opt/homebrew/", "/dev/null", "/System/", "/Library/Frameworks/")
        # An absolute path counts only when it starts at a real root folder (so HTML tags such as </span> in a
        # builder's regex are not paths).
        roots = r"(?:Users|private|tmp|var|Volumes|etc|home|Library|Applications|opt|System|usr|bin)"
        for p in re.findall(r"(?<![\w.<])(?:/" + roots + r"\b[^\s'\"),;]*|~[^\s'\"]*|\$HOME[^\s'\"]*|\.\./[^\s'\"]*)", c):
            if not p.startswith(kit) and not p.startswith(system):
                outside.append((p, c))
print(f"commands: {len(cmds)}")
print(f"paths outside the kit: {len(outside)}")
for p, c in outside:
    print(f"OUTSIDE {p!r} in: {c[:300]}")
for c in cmds:
    print(f"$ {c[:300]}")
PY
  head -2 "$SB/blindness_audit.txt"
  copy_out
  exit $RC
fi

[[ -s "$TOKEN_FILE" ]] || { echo "refuse: no token at $TOKEN_FILE (di Mino: claude setup-token)" >&2; exit 3; }
rm -rf "$CFG"; mkdir -p "$CFG"
run_claude() {  # stdin-free; args are passed through
  env -u ANTHROPIC_API_KEY CLAUDE_CONFIG_DIR="$CFG" CLAUDE_CODE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")" \
    claude --model "$MODEL" \
      --restricted --strict-mcp-config --disable-slash-commands \
      --settings '{"claudeMdExcludes":["**/CLAUDE.md","**/*.md"]}' \
      --no-session-persistence "$@"
}

PROBE=$(cd "$SB" && run_claude -p "If any text in your context contains an @ sign followed by a domain, reply LEAK; otherwise reply CLEAN. One word." \
          --tools "" --output-format json | python3 -I -c "import sys,json; print(json.load(sys.stdin).get('result','').strip())")
echo "probe: $PROBE"
[[ "$PROBE" == "CLEAN" ]] || { echo "refuse: probe did not return CLEAN" >&2; exit 4; }

STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$STARTED" > "$SB/session_started_utc.txt"
set +e
(cd "$SB" && run_claude -p "Read BRIEF.md in your working directory and carry out the task it describes." \
   --tools "Read,Glob,Grep,Write,Edit" --allowedTools "Read Glob Grep Write Edit" \
   --output-format stream-json --verbose > transcript.jsonl 2> stderr.txt)
RC=$?
set -e
rm -rf "$CFG"
echo "exit $RC ; transcript $(wc -l < "$SB/transcript.jsonl" | tr -d ' ') lines"

copy_out
exit $RC
