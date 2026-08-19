#!/usr/bin/env python3
"""
测试改进后的 Gerber 解析器
"""
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.gerber.parser import GerberParser
import os

print("=" * 60)
print("测试 Gerber 解析器")
print("=" * 60)

# 测试文件
test_files = [
    "uploads/05e58489.zip",
    "uploads/161c2989.zip",
]

parser = GerberParser()

for test_file in test_files:
    if not os.path.exists(test_file):
        print(f"\n跳过（文件不存在）: {test_file}")
        continue
    
    print(f"\n测试文件: {test_file}")
    print("-" * 60)
    
    try:
        result = parser.parse_zip(test_file)
        
        print(f"✅ 解析成功")
        print(f"  PCB 尺寸: {result['width']:.2f} x {result['height']:.2f} mm")
        print(f"  文件数量: {result['fileCount']}")
        print(f"  钻孔数量: {result['holeCount']}")
        print(f"  外形闭合: {'是' if result['outlineClosed'] else '否'}")
        print(f"  面积: {result['outlineAreaMm2']:.2f} mm²")
        print(f"  图层数量: {len(result['layers'])}")
        
        # 检查是否使用了真实解析还是估算
        if result['width'] in [100.0, 150.0, 180.0, 200.0]:
            print(f"  ⚠️ 可能使用了估算模式")
        else:
            print(f"  ✅ 使用了真实解析")
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
