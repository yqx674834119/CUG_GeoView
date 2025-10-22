#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cugrs 测试数据快速准备脚本

本脚本用于快速生成 API 测试所需的合成遥感图像数据。
如果无法获取真实的遥感图像，可以使用此脚本生成模拟数据进行测试。

使用方法:
    python prepare_test_data.py
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random
import argparse


class RemoteSensingImageGenerator:
    """遥感图像生成器"""
    
    def __init__(self, size=(512, 512)):
        self.size = size
        self.colors = {
            'water': [(0, 100, 200), (20, 120, 220), (10, 110, 210)],
            'vegetation': [(50, 150, 50), (70, 180, 70), (30, 120, 30)],
            'urban': [(150, 150, 150), (120, 120, 120), (180, 180, 180)],
            'soil': [(139, 69, 19), (160, 82, 45), (210, 180, 140)],
            'road': [(64, 64, 64), (80, 80, 80), (96, 96, 96)]
        }
    
    def create_base_terrain(self, terrain_type='mixed'):
        """创建基础地形"""
        img = Image.new('RGB', self.size, color=(135, 206, 235))  # 天空蓝
        draw = ImageDraw.Draw(img)
        
        if terrain_type == 'urban':
            return self._create_urban_scene(img, draw)
        elif terrain_type == 'vegetation':
            return self._create_vegetation_scene(img, draw)
        elif terrain_type == 'water':
            return self._create_water_scene(img, draw)
        elif terrain_type == 'agricultural':
            return self._create_agricultural_scene(img, draw)
        else:  # mixed
            return self._create_mixed_scene(img, draw)
    
    def _create_urban_scene(self, img, draw):
        """创建城市场景"""
        # 背景
        draw.rectangle([0, 0, self.size[0], self.size[1]], fill=(200, 200, 200))
        
        # 建筑物
        for _ in range(random.randint(8, 15)):
            x = random.randint(0, self.size[0] - 80)
            y = random.randint(0, self.size[1] - 80)
            w = random.randint(40, 80)
            h = random.randint(40, 80)
            color = random.choice(self.colors['urban'])
            draw.rectangle([x, y, x + w, y + h], fill=color, outline=(0, 0, 0))
        
        # 道路网络
        # 主干道
        draw.rectangle([0, self.size[1]//2 - 15, self.size[0], self.size[1]//2 + 15], 
                      fill=random.choice(self.colors['road']))
        draw.rectangle([self.size[0]//2 - 15, 0, self.size[0]//2 + 15, self.size[1]], 
                      fill=random.choice(self.colors['road']))
        
        # 次干道
        for i in range(3):
            y = random.randint(50, self.size[1] - 50)
            draw.rectangle([0, y - 5, self.size[0], y + 5], 
                          fill=random.choice(self.colors['road']))
        
        return img
    
    def _create_vegetation_scene(self, img, draw):
        """创建植被场景"""
        # 绿色背景
        draw.rectangle([0, 0, self.size[0], self.size[1]], 
                      fill=random.choice(self.colors['vegetation']))
        
        # 森林区域
        for _ in range(random.randint(15, 25)):
            x = random.randint(0, self.size[0] - 40)
            y = random.randint(0, self.size[1] - 40)
            r = random.randint(15, 35)
            color = random.choice(self.colors['vegetation'])
            draw.ellipse([x, y, x + r, y + r], fill=color)
        
        # 小径
        for _ in range(2):
            start_x = random.randint(0, self.size[0])
            start_y = random.randint(0, self.size[1])
            end_x = random.randint(0, self.size[0])
            end_y = random.randint(0, self.size[1])
            draw.line([start_x, start_y, end_x, end_y], 
                     fill=(139, 69, 19), width=random.randint(3, 8))
        
        return img
    
    def _create_water_scene(self, img, draw):
        """创建水体场景"""
        # 水体背景
        draw.rectangle([0, 0, self.size[0], self.size[1]], 
                      fill=random.choice(self.colors['water']))
        
        # 岛屿
        for _ in range(random.randint(2, 5)):
            x = random.randint(50, self.size[0] - 100)
            y = random.randint(50, self.size[1] - 100)
            w = random.randint(30, 80)
            h = random.randint(30, 80)
            color = random.choice(self.colors['soil'])
            draw.ellipse([x, y, x + w, y + h], fill=color)
            
            # 岛上植被
            veg_x = x + w//4
            veg_y = y + h//4
            veg_w = w//2
            veg_h = h//2
            veg_color = random.choice(self.colors['vegetation'])
            draw.ellipse([veg_x, veg_y, veg_x + veg_w, veg_y + veg_h], fill=veg_color)
        
        # 海岸线
        coast_points = []
        for i in range(0, self.size[0], 20):
            y = self.size[1] - 50 + random.randint(-20, 20)
            coast_points.extend([i, y])
        if len(coast_points) >= 4:
            draw.polygon(coast_points + [self.size[0], self.size[1], 0, self.size[1]], 
                        fill=random.choice(self.colors['soil']))
        
        return img
    
    def _create_agricultural_scene(self, img, draw):
        """创建农业场景"""
        # 农田背景
        colors = [(255, 215, 0), (218, 165, 32), (240, 230, 140), (154, 205, 50)]
        
        # 创建农田网格
        grid_size = 60
        for x in range(0, self.size[0], grid_size):
            for y in range(0, self.size[1], grid_size):
                color = random.choice(colors)
                draw.rectangle([x, y, x + grid_size, y + grid_size], fill=color)
        
        # 农田边界（田埂）
        for x in range(0, self.size[0], grid_size):
            draw.line([x, 0, x, self.size[1]], fill=(139, 69, 19), width=2)
        for y in range(0, self.size[1], grid_size):
            draw.line([0, y, self.size[0], y], fill=(139, 69, 19), width=2)
        
        # 农舍
        for _ in range(random.randint(1, 3)):
            x = random.randint(0, self.size[0] - 40)
            y = random.randint(0, self.size[1] - 40)
            draw.rectangle([x, y, x + 30, y + 30], fill=(160, 82, 45), outline=(0, 0, 0))
        
        return img
    
    def _create_mixed_scene(self, img, draw):
        """创建混合场景"""
        # 分区域创建不同地物
        quarter_w = self.size[0] // 2
        quarter_h = self.size[1] // 2
        
        # 左上：植被
        draw.rectangle([0, 0, quarter_w, quarter_h], 
                      fill=random.choice(self.colors['vegetation']))
        for _ in range(5):
            x = random.randint(0, quarter_w - 20)
            y = random.randint(0, quarter_h - 20)
            r = random.randint(10, 20)
            color = random.choice(self.colors['vegetation'])
            draw.ellipse([x, y, x + r, y + r], fill=color)
        
        # 右上：城市
        draw.rectangle([quarter_w, 0, self.size[0], quarter_h], 
                      fill=(200, 200, 200))
        for _ in range(4):
            x = random.randint(quarter_w, self.size[0] - 30)
            y = random.randint(0, quarter_h - 30)
            w = random.randint(20, 40)
            h = random.randint(20, 40)
            color = random.choice(self.colors['urban'])
            draw.rectangle([x, y, x + w, y + h], fill=color)
        
        # 左下：水体
        draw.rectangle([0, quarter_h, quarter_w, self.size[1]], 
                      fill=random.choice(self.colors['water']))
        
        # 右下：农田
        draw.rectangle([quarter_w, quarter_h, self.size[0], self.size[1]], 
                      fill=(255, 215, 0))
        
        # 添加道路连接各区域
        draw.rectangle([quarter_w - 5, 0, quarter_w + 5, self.size[1]], 
                      fill=random.choice(self.colors['road']))
        draw.rectangle([0, quarter_h - 5, self.size[0], quarter_h + 5], 
                      fill=random.choice(self.colors['road']))
        
        return img
    
    def add_noise_and_effects(self, img):
        """添加噪声和效果"""
        # 转换为numpy数组
        pixels = np.array(img)
        
        # 添加高斯噪声
        noise = np.random.normal(0, 8, pixels.shape).astype(np.int16)
        pixels = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # 转换回PIL图像
        img = Image.fromarray(pixels)
        
        # 轻微模糊模拟大气效应
        if random.random() > 0.5:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return img
    
    def create_change_pair(self, base_scene_type='urban'):
        """创建变化检测图像对"""
        # 创建第一张图像
        img1 = self.create_base_terrain(base_scene_type)
        img1 = self.add_noise_and_effects(img1)
        
        # 创建第二张图像（基于第一张）
        img2 = img1.copy()
        draw2 = ImageDraw.Draw(img2)
        
        # 添加变化
        if base_scene_type == 'urban':
            # 新建筑
            for _ in range(random.randint(2, 4)):
                x = random.randint(0, self.size[0] - 60)
                y = random.randint(0, self.size[1] - 60)
                w = random.randint(40, 60)
                h = random.randint(40, 60)
                draw2.rectangle([x, y, x + w, y + h], fill=(255, 0, 0), outline=(0, 0, 0))
        
        elif base_scene_type == 'vegetation':
            # 砍伐区域
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, self.size[0] - 80)
                y = random.randint(0, self.size[1] - 80)
                w = random.randint(60, 80)
                h = random.randint(60, 80)
                draw2.rectangle([x, y, x + w, y + h], fill=(139, 69, 19))
        
        else:  # mixed or other
            # 通用变化：添加新的结构
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, self.size[0] - 50)
                y = random.randint(0, self.size[1] - 50)
                r = random.randint(20, 40)
                draw2.ellipse([x, y, x + r, y + r], fill=(255, 255, 0))
        
        # 添加噪声
        img2 = self.add_noise_and_effects(img2)
        
        return img1, img2


