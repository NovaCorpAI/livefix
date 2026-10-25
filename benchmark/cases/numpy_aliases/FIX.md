# numpy_aliases

**Symptom:** `AttributeError: module 'numpy' has no attribute 'float'`

**Root cause:** `np.float` (along with `np.int`, `np.bool`, `np.object`) was a
deprecated alias for the Python builtin. NumPy deprecated it in 1.20 and removed
it in 1.24 (December 2022).

**Minimal fix:**

```diff
-    return np.array(values).astype(np.float)
+    return np.array(values).astype(np.float64)
```

(`float` also works; the test asserts `dtype == np.float64`, which both produce.)

**Why web grounding helps:** the error says the attribute is gone but not what to
use instead. NumPy's own release note and migration guide, surfaced by search,
state the replacement, so the model picks `np.float64` rather than guessing.

Reference: NumPy 1.24 release notes, "Expired deprecations".
