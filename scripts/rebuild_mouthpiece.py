"""Rebuild the original 1.2 mouthpiece, preserving all cup/exterior geometry.

blender --background --python scripts/rebuild_mouthpiece.py -- --output-blend rebuilt_mask.blend
Uses only authored mask data and procedural dimensions; no game assets required.
"""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'assets/full_face_mask.blend')
parser.add_argument('--output-blend',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
source=args.source.resolve();output=args.output_blend.resolve()
if source==output:raise ValueError('Use a separate output path so the source remains available')
bpy.ops.wm.open_mainfile(filepath=str(source))
assert not bpy.data.images and not bpy.data.texts and not bpy.data.libraries
model=next(c for c in bpy.data.collections if c.name.startswith('MASK |'))
game=bpy.data.objects['SK_CodexScubaMask'];rig=bpy.data.objects['Armature']
assert [b.name for b in rig.data.bones]==['Root']
assert len(game.data.materials)==10 and game.data.materials[9].name=='M_Scuba_Mouthpiece'
mat=bpy.data.materials['M_Scuba_Mouthpiece']
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def digest(o):
 return hashlib.sha256(b''.join(struct.pack('<3f',*v.co)for v in o.data.vertices)+b''.join(struct.pack('<I',len(p.vertices))+struct.pack('<'+'I'*len(p.vertices),*p.vertices)for p in o.data.polygons)).hexdigest()
before={o.name:digest(o)for o in model.objects}
for o in list(model.objects):
 if o.name.startswith(('23 |','24 |')):bpy.data.objects.remove(o,do_unlink=True)
created=[]
def make(name,v,f):
 import bmesh
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);model.objects.link(o);me.materials.append(mat)
 for p in me.polygons:p.use_smooth=True
 created.append(o);return o
def catmull(points,steps=6):
 pp=[Vector(p)for p in points];out=[]
 for i in range(len(pp)-1):
  a=pp[max(0,i-1)];b=pp[i];c=pp[i+1];d=pp[min(len(pp)-1,i+2)]
  for j in range(steps):
   t=j/steps;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
 return out+[pp[-1]]
# A continuous hollow duct: lip-facing opening, soft elbow, then interior regulator seat.
path=catmull([(-10.60,0,3.28),(-10.46,0,2.95),(-10.26,0,2.40),(-10.03,0,1.65),(-9.98,0,1.17),(-10.10,0,.82)],8)
nv=48;verts=[];faces=[]
for i,p in enumerate(path):
 tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized();up=tangent.cross(Vector((0,1,0))).normalized()
 t=i/(len(path)-1);a=float(np.interp(t,[0,.18,.45,.75,1],[1.10,1.06,.85,.62,.48]));b=float(np.interp(t,[0,.25,.6,1],[.34,.30,.24,.15]))
 for layer in range(2):
  for j in range(nv):
   q=2*math.pi*j/nv;v=p+Vector((0,1,0))*(a-layer*.085)*math.cos(q)+up*(b-layer*.085)*math.sin(q)
   # Both lip rims sweep toward the mouth corners while the lumen remains open.
   v.x+=.13*(v.y/1.10)**2*(1-smooth(t/.20));verts.append(v)
for i in range(len(path)-1):
 for l in range(2):
  for j in range(nv):
   a=i*nv*2+l*nv+j;b=i*nv*2+l*nv+(j+1)%nv;faces.append((a,b,b+nv*2,a+nv*2))
for i in [0,len(path)-1]:
 for j in range(nv):
  a=i*nv*2+j;b=i*nv*2+(j+1)%nv;faces.append((a,b,b+nv,a+nv))
duct=make('23 | Hollow ergonomic mouthpiece and internal duct',verts,faces)
# Soft, slightly cupped side seats; rounded section avoids hard edges against the lips.
for sign in [-1,1]:
 pathw=catmull([(-10.54,sign*.73,2.86),(-10.42,sign*.98,3.04),(-10.17,sign*1.24,3.31),(-9.98,sign*1.37,3.57),(-9.92,sign*1.40,3.75)],8)
 vv=[];ff=[];n=20
 for i,p in enumerate(pathw):
  t=i/(len(pathw)-1);tangent=(pathw[min(i+1,len(pathw)-1)]-pathw[max(i-1,0)]).normalized()
  x=Vector((1,0,0));across=tangent.cross(x).normalized();depth=across.cross(tangent).normalized()
  radius=.30*(.8+.2*math.sin(math.pi*t))
  # Smooth closed ends use small finite rings and caps.
  taper=min(1,(i+1)/3,(len(pathw)-i)/3)
  for j in range(n):
   ang=2*math.pi*j/n;vv.append(p+across*(radius*taper*math.cos(ang))+depth*(.105*taper*math.sin(ang)))
 for i in range(len(pathw)-1):
  for j in range(n):ff.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
 ff.extend([tuple(reversed(range(n))),tuple(range((len(pathw)-1)*n,len(pathw)*n))])
 make('24 | Curved silicone bite flange '+str(sign),vv,ff)

for o in created:
 o.parent=rig
 group=o.vertex_groups.new(name='Root');group.add(list(range(len(o.data.vertices))),1,'REPLACE')
 modifier=o.modifiers.new('Root rigid binding','ARMATURE');modifier.object=rig
old=game.data
retained=[p for p in old.polygons if p.material_index!=9]
ids=sorted({v for p in retained for v in p.vertices});remap={v:i for i,v in enumerate(ids)}
coords=[old.vertices[i].co.copy()for i in ids]
faces=[tuple(remap[v]for v in p.vertices)for p in retained]
materials=[p.material_index for p in retained]
oldloops=[i for p in retained for i in p.loop_indices]
for o in created:
 o.data.calc_loop_triangles();offset=len(coords);coords.extend(v.co.copy()for v in o.data.vertices)
 faces.extend(tuple(i+offset for i in t.vertices)for t in o.data.loop_triangles)
 materials.extend([9]*len(o.data.loop_triangles))
mesh=bpy.data.meshes.new('Original oral-nasal mask optimized game mesh')
mesh.from_pydata(coords,[],faces);mesh.update()
for m in old.materials:mesh.materials.append(m)
for p,m in zip(mesh.polygons,materials):p.material_index=m;p.use_smooth=True
for layer in old.uv_layers:
 uv=mesh.uv_layers.new(name=layer.name)
 for i,oldi in enumerate(oldloops):uv.data[i].uv=layer.data[oldi].uv
 for i in range(len(oldloops),len(uv.data)):
  v=mesh.vertices[mesh.loops[i].vertex_index].co;uv.data[i].uv=(v.y/4+.5,v.z/5)
game.data=mesh;game.vertex_groups.clear()
group=game.vertex_groups.new(name='Root');group.add(list(range(len(coords))),1,'REPLACE')
after={o.name:digest(o)for o in model.objects}
assert all(before[n]==after[n]for n in before if not n.startswith(('23 |','24 |')))
for data in list(bpy.data.meshes):
 if data.users==0:bpy.data.meshes.remove(data)
bpy.context.preferences.filepaths.save_version=0
output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=False)
report={'passed':True,'source':source.name,'output':output.name,'triangles':len(faces),
 'all_cup_and_exterior_components_unchanged':True,
 'reconstructed_components_equal_original':{n:before.get(n)==after[n]for n in after if n.startswith(('23 |','24 |'))},
 'material_triangle_counts':{m.name:materials.count(i)for i,m in enumerate(mesh.materials)}}
output.with_suffix('.rebuild.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
