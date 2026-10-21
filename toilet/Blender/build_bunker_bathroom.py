# ============================================================================
#  BUNKER COMMUNAL BATHROOM  -  procedural, Unity-ready environment
#
#  Blender 4.2 - 5.x.   Scripting workspace > Open (or New + paste) > Run Script
#  Re-running is safe: everything inside the "BunkerBathroom" collection is
#  deleted and rebuilt.
#
#  Coordinate layout (Blender, Z up, 1 unit = 1 m):
#     interior  X: -4 .. 4  (width 8 m)    Y: 0 .. 11 (length 11 m)   Z: 0 .. 3.2
#     entrance  front wall (Y = 0), centred on X = 0, player walks toward +Y
#     stalls    left wall  (X = -4)
#     urinals   back wall  (Y = 11)
#     sink      right wall (X = +4)
# ============================================================================

import bpy
import bmesh
import json
import math
import os
import random
from mathutils import Euler, Matrix, Vector

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
# Where the FBX files are written. "" = folder of the saved .blend file.
EXPORT_DIR = "/home/asadbekxolbekov/bunker/toilet/Assets/BunkerBathroom/Models"
AUTO_EXPORT = True

ROOM_W, ROOM_L, ROOM_H = 8.0, 11.0, 3.2
WALL_T = 0.25
X0, X1 = -ROOM_W / 2, ROOM_W / 2
Y0, Y1 = 0.0, ROOM_L

DOOR_X = 0.0                 # centre of the entrance in the front wall
DOOR_OPEN_W = 1.2            # clear opening (leaf is ~1.16 m)
DOOR_OPEN_H = 2.3            # clear opening (leaf is ~2.27 m)
DOOR_OPEN_DEG = 0.0          # >0 swings the entrance leaf into the room

STALL_COUNT = 6
STALL_W = 1.0
STALL_D = 1.55
STALL_Y0 = 2.6
STALL_FRONT_X = X0 + STALL_D
STALL_DOOR_ANGLES = (10, 28, 4, 38, 16, 24)   # degrees, swung into the stall

SINK_COUNT = 5
SINK_PITCH = 1.04
SINK_Y0 = 3.3
SINK_Y1 = SINK_Y0 + SINK_COUNT * SINK_PITCH
SINK_FRONT_X = X1 - 0.55
SINK_TOP = 0.86

URINAL_X = (-1.0, 0.0, 1.0)

# (x, y, length) of ceiling fluorescent fixtures, long axis along Y
CEILING_LIGHTS = [(x, y, 1.25) for y in (1.8, 4.3, 6.8, 9.3) for x in (-1.6, 1.6)] + \
                 [(-3.2, 4.1, 1.0), (-3.2, 7.1, 1.0)]
LIGHT_COLOR = (0.86, 0.94, 1.0)     # cold fluorescent white

PLAYER_START = Vector((0.0, 1.0, 0.0))
CAMERA_HEIGHT = 1.65
CHARACTER_POS = Vector((0.9, 1.5, 0.0))

MASTER = "BunkerBathroom"
SHARP_ANGLE = math.radians(40)

