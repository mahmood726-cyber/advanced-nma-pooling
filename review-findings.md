# advanced-nma-pooling — Code Review Findings

**Reviewer:** Claude Opus 4.6 (1M context)
**Date:** 2026-04-03
**Files:** index.html (43 lines, landing page), src/nma_pool/ (Python package)

## P0 — Critical (must fix)

None found.

## P1 — Important

### P1-1: `index.html` is a static landing page only
**Issue:** The index.html is a pure static E156 landing page linking to the e156-submission. No interactive JS, no user input, no CSV export. Security/accessibility audit scope is minimal.
**Status:** No security issues (no JS, no forms, no CSV).

### P1-2: Python CLI uses `import_module` with user-supplied command name
**File:** src/nma_pool/cli.py, line 64
**Issue:** `import_module(module_name)` is called with a value from `COMMANDS` dict, which is statically defined. The command name from argv is validated against `COMMANDS.keys()` by argparse subparsers. **Not exploitable** — the module name comes from a fixed dict, not user input.

## P2 — Minor

### P2-1: `index.html` has proper `</html>` closing tag
**Line:** 44
**Status:** PASS.

### P2-2: `index.html` has `lang="en"` on html element
**Status:** PASS.

### P2-3: No skip-nav needed (single-page static with no interactive elements)
**Status:** N/A.

## Summary

| Severity | Count |
|----------|-------|
| P0       | 0     |
| P1       | 2     |
| P2       | 3     |
