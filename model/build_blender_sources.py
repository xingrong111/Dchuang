"""Run with Blender: blender --background --python model/build_blender_sources.py.
Creates editable .blend scenes from this project's GLBs; requires Blender, never fabricates sources.
"""
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
assets = root/'frontend/public/models'
destination = root/'model/blender-sources'
destination.mkdir(parents=True, exist_ok=True)
for filename in ('daafu.glb','canmao.glb','shouxing.glb'):
    target = destination/(Path(filename).stem+'.blend')
    if target.exists():
        raise FileExistsError(f'源工程已存在，拒绝覆盖：{target}')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(assets/filename))
    imported = list(bpy.context.scene.objects)
    for obj in imported:
        obj['source_asset'] = filename
        obj['provenance'] = '项目程序化泥人模型，非混元输出'
    bpy.ops.object.camera_add(location=(4, -6, 3))
    camera = bpy.context.object
    from mathutils import Vector
    camera.rotation_euler = (Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(3,-4,5))
    bpy.context.object.data.energy = 500
    bpy.context.object.data.size = 5
    bpy.context.scene.render.resolution_x = 1600
    bpy.context.scene.render.resolution_y = 1200
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
print('三份可编辑 Blender 场景已保存；导入不会创造人工精雕或额外 UV 细节。')
