import os
import sys
import struct
from pathlib import Path
from typing import List

class ApateDecryptor:
    def __init__(self):
        self.mask_length_indicator_length = 4  # 面具长度标记长度，与C#代码保持一致
        
    def bytes_to_int(self, byte_data: bytes) -> int:
        """将字节数组转换为int，与C#的BitConverter.ToInt32对应"""
        return struct.unpack('<I', byte_data)[0]
    
    def reverse_byte_array(self, buffer: bytes) -> bytes:
        """将字节数组逆序排列，与C#的ReverseByteArray对应"""
        return bytes(reversed(buffer))
    
    def reveal_file(self, file_path: str) -> bool:
        """
        还原单个文件
        参数:
            file_path: 伪装文件的路径（应该是.mp4后缀）
        返回:
            bool: 是否成功
        """
        try:
            file_path_obj = Path(file_path)
            
            # 检查文件是否存在
            if not file_path_obj.exists():
                print(f"文件不存在: {file_path}")
                return False
                
            # 获取文件大小
            file_size = file_path_obj.stat().st_size
            
            # 检查文件是否足够大以包含标记
            if file_size <= self.mask_length_indicator_length:
                print(f"文件太小，无法包含面具长度标记: {file_path}")
                return False
            
            with open(file_path, 'rb+') as f:
                # 读取文件末尾的面具长度标记（最后4个字节）
                f.seek(-self.mask_length_indicator_length, 2)
                mask_length_bytes = f.read(self.mask_length_indicator_length)
                
                if len(mask_length_bytes) != self.mask_length_indicator_length:
                    print(f"无法读取面具长度标记: {file_path}")
                    return False
                
                # 转换为面具长度
                mask_head_length = self.bytes_to_int(mask_length_bytes)
                
                # 验证面具长度是否合理
                if mask_head_length <= 0 or mask_head_length >= file_size - self.mask_length_indicator_length:
                    print(f"面具长度无效: {mask_head_length} (文件大小: {file_size})")
                    return False
                
                # 计算原始头部的位置
                original_head_position = file_size - self.mask_length_indicator_length - mask_head_length
                
                if original_head_position < 0 or original_head_position >= file_size:
                    print(f"原始头部位置无效: {original_head_position}")
                    return False
                
                # 读取原始头部
                f.seek(original_head_position)
                original_head = f.read(mask_head_length)
                
                if len(original_head) != mask_head_length:
                    print(f"无法读取完整原始头部: {file_path}")
                    return False
                
                # 计算新文件大小（去掉面具和标记）
                new_file_size = file_size - mask_head_length - self.mask_length_indicator_length
                
                # 将原始头部写回文件开头（需要逆序）
                f.seek(0)
                f.write(self.reverse_byte_array(original_head))
                
                # 截断文件到新大小
                f.truncate(new_file_size)
                
            return True
            
        except Exception as e:
            print(f"解密文件时发生错误 {file_path}: {str(e)}")
            return False
    
    def remove_mp4_extension(self, file_path: str) -> str:
        """
        移除.mp4扩展名
        示例: "1.zip.mp4" -> "1.zip"
        """
        path_obj = Path(file_path)
        
        # 检查文件是否以.mp4结尾
        if path_obj.suffix.lower() == '.mp4':
            # 获取不带.mp4的文件名
            new_name = path_obj.stem
            
            # 如果原文件名类似"xxx.mp4"，stem会去掉.mp4
            # 但如果原文件名类似"1.zip.mp4"，stem是"1.zip"，这正是我们想要的
            
            # 构建新路径
            new_path = str(path_obj.parent / new_name)
            return new_path
        
        return file_path
    
    def process_file(self, file_path: str) -> bool:
        """
        处理单个文件：解密并重命名
        """
        # 首先解密文件
        if self.reveal_file(file_path):
            # 然后重命名文件（去掉.mp4扩展名）
            new_path = self.remove_mp4_extension(file_path)
            
            try:
                Path(file_path).rename(new_path)
                print(f"✓ 已解密并重命名: {Path(file_path).name} -> {Path(new_path).name}")
                return True
            except Exception as e:
                print(f"重命名文件失败 {file_path} -> {new_path}: {str(e)}")
                return False
        else:
            print(f"✗ 解密失败: {Path(file_path).name}")
            return False
    
    def find_all_mp4_files(self, root_path: str) -> List[str]:
        """
        递归查找所有.mp4文件
        """
        mp4_files = []
        root_path_obj = Path(root_path)
        
        if root_path_obj.is_file():
            # 如果是单个文件，检查是否为.mp4
            if root_path_obj.suffix.lower() == '.mp4':
                mp4_files.append(str(root_path_obj))
        elif root_path_obj.is_dir():
            # 如果是目录，递归查找
            for file_path in root_path_obj.rglob('*.mp4'):
                mp4_files.append(str(file_path))
        else:
            print(f"路径不存在: {root_path}")
        
        return mp4_files
    
    def ask_confirmation(self, target_path: str, file_count: int, file_list: List[str]) -> bool:
        """
        显示确认对话框，让用户确认是否继续
        """
        print("\n" + "=" * 60)
        print("⚠️  重要：请仔细确认以下信息")
        print("=" * 60)
        print(f"目标路径: {target_path}")
        print(f"找到 {file_count} 个待处理文件")
        
        # 显示前几个文件作为示例
        max_preview = 5
        print(f"\n文件示例（最多显示{max_preview}个）:")
        for i, file_path in enumerate(file_list[:max_preview]):
            file_name = Path(file_path).name
            print(f"  {i+1}. {file_name}")
        
        if file_count > max_preview:
            print(f"  ... 以及其他 {file_count - max_preview} 个文件")
        
        print("\n" + "!" * 60)
        print("警告：此操作将修改原始文件！")
        print("解密后，.mp4扩展名将被移除")
        print("原始文件将被覆盖，无法撤销！")
        print("!" * 60)
        
        # 询问确认
        print("\n请确认：")
        print("1. 我已备份重要文件")
        print("2. 我确定要处理这些文件")
        print("3. 我了解此操作不可撤销")
        
        while True:
            response = input("\n是否继续？(Y/N): ").strip().upper()
            if response == 'Y' or response == 'YES':
                return True
            elif response == 'N' or response == 'NO':
                return False
            else:
                print("请输入 Y(是) 或 N(否)")
    
    def process_directory(self, dir_path: str) -> dict:
        """
        处理整个目录
        返回: 统计信息字典
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        print(f"开始处理目录: {dir_path}")
        print("-" * 50)
        
        # 查找所有.mp4文件
        mp4_files = self.find_all_mp4_files(dir_path)
        stats['total'] = len(mp4_files)
        
        if not mp4_files:
            print("未找到.mp4文件")
            return stats
        
        # 显示文件列表并请求确认
        if not self.ask_confirmation(dir_path, stats['total'], mp4_files):
            print("\n操作已取消。")
            return stats
        
        print("\n开始处理文件...")
        print("-" * 50)
        
        # 处理每个文件
        for i, file_path in enumerate(mp4_files, 1):
            print(f"[{i}/{stats['total']}] 处理: {Path(file_path).name}")
            
            try:
                if self.process_file(file_path):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"处理文件时发生未预期错误 {file_path}: {str(e)}")
                stats['failed'] += 1
        
        return stats
    
    def main(self):
        """
        主函数：处理拖拽的文件或目录
        """
        print("=" * 60)
        print("Apate 文件解密工具 v2.0")
        print("功能：解密通过Apate伪装的文件")
        print("注意：此操作将修改原始文件，请先备份重要数据！")
        print("=" * 60)
        
        # 获取命令行参数
        if len(sys.argv) < 2:
            print("\n使用方法:")
            print("1. 将文件或文件夹拖拽到本程序图标上")
            print("2. 或在命令行中执行: apate_decryptor.exe [文件/文件夹路径]")
            print("\n程序将：")
            print("  - 递归查找所有子文件夹中的.mp4文件")
            print("  - 请求用户确认操作")
            print("  - 解密文件并移除.mp4扩展名")
            print("\n示例:")
            print("  1.zip.mp4  →  1.zip")
            print("  doc.pdf.mp4  →  doc.pdf")
            input("\n按回车键退出...")
            return
        
        target_path = sys.argv[1]
        
        if not os.path.exists(target_path):
            print(f"错误: 路径不存在 - {target_path}")
            input("按回车键退出...")
            return
        
        # 检查路径有效性
        try:
            path_obj = Path(target_path)
            if not path_obj.exists():
                print(f"错误: 路径无效 - {target_path}")
                input("按回车键退出...")
                return
        except Exception as e:
            print(f"错误: 无法访问路径 - {target_path}")
            print(f"详细信息: {str(e)}")
            input("按回车键退出...")
            return
        
        print(f"\n检测到目标路径: {target_path}")
        
        # 处理路径
        stats = self.process_directory(target_path)
        
        # 输出统计信息
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总计: {stats['total']} 个文件")
        print(f"成功: {stats['success']} 个")
        print(f"失败: {stats['failed']} 个")
        
        if stats['success'] > 0:
            print(f"✓ 成功解密 {stats['success']} 个文件")
        
        if stats['failed'] > 0:
            print(f"\n⚠️  注意: {stats['failed']} 个文件处理失败")
            print("可能原因:")
            print("  - 文件不是通过Apate伪装的")
            print("  - 文件已损坏")
            print("  - 文件权限不足")
        
        print("\n" + "=" * 60)
        print("处理已完成。")
        
        # 等待用户按键退出
        input("按回车键退出...")

if __name__ == "__main__":
    decryptor = ApateDecryptor()
    decryptor.main()