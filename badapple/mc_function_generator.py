import os
import json
from typing import Dict, Tuple, List, Any


class BlockDecileMapping:
    """方块-十分位区间映射表类（适配0~9）"""
    def __init__(self, mapping_table: List[Tuple[str, int, int]]):
        self._validate_mapping(mapping_table)
        self.mapping_table = mapping_table
        self.sorted_positions = None

    @staticmethod
    def _validate_mapping(table: List[Tuple[str, int, int]]):
        intervals = sorted([(min_d, max_d) for _, min_d, max_d in table])
        if intervals[0][0] != 0:
            raise ValueError("映射表必须包含最小十分位为0的区间")
        if intervals[-1][1] != 9:
            raise ValueError("映射表必须包含最大十分位为9的区间")
        for i in range(1, len(intervals)):
            if intervals[i][0] != intervals[i - 1][1] + 1:
                raise ValueError(f"映射表区间不连续: {intervals[i - 1]} 与 {intervals[i]} 之间有间隙")

    def set_sorted_positions(self, positions: List[Tuple[int, int, int]]):
        self.sorted_positions = sorted(positions, key=lambda p: (p[2], p[0]))


def get_block_by_decile(decile: int, mapping: BlockDecileMapping) -> str:
    """根据白色像素十分位（0~9）匹配对应的方块"""
    for block, min_d, max_d in mapping.mapping_table:
        if min_d <= decile <= max_d:
            return block
    raise ValueError(f"十分位 {decile} 未匹配到任何方块（映射表配置错误）")


def parse_decile_sequence(sequence: str, sorted_positions: List[Tuple[int, int, int]]) -> Dict[
    Tuple[int, int, int], int]:
    """解析关键帧的0-9序列为坐标→十分位字典"""
    pos_decile = {}
    for idx, pos in enumerate(sorted_positions):
        if idx >= len(sequence):
            decile = 0
        else:
            decile = int(sequence[idx])
        pos_decile[pos] = decile
    return pos_decile


def generate_mc_functions_with_keyframe_sequence(
        cleaned_data: Dict,
        mapping: BlockDecileMapping,
        version_name: str,
        start_x: int = 0,
        y: int = 0,
        start_z: int = 0
) -> None:
    """
    关键帧复用0-9序列生成MC函数，增量帧仅生成变化方块
    """
    output_root = f"function/{version_name}"
    os.makedirs(output_root, exist_ok=True)

    # 1. 解析清理后的JSON数据
    keyframe_sequences = {int(frame): seq for frame, seq in cleaned_data["keyframe_sequences"].items()}
    delta_frames = {int(frame): {eval(pos): int(decile) for pos, decile in pos_decile.items()}
                    for frame, pos_decile in cleaned_data["delta_frames"].items()}
    sorted_positions = [tuple(pos) for pos in cleaned_data["sorted_positions"]]
    mapping.set_sorted_positions(sorted_positions)
    scaled_width, scaled_height = cleaned_data["scaled_size"]
    max_x_idx = scaled_width - 1
    max_z_idx = scaled_height - 1

    # 2. 坐标范围
    min_x = 0 + start_x
    max_x = max_x_idx + start_x
    min_z = 0 + start_z
    max_z = max_z_idx + start_z

    # 3. 生成初始化函数
    init_block = get_block_by_decile(0, mapping)
    init_path = os.path.join(output_root, "start.mcfunction")
    all_frame_nums = sorted(list(keyframe_sequences.keys()) + list(delta_frames.keys()))
    first_frame = min(all_frame_nums)
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(f"fill {min_x} {y} {min_z} {max_x} {y} {max_z} {init_block}\n")
        f.write(f"schedule function badapple:{version_name}/{first_frame} 1t\n")
    print(f"已生成初始化函数: {init_path}")

    # 4. 生成清除函数
    clean_path = os.path.join(output_root, "clean.mcfunction")
    with open(clean_path, "w", encoding="utf-8") as f:
        f.write(f"fill {min_x} {y} {min_z} {max_x} {y} {max_z} minecraft:air\n")
    print(f"已生成清除函数: {clean_path}")

    # 5. 生成帧函数（关键帧解析0-9序列，增量帧用delta_frames）
    last_keyframe_blocks = {}
    for frame_count in all_frame_nums:
        function_content = []
        if frame_count in keyframe_sequences:
            # 关键帧：解析0-9序列→生成方块指令
            sequence = keyframe_sequences[frame_count]
            pos_decile = parse_decile_sequence(sequence, sorted_positions)
            current_blocks = {}
            for pos, decile in pos_decile.items():
                block = get_block_by_decile(decile, mapping)
                mc_x = pos[0] + start_x
                mc_z = pos[2] + start_z
                function_content.append(f"setblock {mc_x} {y} {mc_z} {block}")
                current_blocks[pos] = block
            last_keyframe_blocks = current_blocks.copy()
            print(f"生成关键帧函数: {frame_count}（解析0-9序列，长度{len(sequence)}）")
        else:
            # 增量帧：仅生成变化方块
            frame_delta = delta_frames[frame_count]
            for pos, decile in frame_delta.items():
                block = get_block_by_decile(decile, mapping)
                mc_x = pos[0] + start_x
                mc_z = pos[2] + start_z
                function_content.append(f"setblock {mc_x} {y} {mc_z} {block}")
            print(f"生成增量帧函数: {frame_count}（{len(frame_delta)}个变化方块）")

        # 调度下一帧
        if frame_count < max(all_frame_nums):
            next_frame = [f for f in all_frame_nums if f > frame_count][0]
            function_content.append(f"schedule function badapple:{version_name}/{next_frame} 1t")

        # 写入文件
        frame_path = os.path.join(output_root, f"{frame_count}.mcfunction")
        with open(frame_path, "w", encoding="utf-8") as f:
            f.write("\n".join(function_content))

    print(f"\nMC函数生成完成！输出路径: {os.path.abspath(output_root)}")


# 示例调用
if __name__ == "__main__":
    # 1. 加载清理后的JSON
    with open("white_decile_lightweight.json", "r", encoding="utf-8") as f:
        cleaned_data = json.load(f)

    # 2. 定义映射表
    custom_mapping = [
        ("minecraft:powder_snow_cauldron[level=3]", 8, 9),
        ("minecraft:powder_snow_cauldron[level=2]", 6, 7),
        ("minecraft:powder_snow_cauldron[level=1]", 5, 5),
        ("minecraft:cauldron", 0, 4)
    ]
    mapping = BlockDecileMapping(custom_mapping)

    # 3. 生成MC函数
    VERSION_NAME = "badapple-decile-slim"
    generate_mc_functions_with_keyframe_sequence(
        cleaned_data=cleaned_data,
        mapping=mapping,
        version_name=VERSION_NAME,
        start_x=0,
        y=0,
        start_z=0
    )