#!/usr/bin/env python3
"""Pinned, unprivileged Plasma Setup development tests. No wizard execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "tests/baseline.json").read_text())
SAMPLE = ROOT / "tests/development-package"
SAMPLE_ID = "org.ro.plasmasetup.development"
LANGUAGE = "org.kde.plasmasetup.language"
FINISHED = "org.kde.plasmasetup.finished"


class ContractError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_baseline():
    provenance = LOCK["provenance"]
    path = ROOT / provenance["baseline_path"]
    require(sha(path) == provenance["baseline_sha256"], "PR-01 baseline changed; review and repin before testing")
    baseline = json.loads(path.read_text())
    require(LOCK["artifacts"] == baseline["artifacts"] and LOCK["srpm_contents"] == baseline["srpm_contents"]
            and LOCK["installed_modules"] == baseline["fedora"]["installed_modules"], "harness lock differs from PR-01 baseline")


def command(args, **kwargs):
    result = subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)
    return result.stdout.strip()


def metadata(path):
    path = Path(path)
    data = json.loads((path / "metadata.json").read_text())
    plugin = data.get("KPlugin", {})
    require(data.get("KPackageStructure") == "KDE/PlasmaSetup", f"{path}: wrong KPackageStructure")
    require(data.get("X-KDE-ParentApp") == "org.kde.plasmasetup", f"{path}: wrong parent app")
    require(isinstance(plugin.get("Id"), str) and plugin["Id"], f"{path}: missing plugin ID")
    require(path.name == plugin["Id"] or path == SAMPLE, f"{path}: directory/ID mismatch")
    for field in ("Name", "Description", "License"):
        require(isinstance(plugin.get(field), str) and plugin[field], f"{path}: missing KPlugin.{field}")
    require((path / "contents/ui/main.qml").is_file(), f"{path}: missing required mainscript")
    return {"id": plugin["Id"], "weight": data.get("X-KDE-Weight")}


def validate_order(pages):
    """Stricter Ro policy: Qt's toInt/sort do not reject malformed weights or ties."""
    ids, weights = set(), set()
    for page in pages:
        ident, weight = page["id"], page.get("weight")
        require(ident not in ids, f"duplicate plugin ID: {ident}")
        require(type(weight) is int and 0 <= weight <= 200, f"{ident}: weight must be an integer in [0, 200]")
        require(weight not in weights, f"duplicate weight {weight}: {ident}")
        if ident.startswith("org.ro."):
            require(weight in (1, 190), f"{ident}: reserved Ro test weights are 1 and 190")
        ids.add(ident)
        weights.add(weight)
    ordered = sorted(pages, key=lambda page: page["weight"])
    require(ordered and ordered[0] == {"id": LANGUAGE, "weight": 0}, "language must remain first at weight 0")
    require(ordered[-1] == {"id": FINISHED, "weight": 200}, "upstream finished must remain last at weight 200")
    return ordered


def contracts():
    base = [{"id": p["id"], "weight": p["weight"]} for p in LOCK["installed_modules"]]
    sample = metadata(SAMPLE)
    require(sample == {"id": SAMPLE_ID, "weight": 1}, "development sample must have its unique ID and weight 1")
    qml = (SAMPLE / "contents/ui/main.qml").read_text()
    for item in ("import QtQuick", "import QtQuick.Controls", "import QtQuick.Layouts",
                 "import org.kde.plasmasetup.components", "PlasmaSetupComponents.SetupModule",
                 "available:", "nextEnabled:", "contentItem:"):
        require(item in qml, f"sample missing public import/property: {item}")
    # Positive policy fixture has both future positions, but is not production content.
    return validate_order(base + [sample, {"id": "org.ro.plasmasetup.future-overview-fixture", "weight": 190}])


def prepare(cache):
    cache.mkdir(parents=True, exist_ok=True)
    for artifact in LOCK["artifacts"]:
        path = cache / artifact["filename"]
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".download")
            with urllib.request.urlopen(artifact["url"], timeout=90) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            temporary.rename(path)
        require(sha(path) == artifact["sha256"], f"SHA256 mismatch: {path}; remove corrupt cache and retry")
    srpm = cache / "srpm"
    if not srpm.exists():
        srpm.mkdir()
        payload = subprocess.check_output(["rpm2cpio", str(cache / LOCK["artifacts"][0]["filename"])])
        subprocess.run(["cpio", "-idm", "--quiet", "--no-absolute-filenames"], input=payload, cwd=srpm, check=True)
    for entry in LOCK["srpm_contents"]:
        require(sha(srpm / entry["path"]) == entry["sha256"], f"SRPM payload drift: {entry['path']}")
    source = cache / "source"
    if not source.exists():
        source.mkdir()
        with tarfile.open(srpm / "plasma-setup-6.7.5.tar.xz") as archive:
            archive.extractall(source, filter="data")
    tree = source / "plasma-setup-6.7.5"
    for patch in srpm.glob("*.patch"):
        require("src/components/" not in patch.read_text(), f"Fedora now patches SetupModule: review {patch.name}")
    verify_source(tree)
    return tree


