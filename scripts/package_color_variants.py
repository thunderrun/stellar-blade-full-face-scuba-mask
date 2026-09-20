"""Validate/package the CNS 1.1.2 visor colors; optionally update installed JSON.

Uses the verified 1.1.1 package as its immutable binary/configuration baseline.
The output directory must be empty/new. No Unreal recook is performed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


VERSION = "1.1.2"
CONFIG_NAME = "CodexCNS-ScubaMask.dekcns.json"
BINARY_NAMES = tuple("CodexCNS-ScubaMask-947." + ext for ext in ("pak", "ucas", "utoc"))
FILE_NAMES = (*BINARY_NAMES, CONFIG_NAME)
VARIANT_NAMES = ["Clear", "Smoke", "Blue", "Cyan", "Green", "Amber", "Red", "Purple"]
PARAM_NAMES = {"GlassColor In", "GlassColor Out"}
ARCHIVE_NAME = "Full-Face-Scuba-Mask-CNS-Colors-1.1.2.zip"
INSTALL_PARTS = ("SB", "Content", "Paks", "~mods", "CustomNanosuitSystem", "Cosmetics", "CodexScubaMask")
INSTALL_PREFIX = "/".join(INSTALL_PARTS)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    # Duplicate keys and non-finite constants are invalid for this guarded build.
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Invalid JSON constant {value} in {path}")

    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def inside(path, directory):
    return path == directory or directory in path.parents


def disjoint(first, second, message):
    require(not inside(first, second) and not inside(second, first), message)


def read_owned_file(directory, name):
    path = directory / name
    require(path.resolve().parent == directory.resolve(), f"File escapes directory: {path}")
    require(path.is_file() and not path.is_symlink(), f"Expected regular file: {path}")
    return path.read_bytes()


def baseline(base_dir):
    manifest = load_json(base_dir / "package-manifest.json")
    require(manifest.get("version") == "1.1.1", "Base package must be version 1.1.1")
    records = manifest.get("files")
    require(isinstance(records, list) and len(records) == 4, "Base manifest needs exactly four mod files")
    require(all(isinstance(item, dict) for item in records), "Invalid base file record")
    require({item.get("name") for item in records} == set(FILE_NAMES), "Unexpected base file names")
    contents = {}
    for item in records:
        name = item["name"]
        require(isinstance(item.get("sha256"), str) and
                re.fullmatch(r"[0-9a-fA-F]{64}", item["sha256"]), f"Invalid SHA-256 for {name}")
        data = read_owned_file(base_dir / "files", name)
        require(len(data) == item.get("bytes"), f"Base size mismatch: {name}")
        require(sha256(data) == item["sha256"].lower(), f"Base hash mismatch: {name}")
        contents[name] = data
    return manifest, contents


def single_outfit(document, label):
    require(isinstance(document, list) and len(document) == 1 and isinstance(document[0], dict),
            f"{label} must contain exactly one outfit object")
    return document[0]


def validate_config(repo, base_dir):
    old = single_outfit(load_json(base_dir / "files" / CONFIG_NAME), "Base configuration")
    new = single_outfit(load_json(repo / "cns" / CONFIG_NAME), "Current configuration")
    require(old.get("UniqueFitID") == "Codex_FullFaceScubaMask_v1", "Unexpected base UniqueFitID")
    allowed = {"Description", "OutfitNames", "OutfitDatas"}
    require({k: v for k, v in old.items() if k not in allowed} ==
            {k: v for k, v in new.items() if k not in allowed},
            "Only Description, OutfitNames and OutfitDatas may change; preserve all original controls and fields")
    require(new.get("UniqueFitID") == old["UniqueFitID"], "UniqueFitID must stay unchanged")
    require(new.get("UserConfigs") == old.get("UserConfigs"), "UserConfigs must stay unchanged")
    require(isinstance(new.get("Description"), str) and bool(new["Description"]), "Description must be nonempty")
    require(new.get("OutfitNames") == VARIANT_NAMES, "Expected Clear, Smoke, Blue, Cyan, Green, Amber, Red, Purple in order")
    mesh_paths = old.get("OutfitPaths")
    require(isinstance(mesh_paths, list) and len(mesh_paths) == 1, "Base needs one original mesh path")

    ue = load_json(repo / "ue" / "manifest.json")
    contract = load_json(repo / "ue" / "References" / "material-parameter-contract.json")
    materials = ue.get("materials")
    require(isinstance(materials, list) and len(materials) == 9 and ue.get("expected_material_count") == 9,
            "Expected the original nine material sections")
    cup, visor = materials[7], materials[8]
    require(cup.get("source_name") == "M_Scuba_NasalCup" and visor.get("source_name") == "M_Scuba_Visor",
            "Cup/visor must remain sections 7/8")
    require(visor.get("parent_key") == "visor", "Visor must use the original glass parent")
    require(ue.get("material_parents", {}).get("visor", {}).get("path") == contract.get("visor", {}).get("asset"),
            "Visor parent differs from the native material contract")
    require(PARAM_NAMES <= set(contract.get("visor", {}).get("vectors", {})), "Native glass color parameter contract missing")
    require(PARAM_NAMES <= set(visor.get("vector_parameters", {})), "Visor glass color parameters missing")
    require(all(visor["vector_parameters"][name] == [0.12, 0.12, 0.12, 1.0] for name in PARAM_NAMES),
            "Original clear visor color changed")
    mesh_package = ue.get("mesh_package", "")
    require(mesh_paths[0] == mesh_package + "." + mesh_package.rsplit("/", 1)[-1], "Mesh differs from UE manifest")

    for control in new["UserConfigs"].get("ScalarControls", []):
        index = control.get("MaterialIndex")
        name = control.get("ParamName")
        require(index in (7, 8), "Opacity control targets an unexpected material")
        require(name in contract["visor"].get("scalars", {}) and name in materials[index].get("scalar_parameters", {}),
                "Opacity control is absent from the native material contract")
        require(control.get("Value") == materials[index]["scalar_parameters"][name], "Opacity defaults differ from UE manifest")

    variants = new.get("OutfitDatas")
    require(isinstance(variants, list) and len(variants) == len(VARIANT_NAMES), "Expected eight variant data entries")
    colors = []
    for name, variant in zip(VARIANT_NAMES, variants):
        require(isinstance(variant, dict) and set(variant) == {"Mesh", "Materials", "Parameters"}, f"Unexpected variant fields: {name}")
        require(variant["Mesh"] == mesh_paths[0] and variant["Materials"] == [], f"Variant must retain original mesh/materials: {name}")
        parameters = variant["Parameters"]
        require(isinstance(parameters, list) and len(parameters) == 2, f"Expected two color parameters: {name}")
        require(all(isinstance(param, dict) for param in parameters), f"Invalid parameters: {name}")
        require({param.get("ParamName") for param in parameters} == PARAM_NAMES, f"Wrong glass parameters: {name}")
        values = []
        for param in parameters:
            require(set(param) == {"MaterialIndex", "LayerIndex", "ParamType", "ParamName", "Association", "Value"},
                    f"Unexpected parameter fields: {name}")
            require(param["MaterialIndex"] == 8 and param["LayerIndex"] == -1 and
                    param["ParamType"] == "Vector" and param["Association"] == "Global", f"Color parameter scope changed: {name}")
            value = param["Value"]
            require(isinstance(value, list) and len(value) == 4 and
                    all(type(channel) in (int, float) and math.isfinite(channel) and 0 <= channel <= 1 for channel in value) and
                    value[3] == 1, f"Expected finite RGBA channels in [0,1] with alpha 1: {name}")
            values.append(value)
        require(values[0] == values[1], f"Inner/outer visor colors must match: {name}")
        colors.append(values[0])
    require(colors[0] == [0.12, 0.12, 0.12, 1.0], "Clear must retain the original neutral visor tint")
    require(len({tuple(value) for value in colors}) == len(colors), "Each visor color must be distinct")
    return colors


def install_preflight(install_dir, output_dir, contents, target):
    require(tuple(part.casefold() for part in install_dir.parts[-7:]) == tuple(part.casefold() for part in INSTALL_PARTS),
            "--install-dir must be the existing SB/Content/Paks/~mods/CustomNanosuitSystem/Cosmetics/CodexScubaMask directory")
    require(install_dir.is_dir(), "Install directory does not exist; use the full ZIP for a first installation")
    disjoint(output_dir, install_dir.parents[6], "Output/backups must be outside the game directory")
    for name in BINARY_NAMES:
        require(read_owned_file(install_dir, name) == contents[name], f"Installed binary differs from verified base: {name}")
    old = read_owned_file(install_dir, CONFIG_NAME)
    require(old in (contents[CONFIG_NAME], target), "Installed configuration is neither the verified base nor target; refusing to overwrite it")
    # Refuse a live replacement on Windows so CNS never reads a partially updated session.
    if os.name == "nt":
        processes = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], check=True, capture_output=True).stdout.lower()
        require(b"sb-win64-shipping.exe" not in processes and b"stellarblade.exe" not in processes,
                "Close Stellar Blade before installing the updated configuration")
    return old


def install_json(install_dir, output_dir, contents, target):
    old = install_preflight(install_dir, output_dir, contents, target)
    receipt = {"version": VERSION, "installed_directory": str(install_dir), "json_only": True,
               "binary_archives_unchanged": True, "runtime_verified": False,
               "previous_sha256": sha256(old), "installed_sha256": sha256(target), "backup": None}
    if old != target:
        backup_dir = output_dir / "backups"
        backup_dir.mkdir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backup_dir / (timestamp + "-" + CONFIG_NAME)
        with backup.open("xb") as stream:
            stream.write(old)
            stream.flush()
            os.fsync(stream.fileno())
        require(backup.read_bytes() == old, "Backup readback failed")
        receipt["backup"] = str(backup)
        descriptor, temporary = tempfile.mkstemp(prefix=".scuba-colors-", suffix=".tmp", dir=install_dir)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(target)
                stream.flush()
                os.fsync(stream.fileno())
            require(read_owned_file(install_dir, CONFIG_NAME) == old, "Installed configuration changed during update")
            os.replace(temporary, install_dir / CONFIG_NAME)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    require(read_owned_file(install_dir, CONFIG_NAME) == target, "Installed configuration readback failed")
    for name in BINARY_NAMES:
        require(read_owned_file(install_dir, name) == contents[name], f"Installed binary changed: {name}")
    write_json(output_dir / "installation-receipt.json", receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", required=True, type=Path, help="Verified 1.1.1 CNS_Mod directory containing files/ and package-manifest.json")
    parser.add_argument("--output-dir", required=True, type=Path, help="New/empty package directory outside source, base and game directories")
    parser.add_argument("--install-dir", type=Path, help="Optional existing CodexScubaMask mod folder; replace only its JSON after verification")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    base_dir, output_dir = args.base_dir.resolve(), args.output_dir.resolve()
    install_dir = args.install_dir.resolve() if args.install_dir else None
    disjoint(output_dir, repo, "Output must not overlap the source repository")
    disjoint(output_dir, base_dir, "Output must not overlap the base package")
    require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())), "Output directory must be new or empty")
    base_manifest, contents = baseline(base_dir)
    colors = validate_config(repo, base_dir)
    target = (repo / "cns" / CONFIG_NAME).read_bytes()
    if install_dir:
        disjoint(install_dir, repo, "Install directory must not overlap source")
        disjoint(install_dir, base_dir, "Install directory must not overlap base package")
        install_preflight(install_dir, output_dir, contents, target)

    readme = """Full Face Scuba Mask - CNS 1.1.2 (visor colors)

