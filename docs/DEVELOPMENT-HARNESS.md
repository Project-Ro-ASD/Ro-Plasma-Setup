# KPackage development harness (PR-02)

This is development tooling for Fedora 44 x86_64 and exactly
`plasma-setup-6.7.5-1.fc44.x86_64`. Never include the sample or runner in a Ro
image. The [PR-01 architecture](ARCHITECTURE-PR-01.md) and its
[research baseline](research/baseline-2026-10-09.json) remain authoritative.
`tests/baseline.json` contains the executable subset, provenance digest and
additional component and loader/metadata digests from the same verified artifacts. Baseline
drift fails closed and requires a reviewed repin, including affected tests.

## Scope and ownership

The probe discovers packages with the real Fedora `KDE/PlasmaSetup` structure
plugin and `KPackage::PackageLoader::listKPackages()`, matching upstream
`PagesModel::reload()`. It reads built-in metadata but instantiates **only** the
development module. It never launches `/usr/libexec/plasma-setup`, its bootutil,
KAuth helpers, account controller, built-in pages or upstream wizard shell.

The sample uses the public `available`, `nextEnabled` and required `contentItem`
properties. Its checkbox changes only in-memory state, resetting on each
creation. Strings use `qsTr()` for future translation extraction; no production
catalog, brand asset, Ro-Theme token copy or account backend is included.
Qt Quick Controls' Basic style keeps this probe independent of desktop styling.
Production pages must later consume Ro-Theme's agreed public exports.

Ro-Installer's seed `/var/lib/ro-asd/firstboot/installer-seed-v1.json` is neither
read nor changed. Authentication, accounts, session management and completion
remain upstream-owned; image integration remains Ro-image-compose-owned.

## Important import limitation in this Fedora build

`org.kde.plasmasetup.components` is **static**. Its installed `qmldir` and
`.qmltypes` describe the module, but the RPM supplies no dynamic component
plugin for a generic QML runner. Upstream's executable embeds the plugin.
Thus `qml`/`qmlscene` or static lint alone cannot prove the sample loads.

The harness obtains and SHA256-verifies the exact binary RPM, source RPM,
archive, Fedora patches and critical sources. It builds **only the unchanged
`src/components` subdirectory**, registering that upstream static QML plugin in
a separate unprivileged executable. Fedora's two patches do not touch this
component; this fact is checked. No upstream source is vendored or edited; no
substitute `SetupModule` or override of an `org.kde.*` module is installed. The
runner uses QObject's public property interface, without upstream private
headers. There is no `install()` target.

This is a development adapter for the static component's build, not a new
production SDK. Load results cover the rebuilt, exact SRPM component and the
packaged KPackage discovery plugin. They do **not** certify the original
executable, upstream host-card layout, wizard navigation or firstboot behavior.
Those need separate disposable VM acceptance later.

Evidence: pinned [component build][components], [loader][loader],
[package structure][structure], [custom-module guide][guide],
[Qt static plugin documentation][qt-plugins] and [KPackage API][kpackage].

## Environment and static commands

Static policy tests need Python 3.12+ (standard library only). Read-only installed
package checks additionally require Fedora 44 x86_64 with the exact RPM and
`rpm`. They are safe on a development host; they do not execute QML.

```sh
python3 -m unittest discover -s tests -v
python3 tools/harness.py contracts
python3 tools/harness.py installed
```

`contracts` reports load and graphics as unverified. Checks include required
metadata and mainscript, positive weights 1/190, duplicate IDs/weights,
missing/string/boolean/fractional/out-of-range weights and preserved first/last
pages. This stricter Ro policy is intentional: upstream sorts `toInt()` values
without rejecting ties or malformed weights.

## Container: exact package and real QML loading

Use rootless Podman on an x86_64 Linux host, with networking for the build and
enough storage for Fedora/Qt/KF development dependencies. The Fedora 44 base
image is pinned by digest. Build dependencies come from Fedora 44 repositories;
their actual versions are recorded in each run. They are not a frozen full
distribution snapshot. The target Plasma Setup RPM and source archive are
digest-pinned and cannot silently update to another release or KDE master.

```sh
bash tools/run-container.sh build
mkdir -p test-output
bash tools/run-container.sh test > test-output/container-report.json
```

Build installs the verified RPM **inside the container only**, with its
scriptlets disabled. The test runs as UID 65534, with a read-only root filesystem,
no network, no capabilities and a fresh temporary HOME/XDG tree. There are no
host mounts, graphical sockets, D-Bus sockets or devices. `QT_QPA_PLATFORM=offscreen`
is used for object loading; this is **not graphical certification**.

