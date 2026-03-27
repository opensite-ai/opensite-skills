# Activation Guide for large-scale-refactor Skill

## When to Invoke This Skill

Invoke the `large-scale-refactor` skill when you encounter any of the following scenarios:

### Activation Patterns
- "refactor * across the codebase"
- "migrate * to [new technology]"
- "upgrade * from [old version] to [new version]"
- "replace all instances of * with *"
- "update every * to use *"
- "rename * throughout the project"
- "convert all * files to * format"
- "remove all instances of *"
- "batch * across the codebase"
- Any task estimated to touch 50+ files

### Platform-Specific Invocation

#### Qoder Quest
```
1. Select "Code with Spec" scenario
2. In the Spec Tab, reference this skill by name
3. Click "Run Spec" only after human review
```

#### Claude Code / Codex
```
@large-scale-refactor [task-name]
```

#### Cursor
```
/large-scale-refactor [task-name]
```

#### GitHub Copilot
```
/large-scale-refactor [task-name]
```

#### Factory Droid
```
1. Inject the approved spec as system prompt
2. Set file diff budget as hard stop condition
3. Assign non-overlapping file lists to parallel instances
```

#### Devin Playbooks
```
1. Include spec as first system message
2. Set circuit breaker thresholds
3. Monitor first 10 files for emergent behavior
```

## Skill Workflow

1. **Spec Generation**: Agent creates comprehensive task spec
2. **Spec Review**: Human approves spec before execution
3. **Batched Execution**: Agent processes files in atomic batches
4. **Drift Detection**: Regular self-audits for scope compliance
5. **Checkpointing**: Hard stops at critical decision points
6. **Verification**: Automated validation before marking complete
7. **Context Handoff**: Session state preserved for multi-session tasks

## Key Guardrails

- **Spec Gate**: No execution without approved spec
- **Substitution Test**: Every change must be strictly necessary
- **No Emergent Systems**: No new abstractions without approval
- **Dependency Lockdown**: No unauthorized dependency changes
- **Atomic Commits**: Each subtask lands separately
- **File Budgets**: Session limits based on risk level
- **Parallel Isolation**: Non-overlapping file assignments
- **Drift Checks**: Self-audit every 25 files
- **Change Manifest**: Comprehensive record of all changes
- **Verification Sequence**: Automated scope and dependency checks

## Best Practices

1. **Start Small**: Begin with a pilot batch of 10-20 files
2. **Monitor Early**: Watch first few files closely for emergent behavior
3. **Document Everything**: Maintain OBSERVATIONS.md and CHANGE_MANIFEST.md
4. **Frequent Checkpoints**: Don't let sessions run too long
5. **Context Flushing**: Clear memory between batches to prevent drift
6. **Parallel Safety**: Assign explicit file lists, not patterns
7. **Rollback Ready**: Ensure you can undo any batch independently

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Agent proposing out-of-scope changes | Reinforce spec boundaries, use Substitution Test |
| Tests failing unexpectedly | Check if failure is pre-existing, document in manifest |
| Context window degradation | Flush context, reload only spec and current batch |
| Parallel agents conflicting | Verify non-overlapping file assignments |
| Dependency changes needed | Halt, propose, await approval |
| Ambiguity in spec | Surface to human, await clarification |

### Escalation Path

1. **Log the issue** in OBSERVATIONS.md or escalations.md
2. **Halt execution** at nearest checkpoint
3. **Provide context** about the situation
4. **Offer options** with implications
5. **Await instruction** before proceeding

## Example Usage

### TypeScript Migration
```bash
# 1. Generate spec
@large-scale-refactor js-to-ts-migration

# 2. Review and approve spec
# (human reviews IN SCOPE, OUT OF SCOPE, etc.)

# 3. Execute in batches
# Agent processes 20 files at a time
# Commits each batch separately
# Runs verification sequence after each batch

# 4. Monitor progress
# Check .refactor-session.md for handoff state
# Review CHANGE_MANIFEST.md for each subtask
```

### Framework Upgrade
```bash
# 1. Define scope
@large-scale-refactor react-17-to-18

# 2. Specify boundaries
# IN SCOPE: src/components/, src/hooks/
# OUT OF SCOPE: config/, scripts/, node_modules/

# 3. Parallel execution
# Agent 1: src/components/common/
# Agent 2: src/components/features/
# Agent 3: src/hooks/

# 4. Verification
# Run test suite after each batch
# Check dependency changes
# Validate no out-of-scope files touched
```

## Compatibility

This skill is designed to work across multiple AI coding platforms:
- ✅ Qoder Quest (Code with Spec scenario)
- ✅ Claude Code (automatic invocation)
- ✅ Codex (automatic invocation)
- ✅ Cursor (/large-scale-refactor command)
- ✅ GitHub Copilot (/large-scale-refactor command)
- ✅ Factory Droid (batch mode)
- ✅ Devin Playbooks (parallel execution)

## License

This skill is open-source and available under the MIT License. It can be used freely
in both commercial and non-commercial projects.