def verify_source(tree):
    for name, digest in LOCK["source_files"].items():
        require(sha(tree / name) == digest, f"pinned upstream source drift: {name}")


def installed():
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    require(release.get("ID", "").strip('"') == "fedora" and release.get("VERSION_ID", "").strip('"') == "44", "package checks require Fedora 44")
    actual = command(["rpm", "-q", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}", "plasma-setup"])
    require(actual == LOCK["nevra"], f"unsupported baseline: {actual}; expected {LOCK['nevra']}")
    owned = set(command(["rpm", "-ql", "plasma-setup"]).splitlines())
    for name, digest in LOCK["runtime_files"].items():
        path = Path("/") / name
        require(str(path) in owned and sha(path) == digest, f"Fedora runtime payload drift: {path}")
    root = Path("/usr/share/plasma/packages")
    pages = []
    for page in LOCK["installed_modules"]:
        path = root / page["id"]
        require(str(path / "metadata.json") in owned, f"not Fedora-owned: {path}")
        actual_page = metadata(path)
        require(actual_page == {"id": page["id"], "weight": page["weight"]}, f"installed metadata drift: {path}")
        require(sha(path / "contents/ui/main.qml") == page["main_qml_sha256"], f"installed QML drift: {path}")
        pages.append(actual_page)
    plugin = "/usr/lib64/qt6/plugins/kf6/packagestructure/plasmasetup.so"
    # Query the payload rather than assuming the plugin directory used by other KDE releases.
    candidates = [p for p in owned if p.endswith("/packagestructure/plasmasetup.so")]
    require(len(candidates) == 1 and Path(candidates[0]).is_file(), f"missing real Fedora KPackage structure plugin: {plugin}")
    components = "/usr/lib64/qt6/qml/org/kde/plasmasetup/components/"
    require(components + "qmldir" in owned, "missing upstream QML module descriptor")
    require(not any(p.startswith(components) and p.endswith(".so") for p in owned), "component packaging changed: revisit static plugin harness")
    validate_order(pages)
    return {"nevra": actual, "package_structure_plugin": candidates[0], "qml_components": "static plugin embedded in upstream executable", "pages": pages}


def snapshot(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}


def stage(sandbox, weight):
    """Install only in a harness-created fresh XDG_DATA_HOME, never system/home paths."""
    require((sandbox / ".ro-harness-sandbox").is_file(), "refusing installation outside harness sandbox")
    destination = sandbox / "data/plasma/packages" / SAMPLE_ID
    require(not destination.exists() and not destination.is_symlink(), "sample destination already exists; refusing replacement")
    shutil.copytree(SAMPLE, destination)
    data = json.loads((destination / "metadata.json").read_text())
    data["X-KDE-Weight"] = weight
    (destination / "metadata.json").write_text(json.dumps(data, indent=2) + "\n")
    return destination


def run(runner, cache, graphical=False):
    require(os.geteuid() != 0, "runtime probe must run as an unprivileged user")
    require(Path("/run/.containerenv").exists() or os.environ.get("RO_HARNESS_DISPOSABLE_VM") == "1",
            "runtime tests require an isolated container or disposable VM; host desktop is forbidden")
    require(runner.name == "ro-plasma-probe" and runner.is_file(), "--runner must be the separately built ro-plasma-probe; never pass the upstream wizard")
    if graphical:
        require(not Path("/run/.containerenv").exists() and os.environ.get("RO_HARNESS_DISPOSABLE_VM") == "1",
                "graphical evidence requires a disposable VM desktop")
        require(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"), "no graphical display; rendering unverified")
    verify_source(cache / "source/plasma-setup-6.7.5")
    report = {"schema_version": 1, "static": {"status": "passed", "order_fixture": contracts(), **installed()},
              "load": {"status": "unverified"}, "graphical": {"status": "unverified", "reason": "disposable VM graphical test not run"},
              "firstboot": {"status": "unverified", "reason": "PR-02 never executes upstream wizard or lifecycle"}}
    report["environment"] = command(["rpm", "-q", "qt6-qtbase", "qt6-qtdeclarative", "kf6-kpackage", "extra-cmake-modules"]).splitlines()
    results = []
    for weight in (1, 190):
        with tempfile.TemporaryDirectory(prefix="ro-plasma-harness-") as temporary:
            sandbox = Path(temporary)
            (sandbox / ".ro-harness-sandbox").touch()
            for name in ("home", "data", "config", "cache", "runtime"):
                (sandbox / name).mkdir(mode=0o700)
            sample = stage(sandbox, weight)
            original = snapshot(sample)
            env = dict(os.environ, HOME=str(sandbox / "home"), XDG_DATA_HOME=str(sandbox / "data"),
                       XDG_DATA_DIRS="/usr/share", XDG_CONFIG_HOME=str(sandbox / "config"),
                       XDG_CONFIG_DIRS="/etc/xdg", XDG_CACHE_HOME=str(sandbox / "cache"),
                       XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR", str(sandbox / "runtime")) if graphical else str(sandbox / "runtime"),
                       QML_DISABLE_DISK_CACHE="1", QT_QUICK_CONTROLS_STYLE="Basic")
            if not graphical:
                env.update(QT_QPA_PLATFORM="offscreen", QSG_RHI_BACKEND="software")
                for key in ("DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "WAYLAND_DISPLAY"):
                    env.pop(key, None)
            for key in ("QML_IMPORT_PATH", "QML2_IMPORT_PATH", "QT_PLUGIN_PATH"):
                env.pop(key, None)
            before = {name: snapshot(sandbox / name) for name in ("home", "data", "config")}
            args = [str(runner), str(weight)]
            if graphical:
                args += ["--render", str(sandbox / "frame.png")]
            result = json.loads(command(args, env=env, timeout=45))
            discovered = validate_order(result.get("pages", []))
            expected = validate_order(report["static"]["pages"] + [{"id": SAMPLE_ID, "weight": weight}])
            require(discovered == expected, "real KPackage discovery differs from pinned Fedora pages plus sample")
            after = {name: snapshot(sandbox / name) for name in ("home", "data", "config")}
            require(before == after, "double instantiation changed persistent HOME/data/config state")
            require(snapshot(sample) == original, "module mutated its installed payload")
            require(result.get("status") == "passed", "native load probe did not pass")
            if graphical:
                require((sandbox / "frame.png").is_file(), "graphical test did not save its frame")
                result["render"]["frame_sha256"] = sha(sandbox / "frame.png")
                # Keep reviewable frames outside the persistent state being checked.
                if os.environ.get("RO_HARNESS_EVIDENCE_DIR"):
                    evidence = Path(os.environ["RO_HARNESS_EVIDENCE_DIR"]).resolve()
                    evidence.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(sandbox / "frame.png", evidence / f"sample-weight-{weight}.png")
            # Removal is confined to the exact fresh package copied by this invocation.
            shutil.rmtree(sample)
            removed = json.loads(command([str(runner), "--absent"], env=env, timeout=20))
            require(removed.get("sample_absent") is True, "sample still discovered after removal")
            require(validate_order(removed.get("pages", [])) == validate_order(report["static"]["pages"]),
                    "removal changed upstream package discovery")
            results.append({"weight": weight, "persistent_state_unchanged": True, "removal_verified": True, **result})
    report["load"] = {"status": "passed", "scope": "Fedora KPackage loader + unmodified SRPM SetupModule linked into independent runner", "scenarios": results}
    if graphical:
        report["graphical"] = {"status": "passed", "scope": "standalone sample rendered in disposable VM; upstream host card/lifecycle unverified"}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("contracts", "prepare", "installed", "run"))
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/fedora-baseline")
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--graphical", action="store_true")
    args = parser.parse_args()
    try:
        verify_baseline()
        if args.action == "contracts":
            result = {"static": "passed", "order_fixture": contracts(), "load": "unverified", "graphical": "unverified"}
        elif args.action == "prepare":
            result = {"verified_source": str(prepare(args.cache.resolve()))}
        elif args.action == "installed":
            result = installed()
        else:
            require(args.runner is not None, "run requires --runner PATH")
            result = run(args.runner.resolve(), args.cache.resolve(), args.graphical)
        print(json.dumps(result, indent=2))
    except (ContractError, OSError, ValueError, subprocess.SubprocessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"FAIL: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
