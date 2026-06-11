import bpy
import bmesh
import math
from math import floor
from mathutils import Matrix, Vector


# --- 001 删除无材质球的模型 ---
class Y_OT_DeleteObjectsWithoutMaterials(bpy.types.Operator):
    bl_idname = "object.y_delete_objects_without_materials"
    bl_label = "Delete Objects Without Materials"
    bl_description = "Deletes all mesh objects in the scene that have no materials assigned."

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in bpy.context.scene.objects)

    def execute(self, context):
        deleted_count = 0
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        for obj in list(mesh_objects):
            if not obj.data.materials:
                print(f"删除没有材质的对象: {obj.name}")
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted_count += 1
            else:
                has_valid_material = False
                for slot in obj.material_slots:
                    if slot.material is not None:
                        has_valid_material = True
                        break
                
                if not has_valid_material:
                    print(f"删除只有空材质槽的对象: {obj.name}")
                    bpy.data.objects.remove(obj, do_unlink=True)
                    deleted_count += 1
        
        self.report({'INFO'}, f"操作完成，共删除了 {deleted_count} 个没有材质的对象。")
        return {'FINISHED'}


# --- 002 按材质球命名 ---
class Y_OT_RenameByMaterial(bpy.types.Operator):
    bl_idname = "object.y_rename_by_material"
    bl_label = "Rename Objects by Material"
    bl_description = "Renames mesh objects based on the name of their first material."

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in bpy.context.scene.objects)

    def execute(self, context):
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                materials = obj.data.materials
                if materials:
                    material_name = materials[0].name
                    obj.name = material_name
                    self.report({'INFO'}, f"已将对象重命名为: {material_name}")
                else:
                    self.report({'INFO'}, f"对象 {obj.name} 没有材质，跳过")

        self.report({'INFO'}, "所有符合条件的对象已重命名。")
        return {'FINISHED'}


# --- 003 删除无图片节点模型 ---
class Y_OT_DeleteEmptyModels(bpy.types.Operator):
    bl_idname = "object.y_delete_empty_models"
    bl_label = "Delete Empty Models"
    bl_description = "Deletes all mesh objects that only have empty image texture nodes or no materials."

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in bpy.context.scene.objects)

    def execute(self, context):
        deleted_nodes_count = 0
        for material in list(bpy.data.materials):
            if material and material.use_nodes:
                for node in list(material.node_tree.nodes):
                    if node.type == 'TEX_IMAGE' and node.image is None:
                        material.node_tree.nodes.remove(node)
                        deleted_nodes_count += 1
                        self.report({'INFO'}, f"已删除材质 '{material.name}' 中的一个空白图像节点。")

        self.report({'INFO'}, f"第一步：清理完成。总共删除了 {deleted_nodes_count} 个空白图像节点。")

        def is_material_empty(material):
            if not material or not material.use_nodes:
                return True
            
            has_image_node = False
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image is not None:
                    has_image_node = True
                    break
            
            if has_image_node:
                return False
                
            has_other_nodes = False
            for node in material.node_tree.nodes:
                if node.type not in {'BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'}:
                    has_other_nodes = True
                    break
            
            if not has_other_nodes:
                return True
            return False

        object_names_to_check = [obj.name for obj in bpy.context.scene.objects if obj.type == 'MESH']
        objects_to_delete = set()
        
        for obj_name in object_names_to_check:
            obj = bpy.context.scene.objects.get(obj_name)
            if not obj:
                continue
            
            has_non_empty_material = False
            for material in obj.data.materials:
                if material and not is_material_empty(material):
                    has_non_empty_material = True
                    break
            
            if not has_non_empty_material:
                objects_to_delete.add(obj_name)
                self.report({'INFO'}, f"模型 '{obj_name}' 的所有材质都为空，将被删除。")
        
        if objects_to_delete:
            self.report({'INFO'}, "第二步：开始删除模型...")
            for obj_name in objects_to_delete:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    self.report({'INFO'}, f"已删除模型: '{obj_name}'")
        else:
            self.report({'INFO'}, "第二步：没有找到需要删除的模型。")

        return {'FINISHED'}


# --- 004 重命名之后清理重复模型 ---
class Y_OT_CleanDuplicatesAfterRename(bpy.types.Operator):
    bl_idname = "object.y_clean_duplicates_after_rename"
    bl_label = "Clean Duplicates After Rename"
    bl_description = "Finds and deletes duplicate meshes with the same material."

    @classmethod
    def poll(cls, context):
        return len([obj for obj in bpy.context.scene.objects if obj.type == 'MESH']) >= 2

    def execute(self, context):
        def get_suffix_number(name):
            parts = name.rsplit('.', 1)
            if len(parts) > 1 and parts[1].isdigit():
                return int(parts[1])
            return -1

        def compare_uv_maps(uv_map1, uv_map2, tolerance=1e-5):
            if len(uv_map1.data) != len(uv_map2.data):
                return False
            
            for i in range(len(uv_map1.data)):
                uv1 = uv_map1.data[i].uv
                uv2 = uv_map2.data[i].uv
                if abs(uv1.x - uv2.x) > tolerance or abs(uv1.y - uv2.y) > tolerance:
                    return False
            return True

        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        materials_map = {}
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and len(obj.data.materials) > 0:
                mat = obj.data.materials[0]
                if mat not in materials_map:
                    materials_map[mat] = []
                materials_map[mat].append(obj)

        objects_to_delete = set()
        
        for mat, obj_list in materials_map.items():
            if len(obj_list) <= 1:
                continue
        
            obj_list.sort(key=lambda x: get_suffix_number(x.name))

            i = 0
            while i < len(obj_list):
                obj1 = obj_list[i]
                j = i + 1
                while j < len(obj_list):
                    obj2 = obj_list[j]
        
                    if obj1 in objects_to_delete or obj2 in objects_to_delete:
                        j += 1
                        continue
                    
                    is_same_count = (
                        len(obj1.data.vertices) == len(obj2.data.vertices) and
                        len(obj1.data.edges) == len(obj2.data.edges) and
                        len(obj1.data.polygons) == len(obj2.data.polygons)
                    )
        
                    is_same_uv = False
                    if len(obj1.data.uv_layers) == len(obj2.data.uv_layers):
                        all_uvs_same = True
                        for uv_idx in range(len(obj1.data.uv_layers)):
                            if not compare_uv_maps(obj1.data.uv_layers[uv_idx], obj2.data.uv_layers[uv_idx]):
                                all_uvs_same = False
                                break
                        if all_uvs_same:
                            is_same_uv = True
        
                    if is_same_count and is_same_uv:
                        self.report({'INFO'}, f"找到重复模型: '{obj1.name}' 和 '{obj2.name}'")
                        
                        num1 = get_suffix_number(obj1.name)
                        num2 = get_suffix_number(obj2.name)

                        if num1 > num2:
                            to_delete = obj1
                        else:
                            to_delete = obj2
        
                        self.report({'INFO'}, f"标记 '{to_delete.name}' 为删除")
                        objects_to_delete.add(to_delete)
                        
                    j += 1
                i += 1

        for obj in objects_to_delete:
            bpy.data.objects.remove(obj, do_unlink=True)
            
        self.report({'INFO'}, "重复模型清理完成。")
        return {'FINISHED'}


