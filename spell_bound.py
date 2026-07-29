#!/usr/bin/env python3
"""Spell_Bound — zero-dependency CLI spell checker and correction suggester.

Scans text files for potentially misspelled words and suggests corrections
using Levenshtein distance against the system dictionary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# --- Default word list ---
DEFAULT_WORDLIST = "/usr/share/dict/words"

# Common words that /usr/share/dict/words may not include
EXTRA_WORDS: set[str] = {
    "i", "im", "ive", "youre", "theyre", "weve", "youve", "hes", "shes",
    "dont", "cant", "wont", "isnt", "arent", "wasnt", "werent",
    "didnt", "doesnt", "havent", "hasnt", "couldnt", "wouldnt", "shouldnt",
    "its", "thats", "whats", "whos", "theres", "heres",
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "how", "what", "why", "who", "where", "this", "that", "these", "those",
}

# Regex for splitting text into word tokens
WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")


def _load_dictionary(path: str) -> set[str]:
    """Load a dictionary file into a set of lowercase words.

    Handles both plain word-per-line and /usr/share/dict/words format
    (which may have entries like 'plural's' or 'word's possessive).
    """
    words: set[str] = set(EXTRA_WORDS)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # /usr/share/dict/words has entries like "word's" — strip possessives
                cleaned = line.lower()
                if cleaned.endswith("'s"):
                    cleaned = cleaned[:-2]
                elif cleaned.endswith("s'"):
                    cleaned = cleaned[:-2]
                if cleaned:
                    words.add(cleaned)
        # Re-add contracted forms that might have been stripped
        for ew in EXTRA_WORDS:
            words.add(ew)
    except FileNotFoundError:
        pass
    return words


def _stem_matches(word: str, dictionary: set[str]) -> bool:
    """Check if a word matches the dictionary directly or via simple stemming.

    macOS /usr/share/dict/words contains only root forms, so we try
    common English inflections: plurals, verb conjugations, adverbs.
    """
    w = word.lower()

    if w in dictionary:
        return True

    # Try stripping common suffixes and checking stem
    # Order matters: longer suffixes first to avoid partial stripping
    suffixes = [
        ("ies", "y"),      # babies → baby
        ("iest", "y"),     # happiest → happy
        ("ier", "y"),      # happier → happy
        ("est", ""),       # biggest → big
        ("er", ""),        # bigger → big
        ("iness", "y"),    # happiness → happy
        ("ness", ""),      # darkness → dark
        ("ment", ""),      # enjoyment → enjoy
        ("able", ""),      # enjoyable → enjoy
        ("ible", ""),      # sensible → sense
        ("ing", ""),       # jumping → jump
        ("ingly", ""),     # jumpingly → jump
        ("ed", ""),        # jumped → jump
        ("es", ""),        # watches → watch
        ("s", ""),         # jumps → jump
        ("ly", ""),        # quickly → quick
    ]

    for suffix, replacement in suffixes:
        if w.endswith(suffix) and len(w) - len(suffix) >= 2:
            stem = w[:-len(suffix)] + replacement
            if stem in dictionary:
                return True
            # Also try with double-consonant reduction: running → run
            if suffix in ("ing", "ed", "er", "est") and len(stem) >= 2:
                if stem[-1] == stem[-2] and stem[-1] not in "aeiou":
                    if stem[:-1] in dictionary:
                        return True

    return False


def _levenshtein(s: str, t: str) -> int:
    """Compute Levenshtein (edit) distance between two strings."""
    if len(s) < len(t):
        s, t = t, s
    if not t:
        return len(s)

    prev_row = list(range(len(t) + 1))
    for i, sc in enumerate(s, 1):
        curr_row = [i]
        for j, tc in enumerate(t, 1):
            cost = 0 if sc == tc else 1
            curr_row.append(min(
                prev_row[j] + 1,        # deletion
                curr_row[j - 1] + 1,   # insertion
                prev_row[j - 1] + cost # substitution
            ))
        prev_row = curr_row
    return prev_row[-1]


def _suggest(word: str, dictionary: set[str], limit: int = 5) -> list[str]:
    """Return closest dictionary matches for a word using edit distance."""
    word_lower = word.lower()
    candidates: list[tuple[int, str]] = []

    for dict_word in dictionary:
        # Fast filter: skip words with length difference > max edit distance
        if abs(len(dict_word) - len(word_lower)) > 3:
            continue
        dist = _levenshtein(word_lower, dict_word)
        if dist <= 3:
            candidates.append((dist, dict_word))

    candidates.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    results: list[str] = []
    for _, w in candidates:
        if w not in seen:
            seen.add(w)
            results.append(w)
            if len(results) >= limit:
                break
    return results


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan a text file for potentially misspelled words."""
    dictionary = _load_dictionary(args.wordlist or DEFAULT_WORDLIST)

    if not dictionary:
        print("Error: no dictionary loaded", file=sys.stderr)
        return 1

    try:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Error: permission denied: {args.file}", file=sys.stderr)
        return 1

    issues: list[dict] = []
    line_num = 1
    for line in text.splitlines():
        for match in WORD_RE.finditer(line):
            word = match.group(0)
            # Skip words that are all uppercase (likely acronyms) or capitalized proper nouns
            if word.isupper() or (word[0].isupper() and word[1:].islower()):
                continue
            # Skip short words
            if len(word) <= 1:
                continue
            # Skip if in dictionary (direct match or stem match)
            if _stem_matches(word, dictionary):
                continue
            suggestions = _suggest(word, dictionary)
            entry: dict = {
                "word": word,
                "line": line_num,
                "column": match.start() + 1,
                "suggestions": suggestions,
            }
            issues.append(entry)
        line_num += 1

    if args.format == "json":
        json.dump({"file": os.path.abspath(args.file), "issues": issues},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not issues:
            print(f"\u2713 No misspelled words found in {os.path.abspath(args.file)}")
        else:
            relpath = args.file if not os.path.isabs(args.file) else os.path.basename(args.file)
            print(f"Scanning: {relpath}")
            for issue in issues:
                loc = f"line {issue['line']}, col {issue['column']}"
                if issue["suggestions"]:
                    sugg = ", ".join(issue["suggestions"])
                    print(f"  \u2717 {loc}: '{issue['word']}' — did you mean: {sugg}?")
                else:
                    print(f"  \u2717 {loc}: '{issue['word']}' — no suggestions found")
            print(f"\n{len(issues)} potential issue(s) found.")

    return 0 if not issues else 1


def cmd_suggest(args: argparse.Namespace) -> int:
    """Suggest corrections for a word."""
    dictionary = _load_dictionary(args.wordlist or DEFAULT_WORDLIST)
    word = args.word

    # Check if already in dictionary (direct or stem match)
    if _stem_matches(word, dictionary):
        if args.format == "json":
            json.dump({"word": word, "correct": True, "suggestions": []}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"\u2713 '{word}' is spelled correctly.")
        return 0

    suggestions = _suggest(word, dictionary)

    if args.format == "json":
        json.dump({"word": word, "correct": False, "suggestions": suggestions},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if suggestions:
            print(f"\u2717 '{word}' — did you mean: {', '.join(suggestions)}?")
        else:
            print(f"\u2717 '{word}' — no suggestions found.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spell_bound",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    common.add_argument(
        "--wordlist", metavar="PATH",
        help=f"Custom word list file (default: {DEFAULT_WORDLIST})",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    s_scan = sub.add_parser("scan", parents=[common],
                            help="Scan a text file for misspelled words")
    s_scan.add_argument("file", help="Path to the text file to scan")
    s_scan.set_defaults(func=cmd_scan)

    s_sug = sub.add_parser("suggest", parents=[common],
                           help="Suggest corrections for a word")
    s_sug.add_argument("word", help="Word to get suggestions for")
    s_sug.set_defaults(func=cmd_suggest)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
