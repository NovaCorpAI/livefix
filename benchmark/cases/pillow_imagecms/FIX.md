# pillow_imagecms

**Symptom:** `AttributeError: 'ImageCmsProfile' object has no attribute 'product_name'`

**Root cause:** Pillow 13.0.0 (released 2026-10-16) removed the long-deprecated
`ImageCmsProfile.product_name` and `product_info` attributes. This release is
the only fix for CVE-2026-112398 and several other critical advisories, so a
project that upgrades for the CVE inherits the API removal.

**Minimal fix:**

```diff
-    return profile.product_name.strip()
+    return ImageCms.getProfileName(profile).strip()
```

**Why web grounding helps:** the error names only the missing attribute, not the
replacement, and the removal is days old at the time of writing, so it post-dates
any model training cutoff. The current, documented accessor
(`ImageCms.getProfileName`) is what a live search surfaces.

Reference: Pillow 13.0.0 "Deprecations and removals" documentation.
