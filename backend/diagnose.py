#!/usr/bin/env python3
"""
WAVE-FIXTURE AI 系统诊断脚本
"""
import sqlite3
import json
import os
from datetime import datetime

print("=" * 60)
print("WAVE-FIXTURE AI 系统诊断")
print("=" * 60)
print()

# 1. 检查后端服务
print("1. 后端服务检查")
print("-" * 60)
try:
    import requests
    response = requests.get("http://localhost:8000/api/health", timeout=2)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 后端服务正常")
        print(f"   应用: {data.get('app_name')}")
        print(f"   版本: {data.get('version')}")
    else:
        print(f"❌ 后端服务异常: HTTP {response.status_code}")
except Exception as e:
    print(f"❌ 无法连接后端: {e}")
print()

# 2. 检查数据库
print("2. 数据库检查")
print("-" * 60)
try:
    conn = sqlite3.connect('fixture_ai.db')
    cursor = conn.cursor()
    
    # 统计任务
    cursor.execute('SELECT COUNT(*) FROM jobs')
    total = cursor.fetchone()[0]
    print(f"✅ 总任务数: {total}")
    
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status="completed"')
    completed = cursor.fetchone()[0]
    print(f"✅ 已完成: {completed}")
    
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status="failed"')
    failed = cursor.fetchone()[0]
    print(f"{'⚠️' if failed > 0 else '✅'} 失败: {failed}")
    
    # 最新任务
    cursor.execute('''
        SELECT id, name, status, progress, 
               analysis_data, result_data, dxf_path
        FROM jobs 
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    row = cursor.fetchone()
    
    if row:
        print()
        print("最新任务:")
        print(f"  ID: {row[0]}")
        print(f"  文件: {row[1]}")
        print(f"  状态: {row[2]}")
        print(f"  进度: {row[3]}%")
        
        if row[4]:  # analysis_data
            analysis = json.loads(row[4])
            print(f"  PCB 尺寸: {analysis['width']} x {analysis['height']} mm")
        
        if row[5]:  # result_data
            result = json.loads(row[5])
            print(f"  治具尺寸: {result['fixtureWidth']} x {result['fixtureHeight']} mm")
        
        if row[6]:  # dxf_path
            if os.path.exists(row[6]):
                size = os.path.getsize(row[6])
                print(f"  DXF: {row[6]} ({size/1024:.1f} KB)")
            else:
                print(f"  ❌ DXF 文件不存在: {row[6]}")
    
    conn.close()
except Exception as e:
    print(f"❌ 数据库错误: {e}")
print()

# 3. 检查文件
print("3. 文件系统检查")
print("-" * 60)

# 上传文件
uploads_dir = "uploads"
if os.path.exists(uploads_dir):
    files = [f for f in os.listdir(uploads_dir) if f.endswith('.zip')]
    print(f"✅ 上传文件: {len(files)} 个")
else:
    print(f"❌ 上传目录不存在")

# 输出文件
outputs_dir = "outputs"
if os.path.exists(outputs_dir):
    dxf_files = [f for f in os.listdir(outputs_dir) if f.endswith('.dxf')]
    svg_files = [f for f in os.listdir(outputs_dir) if f.endswith('.svg')]
    print(f"✅ 生成 DXF: {len(dxf_files)} 个")
    print(f"✅ 生成 SVG: {len(svg_files)} 个")
    
    # 显示最新的 DXF
    if dxf_files:
        dxf_files.sort(key=lambda x: os.path.getmtime(os.path.join(outputs_dir, x)), reverse=True)
        latest = dxf_files[0]
        size = os.path.getsize(os.path.join(outputs_dir, latest))
        print(f"   最新: {latest} ({size/1024:.1f} KB)")
else:
    print(f"❌ 输出目录不存在")
print()

# 4. 检查依赖
print("4. 依赖检查")
print("-" * 60)
dependencies = [
    ('fastapi', 'FastAPI'),
    ('sqlalchemy', 'SQLAlchemy'),
    ('shapely', 'Shapely'),
    ('ezdxf', 'ezdxf'),
    ('numpy', 'NumPy'),
]

for package, name in dependencies:
    try:
        __import__(package)
        print(f"✅ {name}")
    except ImportError:
        print(f"❌ {name} 未安装")
print()

# 5. 总结
print("=" * 60)
print("诊断总结")
print("=" * 60)

issues = []

# 检查服务
try:
    import requests
    response = requests.get("http://localhost:8000/api/health", timeout=2)
    if response.status_code != 200:
        issues.append("后端服务异常")
except:
    issues.append("无法连接后端服务")

# 检查文件
if not os.path.exists(outputs_dir):
    issues.append("输出目录不存在")
elif len(dxf_files) == 0:
    issues.append("没有生成 DXF 文件")

if len(issues) == 0:
    print("✅ 系统运行正常！")
    print()
    print("后端功能完全可用：")
    print("  - API 服务正常")
    print("  - 文件处理正常")
    print("  - DXF 生成正常")
    print()
    print("如果前端显示异常，请检查：")
    print("  1. 浏览器控制台是否有错误")
    print("  2. Network 标签页是否有失败的请求")
    print("  3. 环境变量配置是否正确")
else:
    print("⚠️ 发现以下问题：")
    for issue in issues:
        print(f"  - {issue}")
print()