Requires Stellar Blade, Custom Nanosuit System 2.2 and its UE4SS requirements.
With the game closed, copy this archive's SB folder into the StellarBlade game
directory. The four mod files belong in:
SB/Content/Paks/~mods/CustomNanosuitSystem/Cosmetics/CodexScubaMask/
Remove duplicate older copies installed elsewhere.

For an existing 1.1.1 installation, only CodexCNS-ScubaMask.dekcns.json changes.
The PAK/UCAS/UTOC archives are byte-identical to the verified 1.1.1 baseline.
Restart the game once after updating so CNS reloads its configuration.

Equip vanilla glasses to initialize Eve's Eyes component. Open CNS (Alt+N),
choose Eve > glasses/Eyes > Full Face Scuba Mask, then use the variant arrows:
Clear, Smoke, Blue, Cyan, Green, Amber, Red, Purple.

The item cog still provides Inner Nasal Cup On/Off, Visor Opacity and Cup
Opacity. Default opacity remains 10% visor and 20% cup, adjustable from 0-100%.
Existing saved controls and UniqueFitID are preserved. No reset is required.
Color changes affect visor material section 8 (including the lower faceplate);
the frame and nasal cup keep their existing colors. At low opacity, tint can
be subtle and depends on game lighting. Clear retains the original neutral tint.