# --- 005 从选中中删除相同的模型 ---
class Y_OT_DeleteIdenticalSelected(bpy.types.Operator):
    bl_idname = "object.y_delete_identical_selected"
    bl_label = "Delete Identical Selected"
    bl_description = "Deletes duplicate meshes from the current selection based on full data comparison."

    @classmethod
    def poll(cls, context):
        return len([obj for obj in context.selected_objects if obj.type == 'MESH']) >= 2

    def execute(self, context):
        def get_texture_paths(material):
            if not material or not material.use_nodes:
                return []
            
            paths = []
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    paths.append(node.image.filepath)
            return sorted(paths)

        def get_object_data(obj):
            if obj.type != 'MESH':
                return None
        
            data = {
                'name': obj.name,
                'vertex_count': len(obj.data.vertices),
                'edge_count': len(obj.data.edges),
                'face_count': len(obj.data.polygons),
                'uv_count': len(obj.data.uv_layers),
                'uv_data': [],
                'texture_paths': []
            }
            
            for uv_layer in obj.data.uv_layers:
                uv_coords = [uv.uv[:] for uv in uv_layer.data]
                data['uv_data'].append(sorted(uv_coords))
                
            for mat_slot in obj.data.materials:
                if mat_slot:
                    data['texture_paths'].extend(get_texture_paths(mat_slot))
            return data

        def compare_objects(obj1_data, obj2_data):
            if obj1_data['vertex_count'] != obj2_data['vertex_count'] or \
               obj1_data['edge_count'] != obj2_data['edge_count'] or \
               obj1_data['face_count'] != obj2_data['face_count']:
                return False
            
            if obj1_data['uv_count'] != obj2_data['uv_count']:
                return False
            
            if sorted(obj1_data['uv_data']) != sorted(obj2_data['uv_data']):
                return False

            if sorted(obj1_data['texture_paths']) != sorted(obj2_data['texture_paths']):
                return False
            
            return True

        def get_number_from_name(name):
            try:
                if '.' in name:
                    parts = name.split('.')
                    return int(parts[-1])
                else:
                    return -1
            except ValueError:
                return -1

        selected_objects = context.selected_objects
        
        if len(selected_objects) < 2:
            self.report({'WARNING'}, "请至少选择两个模型。")
            return {'CANCELLED'}

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        meshes = [obj for obj in selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "没有选中任何网格模型。")
            return {'CANCELLED'}

        mesh_data_list = [get_object_data(obj) for obj in meshes]
        to_delete = set()

        for i in range(len(meshes)):
            for j in range(i + 1, len(meshes)):
                obj1 = meshes[i]
                obj2 = meshes[j]

                if obj1 in to_delete or obj2 in to_delete:
                    continue

                if compare_objects(mesh_data_list[i], mesh_data_list[j]):
                    num1 = get_number_from_name(obj1.name)
                    num2 = get_number_from_name(obj2.name)

                    if num1 > num2:
                        self.report({'INFO'}, f"找到重复模型: {obj1.name} 和 {obj2.name}。正在删除 {obj1.name}。")
                        to_delete.add(obj1)
                    else:
                        self.report({'INFO'}, f"找到重复模型: {obj1.name} 和 {obj2.name}。正在删除 {obj2.name}。")
                        to_delete.add(obj2)
        
        if to_delete:
            bpy.ops.object.delete({'selected_objects': list(to_delete)}, use_global=False)
            self.report({'INFO'}, f"成功删除了 {len(to_delete)} 个重复模型。")
        else:
            self.report({'INFO'}, "没有在选中项中找到任何重复模型。")
            
        return {'FINISHED'}


# --- 006 选同贴图模型 ---
class Y_OT_SelectSameTexture(bpy.types.Operator):
    bl_idname = "object.y_select_same_texture"
    bl_label = "Select Same Texture"
    bl_description = "Selects all objects in the scene that use the same Base Color texture as the active object."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        def get_base_color_texture(obj):
            for mat_slot in obj.material_slots:
                if not mat_slot.material:
                    continue
                nodes = mat_slot.material.node_tree.nodes if mat_slot.material.use_nodes else []
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        base_color_input = node.inputs.get('Base Color')
                        if not base_color_input:
                            continue
                        for link in base_color_input.links:
                            connected_node = link.from_node
                            if connected_node.type == 'TEX_IMAGE' and connected_node.image:
                                return connected_node.image
            return None

        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "请先选择一个物体作为参考。")
            return {'CANCELLED'}

        target_image = get_base_color_texture(active_obj)
        if not target_image:
            self.report({'WARNING'}, "活动物体没有基础色贴图，无法查找。")
            return {'CANCELLED'}

        matching_objs = []
        for obj in bpy.data.objects:
            if not obj.material_slots:
                continue
            
            has_target = False
            for mat_slot in obj.material_slots:
                if not mat_slot.material:
                    continue
                    
                nodes = mat_slot.material.node_tree.nodes if mat_slot.material.use_nodes else []
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        base_color_input = node.inputs.get('Base Color')
                        if base_color_input and base_color_input.links:
                            tex_node = base_color_input.links[0].from_node
                            if tex_node.type == 'TEX_IMAGE' and tex_node.image == target_image:
                                has_target = True
                                break
                if has_target:
                    break
                    
            if has_target:
                matching_objs.append(obj)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in matching_objs:
            obj.select_set(True)
        context.view_layer.objects.active = active_obj

        self.report({'INFO'}, f"已选中 {len(matching_objs)} 个使用 {target_image.name} 的物体。")
        return {'FINISHED'}


