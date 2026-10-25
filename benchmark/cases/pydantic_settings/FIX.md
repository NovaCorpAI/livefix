# pydantic_settings

**Symptom:** `PydanticImportError` / `ImportError`: `BaseSettings` has been moved
to the `pydantic-settings` package.

**Root cause:** Pydantic v2 (released June 2023) removed `BaseSettings` from the
core `pydantic` package. It now lives in the separate `pydantic-settings`
package, imported as `from pydantic_settings import BaseSettings`.

**Minimal fix:**

```diff
-from pydantic import BaseSettings
+from pydantic_settings import BaseSettings
```

(The package `pydantic-settings` must be installed; it ships with the benchmark
requirements.)

**Why web grounding helps:** the fix is in a different package name than the one
that failed. Pydantic's own v2 migration guide names `pydantic-settings`, which a
model with a pre-v2 cutoff would not know to reach for.

Reference: Pydantic v2 migration guide, "BaseSettings has moved".
