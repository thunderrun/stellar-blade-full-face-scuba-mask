"""Export and check the mask and declared variants with Blender's bundled Python.

blender --background --python scripts/export_mask.py
blender --background --python scripts/export_mask.py -- --validate-only
"""
import argparse
import hashlib
import json
import math
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree


REPO = Path(__file__).resolve().parents[1]
MESH_NAME = "SK_CodexScubaMask"
EXPECTED_ALPHA = {"M_Scuba_NasalCup": 0.20, "M_Scuba_Visor": 0.10}
CNS_CONFIG = REPO / "cns/CodexCNS-ScubaMask.dekcns.json"
SIDE_SLOTS = ["M_GasMask_FilterBody", "M_GasMask_FilterAccent",
              "M_GasMask_SideValveBody", "M_GasMask_SideValveAccent"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_raw_source_privacy(path):
    """Empty Blender strings may still serialize old bytes after their first NUL."""
    data = path.read_bytes()
    texts = [data.decode("latin1")]
    for encoding in ("utf-16le", "utf-16be"):
        for offset in (0, 1):
            aligned = data[offset:offset + ((len(data) - offset) // 2) * 2]
            texts.append(aligned.decode(encoding, errors="ignore"))
    # Match local user/workspace tails even when their drive letter was cleared.
    pattern = re.compile(
        r"[\\/](?:Users|Documents and Settings|home)[\\/]"
        r"|[\\/]Documents[\\/]Codex[\\/]\d{4}-\d{2}-\d{2}[\\/]",
        re.IGNORECASE)
    matches = sum(len(pattern.findall(text)) for text in texts)
    require(matches == 0, "Public source retains local user/workspace path bytes: "
            + str(matches) + " matches across ASCII and UTF-16 scans")
    return matches


def validate_weak_library_references():
    """Appended datablocks can retain donor paths without any linked library."""
    for prop in bpy.data.bl_rna.properties:
        if prop.type != "COLLECTION":
            continue
        for block in getattr(bpy.data, prop.identifier):
            if not isinstance(block, bpy.types.ID):
                continue
            reference = getattr(block, "library_weak_reference", None)
            if reference is not None:
                require(not reference.filepath and not reference.id_name,
                        "Public source retains weak library metadata on " + prop.identifier + ": " + block.name)


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data)
    require(magic == 0x46546C67 and version == 2 and length == len(data), "Invalid GLB")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    require(json_type == 0x4E4F534A, "Missing GLB JSON chunk")
    return json.loads(data[20:20 + json_length])


def nearest_errors(source, target):
    tree = KDTree(len(source))
    for index, point in enumerate(source):
        tree.insert(point, index)
    tree.balance()
    return [tree.find(point)[2] for point in target]


def default_visible_count(manifest, counts):
    hidden = list(manifest.get("side_filter_material_indices", []))
    hidden += list(manifest.get("side_valve_material_indices", []))
    if "hood_toggle_material_index" in manifest:
        hidden.append(manifest["hood_toggle_material_index"])
    return sum(counts.values()) - sum(counts[manifest["material_slots"][i]] for i in hidden)


def section_signatures(mesh):
    """Exact oriented corner geometry, normals, UVs and weights, independent of vertex IDs."""
    mesh.data.calc_loop_triangles()
    triangles = defaultdict(list)
    normals = mesh.data.corner_normals
    uv_layers = list(mesh.data.uv_layers)
    for tri in mesh.data.loop_triangles:
        corners = []
        for loop_index in tri.loops:
            vertex = mesh.data.vertices[mesh.data.loops[loop_index].vertex_index]
            weights = sorted((mesh.vertex_groups[g.group].name, g.weight) for g in vertex.groups)
            values = list(vertex.co) + list(normals[loop_index].vector)
            for layer in uv_layers:
                values.extend(layer.data[loop_index].uv)
            corners.append(struct.pack("<" + "f" * len(values), *values)
                           + json.dumps(weights, separators=(",", ":")).encode())
        triangles[tri.material_index].append(min(b"".join(corners[i:] + corners[:i]) for i in range(3)))
    return {index: hashlib.sha256(b"".join(sorted(items))).hexdigest()
            for index, items in triangles.items()}


def validate_side_toggles(mesh, manifest, counts):
    if "side_filter_material_indices" not in manifest:
        require("side_valve_material_indices" not in manifest, "Incomplete side component contract")
        return {}
    valve_indices = manifest.get("side_valve_material_indices", [])
    legacy_side_valves = bool(valve_indices)
    require(manifest["side_filter_material_indices"] == [12, 13]
            and (not legacy_side_valves or valve_indices == [14, 15]), "Side component slots changed")
    if manifest.get("revision", 0) >= 16:
        require(not legacy_side_valves, "Upper exterior side valves are removed from revision 16 onward")
    expected_slots = SIDE_SLOTS if legacy_side_valves else SIDE_SLOTS[:2]
    require(len(mesh.data.materials) == 12 + len(expected_slots)
            and [m.name for m in mesh.data.materials][12:] == expected_slots,
            "Side component material contract differs")
    config = json.loads(CNS_CONFIG.read_text(encoding="utf-8-sig"))
    rows = config[0]["UserConfigs"]["MaterialToggles"]
    require(len(rows) == 6 + len(expected_slots), "Unexpected optional side toggle rows")
    groups = [(6, "Side Filters")]
    if legacy_side_valves:
        groups.append((8, "Side Valves"))
    for offset, name in groups:
        pair = rows[offset:offset + 2]
        expected_indices = [12, 13] if offset == 6 else [14, 15]
        require([r["MaterialIndex"] for r in pair] == expected_indices
                and all(r["Value"] is False for r in pair), "Side controls must default Off")
        require(pair[0]["DisplayName"] == name and "ControlledBy" not in pair[0]
                and pair[1].get("ControlledBy") == name, "Side controls need one controller per pair")
    return {"filter_material_indices": [12, 13], "side_valve_material_indices": valve_indices,
            "filter_triangles": sum(counts[n] for n in SIDE_SLOTS[:2]),
            "side_valve_triangles": sum(counts.get(n, 0) for n in SIDE_SLOTS[2:]),
            "cns_default_side_filters_visible": False,
            "side_valve_control_present": legacy_side_valves,
            "upper_exterior_side_valves_absent": not legacy_side_valves}


def validate_cup_toggle(mesh, manifest, counts):
    """Check that the toggle hides only the cup and leaves a closed outer visor."""
    if "cup_toggle_material_index" not in manifest:
        return {}
    cup = manifest["cup_toggle_material_index"]
    visor = manifest["always_visible_visor_material_index"]
    require(cup == 7 and visor == 8, "CNS expects cup section 7 and visor section 8")
    require(mesh.data.materials[cup].name == "M_Scuba_NasalCup"
            and mesh.data.materials[visor].name == "M_Scuba_Visor", "Toggle slot names changed")
    require(counts == manifest["material_triangle_counts"], "Update section counts after geometry edits")
    edge_counts = Counter()
    for polygon in mesh.data.polygons:
        if polygon.material_index == visor:
            edge_counts.update(tuple(sorted(edge)) for edge in polygon.edge_keys)
    require(edge_counts and all(count == 2 for count in edge_counts.values()),
            "The always-visible outer visor must have no open or nonmanifold edges")
    adjacency = defaultdict(set)
    for a, b in edge_counts:
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(adjacency)
    components = 0
    while unseen:
        components += 1
        queue = [unseen.pop()]
        while queue:
            for vertex in adjacency[queue.pop()]:
                if vertex in unseen:
                    unseen.remove(vertex)
                    queue.append(vertex)
    require(components == 1, "The always-visible visor must be connected")
    config = json.loads(CNS_CONFIG.read_text(encoding="utf-8-sig"))
    toggles = config[0]["UserConfigs"]["MaterialToggles"]
    require(toggles[0]["MaterialIndex"] == cup and "ControlledBy" not in toggles[0]
            and toggles[0]["Value"] is True, "CNS cup toggle binding/default differs")
    return {"cup_material_index": cup, "always_visible_visor_material_index": visor,
            "cup_triangles": counts["M_Scuba_NasalCup"],
            "always_visible_visor_triangles": counts["M_Scuba_Visor"],
            "cup_off_visible_triangles": default_visible_count(manifest, counts) - counts["M_Scuba_NasalCup"],
            "visibility_scope": "Hood and optional side components Off (default)",
            "outer_visor_connected_components": components,
            "outer_visor_boundary_edges": 0, "outer_visor_nonmanifold_edges": 0,
            "cns_default_cup_visible": True}


def validate_valve_toggle(mesh, manifest, counts):
    """Verify all linked valve sections while preserving the frame and cup."""
    indices = manifest.get("valve_toggle_material_indices")
    if indices is None:
        return {}
    require(indices == [1, 4, 9, 10], "Unexpected valve section mapping")
    expected = {1: ("M_Scuba_Polymer", 2172), 4: ("M_Scuba_Steel", 992),
                9: ("M_Scuba_ValveAccent", 1200), 10: ("M_Scuba_ValveVent", 702)}
    for index, (name, triangles) in expected.items():
        require(mesh.data.materials[index].name == name and counts[name] == triangles,
                "Valve section identity or triangle count differs")
    require(counts["M_Scuba_TealAccent"] == 2204 and counts["M_Scuba_Vent"] == 2204,
            "The independent outer trim and retention gasket must remain visible")
    for p in mesh.data.polygons:
        if p.material_index in indices:
            for i in p.vertices:
                v = mesh.matrix_world @ mesh.data.vertices[i].co
                require(-11.2 < v.x < -9.5 and abs(v.y) < 1.3 and -.6 < v.z < 1.8,
                        "A valve toggle section contains geometry outside the chin valve")
    config = json.loads(CNS_CONFIG.read_text(encoding="utf-8-sig"))
    toggles = config[0]["UserConfigs"]["MaterialToggles"]
    expected_rows = (6 if "hood_toggle_material_index" in manifest else 5)
    expected_rows += len(manifest.get("side_filter_material_indices", []))
    expected_rows += len(manifest.get("side_valve_material_indices", []))
    require(len(toggles) == expected_rows,
            "Unexpected cup, valve and optional hood toggle rows")
    rows = toggles[1:5]
    require([row["MaterialIndex"] for row in rows] == indices
            and all(row["Value"] is True for row in rows), "Valve binding/default differs")
    require(rows[0]["DisplayName"] == "Valve" and "ControlledBy" not in rows[0]
            and all(row.get("ControlledBy") == "Valve" for row in rows[1:]),
            "Valve sections must have one visible controller")
    total = default_visible_count(manifest, counts)
    if manifest["mesh_name"] == MESH_NAME:
        require(total == 48394, "Original mask geometry count changed")
    hidden = sum(counts[expected[i][0]] for i in indices)
    require(hidden == manifest["valve_triangle_count"] == 5066, "Valve triangle count differs")
    require(total - hidden == manifest["valve_off_visible_triangles"],
            "Valve Off visible geometry differs")
    require(total - hidden - counts["M_Scuba_NasalCup"]
            == manifest["cup_and_valve_off_visible_triangles"] == 26380,
            "Combined cup and valve Off visible geometry differs")
    return {"material_indices": indices, "valve_triangles": hidden,
            "valve_off_visible_triangles": total - hidden,
            "cup_and_valve_off_visible_triangles": total - hidden - counts["M_Scuba_NasalCup"],
            "visibility_scope": "Hood and optional side components Off (default)",
            "frame_trim_and_gasket_remain_visible": True,
            "existing_cup_and_visor_indices_preserved": True,
            "cns_visible_controller": "Valve", "cns_default_valve_visible": True}


def validate_hood_toggle(mesh, manifest, counts):
    """Check the appended hood section and all independent toggle combinations."""
    if "hood_toggle_material_index" not in manifest:
        return {}
    require(manifest["hood_toggle_material_index"] == 11 and len(mesh.data.materials) in (12, 14, 16)
            and mesh.data.materials[11].name == "M_Scuba_LatexHood", "Hood slot contract differs")
    baseline = {"M_Scuba_Silicone": 8080, "M_Scuba_Polymer": 2172, "M_Scuba_Teal": 882,
                "M_Scuba_TealAccent": 2204, "M_Scuba_Steel": 992, "M_Scuba_Vent": 2204,
                "M_Scuba_RubberDetail": 1560, "M_Scuba_NasalCup": 16948, "M_Scuba_Visor": 11450,
                "M_Scuba_ValveAccent": 1200, "M_Scuba_ValveVent": 702}
    if manifest["mesh_name"] == "SK_CodexGasMask":
        del baseline["M_Scuba_NasalCup"]
        require(counts["M_Scuba_NasalCup"] > 0, "Large cup section must contain geometry")
    require({name: counts[name] for name in baseline} == baseline,
            "An original mask section triangle count changed")
    hood_count = counts["M_Scuba_LatexHood"]
    require(hood_count == manifest["hood_triangle_count"] == 49404, "Hood triangle count differs")
    config = json.loads(CNS_CONFIG.read_text(encoding="utf-8-sig"))
    toggles = config[0]["UserConfigs"]["MaterialToggles"]
    row = toggles[5]
    require(row["DisplayName"] == "Hood" and row["MaterialIndex"] == 11
            and row["Value"] is False and "ControlledBy" not in row,
            "Hood must be independently controlled and default Off")
    edge_counts = Counter()
    hood_polygons = [p for p in mesh.data.polygons if p.material_index == 11]
    for p in hood_polygons:
        require(len(p.vertices) == 3, "Hood must be triangulated")
        a, b, c = (mesh.data.vertices[i].co for i in p.vertices)
        require((b - a).cross(c - a).length_squared > 1e-14, "Degenerate hood triangle")
        edge_counts.update(tuple(sorted(edge)) for edge in p.edge_keys)
    require(edge_counts and all(count == 2 for count in edge_counts.values()),
            "Thin hood shell must have closed face and neck edge walls")
    total = default_visible_count(manifest, counts)
    visible = {}
    for hood in (False, True):
        for cup in (False, True):
            for valve in (False, True):
                key = "hood_{}_cup_{}_valve_{}".format(int(hood), int(cup), int(valve))
                visible[key] = total + (hood_count if hood else 0) - (0 if cup else counts["M_Scuba_NasalCup"]) - (0 if valve else 5066)
    require(visible["hood_0_cup_1_valve_1"] == manifest["hood_off_visible_triangles"]
            == manifest["default_visible_triangles"], "Default visible mask count differs")
    side_count = sum(counts.get(name, 0) for name in SIDE_SLOTS)
    require(visible["hood_1_cup_1_valve_1"] == sum(counts.values()) - side_count,
            "Combined hood and mask count differs")
    return {"material_index": 11, "hood_triangles": hood_count,
            "cns_visible_controller": "Hood", "cns_default_hood_visible": False,
            "hood_off_visible_triangles": total, "all_sections_visible_triangles": sum(counts.values()),
            "toggle_combination_scope": "Optional side components Off",
            "hood_boundary_edges": 0, "hood_nonmanifold_edges": 0,
            "toggle_combination_visible_triangles": visible}


def export_public_fbx(filepath):
    # Blender's FBX writer includes the absolute .blend filename as metadata.
    # Replace only that field before serialization; mesh/rig data are untouched.
    # Use the installed Blender addon API; no addon source is vendored here.
    from io_scene_fbx import encode_bin
    original_write = encode_bin.write

    def public_write(filename, root, version):
        replaced = 0

        def scrub(element):
            nonlocal replaced
            if (element.id == b"P" and element.props
                    and element.props[0].endswith(b"Original|ApplicationNativeFile")):
                clean = encode_bin.FBXElem(b"P")
                clean.add_string(b"full_face_mask.blend")
                element.props[-1] = clean.props[0]
                replaced += 1
            for child in element.elems:
                scrub(child)

        scrub(root)
        require(replaced == 1, "FBX metadata layout changed; review the privacy scrub")
        return original_write(filename, root, version)

    encode_bin.write = public_write
    try:
        bpy.ops.export_scene.fbx(
            filepath=str(filepath), use_selection=True, object_types={"MESH", "ARMATURE"},
            global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
            axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True,
            mesh_smooth_type="FACE", add_leaf_bones=False, primary_bone_axis="Y",
            secondary_bone_axis="X", use_armature_deform_only=True, bake_anim=False)
    finally:
        encode_bin.write = original_write


def export_one(args, manifest_path, report_name):
    source = args.source.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    mesh_name = manifest.get("mesh_name", MESH_NAME)
    require(Path(mesh_name).name == mesh_name and "/" not in mesh_name and "\\" not in mesh_name,
            "Mesh name must be a basename")
    fbx = output / (mesh_name + ".fbx")
    glb = output / (mesh_name + ".glb")
    require(Path(manifest["fbx_path"]).name == fbx.name, "FBX name differs from manifest")

    raw_private_path_matches = validate_raw_source_privacy(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    require(not bpy.data.images and not bpy.data.libraries and not bpy.data.texts,
            "Public source must not contain images, linked libraries or text blocks")
    validate_weak_library_references()
    require(all(obj.type in {"MESH", "ARMATURE"} for obj in bpy.data.objects),
            "Unexpected non-mask object type")
    rig = bpy.data.objects["Armature"]
    mesh = bpy.data.objects[mesh_name]
    require([bone.name for bone in rig.data.bones] == ["Root"], "Expected one Root bone")
    require(abs(bpy.context.scene.unit_settings.scale_length - 0.01) < 1e-7,
            "Source coordinates must use centimetres")
    slots = [material.name for material in mesh.data.materials]
    require(slots == manifest["material_slots"], "Material order differs from manifest")
    mesh.data.calc_loop_triangles()
    triangle_count = len(mesh.data.loop_triangles)
    require(triangle_count == manifest["triangle_count"], "Update the manifest after geometry edits")
    material_counts = {name: 0 for name in slots}
    for triangle in mesh.data.loop_triangles:
        material_counts[slots[triangle.material_index]] += 1
    require(all(material_counts.values()), "Every material section must contain geometry")
    toggle_checks = validate_cup_toggle(mesh, manifest, material_counts)
    valve_checks = validate_valve_toggle(mesh, manifest, material_counts)
    hood_checks = validate_hood_toggle(mesh, manifest, material_counts)
    side_checks = validate_side_toggles(mesh, manifest, material_counts)
    coords = [mesh.matrix_world @ vertex.co for vertex in mesh.data.vertices]
    require(all(math.isfinite(value) for point in coords for value in point), "Nonfinite source vertex")
    source_section_vertices = defaultdict(set)
    for tri in mesh.data.loop_triangles:
        source_section_vertices[tri.material_index].update(tri.vertices)
    source_sections = {i: [coords[v] for v in vertices] for i, vertices in source_section_vertices.items()}
    source_weighted = all(len(v.groups) == 1 and abs(v.groups[0].weight - 1) < 1e-6
                          and mesh.vertex_groups[v.groups[0].group].name == "Root" for v in mesh.data.vertices)
    require(source_weighted, "Every source vertex must have rigid Root weight 1.0")
    root = rig.matrix_world @ rig.data.bones["Root"].matrix_local
    mesh_count = len([obj for obj in bpy.data.objects if obj.type == "MESH"])
    for name, alpha in EXPECTED_ALPHA.items():
        node = next(node for node in bpy.data.materials[name].node_tree.nodes
                    if node.type == "BSDF_PRINCIPLED")
        require(abs(node.inputs["Alpha"].default_value - alpha) < 1e-6,
                "Incorrect preview opacity for " + name)

    if not args.validate_only:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in (mesh, rig):
            obj.hide_set(False)
            obj.hide_viewport = False
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        export_public_fbx(fbx)
        # glTF uses metres. Keep FBX/source centimetres and restore after exporting.
        old_scale = rig.scale.copy()
        try:
            rig.scale = (0.01, 0.01, 0.01)
            bpy.context.view_layer.update()
            bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB",
                                      use_selection=True, export_apply=False)
        finally:
            rig.scale = old_scale
        # No save: the editable source and its hidden export collection stay intact.

    gltf = read_glb(glb)
    require(not gltf.get("images") and not gltf.get("textures"), "Unexpected GLB images/textures")
    require(all("uri" not in buffer for buffer in gltf.get("buffers", [])), "External GLB buffer")
    arm_node = next(node for node in gltf["nodes"] if node.get("name") == "Armature")
    require(all(abs(value - 0.01) < 1e-6 for value in arm_node["scale"]), "GLB is not metre-scaled")
    alphas = {material["name"]: material.get("pbrMetallicRoughness", {}).get(
        "baseColorFactor", [1, 1, 1, 1])[3] for material in gltf["materials"]}
    require(all(abs(alphas[name] - alpha) < 1e-6 for name, alpha in EXPECTED_ALPHA.items()),
            "GLB opacity differs from requested values")
    require(len(gltf["meshes"]) == 1 and len(gltf["meshes"][0]["primitives"]) == len(slots),
            "GLB section count differs from source")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False,
                             use_prepost_rot=True, ignore_leaf_bones=False)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    require(len(meshes) == 1 and len(arms) == 1, "FBX must contain exactly one mesh and armature")
    imported, arm = meshes[0], arms[0]
    require([bone.name for bone in arm.data.bones] == ["Root"], "FBX has unexpected bones")
    require([material.name for material in imported.data.materials] == slots, "FBX material order changed")
    imported.data.calc_loop_triangles()
    require(len(imported.data.loop_triangles) == triangle_count, "FBX triangle count changed")
    weighted = all(len(vertex.groups) == 1 and abs(vertex.groups[0].weight - 1) < 1e-6
                   and imported.vertex_groups[vertex.groups[0].group].name == "Root"
                   for vertex in imported.data.vertices)
    require(weighted, "Every FBX vertex must have rigid Root weight 1.0")
    imported_coords = [imported.matrix_world @ vertex.co for vertex in imported.data.vertices]
    require(all(math.isfinite(value) for point in imported_coords for value in point), "Nonfinite FBX vertex")
    imported_section_vertices = defaultdict(set)
    imported_counts = Counter()
    for tri in imported.data.loop_triangles:
        imported_section_vertices[tri.material_index].update(tri.vertices)
        imported_counts[slots[tri.material_index]] += 1
    require(dict(imported_counts) == material_counts, "FBX section triangle counts changed")
    section_errors = {}
    for index, source_points in source_sections.items():
        target_points = [imported_coords[v] for v in imported_section_vertices[index]]
        section_errors[slots[index]] = max(nearest_errors(source_points, target_points)
                                           + nearest_errors(target_points, source_points)) * 10
    require(all(value < 0.01 for value in section_errors.values()), "FBX section geometry or material assignments changed")
    error_mm = max(nearest_errors(coords, imported_coords) + nearest_errors(imported_coords, coords)) * 10
    imported_root = arm.matrix_world @ arm.data.bones["Root"].matrix_local
    rotation_error = math.degrees(root.to_quaternion().rotation_difference(imported_root.to_quaternion()).angle)
    position_error = (root.translation - imported_root.translation).length * 10
    require(error_mm < 0.01 and rotation_error < 0.001 and position_error < 0.001,
            "FBX geometry or Root reference pose changed")
    report = {
        "passed": True, "revision": manifest["revision"], "version": manifest.get("version"),
        "blender_version": bpy.app.version_string,
        "source": source.name, "fbx": fbx.name, "glb": glb.name,
        "mesh_name": mesh_name,
        "source_sha256": sha256(source), "fbx_sha256": sha256(fbx), "glb_sha256": sha256(glb),
        "source_mesh_objects": mesh_count, "source_images": 0, "source_linked_libraries": 0,
        "source_text_blocks": 0, "export_meshes": 1, "bones": ["Root"],
        "source_nonempty_weak_library_references": 0,
        "source_raw_private_path_match_count": raw_private_path_matches,
        "all_vertices_rigid_weight_Root": weighted, "triangles": triangle_count,
        "source_vertices": len(coords), "fbx_imported_vertices": len(imported_coords),
        "material_triangle_counts": material_counts, "glb_alpha": alphas,
        "cup_toggle": toggle_checks,
        "valve_toggle": valve_checks,
        "hood_toggle": hood_checks,
        "side_components": side_checks,
        "maximum_fbx_section_vertex_error_mm": section_errors,
        "maximum_fbx_vertex_error_mm": error_mm,
        "Root_rest_rotation_error_degrees": rotation_error,
        "Root_rest_position_error_mm": position_error,
        "bounding_box_cm": [[min(v[i] for v in imported_coords) for i in range(3)],
                            [max(v[i] for v in imported_coords) for i in range(3)]],
    }
    (output / report_name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if output == manifest_path.parent.resolve():
        manifest["fbx_sha256"] = report["fbx_sha256"]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))


