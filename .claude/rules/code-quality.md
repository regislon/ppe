# Code Quality Checks

**MANDATORY**: Run these checks after ANY code changes before committing.

## Workflow

1. Get changed files:
```bash
CHANGED_FILES=$(git diff --name-only HEAD | grep '\.py$' | tr '\n' ' ')
```

2. Format:
```bash
uv run ruff format $CHANGED_FILES
```

3. Lint with auto-fix:
```bash
uv run ruff check --fix $CHANGED_FILES
```

4. Type check:
```bash
uv run mypy --ignore-missing-imports --follow-imports=silent \
  --disable-error-code=import-untyped \
  --disable-error-code=attr-defined \
  --disable-error-code=arg-type \
  --disable-error-code=return-value \
  --disable-error-code=assignment \
  $CHANGED_FILES
```

5. Fix any remaining issues manually
6. Only commit after all checks pass

## Reference

See `CLAUDE.md` section "Code Quality" for full details.