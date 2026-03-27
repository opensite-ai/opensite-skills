# Contributing to OpenSite Skills

Thank you for improving the skill library. This guide covers everything you need
to contribute a new skill, improve an existing one, or fix a bug in the tooling.

---

## Table of Contents

1. [Ways to Contribute](#ways-to-contribute)
2. [Before You Start](#before-you-start)
3. [Proposing a New Skill](#proposing-a-new-skill)
4. [Improving an Existing Skill](#improving-an-existing-skill)
5. [Skill Quality Checklist](#skill-quality-checklist)
6. [Running the Test Suite](#running-the-test-suite)
7. [PR Conventions](#pr-conventions)
8. [Good First Issues](#good-first-issues)

---

## Ways to Contribute

| Type | Description |
|------|-------------|
| **New skill** | Add a skill for a workflow, technology, or domain not yet covered |
| **Skill improvement** | Sharpen instructions, add examples, fix edge cases in an existing skill |
| **Script fix** | Fix a bug in one of the Python helper scripts |
| **Documentation** | Clarify README, fix broken links, add usage examples |
| **Test coverage** | Add tests for scripts that have none, or improve existing tests |
| **Platform support** | Add or update platform-specific notes in `agents/openai.yaml` or `references/activation.md` |

---

## Before You Start

1. **Read the [Agent Skills open standard](https://agentskills.io)** — all skills in this
   repo follow it. Your contribution must be compatible.

2. **Check for an existing issue** — search
   [GitHub Issues](https://github.com/opensite-ai/opensite-skills/issues) before
   opening a duplicate.

3. **For significant new skills**, open an issue first with the template below so
   the community can align on scope before you invest time writing the full skill.

4. **Run setup** to make sure your environment is functional:
   ```bash
   ./setup.sh
   python3 scripts/validate_skills.py
   ```

---

## Proposing a New Skill

### 1. Open an issue

Use this template when opening a "New Skill Proposal" issue:

```
**Skill name** (kebab-case):

**One-sentence description** (what it does + when to use it):

**Platform(s)**: Claude Code / Codex / Cursor / Copilot / Claude Desktop / all

**Who needs this**: (role or situation — "Rails developers running zero-downtime
deploys", "teams migrating a large codebase", etc.)

**Why existing skills don't cover it**:

**Sample trigger phrases**:
- "..."
- "..."

**Rough structure** (optional — a few bullet points on what sections SKILL.md would contain):
```

### 2. Build the skill

Once the issue has a 👍 from a maintainer, create the skill directory:

```
your-skill-name/
├── SKILL.md                  ← required
├── agents/
│   └── openai.yaml           ← required (Codex/OpenAI metadata)
├── references/
│   └── activation.md         ← required (platform activation guide)
├── templates/                ← optional
├── examples/                 ← optional
└── scripts/                  ← optional Python/Bash helpers
```

Use an existing skill (e.g. `rails-query-optimization` or `rust-error-handling`) as
a structural reference.

### 3. Run the validator

```bash
python3 scripts/validate_skills.py
```

All checks must pass before you open a PR.

---

## Improving an Existing Skill

1. **Read the current SKILL.md in full** before making changes — many skills have
   deliberate constraints that look like omissions.

2. **Target the body, not the guardrails** — for skills like `large-scale-refactor`,
   the core guardrails (§§ 1–4) are explicitly protected from deepening. Improvements
   to those sections require a maintainer discussion.

3. **Test your change against the skill's own examples** — if the skill ships
   `examples/`, verify that your updated instructions still produce correct output
   for those examples.

4. **Bump the version** in `agents/openai.yaml` and `SKILL.md` metadata (patch for
   fixes, minor for new content).

---

## Skill Quality Checklist

Use this before opening any PR that adds or modifies a skill.

### SKILL.md

- [ ] File is named exactly `SKILL.md` (case-sensitive)
- [ ] YAML frontmatter is valid — run `python3 -c "import yaml; yaml.safe_load(open('SKILL.md').read().split('---',2)[1])"` with no error
- [ ] `name` field: kebab-case, matches the directory name, no spaces or capitals
- [ ] `description` field: present, under 1024 characters, no XML `<>` characters
- [ ] `description` covers both **what** the skill does and **when** to use it (trigger conditions)
- [ ] `license` field present (use `MIT` unless intentionally different)
- [ ] Only official top-level fields used: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`
- [ ] No hardcoded local machine paths anywhere in the file
- [ ] Instructions are written in the imperative voice
- [ ] No `.bak`, `.tmp`, or draft files left in the skill directory

### `agents/openai.yaml`

- [ ] Present at `agents/openai.yaml`
- [ ] `name`, `description`, `author`, `version` all populated
- [ ] Activation patterns listed

### `references/activation.md`

- [ ] Present at `references/activation.md`
- [ ] Covers at least one explicit invocation example per major platform

### Scripts (if any)

- [ ] No hardcoded absolute paths — use `os.path.dirname(os.path.abspath(__file__))` for relative resolution
- [ ] Python scripts run on Python 3.8+ with zero external dependencies (stdlib only), OR list external deps in a `requirements.txt` with a clear comment
- [ ] Scripts that have significant logic include at least a basic test

### General

- [ ] `python3 scripts/validate_skills.py` passes
- [ ] No files contain internal project names, machine usernames, or local directory structure
- [ ] Changelog or version bump included if modifying an existing skill

---

## Running the Test Suite

### Validate all skill frontmatter

```bash
python3 scripts/validate_skills.py
```

### Run a specific skill's script tests

```bash
# Example: large-scale-refactor
python -m pytest large-scale-refactor/scripts/test_verify_scope.py -v

# Or directly
python large-scale-refactor/scripts/test_verify_scope.py
```

### Test allowlist generation manually

```bash
# Generate an allowlist from one of the example specs
python large-scale-refactor/scripts/generate_allowlist.py \
  large-scale-refactor/examples/refactor-spec.md

# Preview without writing
python large-scale-refactor/scripts/generate_allowlist.py \
  large-scale-refactor/examples/refactor-spec.md --dry-run
```

### Test scope verification manually

```bash
# From inside a git repo with a .refactor-scope-allowlist present
python path/to/large-scale-refactor/scripts/verify_scope.py
python path/to/large-scale-refactor/scripts/verify_scope.py --strict
```

---

## PR Conventions

### Branch naming

```
feat/skill-name          # new skill
fix/skill-name-issue     # bug fix in an existing skill or its scripts
docs/skill-name          # documentation-only change
chore/tooling            # scripts/, setup.sh, validate_skills.py, etc.
```

### Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(rails-query-optimization): add CTE pattern for recursive hierarchies
fix(large-scale-refactor): correct fnmatch glob matching in verify_scope.py
docs(memory): clarify memory-consolidate weekly vs monthly cadence
chore(scripts): update validate_skills.py to check license field
```

### PR description template

```markdown
## Summary
<!-- One paragraph: what changed and why -->

## Checklist
- [ ] `python3 scripts/validate_skills.py` passes
- [ ] No hardcoded local paths
- [ ] Quality checklist above completed
- [ ] Version bumped in `agents/openai.yaml` and SKILL.md metadata (if modifying existing skill)
- [ ] `SKILL.md.bak` and other draft files removed

## Testing
<!-- How did you verify this works? -->

## Related issue
<!-- Closes #N -->
```

### Review expectations

- Maintainers aim to review within **5 business days**.
- All PRs require at least **one approving review** before merge.
- Automated validation (`validate_skills.py`) must pass.
- For new skills, a maintainer will typically ask you to run the skill against a
  real prompt and paste the output as evidence it triggers correctly.

---

## Good First Issues

Look for issues tagged
[`good first issue`](https://github.com/opensite-ai/opensite-skills/issues?q=is%3Aopen+label%3A%22good+first+issue%22)
on GitHub. These are scoped to be completable in a single sitting and are a good
way to get familiar with the repo structure before tackling a full new skill.

Typical good-first-issue types:

- Fix a broken link or outdated reference in a skill's README
- Add a missing `references/activation.md` to a skill that lacks one
- Write tests for a script that has none
- Add a platform-specific note to `§ 7` of an existing skill
- Add a real-world usage example to `examples/`

---

## Questions?

Open a [GitHub Discussion](https://github.com/opensite-ai/opensite-skills/discussions)
or file an issue with the `question` label. We're happy to help.