# Repin validation: plasma-setup 6.7.5 to 6.8.2 (2026-11-03)

Target: Fedora 44 x86_64, `plasma-setup-6.8.2-1.fc44` (replaces
`plasma-setup-6.7.5-1.fc44`). Upstream tag `v6.8.2`, commit
`1f7fee06103f2b0207a851da9b258c7c241bbb1e`.

The executable baseline is [`tests/baseline.json`](../../tests/baseline.json),
backed by the new [research baseline](../research/baseline-2026-11-03.json).
The [6.7.5 baseline](../research/baseline-2026-10-09.json) is unchanged and kept
as the historical record; the test suite checks its digest. Machine-readable
results are in [REPIN-6.8.2.json](REPIN-6.8.2.json). Source positions below are
for the 6.8.2 archive, relative to the archive root; "PR-01" refers to the
[6.7.5 research](../RESEARCH-PR-01.md).

## How the pins were produced

- Binary and source RPMs were downloaded from Koji (same URL layout as
  PR-01) and hashed. All payload file digests of the Koji binary RPM equal the
  installed package (`rpm -qp --dump` against `rpm -q --dump`: identical).
  Hashes pin bytes; they do not assert RPM or GPG signature trust, and the
  detached archive signature is still not verified.
- The SRPM payload was extracted; the archive was unpacked; both Fedora patches
  were applied to an analysis copy. The 18 critical files were compared against
  Git blob IDs of the `v6.8.2` commit (all equal).
- The eight installed page `main.qml` files match the patched source
  byte-for-byte. Installed metadata weights were parsed from the payload.
- The dependency list of the binary RPM is identical to 6.7.5 apart from the
  `config(plasma-setup)` version; the Fedora upgrade trigger is unchanged.

| Artifact | SHA-256 |
| --- | --- |
| Source RPM (Koji) | `0d60a9f44b3128dfebb315f3358cca2eca0d920f652252c16f3e9cd32bd9af3b` |
| x86_64 RPM (Koji) | `7bbfbb837f61a762f5779a4e566206b16ee9fe7f3402ddff028b319cc5a20fdb` |
| Upstream archive from SRPM | `d10c2d766e2b1a3afaa70c2995f0abc8eb9ff2da19c9a4e794ae9e89859758d7` |
| Fedora spec | `ab2f4750045321a39e557b2160d4ead7d9110729a1e56b2929a67aa4332eb177` |

The two Fedora patch files have the same digests as in 6.7.5. The spec differs
only in `Version:` and the changelog. The repository-signed copy of the SRPM
from the Fedora mirrors has different header bytes than the Koji file; the
payload is the same. The pin is the Koji file, as in PR-01.

## Findings re-verified against the 6.8.2 source

