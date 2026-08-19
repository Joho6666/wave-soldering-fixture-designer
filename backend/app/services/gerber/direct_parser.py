"""
直接 Gerber 文件解析（降级方案）
"""
import zipfile
import re
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from typing import Dict, List, Tuple


def parse_gerber_outline_directly(zip_path: str) -> Dict:
    """
    直接解析 Gerber 文件提取外形
    
    当 gerbonara 无法自动识别时使用此降级方案
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        filenames = [f for f in zf.namelist() 
                    if not f.startswith('__MACOSX') and not f.endswith('/')]
        
        # 查找最可能的外形文件
        outline_candidates = []
        for filename in filenames:
            lower = filename.lower()
            if any(keyword in lower for keyword in [
                'outline', 'gko', 'gm1', 'profile', 'border', 'edge'
            ]):
                outline_candidates.append(filename)
        
        # 尝试解析外形文件
        for outline_file in outline_candidates:
            try:
                content = zf.read(outline_file).decode('utf-8', errors='ignore')
                polygon = _parse_gerber_content_to_polygon(content)
                
                if polygon and polygon.is_valid:
                    bounds = polygon.bounds
                    width = bounds[2] - bounds[0]
                    height = bounds[3] - bounds[1]
                    
                    return {
                        'outline': polygon,
                        'width': width,
                        'height': height,
                        'area': polygon.area,
                        'closed': True
                    }
            except Exception as e:
                print(f"解析 {outline_file} 失败: {e}")
                continue
    
    return None


def _parse_gerber_content_to_polygon(content: str) -> Polygon:
    """
    从 Gerber 文件内容提取多边形
    
    简化实现：提取 D01/D02 指令的坐标点
    """
    lines = content.split('\n')
    
    # 解析坐标
    points = []
    current_x = 0
    current_y = 0
    unit_scale = 1.0  # mm
    
    # 检测单位
    for line in lines:
        if '%MOIN*%' in line:
            unit_scale = 25.4  # inch to mm
        elif '%MOMM*%' in line:
            unit_scale = 1.0
    
    # 坐标格式（通常是 X6Y6 表示整数6位小数6位）
    coord_format = (6, 6)  # 默认
    
    for line in lines:
        line = line.strip()
        
        # 解析格式说明
        if line.startswith('%FS'):
            # %FSLAX46Y46*% 表示前导零，绝对坐标，X和Y都是4位整数6位小数
            match = re.search(r'X(\d)(\d)Y(\d)(\d)', line)
            if match:
                coord_format = (int(match.group(1)) + int(match.group(2)), int(match.group(2)))
        
        # 解析坐标移动
        if 'X' in line or 'Y' in line:
            # 提取 X 坐标
            x_match = re.search(r'X([+-]?\d+)', line)
            if x_match:
                x_raw = int(x_match.group(1))
                current_x = x_raw / (10 ** coord_format[1]) * unit_scale
            
            # 提取 Y 坐标
            y_match = re.search(r'Y([+-]?\d+)', line)
            if y_match:
                y_raw = int(y_match.group(1))
                current_y = y_raw / (10 ** coord_format[1]) * unit_scale
            
            # D01 表示绘制线段到当前点
            if 'D01' in line or 'D1*' in line:
                points.append((current_x, current_y))
    
    # 创建多边形
    if len(points) >= 3:
        try:
            # 尝试创建闭合多边形
            polygon = Polygon(points)
            if polygon.is_valid:
                return polygon
            
            # 如果无效，尝试修复
            polygon = polygon.buffer(0)
            if polygon.is_valid:
                return polygon
        except Exception:
            pass
    
    return None
