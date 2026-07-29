# Spell_Bound 🔍

**Zero-dependency spell checker and correction suggester.** Pure Python stdlib — scans text files and suggests corrections using the system dictionary.

> Part of the content QA suite — catch typos before they ship.

## One tool, many domains

| Domain | What Spell_Bound does for you |
|---|---|
| 📝 **Content Writing** | Scan articles, blog posts, and docs for misspelled words before publishing |
| 🤖 **AI Agent Pipelines** | Validate LLM-generated text for spelling errors in automated workflows |
| 📋 **CI/CD** | Gate deployments: fail builds when spelling issues are detected (`--format json` for pipeline parsing) |
| 🎓 **Education** | Check student essays and suggest corrections for learning feedback loops |
| 📚 **Publishing** | Pre-flight manuscript and book scans before typesetting |
| 🧪 **QA / Testing** | Automated spell-check regression in content-heavy apps |

## Install

```bash
git clone git@github.com:realMNohgee/Spell_Bound.git
cd Spell_Bound
python3 spell_bound.py --help
```

## Quick start

```bash
# Scan a file
python3 spell_bound.py scan README.md

# Get suggestions for a word
python3 spell_bound.py suggest recieve

# JSON output for pipelines
python3 spell_bound.py scan --format json README.md

# Use a custom dictionary
python3 spell_bound.py scan --wordlist /path/to/custom/words.txt document.txt
```

## How it works

Spell_Bound uses the system dictionary (`/usr/share/dict/words` on macOS/Linux) combined with common contractions and short words. It splits text into word tokens, filters out likely proper nouns and acronyms, then flags anything not in the dictionary. The `suggest` command uses Levenshtein (edit) distance to find the closest dictionary matches.

## License

MIT — see [LICENSE](LICENSE).

---

🧰 **[Tool on Hermtica Marketplace](https://hermtica.com/marketplace)** — the open, agent-agnostic marketplace for AI agent tools.
