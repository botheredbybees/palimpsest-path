# analysis/tests/conftest.py
# ──────────────────────────────────────────────────────────────────────────────
# pytest configuration for the analysis test suite.
#
# Problem: analysis/analysis.py is not a package (no __init__.py), so pytest
# cannot resolve "from analysis import ..." when invoked from the repo root.
#
# Solution: insert the analysis/ directory onto sys.path before collection
# begins.  With analysis/ on the path, "import analysis" resolves to
# analysis/analysis.py via Python's normal module-file lookup.
#
# This file is discovered automatically by pytest (conftest.py files are
# loaded before any test collection in their directory subtree).
# No imports from the project are made here — only stdlib path manipulation.
# ──────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# Insert analysis/ (the parent of this tests/ directory) so that:
#   from analysis import classify_walker, match_events, ...
# resolves to analysis/analysis.py regardless of where pytest is invoked from.
_analysis_dir = Path(__file__).parent.parent.resolve()
if str(_analysis_dir) not in sys.path:
    sys.path.insert(0, str(_analysis_dir))
