# Maintainer release procedure

The repository is prepared locally. No commit, tag, push or GitHub Release is
created by the packaging script. Use `--draft --prerelease` for the first release.

1. Update `VERSION`, the CMake project version, release notes and the Basic
   cluster software build ID in ZAP. Regenerate the checked-in ZAP defaults.
2. Run all three host test scripts, prepare the pinned SDK, and build from a
   fresh build directory. Inspect known SDK warnings and record hardware tests.
3. Package the firmware:

```sh
python3 scripts/package_release.py
```

Outputs in ignored `dist/` are a firmware ZIP and its external SHA-256 file.
The ZIP contains HEX/S37, flashing instructions, license notices, release
metadata, a source manifest and internal checksums. It contains no SDK/tool
binary installation, NVM dump, private keys, CAD backup, or build cache.

4. Review and commit the intended repository changes. The existing enclosure
   files and original MIT license have been preserved. Review tracked files and
   check that generated SDK copies, credentials and local settings are ignored.
5. Create and push the release tag after committing:

```sh
git tag -a v0.1.0 -m "First public release"
git push origin main
git push origin v0.1.0
```

6. Create a draft GitHub release (requires your GitHub CLI login), or upload the
   same two assets through the GitHub Releases page:

```sh
gh release create v0.1.0 --verify-tag --draft --prerelease \
  --title "v0.1.0 — XIAO MG24 window contact sensor" \
  --notes-file RELEASE_NOTES.md \
  dist/window-contact-sensor-v0.1.0-xiao-mg24.zip \
  dist/window-contact-sensor-v0.1.0-xiao-mg24.zip.sha256
```

Review the draft and publish when ready. GitHub supplies the source archive
from the tag automatically. CI currently validates host tests only, not the
licensed SDK firmware build. Repeat the package step if source files change.
