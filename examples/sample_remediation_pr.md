# Sample LiveFix remediation pull request

This is the pull request LiveFix opens for the bundled example
(`examples/vulnerable_project/`), rendered from a real recorded run. The GitHub
Action (`action.yml` + `.github/workflows/livefix-remediate.yml`) produces exactly
this: the body below, a `LiveFix / remediation-verified` check that is green only because the
tests pass, and the commit trailer at the end.

---

**PR title:** Security remediation: CVE-2026-112398 in pillow

**PR body:**

Resolved the safe version for **CVE-2026-112398** from the live web and landed the upgrade green. Bumped `pillow==12.3.0` to `pillow>=13.0.0`. Repaired the code the upgrade broke. Tests pass.

<details><summary>What LiveFix did</summary>

- Resolved safe version **13.0.0** from the live advisory ([source](https://explore.alas.aws.amazon.com/CVE-2026-112398.html))
- Bumped the pin in the manifest: `pillow==12.3.0` to `pillow>=13.0.0`
- Repaired the code the upgrade broke: `app.py`
  - Replaced direct attribute access with ImageCms.getProfileName to retrieve the profile's product name.
- Verified by the project's own tests: passing
- Full step-by-step trace: [https://smith.langchain.com/public/livefix-demo/r](https://smith.langchain.com/public/livefix-demo/r)

</details>

---

Verified by LiveFix · NovaCorp Labs · novacorplabs.com

---

**Commit message trailer** (machine-readable, greppable in history):

```
LiveFix-Remediation: CVE-2026-112398
LiveFix-Package: pillow
LiveFix-Safe-Version: 13.0.0
LiveFix-Source: https://explore.alas.aws.amazon.com/CVE-2026-112398.html
LiveFix-Verified: tests-pass
LiveFix-Trace: https://smith.langchain.com/public/livefix-demo/r
LiveFix-Maker: NovaCorp Labs
```
