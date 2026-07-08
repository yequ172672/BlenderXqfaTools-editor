# type: ignore
import math
import uuid
import random
import bpy
import bmesh
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatVectorProperty,
    CollectionProperty,
    PointerProperty,
)
from bpy.types import PropertyGroup


class FaceColorManager:
    """面颜色管理器：持有所有面颜色相关的常量与逻辑"""
    UNSET_SLOT = -1
    DEFAULT_COLOR = (0.0, 0.0, 0.0, 1.0)
    ATTR_SLOT = 'layer_vertex_slot'
    ATTR_COLOR = 'layer_vertex_color'

    _pending = {}  # ball_hash → color
    _timer = None

    @staticmethod
    def _do_sync(ball_hash, color):
        """执行实际的网格颜色同步"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            mesh = obj.data
            slot_attr = mesh.attributes.get(attr_slot)
            color_attr = mesh.attributes.get(attr_color)
            if slot_attr is None or color_attr is None:
                continue

            # 收集引用该球的槽索引集合
            data = obj.layer_vertex_colors
            matching = set()
            for i, slot in enumerate(data.slots):
                if slot.ball_hash == ball_hash:
                    matching.add(i)
            if not matching:
                continue

            if obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(mesh)
                slot_layer = bm.loops.layers.int.get(attr_slot)
                color_layer = bm.loops.layers.color.get(attr_color)
                if slot_layer is not None and color_layer is not None:
                    for f in bm.faces:
                        for loop in f.loops:
                            if loop[slot_layer] in matching:
                                loop[color_layer] = color
                    bmesh.update_edit_mesh(mesh)
            else:
                for i in range(len(mesh.loops)):
                    if slot_attr.data[i].value in matching:
                        color_attr.data[i].color = color

    @staticmethod
    def _flush_pending():
        """定时器回调：批量执行所有积压的颜色更新"""
        pending = dict(FaceColorManager._pending)
        FaceColorManager._pending.clear()
        FaceColorManager._timer = None
        for ball_hash, color in pending.items():
            FaceColorManager._do_sync(ball_hash, color)
        for area in bpy.context.screen.areas:
            area.tag_redraw()

    # ---- 工具方法：根据全局球哈希查找球 ----

    @staticmethod
    def find_global_ball(ball_hash):
        """在场景的全局颜色球列表中按 hash_val 查找"""
        for ball in bpy.context.scene.xqfa_color_balls:
            if ball.hash_val == ball_hash:
                return ball
        return None

    @staticmethod
    def get_ball_color(ball_hash):
        """获取全局球的颜色，找不到则返回默认色"""
        ball = FaceColorManager.find_global_ball(ball_hash)
        return ball.color if ball else FaceColorManager.DEFAULT_COLOR

    # ---- 全局球变化 → 同步网格 ----

    @staticmethod
    def on_ball_color_update(ball, context=None):
        """颜色变化时延迟合并执行，避免拖动色盘时高频触发"""
        FaceColorManager._pending[ball.hash_val] = ball.color
        if FaceColorManager._timer is None:
            FaceColorManager._timer = bpy.app.timers.register(
                FaceColorManager._flush_pending, first_interval=0.05)

    @staticmethod
    def ensure_attrs_object(mesh):
        """确保网格存在面颜色属性（对象模式）"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        if mesh.attributes.get(attr_slot) is None:
            attr = mesh.attributes.new(attr_slot, 'INT', 'CORNER')
            for i in range(len(mesh.loops)):
                attr.data[i].value = FaceColorManager.UNSET_SLOT
        if mesh.attributes.get(attr_color) is None:
            mesh.attributes.new(attr_color, 'BYTE_COLOR', 'CORNER')

    @staticmethod
    def ensure_attrs_edit(bm):
        """确保 bmesh 存在面颜色属性层（编辑模式）"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        slot_layer = bm.loops.layers.int.get(attr_slot)
        if slot_layer is None:
            slot_layer = bm.loops.layers.int.new(attr_slot)
            for f in bm.faces:
                for loop in f.loops:
                    loop[slot_layer] = FaceColorManager.UNSET_SLOT
        color_layer = bm.loops.layers.color.get(attr_color)
        if color_layer is None:
            color_layer = bm.loops.layers.color.new(attr_color)
            for f in bm.faces:
                for loop in f.loops:
                    loop[color_layer] = FaceColorManager.DEFAULT_COLOR
        return slot_layer, color_layer

    # ---- 指定 / 取消指定 ----

    @staticmethod
    def set_face_color_for_object(obj, slot_idx, color):
        """将指定物体选中面的所有面拐写入给定的槽索引与颜色"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        mesh = obj.data
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer, color_layer = FaceColorManager.ensure_attrs_edit(bm)
            for f in bm.faces:
                if f.select:
                    for loop in f.loops:
                        loop[slot_layer] = slot_idx
                        loop[color_layer] = color
            bmesh.update_edit_mesh(mesh)
        else:
            FaceColorManager.ensure_attrs_object(mesh)
            slot_attr = mesh.attributes[attr_slot]
            color_attr = mesh.attributes[attr_color]
            for poly in mesh.polygons:
                if poly.select:
                    for loop_idx in poly.loop_indices:
                        slot_attr.data[loop_idx].value = slot_idx
                        color_attr.data[loop_idx].color = color

    @staticmethod
    def set_face_color_for_selected(context, slot_idx, color):
        """将选中物体的选中面的所有面拐指定到给定槽索引（按 selected_objects 遍历）"""
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            FaceColorManager.set_face_color_for_object(obj, slot_idx, color)

    # ---- 选择 / 弃选 ----

    @staticmethod
    def select_faces_by_slot_for_object(obj, slot_idx, select):
        """选择或弃选指定物体中属于给定槽索引的面"""
        attr_slot = FaceColorManager.ATTR_SLOT
        mesh = obj.data
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            if slot_layer is not None:
                for f in bm.faces:
                    match = False
                    for loop in f.loops:
                        if loop[slot_layer] == slot_idx:
                            match = True
                            break
                    if match:
                        f.select = select
            bm.select_flush_mode()
            bmesh.update_edit_mesh(mesh)
        else:
            slot_attr = mesh.attributes.get(attr_slot)
            if slot_attr is None:
                return
            loop_to_poly = [0] * len(mesh.loops)
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    loop_to_poly[loop_idx] = poly.index
            matched_faces = set()
            for i in range(len(mesh.loops)):
                if slot_attr.data[i].value == slot_idx:
                    matched_faces.add(loop_to_poly[i])
            for fi in matched_faces:
                mesh.polygons[fi].select = select

    @staticmethod
    def select_faces_by_slot(context, slot_idx, select):
        """选择或弃选属于指定槽索引的面（按 selected_objects 遍历）"""
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            FaceColorManager.select_faces_by_slot_for_object(obj, slot_idx, select)

    # ---- 删除槽时的数据清理 ----

    @staticmethod
    def remove_slot_cleanup_mesh(obj, removed_idx):
        """删除槽 removed_idx 后清理网格数据：将该索引的面拐归为未设置，大于该索引的递减"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            color_layer = bm.loops.layers.color.get(attr_color)
            if slot_layer is not None and color_layer is not None:
                for f in bm.faces:
                    for loop in f.loops:
                        val = loop[slot_layer]
                        if val == removed_idx:
                            loop[slot_layer] = FaceColorManager.UNSET_SLOT
                            loop[color_layer] = FaceColorManager.DEFAULT_COLOR
                        elif val > removed_idx:
                            loop[slot_layer] = val - 1
                bmesh.update_edit_mesh(mesh)
        else:
            slot_attr = mesh.attributes.get(attr_slot)
            color_attr = mesh.attributes.get(attr_color)
            if slot_attr is None or color_attr is None:
                return
            for i in range(len(mesh.loops)):
                val = slot_attr.data[i].value
                if val == removed_idx:
                    slot_attr.data[i].value = FaceColorManager.UNSET_SLOT
                    color_attr.data[i].color = FaceColorManager.DEFAULT_COLOR
                elif val > removed_idx:
                    slot_attr.data[i].value = val - 1

    @staticmethod
    def sync_color_for_slot(obj, slot_idx):
        """将调用全局球的颜色同步到所有该槽索引的面拐"""
        data = obj.layer_vertex_colors
        if slot_idx < 0 or slot_idx >= len(data.slots):
            return
        ball_hash = data.slots[slot_idx].ball_hash
        color = FaceColorManager.get_ball_color(ball_hash)
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            color_layer = bm.loops.layers.color.get(attr_color)
            if slot_layer is not None and color_layer is not None:
                for f in bm.faces:
                    for loop in f.loops:
                        if loop[slot_layer] == slot_idx:
                            loop[color_layer] = color
                bmesh.update_edit_mesh(mesh)
        else:
            slot_attr = mesh.attributes.get(attr_slot)
            color_attr = mesh.attributes.get(attr_color)
            if slot_attr is None or color_attr is None:
                return
            for i in range(len(mesh.loops)):
                if slot_attr.data[i].value == slot_idx:
                    color_attr.data[i].color = color

    @staticmethod
    def rebuild_from_mesh(obj):
        """从网格的面拐颜色重建物体槽位数据（合并物体后恢复用）"""
        attr_slot = FaceColorManager.ATTR_SLOT
        attr_color = FaceColorManager.ATTR_COLOR
        mesh = obj.data
        slot_attr = mesh.attributes.get(attr_slot)
        color_attr = mesh.attributes.get(attr_color)
        if slot_attr is None or color_attr is None:
            return 0

        # 收集唯一颜色 → 找或建全局球
        mesh_colors = []  # [(float_color, int_key), ...] 按出现顺序
        seen_keys = set()
        balls = bpy.context.scene.xqfa_color_balls

        def _to_key(c):
            return (int(round(c[0] * 255)), int(round(c[1] * 255)),
                    int(round(c[2] * 255)), int(round(c[3] * 255)))

        # 预建已有球的 key → ball 索引（只读，不反复遍历 CollectionProperty）
        key_to_ball = {}
        for ball in balls:
            k = _to_key(ball.color)
            if k not in key_to_ball:
                key_to_ball[k] = ball

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            color_layer = bm.loops.layers.color.get(attr_color)
            if slot_layer is None or color_layer is None:
                return 0
            for f in bm.faces:
                for loop in f.loops:
                    if loop[slot_layer] == FaceColorManager.UNSET_SLOT:
                        continue
                    c = loop[color_layer]
                    k = _to_key(c)
                    if k not in seen_keys:
                        seen_keys.add(k)
                        mesh_colors.append((c, k))

            data = obj.layer_vertex_colors
            data.slots.clear()
            key_to_idx = {}
            for idx, (c, k) in enumerate(mesh_colors):
                ball = key_to_ball.get(k)
                if ball is None:
                    ball = balls.add()
                    ball.name = f"Color.{len(balls) + 1:03d}"
                    ball.hash_val = uuid.uuid4().hex
                    ball.color = c
                    key_to_ball[k] = ball
                slot = data.slots.add()
                slot.ball_hash = ball.hash_val
                key_to_idx[k] = idx

            # 重映射面拐 INT 索引
            for f in bm.faces:
                for loop in f.loops:
                    if loop[slot_layer] == FaceColorManager.UNSET_SLOT:
                        continue
                    k = _to_key(loop[color_layer])
                    loop[slot_layer] = key_to_idx.get(k, FaceColorManager.UNSET_SLOT)
            bmesh.update_edit_mesh(mesh)
        else:
            for i in range(len(mesh.loops)):
                if slot_attr.data[i].value == FaceColorManager.UNSET_SLOT:
                    continue
                c = color_attr.data[i].color
                k = _to_key(c)
                if k not in seen_keys:
                    seen_keys.add(k)
                    mesh_colors.append((c, k))

            data = obj.layer_vertex_colors
            data.slots.clear()
            key_to_idx = {}
            for idx, (c, k) in enumerate(mesh_colors):
                ball = key_to_ball.get(k)
                if ball is None:
                    ball = balls.add()
                    ball.name = f"Color.{len(balls) + 1:03d}"
                    ball.hash_val = uuid.uuid4().hex
                    ball.color = c
                    key_to_ball[k] = ball
                slot = data.slots.add()
                slot.ball_hash = ball.hash_val
                key_to_idx[k] = idx

            for i in range(len(mesh.loops)):
                if slot_attr.data[i].value == FaceColorManager.UNSET_SLOT:
                    continue
                k = _to_key(color_attr.data[i].color)
                slot_attr.data[i].value = key_to_idx.get(k, FaceColorManager.UNSET_SLOT)

        data.active_index = 0 if len(data.slots) > 0 else -1
        return len(data.slots)


##########################
# Property Groups
##########################

class FaceColorBall(PropertyGroup):
    """全局颜色球 —— 跨物体共享的颜色定义"""
    hash_val: StringProperty(
        name="哈希值",
        default="",
        description="唯一标识符",
    )
    color: FloatVectorProperty(
        name="颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.5, 0.5, 0.5, 1.0),
        update=lambda self, ctx: FaceColorManager.on_ball_color_update(self, ctx),
    )


class LayerVertexColorSlot(PropertyGroup):
    """物体上的一个颜色槽位，引用一个全局颜色球"""
    ball_hash: StringProperty(
        name="球哈希",
        default="",
        description="关联到的全局颜色球哈希值",
    )


class LayerVertexColorData(PropertyGroup):
    """物体上的分层顶点色数据容器"""
    slots: CollectionProperty(type=LayerVertexColorSlot)
    active_index: IntProperty(default=-1, min=-1)


##########################
# UI Lists
##########################

class XQFA_UL_GlobalColorBalls(bpy.types.UIList):
    """全局颜色球列表"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon='COLOR')
            row.prop(item, "color", text="")
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, "color", text="")


