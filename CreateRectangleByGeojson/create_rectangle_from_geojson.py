#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从GeoJSON文件创建矩形面工具 - 批量处理版本
支持批量处理目录下所有GeoJSON文件，生成对应的矩形面文件
"""

import json
import sys
import os
import glob
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

class GeoJsonBatchProcessor:
    """GeoJSON批量处理器"""
    
    def __init__(self):
        self.supported_formats = ['.geojson', '.json']
        self.processed_count = 0
        self.error_files = []
        self.success_files = []
    
    def validate_geojson_file(self, file_path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """验证GeoJSON文件格式"""
        try:
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}", None
            
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return False, f"不支持的文件格式: {file_ext}", None
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, f"文件为空: {file_path}", None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            if not isinstance(geojson_data, dict):
                return False, f"GeoJSON数据必须是对象格式: {file_path}", None
            
            if 'type' not in geojson_data:
                return False, f"缺少必需的'type'字段: {file_path}", None
            
            geojson_type = geojson_data.get('type', '').lower()
            valid_types = ['point', 'linestring', 'polygon', 'multipoint', 'multilinestring', 
                          'multipolygon', 'geometrycollection', 'feature', 'featurecollection']
            
            if geojson_type not in valid_types:
                return False, f"无效的GeoJSON类型 '{geojson_type}': {file_path}", None
            
            if not self._has_valid_coordinates(geojson_data):
                return False, f"缺少有效的坐标数据: {file_path}", None
            
            return True, "", geojson_data
            
        except json.JSONDecodeError as e:
            return False, f"JSON格式错误: {str(e)} - {file_path}", None
        except UnicodeDecodeError as e:
            return False, f"文件编码错误，请确保使用UTF-8编码: {str(e)} - {file_path}", None
        except Exception as e:
            return False, f"读取文件时出错: {str(e)} - {file_path}", None
    
    def _has_valid_coordinates(self, geojson_data: Dict[str, Any]) -> bool:
        """检查GeoJSON数据是否包含有效的坐标"""
        coordinates = []
        
        def extract_coordinates(obj):
            if isinstance(obj, list):
                if len(obj) > 0 and isinstance(obj[0], (int, float)):
                    coordinates.append(obj)
                else:
                    for item in obj:
                        extract_coordinates(item)
        
        geojson_type = geojson_data.get('type', '').lower()
        
        if geojson_type == 'featurecollection':
            for feature in geojson_data.get('features', []):
                geometry = feature.get('geometry', {})
                extract_coordinates(geometry.get('coordinates', []))
        elif geojson_type == 'feature':
            geometry = geojson_data.get('geometry', {})
            extract_coordinates(geometry.get('coordinates', []))
        else:
            extract_coordinates(geojson_data.get('coordinates', []))
        
        return len(coordinates) > 0
    
    def calculate_bounds(self, geojson_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算GeoJSON数据的边界信息"""
        coordinates = []
        
        def extract_coordinates(obj):
            if isinstance(obj, list):
                if len(obj) > 0 and isinstance(obj[0], (int, float)):
                    coordinates.append(obj)
                else:
                    for item in obj:
                        extract_coordinates(item)
        
        geojson_type = geojson_data.get('type', '').lower()
        
        if geojson_type == 'featurecollection':
            for feature in geojson_data.get('features', []):
                geometry = feature.get('geometry', {})
                extract_coordinates(geometry.get('coordinates', []))
        elif geojson_type == 'feature':
            geometry = geojson_data.get('geometry', {})
            extract_coordinates(geometry.get('coordinates', []))
        else:
            extract_coordinates(geojson_data.get('coordinates', []))
        
        if not coordinates:
            raise ValueError("未找到有效的坐标数据")
        
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        
        corners = {
            '西南角 (SW)': [min_lon, min_lat],
            '西北角 (NW)': [min_lon, max_lat],
            '东北角 (NE)': [max_lon, max_lat],
            '东南角 (SE)': [max_lon, min_lat]
        }
        
        bounds_info = {
            "bounds": {
                "min_lon": min_lon,
                "max_lon": max_lon,
                "min_lat": min_lat,
                "max_lat": max_lat
            },
            "corners": corners,
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "center": [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2],
            "width": max_lon - min_lon,
            "height": max_lat - min_lat
        }
        
        return bounds_info
    
    def create_rectangle_geojson(self, bounds_info: Dict[str, Any], source_filename: str) -> Dict[str, Any]:
        """通过边界信息创建矩形面GeoJSON"""
        corners = bounds_info['corners']
        
        rectangle_coordinates = [
            corners['西南角 (SW)'],
            corners['西北角 (NW)'],
            corners['东北角 (NE)'],
            corners['东南角 (SE)'],
            corners['西南角 (SW)']
        ]
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [rectangle_coordinates]
            },
            "properties": {
                "name": f"{source_filename}四角边框矩形面",
                "description": f"通过{source_filename}边界数据生成的矩形面",
                "source_file": source_filename,
                "bounds": bounds_info['bounds'],
                "center": bounds_info['center'],
                "width": bounds_info['width'],
                "height": bounds_info['height'],
                "bbox": bounds_info['bbox']
            }
        }
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": [feature]
        }
        
        return geojson_data
    
    def save_rectangle_geojson(self, geojson_data: Dict[str, Any], output_path: str, filename: str):
        """保存矩形面GeoJSON文件"""
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            
            output_file = os.path.join(output_path, filename)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已生成: {filename}")
            
        except Exception as e:
            print(f"❌ 保存文件时出错: {str(e)} - {filename}")
            raise
    
    def print_bounds_info(self, bounds_info: Dict[str, Any], source_file: str):
        """打印边界信息"""
        bounds = bounds_info['bounds']
        center = bounds_info['center']
        
        print(f"  📍 边界范围: {bounds['min_lon']:.6f}° ~ {bounds['max_lon']:.6f}° (经度), {bounds['min_lat']:.6f}° ~ {bounds['max_lat']:.6f}° (纬度)")
        print(f"  🎯 中心点: [{center[0]:.6f}, {center[1]:.6f}]")
        print(f"  📏 尺寸: {bounds_info['width']:.6f}° × {bounds_info['height']:.6f}°")
    
    def process_directory(self, input_dir: str, output_dir: str):
        """批量处理目录下的所有GeoJSON文件"""
        print(f"🔍 正在扫描目录: {input_dir}")
        
        geojson_files = []
        for ext in self.supported_formats:
            pattern = os.path.join(input_dir, f"*{ext}")
            geojson_files.extend(glob.glob(pattern))
        
        if not geojson_files:
            print(f"❌ 在目录 {input_dir} 中未找到任何GeoJSON文件")
            return
        
        print(f"📁 找到 {len(geojson_files)} 个GeoJSON文件")
        print("=" * 80)
        
        print("🔍 正在验证文件格式...")
        valid_files = []
        
        for file_path in geojson_files:
            filename = os.path.basename(file_path)
            print(f"  检查: {filename}")
            
            is_valid, error_msg, geojson_data = self.validate_geojson_file(file_path)
            
            if is_valid:
                valid_files.append((file_path, geojson_data))
                print(f"  ✅ 格式正确")
            else:
                self.error_files.append((file_path, error_msg))
                print(f"  ❌ 格式错误: {error_msg}")
        
        if self.error_files:
            print("\n" + "=" * 80)
            print("❌ 发现格式错误的文件，程序停止执行")
            print("请手动处理以下文件后重新运行程序:")
            print("-" * 80)
            
            for file_path, error_msg in self.error_files:
                filename = os.path.basename(file_path)
                print(f"文件: {filename}")
                print(f"错误: {error_msg}")
                print("-" * 40)
            
            sys.exit(1)
        
        print(f"\n✅ 所有文件验证通过，开始处理...")
        print("=" * 80)
        
        for file_path, geojson_data in valid_files:
            try:
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                output_filename = f"{name_without_ext}四角边框矩形面.geojson"
                
                print(f"\n📄 处理文件: {filename}")
                
                bounds_info = self.calculate_bounds(geojson_data)
                self.print_bounds_info(bounds_info, filename)
                
                rectangle_geojson = self.create_rectangle_geojson(bounds_info, name_without_ext)
                self.save_rectangle_geojson(rectangle_geojson, output_dir, output_filename)
                
                self.success_files.append(filename)
                self.processed_count += 1
                
            except Exception as e:
                print(f"❌ 处理文件时出错: {str(e)} - {filename}")
                self.error_files.append((file_path, str(e)))
        
        self.print_summary()
    
    def print_summary(self):
        """打印处理结果摘要"""
        print("\n" + "=" * 80)
        print("📊 处理结果摘要")
        print("=" * 80)
        print(f"✅ 成功处理: {self.processed_count} 个文件")
        
        if self.success_files:
            print("\n📁 成功生成的文件:")
            for filename in self.success_files:
                print(f"  - {filename}")
        
        if self.error_files:
            print(f"\n❌ 处理失败: {len(self.error_files)} 个文件")
            for file_path, error_msg in self.error_files:
                filename = os.path.basename(file_path)
                print(f"  - {filename}: {error_msg}")
        
        print("=" * 80)