# --- 007 节点复制到最前面的模型 ---
class Y_OT_CopyNodesToFirst(bpy.types.Operator):
    bl_idname = "object.y_copy_nodes_to_first"
    bl_label = "Copy Nodes to First"
    bl_description = "Copies image texture nodes from duplicate meshes to the first mesh in the selection."

    @classmethod
    def poll(cls, context):
        return len([obj for obj in context.selected_objects if obj.type == 'MESH']) >= 2

    def execute(self, context):
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

        def get_uv_data(mesh):
            uv_data = {}
            for uv_layer in mesh.uv_layers:
                uv_data[uv_layer.name] = sorted([uv.uv[:] for uv in uv_layer.data])
            return uv_data

        def get_texture_nodes_info(material):
            if not material or not material.use_nodes:
                return []
            
            nodes_info = []
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    node_info = {
                        'name': node.name,
                        'image': node.image,
                        'colorspace': node.image.colorspace_settings.name,
                        'location': node.location,
                        'links': []
                    }
                    for output_socket in node.outputs:
                        for link in output_socket.links:
                            node_info['links'].append({
                                'from_socket_name': output_socket.name,
                                'to_node_name': link.to_node.name,
                                'to_socket_name': link.to_socket.name
                            })
                    nodes_info.append(node_info)
            return nodes_info

        def compare_meshes(mesh1, mesh2):
            if len(mesh1.uv_layers) != len(mesh2.uv_layers):
                return False, f"UV层数量不匹配：'{mesh1.name}' 有 {len(mesh1.uv_layers)} 个，'{mesh2.name}' 有 {len(mesh2.uv_layers)} 个。"

            uv1_data = get_uv_data(mesh1)
            uv2_data = get_uv_data(mesh2)
            
            uv1_names = sorted(uv1_data.keys())
            uv2_names = sorted(uv2_data.keys())
            
            if uv1_names != uv2_names:
                return False, f"UV名称不匹配：'{mesh1.name}' 的 UV名称是 {uv1_names}，'{mesh2.name}' 的是 {uv2_names}。"

            for name, coords in uv1_data.items():
                if name not in uv2_data or coords != uv2_data[name]:
                    return False, f"UV名称 '{name}' 的坐标数据不匹配。"
            return True, None

        selected_objects = context.selected_objects

        if len(selected_objects) < 2:
            self.report({'WARNING'}, "请至少选择两个模型。")
            return {'CANCELLED'}

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        meshes = [obj for obj in selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "没有选中任何网格模型。")
            return {'CANCELLED'}

        meshes.sort(key=lambda obj: natural_sort_key(obj.name))
        
        processed_objects = set()

        for i in range(len(meshes)):
            obj1 = meshes[i]
            if obj1 in processed_objects:
                continue
            
            duplicates = []
            for j in range(i + 1, len(meshes)):
                obj2 = meshes[j]
                if obj2 not in processed_objects:
                    is_same, reason = compare_meshes(obj1.data, obj2.data)
                    
                    if is_same:
                        duplicates.append(obj2)
                    else:
                        print(f"对比 '{obj1.name}' 和 '{obj2.name}'：不匹配。原因：{reason}")
                        
            if duplicates:
                target_obj = obj1
                self.report({'INFO'}, f"找到与 '{target_obj.name}' UV布局相同的模型：{[d.name for d in duplicates]}")
                
                for dup_obj in duplicates:
                    source_material = dup_obj.data.materials[0]
                    target_material = target_obj.data.materials[0]
                    
                    if not target_material:
                        self.report({'WARNING'}, f"警告：目标模型 '{target_obj.name}' 没有材质，跳过。")
                        continue
                        
                    source_nodes_info = get_texture_nodes_info(source_material)
                    
                    for node_info in source_nodes_info:
                        new_node = target_material.node_tree.nodes.new(type='ShaderNodeTexImage')
                        new_node.name = node_info['name'] + "_copied"
                        new_node.image = node_info['image']
                        new_node.image.colorspace_settings.name = node_info['colorspace']
                        new_node.location = node_info['location']
                        self.report({'INFO'}, f"已为 '{target_obj.name}' 创建新贴图节点：'{new_node.name}'")
                        
                        for link_info in node_info['links']:
                            from_socket = new_node.outputs.get(link_info['from_socket_name'])
                            to_node = target_material.node_tree.nodes.get(link_info['to_node_name'])
                            
                            if from_socket and to_node:
                                to_socket = to_node.inputs.get(link_info['to_socket_name'])
                                if to_socket:
                                    try:
                                        target_material.node_tree.links.new(from_socket, to_socket)
                                    except Exception as e:
                                        self.report({'WARNING'}, f"警告: 无法连接节点 '{new_node.name}'。错误：{e}")

                    processed_objects.add(dup_obj)
                    self.report({'INFO'}, f"已完成 '{dup_obj.name}' 的贴图节点复制。")

        self.report({'INFO'}, "脚本运行完毕。")
        if processed_objects:
            self.report({'INFO'}, "请手动检查并删除已处理的模型。")
        else:
            self.report({'INFO'}, "没有找到需要复制贴图节点的重复模型。")
        
        return {'FINISHED'}

