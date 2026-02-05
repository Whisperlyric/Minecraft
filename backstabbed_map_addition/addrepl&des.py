def process_mcfunction(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            line = line.rstrip()  # 移除行尾的换行符和空白
            if not line:  # 如果是空行，直接写入
                outfile.write('\n')
                continue
                
            if '_door' in line:
                # 如果行中包含"_door"，在末尾添加" destroy"
                processed_line = line + ' destroy\n'
            else:
                # 否则在末尾添加" replace"
                processed_line = line + ' replace\n'
            
            outfile.write(processed_line)

# 使用示例
input_filename = 'output.txt'  # 输入文件名
output_filename = 'reset.mcfunction'  # 输出文件名

process_mcfunction(input_filename, output_filename)