Validation: JSON structure, original controls, native material parameter names,
binary hashes and ZIP content checked. Live CNS selection, tint appearance,
opacity interactions and persistence still require in-game verification.
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    files_dir = output_dir / "files"
    files_dir.mkdir()
    packaged = dict(contents)
    packaged[CONFIG_NAME] = target
    for name, data in packaged.items():
        with (files_dir / name).open("xb") as stream:
            stream.write(data)
    (output_dir / "README.txt").write_text(readme, encoding="utf-8", newline="\n")
    archive = output_dir / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr("README.txt", readme.encode("utf-8"))
        for name, data in packaged.items():
            bundle.writestr(INSTALL_PREFIX + "/" + name, data)
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None, "ZIP CRC check failed")
        expected = {"README.txt", *(INSTALL_PREFIX + "/" + name for name in FILE_NAMES)}
        require(len(bundle.namelist()) == len(expected) and set(bundle.namelist()) == expected, "ZIP contains unexpected paths")
        for name, data in packaged.items():
            require(bundle.read(INSTALL_PREFIX + "/" + name) == data, f"ZIP readback failed: {name}")
            require((files_dir / name).read_bytes() == data, f"Package readback failed: {name}")
    manifest = {"version": VERSION, "feature": "Eight CNS visor color variants",
                "geometry_version": base_manifest.get("geometry_version", "1.1.0"),
                "base_version": "1.1.1", "base_manifest_sha256": sha256((base_dir / "package-manifest.json").read_bytes()),
                "binary_archives_unchanged": True,
                "files": [{"name": name, "bytes": len(packaged[name]), "sha256": sha256(packaged[name])} for name in FILE_NAMES],
                "archive": ARCHIVE_NAME, "archive_sha256": sha256(archive.read_bytes()),
                "archive_audit_passed": True, "native_material_contract_checked": True,
                "original_user_configs_preserved": True, "unique_fit_id_preserved": True,
                "variant_count": len(VARIANT_NAMES), "variants": dict(zip(VARIANT_NAMES, colors)),
                "runtime_verified": False, "published_to_nexus": False}
    write_json(output_dir / "package-manifest.json", manifest)
    if install_dir:
        install_json(install_dir, output_dir, contents, target)
    print(json.dumps({"package_directory": str(output_dir), "archive": str(archive),
                      "archive_sha256": manifest["archive_sha256"], "installed_json": bool(install_dir),
                      "runtime_verified": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
