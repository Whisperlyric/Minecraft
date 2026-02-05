import cv2
import os


def get_leaf_litter_state(quadrant_values):
    nw, ne, sw, se = quadrant_values

    count = sum(quadrant_values)

    if count == 1:
        if nw:
            return "[facing=north,segment_amount=1]"
        elif se:
            return "[facing=south,segment_amount=1]"
        elif sw:
            return "[facing=west,segment_amount=1]"
        elif ne:
            return "[facing=east,segment_amount=1]"

    elif count == 2:
        if nw and ne:
            return "[facing=east,segment_amount=2]"
        elif se and sw:
            return "[facing=west,segment_amount=2]"
        elif nw and sw:
            return "[facing=north,segment_amount=2]"
        elif ne and se:
            return "[facing=south,segment_amount=2]"

    elif count == 3:
        if not nw:
            return "[facing=west,segment_amount=3]"
        elif not se:
            return "[facing=east,segment_amount=3]"
        elif not sw:
            return "[facing=south,segment_amount=3]"
        elif not ne:
            return "[facing=north,segment_amount=3]"

    elif count == 4:
        return "[facing=north,segment_amount=4]"

    return None


def generate_badapple_mcfunction(video_path, n, version_name, start_x, start_z, y):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Couldn't open video")

    video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    scaled_width = video_width // n
    scaled_height = video_height // n

    group_width = scaled_width // 2
    group_height = scaled_height // 2

    output_root = f"function/{version_name}"
    os.makedirs(output_root, exist_ok=True)
    frame_count = 0

    init_function_path = os.path.join(output_root, "start.mcfunction")
    with open(init_function_path, "w", encoding="utf-8") as f:
        f.write(
            f"fill {start_x} {y-1} {start_z} {start_x + group_width - 1} {y-1} {start_z + group_height - 1} minecraft:white_concrete\n"
            f"fill {start_x} {y} {start_z} {start_x + group_width - 1} {y} {start_z + group_height - 1} minecraft:leaf_litter[facing=north,segment_amount=4]\n")
        f.write(f"schedule function badapple:badapple-leaf-litter/0 1t\n")
    print(f"已生成初始化帧：{init_function_path}")

    end_function_path = os.path.join(output_root, "clean.mcfunction")
    with open(end_function_path, "w", encoding="utf-8") as f:
        f.write(
            f"fill {start_x} {y} {start_z} {start_x + group_width - 1} {y} {start_z + group_height - 1} minecraft:air\n")
    print(f"已生成清除函数：{end_function_path}")

    previous_frame_blocks = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        pixel_array = []
        for i in range(scaled_height):
            row = []
            for j in range(scaled_width):
                black_pixels = 0
                total_pixels = 0

                for dy in range(n):
                    for dx in range(n):
                        orig_x = j * n + dx
                        orig_y = i * n + dy

                        if orig_x < video_width and orig_y < video_height:
                            if binary[orig_y, orig_x] == 0:
                                black_pixels += 1
                            total_pixels += 1

                row.append(black_pixels / total_pixels > 0.5)
            pixel_array.append(row)

        current_frame_blocks = {}
        function_content = []

        for i in range(0, scaled_height, 2):
            for j in range(0, scaled_width, 2):
                if i + 1 >= scaled_height or j + 1 >= scaled_width:
                    continue

                quadrants = [
                    pixel_array[i][j],
                    pixel_array[i][j + 1],
                    pixel_array[i + 1][j],
                    pixel_array[i + 1][j + 1]
                ]

                leaf_state = get_leaf_litter_state(quadrants)

                mc_x = start_x + (j // 2)
                mc_z = start_z + (i // 2)
                pos = (mc_x, y, mc_z)

                if leaf_state:
                    current_block = f"minecraft:leaf_litter{leaf_state}"
                    current_frame_blocks[pos] = current_block
                else:
                    current_block = "minecraft:air"
                    current_frame_blocks[pos] = current_block

                if frame_count > 30 and (
                        pos not in previous_frame_blocks or previous_frame_blocks[pos] != current_block):
                    cmd = f"setblock {mc_x} {y} {mc_z} {current_block}"
                    function_content.append(cmd)

        if frame_count < video_length - 1:
            function_content.append(f"schedule function badapple:badapple-leaf-litter/{frame_count + 1} 1t")

        function_path = os.path.join(output_root, f"{frame_count}.mcfunction")
        with open(function_path, "w", encoding="utf-8") as f:
            f.write("\n".join(function_content))

        previous_frame_blocks = current_frame_blocks.copy()

        frame_count += 1
        print(f"已生成第{frame_count}帧函数：{function_path}")

    cap.release()
    print(f"\n生成完成！共{frame_count}帧，输出路径：{os.path.abspath(output_root)}")


VIDEO_PATH = "badapple.mp4"
PIXEL_BLOCK_SIZE = 6
VERSION_NAME = "badapple-leaf-litter"

generate_badapple_mcfunction(VIDEO_PATH, PIXEL_BLOCK_SIZE, VERSION_NAME, start_x=0, y=0, start_z=0)