# --- 008 恢复原始材质 (去后缀) ---
class Y_OT_RestoreOriginalMaterials(bpy.types.Operator):
    bl_idname = "object.y_restore_original_materials"
    bl_label = "Restore Original Materials"
    bl_description = "Replaces materials with .00x suffix with original versions (if exist) and safely deletes unused duplicates."

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        import re
        
        selected_objects = context.selected_objects
        replaced_slots_count = 0
        potential_garbage = set()

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue
            
            for slot in obj.material_slots:
                mat = slot.material
                if not mat:
                    continue
                
                match = re.search(r'^(.+)(\.\d{3})$', mat.name)
                if match:
                    base_name = match.group(1)
                    original_mat = bpy.data.materials.get(base_name)
                    
                    if original_mat:
                        potential_garbage.add(mat)
                        slot.material = original_mat
                        replaced_slots_count += 1
        
        if replaced_slots_count == 0:
            self.report({'WARNING'}, "未找到可替换的后缀材质。")
            return {'CANCELLED'}

        deleted_count = 0
        kept_count = 0
        
        for mat in potential_garbage:
            if mat.users == 0:
                name = mat.name
                bpy.data.materials.remove(mat)
                deleted_count += 1
            else:
                kept_count += 1

        self.report({'INFO'}, f"操作完成：重置了 {replaced_slots_count} 个材质槽，清理了 {deleted_count} 个副本，保留了 {kept_count} 个仍被占用的副本。")
        return {'FINISHED'}


# --- 009 连接自发光加透贴 ---
class Y_OT_SetupEmissiveAlpha(bpy.types.Operator):
    bl_idname = "object.y_setup_emissive_alpha"
    bl_label = "Connect Emissive/Alpha"
    bl_description = "Connects the selected image texture node to the Principled BSDF's Emission and Alpha inputs."

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or not obj.active_material or not obj.active_material.use_nodes:
            return False
        
        for node in obj.active_material.node_tree.nodes:
            if node.select and node.type == 'TEX_IMAGE':
                return True
        return False

    def execute(self, context):
        try:
            obj = context.active_object
            material = obj.active_material
            
            image_node = None
            for node in material.node_tree.nodes:
                if node.select and node.type == 'TEX_IMAGE':
                    image_node = node
                    break
            
            if not image_node:
                self.report({'WARNING'}, "请在着色器编辑器中选中一个图像纹理节点。")
                return {'CANCELLED'}

            principled_bsdf_node = None
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_bsdf_node = node
                    break
            
            if not principled_bsdf_node:
                self.report({'WARNING'}, "未找到 Principled BSDF 节点，操作取消。")
                return {'CANCELLED'}
            
            if image_node.image:
                image_node.image.colorspace_settings.name = 'sRGB'
                self.report({'INFO'}, f"步骤 1：已将 '{image_node.name}' 的色彩空间设置为 'sRGB'。")
            
            if image_node.outputs.get('Color') and principled_bsdf_node.inputs.get('Emission'):
                try:
                    if principled_bsdf_node.inputs['Emission'].links:
                        for link in list(principled_bsdf_node.inputs['Emission'].links):
                            material.node_tree.links.remove(link)
                    
                    material.node_tree.links.new(image_node.outputs['Color'], principled_bsdf_node.inputs['Emission'])
                    self.report({'INFO'}, "步骤 2：已将图像纹理节点的颜色输出连接到 Principled BSDF 的自发光输入。")
                except Exception as e:
                    self.report({'WARNING'}, f"警告：连接颜色到自发光时发生错误：{e}")

            if image_node.outputs.get('Alpha') and principled_bsdf_node.inputs.get('Alpha'):
                try:
                    if principled_bsdf_node.inputs['Alpha'].links:
                        for link in list(principled_bsdf_node.inputs['Alpha'].links):
                            material.node_tree.links.remove(link)
                    
                    material.node_tree.links.new(image_node.outputs['Alpha'], principled_bsdf_node.inputs['Alpha'])
                    self.report({'INFO'}, "步骤 3：已将图像纹理节点的 Alpha 输出连接到 Principled BSDF 的 Alpha 输入。")
                except Exception as e:
                    self.report({'WARNING'}, f"警告：连接 Alpha 到 Alpha 时发生错误：{e}")
            
            self.report({'INFO'}, "所有操作完成！")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"错误：脚本运行时发生意外错误：{e}")
            return {'CANCELLED'}


# --- 010 常规一键连法线 ---
class Y_OT_SetupNormalMap(bpy.types.Operator):
    bl_idname = "object.y_setup_normal_map"
    bl_label = "Connect Normal Map"
    bl_description = "Sets up the selected image texture node as a normal map for Principled BSDF."

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or not obj.active_material or not obj.active_material.use_nodes:
            return False
        
        for node in obj.active_material.node_tree.nodes:
            if node.select and node.type == 'TEX_IMAGE':
                return True
        return False

    def execute(self, context):
        try:
            obj = context.active_object
            material = obj.active_material
            
            image_node = None
            for node in material.node_tree.nodes:
                if node.select and node.type == 'TEX_IMAGE':
                    image_node = node
                    break
            
            if not image_node:
                self.report({'WARNING'}, "请在着色器编辑器中选中一个图像纹理节点。")
                return {'CANCELLED'}
            
            if image_node.image:
                image_node.image.colorspace_settings.name = 'Non-Color'
                self.report({'INFO'}, f"步骤 1：已将 '{image_node.name}' 的色彩空间设置为 'Non-Color'。")
            
            normal_map_node = None
            for node in material.node_tree.nodes:
                if node.type == 'NORMAL_MAP':
                    normal_map_node = node
                    break
                    
            if not normal_map_node:
                normal_map_node = material.node_tree.nodes.new(type='ShaderNodeNormalMap')
                normal_map_node.location = image_node.location
                normal_map_node.location.x += 250
                self.report({'INFO'}, "步骤 2：已创建新的法线贴图节点。")
            else:
                self.report({'INFO'}, "步骤 2：已找到现有的法线贴图节点。")
            
            if image_node.outputs.get('Color'):
                try:
                    material.node_tree.links.new(
                        image_node.outputs['Color'], 
                        normal_map_node.inputs['Color']
                    )
                    self.report({'INFO'}, "步骤 3：已将图像纹理节点连接到法线贴图节。")
                except Exception as e:
                    self.report({'WARNING'}, f"警告：连接到法线贴图节点时发生错误：{e}")
            else:
                self.report({'WARNING'}, "警告：图像纹理节点没有颜色输出。操作取消。")
                return {'CANCELLED'}
            
            principled_bsdf_node = None
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_bsdf_node = node
                    break
                    
            if principled_bsdf_node:
                if principled_bsdf_node.inputs.get('Normal') and principled_bsdf_node.inputs['Normal'].links:
                    for link in list(principled_bsdf_node.inputs['Normal'].links):
                        material.node_tree.links.remove(link)
                        
                material.node_tree.links.new(
                    normal_map_node.outputs['Normal'],
                    principled_bsdf_node.inputs['Normal']
                )
                self.report({'INFO'}, "步骤 4：已将法线贴图连接到 Principled BSDF 着色器的法向输入。")
            else:
                self.report({'WARNING'}, "警告：未找到 Principled BSDF 节点，跳过法向连接。")

            self.report({'INFO'}, "所有操作完成！")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"错误：脚本运行时发生意外错误：{e}")
            return {'CANCELLED'}


