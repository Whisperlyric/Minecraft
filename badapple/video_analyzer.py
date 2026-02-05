import cv2
import os
import json
from typing import Dict, Tuple, List


def analyze_video_white_decile(  # 十分位
        video_path: str,
        pixel_block_size: int,
        start_frame: int = 41,
        end_frame: int = 6516,
        keyframe_interval: int = 100
) -> Dict:
    """
    分析视频指定帧区间内每个方块区域的白色像素十分位（0~9）
    :param video_path: 视频文件路径
    :param pixel_block_size: 每个方块对应的视频像素块大小（n×n）
    :param start_frame: 起始帧（包含）
    :param end_frame: 结束帧（包含）
    :param keyframe_interval: 关键帧间隔（I帧间隔）
    :return: 包含关键帧、增量帧、坐标列表的字典
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"无法打开视频文件: {video_path}")

    # 获取视频基础信息
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scaled_width = video_width // pixel_block_size
    scaled_height = video_height // pixel_block_size

    # 存储关键帧完整数据、增量帧差分数据、坐标列表
    frame_data = {
        "keyframes": {},  # 关键帧：帧号 -> (坐标)->十分位（完整数据）
        "delta_frames": {},  # 增量帧：帧号 -> (坐标)->十分位（仅变化数据）
        "sorted_positions": [],  # 固定坐标顺序（用于后续解析）
        "keyframe_interval": keyframe_interval,
        "scaled_size": (scaled_width, scaled_height)
    }
    frame_count = 0
    prev_frame_decile = {}  # 前一帧完整数据（十分位）

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 跳过指定区间外的帧
        if frame_count < start_frame:
            frame_count += 1
            continue
        if frame_count > end_frame:
            break

        # 转为灰度图并二值化（127为阈值，大于为白(255)，小于为黑(0)）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # 存储当前帧完整十分位数据
        current_frame_decile = {}
        # 按固定顺序遍历（先Z后X），确保坐标顺序统一
        for i in range(scaled_height):  # Z轴（行）
            for j in range(scaled_width):  # X轴（列）
                mc_x = j
                mc_z = i
                pos = (mc_x, 0, mc_z)

                black_pixels = 0
                total_pixels = 0

                # 统计当前方块对应像素块的黑白像素数
                for dy in range(pixel_block_size):
                    for dx in range(pixel_block_size):
                        orig_x = j * pixel_block_size + dx
                        orig_y = i * pixel_block_size + dy
                        if orig_x < video_width and orig_y < video_height:
                            if binary[orig_y, orig_x] == 0:
                                black_pixels += 1
                            total_pixels += 1

                # ========== 关键改动1：千分位→十分位 ==========
                # 计算白色像素十分位（0~9）
                if total_pixels == 0:
                    white_decile = 0
                else:
                    white_ratio = (total_pixels - black_pixels) / total_pixels
                    white_decile = round(white_ratio * 10)  # ×10而非×1000
                    # 确保数值在0~9的范围内（无10的情况，无需替换）
                    white_decile = max(0, min(9, white_decile))

                current_frame_decile[pos] = white_decile

        # 初始化坐标列表（仅第一次循环时）
        if not frame_data["sorted_positions"]:
            frame_data["sorted_positions"] = sorted(current_frame_decile.keys(), key=lambda p: (p[2], p[0]))

        # 判断是否为关键帧
        is_keyframe = (
                frame_count == start_frame or
                frame_count % keyframe_interval == 0 or
                frame_count == end_frame
        )

        if is_keyframe:
            # 关键帧：保存完整数据（十分位）
            frame_data["keyframes"][frame_count] = current_frame_decile
            print(f"已保存关键帧: {frame_count} (完整数据，共{len(current_frame_decile)}个坐标)")
        else:
            # 增量帧：仅保存与前一帧变化的坐标（十分位）
            delta_decile = {}
            for pos in frame_data["sorted_positions"]:
                prev_decile = prev_frame_decile.get(pos, 0)
                curr_decile = current_frame_decile.get(pos, 0)
                if prev_decile != curr_decile:
                    delta_decile[pos] = curr_decile
            frame_data["delta_frames"][frame_count] = delta_decile
            # 进度打印（增量帧）
            if frame_count % 100 == 0:
                progress = (frame_count - start_frame + 1) / (end_frame - start_frame + 1) * 100
                print(f"分析进度: 帧{frame_count}/{end_frame} ({progress:.1f}%)，变化坐标数: {len(delta_decile)}")

        # 更新前一帧数据（十分位）
        prev_frame_decile = current_frame_decile.copy()
        frame_count += 1

    cap.release()
    print(f"\n视频分析完成！")
    print(f"- 关键帧数量: {len(frame_data['keyframes'])} (间隔{keyframe_interval}帧)")
    print(f"- 增量帧数量: {len(frame_data['delta_frames'])}")
    print(f"- 总分析帧数: {len(frame_data['keyframes']) + len(frame_data['delta_frames'])}")
    print(f"- 坐标总数: {len(frame_data['sorted_positions'])}")
    return frame_data


def frame_data_to_string(frame_data: Dict) -> Dict[int, str]:
    """
    将关键帧+增量帧数据拼接为字符串（十分位：一位一组）
    """
    frame_string_map = {}
    sorted_positions = frame_data["sorted_positions"]
    keyframes = frame_data["keyframes"]
    delta_frames = frame_data["delta_frames"]

    # 先还原所有帧的完整十分位数据
    full_frame_decile = {}
    last_keyframe_decile = {}
    all_frame_nums = sorted(list(keyframes.keys()) + list(delta_frames.keys()))

    for frame_num in all_frame_nums:
        if frame_num in keyframes:
            full_decile = keyframes[frame_num]
            last_keyframe_decile = full_decile.copy()
        else:
            full_decile = last_keyframe_decile.copy()
            delta_decile = delta_frames[frame_num]
            for pos, decile in delta_decile.items():
                full_decile[pos] = decile
            last_keyframe_decile = full_decile.copy()

        full_frame_decile[frame_num] = full_decile

        # ========== 关键改动2：拼接字符串从三位→一位 ==========
        # 按固定顺序拼接字符串（一位一组，无需补充前置零）
        decile_string = ""
        for pos in sorted_positions:
            decile = full_decile.get(pos, 0)
            decile_string += f"{decile}"  # 直接拼接数字（0→"0"，8→"8"）
        frame_string_map[frame_num] = decile_string

    print(
        f"已拼接所有帧字符串，示例（帧{next(iter(frame_string_map.keys()))}）: {next(iter(frame_string_map.values()))[:20]}...")
    return frame_string_map


# 示例调用
if __name__ == "__main__":
    VIDEO_PATH = "..\\badapple.mp4"
    PIXEL_BLOCK_SIZE = 12
    KEYFRAME_INTERVAL = 100

    # 1. 分析视频得到十分位的增量帧数据
    frame_data = analyze_video_white_decile(
        VIDEO_PATH,
        PIXEL_BLOCK_SIZE,
        keyframe_interval=KEYFRAME_INTERVAL
    )

    # 2. 还原并拼接所有帧的字符串（一位一组）
    frame_string_data = frame_data_to_string(frame_data)

    # 3. 保存轻量化的JSON数据（十分位版本）
    output_data = {
        "lightweight_data": {
            "keyframes": {
                str(frame): {str(pos): decile for pos, decile in pos_decile.items()}
                for frame, pos_decile in frame_data["keyframes"].items()
            },
            "delta_frames": {
                str(frame): {str(pos): decile for pos, decile in pos_decile.items()}
                for frame, pos_decile in frame_data["delta_frames"].items()
            },
            "sorted_positions": [list(pos) for pos in frame_data["sorted_positions"]],
            "keyframe_interval": frame_data["keyframe_interval"],
            "scaled_size": frame_data["scaled_size"]
        },
        "frame_string": frame_string_data  # 一位一组的拼接字符串
    }

    # 保存JSON（进一步压缩体积）
    with open("white_decile_lightweight.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, separators=(",", ":"))
    print("轻量化十分位数据已保存至 white_decile_lightweight.json")