def create_test_dataset(output_dir='test_data', size=(512, 512)):
    """创建完整的测试数据集"""
    print(f"开始创建测试数据集，输出目录: {output_dir}")
    print(f"图像尺寸: {size[0]}x{size[1]}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    generator = RemoteSensingImageGenerator(size)
    
    # 1. 创建单张测试图像（混合场景）
    print("\n1. 创建单张测试图像...")
    single_img = generator.create_base_terrain('mixed')
    single_img = generator.add_noise_and_effects(single_img)
    single_path = os.path.join(output_dir, 'single_image.jpg')
    single_img.save(single_path, quality=90)
    print(f"   ✅ 保存: {single_path}")
    
    # 2. 创建变化检测图像对
    print("\n2. 创建变化检测图像对...")
    img1, img2 = generator.create_change_pair('urban')
    
    pair1_path = os.path.join(output_dir, 'image_pair_1.jpg')
    pair2_path = os.path.join(output_dir, 'image_pair_2.jpg')
    
    img1.save(pair1_path, quality=90)
    img2.save(pair2_path, quality=90)
    
    print(f"   ✅ 保存: {pair1_path}")
    print(f"   ✅ 保存: {pair2_path}")
    
    # 3. 创建批量处理图像
    print("\n3. 创建批量处理图像...")
    batch_scenes = ['vegetation', 'water', 'agricultural']
    
    for i, scene_type in enumerate(batch_scenes, 1):
        batch_img = generator.create_base_terrain(scene_type)
        batch_img = generator.add_noise_and_effects(batch_img)
        
        batch_path = os.path.join(output_dir, f'batch_image_{i}.jpg')
        batch_img.save(batch_path, quality=90)
        print(f"   ✅ 保存: {batch_path} ({scene_type})")
    
    # 4. 创建额外的测试图像（可选）
    print("\n4. 创建额外测试图像...")
    extra_scenes = ['urban', 'mixed']
    
    for i, scene_type in enumerate(extra_scenes, 1):
        extra_img = generator.create_base_terrain(scene_type)
        extra_img = generator.add_noise_and_effects(extra_img)
        
        extra_path = os.path.join(output_dir, f'extra_image_{i}.jpg')
        extra_img.save(extra_path, quality=90)
        print(f"   ✅ 保存: {extra_path} ({scene_type})")
    
    print("\n" + "="*50)
    print("🎉 测试数据集创建完成！")
    print("="*50)
    
    # 显示创建的文件信息
    print("\n📁 创建的文件:")
    total_size = 0
    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith(('.jpg', '.png')):
            filepath = os.path.join(output_dir, filename)
            file_size = os.path.getsize(filepath)
            total_size += file_size
            print(f"   📄 {filename:<20} ({file_size/1024:.1f} KB)")
    
    print(f"\n💾 总大小: {total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)")
    
    print("\n🚀 现在可以运行测试:")
    print("   python test_api_comprehensive.py")
    
    return True


def validate_test_data(data_dir='test_data'):
    """验证测试数据是否完整"""
    required_files = [
        'single_image.jpg',
        'image_pair_1.jpg', 
        'image_pair_2.jpg',
        'batch_image_1.jpg',
        'batch_image_2.jpg', 
        'batch_image_3.jpg'
    ]
    
    print(f"\n🔍 验证测试数据 ({data_dir})...")
    
    missing_files = []
    existing_files = []
    
    for filename in required_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            existing_files.append((filename, file_size))
            print(f"   ✅ {filename} ({file_size/1024:.1f} KB)")
        else:
            missing_files.append(filename)
            print(f"   ❌ {filename} (缺失)")
    
    if missing_files:
        print(f"\n⚠️  缺少 {len(missing_files)} 个文件:")
        for filename in missing_files:
            print(f"   - {filename}")
        return False
    else:
        print(f"\n✅ 所有 {len(required_files)} 个测试文件都存在")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='cugrs 测试数据准备工具')
    parser.add_argument('--output-dir', '-o', default='test_data', 
                       help='输出目录 (默认: test_data)')
    parser.add_argument('--size', '-s', nargs=2, type=int, default=[512, 512],
                       metavar=('WIDTH', 'HEIGHT'),
                       help='图像尺寸 (默认: 512 512)')
    parser.add_argument('--validate', '-v', action='store_true',
                       help='仅验证现有测试数据')
    parser.add_argument('--force', '-f', action='store_true',
                       help='强制重新创建（覆盖现有文件）')
    
    args = parser.parse_args()
    
    print("🌍 cugrs 测试数据准备工具")
    print("=" * 40)
    
    # 如果只是验证
    if args.validate:
        success = validate_test_data(args.output_dir)
        return 0 if success else 1
    
    # 检查是否已存在数据
    if os.path.exists(args.output_dir) and os.listdir(args.output_dir) and not args.force:
        print(f"\n📁 目录 '{args.output_dir}' 已存在且不为空")
        
        # 验证现有数据
        if validate_test_data(args.output_dir):
            print("\n✅ 现有测试数据完整，无需重新创建")
            print("\n💡 提示:")
            print("   - 使用 --force 强制重新创建")
            print("   - 使用 --validate 仅验证数据")
            return 0
        else:
            print("\n⚠️  现有数据不完整，将重新创建...")
    
    # 创建测试数据
    try:
        success = create_test_dataset(
            output_dir=args.output_dir,
            size=tuple(args.size)
        )
        
        if success:
            print("\n🎯 下一步:")
            print("   1. 启动后端服务: python app.py")
            print("   2. 运行测试: python test_api_comprehensive.py")
            return 0
        else:
            print("\n❌ 创建测试数据失败")
            return 1
            
    except Exception as e:
        print(f"\n💥 创建过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())