Each test run copies the sample to
`$XDG_DATA_HOME/plasma/packages/org.ro.plasmasetup.development` in a fresh sandbox.
KPackage's normal data lookup discovers it alongside Fedora's
`/usr/share/plasma/packages/org.kde.plasmasetup.*`. The system installation root,
required `contents/ui/main.qml` mapping and Fedora structure-plugin path are
validated from actual installed payload ownership. No Fedora-owned files are
replaced. Install refuses an existing destination; removal deletes only this
invocation's copied module. The runner checks disappearance and that all eight
upstream packages remain discoverable afterward. No sample survives the command.

The two discovery scenarios use the **same development sample**, once at weight
1 and once at 190. These are fixtures for later introduction/overview pages, not
implementations of those pages. Actual discovered order must be exactly the
pinned eight Fedora pages plus that sample. Language stays first at 0; upstream
finished stays last at 200. A separate policy fixture tests both future positions
together.

The runtime runner checks upstream property defaults and notify signals,
available false/true, checkbox-bound nextEnabled false/true, required/writable
contentItem, and two successive instances with fresh state. The first is
destroyed before the second, reflecting discovery then display. Content hashes
of HOME, data and config must remain identical; the container's read-only root
prevents system writes. Cache/runtime directories are ephemeral and are not
claimed to be persistent state. A failing test exits nonzero with `FAIL:` and the
specific contract/import/discovery error on stderr; stdout is the JSON report.

To rebuild after changing tooling or the sample, run `build` again. Remove only
the local development image when finished:

```sh
podman image rm localhost/ro-plasma-setup-harness:6.7.5-1.fc44
```

## Disposable VM: graphical sample test

Use a disposable Fedora 44 x86_64 desktop VM snapshot with an ordinary test user,
the exact Plasma Setup RPM, Qt 6.10+, KF/ECM 6.26+, a working Wayland/X11 display,
and the dependencies listed in `containers/Containerfile`. Do not use the
`plasma-setup` system user. Do not enable/restart login-manager/setup services,
alter accounts or manipulate OOBE markers. PR-02's native runner is separate
from the privileged wizard; it displays only this sample in a plain Qt window.

Run these commands **inside that VM**. The variable is an explicit assertion by
the operator that the machine is disposable; it is not automatic VM detection.

```sh
python3 tools/harness.py prepare --cache .cache/fedora-baseline
cmake -S tests/runtime -B build/probe -G Ninja \
  -DPLASMA_SETUP_SOURCE="$PWD/.cache/fedora-baseline/source/plasma-setup-6.7.5"
cmake --build build/probe --parallel 2
mkdir -p test-output/vm
RO_HARNESS_DISPOSABLE_VM=1 RO_HARNESS_EVIDENCE_DIR="$PWD/test-output/vm" \
  python3 tools/harness.py run --graphical \
  --cache .cache/fedora-baseline --runner build/probe/ro-plasma-probe \
  > test-output/vm/report.json
```

`prepare` needs `rpm2cpio`, `cpio`, Python 3.12+ and download access. Runtime
downloads nothing. Graphical mode rejects offscreen/minimal platforms and
containers. It opens the sample, verifies an exposed nonblank frame and saves
weight-1/190 screenshots with digests. Review the images for visible text,
checkbox, clipping and keyboard interaction; the automated frame check is only
rendering evidence, not a visual-quality/accessibility review. Record VM image,
package versions, resolution, scale, locale and manual findings with the report.

If this VM step cannot run, retain `graphical.status = unverified`. Static and
offscreen load success cannot promote that status. Even a successful standalone
VM test leaves actual upstream shell and firstboot lifecycle **unverified**.

[components]: https://github.com/KDE/plasma-setup/blob/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd/src/components/CMakeLists.txt
[loader]: https://github.com/KDE/plasma-setup/blob/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd/src/pagesmodel.cpp
[structure]: https://github.com/KDE/plasma-setup/blob/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd/src/packagestructure/plasmasetuppackage.cpp
[guide]: https://github.com/KDE/plasma-setup/blob/6089b09b2c4f9b95f58da5c7f2a2d65faf9ba7bd/docs/CUSTOM_MODULES.md
[qt-plugins]: https://doc.qt.io/qt-6/qtqml-modules-cppplugins.html
[kpackage]: https://api.kde.org/kpackage-packageloader.html