# --- 011 选同材质模型 ---
class Y_OT_SelectSameMaterial(bpy.types.Operator):
    bl_idname = "object.y_select_same_material"
    bl_label = "Select Same Material"
    bl_description = "Selects all objects in the scene that have the exact same material list and order as the active object."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        active_obj = context.active_object
        
        if not active_obj:
            self.report({'WARNING'}, "没有选中的活动物体。")
            return {'CANCELLED'}

        active_materials = [slot.material for slot in active_obj.material_slots]
        
        if not active_materials:
            self.report({'WARNING'}, f"活动物体 '{active_obj.name}' 没有材质球。")
            return {'CANCELLED'}

        matching_objs = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            
            obj_materials = [slot.material for slot in obj.material_slots]
            
            if obj_materials == active_materials:
                matching_objs.append(obj)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in matching_objs:
            obj.select_set(True)
        
        context.view_layer.objects.active = active_obj

        self.report({'INFO'}, f"已选中 {len(matching_objs)} 个严格匹配的物体。")
        return {'FINISHED'}

# --- 012 根据图片尺寸重命名材质球 ---
class Y_OT_RenameByImageSize(bpy.types.Operator):
    bl_idname = "object.y_rename_by_image_size"
    bl_label = "Rename Materials by Image Size"
    bl_description = "Renames all materials based on the largest dimension of their connected Base Color texture."

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        import re
        
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            
            nodes = mat.node_tree.nodes
            
            bsdf_node = next(
                (n for n in nodes if n.type == 'BSDF_PRINCIPLED'),
                None
            )
            if not bsdf_node:
                continue
            
            base_color_input = bsdf_node.inputs.get('Base Color')
            if not base_color_input or not base_color_input.links:
                continue
            
            linked_node = base_color_input.links[0].from_node
            
            while linked_node and linked_node.type != 'TEX_IMAGE':
                if linked_node.inputs and linked_node.inputs[0].links:
                    linked_node = linked_node.inputs[0].links[0].from_node
                else:
                    linked_node = None
                    break
            
            if not linked_node or not linked_node.image:
                continue
            
            img = linked_node.image
            max_size = max(img.size[0], img.size[1])
            
            name = re.sub(r'^\d+_', '', mat.name)
            new_name = f"{max_size}_{name}"
            
            if new_name not in bpy.data.materials:
                mat.name = new_name
                self.report({'INFO'}, f"材质 '{mat.name}' 已重命名为 '{new_name}'。")
            else:
                self.report({'WARNING'}, f"警告：材质 '{mat.name}' 重命名冲突，跳过。")

        self.report({'INFO'}, "所有材质名称更新完成。")
        return {'FINISHED'}



# --- MMD 材质一键转标准 ---
class Y_OT_ConvertMmdMaterial(bpy.types.Operator):
    bl_idname = "object.y_convert_mmd_material"
    bl_label = "Convert MMD Material to Principled"
    bl_description = "Converts MMD shader nodes in selected objects' materials to Principled BSDF."

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        selected_objects = context.selected_objects

        materials_to_process = set()
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material:
                        materials_to_process.add(slot.material)

        if not materials_to_process:
            self.report({'WARNING'}, "在选中的网格物体上没有找到任何材质。")
            return {'CANCELLED'}

        self.report({'INFO'}, f"开始转换 {len(materials_to_process)} 个MMD材质...")

        for mat in materials_to_process:
            if not mat.use_nodes:
                continue

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            
            self.report({'INFO'}, f"正在处理材质: '{mat.name}'")

            mmd_shader_node = nodes.get("mmd_shader")
            if mmd_shader_node:
                for output in mmd_shader_node.outputs:
                    for link in list(output.links):
                        links.remove(link)
            
            principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            if mmd_shader_node:
                principled_node.location = mmd_shader_node.location
            
            base_tex_node = nodes.get("mmd_base_tex")
            if base_tex_node:
                links.new(base_tex_node.outputs['Color'], principled_node.inputs['Base Color'])
                links.new(base_tex_node.outputs['Alpha'], principled_node.inputs['Alpha'])

            output_node = next((node for node in nodes if node.type == 'OUTPUT_MATERIAL'), None)
            
            if output_node:
                if output_node.inputs['Surface'].links:
                    for link in list(output_node.inputs['Surface'].links):
                        links.remove(link)
                links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
        
        self.report({'INFO'}, "MMD材质转换完成。")
        return {'FINISHED'}