class XQFA_UL_LayerVertexColorSlots(bpy.types.UIList):
    """物体分层顶点色槽位列表 —— [▼] 图标 | 名称 | 色块 或 [▼] 新建"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type not in {'DEFAULT', 'COMPACT'}:
            return
        slot_item = item
        ball = FaceColorManager.find_global_ball(slot_item.ball_hash)
        slot_idx = self._get_slot_index(data, slot_item)

        row = layout.row(align=True)
        op = row.operator("xqfa.slot_pick_ball", text="", icon='COLOR', emboss=False)
        op.slot_index = slot_idx

        if ball:
            row.prop(ball, "name", text="", emboss=False)
            row.prop(ball, "color", text="")
            op = row.operator("xqfa.slot_clear_ball", text="", icon='X', emboss=False)
            op.slot_index = slot_idx
        else:
            op = row.operator("xqfa.slot_new_ball", text="新建", icon='ADD')
            op.slot_index = slot_idx

    @staticmethod
    def _get_slot_index(data, item):
        for i, s in enumerate(data.slots):
            if s == item:
                return i
        return -1


##########################
# Operators —— 全局颜色球
##########################

class XQFA_OT_GlobalBallAdd(bpy.types.Operator):
    """添加一个新的全局颜色球"""
    bl_idname = "xqfa.global_ball_add"
    bl_label = "添加颜色球"
    bl_description = "创建一个新的全局颜色球"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def _generate_unique_name(balls, base="Color"):
        existing = {b.name for b in balls}
        if base not in existing:
            return base
        for i in range(1, 1000):
            name = f"{base}.{i:03d}"
            if name not in existing:
                return name
        return f"{base}.001"

    def execute(self, context):
        balls = context.scene.xqfa_color_balls
        ball = balls.add()
        ball.name = self._generate_unique_name(balls)
        ball.hash_val = uuid.uuid4().hex
        ball.color = (1.0, 1.0, 1.0, 1.0)
        context.scene.xqfa_color_balls_active_index = len(balls) - 1
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已添加全局颜色球 '{ball.name}'")
        return {'FINISHED'}


class XQFA_OT_GlobalBallRemove(bpy.types.Operator):
    """删除当前选中的全局颜色球"""
    bl_idname = "xqfa.global_ball_remove"
    bl_label = "删除颜色球"
    bl_description = "删除当前全局颜色球，所有引用该球的槽位将被清空"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        balls = context.scene.xqfa_color_balls
        idx = context.scene.xqfa_color_balls_active_index
        return len(balls) > 0 and 0 <= idx < len(balls)

    def execute(self, context):
        balls = context.scene.xqfa_color_balls
        idx = context.scene.xqfa_color_balls_active_index
        if idx < 0 or idx >= len(balls):
            return {'CANCELLED'}

        ball_hash = balls[idx].hash_val
        ball_name = balls[idx].name

        # 清空所有引用了该球的物体槽位
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for slot in obj.layer_vertex_colors.slots:
                if slot.ball_hash == ball_hash:
                    slot.ball_hash = ""

        balls.remove(idx)
        if len(balls) > 0:
            context.scene.xqfa_color_balls_active_index = min(idx, len(balls) - 1)
        else:
            context.scene.xqfa_color_balls_active_index = -1

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已删除全局颜色球 '{ball_name}'")
        return {'FINISHED'}


class XQFA_OT_GlobalBallRemoveByHash(bpy.types.Operator):
    """按哈希值删除全局颜色球"""
    bl_idname = "xqfa.global_ball_remove_by_hash"
    bl_label = "删除"
    bl_description = "删除该全局颜色球，所有引用该球的槽位将被清空"
    bl_options = {'REGISTER', 'UNDO'}

    ball_hash: StringProperty(default="")

    def execute(self, context):
        balls = context.scene.xqfa_color_balls
        for idx, ball in enumerate(balls):
            if ball.hash_val == self.ball_hash:
                # 清空所有引用了该球的物体槽位
                for obj in bpy.data.objects:
                    if obj.type != 'MESH':
                        continue
                    for slot in obj.layer_vertex_colors.slots:
                        if slot.ball_hash == self.ball_hash:
                            slot.ball_hash = ""
                balls.remove(idx)
                if len(balls) > 0:
                    context.scene.xqfa_color_balls_active_index = min(idx, len(balls) - 1)
                else:
                    context.scene.xqfa_color_balls_active_index = -1
                for area in context.screen.areas:
                    area.tag_redraw()
                return {'FINISHED'}
        return {'CANCELLED'}


##########################
# Operators —— 物体槽位
##########################

class XQFA_OT_FaceColorSlotAdd(bpy.types.Operator):
    """为当前物体添加一个空槽位"""
    bl_idname = "xqfa.face_color_slot_add"
    bl_label = "添加槽位"
    bl_description = "为当前物体添加一个空的分层顶点色槽位"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH')

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        data.slots.add()
        data.active_index = len(data.slots) - 1
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class XQFA_OT_FaceColorSlotRemove(bpy.types.Operator):
    """删除当前选中的物体颜色槽位"""
    bl_idname = "xqfa.face_color_slot_remove"
    bl_label = "删除槽位"
    bl_description = "删除当前槽位并清理网格数据（高索引自动递减）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        data = obj.layer_vertex_colors
        return len(data.slots) > 0 and 0 <= data.active_index < len(data.slots)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = data.active_index

        if idx < 0 or idx >= len(data.slots):
            self.report({'ERROR'}, "无效的槽位索引")
            return {'CANCELLED'}

        FaceColorManager.remove_slot_cleanup_mesh(obj, idx)
        data.slots.remove(idx)

        if len(data.slots) > 0:
            data.active_index = min(idx, len(data.slots) - 1)
        else:
            data.active_index = -1

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已删除槽位 {idx}")
        return {'FINISHED'}


class XQFA_OT_FaceColorSlotMove(bpy.types.Operator):
    """在列表中上移或下移槽位（同步更新网格数据中的槽索引）"""
    bl_idname = "xqfa.face_color_slot_move"
    bl_label = "移动槽位"
    bl_description = "移动当前槽位的位置"
    bl_options = {'REGISTER', 'UNDO'}

    direction: StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        data = obj.layer_vertex_colors
        return len(data.slots) > 1 and 0 <= data.active_index < len(data.slots)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = data.active_index
        target = idx - 1 if self.direction == 'UP' else idx + 1
        if target < 0 or target >= len(data.slots):
            return {'CANCELLED'}

        # 交换 slots
        data.slots.move(idx, target)
        data.active_index = target

        # 同步网格中的 INT 索引：idx ↔ target
        attr_slot = FaceColorManager.ATTR_SLOT
        mesh = obj.data
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            if slot_layer is not None:
                for f in bm.faces:
                    for loop in f.loops:
                        val = loop[slot_layer]
                        if val == idx:
                            loop[slot_layer] = target
                        elif val == target:
                            loop[slot_layer] = idx
                bmesh.update_edit_mesh(mesh)
        else:
            slot_attr = mesh.attributes.get(attr_slot)
            if slot_attr is not None:
                for i in range(len(mesh.loops)):
                    val = slot_attr.data[i].value
                    if val == idx:
                        slot_attr.data[i].value = target
                    elif val == target:
                        slot_attr.data[i].value = idx

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


##########################
# Operator —— 清理
##########################

class XQFA_OT_CleanupUnusedBalls(bpy.types.Operator):
    """清理没有被任何槽位引用的全局颜色球"""
    bl_idname = "xqfa.cleanup_unused_balls"
    bl_label = "清理未使用颜色"
    bl_description = "删除所有未被引用的全局颜色球"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 收集所有被引用的 ball_hash
        used_hashes = set()
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for slot in obj.layer_vertex_colors.slots:
                if slot.ball_hash:
                    used_hashes.add(slot.ball_hash)

        balls = context.scene.xqfa_color_balls
        removed_count = 0
        # 从后往前删除，避免索引偏移
        for i in range(len(balls) - 1, -1, -1):
            if balls[i].hash_val not in used_hashes:
                balls.remove(i)
                removed_count += 1

        if len(balls) > 0:
            context.scene.xqfa_color_balls_active_index = min(
                context.scene.xqfa_color_balls_active_index, len(balls) - 1)
        else:
            context.scene.xqfa_color_balls_active_index = -1

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"清理了 {removed_count} 个未使用的颜色球")
        return {'FINISHED'}


class XQFA_OT_RebuildSlotData(bpy.types.Operator):
    """从网格属性重建物体槽位数据（合并物体后恢复）"""
    bl_idname = "xqfa.rebuild_slot_data"
    bl_label = "重建槽位数据"
    bl_description = "从网格 layer_vertex_slot 属性重建物体的槽位列表"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        needed = FaceColorManager.rebuild_from_mesh(obj)
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已重建槽位数据（共 {needed} 个槽位）")
        return {'FINISHED'}


class XQFA_OT_AddSlotsFromVertexGroups(bpy.types.Operator):
    """从活动顶点组创建槽位"""
    bl_idname = "xqfa.add_slots_from_vgroups"
    bl_label = "从活动顶点组添加"
    bl_description = "从当前活动的顶点组创建一个槽位"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        vg = obj.vertex_groups.active if (obj and obj.type == 'MESH') else None
        return vg is not None

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        balls = context.scene.xqfa_color_balls
        vg = obj.vertex_groups.active

        ball = balls.add()
        ball.name = vg.name
        ball.hash_val = uuid.uuid4().hex
        slot = data.slots.add()
        slot.ball_hash = ball.hash_val
        data.active_index = len(data.slots) - 1
        slot_idx = data.active_index

        # 切换到编辑模式，选中顶点组并指定槽索引
        prev_mode = obj.mode
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        obj.vertex_groups.active_index = vg.index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.select_mode(type='FACE')

        # 先写入槽索引（用默认色），颜色球颜色随后设置触发全局同步
        FaceColorManager.set_face_color_for_object(obj, slot_idx, FaceColorManager.DEFAULT_COLOR)

        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)

        # 最后设置颜色 → 触发 on_ball_color_update 同步所有网格
        ball.color = _hcl_to_rgba(
            random.uniform(0, 360), random.uniform(30, 80), random.uniform(35, 75))

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已从顶点组 '{vg.name}' 创建槽位并指定")
        return {'FINISHED'}


class XQFA_OT_AddSlotsFromMaterials(bpy.types.Operator):
    """从活动材质槽创建槽位"""
    bl_idname = "xqfa.add_slots_from_materials"
    bl_label = "从活动材质添加"
    bl_description = "从当前活动的材质创建槽位并指定对应面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        idx = obj.active_material_index
        return 0 <= idx < len(obj.material_slots)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        balls = context.scene.xqfa_color_balls
        idx = obj.active_material_index
        mat_slot = obj.material_slots[idx]
        mat = mat_slot.material

        ball = balls.add()
        ball.name = mat.name if mat else f"Material.{idx + 1:03d}"
        ball.hash_val = uuid.uuid4().hex
        slot = data.slots.add()
        slot.ball_hash = ball.hash_val
        data.active_index = len(data.slots) - 1
        slot_idx = data.active_index

        # 切换到编辑模式，选中该材质的面并指定槽索引
        prev_mode = obj.mode
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        obj.active_material_index = idx
        bpy.ops.object.material_slot_select()

        FaceColorManager.set_face_color_for_object(obj, slot_idx, FaceColorManager.DEFAULT_COLOR)

        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)

        # 最后设置颜色 → 触发 on_ball_color_update 同步所有网格
        ball.color = _hcl_to_rgba(
            random.uniform(0, 360), random.uniform(30, 80), random.uniform(35, 75))

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已从材质 '{ball.name}' 创建槽位并指定")
        return {'FINISHED'}


class XQFA_OT_SetByMaterial(bpy.types.Operator):
    """按材质分配给面指定槽位颜色"""
    bl_idname = "xqfa.set_by_material"
    bl_label = "按材质设置"
    bl_description = "按材质创建槽位并指定面，清空已有槽位"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        balls = context.scene.xqfa_color_balls

        # 清空现有槽位
        old_count = len(data.slots)
        for i in range(old_count - 1, -1, -1):
            FaceColorManager.remove_slot_cleanup_mesh(obj, i)
            data.slots.remove(i)

        # 按材质创建槽位（颜色随后统一设置）
        mat_count = len(obj.material_slots)
        if mat_count == 0:
            self.report({'WARNING'}, "物体没有材质槽")
            return {'CANCELLED'}

        for i, mat_slot in enumerate(obj.material_slots):
            mat = mat_slot.material
            ball = balls.add()
            ball.name = mat.name if mat else f"Material.{i + 1:03d}"
            ball.hash_val = uuid.uuid4().hex
            slot = data.slots.add()
            slot.ball_hash = ball.hash_val

        # 切换到编辑模式，只写入槽索引
        prev_mode = obj.mode
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        slot_layer = bm.loops.layers.int.get(FaceColorManager.ATTR_SLOT)
        color_layer = bm.loops.layers.color.get(FaceColorManager.ATTR_COLOR)
        if slot_layer is None or color_layer is None:
            slot_layer, color_layer = FaceColorManager.ensure_attrs_edit(bm)

        for f in bm.faces:
            idx = f.material_index
            if 0 <= idx < mat_count:
                for loop in f.loops:
                    loop[slot_layer] = idx
        bmesh.update_edit_mesh(mesh)

        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)

        # 生成颜色并设置 → 触发 on_ball_color_update 同步所有网格
        colors = _generate_distinct_colors(mat_count)
        new_balls = [b for b in balls[-mat_count:]]
        for ball, color in zip(new_balls, colors):
            ball.color = color

        data.active_index = 0
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已按 {mat_count} 个材质设置槽位")
        return {'FINISHED'}


class XQFA_OT_SetByLooseParts(bpy.types.Operator):
    """按松散块分配给面指定槽位颜色"""
    bl_idname = "xqfa.set_by_loose_parts"
    bl_label = "按松散块设置"
    bl_description = "按网格松散块创建槽位并指定面，清空已有槽位"
    bl_options = {'REGISTER', 'UNDO'}

    limit: IntProperty(
        name="数量限制",
        default=8,
        min=2,
        max=256,
        description="最大松散块数量，超出部分合并到最后一个槽位",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        balls = context.scene.xqfa_color_balls

        # 清空现有槽位
        old_count = len(data.slots)
        for i in range(old_count - 1, -1, -1):
            FaceColorManager.remove_slot_cleanup_mesh(obj, i)
            data.slots.remove(i)

        # 切换到编辑模式
        prev_mode = obj.mode
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # 松散块
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        islands = []
        visited = set()
        for f in bm.faces:
            if f in visited:
                continue
            island = []
            stack = [f]
            while stack:
                fc = stack.pop()
                if fc in visited:
                    continue
                visited.add(fc)
                island.append(fc)
                for e in fc.edges:
                    for nf in e.link_faces:
                        if nf not in visited:
                            stack.append(nf)
            islands.append(island)

        if len(islands) == 0:
            if prev_mode != 'EDIT':
                bpy.ops.object.mode_set(mode=prev_mode)
            return {'CANCELLED'}

        # 按面数从大到小排序
        islands.sort(key=len, reverse=True)

        # 限制槽位数
        slot_count = min(self.limit, len(islands))

        # 创建槽位（颜色随后统一设置）
        for i in range(slot_count):
            ball = balls.add()
            ball.name = f"Part.{i + 1:03d}"
            ball.hash_val = uuid.uuid4().hex
            slot = data.slots.add()
            slot.ball_hash = ball.hash_val

        # 只写入槽索引
        slot_layer = bm.loops.layers.int.get(FaceColorManager.ATTR_SLOT)
        color_layer = bm.loops.layers.color.get(FaceColorManager.ATTR_COLOR)
        if slot_layer is None or color_layer is None:
            slot_layer, color_layer = FaceColorManager.ensure_attrs_edit(bm)

        for i, island in enumerate(islands):
            idx = i if i < slot_count - 1 else slot_count - 1
            for f in island:
                for loop in f.loops:
                    loop[slot_layer] = idx

        bmesh.update_edit_mesh(mesh)

        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)

        # 生成颜色并设置 → 触发 on_ball_color_update 同步所有网格
        colors = _generate_distinct_colors(slot_count)
        new_balls = [b for b in balls[-slot_count:]]
        for ball, color in zip(new_balls, colors):
            ball.color = color

        data.active_index = 0
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已按 {len(islands)} 个松散块设置 {slot_count} 个槽位")
        return {'FINISHED'}


def _hcl_to_rgba(h, c, l, a=1.0):
    """HCL (H 0-360, C 0-100, L 0-100) → sRGB RGBA (0–1)"""
    hr = h * math.pi / 180.0
    lab_l = l
    lab_a = c * math.cos(hr)
    lab_b = c * math.sin(hr)

    # Lab → XYZ (D65)
    fy = (lab_l + 16.0) / 116.0
    fx = lab_a / 500.0 + fy
    fz = fy - lab_b / 200.0

    delta = 6.0 / 29.0
    delta3 = delta * delta * delta

    def _f_inv(t):
        if t > delta:
            return t * t * t
        return 3.0 * delta * delta * (t - 4.0 / 29.0)

    xr = _f_inv(fx) * 0.95047
    yr = _f_inv(fy)
    zr = _f_inv(fz) * 1.08883

    # XYZ → linear RGB
    lr = 3.2404542 * xr - 1.5371385 * yr - 0.4985314 * zr
    lg = -0.9692660 * xr + 1.8760108 * yr + 0.0415560 * zr
    lb = 0.0556434 * xr - 0.2040259 * yr + 1.0572252 * zr

    # linear → sRGB
    def _srgb(c_lin):
        if c_lin <= 0.0031308:
            return 12.92 * c_lin
        return 1.055 * (c_lin ** (1.0 / 2.4)) - 0.055

    r = max(0.0, min(1.0, _srgb(lr)))
    g = max(0.0, min(1.0, _srgb(lg)))
    b = max(0.0, min(1.0, _srgb(lb)))
    return (r, g, b, a)


def _generate_distinct_colors(n, h_range=(0, 360), c_range=(30, 80), l_range=(35, 75)):
    """I Want Hue 算法：生成 n 个视觉上互不相同的颜色"""
    if n <= 0:
        return []

    # 生成候选色（HCL 空间随机采样）
    candidates = []
    num_candidates = max(n * 20, 200)
    for _ in range(num_candidates):
        h = random.uniform(*h_range)
        c = random.uniform(*c_range)
        l = random.uniform(*l_range)
        candidates.append((h, c, l))

    # 距离计算（HCL 加权欧几里得）
    def _dist(a, b):
        dh = min(abs(a[0] - b[0]), 360 - abs(a[0] - b[0]))
        dc = a[1] - b[1]
        dl = a[2] - b[2]
        return (dh * 1.2) * (dh * 1.2) + dc * dc + dl * dl

    # 选第一个色
    selected = [candidates.pop(random.randrange(len(candidates)))]

    # 贪心选剩余的：每次挑离已选色最远的候选
    while len(selected) < n and candidates:
        best = None
        best_dist = -1
        for c in candidates:
            d = min(_dist(c, s) for s in selected)
            if d > best_dist:
                best_dist = d
                best = c
        if best is None:
            break
        selected.append(best)
        candidates.remove(best)

    # 如果候选不够，补随机色
    while len(selected) < n:
        h = random.uniform(*h_range)
        c = random.uniform(*c_range)
        l = random.uniform(*l_range)
        selected.append((h, c, l))

    return [_hcl_to_rgba(h, c, l) for h, c, l in selected]


class XQFA_OT_RemoveAllSlots(bpy.types.Operator):
    """删除当前物体所有分层顶点色（保留全局颜色球）"""
    bl_idname = "xqfa.remove_all_slots"
    bl_label = "删除所有颜色"
    bl_description = "删除当前物体全部分层顶点色槽位和面拐数据"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors

        # 清空所有槽位
        old_count = len(data.slots)
        for i in range(old_count - 1, -1, -1):
            FaceColorManager.remove_slot_cleanup_mesh(obj, i)
            data.slots.remove(i)

        data.active_index = -1
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, "已删除所有分层顶点色")
        return {'FINISHED'}


class XQFA_MT_LayerVertexUtility(bpy.types.Menu):
    """展开功能菜单"""
    bl_label = "展开功能"
    bl_idname = "XQFA_MT_layer_vertex_utility"

    def draw(self, context):
        layout = self.layout
        layout.operator(XQFA_OT_AddSlotsFromVertexGroups.bl_idname, icon='GROUP_VERTEX')
        layout.operator(XQFA_OT_AddSlotsFromMaterials.bl_idname, icon='MATERIAL')
        layout.separator()
        layout.operator(XQFA_OT_SetByMaterial.bl_idname, icon='MATERIAL_DATA')
        layout.operator(XQFA_OT_SetByLooseParts.bl_idname, icon='MOD_EXPLODE')
        layout.separator()
        layout.operator(XQFA_OT_RebuildSlotData.bl_idname, icon='FILE_REFRESH')
        layout.operator(XQFA_OT_CleanupUnusedBalls.bl_idname, icon='BRUSH_DATA')
        layout.separator()
        layout.operator(XQFA_OT_RemoveAllSlots.bl_idname, icon='TRASH')


##########################
# Operator —— 槽位切换全局球
##########################

class XQFA_OT_SlotPickBall(bpy.types.Operator):
    """为当前槽位选择一个全局颜色球（弹出列表，每项右侧有色块）"""
    bl_idname = "xqfa.slot_pick_ball"
    bl_label = "选择颜色球"
    bl_description = "为当前槽位切换关联的全局颜色球"
    bl_options = {'REGISTER', 'UNDO'}

    slot_index: IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        return len(context.scene.xqfa_color_balls) > 0

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=280)

    def draw(self, context):
        layout = self.layout
        for ball in context.scene.xqfa_color_balls:
            row = layout.row(align=True)
            op = row.operator("xqfa.slot_pick_ball_exec", text=ball.name, icon='COLOR')
            op.slot_index = self.slot_index
            op.ball_hash = ball.hash_val
            row.prop(ball, "color", text="")
            op = row.operator("xqfa.global_ball_remove_by_hash", text="", icon='X', emboss=False)
            op.ball_hash = ball.hash_val


class XQFA_OT_SlotPickBallExec(bpy.types.Operator):
    """执行槽位颜色球切换"""
    bl_idname = "xqfa.slot_pick_ball_exec"
    bl_label = "选择"
    bl_description = "将所选槽位关联到此颜色球"
    bl_options = {'REGISTER', 'UNDO'}

    slot_index: IntProperty(default=-1)
    ball_hash: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = self.slot_index
        if idx < 0 or idx >= len(data.slots):
            return {'CANCELLED'}

        data.slots[idx].ball_hash = self.ball_hash
        FaceColorManager.sync_color_for_slot(obj, idx)

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class XQFA_OT_SlotNewBall(bpy.types.Operator):
    """为指定槽位新建一个全局颜色球并关联"""
    bl_idname = "xqfa.slot_new_ball"
    bl_label = "新建颜色球"
    bl_description = "新建全局颜色球并关联到指定槽位"
    bl_options = {'REGISTER', 'UNDO'}

    slot_index: IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        data = obj.layer_vertex_colors
        return 0 <= data.active_index < len(data.slots)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = self.slot_index if self.slot_index >= 0 else data.active_index

        # 生成名称
        balls = context.scene.xqfa_color_balls
        existing = {b.name for b in balls}
        base = "Color"
        if base not in existing:
            name = base
        else:
            for i in range(1, 1000):
                name = f"{base}.{i:03d}"
                if name not in existing:
                    break
            else:
                name = f"{base}.001"

        ball = balls.add()
        ball.name = name
        ball.hash_val = uuid.uuid4().hex
        ball.color = (1.0, 1.0, 1.0, 1.0)

        data.slots[idx].ball_hash = ball.hash_val
        FaceColorManager.sync_color_for_slot(obj, idx)

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class XQFA_OT_SlotClearBall(bpy.types.Operator):
    """断开当前槽位的颜色球关联（变为空槽）"""
    bl_idname = "xqfa.slot_clear_ball"
    bl_label = "断开"
    bl_description = "断开当前槽位的颜色球关联"
    bl_options = {'REGISTER', 'UNDO'}

    slot_index: IntProperty(default=-1)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = self.slot_index if self.slot_index >= 0 else data.active_index

        data.slots[idx].ball_hash = ""
        # 将所有该槽索引的面拐颜色重置为默认
        attr_color = FaceColorManager.ATTR_COLOR
        attr_slot = FaceColorManager.ATTR_SLOT
        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            slot_layer = bm.loops.layers.int.get(attr_slot)
            color_layer = bm.loops.layers.color.get(attr_color)
            if slot_layer is not None and color_layer is not None:
                for f in bm.faces:
                    for loop in f.loops:
                        if loop[slot_layer] == idx:
                            loop[color_layer] = FaceColorManager.DEFAULT_COLOR
                bmesh.update_edit_mesh(mesh)
        else:
            slot_attr = mesh.attributes.get(attr_slot)
            color_attr = mesh.attributes.get(attr_color)
            if slot_attr is not None and color_attr is not None:
                for i in range(len(mesh.loops)):
                    if slot_attr.data[i].value == idx:
                        color_attr.data[i].color = FaceColorManager.DEFAULT_COLOR

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


##########################
# Operators —— 面操作
##########################

class XQFA_OT_FaceColorAssign(bpy.types.Operator):
    """将选中面的所有面拐分配到当前活动槽位"""
    bl_idname = "xqfa.face_color_assign"
    bl_label = "指定"
    bl_description = "将选中面的所有面拐分配到当前槽位"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and len(obj.layer_vertex_colors.slots) > 0
                and obj.layer_vertex_colors.active_index >= 0)

    def execute(self, context):
        obj = context.active_object
        data = obj.layer_vertex_colors
        idx = data.active_index
        if idx < 0 or idx >= len(data.slots):
            self.report({'ERROR'}, "请先选择一个槽位")
            return {'CANCELLED'}

        color = FaceColorManager.get_ball_color(data.slots[idx].ball_hash)
        FaceColorManager.set_face_color_for_object(obj, idx, color)

        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已指定到槽位 {idx}")
        return {'FINISHED'}


class XQFA_OT_FaceColorUnassign(bpy.types.Operator):
    """将选中面的所有面拐恢复为未分配状态"""
    bl_idname = "xqfa.face_color_unassign"
    bl_label = "移除"
    bl_description = "将选中面的所有面拐恢复为未分配状态"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.active_object.mode == 'EDIT')

    def execute(self, context):
        obj = context.active_object
        FaceColorManager.set_face_color_for_object(
            obj,
            FaceColorManager.UNSET_SLOT,
            FaceColorManager.DEFAULT_COLOR,
        )
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, "已移除选中面的分层顶点色")
        return {'FINISHED'}


class XQFA_OT_FaceColorSelect(bpy.types.Operator):
    """选择属于当前活动槽位的所有面"""
    bl_idname = "xqfa.face_color_select"
    bl_label = "选择"
    bl_description = "选择属于当前槽位的所有面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and len(obj.layer_vertex_colors.slots) > 0
                and obj.layer_vertex_colors.active_index >= 0)

    def execute(self, context):
        obj = context.active_object
        idx = obj.layer_vertex_colors.active_index
        FaceColorManager.select_faces_by_slot_for_object(obj, idx, True)
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已选择槽位 {idx} 的面")
        return {'FINISHED'}


class XQFA_OT_FaceColorDeselect(bpy.types.Operator):
    """弃选属于当前活动槽位的所有面"""
    bl_idname = "xqfa.face_color_deselect"
    bl_label = "弃选"
    bl_description = "取消选择属于当前槽位的所有面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and len(obj.layer_vertex_colors.slots) > 0
                and obj.layer_vertex_colors.active_index >= 0)

    def execute(self, context):
        obj = context.active_object
        idx = obj.layer_vertex_colors.active_index
        FaceColorManager.select_faces_by_slot_for_object(obj, idx, False)
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, f"已弃选槽位 {idx} 的面")
        return {'FINISHED'}


##########################
# Panel
##########################

class XQFA_PT_LayerVertexColors(bpy.types.Panel):
    """分层顶点色面板"""
    bl_label = "分层顶点色"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'AttributeTools'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            return

        data = obj.layer_vertex_colors
        slots = data.slots
        active_idx = data.active_index

        # ---- 槽位列表 ----
        row = layout.row()
        row.template_list(
            "XQFA_UL_LayerVertexColorSlots", "",
            data, "slots",
            data, "active_index",
            rows=4,
        )
        col = row.column(align=True)
        col.operator(XQFA_OT_FaceColorSlotAdd.bl_idname, icon='ADD', text="")
        # if 0 <= active_idx < len(slots):
        col.operator(XQFA_OT_FaceColorSlotRemove.bl_idname, icon='REMOVE', text="")
        col.separator()
        col.menu(XQFA_MT_LayerVertexUtility.bl_idname, text="", icon='DOWNARROW_HLT')
        col.separator()
        op = col.operator(XQFA_OT_FaceColorSlotMove.bl_idname, text="", icon='TRIA_UP')
        op.direction = 'UP'
        op = col.operator(XQFA_OT_FaceColorSlotMove.bl_idname, text="", icon='TRIA_DOWN')
        op.direction = 'DOWN'

        # ---- 面操作（仅编辑模式） ----
        if obj.mode == 'EDIT' and len(slots) > 0 and 0 <= active_idx < len(slots):
            layout.separator()
            row = layout.row(align=True)
            row.operator(XQFA_OT_FaceColorAssign.bl_idname, text="指定", icon='CHECKMARK')
            row.operator(XQFA_OT_FaceColorUnassign.bl_idname, text="移除", icon='X')
            row.operator(XQFA_OT_FaceColorSelect.bl_idname, text="选择", icon='RESTRICT_SELECT_OFF')
            row.operator(XQFA_OT_FaceColorDeselect.bl_idname, text="弃选", icon='RESTRICT_SELECT_ON')


##########################
# Registration
##########################

classes = (
    FaceColorBall,
    LayerVertexColorSlot,
    LayerVertexColorData,
    XQFA_UL_GlobalColorBalls,
    XQFA_UL_LayerVertexColorSlots,
    XQFA_OT_GlobalBallAdd,
    XQFA_OT_GlobalBallRemove,
    XQFA_OT_GlobalBallRemoveByHash,
    XQFA_OT_FaceColorSlotAdd,
    XQFA_OT_FaceColorSlotRemove,
    XQFA_OT_FaceColorSlotMove,
    XQFA_OT_AddSlotsFromVertexGroups,
    XQFA_OT_AddSlotsFromMaterials,
    XQFA_OT_SetByMaterial,
    XQFA_OT_SetByLooseParts,
    XQFA_OT_CleanupUnusedBalls,
    XQFA_OT_RebuildSlotData,
    XQFA_OT_RemoveAllSlots,
    XQFA_MT_LayerVertexUtility,
    XQFA_OT_SlotPickBall,
    XQFA_OT_SlotPickBallExec,
    XQFA_OT_SlotNewBall,
    XQFA_OT_SlotClearBall,
    XQFA_OT_FaceColorAssign,
    XQFA_OT_FaceColorUnassign,
    XQFA_OT_FaceColorSelect,
    XQFA_OT_FaceColorDeselect,
    XQFA_PT_LayerVertexColors,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.xqfa_color_balls = CollectionProperty(type=FaceColorBall)
    bpy.types.Scene.xqfa_color_balls_active_index = IntProperty(default=-1, min=-1)
    bpy.types.Object.layer_vertex_colors = PointerProperty(type=LayerVertexColorData)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.xqfa_color_balls
    del bpy.types.Scene.xqfa_color_balls_active_index
    del bpy.types.Object.layer_vertex_colors
