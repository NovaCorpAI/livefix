# flask_markup

**Symptom:** `ImportError: cannot import name 'Markup' from 'flask'`

**Root cause:** Flask re-exported `Markup` (and `escape`) from MarkupSafe for
convenience. That re-export was deprecated and removed in Flask 3.1 (November
2024). The symbol should be imported from `markupsafe` directly.

**Minimal fix:**

```diff
-from flask import Markup
+from markupsafe import Markup
```

**Why web grounding helps:** the error points at `flask` but the symbol lives in
another, still-installed package (`markupsafe`). The Flask 3.1 changelog states
the move, which search surfaces, so the model redirects the import correctly
instead of trying to recreate `Markup`.

Reference: Flask 3.1 changelog, "Remove previously deprecated code".
