# Benchmark ground truth: every advisory is real and checkable

The security benchmark grades the model against five real, 2026-disclosed
vulnerabilities across two ecosystems. None of this is invented: each CVE exists
in both the U.S. National Vulnerability Database (NVD) and OSV, and the minimal
safe version we grade against matches the authoritative fixed version in the
GitHub Advisory Database. Verify any row in about ten seconds with the links
below.

| Advisory | Package | Ecosystem | Safe version (graded) | NVD | OSV | GitHub Advisory |
| --- | --- | --- | --- | --- | --- | --- |
| CVE-2026-112398 | pillow | PyPI | 13.0.0 | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-112398) | [OSV](https://osv.dev/vulnerability/CVE-2026-112398) | [GHSA-5x8w-8jj5-q52h](https://github.com/advisories/GHSA-5x8w-8jj5-q52h) |
| CVE-2026-111497 | brotli | PyPI | 1.2.1 | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-111497) | [OSV](https://osv.dev/vulnerability/CVE-2026-111497) | [GHSA-9v8h-qqgm-4m35](https://github.com/advisories/GHSA-9v8h-qqgm-4m35) |
| CVE-2026-42309 | pillow | PyPI | 12.2.0 | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-42309) | [OSV](https://osv.dev/vulnerability/CVE-2026-42309) | [GHSA-5xmw-vc9v-4wf2](https://github.com/advisories/GHSA-5xmw-vc9v-4wf2) |
| CVE-2026-97689 | urllib3 | PyPI | 2.8.0 | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-97689) | [OSV](https://osv.dev/vulnerability/CVE-2026-97689) | [GHSA-vxq7-64xx-v4gw](https://github.com/advisories/GHSA-vxq7-64xx-v4gw) |
| CVE-2026-59873 | tar | npm | 7.5.19 | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-59873) | [OSV](https://osv.dev/vulnerability/CVE-2026-59873) | [GHSA-23hp-3jrh-7fpw](https://github.com/advisories/GHSA-23hp-3jrh-7fpw) |

Each safe version above was cross-checked against the fixed version in the
advisory's OSV and GitHub Advisory records (the `fixed` event of the ecosystem
range). All five match the value the benchmark grades on, which is stored in
[`advisories.json`](advisories.json) as `min_safe` / `fixed_versions` and is
never shown to the model.

Why these five, and why they prove the point: all were published in 2026, after
every current model's training cutoff, so the safe-version fact cannot be in the
weights. That is exactly why the model, run with the live web off, abstains on
all five (0/15) instead of guessing, and resolves all five with the web on
(15/15). The gap is the value of live search, and it is impossible to fake.
