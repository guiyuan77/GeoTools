#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Excel文件中的几何数据创建矩形面工具 - 批量处理版本
支持处理Excel文件中的几何数据，自动识别格式并计算边界矩形
"""

import json
import sys
import os
import glob
import re
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Union
from pathlib import Path

class GeometryProcessor:
    """几何数据处理器"""
    
    def __init__(self, geometry_field_name: str = 'geom'):
        self.supported_excel_formats = ['.csv', '.xlsx', '.xls']
        self.geometry_field_name = geometry_field_name
        self.processed_count = 0
        self.error_files = []
        self.success_files = []
    
    def detect_geometry_format(self, geom_str: str) -> Tuple[str, Dict[str, Any]]:
        """
        检测几何数据的格式
        
        Args:
            geom_str: 几何数据字符串
            
        Returns:
            (格式类型, 解析后的几何数据)
        """
        if not geom_str or pd.isna(geom_str):
            return "empty", {}
        
        geom_str = str(geom_str).strip()
        
        # 检测GeoJSON格式
        if self._is_geojson(geom_str):
            return "geojson", self._parse_geojson(geom_str)
        
        # 检测WKT格式
        if self._is_wkt(geom_str):
            return "wkt", self._parse_wkt(geom_str)
        
        # 检测JSON格式
        if self._is_json(geom_str):
            return "json", self._parse_json(geom_str)
        
        # 检测坐标对格式 (经度,纬度)
        if self._is_coordinate_pair(geom_str):
            return "coordinate_pair", self._parse_coordinate_pair(geom_str)
        
        # 检测坐标数组格式 [经度,纬度]
        if self._is_coordinate_array(geom_str):
            return "coordinate_array", self._parse_coordinate_array(geom_str)
        
        return "unknown", {}
    
    def _is_geojson(self, geom_str: str) -> bool:
        """检测是否为GeoJSON格式"""
        try:
            data = json.loads(geom_str)
            return isinstance(data, dict) and 'type' in data
        except:
            return False
    
    def _is_wkt(self, geom_str: str) -> bool:
        """检测是否为WKT格式"""
        # 清理字符串，移除换行符和多余空格
        cleaned_str = re.sub(r'\s+', ' ', geom_str.strip())
        
        # 更宽松的WKT模式匹配，支持嵌套括号
        wkt_patterns = [
            r'^POINT\s*\(.*\)$',
            r'^LINESTRING\s*\(.*\)$',
            r'^POLYGON\s*\(.*\)$',
            r'^MULTIPOINT\s*\(.*\)$',
            r'^MULTILINESTRING\s*\(.*\)$',
            r'^MULTIPOLYGON\s*\(.*\)$'
        ]
        return any(re.match(pattern, cleaned_str.upper()) for pattern in wkt_patterns)
    
    def _is_json(self, geom_str: str) -> bool:
        """检测是否为JSON格式"""
        try:
            json.loads(geom_str)
            return True
        except:
            return False
    
    def _is_coordinate_pair(self, geom_str: str) -> bool:
        """检测是否为坐标对格式 (经度,纬度)"""
        pattern = r'^\s*\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)\s*$'
        return bool(re.match(pattern, geom_str))
    
    def _is_coordinate_array(self, geom_str: str) -> bool:
        """检测是否为坐标数组格式 [经度,纬度]"""
        pattern = r'^\s*\[\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\]\s*$'
        return bool(re.match(pattern, geom_str))
    
    def _parse_geojson(self, geom_str: str) -> Dict[str, Any]:
        """解析GeoJSON格式"""
        try:
            data = json.loads(geom_str)
            return self._extract_coordinates_from_geojson(data)
        except Exception as e:
            raise ValueError(f"GeoJSON解析错误: {str(e)}")
    
    def _parse_wkt(self, geom_str: str) -> Dict[str, Any]:
        """解析WKT格式"""
        try:
            coordinates = []
            
            # 处理复杂的WKT格式（如MULTIPOLYGON）
            # 移除所有多余的括号，提取所有坐标对
            # 使用更灵活的正则表达式来匹配坐标对
            coord_pairs = re.findall(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', geom_str)
            
            if not coord_pairs:
                raise ValueError("无法提取WKT坐标")
            
            for lon, lat in coord_pairs:
                try:
                    coordinates.append([float(lon), float(lat)])
                except ValueError:
                    continue  # 跳过无效的坐标
            
            if not coordinates:
                raise ValueError("没有找到有效的坐标")
            
            return {"coordinates": coordinates}
        except Exception as e:
            raise ValueError(f"WKT解析错误: {str(e)}")
    
    def _parse_json(self, geom_str: str) -> Dict[str, Any]:
        """解析JSON格式"""
        try:
            data = json.loads(geom_str)
            if isinstance(data, list):
                # 假设是坐标数组
                return {"coordinates": data}
            elif isinstance(data, dict):
                # 假设是几何对象
                return self._extract_coordinates_from_geojson(data)
            else:
                raise ValueError("不支持的JSON格式")
        except Exception as e:
            raise ValueError(f"JSON解析错误: {str(e)}")
    
    def _parse_coordinate_pair(self, geom_str: str) -> Dict[str, Any]:
        """解析坐标对格式"""
        try:
            # 提取数字
            numbers = re.findall(r'-?\d+\.?\d*', geom_str)
            if len(numbers) >= 2:
                lon, lat = float(numbers[0]), float(numbers[1])
                return {"coordinates": [[lon, lat]]}
            else:
                raise ValueError("坐标对格式错误")
        except Exception as e:
            raise ValueError(f"坐标对解析错误: {str(e)}")
    
    def _parse_coordinate_array(self, geom_str: str) -> Dict[str, Any]:
        """解析坐标数组格式"""
        try:
            # 提取数字
            numbers = re.findall(r'-?\d+\.?\d*', geom_str)
            if len(numbers) >= 2:
                lon, lat = float(numbers[0]), float(numbers[1])
                return {"coordinates": [[lon, lat]]}
            else:
                raise ValueError("坐标数组格式错误")
        except Exception as e:
            raise ValueError(f"坐标数组解析错误: {str(e)}")
    
    def _extract_coordinates_from_geojson(self, geojson_data: Dict[str, Any]) -> Dict[str, Any]:
        """从GeoJSON数据中提取坐标"""
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
        
        return {"coordinates": coordinates}
    
    def calculate_bounds(self, coordinates: List[List[float]]) -> Dict[str, Any]:
        """计算坐标的边界信息"""
        if not coordinates:
            raise ValueError("没有有效的坐标数据")
        
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        
        bounds_info = {
            "top_left_longitude": min_lon,
            "top_left_latitude": max_lat,
            "bottom_left_longitude": min_lon,
            "bottom_left_latitude": min_lat,
            "top_right_longitude": max_lon,
            "top_right_latitude": max_lat,
            "bottom_right_longitude": max_lon,
            "bottom_right_latitude": min_lat,
            "center": [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2],
            "width": max_lon - min_lon,
            "height": max_lat - min_lat
        }
        
        return bounds_info
    
    def process_excel_file(self, input_file: str, output_dir: str = None):
        """处理Excel文件中的几何数据"""
        try:
            print(f"📄 正在读取文件: {input_file}")
            
            # 读取Excel文件
            if input_file.lower().endswith('.csv'):
                df = pd.read_csv(input_file, encoding='utf-8')
            else:
                df = pd.read_excel(input_file)
            
            print(f"✅ 成功读取文件，共 {len(df)} 行数据")
            
            # 检查是否存在几何数据字段
            if self.geometry_field_name not in df.columns:
                raise ValueError(f"文件中未找到'{self.geometry_field_name}'字段")
            
            print("🔍 正在处理几何数据...")
            
            # 新增字段
            new_columns = [
                'top_left_longitude', 'top_left_latitude',
                'bottom_left_longitude', 'bottom_left_latitude',
                'top_right_longitude', 'top_right_latitude',
                'bottom_right_longitude', 'bottom_right_latitude'
            ]
            
            for col in new_columns:
                df[col] = None
            
            # 处理每一行数据
            processed_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    geom_str = row[self.geometry_field_name]
                    
                    # 检测几何格式
                    format_type, parsed_data = self.detect_geometry_format(geom_str)
                    
                    if format_type == "empty":
                        print(f"  ⚠️ 第 {index+1} 行: 几何数据为空")
                        continue
                    elif format_type == "unknown":
                        print(f"  ❌ 第 {index+1} 行: 无法识别的几何格式")
                        error_count += 1
                        continue
                    
                    # 计算边界
                    coordinates = parsed_data.get('coordinates', [])
                    if not coordinates:
                        print(f"  ❌ 第 {index+1} 行: 无法提取坐标数据")
                        error_count += 1
                        continue
                    
                    bounds_info = self.calculate_bounds(coordinates)
                    
                    # 更新数据
                    df.at[index, 'top_left_longitude'] = bounds_info['top_left_longitude']
                    df.at[index, 'top_left_latitude'] = bounds_info['top_left_latitude']
                    df.at[index, 'bottom_left_longitude'] = bounds_info['bottom_left_longitude']
                    df.at[index, 'bottom_left_latitude'] = bounds_info['bottom_left_latitude']
                    df.at[index, 'top_right_longitude'] = bounds_info['top_right_longitude']
                    df.at[index, 'top_right_latitude'] = bounds_info['top_right_latitude']
                    df.at[index, 'bottom_right_longitude'] = bounds_info['bottom_right_longitude']
                    df.at[index, 'bottom_right_latitude'] = bounds_info['bottom_right_latitude']
                    
                    processed_count += 1
                    
                    if (index + 1) % 100 == 0:
                        print(f"  📊 已处理 {index + 1} 行数据...")
                
                except Exception as e:
                    print(f"  ❌ 第 {index+1} 行处理失败: {str(e)}")
                    error_count += 1
            
            # 生成输出文件名
            input_path = Path(input_file)
            output_filename = f"{input_path.stem}_with_bounds{input_path.suffix}"
            
            if output_dir:
                output_path = Path(output_dir) / output_filename
            else:
                output_path = input_path.parent / output_filename
            
            # 保存文件
            if input_file.lower().endswith('.csv'):
                df.to_csv(output_path, index=False, encoding='utf-8')
            else:
                df.to_excel(output_path, index=False)
            
            print(f"✅ 已生成: {output_filename}")
            print(f"📊 处理结果: 成功 {processed_count} 行，失败 {error_count} 行")
            
            return output_path
            
        except Exception as e:
            print(f"❌ 处理文件时出错: {str(e)}")
            raise
    
    def validate_excel_file(self, file_path: str) -> Tuple[bool, str]:
        """验证Excel文件"""
        try:
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"
            
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_excel_formats:
                return False, f"不支持的文件格式: {file_ext}"
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, f"文件为空: {file_path}"
            
            # 尝试读取文件
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)
            
            if self.geometry_field_name not in df.columns:
                return False, f"文件中未找到'{self.geometry_field_name}'字段"
            
            return True, ""
            
        except Exception as e:
            return False, f"文件验证失败: {str(e)}"
    
    def process_directory(self, input_dir: str, output_dir: str = None, geometry_field_name: str = 'geom'):
        """批量处理目录下的所有Excel文件"""
        # 更新几何字段名
        self.geometry_field_name = geometry_field_name
        print(f"🔍 正在扫描目录: {input_dir}")
        
        excel_files = []
        for ext in self.supported_excel_formats:
            pattern = os.path.join(input_dir, f"*{ext}")
            excel_files.extend(glob.glob(pattern))
        
        if not excel_files:
            print(f"❌ 在目录 {input_dir} 中未找到任何Excel文件")
            return
        
        print(f"📁 找到 {len(excel_files)} 个Excel文件")
        print("=" * 80)
        
        print("🔍 正在验证文件格式...")
        valid_files = []
        
        for file_path in excel_files:
            filename = os.path.basename(file_path)
            print(f"  检查: {filename}")
            
            is_valid, error_msg = self.validate_excel_file(file_path)
            
            if is_valid:
                valid_files.append(file_path)
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
        
        for file_path in valid_files:
            try:
                filename = os.path.basename(file_path)
                print(f"\n📄 处理文件: {filename}")
                
                output_path = self.process_excel_file(file_path, output_dir)
                
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
    print("🔲 Excel几何数据矩形面批量创建器")
    print("=" * 50)
    print("用法: python create_rectangle_from_geojson.py <输入目录> [输出目录] [几何字段名]")
    print()
    print("参数说明:")
    print("  <输入目录>    包含Excel文件的目录绝对路径")
    print("  [输出目录]    生成文件的保存目录绝对路径（可选，默认保存到原目录）")
    print("  [几何字段名]  几何数据字段名（可选，默认为'geom'）")
    print()
    print("示例:")
    print("  python create_rectangle_from_geojson.py C:\\data\\excel C:\\output")
    print("  python create_rectangle_from_geojson.py C:\\data\\excel C:\\output geometry")
    print("  python create_rectangle_from_geojson.py /home/user/data")
    print("  python create_rectangle_from_geojson.py /home/user/data /home/user/output coordinates")
    print()
    print("功能:")
    print("  - 批量处理目录下所有Excel文件(.csv, .xlsx)")
    print("  - 自动识别指定字段中的几何格式")
    print("  - 计算最小可包围矩形边框")
    print("  - 新增8个坐标字段到输出文件")
    print("  - 支持GeoJSON、WKT、JSON等多种格式")
    print("  - 支持自定义几何数据字段名")
    print("=" * 50)

def main():
    """主函数"""
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print_usage()
        sys.exit(1)
    
    input_dir = sys.argv[1].strip().strip('"')
    output_dir = sys.argv[2].strip().strip('"') if len(sys.argv) >= 3 else None
    geometry_field_name = sys.argv[3].strip().strip('"') if len(sys.argv) == 4 else 'geom'
    
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        sys.exit(1)
    
    if not os.path.isdir(input_dir):
        print(f"❌ 输入路径不是目录: {input_dir}")
        sys.exit(1)
    
    if output_dir:
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"📁 创建输出目录: {output_dir}")
        except Exception as e:
            print(f"❌ 无法创建输出目录: {str(e)}")
            sys.exit(1)
    
    processor = GeometryProcessor(geometry_field_name)
    
    try:
        processor.process_directory(input_dir, output_dir, geometry_field_name)
        print(f"\n🎉 批量处理完成！")
        print(f"📝 使用的几何字段名: {geometry_field_name}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()