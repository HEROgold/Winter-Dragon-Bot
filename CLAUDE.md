# CLAUDE.md

## Import style

Prefer lazy imports (import inside the function/method that uses the name) over module-level imports. Module-level imports are only used when required by the tooling/library itself (e.g. pydantic needs types resolvable at class-definition time).
