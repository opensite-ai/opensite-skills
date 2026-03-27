# large-scale-refactor Skill

**Enterprise-grade guardrails for large-scale AI refactoring tasks**

![Build Status](https://img.shields.io/badge/status-production-ready-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Version](https://img.shields.io/badge/version-1.0.0-orange)

## Overview

The `large-scale-refactor` skill provides comprehensive guardrails, protocols, and operating constraints for large-scale, long-running, or parallelized AI coding tasks. It's designed to prevent scope creep, context drift, silent compounding errors, and emergent behavior outside defined task boundaries.

## Key Features

- **Spec Gate**: Mandatory human approval before execution
- **Scope Enforcement**: Explicit IN SCOPE / OUT OF SCOPE boundaries
- **Batched Execution**: Atomic, reviewable batches (10-200 files)
- **Drift Detection**: Regular self-audits every 25 files
- **Parallel Safety**: Non-overlapping file assignments
- **Verification Sequence**: Automated scope and dependency checks
- **Context Handoff**: Session state preservation for multi-session tasks

## When to Use

Invoke this skill for any task that:
- Touches 50+ files
- Runs across multiple agent sessions
- Requires parallel execution
- Involves framework migrations, language upgrades, or cross-cutting changes

### Activation Patterns

```
refactor * across the codebase
migrate * to [new technology]
upgrade * from [old version]
replace all instances of *
update every * to use *
rename * throughout
convert all * files
remove all instances
batch * across the codebase
```

## Installation

### For OpenSite Skills Library

```bash
# Clone the repository
git clone https://github.com/opensite-ai/opensite-skills.git
cd opensite-skills/large-scale-refactor

# Make scripts executable (no external dependencies — stdlib only)
chmod +x scripts/*.py
```

### For Individual Use

Simply copy the `large-scale-refactor` directory to your skills library or project.

## Usage

### Basic Workflow

```bash
# 1. Generate refactoring spec
@large-scale-refactor js-to-ts-migration

# 2. Review and approve spec (human step)
# Edit the generated spec to ensure accuracy

# 3. Generate scope allowlist
python scripts/generate_allowlist.py refactor-spec.md

# 4. Execute in batches
# Agent processes files according to spec

# 5. Verify scope compliance
python scripts/verify_scope.py --strict

# 6. Monitor progress via handoff files
cat .refactor-session.md
```

### Platform-Specific Invocation

#### Qoder Quest
```
1. Select "Code with Spec" scenario
2. Reference this skill by name
3. Click "Run Spec" only after human review
```

#### Claude Code / Codex
```
@large-scale-refactor [task-name]
```

#### Cursor / GitHub Copilot
```
/large-scale-refactor [task-name]
```

#### Factory Droid / Devin
```
1. Inject approved spec as system prompt
2. Set file diff budget as hard stop
3. Assign non-overlapping file lists
```

## Skill Components

### Core Files

- `SKILL.md` - Main skill instructions with comprehensive guardrails
- `references/activation.md` - Platform-specific activation guide
- `agents/openai.yaml` - OpenAI/Claude platform metadata

### Templates

- `templates/change-manifest.md` - Template for documenting changes
- `examples/refactor-spec.md` - Example refactoring specification

### Scripts

- `scripts/verify_scope.py` - Validate all changes are within scope
- `scripts/generate_allowlist.py` - Generate allowlist from spec

## Core Guardrails

### § 1 — Spec Gate
- **Mandatory written spec** before any execution
- **Human approval required** before starting
- **Platform-specific** implementation guides

### § 2 — Scope Enforcement
- **One Task Rule**: Agent has exactly one job
- **Substitution Test**: Every change must be necessary
- **No Emergent Systems**: No new abstractions without approval
- **Dependency Lockdown**: No unauthorized changes

### § 3 — Execution Protocol
- **Atomic commits** for each subtask
- **File budgets** based on risk level (20-200 files)
- **Parallel isolation** with non-overlapping assignments
- **Drift detection** every 25 files

### § 4 — Human Checkpoints
- **Hard stops** at critical points
- **Checkpoint triggers**: Spec gate, drift, scope violations, etc.
- **Structured format** for clear communication

### § 5 — Verification
- **Change manifest** for each subtask
- **Automated verification sequence**
- **Scope compliance** checking
- **Test results** documentation

### § 6 — Context Handoff
- **Session handoff file** for multi-session tasks
- **Progress tracking** across sessions
- **State preservation** for different agents/platforms

## Best Practices

### Starting a Refactor

1. **Begin with a pilot**: Start with 10-20 files to validate approach
2. **Monitor closely**: Watch first few files for emergent behavior
3. **Document everything**: Maintain OBSERVATIONS.md and CHANGE_MANIFEST.md
4. **Frequent checkpoints**: Don't let sessions run too long
5. **Context management**: Flush context between batches

### Parallel Execution

1. **Explicit assignments**: Assign specific file lists, not patterns
2. **Non-overlapping**: Ensure no two agents touch same files
3. **Shared spec**: All instances use same approved spec
4. **No communication**: Agents don't observe each other's output

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Out-of-scope changes | Reinforce spec boundaries, use Substitution Test |
| Test failures | Check if pre-existing, document in manifest |
| Context drift | Flush context, reload spec and current batch |
| Parallel conflicts | Verify non-overlapping file assignments |
| Dependency changes | Halt, propose, await approval |
| Spec ambiguity | Surface to human, await clarification |

## Examples

### TypeScript Migration

```bash
# Generate spec
@large-scale-refactor js-to-ts-migration

# Create allowlist
python scripts/generate_allowlist.py refactor-spec.md

# Execute (agent processes 20 files at a time)
# Commits each batch separately
# Runs verification after each batch

# Monitor
cat .refactor-session.md
```

### Framework Upgrade

```bash
# Define scope
@large-scale-refactor react-17-to-18

# Parallel execution
# Agent 1: src/components/common/
# Agent 2: src/components/features/
# Agent 3: src/hooks/

# Verify
python scripts/verify_scope.py --strict
```

## Development

### Testing

```bash
# Run verification script tests
python -m pytest scripts/test_verify_scope.py

# Test allowlist generation
python scripts/generate_allowlist.py examples/refactor-spec.md
cat .refactor-scope-allowlist
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## Compatibility

This skill works across multiple AI coding platforms:

- ✅ Qoder Quest (Code with Spec scenario)
- ✅ Claude Code (automatic invocation)
- ✅ Codex (automatic invocation)
- ✅ Cursor (/large-scale-refactor command)
- ✅ GitHub Copilot (/large-scale-refactor command)
- ✅ Factory Droid (batch mode)
- ✅ Devin Playbooks (parallel execution)

## License

MIT License - Free for commercial and non-commercial use.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/opensite-ai/opensite-skills/issues
- Repository: https://github.com/opensite-ai/opensite-skills

## Changelog

### 1.0.0 (2026-03-27)
- Initial production-ready release
- Comprehensive guardrails and protocols
- Multi-platform support
- Verification scripts and templates
- Full documentation

## Roadmap

- Enhanced pattern matching in verification scripts
- Integration with CI/CD pipelines
- Additional platform support
- Performance optimization for very large codebases

---

**Built with ❤️ by OpenSite AI**

*Enterprise-grade AI coding infrastructure for everyone*
