# type: ignore
import bpy
import uuid
from bpy.types import Panel, Operator, Scene
from bpy.props import StringProperty, EnumProperty
from bpy.utils import register_class, unregister_class


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------

LANG = {
    "en": {
        "ABP_PT_generator.label": "ABP Generator",
        "ABP_PT_generator.mapping_header": "Bone Mappings (from rename list):",
        "ABP_PT_generator.mapping_empty": "(empty - add items in the tool above)",
        "ABP_PT_generator.asset_path": "ABP Asset Path",
        "ABP_PT_generator.generate": "Generate ABP Text",
        "ABP_PT_generator.node_count": "Nodes to generate: ",
        "abp.generate_text": "Generate ABP Text",
        "abp.generate_text.tip": "Generate UE4/5 Animation Blueprint constraint node text from current mapping list",
        "report.empty_list": "Bone mapping list is empty, please add items first",
        "report.empty_path": "ABP Asset Path cannot be empty",
        "report.save_error": "Failed to save file",
        "report.success": " nodes generated, saved and copied to clipboard",
        "abp.version": "UE Version",
    },
    "zh": {
        "ABP_PT_generator.label": "ABP 生成器",
        "ABP_PT_generator.mapping_header": "骨骼映射 (来自重命名列表):",
        "ABP_PT_generator.mapping_empty": "(空 - 请先在上方工具中添加映射项)",
        "ABP_PT_generator.asset_path": "ABP 资产路径",
        "ABP_PT_generator.generate": "生成 ABP 文本",
        "ABP_PT_generator.node_count": "待生成节点数: ",
        "abp.generate_text": "生成 ABP 文本",
        "abp.generate_text.tip": "根据当前映射列表生成 UE4/5 动画蓝图约束节点文本",
        "report.empty_list": "骨骼映射列表为空，请先添加映射项",
        "report.empty_path": "ABP 资产路径不能为空",
        "report.save_error": "文件保存失败",
        "report.success": " 个约束节点已生成，已保存并复制到剪贴板",
        "abp.version": "UE 版本",
    },
}


