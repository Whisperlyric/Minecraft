def convert_line(line):
    # 移除行尾的换行符
    line = line.strip()
    # 如果行是空的，直接返回空行
    if not line:
        return ""
    # 将行分割为命令部分和方块状态部分
    if line.startswith("setblock "):
        # 提取坐标和方块状态部分
        content = line[len("setblock "):]
        # 构造新的execute命令
        return f"execute unless {content} run setblock {content}"
    return line

def convert_file(input_filename, output_filename):
    with open(input_filename, 'r') as infile, open(output_filename, 'w') as outfile:
        for line in infile:
            converted_line = convert_line(line)
            outfile.write(converted_line + '\n')

# 使用示例
input_file = "setblocks.txt"  # 你的输入文件名
output_file = "output.txt"  # 输出文件名

convert_file(input_file, output_file)
print(f"转换完成，结果已写入 {output_file}")