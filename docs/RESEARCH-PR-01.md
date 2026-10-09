# PR-01 research evidence

Inspected on 2026-10-09 (Europe/Istanbul). This records static source/package
findings for the [architecture proposal](ARCHITECTURE-PR-01.md), not runtime
certification. Machine-readable identifiers, hashes and checked files are in
[the baseline](research/baseline-2026-10-09.json).

## Sources and method

The [Fedora package index](https://packages.fedoraproject.org/pkgs/plasma-setup/plasma-setup/fedora-44-updates.html)
identifies `plasma-setup-6.7.5-1.fc44`. The exact
[source RPM](https://kojipkgs.fedoraproject.org/packages/plasma-setup/6.7.5/1.fc44/src/plasma-setup-6.7.5-1.fc44.src.rpm)
and [x86_64 RPM](https://kojipkgs.fedoraproject.org/packages/plasma-setup/6.7.5/1.fc44/x86_64/plasma-setup-6.7.5-1.fc44.x86_64.rpm)
were downloaded and extracted in `/tmp`, without installation/execution.

The SRPM contains the upstream 6.7.5 archive, detached signature, spec and two
patches. Both patches applied cleanly to an analysis copy. The spec's optional
PNG substitution depends on build-root wallpaper files; the inspected binary
contains JXL wallpaper names. The archive's selected critical files were
checked against Git blob IDs in KDE's
[`v6.7.5` mirror commit](https://github.com/KDE/plasma-setup/tree/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd).
The binary's eight page `main.qml` payloads match the patched source byte-for-byte.

Ro-Theme was inspected through its GitHub tree and selected files at
[`ccfba78000cadaedf82baa78b536964d16110b41`](https://github.com/Project-Ro-ASD/Ro-Theme/tree/ccfba78000cadaedf82baa78b536964d16110b41).
Retrieved text snapshots were checked against that revision's Git blob IDs.
No Ro-Theme checkout was changed. Asset inventory was inspected; no artwork
redesign or rendering test was performed.

| Artifact | SHA-256 |
| --- | --- |
| Source RPM | `d60561f145e835b851ba071a7fe5f5718d6766103717116d5cf2af7e7bca2ff2` |
| x86_64 RPM | `70384f7c964c26a68daece7cf178c3d02e64cb59e76c4523cfbfa34dae690057` |
| Upstream archive from SRPM | `64bc032ef9e8a6549fc2dd8b5fa64118e25da652e3de8adb1c974efbd33258dd` |
| Fedora spec | `30135d25346f1c63aea1a00cb6945beebba9640276872ebc9013cb16828829ef` |

Hashes establish the inspected bytes; they do not assert RPM/GPG signature
verification. The mutable Fedora `f44` source links below are browsing aids;
the exact SRPM, hashes and extracted spec are the package baseline.

## R1. Public extension point

[`docs/CUSTOM_MODULES.md`](https://github.com/KDE/plasma-setup/blob/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd/docs/CUSTOM_MODULES.md)
explicitly describes custom `KDE/PlasmaSetup` KPackages, metadata weights,
`SetupModule`, `available`, `nextEnabled`, `contentItem`, installation and
separate optional C++ utilities. This supports additions without modifying
the application. It does not document replacing the shell or built-in modules.

`src/packagestructure/plasmasetuppackage.cpp:12–16` sets `plasma/packages` and
required `ui/main.qml`; `src/pagesmodel.cpp:23–43` discovers packages, sorts
weights and evaluates availability. `src/components/setupmodule.h:17–22`
defines the QML properties. These are source positions in the inspected archive.

## R2. Navigation and initialization constraints

`src/pagesmodel.cpp:34–37` creates an availability probe;
`pageItem():63–67` constructs the display instance separately. Availability is
not continuously observed by the model. `src/qml/Wizard.qml:93–97` invokes
`onPageActivated()` only during forward movement. Initial display and Back do
not invoke it. `onFinalPage` compares index with `stepCount - 1`; finality has
no special module-role metadata.

The comparator uses only integer weight; there is no tie-breaker. The installed
module IDs and weights are recorded in the baseline. `modules/CMakeLists.txt`
comments out cellular installation, notwithstanding its presence in source.

## R3. Shell and configuration boundaries

`src/CMakeLists.txt` embeds Main/Wizard/Landing/SessionMenu through
`qt_target_qml_sources`; `src/main.cpp:55–56` loads the module. The added
functional CLI option is `--remove-autologin`, not a branding/seed option.

`files/plasmasetuprc` documents only `[Accounts] UserGroups`, and
`src/accountcontroller.cpp:173–177` opens its absolute build-time path using
`KConfig::SimpleConfig`. Searching implementation/configuration found no
setup branding keys, ordered module-list configuration, logo slot, or seed
consumer. `/etc/xdg/plasmasetuprc` is Fedora-owned `%config(noreplace)` in the
binary header and spec.

## R4. Fedora branding patches

The exact SRPM applies:

- [`plasma-setup-load-default-wallpaper.patch`](https://src.fedoraproject.org/rpms/plasma-setup/blob/f44/f/plasma-setup-load-default-wallpaper.patch):
  changes landing lookup from `wallpapers/Next` PNG to `wallpapers/Default`
  JXL, light/dark directories, landscape `5120x2880.jxl` and portrait
  `1440x2960.jxl`. Spec `%prep` changes suffix to PNG if a specific default PNG
  exists in the build root. The inspected binary contains JXL names.
- [`plasma-setup-select-fedora-lookandfeel.patch`](https://src.fedoraproject.org/rpms/plasma-setup/blob/f44/f/plasma-setup-select-fedora-lookandfeel.patch):
  substitutes Fedora light/dark look-and-feel IDs for Breeze IDs.

Both path/format identifiers were found in the executable, and both Fedora
theme IDs were found in the installed prepare utility. These confirm the
packaged behavior rather than assuming upstream tag behavior alone.

## R5. Theme limitations

`modules/prepareutil/prepareutil.cpp:39` detects dark mode by
`ColorScheme == BreezeDark`. The Fedora patch does not change detection.
Lines 92–102 apply hard-coded Fedora IDs via `plasma-apply-lookandfeel`.
`modules/prepare/contents/ui/main.qml` exposes the toggle but has scaling UI
commented out. Ro-Theme's `RoDark` defaults do not satisfy this comparison.

`src/auth/authhelper.cpp`, function `setnewuserglobaltheme`, copies the setup
user's local `.config/kdeglobals` to the new user's home. `InitialStartUtil`
invokes it after creating a user; existing-user flow skips those steps.
This is not a general export of all system-wide theme defaults.

## R6. Landing and completion presentation

`src/qml/LandingComponent.qml` contains fixed Plasma Desktop/Mobile welcome
strings, a Plasma symbolic icon, 18-point white text, a darkening overlay and
the fixed wallpaper convention. Its distribution name comes from
`InitialStartUtil::distroName()`, which returns `KOSRelease::name()`.

`modules/finished/contents/ui/main.qml` contains existing/new-user messages
and a local `konqi-calling.png`; the properties are not wired to a system
branding descriptor. Editing this Fedora-owned module is a source/payload
change, not public branding configuration. Appending an extra page can change
which page gets Finish, so the proposed overview remains below weight 200.

## R7. Language and seed

`modules/languageutil/languageutil.cpp` initializes from system locale,
loads available translations from `plasmashell`, sets session language and
calls locale1 for upstream language application. No reference to
`installer-seed-v1.json`, `installer_ui_language_hint` or `/var/lib/ro-asd`
exists in the inspected source.

Local installer `lib/models/installer_handoff.dart:3–9` defines the path and
exact two-field object; its validation/tests reject identity, password,
locale, keyboard, timezone and other extra fields. Target finalization writes
the file and chmods it to `0644`. No upstream consumption is assumed.

## R8. Firstboot/lifecycle risks

The binary's service/sysuser/tmpfiles match the described upstream ownership.
`rpm -qp --triggers` confirms Fedora's older-release upgrade marker trigger.
RPM dependencies include `plasma-lookandfeel-fedora >= 6.5.3-3`,
`system-backgrounds-kde`, and `qt6qml(org.kde.plasma.private.kcm_keyboard)`.
The latter is an upstream dependency, not a recommended Ro extension import.

`src/initialstartutil.cpp:30–49` calls the void creation routine, then attempts
flag creation/logout even if creation returned on failure. This needs failure
injection/upstream handling; no VM reproduction or account change was attempted.
The existing source comments disable new-user temporary autologin calls.

## R9. Ro-Theme reuse and export gap

The inspected tree has colors/spacing/radius/opacity/motion tokens and generated
`dist/qml/RoTokens.qml`, but no typography source or public token `qmldir`.
The spec installs color schemes/global themes and shared wallpaper JPEGs,
but not the token singleton or a shared brand-logo directory. The logo's
canonical asset and Plymouth copy have the same Git blob ID.

Current system `kdeglobals` selects RoDark / `org.ro.dark`. Current spec does
not write per-user theme files in `%post`; the reset script now changes only
the invoking user on explicit invocation. This differs from the older script
behavior described by the local release policy snapshot. PR-01 records the
difference without changing that repository.

## Reproduction

Use a fresh temporary analysis directory. These commands read/extract data;
do not install the packages or launch the setup executable.

```bash
research_dir=$(mktemp -d /tmp/ro-plasma-research.XXXXXX)
curl -fL https://kojipkgs.fedoraproject.org/packages/plasma-setup/6.7.5/1.fc44/src/plasma-setup-6.7.5-1.fc44.src.rpm -o "$research_dir/source.rpm"
curl -fL https://kojipkgs.fedoraproject.org/packages/plasma-setup/6.7.5/1.fc44/x86_64/plasma-setup-6.7.5-1.fc44.x86_64.rpm -o "$research_dir/binary.rpm"
sha256sum "$research_dir/source.rpm" "$research_dir/binary.rpm"
rpm -qp --requires "$research_dir/binary.rpm"
rpm -qp --scripts "$research_dir/binary.rpm"
rpm -qp --triggers "$research_dir/binary.rpm"
mkdir "$research_dir/srpm" "$research_dir/rpm" "$research_dir/upstream"
rpm2cpio "$research_dir/source.rpm" | cpio -id --quiet -D "$research_dir/srpm"
rpm2cpio "$research_dir/binary.rpm" | cpio -id --quiet -D "$research_dir/rpm"
tar -xf "$research_dir/srpm/plasma-setup-6.7.5.tar.xz" -C "$research_dir/upstream"
cp -a "$research_dir/upstream/plasma-setup-6.7.5" "$research_dir/fedora"
patch -p1 --batch -d "$research_dir/fedora" -i "$research_dir/srpm/plasma-setup-load-default-wallpaper.patch"
patch -p1 --batch -d "$research_dir/fedora" -i "$research_dir/srpm/plasma-setup-select-fedora-lookandfeel.patch"
rg -n 'installer-seed|installer_ui_language_hint|ro-asd' "$research_dir/fedora"
```

The final search should have no implementation matches (exit 1 is expected).
Compare every installed page `main.qml` with the corresponding patched
`modules/<suffix>/contents/ui/main.qml`, parse installed metadata weights,
and inspect compiled wallpaper/theme identifiers without executing the binary.
Ro-Theme blobs can be checked with `git hash-object` against the baseline.

No permanent upstream source or extracted RPM payload is vendored into this
repository. Temporary analysis artifacts are not runtime integration.