# --- 清理重复贴图节点 ---
class Y_OT_CleanDuplicateNodes(bpy.types.Operator):
    bl_idname = "object.y_clean_duplicate_nodes"
    bl_label = "Clean Duplicate Nodes"
    bl_description = "Cleans duplicate image texture nodes in selected object's materials."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        deleted_count = 0
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "Please select at least one object.")
            return {'CANCELLED'}

        processed_materials = set()
        for obj in selected_objects:
            if obj.type != 'MESH' and obj.type != 'LIGHT' and obj.type != 'CAMERA' and obj.type != 'EMPTY':
                continue
            for material_slot in obj.material_slots:
                material = material_slot.material
                if not material or not material.use_nodes or material in processed_materials:
                    continue
                try:
                    image_nodes_map = {}
                    nodes_to_delete = []
                    for node in list(material.node_tree.nodes):
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            image_path = node.image.filepath
                            has_links = any(link for output in node.outputs for link in output.links)
                            if image_path in image_nodes_map:
                                original_node, original_has_links = image_nodes_map[image_path]
                                if has_links and not original_has_links:
                                    nodes_to_delete.append(original_node)
                                    image_nodes_map[image_path] = (node, True)
                                else:
                                    nodes_to_delete.append(node)
                                self.report({'INFO'}, f"Found duplicate node: '{node.name}' in material '{material.name}'")
                            else:
                                image_nodes_map[image_path] = (node, has_links)
                    
                    if nodes_to_delete:
                        for node in nodes_to_delete:
                            original_node, _ = image_nodes_map.get(node.image.filepath)
                            if original_node:
                                for output_socket in node.outputs:
                                    for link in list(output_socket.links):
                                        original_output = original_node.outputs.get(output_socket.name)
                                        if original_output:
                                            try:
                                                material.node_tree.links.new(original_output, link.to_socket)
                                                material.node_tree.links.remove(link)
                                            except Exception as e:
                                                self.report({'WARNING'}, f"Failed to relink '{node.name}'. Error: {e}")
                                                material.node_tree.links.remove(link)
                        for node in nodes_to_delete:
                            try:
                                material.node_tree.nodes.remove(node)
                                deleted_count += 1
                            except Exception as e:
                                self.report({'WARNING'}, f"Failed to delete node '{node.name}'. Error: {e}")
                finally:
                    processed_materials.add(material)

        self.report({'INFO'}, f"Cleanup complete. Total {deleted_count} duplicate nodes deleted.")
        return {'FINISHED'}


# --- 贴图节点连接 ---
class Y_OT_SetupPrincipled(bpy.types.Operator):
    bl_idname = "object.y_setup_principled"
    bl_label = "Setup Principled Shader"
    bl_description = "Connects selected image node to Principled BSDF."

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material and context.active_object.active_material.use_nodes:
            return any(node.select and node.type == 'TEX_IMAGE' for node in context.active_object.active_material.node_tree.nodes)
        return False

    def execute(self, context):
        obj = context.active_object
        material = obj.active_material
        image_node = None
        for node in material.node_tree.nodes:
            if node.select and node.type == 'TEX_IMAGE':
                image_node = node
                break
        
        principled_bsdf_node = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf_node = node
                break
        
        if not principled_bsdf_node:
            self.report({'WARNING'}, "Principled BSDF node not found.")
            return {'CANCELLED'}
        
        image_node.image.colorspace_settings.name = 'sRGB'
        
        if image_node.outputs.get('Color') and principled_bsdf_node.inputs.get('Base Color'):
            if principled_bsdf_node.inputs['Base Color'].links:
                material.node_tree.links.remove(principled_bsdf_node.inputs['Base Color'].links[0])
            material.node_tree.links.new(image_node.outputs['Color'], principled_bsdf_node.inputs['Base Color'])
        
        if image_node.outputs.get('Alpha') and principled_bsdf_node.inputs.get('Metallic'):
            if principled_bsdf_node.inputs['Metallic'].links:
                material.node_tree.links.remove(principled_bsdf_node.inputs['Metallic'].links[0])
            material.node_tree.links.new(image_node.outputs['Alpha'], principled_bsdf_node.inputs['Metallic'])

        invert_node = material.node_tree.nodes.new(type='ShaderNodeInvert')
        invert_node.location = (image_node.location.x + 300, image_node.location.y - 100)
        
        if image_node.outputs.get('Alpha') and invert_node.inputs.get('Color'):
            material.node_tree.links.new(image_node.outputs['Alpha'], invert_node.inputs['Color'])
        
        if invert_node.outputs.get('Color') and principled_bsdf_node.inputs.get('Roughness'):
            if principled_bsdf_node.inputs['Roughness'].links:
                material.node_tree.links.remove(principled_bsdf_node.inputs['Roughness'].links[0])
            material.node_tree.links.new(invert_node.outputs['Color'], principled_bsdf_node.inputs['Roughness'])

        self.report({'INFO'}, "Shader setup complete.")
        return {'FINISHED'}