def main():
    global CNS_CONFIG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO / "assets/full_face_mask.blend")
    parser.add_argument("--output-dir", type=Path, default=REPO / "assets")
    parser.add_argument("--manifest", type=Path, default=REPO / "assets/asset_manifest.json")
    parser.add_argument("--cns-config", type=Path, default=CNS_CONFIG)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    CNS_CONFIG = args.cns_config.resolve()
    first_path = args.manifest.resolve()
    first = json.loads(first_path.read_text(encoding="utf-8-sig"))
    jobs = [(first_path, "export_validation.json")]
    for variant in first.get("additional_variants", []):
        path = (first_path.parent / variant["manifest"]).resolve()
        require(path.parent == first_path.parent, "Variant manifest must share the source manifest directory")
        report_name = variant["report"]
        require(Path(report_name).name == report_name and "/" not in report_name and "\\" not in report_name,
                "Variant report must be a basename")
        jobs.append((path, report_name))
    require(len({path for path, _ in jobs}) == len(jobs)
            and len({report for _, report in jobs}) == len(jobs), "Duplicate variant manifest/report")
    manifests = [json.loads(path.read_text(encoding="utf-8-sig")) for path, _ in jobs]
    names = [m["mesh_name"] for m in manifests]
    require(len(set(names)) == len(names), "Duplicate optimized mesh name")
    if len(jobs) > 1:
        require(names == [MESH_NAME, "SK_CodexGasMask"], "Expected original cup first and large cup second")
        require(all(not m.get("additional_variants") for m in manifests[1:]), "Nested variant manifests are unsupported")
        config = json.loads(CNS_CONFIG.read_text(encoding="utf-8-sig"))[0]
        expected_paths = ["/Game/OutfitMods/CodexScubaMask/Models/{0}.{0}".format(name) for name in names]
        require(config["UniqueFitID"] == "Codex_FullFaceScubaMask_v1"
                and config["OutfitPaths"] == expected_paths and not config.get("OutfitDatas")
                and len(config.get("OutfitNames", [])) == len(jobs), "CNS mesh variant contract differs")
        bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
        original = bpy.data.objects[names[0]]
        original_sections = section_signatures(original)
        for manifest in manifests[1:]:
            other = bpy.data.objects[manifest["mesh_name"]]
            require(manifest["material_slots"] == first["material_slots"]
                    and manifest["skeleton_path"] == first["skeleton_path"], "Variant material/rig contract differs")
            require(other.matrix_world == original.matrix_world, "Variant object transform differs")
            require([m.name for m in other.data.materials] == [m.name for m in original.data.materials],
                    "Variant material definitions differ")
            sections = section_signatures(other)
            require(set(sections) == set(original_sections), "Variant section inventory differs")
            require(all(sections[i] == signature for i, signature in original_sections.items() if i != 7),
                    "Variant changes geometry, normals, UVs or weights outside cup section 7")
            require(sections[7] != original_sections[7], "Large cup variant must differ from the original cup")
    for manifest_path, report_name in jobs:
        export_one(args, manifest_path, report_name)


if __name__ == "__main__":
    main()