def _get_lang():
    try:
        current = bpy.context.preferences.view.language
        if current in ("zh_CN", "zh_TW"):
            return LANG["zh"]
    except Exception:
        pass
    return LANG["en"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_guid():
    """Generate UE4-style 32-char uppercase hex GUID (no dashes)."""
    return uuid.uuid4().hex.upper()


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _build_abp_node(
    node_name, bone_to_modify, target_bone,
    pos_x, pos_y, node_guid,
    pin_comp_pose_id, pin_b_alpha_id, pin_alpha_id,
    pin_alpha_curve_id, pin_weight_id, pin_pose_id,
    component_pose_linked_to, pose_linked_to_segment,
):
    """Build a single 25-line ABP constraint node text block (updated format)."""
    # Shorthand constants for pin type fields
    PV = "PinType.PinValueType=()"
    PC = "PinType.ContainerType=None"
    PF = ("PinType.bIsReference=False,PinType.bIsConst=False,"
          "PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False")
    PG = "PersistentGuid=00000000000000000000000000000000"
    BV = ("bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,"
          "bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,")
    NS = "NSLOCTEXT"
    LF = "LOCGEN_FORMAT_NAMED"
    SC = 'ScriptStruct\'"/Script/Engine.ComponentSpacePoseLink"\''

    lines = [
        # 1: Begin Object header (no ExportPath)
        f'Begin Object Class=/Script/AnimGraph.AnimGraphNode_Constraint Name="{node_name}"',
        # 2: Node data
        f'   Node=(BoneToModify=(BoneName="{bone_to_modify}"),ConstraintSetup=((TargetBone=(BoneName="{target_bone}"),TransformType=Rotation)),ConstraintWeights=(1.000000))',
        # 3-14: ShowPinForProperties (12 entries, order matches UE export)
        f'   ShowPinForProperties(0)=(PropertyName="BoneToModify",PropertyFriendlyName="Bone to Modify",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:BoneToModify", "Name of bone to control. This is the main bone chain to modify from. *"),CategoryName="SkeletalControl")',
        f'   ShowPinForProperties(1)=(PropertyName="ConstraintSetup",PropertyFriendlyName="Constraint Setup",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:ConstraintSetup", "List of constraints"),CategoryName="Constraints")',
        f'   ShowPinForProperties(2)=(PropertyName="ConstraintWeights",PropertyFriendlyName="Constraint Weights",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:ConstraintWeights", "Weight data - post edit syncs up to ConstraintSetups"),CategoryName="Runtime",bShowPin=True,bCanToggleVisibility=True)',
        f'   ShowPinForProperties(3)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_SkeletalControlBase:ComponentPose", "Input link"),CategoryName="Links",bShowPin=True)',
        f'   ShowPinForProperties(4)=(PropertyName="LODThreshold",PropertyFriendlyName="LOD Threshold",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_SkeletalControlBase:LODThreshold", "* Max LOD that this node is allowed to run\\n* For example if you have LODThreadhold to be 2, it will run until LOD 2 (based on 0 index)\\n* when the component LOD becomes 3, it will stop update/evaluate\\n* currently transition would be issue and that has to be re-visited"),CategoryName="Performance")',
        '   ShowPinForProperties(5)=(PropertyName="AlphaInputType",PropertyFriendlyName="Alpha Input Type",PropertyTooltip="Alpha Input Type",CategoryName="Alpha")',
        '   ShowPinForProperties(6)=(PropertyName="bAlphaBoolEnabled",PropertyFriendlyName="bEnabled",PropertyTooltip="Alpha Bool Enabled",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        f'   ShowPinForProperties(7)=(PropertyName="Alpha",PropertyFriendlyName="Alpha",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_SkeletalControlBase:Alpha", "Current strength of the skeletal control"),CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        '   ShowPinForProperties(8)=(PropertyName="AlphaScaleBias",PropertyFriendlyName="Alpha Scale Bias",PropertyTooltip="Alpha Scale Bias",CategoryName="Alpha")',
        '   ShowPinForProperties(9)=(PropertyName="AlphaBoolBlend",PropertyFriendlyName="Blend Settings",PropertyTooltip="Alpha Bool Blend",CategoryName="Alpha")',
        '   ShowPinForProperties(10)=(PropertyName="AlphaCurveName",PropertyFriendlyName="Alpha Curve Name",PropertyTooltip="Alpha Curve Name",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        '   ShowPinForProperties(11)=(PropertyName="AlphaScaleBiasClamp",PropertyFriendlyName="Alpha Scale Bias Clamp",PropertyTooltip="Alpha Scale Bias Clamp",CategoryName="Alpha")',
        # 15-18: Position + ErrorType + GUID
        f'   NodePosX={pos_x}',
        f'   NodePosY={pos_y}',
        '   ErrorType=3',
        f'   NodeGuid={node_guid}',
        # 19: ConstraintWeights_0 Pin (float type, LOCGEN_FORMAT_NAMED)
        f'   CustomProperties Pin (PinId={pin_weight_id},PinName="ConstraintWeights_0",PinFriendlyName={LF}({NS}("K2Node", "PinFriendlyNameWithIndex", "{{PinName}} {{Index}}"), "PinName", "Constraint Weights", "Index", 0),PinToolTip="Constraint Weights 0\\n\u6d6e\u70b9\\n\\n\u6743\u91cd\u6570\u636e - \u5c06\u7f16\u8f91\u540c\u6b65\u516c\u5e03\u5230ConstraintSetups",PinType.PinCategory="float",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="1.000000",AutogeneratedDefaultValue="0.0",{PG},{BV})',
        # 20: ComponentPose Pin
        f'   CustomProperties Pin (PinId={pin_comp_pose_id},PinName="ComponentPose",PinFriendlyName="Component Pose",PinToolTip="Component Pose\\n\u7ec4\u4ef6\u7a7a\u95f4\u59ff\u52bf\u94fe\u63a5 \u7ed3\u6784\\n\\n\u8f93\u5165\u94fe\u63a5",PinType.PinCategory="struct",PinType.PinSubCategory="",PinType.PinSubCategoryObject={SC},PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="(LinkID=-1,SourceLinkID=-1)",AutogeneratedDefaultValue="(LinkID=-1,SourceLinkID=-1)",LinkedTo={component_pose_linked_to},{PG},{BV})',
        # 21: bAlphaBoolEnabled Pin
        f'   CustomProperties Pin (PinId={pin_b_alpha_id},PinName="bAlphaBoolEnabled",PinFriendlyName="bEnabled",PinToolTip="Enabled\\n\u5e03\u5c14\\n\\nAlpha Bool Enabled",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="True",AutogeneratedDefaultValue="True",{PG},bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)',
        # 22: Alpha Pin (float type)
        f'   CustomProperties Pin (PinId={pin_alpha_id},PinName="Alpha",PinFriendlyName="Alpha",PinToolTip="Alpha\\n\u6d6e\u70b9\\n\\n\u9aa8\u9abc\u63a7\u5236\u7684\u5f53\u524d\u5f3a\u5ea6",PinType.PinCategory="float",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="1.000000",AutogeneratedDefaultValue="1.000000",{PG},{BV})',
        # 23: AlphaCurveName Pin
        f'   CustomProperties Pin (PinId={pin_alpha_curve_id},PinName="AlphaCurveName",PinFriendlyName="Alpha Curve Name",PinToolTip="Alpha Curve Name\\n\u547d\u540d\\n\\nAlpha Curve Name",PinType.PinCategory="name",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="None",AutogeneratedDefaultValue="None",{PG},bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)',
        # 24: Pose Pin (output) - LinkedTo segment varies for tail vs non-tail
        f'   CustomProperties Pin (PinId={pin_pose_id},PinName="Pose",Direction="EGPD_Output",PinType.PinCategory="struct",PinType.PinSubCategory="",PinType.PinSubCategoryObject={SC},PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},{pose_linked_to_segment}{PG},{BV})',
        # 25: End Object
        'End Object',
    ]
    return "\n".join(lines)


def _build_abp_node_ue5(
    node_name, bone_to_modify, target_bone,
    pos_x, pos_y, node_guid, asset_path,
    pin_comp_pose_id, pin_b_alpha_id, pin_alpha_id,
    pin_alpha_curve_id, pin_weight_id, pin_pose_id,
    component_pose_linked_to, pose_linked_to_segment,
):
    """Build a single ABP constraint node text block (UE 5.3 format)."""
    # UE5 does not support spaces in bone names - replace with hyphens
    bone_to_modify = bone_to_modify.replace(" ", "-")
    target_bone = target_bone.replace(" ", "-")
    PV = "PinType.PinValueType=()"
    PC = "PinType.ContainerType=None"
    PF = ("PinType.bIsReference=False,PinType.bIsConst=False,"
          "PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,"
          "PinType.bSerializeAsSinglePrecisionFloat=False")
    PG = "PersistentGuid=00000000000000000000000000000000"
    BV = ("bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,"
          "bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,")
    NS = "NSLOCTEXT"
    SC = '"/Script/CoreUObject.ScriptStruct\'/Script/Engine.ComponentSpacePoseLink\'"'
    export_path = f"/Script/AnimGraph.AnimGraphNode_Constraint\'{asset_path}:{node_name}\'"

    lines = [
        # 1: Begin Object header (with ExportPath)
        f'Begin Object Class=/Script/AnimGraph.AnimGraphNode_Constraint Name="{node_name}" ExportPath="{export_path}"',
        # 2: Node data
        f'   Node=(BoneToModify=(BoneName="{bone_to_modify}"),ConstraintSetup=((TargetBone=(BoneName="{target_bone}"),TransformType=Rotation)),ConstraintWeights=(1.000000))',
        # 3-14: ShowPinForProperties (12 entries, UE5.3 reordered)
        f'   ShowPinForProperties(0)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_SkeletalControlBase:ComponentPose", "Input link"),CategoryName="Links",bShowPin=True)',
        f'   ShowPinForProperties(1)=(PropertyName="LODThreshold",PropertyFriendlyName="LOD Threshold",PropertyTooltip={NS}("", "{_generate_guid()}", "* Max LOD that this node is allowed to run\\n* For example if you have LODThreshold to be 2, it will run until LOD 2 (based on 0 index)\\n* when the component LOD becomes 3, it will stop update/evaluate\\n* currently transition would be issue and that has to be re-visited"),CategoryName="Performance")',
        '   ShowPinForProperties(2)=(PropertyName="AlphaInputType",PropertyFriendlyName="Alpha Input Type",CategoryName="Alpha")',
        '   ShowPinForProperties(3)=(PropertyName="bAlphaBoolEnabled",PropertyFriendlyName="bEnabled",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        f'   ShowPinForProperties(4)=(PropertyName="Alpha",PropertyFriendlyName="Alpha",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_SkeletalControlBase:Alpha", "Current strength of the skeletal control"),CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        '   ShowPinForProperties(5)=(PropertyName="AlphaScaleBias",PropertyFriendlyName="Alpha Scale Bias",CategoryName="Alpha")',
        '   ShowPinForProperties(6)=(PropertyName="AlphaBoolBlend",PropertyFriendlyName="Blend Settings",CategoryName="Alpha")',
        '   ShowPinForProperties(7)=(PropertyName="AlphaCurveName",PropertyFriendlyName="Alpha Curve Name",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        '   ShowPinForProperties(8)=(PropertyName="AlphaScaleBiasClamp",PropertyFriendlyName="Alpha Scale Bias Clamp",CategoryName="Alpha")',
        f'   ShowPinForProperties(9)=(PropertyName="BoneToModify",PropertyFriendlyName="Bone to Modify",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:BoneToModify", "Name of bone to control. This is the main bone chain to modify from. *"),CategoryName="SkeletalControl")',
        f'   ShowPinForProperties(10)=(PropertyName="ConstraintSetup",PropertyFriendlyName="Constraint Setup",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:ConstraintSetup", "List of constraints"),CategoryName="Constraints")',
        f'   ShowPinForProperties(11)=(PropertyName="ConstraintWeights",PropertyFriendlyName="Constraint Weights",PropertyTooltip={NS}("UObjectToolTips", "AnimNode_Constraint:ConstraintWeights", "Weight data - post edit syncs up to ConstraintSetups"),CategoryName="Runtime",bShowPin=True,bCanToggleVisibility=True)',
        # 15-17: Position + GUID (no ErrorType in UE5.3)
        f'   NodePosX={pos_x}',
        f'   NodePosY={pos_y}',
        f'   NodeGuid={node_guid}',
        # 18: ComponentPose Pin
        f'   CustomProperties Pin (PinId={pin_comp_pose_id},PinName="ComponentPose",PinFriendlyName={NS}("", "{_generate_guid()}", "Component Pose"),PinToolTip="Component Pose\\n\u7ec4\u4ef6\u7a7a\u95f4\u59ff\u52bf\u94fe\u63a5 \u7ed3\u6784\\n\\n\u8f93\u5165\u94fe\u63a5",PinType.PinCategory="struct",PinType.PinSubCategory="",PinType.PinSubCategoryObject={SC},PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="(LinkID=-1,SourceLinkID=-1)",AutogeneratedDefaultValue="(LinkID=-1,SourceLinkID=-1)",LinkedTo={component_pose_linked_to},{PG},{BV})',
        # 19: bAlphaBoolEnabled Pin
        f'   CustomProperties Pin (PinId={pin_b_alpha_id},PinName="bAlphaBoolEnabled",PinFriendlyName={NS}("", "{_generate_guid()}", "bEnabled"),PinToolTip="Enabled\\n\u5e03\u5c14",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="True",AutogeneratedDefaultValue="True",{PG},bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)',
        # 20: Alpha Pin (real/float type in UE5)
        f'   CustomProperties Pin (PinId={pin_alpha_id},PinName="Alpha",PinFriendlyName={NS}("", "{_generate_guid()}", "Alpha"),PinToolTip="Alpha\\n\u6d6e\u70b9\uff08\u5355\u7cbe\u5ea6\uff09\\n\\n\u9aa8\u9abc\u63a7\u5236\u7684\u5f53\u524d\u5f3a\u5ea6",PinType.PinCategory="real",PinType.PinSubCategory="float",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="1.000000",AutogeneratedDefaultValue="1.000000",{PG},{BV})',
        # 21: AlphaCurveName Pin
        f'   CustomProperties Pin (PinId={pin_alpha_curve_id},PinName="AlphaCurveName",PinFriendlyName={NS}("", "{_generate_guid()}", "Alpha Curve Name"),PinToolTip="Alpha Curve Name\\n\u547d\u540d",PinType.PinCategory="name",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="None",AutogeneratedDefaultValue="None",{PG},bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)',
        # 22: ConstraintWeights_0 Pin (real/float type in UE5)
        f'   CustomProperties Pin (PinId={pin_weight_id},PinName="ConstraintWeights_0",PinFriendlyName=LOCGEN_FORMAT_NAMED({NS}("K2Node", "PinFriendlyNameWithIndex", "{{PinName}} {{Index}}"), "Index", 0, "PinName", {NS}("", "{_generate_guid()}", "Constraint Weights")),PinToolTip="Constraint Weights 0\\n\u6d6e\u70b9\uff08\u5355\u7cbe\u5ea6\uff09\\n\\n\u6743\u91cd\u6570\u636e - \u5c06\u7f16\u8f91\u540c\u6b65\u516c\u5e03\u5230ConstraintSetups",PinType.PinCategory="real",PinType.PinSubCategory="float",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},DefaultValue="1.000000",AutogeneratedDefaultValue="0.0",{PG},{BV})',
        # 23: Pose Pin (output)
        f'   CustomProperties Pin (PinId={pin_pose_id},PinName="Pose",Direction="EGPD_Output",PinType.PinCategory="struct",PinType.PinSubCategory="",PinType.PinSubCategoryObject={SC},PinType.PinSubCategoryMemberReference=(),{PV},{PC},{PF},{pose_linked_to_segment}{PG},{BV})',
        # 24: End Object
        'End Object',
    ]
    return "\n".join(lines)


def generate_abp_text(bone_mappings, asset_path, version="UE4", start_x=-912, step_x=288, start_y=64, step_y=256, cols=5):
    """
    Generate complete ABP constraint node chain text.

    Args:
        bone_mappings: list of (bone_to_modify, target_bone) tuples
        asset_path: UE asset path e.g. "/Game/Character/ABP_name.ABP_name"
        version: "UE4" or "UE5" to select node format
        start_x: first node X position
        step_x: X spacing between nodes
        start_y: first row Y position
        step_y: Y spacing between rows
        cols: nodes per row before wrapping

    Returns:
        Complete ABP text string ready to paste into UE editor
    """
    n = len(bone_mappings)
    if n == 0:
        return ""

    # Pre-generate per-node data: names, GUIDs, pin IDs
    nodes = []
    for i in range(n):
        nodes.append({
            "name": f"AnimGraphNode_Constraint_{i + 1}",
            "node_guid": _generate_guid(),
            "pin_comp_pose": _generate_guid(),
            "pin_b_alpha": _generate_guid(),
            "pin_alpha": _generate_guid(),
            "pin_alpha_curve": _generate_guid(),
            "pin_weight": _generate_guid(),
            "pin_pose": _generate_guid(),
        })

    result_blocks = []
    for i, (bone_to_modify, target_bone) in enumerate(bone_mappings):
        node = nodes[i]
        col = i % cols
        row = i // cols
        pos_x = start_x + col * step_x
        pos_y = start_y + row * step_y

        # ComponentPose input linkage
        if i == 0:
            # First node: no input connection
            comp_pose_linked_to = "()"
        else:
            prev = nodes[i - 1]
            comp_pose_linked_to = f"({prev['name']} {prev['pin_pose']},)"

        # Pose output linkage
        if i == n - 1:
            # Tail node: omit LinkedTo entirely
            pose_linked_to_segment = ""
        else:
            nxt = nodes[i + 1]
            pose_linked_to_segment = f"LinkedTo=({nxt['name']} {nxt['pin_comp_pose']}),"

        if version == "UE5":
            block = _build_abp_node_ue5(
                node_name=node["name"],
                bone_to_modify=bone_to_modify,
                target_bone=target_bone,
                pos_x=pos_x,
                pos_y=pos_y,
                node_guid=node["node_guid"],
                asset_path=asset_path,
                pin_comp_pose_id=node["pin_comp_pose"],
                pin_b_alpha_id=node["pin_b_alpha"],
                pin_alpha_id=node["pin_alpha"],
                pin_alpha_curve_id=node["pin_alpha_curve"],
                pin_weight_id=node["pin_weight"],
                pin_pose_id=node["pin_pose"],
                component_pose_linked_to=comp_pose_linked_to,
                pose_linked_to_segment=pose_linked_to_segment,
            )
        else:
            block = _build_abp_node(
                node_name=node["name"],
                bone_to_modify=bone_to_modify,
                target_bone=target_bone,
                pos_x=pos_x,
                pos_y=pos_y,
                node_guid=node["node_guid"],
                pin_comp_pose_id=node["pin_comp_pose"],
                pin_b_alpha_id=node["pin_b_alpha"],
                pin_alpha_id=node["pin_alpha"],
                pin_alpha_curve_id=node["pin_alpha_curve"],
                pin_weight_id=node["pin_weight"],
                pin_pose_id=node["pin_pose"],
                component_pose_linked_to=comp_pose_linked_to,
                pose_linked_to_segment=pose_linked_to_segment,
            )
        result_blocks.append(block)

    return "\n".join(result_blocks)


# ---------------------------------------------------------------------------
# UI Panel
# ---------------------------------------------------------------------------

class ABPGeneratorPanel(Panel):
    bl_idname = "ABP_PT_generator"
    bl_label = LANG["en"]["ABP_PT_generator.label"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'MappingTools'

    def draw(self, context):
        lang = _get_lang()
        layout = self.layout
        scene = context.scene

        # Mapping list preview (read-only)
        box = layout.box()
        box.label(text=lang["ABP_PT_generator.mapping_header"])
        my_list = scene.my_list
        if len(my_list) == 0:
            box.label(text=lang["ABP_PT_generator.mapping_empty"], icon="INFO")
        else:
            MAX_PREVIEW = 8
            for i, item in enumerate(my_list):
                if i >= MAX_PREVIEW:
                    remaining = len(my_list) - MAX_PREVIEW
                    box.label(text=f"... +{remaining} more")
                    break
                row = box.row()
                row.label(text=f"{i + 1}. {item.vg}  ->  {item.bone}")

        # ABP asset path input
        layout.prop(scene, "abp_asset_path", text=lang["ABP_PT_generator.asset_path"])

        # Version selector + Generate button
        row = layout.row(align=True)
        row.prop(scene, "abp_version", text=lang["abp.version"])
        row.operator("abp.generate_text", text=lang["ABP_PT_generator.generate"], icon="FILE_TEXT")

        # Node count status
        layout.label(text=lang["ABP_PT_generator.node_count"] + str(len(my_list)))


# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------

class GenerateABPText(Operator):
    bl_idname = "abp.generate_text"
    bl_label = LANG["en"]["abp.generate_text"]
    bl_description = LANG["en"]["abp.generate_text.tip"]

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.txt", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return len(context.scene.my_list) > 0

    def invoke(self, context, event):
        lang = _get_lang()
        if len(context.scene.my_list) == 0:
            self.report({"ERROR"}, lang["report.empty_list"])
            return {"CANCELLED"}
        if not context.scene.abp_asset_path.strip():
            self.report({"ERROR"}, lang["report.empty_path"])
            return {"CANCELLED"}
        # Default filename
        self.filepath = "abp_constraints.txt"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        lang = _get_lang()
        scene = context.scene

        # 1. Extract bone mappings from my_list
        bone_mappings = []
        skipped = 0
        for item in scene.my_list:
            if item.vg and item.bone:
                bone_mappings.append((item.vg, item.bone))
            else:
                skipped += 1

        if not bone_mappings:
            self.report({"ERROR"}, lang["report.empty_list"])
            return {"CANCELLED"}

        # 2. Generate ABP text
        asset_path = scene.abp_asset_path.strip()
        version = scene.abp_version
        result_text = generate_abp_text(bone_mappings, asset_path, version=version)

        # 3. Save to file
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(result_text)
        except Exception as e:
            self.report({"ERROR"}, f"{lang['report.save_error']}: {e}")
            return {"CANCELLED"}

        # 4. Copy to clipboard
        try:
            context.window_manager.clipboard = result_text
        except Exception:
            pass  # clipboard may not be available in some environments

        # 5. Report success
        node_count = len(bone_mappings)
        msg = f"{node_count}{lang['report.success']}"
        if skipped > 0:
            msg += f" (skipped {skipped} empty entries)"
        self.report({"INFO"}, msg)
        print(f"[ABP Generator] {msg}")
        print(f"[ABP Generator] Saved to: {self.filepath}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    ABPGeneratorPanel,
    GenerateABPText,
)


def register():
    for cls in classes:
        register_class(cls)

    Scene.abp_asset_path = StringProperty(
        name="ABP Asset Path",
        description="UE4/5 Animation Blueprint asset path, e.g. /Game/Character/ABP_name.ABP_name",
        default="/Game/Character/ABP_example.ABP_example",
    )
    Scene.abp_version = EnumProperty(
        name="UE Version",
        description="Target Unreal Engine version for ABP node format",
        items=[
            ("UE4", "4.26", "UE 4.26 format"),
            ("UE5", "5.3", "UE 5.3 format"),
        ],
        default="UE4",
    )


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.abp_asset_path
    del Scene.abp_version
