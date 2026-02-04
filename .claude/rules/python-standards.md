---
paths:
  - "goose/**/*.py"
  - "test/**/*.py"
---

# Python Code Standards

**MANDATORY**: Read `docs/CODE_STANDARDS.md` before writing or modifying ANY code.

## Quick Reference

### Function Design (CODE_STANDARDS.md#function-and-method-design)
- Max 50 lines preferred; refactor if >100 lines
- Single responsibility: no "and" in function names
- Pipeline functions orchestrate, don't implement inline

### Type Hints (CODE_STANDARDS.md#type-hints)
- All parameters and returns MUST have type hints
- Use modern syntax: `list[str]`, `dict[str, int]`, `X | None`

### Error Handling (CODE_STANDARDS.md#error-handling-patterns)
- Validate inputs early with descriptive messages
- Use specific exceptions: `ValueError`, `KeyError`, `FileNotFoundError`
- Include context: expected vs. received

### Logging (CODE_STANDARDS.md#logging-best-practices)
- INFO: milestones, counts, configuration
- WARNING: recoverable issues
- ERROR: serious problems
- Always use f-strings with context

### Performance (CODE_STANDARDS.md#performance-considerations)
- Polars over Pandas for new code
- `UPath` for all path operations
- Lazy evaluation: `pl.scan_parquet()` not `pl.read_parquet()`

### Anti-Patterns (CODE_STANDARDS.md#common-anti-patterns-to-avoid)
- No magic strings/numbers - use constants
- No mutable default arguments
- No bare `except:` - use specific exceptions
- No `len(x) == 0` - use truthiness or `.empty`/`.is_empty()`