# ----------------------------------------------------------------------------
# MATERIALS
# name: (linear base colour, roughness, metallic, noise scale, colour variation,
#        roughness variation, bump strength, darken near floor, emission)
# ----------------------------------------------------------------------------
MATERIAL_DEFS = {
    "Dark_Grey_Metal":       ((0.060, 0.065, 0.070), 0.55, 0.35, 6.0, 0.25, 0.10, 0.00, False, 0.0),
    "Worn_Grey_Metal":       ((0.170, 0.175, 0.180), 0.50, 0.60, 9.0, 0.25, 0.08, 0.02, False, 0.0),
    "Concrete":              ((0.200, 0.200, 0.190), 0.92, 0.00, 3.0, 0.35, 0.05, 0.15, True, 0.0),
    "Wall_Panel":            ((0.230, 0.235, 0.235), 0.65, 0.10, 4.0, 0.20, 0.10, 0.00, True, 0.0),
    "Floor_Tile":            ((0.120, 0.125, 0.130), 0.40, 0.00, 2.5, 0.25, 0.12, 0.02, False, 0.0),
    "Floor_Tile_Worn":       ((0.100, 0.103, 0.105), 0.50, 0.00, 2.5, 0.30, 0.12, 0.02, False, 0.0),
    "Grout":                 ((0.050, 0.050, 0.050), 0.95, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Stainless_Steel":       ((0.550, 0.550, 0.550), 0.32, 1.00, 40.0, 0.05, 0.04, 0.00, False, 0.0),
    "Industrial_Yellow":     ((0.450, 0.320, 0.050), 0.70, 0.00, 5.0, 0.30, 0.10, 0.00, False, 0.0),
    "White_Ceramic":         ((0.720, 0.720, 0.700), 0.22, 0.00, 6.0, 0.06, 0.05, 0.00, False, 0.0),
    "Glass":                 ((0.800, 0.820, 0.830), 0.05, 1.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Rubber":                ((0.020, 0.020, 0.020), 0.90, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Dark_Plastic":          ((0.025, 0.025, 0.028), 0.50, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Light_Emissive":        ((0.900, 0.950, 1.000), 0.50, 0.00, 0.0, 0.00, 0.00, 0.00, False, 6.0),
    "Drain_Void":            ((0.010, 0.010, 0.010), 0.90, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Sign_Paper":            ((0.600, 0.580, 0.480), 0.85, 0.00, 8.0, 0.20, 0.00, 0.00, False, 0.0),
    "Sign_Ink":              ((0.020, 0.020, 0.020), 0.60, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
    "Character_Placeholder": ((0.600, 0.250, 0.050), 0.60, 0.00, 0.0, 0.00, 0.00, 0.00, False, 0.0),
}
MATS = {}

COLL = {}       # collection key -> bpy collection
ROOTS = {}      # collection key -> parent empty


# ============================================================================
# GENERIC HELPERS
# ============================================================================
def T(v):
    return Matrix.Translation(Vector(v))


AXIS_ROT = {
    "Z": Matrix.Identity(4),
    "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
    "Y": Matrix.Rotation(-math.pi / 2, 4, "X"),
}


def set_input(node, names, value):
    if isinstance(names, str):
        names = (names,)
    for n in names:
        sock = node.inputs.get(n)
        if sock is not None:
            sock.default_value = value
            return sock
    return None


def create_material(name, color, roughness, metallic=0.0, noise_scale=0.0, color_var=0.0,
                    rough_var=0.0, bump=0.0, floor_grime=False, emission=0.0):
    """Principled material. The flat values (base colour / roughness / metallic) are set
    on the sockets so the FBX exporter and Unity pick them up; the procedural noise is
    a Blender-side preview of wear only."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    rgba = (*color, 1.0)

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (400, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_input(bsdf, "Base Color", rgba)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", metallic)
    if emission > 0:
        set_input(bsdf, ("Emission Color", "Emission"), rgba)
        set_input(bsdf, "Emission Strength", emission)

    mat.diffuse_color = rgba            # solid viewport colour
    mat.roughness = roughness
    mat.metallic = metallic

    if noise_scale > 0 and (color_var > 0 or rough_var > 0 or bump > 0):
        geo = nodes.new("ShaderNodeNewGeometry")
        geo.location = (-900, 0)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-700, 0)
        set_input(noise, "Scale", noise_scale)
        set_input(noise, "Detail", 6.0)
        set_input(noise, "Roughness", 0.6)
        links.new(geo.outputs["Position"], noise.inputs["Vector"])

        if color_var > 0:
            ramp = nodes.new("ShaderNodeValToRGB")
            ramp.location = (-450, 150)
            e0, e1 = ramp.color_ramp.elements
            e0.position, e1.position = 0.3, 0.7
            e0.color = (*[c * (1 - color_var) for c in color], 1)
            e1.color = (*[min(1.0, c * (1 + color_var * 0.5)) for c in color], 1)
            links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
            col_out = ramp.outputs["Color"]
            if floor_grime:
                sep = nodes.new("ShaderNodeSeparateXYZ")
                sep.location = (-450, 400)
                links.new(geo.outputs["Position"], sep.inputs[0])
                mr = nodes.new("ShaderNodeMapRange")
                mr.location = (-250, 400)
                set_input(mr, "From Min", 0.0)
                set_input(mr, "From Max", 0.6)
                set_input(mr, "To Min", 0.6)
                set_input(mr, "To Max", 1.0)
                links.new(sep.outputs[2], mr.inputs["Value"])
                mul = nodes.new("ShaderNodeVectorMath")
                mul.location = (100, 250)
                mul.operation = "MULTIPLY"
                links.new(col_out, mul.inputs[0])
                links.new(mr.outputs["Result"], mul.inputs[1])
                col_out = mul.outputs["Vector"]
            links.new(col_out, bsdf.inputs["Base Color"])

        if rough_var > 0:
            mr2 = nodes.new("ShaderNodeMapRange")
            mr2.location = (-450, -150)
            set_input(mr2, "From Min", 0.3)
            set_input(mr2, "From Max", 0.7)
            set_input(mr2, "To Min", max(0.0, roughness - rough_var))
            set_input(mr2, "To Max", min(1.0, roughness + rough_var))
            links.new(noise.outputs["Fac"], mr2.inputs["Value"])
            links.new(mr2.outputs["Result"], bsdf.inputs["Roughness"])

        if bump > 0:
            bn = nodes.new("ShaderNodeBump")
            bn.location = (100, -300)
            set_input(bn, "Strength", bump)
            set_input(bn, "Distance", 0.01)
            links.new(noise.outputs["Fac"], bn.inputs["Height"])
            links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def create_materials():
    for name, d in MATERIAL_DEFS.items():
        MATS[name] = create_material(name, *d)


# ---- text -------------------------------------------------------------------
_TEXT_CACHE = {}


def text_geometry(body, size, align="CENTER", extrude=0.0006):
    """Builds a font object, converts it to mesh data and returns (verts, faces) in
    text space: X = reading direction, Y = up, Z = out of the surface."""
    key = (body, size, align, extrude)
    if key in _TEXT_CACHE:
        return _TEXT_CACHE[key]
    cu = bpy.data.curves.new("tmp_text", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.resolution_u = 3
    ob = bpy.data.objects.new("tmp_text", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    verts = [v.co.copy() + Vector((0, 0, extrude)) for v in me.vertices]   # back face on Z = 0
    faces = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    _TEXT_CACHE[key] = (verts, faces)
    return verts, faces


# ---- mesh builder -----------------------------------------------------------
class MeshBuilder:
    """Accumulates boxes / cylinders / text into ONE mesh with several material
    slots, so each logical asset is a single object (few draw calls in Unity)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []
        self.groups = {}

    def _assign(self, verts, mat, group=None):
        if mat not in MATS:
            raise KeyError("Unknown material " + mat)
        if mat not in self.mats:
            self.mats.append(mat)
        idx = self.mats.index(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = idx
        if group:
            self.groups.setdefault(group, []).extend(verts)

    def box(self, lo, hi, mat, M=None, rot=None, group=None):
        lo, hi = Vector(lo), Vector(hi)
        c, s = (lo + hi) / 2, hi - lo
        m = (M or Matrix.Identity(4)) @ T(c)
        if rot:
            m = m @ Euler(rot).to_matrix().to_4x4()
        m = m @ Matrix.Diagonal((abs(s.x), abs(s.y), abs(s.z), 1.0))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._assign(r["verts"], mat, group)

    def cyl(self, center, radius, length, mat, axis="Z", segs=12, radius2=None,
            ellipse=(1.0, 1.0), M=None, rot=None, group=None):
        m = (M or Matrix.Identity(4)) @ T(center)
        if rot:
            m = m @ Euler(rot).to_matrix().to_4x4()
        m = m @ AXIS_ROT[axis] @ Matrix.Diagonal((ellipse[0], ellipse[1], 1.0, 1.0))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=radius,
                                  radius2=radius if radius2 is None else radius2,
                                  depth=length, matrix=m)
        self._assign(r["verts"], mat, group)

    def text(self, body, size, mat, M, align="CENTER", extrude=0.0006):
        """M places text space (X right, Y up, Z out) into builder space."""
        verts, faces = text_geometry(body, size, align, extrude)
        vs = [self.bm.verts.new(M @ v) for v in verts]
        new_faces = []
        for f in faces:
            try:
                new_faces.append(self.bm.faces.new([vs[i] for i in f]))
            except ValueError:
                pass
        self._assign(vs, mat)

    def build(self, name, key, origin=None, location=None, rotation_z=0.0):
        """origin: geometry was authored in world space -> recentre on this point.
        location: geometry was authored in local space -> place object here."""
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) != 2 or e.calc_face_angle(math.pi) > SHARP_ANGLE:
                e.smooth = False

        # box-projected UVs, 1 UV unit = 1 m, so tiling textures line up in Unity
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                p = loop.vert.co
                loop[uv].uv = (p.y, p.z) if ax == 0 else (p.x, p.z) if ax == 1 else (p.x, p.y)

        if origin is not None:
            bmesh.ops.translate(bm, vec=-Vector(origin), verts=bm.verts)

        bm.verts.index_update()
        groups = {g: sorted({v.index for v in vs if v.is_valid}) for g, vs in self.groups.items()}

        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(MATS[m])
        try:                                    # Blender < 4.1 needs this for sharp edges
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.pi
        except AttributeError:
            pass

        obj = bpy.data.objects.new(name, me)
        COLL[key].objects.link(obj)
        if key in ROOTS:
            obj.parent = ROOTS[key]
        if origin is not None:
            obj.location = Vector(origin)
        elif location is not None:
            obj.location = Vector(location)
        obj.rotation_euler = (0.0, 0.0, rotation_z)
        for g, idx in groups.items():
            obj.vertex_groups.new(name=g).add(idx, 1.0, "REPLACE")
        return obj


# ---- wall frames ------------------------------------------------------------
# A wall frame is a matrix whose local axes are:
#   X = to the viewer's right when facing the wall, Y = up, Z = out of the wall
# with its origin on the wall surface at world coordinate `a` along the wall.
WALLS = {
    "L": (Vector((1, 0, 0)), lambda a: Vector((X0, a, 0))),
    "R": (Vector((-1, 0, 0)), lambda a: Vector((X1, a, 0))),
    "B": (Vector((0, -1, 0)), lambda a: Vector((a, Y1, 0))),
    "F": (Vector((0, 1, 0)), lambda a: Vector((a, Y0, 0))),
}
WALL_SIGN = {"L": 1, "R": -1, "B": 1, "F": -1}   # local X vs world coordinate along wall


def wall_frame(wall, a=0.0):
    n, pt = WALLS[wall]
    up = Vector((0, 0, 1))
    right = (-n).cross(up)
    p = pt(a)
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = right[i], up[i], n[i], p[i]
    return M


# ---- scene structure --------------------------------------------------------
def get_collection(name, parent):
    c = bpy.data.collections.new(name)
    parent.children.link(c)
    return c


def new_empty(name, key, location, display="PLAIN_AXES", size=0.3, parent=True):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = display
    e.empty_display_size = size
    e.location = Vector(location)
    COLL[key].objects.link(e)
    if parent and key in ROOTS:
        e.parent = ROOTS[key]
    return e


def cleanup():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    master = bpy.data.collections.get(MASTER)
    if master:
        for o in list(master.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for c in list(master.children_recursive):
            bpy.data.collections.remove(c)
        bpy.data.collections.remove(master)
    # the untouched default startup cube would sit in the middle of the room
    cube = bpy.data.objects.get("Cube")
    if cube and cube.type == "MESH" and len(cube.data.vertices) == 8 and cube.location.length < 1e-6:
        bpy.data.objects.remove(cube, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures,
                       bpy.data.lights, bpy.data.cameras):
        for d in list(datablocks):
            if d.users == 0:
                datablocks.remove(d)


def setup_collections():
    master = bpy.data.collections.new(MASTER)
    bpy.context.scene.collection.children.link(master)
    for key in ("ENVIRONMENT", "DETAILS", "LIGHTS", "COLLISION", "GAMEPLAY", "CHARACTER"):
        COLL[key] = get_collection(key, master)

    def root(name, key):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "CUBE"
        e.empty_display_size = 0.25
        COLL[key].objects.link(e)
        return e

    env_root = root("BunkerBathroom_Root", "ENVIRONMENT")
    ROOTS["ENVIRONMENT"] = env_root
    ROOTS["GAMEPLAY"] = env_root
    ROOTS["LIGHTS"] = env_root
    ROOTS["DETAILS"] = root("BunkerBathroom_Details", "DETAILS")
    ROOTS["COLLISION"] = root("BunkerBathroom_Collision", "COLLISION")


# ============================================================================
# ARCHITECTURE
# ============================================================================
def create_floor():
    rng = random.Random(7)
    b = MeshBuilder()
    b.box((X0, Y0, -0.12), (X1, Y1, 0.0), "Grout")
    nx, ny, g = 13, 18, 0.004
    tw, tl = (X1 - X0) / nx, (Y1 - Y0) / ny
    for i in range(nx):
        for j in range(ny):
            x, y = X0 + i * tw + g, Y0 + j * tl + g
            mat = "Floor_Tile_Worn" if rng.random() < 0.18 else "Floor_Tile"
            b.box((x, y, -0.01), (x + tw - 2 * g, y + tl - 2 * g, 0.004), mat)
    dl, dr = DOOR_X - DOOR_OPEN_W / 2, DOOR_X + DOOR_OPEN_W / 2
    b.box((dl, Y0 - WALL_T, -0.12), (dr, Y0, 0.0), "Grout")
    return b.build("Floor", "ENVIRONMENT")


def create_wall():
    dl, dr = DOOR_X - DOOR_OPEN_W / 2, DOOR_X + DOOR_OPEN_W / 2
    b = MeshBuilder()
    b.box((X0 - WALL_T, Y0 - WALL_T, 0), (X0, Y1 + WALL_T, ROOM_H), "Concrete")
    b.box((X1, Y0 - WALL_T, 0), (X1 + WALL_T, Y1 + WALL_T, ROOM_H), "Concrete")
    b.box((X0, Y1, 0), (X1, Y1 + WALL_T, ROOM_H), "Concrete")
    b.box((X0, Y0 - WALL_T, 0), (dl, Y0, ROOM_H), "Concrete")
    b.box((dr, Y0 - WALL_T, 0), (X1, Y0, ROOM_H), "Concrete")
    b.box((dl, Y0 - WALL_T, DOOR_OPEN_H), (dr, Y0, ROOM_H), "Concrete")
    b.build("Walls", "ENVIRONMENT")

    c = MeshBuilder()
    c.box((X0 - WALL_T, Y0 - WALL_T, ROOM_H), (X1 + WALL_T, Y1 + WALL_T, ROOM_H + 0.25), "Concrete")
    c.build("Ceiling", "ENVIRONMENT")


def create_wall_lining():
    """Lower painted wall panels, dark skirting and the faded yellow safety stripe."""
    dl, dr = DOOR_X - DOOR_OPEN_W / 2, DOOR_X + DOOR_OPEN_W / 2
    runs = [("L", Y0, Y1), ("R", Y0, Y1), ("B", X0, X1),
            ("F", X0, dl - 0.13), ("F", dr + 0.13, X1)]
    b = MeshBuilder()
    for wall, a0, a1 in runs:
        M = wall_frame(wall)
        s = WALL_SIGN[wall]
        l0, l1 = sorted((s * a0, s * a1))
        n = max(1, round((l1 - l0) / 1.2))
        w = (l1 - l0) / n
        for k in range(n):
            b.box((l0 + k * w + 0.004, 0.0, 0.0), (l0 + (k + 1) * w - 0.004, 1.2, 0.02), "Wall_Panel", M)
        b.box((l0, 0.0, 0.0), (l1, 0.12, 0.03), "Dark_Grey_Metal", M)
        b.box((l0, 1.2, 0.0), (l1, 1.28, 0.025), "Industrial_Yellow", M)
        b.box((l0, 1.28, 0.0), (l1, 1.30, 0.03), "Worn_Grey_Metal", M)
    return b.build("Wall_Lining", "ENVIRONMENT")


def create_ceiling_lights():
    b = MeshBuilder()
    z = ROOM_H
    for i, (x, y, L) in enumerate(CEILING_LIGHTS):
        b.box((x - 0.15, y - L / 2, z - 0.08), (x + 0.15, y + L / 2, z), "Worn_Grey_Metal")
        b.box((x - 0.12, y - L / 2 + 0.04, z - 0.095), (x + 0.12, y + L / 2 - 0.04, z - 0.075), "Light_Emissive")
        for e in (-1, 1):
            yc = y + e * (L / 2 - 0.015)
            b.box((x - 0.155, yc - 0.025, z - 0.1), (x + 0.155, yc + 0.025, z), "Dark_Grey_Metal")
        create_light("Light_Ceiling_%02d" % (i + 1), (x, y, z - 0.1), 0.24, L - 0.08, 70.0 * L / 1.25)
        new_empty("LIGHT_CEIL_%02d" % (i + 1), "GAMEPLAY", (x, y, z - 0.11), size=0.15)
    return b.build("Ceiling_Lights", "ENVIRONMENT")


def create_light(name, loc, size_x, size_y, energy):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size_x, size_y
    ld.energy = energy
    ld.color = LIGHT_COLOR
    try:
        ld.use_shadow = True
    except AttributeError:
        pass
    lo = bpy.data.objects.new(name, ld)
    lo.location = Vector(loc)
    COLL["LIGHTS"].objects.link(lo)
    lo.parent = ROOTS["LIGHTS"]
    return lo


def create_ventilation_duct():
    b = MeshBuilder()
    z0 = ROOM_H - 0.3
    b.box((-0.3, Y0, z0), (0.3, Y1, ROOM_H), "Worn_Grey_Metal")
    y = 0.8
    while y < Y1 - 0.3:
        b.box((-0.32, y - 0.015, z0 - 0.02), (0.32, y + 0.015, ROOM_H), "Worn_Grey_Metal")
        y += 1.6
    for gy in (2.5, 5.5, 8.5):
        b.box((-0.22, gy - 0.17, z0 - 0.012), (0.22, gy + 0.17, z0), "Stainless_Steel")
        b.box((-0.19, gy - 0.14, z0 - 0.014), (0.19, gy + 0.14, z0 - 0.011), "Drain_Void")
        for k in range(7):
            sy = gy - 0.12 + k * 0.04
            b.box((-0.19, sy - 0.006, z0 - 0.022), (0.19, sy + 0.006, z0 - 0.012), "Worn_Grey_Metal")
    return b.build("Ventilation_Duct", "ENVIRONMENT", origin=(0, Y1 / 2, z0))


def add_pipe_run(b, x, z, r, mat, y0=Y0, y1=Y1, coupling_step=2.2, hanger_step=1.8):
    b.cyl((x, (y0 + y1) / 2, z), r, y1 - y0, mat, axis="Y", segs=12)
    y = y0 + 1.0
    while y < y1 - 0.4:
        b.cyl((x, y, z), r + 0.012, 0.08, mat, axis="Y", segs=12)
        y += coupling_step
    y = y0 + 0.6
    while y < y1 - 0.3:
        b.cyl((x, y, z), r + 0.008, 0.03, "Dark_Grey_Metal", axis="Y", segs=12)
        top = z + r
        if top < ROOM_H - 0.01:
            b.cyl((x, y, (top + ROOM_H) / 2), 0.008, ROOM_H - top, "Worn_Grey_Metal", segs=6)
        y += hanger_step


def create_pipes():
    b = MeshBuilder()
    add_pipe_run(b, 3.55, 2.98, 0.06, "Worn_Grey_Metal")
    add_pipe_run(b, 3.30, 3.04, 0.04, "Industrial_Yellow")
    add_pipe_run(b, -3.55, 2.95, 0.05, "Dark_Grey_Metal")

    # riser in the back-right corner with an isolation valve
    rx, ry = 3.85, 10.75
    b.cyl((rx, ry, 2.98 / 2), 0.05, 2.98, "Worn_Grey_Metal")
    b.cyl(((rx + 3.55) / 2, ry, 2.98), 0.05, rx - 3.55, "Worn_Grey_Metal", axis="X")
    b.cyl((rx, ry, 2.98), 0.065, 0.12, "Worn_Grey_Metal")
    for zc in (0.6, 2.2):
        b.cyl((rx, ry, zc), 0.062, 0.06, "Worn_Grey_Metal")
        b.box((rx, ry - 0.03, zc - 0.025), (X1, ry + 0.03, zc + 0.025), "Dark_Grey_Metal")
    vz = 1.3
    b.cyl((rx, ry, vz), 0.075, 0.16, "Worn_Grey_Metal")
    b.cyl((rx - 0.1, ry, vz), 0.012, 0.16, "Stainless_Steel", axis="X", segs=8)
    wx, R = rx - 0.18, 0.11
    for k in range(8):
        ang = k * math.pi / 4
        b.box((-0.009, -R * math.sin(math.pi / 8) - 0.006, -0.009),
              (0.009, R * math.sin(math.pi / 8) + 0.006, 0.009), "Industrial_Yellow",
              M=T((wx, ry + R * math.cos(ang), vz + R * math.sin(ang))), rot=(ang + math.pi / 2, 0, 0))
    for ang in (0.0, math.pi / 2):
        b.box((-0.006, -R, -0.008), (0.006, R, 0.008), "Industrial_Yellow", M=T((wx, ry, vz)), rot=(ang, 0, 0))
    b.cyl((wx, ry, vz), 0.025, 0.03, "Industrial_Yellow", axis="X")
    return b.build("Pipes", "ENVIRONMENT", origin=(X1, Y1 / 2, ROOM_H))


def create_cable_tray():
    b = MeshBuilder()
    x0, z0, ya, yb = X0 + 0.05, 2.62, 0.3, Y1 - 0.3
    b.box((x0, ya, z0), (x0 + 0.28, yb, z0 + 0.008), "Worn_Grey_Metal")
    b.box((x0, ya, z0), (x0 + 0.012, yb, z0 + 0.07), "Worn_Grey_Metal")
    b.box((x0 + 0.268, ya, z0), (x0 + 0.28, yb, z0 + 0.07), "Worn_Grey_Metal")
    y = ya + 0.2
    while y < yb:
        b.box((X0, y - 0.015, z0 - 0.04), (x0 + 0.3, y + 0.015, z0), "Dark_Grey_Metal")
        b.box((X0, y - 0.03, z0 - 0.08), (X0 + 0.01, y + 0.03, z0 + 0.01), "Dark_Grey_Metal")
        y += 1.5
    for k, cx in enumerate((0.07, 0.13, 0.19)):
        b.cyl((x0 + cx, (ya + yb) / 2, z0 + 0.024), 0.014 + 0.003 * k, yb - ya, "Rubber", axis="Y", segs=8)
    b.box((x0 + 0.04, ya - 0.06, z0), (x0 + 0.22, ya + 0.0, ROOM_H), "Rubber")
    return b.build("Cable_Tray", "ENVIRONMENT", origin=(X0, Y1 / 2, z0))


def create_conduits():
    b = MeshBuilder()
    r, mat = 0.012, "Dark_Grey_Metal"
    b.cyl((0, Y1 - 0.04, 2.6), r, ROOM_W, mat, axis="X", segs=8)            # back wall
    b.cyl((X1 - 0.04, Y1 / 2, 2.5), r, ROOM_L, mat, axis="Y", segs=8)       # right wall
    b.cyl(((1.1 + X1) / 2, Y0 + 0.04, 2.5), r, X1 - 1.1, mat, axis="X", segs=8)   # front wall
    b.cyl((1.1, Y0 + 0.04, (1.52 + 2.5) / 2), r, 2.5 - 1.52, mat, segs=8)  # switch drop
    for i in range(SINK_COUNT):                                              # mirror lamp drops
        yc = SINK_Y0 + (i + 0.5) * SINK_PITCH
        b.cyl((X1 - 0.04, yc, (2.24 + 2.5) / 2), r, 0.26, mat, segs=8)
    for x in (-3.0, -1.5, 1.5, 3.0):
        b.box((x - 0.012, Y1 - 0.06, 2.575), (x + 0.012, Y1, 2.625), "Worn_Grey_Metal")
    for y in (1.0, 2.5, 9.5):
        b.box((X1 - 0.06, y - 0.012, 2.475), (X1, y + 0.012, 2.525), "Worn_Grey_Metal")
    # junction boxes
    for x in (-2.0, 2.0):
        b.box((x - 0.07, Y1 - 0.07, 2.53), (x + 0.07, Y1, 2.67), "Dark_Grey_Metal")
    for y in (3.0, 9.0):
        b.box((X1 - 0.07, y - 0.07, 2.43), (X1, y + 0.07, 2.57), "Dark_Grey_Metal")
    b.box((1.03, Y0, 2.43), (1.17, Y0 + 0.07, 2.57), "Dark_Grey_Metal")
    b.box((X1 - 0.07, Y0, 2.43), (X1, Y0 + 0.07, 2.57), "Dark_Grey_Metal")
    return b.build("Electrical_Conduits", "DETAILS", origin=(0, Y1 / 2, 2.5))


def add_drain_channel(b, x0, y0, x1, y1):
    along_y = (y1 - y0) > (x1 - x0)
    zt = 0.0045
    b.box((x0, y0, -0.005), (x1, y1, zt), "Drain_Void")
    rim = 0.018
    b.box((x0 - rim, y0 - rim, 0), (x1 + rim, y0, zt + 0.004), "Stainless_Steel")
    b.box((x0 - rim, y1, 0), (x1 + rim, y1 + rim, zt + 0.004), "Stainless_Steel")
    b.box((x0 - rim, y0, 0), (x0, y1, zt + 0.004), "Stainless_Steel")
    b.box((x1, y0, 0), (x1 + rim, y1, zt + 0.004), "Stainless_Steel")
    step, t = 0.045, 0.006
    if along_y:
        y = y0 + step / 2
        while y < y1:
            b.box((x0, y - t, zt), (x1, y + t, zt + 0.003), "Stainless_Steel")
            y += step
    else:
        x = x0 + step / 2
        while x < x1:
            b.box((x - t, y0, zt), (x + t, y1, zt + 0.003), "Stainless_Steel")
            x += step


def create_floor_details():
    b = MeshBuilder()
    add_drain_channel(b, STALL_FRONT_X + 0.42, STALL_Y0 + 0.2, STALL_FRONT_X + 0.58, STALL_Y0 + STALL_COUNT * STALL_W - 0.2)
    add_drain_channel(b, SINK_FRONT_X - 0.53, SINK_Y0 + 0.1, SINK_FRONT_X - 0.37, SINK_Y1 - 0.1)
    add_drain_channel(b, -1.55, Y1 - 0.58, 1.55, Y1 - 0.42)
    add_drain_channel(b, -0.12, 5.88, 0.12, 6.12)                    # central floor drain
    b.build("Floor_Drains", "ENVIRONMENT")

    m = MeshBuilder()
    z0, z1, w = 0.004, 0.0055, 0.025
    fx = STALL_FRONT_X + 0.2
    m.box((fx - w, STALL_Y0, z0), (fx + w, STALL_Y0 + STALL_COUNT * STALL_W, z1), "Industrial_Yellow")
    sx = SINK_FRONT_X - 0.2
    m.box((sx - w, SINK_Y0, z0), (sx + w, SINK_Y1, z1), "Industrial_Yellow")
    # keep-clear zone inside the entrance
    m.box((DOOR_X - 0.75, 0.05, z0), (DOOR_X - 0.70, 1.25, z1), "Industrial_Yellow")
    m.box((DOOR_X + 0.70, 0.05, z0), (DOOR_X + 0.75, 1.25, z1), "Industrial_Yellow")
    m.box((DOOR_X - 0.75, 1.20, z0), (DOOR_X + 0.75, 1.25, z1), "Industrial_Yellow")
    m.build("Floor_Markings", "ENVIRONMENT")


# ============================================================================
# ENTRANCE DOOR
# ============================================================================
def create_door():
    dl, dr = DOOR_X - DOOR_OPEN_W / 2, DOOR_X + DOOR_OPEN_W / 2
    fw, yb, yf = 0.12, Y0 - WALL_T - 0.03, Y0 + 0.03
    f = MeshBuilder()
    f.box((dl - fw, yb, 0), (dl + 0.01, yf, DOOR_OPEN_H + fw), "Dark_Grey_Metal")
    f.box((dr - 0.01, yb, 0), (dr + fw, yf, DOOR_OPEN_H + fw), "Dark_Grey_Metal")
    f.box((dl - fw, yb, DOOR_OPEN_H - 0.01), (dr + fw, yf, DOOR_OPEN_H + fw), "Dark_Grey_Metal")
    for x in (dl - 0.085, dr + 0.045):                          # yellow jamb stripes
        f.box((x, yf, 0), (x + 0.04, yf + 0.004, DOOR_OPEN_H + 0.06), "Industrial_Yellow")
    f.box((dl - fw, yf, DOOR_OPEN_H + 0.045), (dr + fw, yf + 0.004, DOOR_OPEN_H + 0.085), "Industrial_Yellow")
    f.box((dl, Y0 - WALL_T, 0), (dr, Y0, 0.012), "Stainless_Steel")         # threshold
    f.box((dl + 0.01, -0.19, 0.012), (dr - 0.01, -0.17, 0.03), "Rubber")    # floor seal
    # bolt keeper on the latch-side jamb
    f.box((dr - 0.02, -0.12, 1.32), (dr - 0.01, -0.07, 1.40), "Worn_Grey_Metal")
    f.build("Door_Entrance_Frame", "ENVIRONMENT", origin=(DOOR_X, Y0, 0))

    # leaf - local space, origin on the hinge axis, room side = +Y
    W, H, t = DOOR_OPEN_W - 0.03, DOOR_OPEN_H - 0.03, 0.04
    d = MeshBuilder()
    d.box((0.005, -t, 0.012), (W, t, H), "Dark_Grey_Metal")
    for s in (-1, 1):
        y0, y1 = sorted((s * t, s * (t + 0.004)))
        d.box((0.03, y0, 1.0), (W - 0.03, y1, 1.12), "Industrial_Yellow")      # safety stripe
        y0, y1 = sorted((s * t, s * (t + 0.01)))
        for zc in (0.6, 1.9):
            d.box((0.04, y0, zc - 0.035), (W - 0.04, y1, zc + 0.035), "Worn_Grey_Metal")
        d.box((0.02, y0, 0.012), (W - 0.02, y1, 0.13), "Worn_Grey_Metal")      # kick plate
        # lever handle
        hx, hz = W - 0.13, 1.05
        d.box((hx - 0.03, y0, hz - 0.1), (hx + 0.03, y1, hz + 0.1), "Stainless_Steel")
        d.cyl((hx, s * (t + 0.03), hz), 0.012, 0.04, "Stainless_Steel", axis="Y", segs=10)
        d.cyl((hx - 0.07, s * (t + 0.05), hz), 0.012, 0.15, "Stainless_Steel", axis="X", segs=10)
    # louvre vent in the lower leaf
    d.box((0.3, -t - 0.002, 0.18), (W - 0.3, t + 0.002, 0.48), "Drain_Void")
    for k in range(6):
        d.box((-(W - 0.64) / 2, -0.045, -0.006), ((W - 0.64) / 2, 0.045, 0.006), "Worn_Grey_Metal",
              M=T((W / 2, 0, 0.21 + k * 0.045)), rot=(math.radians(35), 0, 0))
    # slide-bolt lock (room side) + key cylinder (corridor side)
    d.box((W - 0.22, t, 1.31), (W - 0.02, t + 0.025, 1.39), "Worn_Grey_Metal")
    d.cyl((W - 0.1, t + 0.035, 1.35), 0.01, 0.22, "Stainless_Steel", axis="X", segs=8)
    d.cyl((W - 0.18, t + 0.05, 1.35), 0.014, 0.04, "Dark_Plastic", axis="Y", segs=8)
    d.cyl((W - 0.13, -t - 0.006, 1.3), 0.02, 0.012, "Stainless_Steel", axis="Y", segs=12)
    # hinges on the room side
    for zc in (0.35, 1.15, 1.95):
        d.cyl((0.0, t + 0.012, zc), 0.022, 0.2, "Worn_Grey_Metal", segs=10)
        d.box((0.0, t, zc - 0.09), (0.12, t + 0.006, zc + 0.09), "Worn_Grey_Metal")
    leaf = d.build("Door_Entrance_Leaf", "ENVIRONMENT", location=(dl + 0.01, -0.125, 0.0),
                   rotation_z=math.radians(DOOR_OPEN_DEG))
    leaf["keep_rotation"] = True
    return leaf


# ============================================================================
# STALLS + TOILETS
# ============================================================================
def create_toilet(name, location):
    """Industrial floor toilet with a wall flush valve. Local: wall at x=0, faces +X."""
    b = MeshBuilder()
    b.box((0.03, -0.13, 0.08), (0.26, 0.13, 0.40), "White_Ceramic")
    b.cyl((0.36, 0, 0.17), 1.0, 0.34, "White_Ceramic", radius2=0.8, ellipse=(0.17, 0.13), segs=16)
    b.cyl((0.42, 0, 0.365), 0.85, 0.07, "White_Ceramic", radius2=1.0, ellipse=(0.26, 0.19), segs=20)
    b.cyl((0.43, 0, 0.415), 1.0, 0.025, "Dark_Plastic", ellipse=(0.25, 0.185), segs=20)
    b.cyl((0.43, 0, 0.432), 1.0, 0.012, "Dark_Plastic", ellipse=(0.24, 0.18), segs=20)
    b.box((0.15, -0.09, 0.40), (0.21, 0.09, 0.44), "Dark_Plastic")
    b.cyl((0.08, 0, 0.68), 0.018, 0.56, "Stainless_Steel", segs=10)         # flush pipe
    b.box((0.02, -0.07, 0.95), (0.12, 0.07, 1.09), "Stainless_Steel")      # flush valve
    b.cyl((0.125, 0, 1.03), 0.025, 0.012, "Dark_Plastic", axis="X", segs=12)
    return b.build(name, "ENVIRONMENT", location=location)


def create_stalls():
    FX = STALL_FRONT_X
    yk = [STALL_Y0 + k * STALL_W for k in range(STALL_COUNT + 1)]
    p = MeshBuilder()
    for y in yk:
        p.box((X0 + 0.02, y - 0.0125, 0.15), (FX - 0.03, y + 0.0125, 2.0), "Dark_Grey_Metal")
        for z in (0.4, 1.75):
            p.box((X0, y - 0.03, z - 0.04), (X0 + 0.05, y + 0.03, z + 0.04), "Stainless_Steel")
        p.box((FX - 0.03, y - 0.06, 0.1), (FX + 0.03, y + 0.06, 2.0), "Dark_Grey_Metal")   # pilaster
        p.box((FX - 0.035, y - 0.065, 0.0), (FX + 0.035, y + 0.065, 0.1), "Stainless_Steel")
    p.box((FX - 0.02, yk[0] - 0.06, 2.0), (FX + 0.02, yk[-1] + 0.06, 2.05), "Stainless_Steel")
    p.build("Stall_Partitions", "ENVIRONMENT", origin=(FX, (yk[0] + yk[-1]) / 2, 0))

    acc = MeshBuilder()
    door_text = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # text faces +X
    for i in range(STALL_COUNT):
        y0, y1 = yk[i], yk[i + 1]
        dw = (y1 - 0.065) - (y0 + 0.065)
        d = MeshBuilder()
        d.box((-0.0125, 0.003, 0.15), (0.0125, dw - 0.003, 1.95), "Dark_Grey_Metal")
        for s in (-1, 1):
            xa, xb = sorted((s * 0.0125, s * 0.015))
            d.box((xa, 0.02, 0.16), (xb, dw - 0.02, 0.38), "Worn_Grey_Metal")         # kick plate
        d.box((0.0125, dw / 2 - 0.1, 1.72), (0.016, dw / 2 + 0.1, 1.84), "Industrial_Yellow")
        d.text("%02d" % (i + 1), 0.08, "Sign_Ink", T((0.016, dw / 2, 1.78)) @ door_text)
        d.cyl((0.05, dw - 0.08, 1.0), 0.012, 0.18, "Stainless_Steel", segs=10)        # pull handle
        for zc in (0.93, 1.07):
            d.cyl((0.03, dw - 0.08, zc), 0.008, 0.04, "Stainless_Steel", axis="X", segs=8)
        d.box((-0.035, dw - 0.11, 1.02), (-0.0125, dw - 0.05, 1.08), "Worn_Grey_Metal")  # latch
        d.box((0.0125, dw - 0.12, 1.12), (0.016, dw - 0.04, 1.16), "Industrial_Yellow")  # indicator
        for zc in (0.45, 1.65):
            d.cyl((0.0, 0.0, zc), 0.012, 0.12, "Stainless_Steel", segs=8)
        door = d.build("Stall_%02d_Door" % (i + 1), "ENVIRONMENT", location=(FX, y0 + 0.065, 0.0),
                       rotation_z=math.radians(STALL_DOOR_ANGLES[i % len(STALL_DOOR_ANGLES)]))
        door["keep_rotation"] = True

        create_toilet("Stall_%02d_Toilet" % (i + 1), (X0, (y0 + y1) / 2, 0.0))

        # paper dispenser on the partition to the toilet's left
        py = y1 - 0.0125
        acc.box((X0 + 0.5, py - 0.11, 0.62), (X0 + 0.74, py, 0.84), "Stainless_Steel")
        acc.box((X0 + 0.52, py - 0.112, 0.63), (X0 + 0.72, py - 0.11, 0.66), "Drain_Void")
        # coat hook on the partition behind the door
        acc.cyl((FX - 0.25, y0 + 0.0125 + 0.03, 1.7), 0.01, 0.06, "Stainless_Steel", axis="Y", segs=8)
    acc.build("Stall_Accessories", "DETAILS", origin=(X0, (yk[0] + yk[-1]) / 2, 0))


# ============================================================================
# URINALS
# ============================================================================
def create_urinal(name, x):
    M = wall_frame("B", x)
    b = MeshBuilder()
    b.box((-0.18, 0.45, 0.02), (0.18, 1.15, 0.06), "White_Ceramic", M)
    for s in (-1, 1):
        b.box((s * 0.16, 0.45, 0.02), (s * 0.20, 1.10, 0.32), "White_Ceramic", M)
    b.box((-0.20, 0.42, 0.02), (0.20, 0.60, 0.36), "White_Ceramic", M)
    b.cyl((0, 0.60, 0.345), 0.025, 0.40, "White_Ceramic", axis="X", segs=10, M=M)
    b.box((-0.20, 1.10, 0.02), (0.20, 1.16, 0.16), "White_Ceramic", M)
    b.cyl((0, 0.602, 0.18), 0.04, 0.004, "Stainless_Steel", axis="Y", segs=12, M=M)
    b.cyl((0, 1.29, 0.06), 0.012, 0.26, "Stainless_Steel", axis="Y", segs=10, M=M)       # flush pipe
    b.box((-0.06, 1.42, 0.02), (0.06, 1.56, 0.10), "Dark_Grey_Metal", M)                  # valve box
    b.cyl((0, 1.49, 0.105), 0.02, 0.01, "Stainless_Steel", axis="Z", segs=12, M=M)
    b.cyl((0, 0.335, 0.15), 0.025, 0.17, "Stainless_Steel", axis="Y", segs=10, M=M)     # drain
    b.cyl((0, 0.27, 0.085), 0.025, 0.13, "Stainless_Steel", axis="Z", segs=10, M=M)
    return b.build(name, "ENVIRONMENT", origin=M.translation)


def create_urinals():
    for i, x in enumerate(URINAL_X):
        create_urinal("Urinal_%02d" % (i + 1), x)
    M = wall_frame("B", 0.0)
    b = MeshBuilder()
    for k in range(len(URINAL_X) - 1):
        lx = (URINAL_X[k] + URINAL_X[k + 1]) / 2
        b.box((lx - 0.015, 0.55, 0.03), (lx + 0.015, 1.45, 0.48), "Dark_Grey_Metal", M)
        for yc in (0.7, 1.3):
            b.box((lx - 0.03, yc - 0.03, 0.0), (lx + 0.03, yc + 0.03, 0.05), "Stainless_Steel", M)
    b.build("Urinal_Dividers", "ENVIRONMENT", origin=M.translation)


# ============================================================================
# SINK
# ============================================================================
def create_sink():
    SX, y0, y1 = SINK_FRONT_X, SINK_Y0, SINK_Y1
    t = MeshBuilder()
    t.box((SX, y0, 0.60), (X1, y1, 0.645), "Stainless_Steel")
    t.box((SX, y0, 0.60), (SX + 0.03, y1, SINK_TOP), "Stainless_Steel")
    t.box((X1 - 0.03, y0, 0.60), (X1, y1, 1.10), "Stainless_Steel")             # backsplash
    t.box((SX, y0, 0.60), (X1, y0 + 0.03, SINK_TOP), "Stainless_Steel")
    t.box((SX, y1 - 0.03, 0.60), (X1, y1, SINK_TOP), "Stainless_Steel")
    t.cyl((SX + 0.012, (y0 + y1) / 2, SINK_TOP), 0.018, y1 - y0, "Stainless_Steel", axis="Y", segs=10)
    for k in range(1, SINK_COUNT):
        yb = y0 + k * SINK_PITCH
        t.box((SX + 0.03, yb - 0.008, 0.645), (X1 - 0.03, yb + 0.008, 0.80), "Stainless_Steel")
    for i in range(SINK_COUNT):
        yc = y0 + (i + 0.5) * SINK_PITCH
        t.cyl((SX + 0.27, yc, 0.647), 0.035, 0.004, "Drain_Void", segs=12)
    ang = math.atan2(0.28, 0.45)
    for yb in (y0 + 0.15, y0 + 2 * SINK_PITCH, y0 + 3 * SINK_PITCH, y1 - 0.15):
        t.box((SX + 0.05, yb - 0.015, 0.57), (X1, yb + 0.015, 0.60), "Worn_Grey_Metal")
        t.box((-0.265, -0.012, -0.015), (0.265, 0.012, 0.015), "Worn_Grey_Metal",
              M=T((X1 - 0.225, yb, 0.44)), rot=(0, ang, 0))
        t.box((X1 - 0.01, yb - 0.04, 0.26), (X1, yb + 0.04, 0.62), "Worn_Grey_Metal")
    t.build("Sink_Trough", "ENVIRONMENT", origin=(X1, (y0 + y1) / 2, 0))

    f, m, lamps, soap, pl = MeshBuilder(), MeshBuilder(), MeshBuilder(), MeshBuilder(), MeshBuilder()
    for i in range(SINK_COUNT):
        yc = y0 + (i + 0.5) * SINK_PITCH
        # faucet: wall plate, spout, outlet, wrist-blade handle
        f.cyl((X1 - 0.038, yc, 1.0), 0.03, 0.016, "Stainless_Steel", axis="X", segs=12)
        f.cyl((X1 - 0.12, yc, 1.0), 0.013, 0.18, "Stainless_Steel", axis="X", segs=10)
        f.cyl((X1 - 0.21, yc, 0.975), 0.015, 0.05, "Stainless_Steel", segs=10)
        f.cyl((X1 - 0.21, yc, 0.946), 0.012, 0.01, "Dark_Plastic", segs=10)
        f.cyl((X1 - 0.045, yc + 0.1, 1.0), 0.02, 0.03, "Stainless_Steel", axis="X", segs=10)
        f.box((X1 - 0.07, yc + 0.1, 0.994), (X1 - 0.055, yc + 0.21, 1.006), "Stainless_Steel")
        # mirror
        m.box((X1 - 0.025, yc - 0.31, 1.34), (X1, yc + 0.31, 2.10), "Stainless_Steel")
        m.box((X1 - 0.032, yc - 0.29, 1.36), (X1 - 0.02, yc + 0.29, 2.08), "Glass")
        # mirror lamp
        lamps.box((X1 - 0.15, yc - 0.16, 2.17), (X1, yc + 0.16, 2.24), "Dark_Grey_Metal")
        lamps.box((X1 - 0.14, yc - 0.15, 2.165), (X1 - 0.01, yc + 0.15, 2.172), "Light_Emissive")
        create_light("Light_Mirror_%02d" % (i + 1), (X1 - 0.075, yc, 2.16), 0.12, 0.28, 10.0)
        new_empty("LIGHT_WALL_%02d" % (i + 1), "GAMEPLAY", (X1 - 0.075, yc, 2.15), size=0.1)
        # plumbing: tail, nut, trap arm
        pl.cyl((SX + 0.27, yc, 0.51), 0.02, 0.18, "Stainless_Steel", segs=10)
        pl.cyl((SX + 0.27, yc, 0.57), 0.026, 0.03, "Worn_Grey_Metal", segs=10)
        pl.cyl(((SX + 0.27 + X1) / 2, yc, 0.43), 0.02, X1 - SX - 0.25, "Stainless_Steel", axis="X", segs=10)
        pl.cyl((SX + 0.27, yc, 0.43), 0.024, 0.04, "Stainless_Steel", segs=10)
    for k in range(SINK_COUNT + 1):                                             # soap dispensers
        yb = y0 + k * SINK_PITCH
        soap.box((X1 - 0.105, yb - 0.05, 1.38), (X1, yb + 0.05, 1.58), "Dark_Plastic")
        soap.box((X1 - 0.11, yb - 0.035, 1.47), (X1 - 0.105, yb + 0.035, 1.54), "Stainless_Steel")
        soap.cyl((X1 - 0.08, yb, 1.37), 0.006, 0.02, "Stainless_Steel", segs=8)
    # supply lines along the wall back to the riser
    for zc in (0.25, 0.30):
        pl.cyl((X1 - 0.05, (y0 + 10.75) / 2, zc), 0.015, 10.75 - y0, "Worn_Grey_Metal", axis="Y", segs=8)
    yy = y0 + 0.5
    while yy < 10.6:
        pl.box((X1 - 0.07, yy - 0.012, 0.22), (X1, yy + 0.012, 0.33), "Dark_Grey_Metal")
        yy += 1.0
    pl.cyl((X1 - 0.05, 10.75, 0.275), 0.022, 0.1, "Worn_Grey_Metal", segs=8)

    f.build("Sink_Faucets", "DETAILS", origin=(X1, (y0 + y1) / 2, 1.0))
    m.build("Sink_Mirrors", "ENVIRONMENT", origin=(X1, (y0 + y1) / 2, 1.7))
    lamps.build("Mirror_Lamps", "ENVIRONMENT", origin=(X1, (y0 + y1) / 2, 2.2))
    soap.build("Soap_Dispensers", "DETAILS", origin=(X1, (y0 + y1) / 2, 1.5))
    pl.build("Sink_Plumbing", "DETAILS", origin=(X1, (y0 + y1) / 2, 0.4))

    # towel dispenser + bin past the end of the sink
    a = MeshBuilder()
    a.box((X1 - 0.13, 8.68, 1.0), (X1, 9.02, 1.45), "Stainless_Steel")
    a.box((X1 - 0.134, 8.72, 1.02), (X1 - 0.13, 8.98, 1.04), "Drain_Void")
    a.cyl((3.7, 9.15, 0.31), 0.18, 0.62, "Dark_Grey_Metal", segs=16)
    a.cyl((3.7, 9.15, 0.64), 0.185, 0.04, "Industrial_Yellow", segs=16)
    a.box((3.5, 9.11, 0.01), (3.53, 9.19, 0.05), "Worn_Grey_Metal")
    a.build("Towel_Dispenser_And_Bin", "DETAILS", origin=(3.7, 9.0, 0))


# ============================================================================
# WALL DETAILS, PANELS, GRILLES, SIGNAGE
# ============================================================================
def add_wall_grille(b, M, cx, cy, w, h, base=0.0):
    b.box((cx - w / 2, cy - h / 2, base), (cx + w / 2, cy + h / 2, base + 0.006), "Drain_Void", M)
    bw = 0.03
    for lo, hi in (((cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2 + bw)),
                   ((cx - w / 2, cy + h / 2 - bw), (cx + w / 2, cy + h / 2)),
                   ((cx - w / 2, cy - h / 2), (cx - w / 2 + bw, cy + h / 2)),
                   ((cx + w / 2 - bw, cy - h / 2), (cx + w / 2, cy + h / 2))):
        b.box((lo[0], lo[1], base), (hi[0], hi[1], base + 0.03), "Worn_Grey_Metal", M)
    n = int((h - 2 * bw) / 0.035)
    for k in range(n):
        yc = cy - h / 2 + bw + 0.0175 + k * 0.035
        b.box((-(w - 2 * bw) / 2, -0.016, -0.004), ((w - 2 * bw) / 2, 0.016, 0.004), "Worn_Grey_Metal",
              M=M @ T((cx, yc, base + 0.015)), rot=(math.radians(-40), 0, 0))


def add_maintenance_panel(b, M, cx, y0, w, h, base=0.02, label="MAINTENANCE"):
    b.box((cx - w / 2 - 0.025, y0 - 0.025, base), (cx + w / 2 + 0.025, y0 + h + 0.025, base + 0.015), "Dark_Grey_Metal", M)
    b.box((cx - w / 2, y0, base), (cx + w / 2, y0 + h, base + 0.028), "Worn_Grey_Metal", M)
    for yc in (y0 + 0.15, y0 + h - 0.15):
        b.cyl((cx - w / 2 - 0.006, yc, base + 0.028), 0.012, 0.1, "Stainless_Steel", axis="Y", segs=8, M=M)
    b.box((cx + w / 2 - 0.09, y0 + h / 2 - 0.05, base + 0.028), (cx + w / 2 - 0.04, y0 + h / 2 + 0.05, base + 0.045), "Dark_Plastic", M)
    b.box((cx - 0.17, y0 + h - 0.13, base + 0.028), (cx + 0.17, y0 + h - 0.06, base + 0.031), "Industrial_Yellow", M)
    b.text(label, 0.032, "Sign_Ink", M @ T((cx, y0 + h - 0.095, base + 0.031)))
    for dx in (-1, 1):                                   # screws
        for dy in (0, 1):
            b.cyl((cx + dx * (w / 2 - 0.03), y0 + 0.03 + dy * (h - 0.06), base + 0.03), 0.008, 0.006,
                  "Stainless_Steel", axis="Z", segs=8, M=M)


def create_wall_details():
    b = MeshBuilder()
    # ventilation grilles
    add_wall_grille(b, wall_frame("B", 0.0), 0.0, 2.15, 0.7, 0.4)
    add_wall_grille(b, wall_frame("R", 1.6), 0.0, 2.1, 0.5, 0.3)
    add_wall_grille(b, wall_frame("L", 9.9), 0.0, 2.3, 0.5, 0.3)
    # maintenance access panels
    add_maintenance_panel(b, wall_frame("B", -3.2), 0.0, 0.3, 0.7, 1.0)
    add_maintenance_panel(b, wall_frame("R", 9.9), 0.0, 0.5, 0.7, 1.0, label="PLUMBING ACCESS")
    # light switch box beside the door (room side)
    Mf = wall_frame("F", 1.1)
    b.box((-0.07, 1.38, 0.0), (0.07, 1.52, 0.06), "Dark_Grey_Metal", Mf)
    for dx in (-0.025, 0.025):
        b.box((dx - 0.008, 1.43, 0.06), (dx + 0.008, 1.47, 0.075), "Dark_Plastic", Mf)
    # electrical distribution box on the back wall
    Mb = wall_frame("B", -1.9)
    b.box((-0.18, 1.55, 0.0), (0.18, 2.0, 0.14), "Dark_Grey_Metal", Mb)
    b.box((-0.18, 1.93, 0.14), (0.18, 1.96, 0.143), "Industrial_Yellow", Mb)
    b.box((-0.11, 1.84, 0.14), (0.11, 1.90, 0.142), "Industrial_Yellow", Mb)
    b.text("ELECTRICAL", 0.026, "Sign_Ink", Mb @ T((0, 1.87, 0.142)))
    b.box((0.13, 1.7, 0.14), (0.15, 1.8, 0.16), "Worn_Grey_Metal", Mb)
    # intercom by the entrance
    Mi = wall_frame("R", 1.0)
    b.box((-0.1, 1.35, 0.0), (0.1, 1.62, 0.06), "Dark_Plastic", Mi)
    b.box((-0.07, 1.48, 0.06), (0.07, 1.59, 0.063), "Stainless_Steel", Mi)
    b.cyl((0.0, 1.41, 0.065), 0.015, 0.012, "Industrial_Yellow", axis="Z", segs=10, M=Mi)
    b.build("Wall_Details", "DETAILS")


def create_signage():
    """Safety poster + cleaning schedule on the left wall just inside the entrance."""
    a = 1.6
    M = wall_frame("L", a)
    b = MeshBuilder()
    # poster: thin metal sign
    b.box((-0.42, 1.48, 0.02), (0.42, 2.50, 0.032), "Industrial_Yellow", M)
    b.box((-0.42, 2.32, 0.032), (0.42, 2.50, 0.034), "Sign_Ink", M)
    for lo, hi in (((-0.39, 1.51), (0.39, 1.525)), ((-0.39, 2.295), (0.39, 2.31)),
                   ((-0.39, 1.51), (-0.375, 2.31)), ((0.375, 1.51), (0.39, 2.31))):
        b.box((lo[0], lo[1], 0.032), (hi[0], hi[1], 0.034), "Sign_Ink", M)
    b.text("NOTICE", 0.07, "Industrial_Yellow", M @ T((0, 2.41, 0.034)))
    b.text("A CLEAN\nBUNKER IS A\nSAFER BUNKER.", 0.085, "Sign_Ink", M @ T((0, 1.93, 0.034)))
    b.box((-0.25, 1.62, 0.032), (0.25, 1.627, 0.034), "Sign_Ink", M)
    b.text("SANITATION DIVISION  -  SECTOR C", 0.022, "Sign_Ink", M @ T((0, 1.575, 0.034)))
    for dx in (-0.39, 0.39):
        for dy in (1.51, 2.47):
            b.cyl((dx, dy, 0.035), 0.008, 0.006, "Stainless_Steel", axis="Z", segs=8, M=M)

    # cleaning schedule board below it, on standoffs over the yellow stripe
    b.box((-0.25, 0.92, 0.0), (0.25, 1.46, 0.035), "Worn_Grey_Metal", M)
    b.box((-0.23, 0.94, 0.035), (0.23, 1.44, 0.038), "Sign_Paper", M)
    b.text("CLEANING SCHEDULE", 0.03, "Sign_Ink", M @ T((0, 1.405, 0.038)))
    b.box((-0.21, 1.38, 0.038), (0.21, 1.384, 0.039), "Sign_Ink", M)
    rows = [("MON", "FLOORS / STALLS"), ("TUE", "SINKS / MIRRORS"), ("WED", "TOILETS / URINALS"),
            ("THU", "FLOORS / STALLS"), ("FRI", "SINKS / MIRRORS"), ("SAT", "TOILETS / URINALS"),
            ("SUN", "DEEP CLEAN")]
    for k, (day, task) in enumerate(rows):
        yc = 1.35 - k * 0.048
        b.text(day, 0.024, "Sign_Ink", M @ T((-0.2, yc, 0.038)), align="LEFT")
        b.text(task, 0.024, "Sign_Ink", M @ T((-0.1, yc, 0.038)), align="LEFT")
        b.box((-0.21, yc - 0.026, 0.038), (0.21, yc - 0.024, 0.039), "Sign_Ink", M)
    b.text("INSPECTED: ________", 0.018, "Sign_Ink", M @ T((-0.2, 0.98, 0.038)), align="LEFT")
    b.box((-0.06, 1.44, 0.035), (0.06, 1.47, 0.045), "Stainless_Steel", M)        # clip
    b.build("Signage", "DETAILS", origin=M.translation)


# ============================================================================
# COLLISION
# ============================================================================
def create_collision_box(name, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    c = (lo + hi) / 2
    b = MeshBuilder()
    b.box(lo - c, hi - c, "Grout")
    o = b.build("COL_" + name, "COLLISION", location=c)
    o.data.materials.clear()
    o.display_type = "WIRE"
    o.hide_render = True
    return o


def create_collision():
    dl, dr = DOOR_X - DOOR_OPEN_W / 2, DOOR_X + DOOR_OPEN_W / 2
    cb = create_collision_box
    cb("Floor", (X0 - WALL_T, Y0 - WALL_T, -0.2), (X1 + WALL_T, Y1 + WALL_T, 0.0))
    cb("Ceiling", (X0 - WALL_T, Y0 - WALL_T, ROOM_H), (X1 + WALL_T, Y1 + WALL_T, ROOM_H + 0.25))
    cb("Wall_Left", (X0 - WALL_T, Y0 - WALL_T, 0), (X0, Y1 + WALL_T, ROOM_H))
    cb("Wall_Right", (X1, Y0 - WALL_T, 0), (X1 + WALL_T, Y1 + WALL_T, ROOM_H))
    cb("Wall_Back", (X0, Y1, 0), (X1, Y1 + WALL_T, ROOM_H))
    cb("Wall_Front_L", (X0, Y0 - WALL_T, 0), (dl, Y0, ROOM_H))
    cb("Wall_Front_R", (dr, Y0 - WALL_T, 0), (X1, Y0, ROOM_H))
    cb("Wall_Front_Header", (dl, Y0 - WALL_T, DOOR_OPEN_H), (dr, Y0, ROOM_H))
    cb("DoorFrame_L", (dl - 0.12, Y0 - WALL_T - 0.03, 0), (dl + 0.01, Y0 + 0.03, DOOR_OPEN_H + 0.12))
    cb("DoorFrame_R", (dr - 0.01, Y0 - WALL_T - 0.03, 0), (dr + 0.12, Y0 + 0.03, DOOR_OPEN_H + 0.12))
    if abs(DOOR_OPEN_DEG) < 1e-3:
        cb("Door_Leaf_Closed", (dl, -0.17, 0), (dr, -0.08, DOOR_OPEN_H))

    FX = STALL_FRONT_X
    for k in range(STALL_COUNT + 1):
        y = STALL_Y0 + k * STALL_W
        cb("Stall_Partition_%02d" % k, (X0, y - 0.02, 0), (FX, y + 0.02, 2.05))
        cb("Stall_Pilaster_%02d" % k, (FX - 0.035, y - 0.065, 0), (FX + 0.035, y + 0.065, 2.05))
    for i in range(STALL_COUNT):
        yc = STALL_Y0 + (i + 0.5) * STALL_W
        cb("Toilet_%02d" % (i + 1), (X0, yc - 0.2, 0), (X0 + 0.69, yc + 0.2, 0.44))

    for i, x in enumerate(URINAL_X):
        cb("Urinal_%02d" % (i + 1), (x - 0.2, Y1 - 0.36, 0.0), (x + 0.2, Y1, 1.16))
    for k in range(len(URINAL_X) - 1):
        lx = (URINAL_X[k] + URINAL_X[k + 1]) / 2
        cb("Urinal_Divider_%02d" % (k + 1), (lx - 0.02, Y1 - 0.48, 0.0), (lx + 0.02, Y1, 1.45))

    cb("Sink", (SINK_FRONT_X - 0.02, SINK_Y0, 0.0), (X1, SINK_Y1, 1.1))
    cb("Trash_Bin", (3.52, 8.97, 0), (3.88, 9.33, 0.66))
    cb("Pipe_Riser", (3.8, 10.7, 0), (X1, 10.8, ROOM_H))


# ============================================================================
# PLACEHOLDER CHARACTER, CAMERA, SPAWN POINTS
# ============================================================================
def create_character():
    b = MeshBuilder()
    mat = "Character_Placeholder"
    b.box((-0.09, -0.10, 1.57), (0.09, 0.10, 1.80), mat, group="Head")
    b.box((-0.06, 0.10, 1.66), (0.06, 0.115, 1.71), "Dark_Plastic", group="Head")   # visor = forward
    b.box((-0.05, -0.05, 1.47), (0.05, 0.05, 1.58), mat, group="Neck")
    b.box((-0.19, -0.11, 1.22), (0.19, 0.11, 1.48), mat, group="Chest")
    b.box((-0.16, -0.10, 1.04), (0.16, 0.10, 1.23), mat, group="Spine")
    b.box((-0.17, -0.11, 0.88), (0.17, 0.11, 1.05), mat, group="Hips")
    bones = [("Hips", (0, 0, 0.92), (0, 0, 1.05), None),
             ("Spine", (0, 0, 1.05), (0, 0, 1.25), "Hips"),
             ("Chest", (0, 0, 1.25), (0, 0, 1.47), "Spine"),
             ("Neck", (0, 0, 1.47), (0, 0, 1.57), "Chest"),
             ("Head", (0, 0, 1.57), (0, 0, 1.80), "Neck")]
    # the character faces +Y, so its left side is -X
    for side, s in (("L", -1), ("R", 1)):
        b.box((s * 0.035, -0.075, 0.50), (s * 0.165, 0.075, 0.90), mat, group="UpperLeg." + side)
        b.box((s * 0.045, -0.06, 0.08), (s * 0.155, 0.06, 0.50), mat, group="LowerLeg." + side)
        b.box((s * 0.04, -0.08, 0.0), (s * 0.16, 0.18, 0.08), mat, group="Foot." + side)
        b.box((s * 0.20, -0.055, 1.13), (s * 0.31, 0.055, 1.46), mat, group="UpperArm." + side)
        b.box((s * 0.215, -0.05, 0.86), (s * 0.305, 0.05, 1.14), mat, group="LowerArm." + side)
        b.box((s * 0.22, -0.035, 0.72), (s * 0.30, 0.045, 0.86), mat, group="Hand." + side)
        bones += [("UpperLeg." + side, (s * 0.1, 0, 0.92), (s * 0.1, 0, 0.50), "Hips"),
                  ("LowerLeg." + side, (s * 0.1, 0, 0.50), (s * 0.1, 0, 0.09), "UpperLeg." + side),
                  ("Foot." + side, (s * 0.1, 0, 0.09), (s * 0.1, 0.16, 0.03), "LowerLeg." + side),
                  ("UpperArm." + side, (s * 0.255, 0, 1.44), (s * 0.26, 0, 1.14), "Chest"),
                  ("LowerArm." + side, (s * 0.26, 0, 1.14), (s * 0.26, 0, 0.87), "UpperArm." + side),
                  ("Hand." + side, (s * 0.26, 0, 0.87), (s * 0.26, 0, 0.73), "LowerArm." + side)]
    body = b.build("PlaceholderHuman_Mesh", "CHARACTER")

    arm_data = bpy.data.armatures.new("PlaceholderHuman_Armature")
    rig = bpy.data.objects.new("PlaceholderHuman_Rig", arm_data)
    COLL["CHARACTER"].objects.link(rig)
    rig.location = CHARACTER_POS
    rig.show_in_front = True
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    vl.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent in bones:
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail = head, tail
        if parent:
            eb.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)

    body.parent = rig
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    return rig


def create_gameplay_markers():
    new_empty("PLAYER_START", "GAMEPLAY", PLAYER_START, display="SINGLE_ARROW", size=0.6)
    new_empty("PLAYER_CAMERA_START", "GAMEPLAY", PLAYER_START + Vector((0, 0, CAMERA_HEIGHT)), display="SPHERE", size=0.08)
    new_empty("PLAYER_LOOK_TARGET", "GAMEPLAY", (PLAYER_START.x, 6.0, CAMERA_HEIGHT), size=0.15)

    cam_data = bpy.data.cameras.new("PLAYER_CAMERA")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(80)
    cam_data.clip_start = 0.05
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("PLAYER_CAMERA", cam_data)
    cam.location = PLAYER_START + Vector((0, 0, CAMERA_HEIGHT))
    cam.rotation_euler = (math.radians(90), 0, 0)          # looks along +Y into the room
    COLL["GAMEPLAY"].objects.link(cam)
    bpy.context.scene.camera = cam


# ============================================================================
# SCENE SETTINGS / FINALIZE / EXPORT
# ============================================================================
def setup_scene():
    scene = bpy.context.scene
    us = scene.unit_settings
    us.system = "METRIC"
    us.scale_length = 1.0
    us.length_unit = "METERS"

    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    ee = scene.eevee
    for attr, val in (("use_gtao", True), ("gtao_distance", 0.6), ("use_soft_shadows", True),
                      ("use_shadows", True), ("use_raytracing", True), ("shadow_ray_count", 2),
                      ("taa_render_samples", 64)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background") if world.node_tree else None
    if bg:
        bg.inputs["Color"].default_value = (0.02, 0.022, 0.025, 1)
        bg.inputs["Strength"].default_value = 1.0

    try:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "MATERIAL"
                        space.clip_end = 200
    except AttributeError:
        pass


def apply_rotation_scale():
    """Bake rotation/scale into mesh data (location kept so pivots stay meaningful).
    Doors keep their rotation so they can be swung in Unity around the hinge."""
    for o in COLL["ENVIRONMENT"].objects[:] + COLL["DETAILS"].objects[:] + COLL["COLLISION"].objects[:]:
        if o.type != "MESH" or o.get("keep_rotation"):
            continue
        m = o.matrix_basis.to_3x3()
        if m == Matrix.Identity(3):
            continue
        o.data.transform(m.to_4x4())
        o.rotation_euler = (0, 0, 0)
        o.scale = (1, 1, 1)


def hierarchy(root):
    out = [root]
    for c in root.children:
        out += hierarchy(c)
    return out


def export_fbx(path, roots):
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    objs = [o for r in roots for o in hierarchy(r) if o.type in {"MESH", "EMPTY"}]
    for o in objs:
        o.select_set(True)
    vl.objects.active = roots[0]
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_tspace=False,
        use_custom_props=False,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
    )
    for o in objs:
        o.select_set(False)
    return len(objs)


def write_material_table(path):
    data = {"materials": []}
    for name, d in MATERIAL_DEFS.items():
        color, rough, metal = d[0], d[1], d[2]
        data["materials"].append({"name": name, "color": list(color), "metallic": metal,
                                  "smoothness": round(1.0 - rough, 3), "emission": d[8]})
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def export_all():
    out = EXPORT_DIR or (bpy.path.abspath("//") if bpy.data.filepath else "")
    if not out:
        print("[BunkerBathroom] .blend not saved and EXPORT_DIR empty -> skipped FBX export.")
        return None
    os.makedirs(out, exist_ok=True)
    env_path = os.path.join(out, "BunkerBathroom_Environment.fbx")
    col_path = os.path.join(out, "BunkerBathroom_Collision.fbx")
    n_env = export_fbx(env_path, [ROOTS["ENVIRONMENT"], ROOTS["DETAILS"]])
    n_col = export_fbx(col_path, [ROOTS["COLLISION"]])
    write_material_table(os.path.join(out, "BunkerBathroom_Materials.json"))
    print("[BunkerBathroom] exported %d objects -> %s" % (n_env, env_path))
    print("[BunkerBathroom] exported %d objects -> %s" % (n_col, col_path))
    return out


def report():
    tris = 0
    for key in ("ENVIRONMENT", "DETAILS"):
        for o in COLL[key].objects:
            if o.type == "MESH":
                tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("[BunkerBathroom] visible triangles: %d" % tris)


def main():
    cleanup()
    setup_collections()
    create_materials()
    setup_scene()

    create_floor()
    create_wall()
    create_wall_lining()
    create_ceiling_lights()
    create_ventilation_duct()
    create_pipes()
    create_cable_tray()
    create_conduits()
    create_floor_details()
    create_door()
    create_stalls()
    create_urinals()
    create_sink()
    create_wall_details()
    create_signage()
    create_collision()
    create_gameplay_markers()
    create_character()

    apply_rotation_scale()
    bpy.context.view_layer.update()
    report()
    if AUTO_EXPORT:
        export_all()
    # hide collision boxes in the viewport (eye icon) - unhide to edit them
    lc = bpy.context.view_layer.layer_collection.children[MASTER].children["COLLISION"]
    lc.hide_viewport = True
    print("[BunkerBathroom] done.")


main()
