"""UE4.26 editor commandlet. Generates assets in this isolated SB project only.

The FBX must contain one skeletal mesh, the vanilla glasses Root skeleton,
the fitted glasses-local transform, and no exporter-added leaf bones.
"""
import hashlib
import json
import os
import shutil
import struct
import traceback
from datetime import datetime
from pathlib import Path

import unreal

PROJECT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get("CODEX_SCUBA_MANIFEST", str(PROJECT / "manifest.json"))).resolve()
REPORT_PATH = PROJECT / "Saved" / "scuba-import-report.json"
ASSET_ROOT = "/Game/OutfitMods/CodexScubaMask"
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {"success": False, "manifest": str(MANIFEST), "warnings": []}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def set_prop(obj, name, value):
    # Required API properties fail explicitly instead of silently using defaults.
    obj.set_editor_property(name, value)


def path_of(obj):
    return obj.get_path_name() if obj is not None else None


def package_of(obj):
    return path_of(obj).split(".", 1)[0]


def save(obj):
    require(LIB.save_loaded_asset(obj, False), "Could not save " + path_of(obj))


def new_asset(name, folder, cls, factory):
    asset_path = folder + "/" + name
    existing = LIB.load_asset(asset_path) if LIB.does_asset_exist(asset_path) else None
    if existing:
        require(isinstance(existing, cls), "Existing asset has unexpected class: " + path_of(existing))
        return existing
    LIB.make_directory(folder)
    result = TOOLS.create_asset(name, folder, cls, factory)
    require(result is not None, "Could not create " + folder + "/" + name)
    return result


def material_texture(path):
    """Load stock editor texture or a nonshipping original-path placeholder."""
    flat_path = "/Game/Art/Character/Generic/GlobalTexture/Base_Flat_N.Base_Flat_N"
    if path == flat_path and not LIB.does_asset_exist(path):
        LIB.make_directory(flat_path.rsplit("/", 1)[0])
        texture = LIB.duplicate_asset("/Engine/EngineMaterials/DefaultNormal.DefaultNormal",
                                      flat_path.split(".", 1)[0])
        require(texture is not None, "Could not create excluded flat-normal placeholder")
        save(texture)
    texture = LIB.load_asset(path)
    require(isinstance(texture, unreal.Texture), "Texture reference missing: " + path)
    return texture


