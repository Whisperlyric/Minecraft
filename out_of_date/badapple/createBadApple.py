import cv2
import os


def generate_badapple_mcfunction(video_path, n, version_name, start_x, start_z, y):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Couldn't open video")

    video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    scaled_width = video_width // n
    scaled_height = video_height // n

    output_root = f"function/{version_name}"
    os.makedirs(output_root, exist_ok=True)
    frame_count = 0

    init_function_path = os.path.join(output_root, "start.mcfunction")
    with open(init_function_path, "w", encoding="utf-8") as f:
        f.write(f"fill {start_x} {y} {start_z} {start_x + scaled_width - 1} {y} {start_z + scaled_height - 1} minecraft:black_concrete\n")
        f.write(f"schedule function badapple:badapple-template/0 1t\n")
    print(f"已生成初始化帧：{init_function_path}")

    end_function_path = os.path.join(output_root, "clean.mcfunction")
    with open(end_function_path, "w", encoding="utf-8") as f:
        f.write(f"fill {start_x} {y} {start_z} {start_x + scaled_width- 1} {y} {start_z + scaled_height - 1} minecraft:air\n")
    print(f"已生成清除函数：{end_function_path}")

    previous_frame_blocks = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        current_frame_blocks = {}
        function_content=[]

        for i in range(scaled_height):
            for j in range(scaled_width):
                mc_x = j + start_x
                mc_z = i + start_z
                pos = (mc_x, y, mc_z)

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

                current_block = "minecraft:black_concrete" if (
                            black_pixels / total_pixels > 0.5) else "minecraft:white_concrete"
                current_frame_blocks[pos] = current_block

                if frame_count>30 and (pos not in previous_frame_blocks or previous_frame_blocks[pos] != current_block):
                    cmd = f"setblock {mc_x} {y} {mc_z} {current_block}"
                    function_content.append(cmd)

        if frame_count < video_length - 1:
            function_content.append(f"schedule function badapple:badapple-template/{frame_count+1} 1t")

        function_path = os.path.join(output_root, f"{frame_count}.mcfunction")
        with open(function_path, "w", encoding="utf-8") as f:
            f.write("\n".join(function_content))

        previous_frame_blocks = current_frame_blocks.copy()

        frame_count += 1
        print(f"已生成第{frame_count}帧函数：{function_path}")

    cap.release()
    print(f"\n生成完成！共{frame_count}帧，输出路径：{os.path.abspath(output_root)}")


VIDEO_PATH = "badapple.mp4"
PIXEL_BLOCK_SIZE = 12
VERSION_NAME = "badapple-template"

generate_badapple_mcfunction(VIDEO_PATH, PIXEL_BLOCK_SIZE, VERSION_NAME, start_x=0, y=0, start_z=0)