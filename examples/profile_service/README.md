# profile_service: a multi-file security break

A harder remediation than the single-file example. This small service reads
three fields from an ICC color profile, each in its own module:

- `colorprofile/name.py` uses `profile.product_name`
- `colorprofile/description.py` uses `profile.product_desc`
- `colorprofile/rights.py` uses `profile.product_copyright`

All three attributes were **removed in Pillow 13.0.0**, the security release for
CVE-2026-112398. So the single upgrade that closes the CVE breaks the build in
three places at once, each needing a different replacement
(`ImageCms.getProfileName`, `getProfileDescription`, `getProfileCopyright`).

LiveFix resolves the safe version, bumps the pin, then repairs each module in
turn, re-running the tests until the whole build is green:

```bash
python -m livefix.remediate --project examples/profile_service \
  --package pillow --advisory CVE-2026-112398 --test "python -m pytest -q" --install
```

Expected: three repair iterations (one per module), then the test passes. This
is the point the one-file example cannot make on its own: the repair loop keeps
going across files until the real build is green, not just the first error.

To run it through the GitHub Action, set the workflow's `project` input to
`examples/profile_service`.