| Finding | 6.8.2 result | Evidence |
| --- | --- | --- |
| Built-in page IDs and weights | **Unchanged.** `language` 0, `keyboard` 5, `prepare` 10, `account` 20, `hostname` 30, `time` 40, `wifi` 50, `finished` 200. `cellular` (60) stays in source but is commented out of the build and not installed. | `modules/<id>/metadata.json` `X-KDE-Weight` (`language` line 142, `keyboard` 136, `prepare` 139, `account` 139, `hostname` 136, `time` 186, `wifi` 140, `finished` 141); `modules/CMakeLists.txt:8-9`; installed metadata checked by `harness.py installed` |
| Positional finality | **Unchanged.** The last model row is final; no module-role metadata. Finish is shown when `currentIndex == stepCount - 1`. | `src/qml/Wizard.qml:35`, finish button `:346-366` (`visible: root.onFinalPage` at `:351`) |
| Loader: PagesModel reload | **Unchanged** (file hash identical to 6.7.5): `listKPackages("KDE/PlasmaSetup")`, sort, availability probe by instantiating each module, only available modules appended. | `src/pagesmodel.cpp:19-47` |
| Loader: no weight tie-breaker | **Unchanged.** Comparator is `toInt() <` only. Ties and malformed weights are not rejected; Ro policy remains stricter. | `src/pagesmodel.cpp:25-29` |
| Package structure | **Unchanged.** `plasma/packages`, `ui` directory, required `ui/main.qml`. (PR-01 cited lines 12-16; the exact span is 10-14.) | `src/packagestructure/plasmasetuppackage.cpp:10-14` |
| `finish()` / `doUserCreationSteps()` false-completion risk | **Unchanged.** `finish()` calls `doUserCreationSteps()` (void), then `createCompletionFlag()` and `logOut()` unconditionally. A failed `createUser()` only logs a warning and returns; a TODO still says the error is not handled. | `src/initialstartutil.cpp:30-35`, `:44-49` |
| Finish handler | Unchanged semantics. Clicking Finish sets `nextEnabled = false` and calls `InitialStartUtil.finish()`. New: Enter/Return trigger the button, and focus moves to Finish when the final page is reached. | `src/qml/Wizard.qml:110-112`, `:357-365` |
| Dark-theme detection | **Unchanged.** Initial state is `colorScheme() == u"BreezeDark"_s`. Fedora does not patch it, so RoDark does not count as dark. | `modules/prepareutil/prepareutil.cpp:39`; toggle UI `modules/prepare/contents/ui/main.qml:76-80`; scaling UI still commented out (`:29-61`) |
| Fedora look-and-feel patch | **Unchanged.** Same patch; applies with no offset. Applies `org.fedoraproject.fedora(dark).desktop`. Both IDs found in the installed library (UTF-16 literals). | patched `modules/prepareutil/prepareutil.cpp:96,98` (unpatched `:96,98` use Breeze IDs) |
| Wallpaper patch | **Unchanged in content.** Same patch file; applies with a +7 line offset in `LandingComponent.qml`. Installed binary contains the `wallpapers/Default/...` and `.jxl` names (UTF-16). | patched `src/qml/LandingComponent.qml:53-57` (upstream `Next`/PNG at `:56-57`); `docs/research/baseline-2026-11-03.json` `binary_identifier_checks` |
| Static `org.kde.plasmasetup.components` | **Unchanged.** `add_library(componentsplugin STATIC)`; the installed module has `qmldir`, `.qmltypes`, `kde-qmlmodule.version`, `qml/Debouncer.qml` and no `.so`. | `src/components/CMakeLists.txt:4`; `harness.py installed` rejects any `.so` there |
| Distribution name / branding | Unchanged. `InitialStartUtil::distroName()` returns `KOSRelease::name()`. | `src/initialstartutil.cpp:25-28`; `src/qml/LandingComponent.qml:186` |
| No seed consumer | Unchanged. No `installer-seed`, `installer_ui_language_hint` or `/var/lib/ro-asd` string in the patched 6.8.2 tree. | recursive search (no matches) |
| Setup config | Unchanged keys. Only the position moved: the absolute-path `KConfig` (`SimpleConfig`) open is now at `src/accountcontroller.cpp:193` (was 175). | `files/plasmasetuprc` (hash unchanged) |

## Behavior changes between 6.7.5 and 6.8.2 that matter for Ro pages

1. **`onPageActivated()` is now called in more cases.**
   - 6.7.5 called it only on forward movement (`Wizard.qml:93-97`).
   - 6.8.2 routes it through `activatePage()` (`src/qml/Wizard.qml:85-89`) and
     calls it on forward movement (`:105`), on Back (`:139`) and when leaving
     the landing screen for the first page (`:166`).
   - A Ro page must treat the hook as idempotent and must not assume it runs
     only once per forward step. It must not reset user input on Back.
   - A hook runs for the page that becomes current, never for the landing screen.