def make_dummy_parent(parent_spec, reference, materials):
    """Borrow the existing game's MI by path; this UMaterial MUST NOT SHIP."""
    path = parent_spec["path"]
    package = path.split(".", 1)[0]
    dummy = new_asset(package.rsplit("/", 1)[1], package.rsplit("/", 1)[0],
                      unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(dummy)
    set_prop(dummy, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT
             if parent_spec.get("translucent") else unreal.BlendMode.BLEND_OPAQUE)
    # Connected parameters make the editor retain overrides. The graph's visual
    # output is irrelevant: the game's original parent/shader replaces this dummy.
    nodes = []
    definitions = {"scalar_parameters": {}, "vector_parameters": {}, "texture_parameters": {}}
    for spec in materials:
        for group in definitions:
            definitions[group].update(spec.get(group, {}))
    for name in definitions["scalar_parameters"]:
        require(name in reference["scalars"], "Unverified game scalar: " + name)
        node = lib.create_material_expression(dummy, unreal.MaterialExpressionScalarParameter)
        set_prop(node, "parameter_name", name)
        set_prop(node, "default_value", float(reference["scalars"][name]))
        nodes.append(node)
    for name in definitions["vector_parameters"]:
        require(name in reference["vectors"], "Unverified game vector: " + name)
        node = lib.create_material_expression(dummy, unreal.MaterialExpressionVectorParameter)
        set_prop(node, "parameter_name", name)
        color = reference["vectors"][name]
        set_prop(node, "default_value", unreal.LinearColor(color["R"], color["G"], color["B"], color["A"]))
        nodes.append(node)
    for name, texture_path in definitions["texture_parameters"].items():
        require(name in reference["textures"], "Unverified game texture parameter: " + name)
        node = lib.create_material_expression(dummy, unreal.MaterialExpressionTextureSampleParameter2D)
        set_prop(node, "parameter_name", name)
        set_prop(node, "texture", material_texture(texture_path))
        set_prop(node, "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
                 if "Normal" in name else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        nodes.append(node)
    require(bool(nodes), "Dummy needs at least one verified dynamic parameter")
    combined = nodes[0]
    for node in nodes[1:]:
        add = lib.create_material_expression(dummy, unreal.MaterialExpressionAdd)
        require(lib.connect_material_expressions(combined, "", add, "A"), "Cannot connect dummy A")
        require(lib.connect_material_expressions(node, "", add, "B"), "Cannot connect dummy B")
        combined = add
    require(lib.connect_material_property(combined, "", unreal.MaterialProperty.MP_BASE_COLOR),
            "Cannot connect dummy parameters")
    lib.set_material_usage(dummy, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    lib.recompile_material(dummy)
    save(dummy)
    return dummy


def make_material_instance(spec, parent):
    factory = unreal.MaterialInstanceConstantFactoryNew()
    instance = new_asset(spec["asset_name"], ASSET_ROOT + "/Materials",
                         unreal.MaterialInstanceConstant, factory)
    lib = unreal.MaterialEditingLibrary
    lib.set_material_instance_parent(instance, parent)
    lib.clear_all_material_instance_parameters(instance)
    # No static parameters, blend/base-property overrides, or new shader graphs.
    # UE4.26's setter wrappers return false unconditionally (see installed
    # MaterialEditingLibrary.cpp), so validate actual readback instead.
    scalar_readback = {}
    for name, value in spec.get("scalar_parameters", {}).items():
        lib.set_material_instance_scalar_parameter_value(instance, name, float(value))
        actual = lib.get_material_instance_scalar_parameter_value(instance, name)
        scalar_readback[name] = actual
        # Native material scalars are float32. Match their exact representable
        # value, rather than treating the requested decimal as a Python float64.
        require(struct.pack("<f", actual) == struct.pack("<f", float(value)),
                "Scalar readback differs: " + name)
    for name, value in spec.get("vector_parameters", {}).items():
        lib.set_material_instance_vector_parameter_value(instance, name, unreal.LinearColor(*value))
        actual = lib.get_material_instance_vector_parameter_value(instance, name)
        require(max(abs(a - b) for a, b in zip([actual.r, actual.g, actual.b, actual.a], value)) < 1e-6,
                "Vector readback differs: " + name)
    for name, path in spec.get("texture_parameters", {}).items():
        lib.set_material_instance_texture_parameter_value(instance, name, material_texture(path))
        require(path_of(lib.get_material_instance_texture_parameter_value(instance, name)) == path,
                "Texture readback differs: " + name)
    lib.update_material_instance(instance)
    save(instance)
    REPORT.setdefault("native_scalar_readback", {})[path_of(instance)] = scalar_readback
    REPORT["scalar_readback_validation"] = "exact IEEE754 float32 bit equality to requested native value"
    return instance


def make_label(name, assets, chunk_id, priority):
    factory = unreal.DataAssetFactory()
    set_prop(factory, "data_asset_class", unreal.PrimaryAssetLabel)
    label = new_asset(name, ASSET_ROOT + "/Labels", unreal.PrimaryAssetLabel, factory)
    rules = unreal.PrimaryAssetRules()
    set_prop(rules, "priority", priority)
    set_prop(rules, "chunk_id", chunk_id)
    set_prop(rules, "apply_recursively", False)
    set_prop(rules, "cook_rule", unreal.PrimaryAssetCookRule.ALWAYS_COOK)
    set_prop(label, "rules", rules)
    set_prop(label, "explicit_assets", assets)
    set_prop(label, "label_assets_in_my_directory", False)
    set_prop(label, "is_runtime_label", False)
    save(label)
    return label


def main():
    config = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    engine = unreal.SystemLibrary.get_engine_version()
    require(engine.startswith(config["expected_engine"] + "."),
            "Expected stock UE4.26.x; actual engine: " + engine)
    actual_project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    require(Path(actual_project).resolve() == PROJECT,
            "Run this script only with its isolated SB.uproject")
    fbx = (MANIFEST.parent / config["fbx"]).resolve()
    require(fbx.is_file(), "Fitted FBX not found: " + str(fbx))
    mesh_package = config["mesh_package"]
    require(mesh_package.startswith(ASSET_ROOT + "/Models/"), "Mesh must remain in custom mod namespace")
    skeleton_path = config["original_skeleton"]
    expected_skeleton = "/Game/Art/Character/PC/00_ACC/ACC_GLA_03/ACC_GLA_03M_Skeleton.ACC_GLA_03M_Skeleton"
    require(skeleton_path == expected_skeleton, "Unexpected original glasses skeleton path")
    require(config["expected_bones"] == ["Root"], "This build targets the rigid vanilla glasses Root rig")
    require(0 < config["chunk_id"] < 2147483647, "Invalid custom chunk ID")
    materials = config["materials"]
    expected_material_count = config["expected_material_count"]
    require(len(materials) == expected_material_count
            and len({s["source_name"] for s in materials}) == expected_material_count,
            "Material slots differ from the revision's declared count")
    require(config.get("material_mode") == "game_material_instances",
            "Stellar Blade requires game-compatible MI children; custom UMaterial shaders are not supported here")
    reference_path = (MANIFEST.parent / config["material_reference"]).resolve()
    reference = json.loads(reference_path.read_text(encoding="utf-8-sig"))
    for key, parent_spec in config["material_parents"].items():
        require(parent_spec["path"] == reference[key]["asset"], "Unverified parent reference")
        require(not reference[key]["bHasStaticPermutationResource"]
                and not reference[key]["static_overrides"], "Choose a parent without a static override")
    source_manifest = (MANIFEST.parent / config["source_manifest"]).resolve()
    source = json.loads(source_manifest.read_text(encoding="utf-8-sig"))
    require(source["material_slots"] == [m["source_name"] for m in materials],
            "Final Blender export manifest material slots differ from importer manifest")
    require(source["skeleton_path"] == skeleton_path and source["bone"] == "Root"
            and source["units"] == "centimetres", "Final Blender export rig/units differ")
    # Both manifests use portable relative FBX paths.
    require(source["mesh_name"] == mesh_package.rsplit("/", 1)[1]
            and Path(source["fbx_path"]).name == fbx.name, "Final Blender export filename differs")
    REPORT.update(engine=engine, fbx=str(fbx), fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
                  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  source_manifest=str(source_manifest),
                  source_manifest_sha256=hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
                  material_reference=str(reference_path),
                  material_reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                  material_mode=config["material_mode"],
                  chunk_id=config["chunk_id"], expected_bones=config["expected_bones"])

    # Python commandlets do not wait for the editor's usual background asset scan.
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
        ["/Game", "/Engine/EngineMaterials", "/Engine/EngineResources"], True)
    existing_skeleton = LIB.load_asset(skeleton_path) if LIB.does_asset_exist(skeleton_path) else None
    if existing_skeleton:
        require(isinstance(existing_skeleton, unreal.Skeleton), "Dummy skeleton path is not a Skeleton")
    # UE4.26 reimport can retain the previous LOD section/material order even
    # with reorder_material_to_fbx_order enabled. Replace only our generated mesh
    # so the inner cup precedes the outer visor in translucent draw submission.
    if LIB.does_asset_exist(mesh_package):
        old_mesh = LIB.load_asset(mesh_package)
        require(isinstance(old_mesh, unreal.SkeletalMesh), "Generated mesh path has unexpected class")
        package_file = PROJECT / "Content" / (mesh_package[len("/Game/"):] + ".uasset")
        require(package_file.is_file(), "Cannot back up existing generated mesh package")
        backup = PROJECT / "Saved" / "MeshReplacementBackup" / datetime.now().strftime("%Y%m%d-%H%M%S")
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(package_file), str(backup / package_file.name))
        require(LIB.delete_loaded_asset(old_mesh), "Could not replace generated skeletal mesh")
        require(not LIB.does_asset_exist(mesh_package), "Old generated skeletal mesh still exists")
        REPORT["previous_generated_mesh_backup"] = str(backup / package_file.name)
    REPORT["mesh_import_mode"] = "fresh generated mesh; original-path dummy skeleton retained"
    options = unreal.FbxImportUI()
    settings = {
        "automated_import_should_detect_type": False, "import_mesh": True,
        "import_as_skeletal": True, "import_materials": False, "import_textures": False,
        "import_animations": False, "create_physics_asset": False, "override_full_name": True,
        "mesh_type_to_import": unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        "skeleton": existing_skeleton,
    }
    for name, value in settings.items():
        set_prop(options, name, value)
    skeletal = options.get_editor_property("skeletal_mesh_import_data")
    import_settings = {
        "import_uniform_scale": 1.0, "convert_scene": True, "convert_scene_unit": True,
        "force_front_x_axis": False, "update_skeleton_reference_pose": False,
        "use_t0_as_ref_pose": False, "preserve_smoothing_groups": True,
        "import_morph_targets": False, "import_mesh_lo_ds": False,
        "reorder_material_to_fbx_order": True,
        "normal_import_method": unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
    }
    for name, value in import_settings.items():
        set_prop(skeletal, name, value)
    REPORT["import_settings"] = {name: str(value) for name, value in import_settings.items()}
    REPORT["fbx_contract"] = "One weighted Root bone, no leaf bones, no armature wrapper bone, fitted vanilla glasses local coordinates"
    task = unreal.AssetImportTask()
    for name, value in {
        "filename": str(fbx), "destination_path": mesh_package.rsplit("/", 1)[0],
        "destination_name": mesh_package.rsplit("/", 1)[1], "automated": True,
        "replace_existing": True, "save": True, "options": options,
    }.items():
        set_prop(task, name, value)
    TOOLS.import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))
    REPORT["imported_paths"] = imported_paths
    mesh = LIB.load_asset(mesh_package)
    require(isinstance(mesh, unreal.SkeletalMesh), "No skeletal mesh at expected output path")
    require(sum(isinstance(LIB.load_asset(p), unreal.SkeletalMesh) for p in imported_paths) == 1,
            "FBX must import exactly one skeletal mesh")
    require(mesh.get_editor_property("physics_asset") is None, "Unexpected physics asset")
    probe = unreal.SkeletalMeshComponent()
    probe.set_skeletal_mesh(mesh, True)
    bones = [str(probe.get_bone_name(i)) for i in range(probe.get_num_bones())]
    require(bones == config["expected_bones"], "Imported FBX skeleton differs: " + repr(bones))
    root_position = probe.get_ref_pose_position(0)
    REPORT["imported_bones"] = bones
    REPORT["root_reference_position_cm"] = [root_position.x, root_position.y, root_position.z]
    skeleton = mesh.get_editor_property("skeleton")
    require(isinstance(skeleton, unreal.Skeleton), "Imported mesh has no skeleton")
    old_skeleton = package_of(skeleton)
    if path_of(skeleton) != skeleton_path:
        require(existing_skeleton is None, "Importer did not use the existing original-path dummy skeleton")
        LIB.make_directory(skeleton_path.split(".", 1)[0].rsplit("/", 1)[0])
        require(LIB.rename_loaded_asset(skeleton, skeleton_path.split(".", 1)[0]),
                "Could not rename imported skeleton to original game softpath")
    require(path_of(mesh.get_editor_property("skeleton")) == skeleton_path,
            "Mesh reference did not follow dummy skeleton rename")
    save(skeleton)
    save(mesh)

    specs = {m["source_name"]: m for m in materials}
    parents = {}
    for key, parent_spec in config["material_parents"].items():
        parent_materials = [spec for spec in materials if spec["parent_key"] == key]
        parents[key] = make_dummy_parent(parent_spec, reference[key], parent_materials)
    built = {name: make_material_instance(spec, parents[spec["parent_key"]]) for name, spec in specs.items()}
    slots = list(mesh.get_editor_property("materials"))
    require(len(slots) == len(materials), "Imported material-slot count differs from manifest")
    imported_order = [str(slot.get_editor_property("imported_material_slot_name")) for slot in slots]
    require(imported_order == [spec["source_name"] for spec in materials],
            "Imported material order differs from FBX contract: " + repr(imported_order))
    slot_report, seen = [], set()
    for slot in slots:
        source_name = str(slot.get_editor_property("imported_material_slot_name"))
        require(source_name in specs,
                "Unknown imported material name; do not guess slot order: " + source_name)
        require(source_name not in seen, "Duplicate imported material name " + source_name)
        seen.add(source_name)
        set_prop(slot, "material_interface", built[source_name])
        slot_report.append({"imported_name": source_name, "material": path_of(built[source_name]),
                            "class": built[source_name].get_class().get_name(),
                            "external_game_parent": path_of(parents[specs[source_name]["parent_key"]]),
                            "scalar_parameters": specs[source_name].get("scalar_parameters", {}),
                            "vector_parameters": specs[source_name].get("vector_parameters", {}),
                            "texture_parameters": specs[source_name].get("texture_parameters", {})})
    set_prop(mesh, "materials", slots)
    save(mesh)

    # A higher-priority explicit label isolates the dummy skeleton in chunk 0.
    # Only the custom chunk is a deliverable; never ship chunk 0 or global.utoc.
    excluded_assets = [skeleton] + list(parents.values())
    for texture_path in sorted({p for spec in materials for p in spec["texture_parameters"].values()}):
        excluded_assets.append(material_texture(texture_path))
    dummy_label = make_label("PAL_OriginalAssets_Chunk0", excluded_assets, 0, 100)
    assets = [mesh] + [built[spec["source_name"]] for spec in materials]
    label = make_label("PAL_CodexScubaMask", assets, config["chunk_id"], 1)
    require(all(package_of(a).startswith(ASSET_ROOT + "/") for a in assets),
            "Custom label contains an original game asset")
    REPORT.update(
        success=True, mesh=path_of(mesh), skeleton=path_of(skeleton),
        old_dummy_skeleton_package=old_skeleton, material_slots=slot_report,
        explicit_custom_assets=[path_of(a) for a in assets],
        excluded_original_assets=[path_of(a) for a in excluded_assets],
        custom_label=path_of(label), dummy_label=path_of(dummy_label),
        bone_validation="Imported mesh checked: Root only. Confirm cooked reference quaternion/bounds by re-export before release.",
        archive_validation="Required: mesh plus {} MaterialInstanceConstants only; no UMaterial/shader graphs, static overrides, dummy parents, dummy textures, original skeleton or other game assets.".format(expected_material_count),
    )
    unreal.log("SCUBA_IMPORT_SUCCESS " + path_of(mesh))


try:
    main()
except Exception as error:
    REPORT["error"] = str(error)
    REPORT["traceback"] = traceback.format_exc()
    unreal.log_error(REPORT["traceback"])
    raise
finally:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
