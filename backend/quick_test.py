#!/usr/bin/env python3
"""
快速测试脚本 - 直接调用 API
"""
import requests
import time

print("=" * 60)
print("WAVE-FIXTURE AI 快速测试")
print("=" * 60)

# 测试文件
test_file = "D:/Downloads/WAVE_FIXTURE_upload_test_pack.zip"

print(f"\n上传文件: {test_file}")
print("-" * 60)

try:
    # 上传文件
    with open(test_file, 'rb') as f:
        files = {'file': ('test.zip', f, 'application/zip')}
        response = requests.post(
            'http://localhost:8000/api/jobs',
            files=files,
            timeout=30
        )
    
    if response.status_code == 200:
        result = response.json()
        job_id = result['id']
        
        print(f"✅ 上传成功！")
        print(f"   Job ID: {job_id}")
        print(f"   状态: {result['status']}")
        print(f"   进度: {result['progress']}%")
        
        # 等待处理
        print(f"\n等待处理...")
        time.sleep(2)
        
        # 查询状态
        status_response = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"\n✅ 处理状态:")
            print(f"   状态: {status['status']}")
            print(f"   进度: {status['progress']}%")
            
            if status['status'] == 'completed':
                print(f"\n✅ 处理完成！")
                print(f"   可以下载 DXF: http://localhost:8000/api/jobs/{job_id}/result.dxf")
            elif status['status'] == 'failed':
                print(f"\n❌ 处理失败")
                if 'error' in status:
                    print(f"   错误: {status['error']}")
    else:
        print(f"❌ 上传失败: HTTP {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