# --- 顶点环减面 ---
class Y_OT_MergeVerticesToTarget(bpy.types.Operator):
    bl_idname = "mesh.y_merge_vertices_to_target"
    bl_label = "顶点环减面"
    bl_description = "将选定的顶点环合并到指定的数量"

    target_count: bpy.props.IntProperty(
        name="保留数量",
        description="希望最终保留的顶点数量",
        default=8,
        min=3
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def get_ordered_loop(self, bm, selected_verts):
        if not selected_verts:
            return None

        vert_map = {v.index: v for v in selected_verts}
        visited = set()
        
        start_vert = selected_verts[0]
        
        ordered_loop = [start_vert]
        visited.add(start_vert)

        current_vert = start_vert
        for _ in range(len(selected_verts) - 1):
            found_next = False
            for edge in current_vert.link_edges:
                next_vert = edge.other_vert(current_vert)
                if next_vert.index in vert_map and next_vert not in visited:
                    ordered_loop.append(next_vert)
                    visited.add(next_vert)
                    current_vert = next_vert
                    found_next = True
                    break
            if not found_next:
                return None
        
        is_closed = any(e.other_vert(start_vert) == current_vert for e in start_vert.link_edges)

        if len(ordered_loop) == len(selected_verts):
            return ordered_loop, is_closed
        return None, False

    def invoke(self, context, event):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        selected_verts = [v for v in bm.verts if v.select]
        initial_count = len(selected_verts)
        
        if initial_count < 4:
            self.report({'WARNING'}, "请至少选择4个顶点")
            return {'CANCELLED'}

        self.target_count = initial_count // 2
        
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()

        selected_verts = [v for v in bm.verts if v.select]
        initial_count = len(selected_verts)

        if self.target_count >= initial_count:
            self.report({'INFO'}, "目标数量不小于当前数量，无需操作")
            return {'CANCELLED'}

        ordered_verts, is_closed = self.get_ordered_loop(bm, selected_verts)

        if not ordered_verts:
            self.report({'WARNING'}, "选择的顶点不是一个连续的环")
            return {'CANCELLED'}
        
        to_remove_count = initial_count - self.target_count
        step = initial_count / to_remove_count
        
        verts_to_merge = []
        accumulator = 0.0
        
        for i in range(1, len(ordered_verts)):
            accumulator += 1.0
            if accumulator >= step:
                verts_to_merge.append(ordered_verts[i])
                accumulator -= step
                if len(verts_to_merge) == to_remove_count:
                    break

        i = len(ordered_verts) - 1
        while len(verts_to_merge) < to_remove_count and i > 0:
            if ordered_verts[i] not in verts_to_merge:
                verts_to_merge.append(ordered_verts[i])
            i -= 1

        for v in verts_to_merge:
            if v.is_valid:
                v_index = ordered_verts.index(v)
                if is_closed:
                    dest_vert = ordered_verts[v_index - 1]
                else:
                    if v_index > 0:
                         dest_vert = ordered_verts[v_index - 1]
                    else:
                        continue
                
                if dest_vert.is_valid:
                    bmesh.ops.pointmerge(bm, verts=[v, dest_vert], merge_co=dest_vert.co)

        bmesh.update_edit_mesh(me)
        return {'FINISHED'}

# ====================================================================================
# == 高级姿态镜像
# ====================================================================================

class Y_PoseMirrorSettings(bpy.types.PropertyGroup):
    mirror_location: bpy.props.BoolProperty(
        name="镜像位置",
        description="开启后，将同时镜像骨骼的位置。通常只为根骨骼或IK控制器开启",
        default=False
    )
    
    mirror_scheme: bpy.props.EnumProperty(
        name="镜像方案",
        description="选择镜像姿态的算法",
        items=[
            ('LOCAL', "局部旋转", "操作/指令镜像，最符合动画直觉，能正确处理复杂旋转 (推荐)"),
            ('WORLD', "世界原点", "空间镜像，用于确保最终姿态在空间中完美对称"),
            ('SIMPLE', "轴向翻转", "速度最快，但只适用于非常标准的骨架")
        ],
        default='LOCAL'
    )
    
    local_mirror_axes: bpy.props.EnumProperty(
        name="局部镜像轴",
        description="[仅局部旋转方案使用] 定义在骨骼自身空间中如何翻转旋转",
        items=[
            ('FLIP_Z', "翻转 Z 轴", '修复"前后颠倒"问题 (最常用)'),
            ('FLIP_Y', "翻转 Y 轴", "特殊情况使用"),
            ('FLIP_YZ', "翻转 YZ 轴", "相当于绕骨骼X轴旋转180度")
        ],
        default='FLIP_Z'
    )
    
    left_pattern: bpy.props.StringProperty(
        name="左侧标识",
        description="定义骨骼名称中代表左侧的部分 (例如: .L, _L, Left, L_)",
        default=".L"
    )
    
    right_pattern: bpy.props.StringProperty(
        name="右侧标识",
        description="定义骨骼名称中代表右侧的部分 (例如: .R, _R, Right, R_)",
        default=".R"
    )

# --- 姿态镜像操作符 ---
class Y_OT_MirrorPose(bpy.types.Operator):
    bl_idname = "pose.y_mirror_pose"
    bl_label = "镜像姿态 (高级)"
    bl_description = "根据UI面板中的高级设置镜像选中骨骼的姿态"
    
    @classmethod
    def poll(cls, context):
        return (context.object and
                context.object.type == 'ARMATURE' and
                context.mode == 'POSE')

    def execute(self, context):
        settings = context.scene.y_pose_mirror_settings
        
        if not context.selected_pose_bones:
            self.report({'WARNING'}, "请至少选择一个骨骼来进行镜像")
            return {'CANCELLED'}
            
        if not settings.left_pattern or not settings.right_pattern:
            self.report({'ERROR'}, "左右标识符不能为空，请在UI面板中设置")
            return {'CANCELLED'}

        armature_obj = context.object
        all_pose_bones = armature_obj.pose.bones
        selected_pose_bones = context.selected_pose_bones[:]  

        mirrored_count = 0
        self.report({'INFO'}, f"镜像方案: {settings.mirror_scheme}, 镜像位置: {settings.mirror_location}")
        
        mirror_matrix_x_reflection = Matrix.Scale(-1, 4, (1, 0, 0))

        for source_bone in selected_pose_bones:
            source_name = source_bone.name
            target_name = ""
            
            if source_name.endswith(settings.left_pattern):
                target_name = source_name[:-len(settings.left_pattern)] + settings.right_pattern
            elif source_name.endswith(settings.right_pattern):
                target_name = source_name[:-len(settings.right_pattern)] + settings.left_pattern
            elif source_name.startswith(settings.left_pattern):
                target_name = settings.right_pattern + source_name[len(settings.left_pattern):]
            elif source_name.startswith(settings.right_pattern):
                target_name = settings.left_pattern + source_name[len(settings.right_pattern):]
            else:
                continue

            target_bone = all_pose_bones.get(target_name)

            if target_bone and target_bone != source_bone:
                mirrored_count += 1
                
                if settings.mirror_scheme == 'SIMPLE':
                    if settings.mirror_location:
                        loc = source_bone.location.copy()
                        loc.x = -loc.x
                        target_bone.location = loc
                    
                    if source_bone.rotation_mode == 'QUATERNION':
                        q = source_bone.rotation_quaternion.copy()
                        target_bone.rotation_quaternion = (q.w, q.x, -q.y, -q.z)
                    else:
                        e = source_bone.rotation_euler.copy()
                        target_bone.rotation_euler = (e.x, -e.y, -e.z)
                    
                    target_bone.scale = source_bone.scale.copy()
                    continue

                elif settings.mirror_scheme == 'LOCAL':
                    if settings.local_mirror_axes == 'FLIP_YZ':
                        local_mirror_transform = Matrix.Rotation(math.pi, 4, 'X')
                    elif settings.local_mirror_axes == 'FLIP_Y':
                        local_mirror_transform = Matrix(((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
                    else:
                        local_mirror_transform = Matrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))
                    
                    source_pose_matrix = source_bone.matrix_basis.copy()
                    target_pose_matrix = local_mirror_transform @ source_pose_matrix @ local_mirror_transform
                    _loc, mirrored_rot, mirrored_scale = target_pose_matrix.decompose()

                    if settings.mirror_location:
                        target_bone.location = _loc
                    target_bone.rotation_quaternion = mirrored_rot
                    target_bone.scale = mirrored_scale
                    continue

                elif settings.mirror_scheme == 'WORLD':
                    arm_mat = armature_obj.matrix_world
                    source_mat_world = arm_mat @ source_bone.matrix
                    mirrored_mat_world = mirror_matrix_x_reflection @ source_mat_world @ mirror_matrix_x_reflection
                    final_target_matrix_in_armature_space = arm_mat.inverted() @ mirrored_mat_world
                    
                    if target_bone.parent:
                        pose_matrix = target_bone.parent.matrix.inverted() @ final_target_matrix_in_armature_space
                    else:
                        pose_matrix = final_target_matrix_in_armature_space
                    
                    mirrored_loc, mirrored_rot, mirrored_scale = pose_matrix.decompose()

                    if settings.mirror_location:
                        target_bone.location = mirrored_loc
                    target_bone.rotation_quaternion = mirrored_rot
                    target_bone.scale = mirrored_scale

        if mirrored_count > 0:
            self.report({'INFO'}, f"成功镜像了 {mirrored_count} 个骨骼的姿态。")
        else:
            self.report({'WARNING'}, "未找到匹配骨骼，请检查命名规则和所选骨骼")
        
        context.view_layer.update()
        return {'FINISHED'}


# --- 插件面板 UI ---
class Y_PT_Panel(bpy.types.Panel):
    bl_label = "模型整理工具集"
    bl_idname = "Y_PT_Y_TOOLS"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'GeneralTools'

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text="通用工具：")
        row = layout.row()
        row.operator(Y_OT_DeleteObjectsWithoutMaterials.bl_idname, text="001删除无材质球的模型")
        row = layout.row()
        row.operator(Y_OT_RenameByMaterial.bl_idname, text="002按材质球重命名模型")
        row = layout.row()
        row.operator(Y_OT_DeleteEmptyModels.bl_idname, text="003删除无图片节点模型")
        row = layout.row()
        row.operator(Y_OT_CleanDuplicatesAfterRename.bl_idname, text="004重命名之后清理重复模型")
        row = layout.row()
        row.operator(Y_OT_DeleteIdenticalSelected.bl_idname, text="005从选中中删除相同的模型")
        row = layout.row()
        row.operator(Y_OT_CopyNodesToFirst.bl_idname, text="007节点复制到最前面的模型")

        row = layout.row()
        row.label(text="材质工具：")

        row = layout.row()
        row.operator(Y_OT_SelectSameTexture.bl_idname, text="006选同贴图模型")

        row = layout.row()
        row.operator(Y_OT_RestoreOriginalMaterials.bl_idname, text="008恢复原始材质(去后缀)")

        row = layout.row()
        row.operator(Y_OT_SelectSameMaterial.bl_idname, text="011选同材质模型")

        row = layout.row()
        row.operator(Y_OT_RenameByImageSize.bl_idname, text="012根据图片尺寸重命名材质球")
        
        row = layout.row()
        row.operator(Y_OT_ConvertMmdMaterial.bl_idname, text="MMD材质一键转标准")

        row = layout.row()
        row.operator(Y_OT_CleanDuplicateNodes.bl_idname, text="清理重复贴图节点")
        
        row = layout.row()
        row.operator(Y_OT_SetupPrincipled.bl_idname, text="连接基础色金属度粗糙度")

        row = layout.row()
        row.operator(Y_OT_SetupEmissiveAlpha.bl_idname, text="连接自发光加透贴")

        row = layout.row()
        row.operator(Y_OT_SetupNormalMap.bl_idname, text="常规一键连法线")

        # 编辑模式工具
        box = layout.box()
        box.label(text="编辑模式工具：")
        col = box.column(align=True)
        col.enabled = (context.mode == 'EDIT_MESH')
        col.operator(Y_OT_MergeVerticesToTarget.bl_idname, text="顶点环减面")

        # 姿态/骨架工具
        box = layout.box()
        box.label(text="姿态/骨架工具:")
        col = box.column(align=True)
        col.enabled = context.mode == 'POSE'

        settings = context.scene.y_pose_mirror_settings
        
        col.prop(settings, "mirror_location")
        col.separator()

        col.prop(settings, "mirror_scheme", expand=True)
        
        if settings.mirror_scheme == 'LOCAL':
            sub_box = col.box()
            sub_box.prop(settings, "local_mirror_axes", expand=True)

        col.separator()
        
        split = col.split(factor=0.5, align=True)
        split.prop(settings, "left_pattern", text="左")
        split.prop(settings, "right_pattern", text="右")
        
        col.operator(Y_OT_MirrorPose.bl_idname, text="镜像选中骨骼姿态", icon='MOD_MIRROR')


classes = (
    Y_OT_DeleteObjectsWithoutMaterials,
    Y_PoseMirrorSettings,
    Y_OT_RenameByMaterial,
    Y_OT_DeleteEmptyModels,
    Y_OT_CleanDuplicatesAfterRename,
    Y_OT_DeleteIdenticalSelected,
    Y_OT_SelectSameTexture,
    Y_OT_CopyNodesToFirst,
    Y_OT_RestoreOriginalMaterials,
    Y_OT_SetupEmissiveAlpha,
    Y_OT_SetupNormalMap,
    Y_OT_SelectSameMaterial,
    Y_OT_RenameByImageSize,
    Y_OT_ConvertMmdMaterial,
    Y_OT_CleanDuplicateNodes,
    Y_OT_SetupPrincipled,
    Y_OT_MergeVerticesToTarget,
    Y_OT_MirrorPose,
    Y_PT_Panel
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.y_pose_mirror_settings = bpy.props.PointerProperty(type=Y_PoseMirrorSettings)


def unregister():
    del bpy.types.Scene.y_pose_mirror_settings
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
