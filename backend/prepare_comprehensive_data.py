#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cugrs 全面测试数据生成脚本
Comprehensive Test Data Generator for Sentinel-2 and Remote Sensing Scenarios

功能:
1. 生成模拟 Sentinel-2 样式的遥感图像 (TIF/JPG格式)
2. 针对不同功能模块生成专用测试数据:
   - 变化检测 (Change Detection): 双时相图像对
   - 目标检测 (Object Detection): 包含特定目标(飞机/油罐等)的图像
   - 地物分类 (Semantic Segmentation): 多类别地物分布图
   - 场景分类 (Scene Classification): 不同场景类别的图像
   - 图像复原 (Image Restoration): 低分辨率/模糊/噪声图像

使用库: PIL, numpy
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import random
import argparse
import json

class Sentinel2Generator:
    """模拟 Sentinel-2 数据的生成器"""
    
    def __init__(self, output_base_dir='test_data_comprehensive'):
        self.base_dir = output_base_dir
        self.size = (1024, 1024) # 模拟 Sentinel-2 标准切片大小
        
        # Sentinel-2 典型假彩色/真彩色配方
        self.colors = {
            'water': (10, 60, 120),       # 深水
            'shallow_water': (60, 140, 200), # 浅水
            'forest': (20, 90, 40),       # 森林
            'grass': (80, 160, 60),       # 草地
            'urban': (180, 180, 175),     # 城市亮灰
            'road': (100, 100, 100),      # 道路深灰
            'agri': (160, 140, 80),       # 农田
            'bare': (140, 120, 100)       # 裸土
        }
        
        # 目标检测颜色
        self.target_colors = {
            'plane': (220, 220, 255),
            'ship': (200, 200, 200),
            'storage_tank': (240, 240, 240),
            'bridge': (160, 160, 160)
        }

        self._init_dirs()

    def _init_dirs(self):
        """初始化目录结构"""
        subdirs = ['change_detection', 'object_detection', 'semantic_segmentation', 
                   'scene_classification', 'image_restoration']
        for d in subdirs:
            path = os.path.join(self.base_dir, d)
            os.makedirs(path, exist_ok=True)

    def _generate_base_map(self, scene_type='mixed'):
        """生成底图"""
        img = Image.new('RGB', self.size, color=self.colors['water']) # 默认水底
        draw = ImageDraw.Draw(img)
        
        # 随机生成地形
        if scene_type == 'urban':
            draw.rectangle([0, 0, self.size[0], self.size[1]], fill=self.colors['urban'])
            self._draw_grid(draw, step=80, width=4, color=self.colors['road']) # 街道
            self._draw_blobs(draw, count=50, min_s=20, max_s=50, color=(140, 140, 140), shape='rect') # 建筑
        elif scene_type == 'forest':
            draw.rectangle([0, 0, self.size[0], self.size[1]], fill=self.colors['forest'])
            self._draw_blobs(draw, count=50, min_s=30, max_s=100, color=self.colors['grass'], shape='ellipse')
        elif scene_type == 'mixed':
            # 分割区域
            draw.rectangle([0, 0, self.size[0], self.size[1]//2], fill=self.colors['forest'])
            draw.rectangle([0, self.size[1]//2, self.size[0], self.size[1]], fill=self.colors['urban'])
            # 河流
            self._draw_river(draw)
        
        return img, draw

    def _draw_grid(self, draw, step=100, width=5, color=(100,100,100)):
        for x in range(0, self.size[0], step):
            draw.line([(x, 0), (x, self.size[1])], fill=color, width=width)
        for y in range(0, self.size[1], step):
            draw.line([(0, y), (self.size[0], y)], fill=color, width=width)

    def _draw_blobs(self, draw, count=10, min_s=10, max_s=30, color=(0,0,0), shape='rect'):
        for _ in range(count):
            x = random.randint(0, self.size[0]-max_s)
            y = random.randint(0, self.size[1]-max_s)
            w = random.randint(min_s, max_s)
            h = random.randint(min_s, max_s)
            if shape == 'rect':
                draw.rectangle([x, y, x+w, y+h], fill=color)
            else:
                draw.ellipse([x, y, x+w, y+h], fill=color)

    def _draw_river(self, draw):
        # 简单模拟河流
        points = []
        y = random.randint(200, 800)
        for x in range(0, 1024, 50):
            y += random.randint(-30, 30)
            points.append((x, y))
        draw.line(points, fill=self.colors['water'], width=40)

    def _save_image(self, img, folder, name_base, fmt='tif'):
        """保存图像，支持 jpg 和 tif"""
        path = os.path.join(self.base_dir, folder, f"{name_base}.{fmt}")
        img.save(path)
        print(f"Generated: {path}")
        return path

    def generate_change_detection_data(self):
        """生成变化检测数据 (Sentinel-2 风格)"""
        print("Generating Change Detection Data...")
        # 1. 城市扩张 (A: 荒地 -> B: 建筑)
        img1, draw1 = self._generate_base_map('forest')
        
        img2 = img1.copy()
        draw2 = ImageDraw.Draw(img2)
        
        # 添加变化区域 (新增建筑)
        for _ in range(10):
            x = random.randint(100, 900)
            y = random.randint(100, 900)
            w, h = 60, 60
            draw2.rectangle([x, y, x+w, y+h], fill=self.colors['urban']) # 变为了水泥地/建筑
        
        self._save_image(img1, 'change_detection', 'city_expansion_T1', 'jpg')
        self._save_image(img2, 'change_detection', 'city_expansion_T2', 'jpg')
        
        # TIF 格式测试
        self._save_image(img1, 'change_detection', 'city_expansion_T1', 'tif')
        self._save_image(img2, 'change_detection', 'city_expansion_T2', 'tif')

    def generate_object_detection_data(self):
        """生成目标检测数据"""
        print("Generating Object Detection Data...")
        img, draw = self._generate_base_map('mixed')
        
        # 绘制飞机 (白色十字)
        for _ in range(5):
            x = random.randint(50, 950)
            y = random.randint(50, 950)
            draw.text((x,y), "+", fill=(255,255,255)) # 极其简化的飞机
            # 实际上画个十字形状
            draw.rectangle([x, y-15, x+4, y+15], fill=self.target_colors['plane'])
            draw.rectangle([x-15, y, x+15, y+4], fill=self.target_colors['plane'])
            
        # 绘制油罐 (圆形)
        for _ in range(8):
            x = random.randint(50, 950)
            y = random.randint(50, 950)
            draw.ellipse([x,y,x+20,y+20], fill=self.target_colors['storage_tank'], outline=(100,100,100))

        self._save_image(img, 'object_detection', 'airport_simulation', 'jpg')
        self._save_image(img, 'object_detection', 'oil_storage_simulation', 'tif')

    def generate_semantic_segmentation_data(self):
        """生成语义分割数据 (地物分类)"""
        print("Generating Semantic Segmentation Data...")
        img, draw = self._generate_base_map('mixed')
        self._save_image(img, 'semantic_segmentation', 'land_cover_sample', 'tif')
        self._save_image(img, 'semantic_segmentation', 'land_cover_sample', 'jpg')

    def generate_scene_classification_data(self):
        """生成场景分类数据"""
        print("Generating Scene Classification Data...")
        scenes = ['urban', 'forest']
        for scene in scenes:
            img, _ = self._generate_base_map(scene)
            self._save_image(img, 'scene_classification', f'scene_{scene}', 'jpg')

    def generate_image_restoration_data(self):
        """生成图像复原数据 (模糊/噪声)"""
        print("Generating Image Restoration Data...")
        img, _ = self._generate_base_map('urban')
        
        # 模糊
        blurred = img.filter(ImageFilter.GaussianBlur(5))
        self._save_image(blurred, 'image_restoration', 'blurred_input', 'jpg')
        
        # 噪声
        np_img = np.array(img)
        noise = np.random.normal(0, 25, np_img.shape)
        noisy_img = np.clip(np_img + noise, 0, 255).astype(np.uint8)
        self._save_image(Image.fromarray(noisy_img), 'image_restoration', 'noisy_input', 'jpg')

    def run_all(self):
        self.generate_change_detection_data()
        self.generate_object_detection_data()
        self.generate_semantic_segmentation_data()
        self.generate_scene_classification_data()
        self.generate_image_restoration_data()
        print("Comprehensive Test Data Generation Complete!")

if __name__ == "__main__":
    generator = Sentinel2Generator(output_base_dir='/home/livablecity/GeoView/backend/test_data_comprehensive')
    generator.run_all()