def print_usage():
    """打印使用说明"""
    print("🔲 GeoJSON矩形面批量创建器")
    print("=" * 50)
    print("用法: python create_rectangle_from_geojson.py <输入目录> <输出目录>")
    print()
    print("参数说明:")
    print("  <输入目录>  包含GeoJSON文件的目录绝对路径")
    print("  <输出目录>  生成文件的保存目录绝对路径")
    print()
    print("示例:")
    print("  python create_rectangle_from_geojson.py C:\\data\\geojson C:\\output\\rectangles")
    print("  python create_rectangle_from_geojson.py /home/user/data /home/user/output")
    print()
    print("功能:")
    print("  - 批量处理目录下所有GeoJSON文件")
    print("  - 生成对应的矩形面文件")
    print("  - 文件名格式: 原文件名 + '四角边框矩形面'")
    print("  - 自动验证文件格式，遇到错误文件时停止处理")
    print("=" * 50)

def main():
    """主函数"""
    if len(sys.argv) != 3:
        print_usage()
        sys.exit(1)
    
    input_dir = sys.argv[1].strip().strip('"')
    output_dir = sys.argv[2].strip().strip('"')
    
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        sys.exit(1)
    
    if not os.path.isdir(input_dir):
        print(f"❌ 输入路径不是目录: {input_dir}")
        sys.exit(1)
    
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 创建输出目录: {output_dir}")
    except Exception as e:
        print(f"❌ 无法创建输出目录: {str(e)}")
        sys.exit(1)
    
    processor = GeoJsonBatchProcessor()
    
    try:
        processor.process_directory(input_dir, output_dir)
        print(f"\n🎉 批量处理完成！")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 