# py310_collections

**Symptom:** `ImportError: cannot import name 'Mapping' from 'collections'`

**Root cause:** The ABCs in `collections` were deprecated aliases for years and
removed in Python 3.10 (released October 2021). The canonical home is
`collections.abc`.

**Minimal fix:**

```diff
-from collections import Mapping
+from collections.abc import Mapping
```

**Why web grounding helps:** the failure names only `collections`, not where the
symbol went. The current, documented location (`collections.abc`) is the first
result of a search for the error, which is what LiveFix feeds the model.

Reference: Python 3.10 "What's New" / `collections.abc` docs.