2. **New public `SetupModule::nextRequested()` signal**
   (`src/components/setupmodule.h:47-50`). `Wizard.qml:446-454` handles it: it
   calls `requestNextPage()` only if the module is current and
   `nextEnabled` is true, and ignores it on the final page, so a page cannot use
   it to complete setup. Upstream `hostname` (`:117-121`) and `account`
   (`:235`) emit it on Enter. Optional for Ro pages. The probe now requires
   the signal to exist in the SRPM component, and it must not fire at creation.
   This is a new API surface (additive); nothing in 6.7.5 had it.
3. **`SetupModule` otherwise unchanged:** properties `available`, `cardWidth`,
   `nextEnabled`, `contentItem` (required) and the four notify signals have the
   same declarations (`setupmodule.h:18-23`, `:42-46`). `setupmodule.cpp` and
   `src/components/CMakeLists.txt` hashes are identical to 6.7.5. The static
   `Debouncer.qml` is unchanged.
4. **Keyboard and focus handling in the shell:** Enter/Return on Back, Next,
   Finish and the landing button; focus is forced on the landing button
   (`LandingComponent.qml`), on Finish when the final page is shown, and on the
   language search field via the language page's own hook. Landing content is
   disabled while hidden (`enabled: !root.showingLanding` on the steps host,
   `landingActive` on the landing). Ro pages should expect focus to be moved by
   the shell and must supply sensible tab order and accessible names.
5. **Window activation resets the landing screen** (`src/qml/Main.qml:24-28`).
   This is shell behavior and not a page-level concern.
6. **Built-in page implementation changes (no ID or weight change):**
   `language` main.qml uses a new `languageModel` proxy
   (`modules/languageutil/languagesortfilterproxymodel.{h,cpp}`) instead of
   `availableLanguages`; `account` gets `sanitizeUsername()`
   (`src/accountcontroller.cpp:163-178`); `hostname` and `account` emit
   `nextRequested`; `wifi` `ConnectionItemDelegate.qml` changed. `keyboard`,
   `prepare`, `time`, `finished` `main.qml` are byte-identical to 6.7.5. The new
   installed `main.qml` hashes for `language`, `account` and `hostname` are in
   the baseline.
7. **Build minimums raised:** Qt 6.10 to 6.11 and KF 6.26 to 6.30
   (`CMakeLists.txt:11-12`). The probe's CMake minimums were raised to match.
8. **Minor:** `files/kglobalaccelrc` uses `org.kde.screenreader.desktop`;
   `SessionMenu.qml` tooltips removed; more translations (el, pa, sr variants,
   ta, ug).

Nothing observed changes the PR-01 constraints: weights 1 and 190 stay free,
language stays first at weight 0, finished stays last at weight 200, the
dark-theme comparison still requires `BreezeDark`, and there is still no
upstream branding configuration or seed consumer.

## What this validation does not claim

Static inspection, the policy tests and the container load test do not
execute the upstream wizard, do not render the sample in a graphical session and
do not exercise the new activation or `nextRequested` behavior against the real
shell. Those need the separate disposable VM acceptance described in the
harness guide. The Ro-Theme and installer-context sections of the old baseline
were not re-inspected for this repin and are not part of the 6.8.2 baseline.

## Commands

`python3 -m unittest discover -s tests -v`, `python3 tools/harness.py contracts`
and `python3 tools/harness.py installed` pass on this host (Fedora 44 with the
exact installed RPM). `python3 tools/harness.py prepare --cache <dir>` downloads
and verifies the Koji artifacts, SRPM payload, patches and critical sources.
The container load test (`tools/run-container.sh build` then `test`) **passed** on 2026-11-03: the development package loads against the rebuilt 6.8.2 `org.kde.plasmasetup.components` with the packaged discovery plugin. Environment: `qt6-qtbase-6.11.2-3.fc44.x86_64`, `qt6-qtdeclarative-6.11.2-2.fc44.x86_64`, `kf6-kpackage-6.31.0-1.fc44.x86_64`, `extra-cmake-modules-6.31.0-1.fc44.noarch`. Graphical and firstboot remain unverified.
