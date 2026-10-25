# pandas_append

**Symptom:** `AttributeError: 'DataFrame' object has no attribute 'append'`

**Root cause:** `DataFrame.append` and `Series.append` were deprecated in pandas
1.4 and removed in pandas 2.0 (April 2023). The documented replacement is
`pandas.concat`.

**Minimal fix:**

```diff
-    return df.append(row, ignore_index=True)
+    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)
```

**Why web grounding helps:** `concat` takes a list of frames, not a dict, so a
model guessing from the error alone often produces a call that still fails. The
pandas migration note shows the exact `pd.concat([df, pd.DataFrame([row])])`
shape, which is what search puts in front of the model.

Reference: pandas 2.0 "What's new" / "Removal of prior version deprecations".
