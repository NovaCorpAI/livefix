# vulnerable_project (end-to-end remediation example)

A minimal project that starts in the state security tooling leaves you in: a
dependency pinned to a version with a **critical, 2026-disclosed CVE**, where the
only fix is a major upgrade that also **breaks your code**.

- `requirements.txt` pins `pillow==12.3.0`, vulnerable to **CVE-2026-112398**
  (critical RCE). The fix ships only in Pillow 13.0.0.
- `app.py` reads an ICC profile name via `ImageCmsProfile.product_name`, which
  Pillow 13.0.0 removed. So the security upgrade turns the build red.

This is exactly the gap a Dependabot-style bump PR leaves open: it would raise
the pin and break the tests, then rot unmerged.

## Run LiveFix end to end

```bash
python -m livefix.remediate \
  --project examples/vulnerable_project \
  --package pillow \
  --advisory CVE-2026-112398 \
  --note "critical RCE via crafted image" \
  --test "python -m pytest -q"
```

LiveFix will:

1. **Resolve** the safe version from the live web (Tavily): `13.0.0`. A plain
   model cannot know this, because the CVE post-dates its training cutoff; it
   abstains. This is the step the web makes possible.
2. **Bump** the pin: `pillow==12.3.0` -> `pillow>=13.0.0`.
3. **Repair** the code the upgrade broke: `profile.product_name` ->
   `ImageCms.getProfileName(profile)`, verified by the test.

The result is a green, merge-ready change. Re-running resets by `git checkout`
of `app.py` and `requirements.txt`.
