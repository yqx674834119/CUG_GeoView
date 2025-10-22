#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cugrs 后端 API 接口全面测试脚本

本脚本测试所有API接口的各种功能和参数组合，包括：
1. 文件上传接口
2. 模型管理接口
3. 分析功能接口（变化检测、目标检测、语义分割、场景分类、图像复原）
4. 图像预处理接口
5. 历史记录接口

使用方法：
1. 确保后端服务已启动 (python app.py)
2. 准备测试数据（参考文档中的测试数据说明）
3. 运行测试：python test_api_comprehensive.py
"""

import requests
import json
import os
import time
from typing import Dict, List, Any, Optional
import unittest
from unittest import TestCase


class cugrsAPITester(TestCase):
    """cugrs API 全面测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.base_url = "http://localhost:5000"
        self.test_data_dir = "test_data"  # 测试数据目录
        self.uploaded_files = []  # 存储上传的文件信息
        
        # 测试图片路径（需要用户提供）
        self.test_images = {
            'single': os.path.join(self.test_data_dir, 'single_image.jpg'),
            'pair_1': os.path.join(self.test_data_dir, 'image_pair_1.jpg'),
            'pair_2': os.path.join(self.test_data_dir, 'image_pair_2.jpg'),
            'batch_1': os.path.join(self.test_data_dir, 'batch_image_1.jpg'),
            'batch_2': os.path.join(self.test_data_dir, 'batch_image_2.jpg'),
            'batch_3': os.path.join(self.test_data_dir, 'batch_image_3.jpg')
        }
        
        # 检查测试数据是否存在
        self._check_test_data()
    
    def _check_test_data(self):
        """检查测试数据是否存在"""
        missing_files = []
        for name, path in self.test_images.items():
            if not os.path.exists(path):
                missing_files.append(f"{name}: {path}")
        
        if missing_files:
            print("\n⚠️  缺少测试数据文件:")
            for file in missing_files:
                print(f"   - {file}")
            print("\n请参考文档准备测试数据后再运行测试。")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """统一的请求方法"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            return {
                'status_code': response.status_code,
                'data': response.json() if response.content else {},
                'success': response.status_code == 200
            }
        except requests.exceptions.RequestException as e:
            return {
                'status_code': 0,
                'data': {'error': str(e)},
                'success': False
            }
    
    def _upload_file(self, file_path: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """上传文件辅助方法"""
        if not os.path.exists(file_path):
            print(f"⚠️  文件不存在: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            files = {'files': f}
            data = {'type': analysis_type}
            result = self._make_request('POST', '/api/file/upload', files=files, data=data)
            
        if result['success'] and result['data'].get('success'):
            uploaded_info = result['data']['data'][0]
            self.uploaded_files.append(uploaded_info)
            return uploaded_info
        return None

    # ==================== 文件上传接口测试 ====================
    
    def test_01_file_upload_change_detection(self):
        """测试文件上传 - 变化检测类型"""
        print("\n🧪 测试文件上传 - 变化检测类型")
        
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
            
        result = self._upload_file(self.test_images['single'], "变化检测")
        self.assertIsNotNone(result, "文件上传失败")
        self.assertIn('src', result, "返回结果缺少src字段")
        self.assertIn('filename', result, "返回结果缺少filename字段")
        self.assertIn('photo_id', result, "返回结果缺少photo_id字段")
        print(f"✅ 上传成功: {result['filename']}")
    
    def test_02_file_upload_all_types(self):
        """测试文件上传 - 所有分析类型"""
        print("\n🧪 测试文件上传 - 所有分析类型")
        
        analysis_types = ["变化检测", "目标检测", "地物分类", "场景分类", "图像复原"]
        
        for analysis_type in analysis_types:
            if not os.path.exists(self.test_images['single']):
                print(f"⚠️  跳过 {analysis_type} - 测试图片不存在")
                continue
                
            result = self._upload_file(self.test_images['single'], analysis_type)
            self.assertIsNotNone(result, f"{analysis_type} 文件上传失败")
            print(f"✅ {analysis_type} 上传成功")
    
    def test_03_file_upload_multiple_files(self):
        """测试多文件上传"""
        print("\n🧪 测试多文件上传")
        
        test_files = [self.test_images['batch_1'], self.test_images['batch_2']]
        existing_files = [f for f in test_files if os.path.exists(f)]
        
        if not existing_files:
            self.skipTest("测试图片不存在")
        
        files = [('files', open(f, 'rb')) for f in existing_files]
        data = {'type': '目标检测'}
        
        try:
            result = self._make_request('POST', '/api/file/upload', files=files, data=data)
            self.assertTrue(result['success'], "多文件上传失败")
            
            if result['data'].get('success'):
                uploaded_count = len(result['data']['data'])
                self.assertEqual(uploaded_count, len(existing_files), "上传文件数量不匹配")
                print(f"✅ 成功上传 {uploaded_count} 个文件")
                
                # 保存上传信息
                self.uploaded_files.extend(result['data']['data'])
        finally:
            # 关闭文件
            for _, f in files:
                f.close()

    # ==================== 模型管理接口测试 ====================
    
    def test_04_get_all_model_types(self):
        """测试获取所有类型的模型列表"""
        print("\n🧪 测试获取所有类型的模型列表")
        
        model_types = [
            'change_detection',
            'classification', 
            'image_restoration',
            'object_detection',
            'semantic_segmentation'
        ]
        
        for model_type in model_types:
            result = self._make_request('GET', f'/api/model/list/{model_type}')
            self.assertTrue(result['success'], f"获取{model_type}模型列表失败")
            
            if result['data'].get('success'):
                models = result['data']['data']
                print(f"✅ {model_type}: 找到 {len(models)} 个模型")
                
                # 验证模型信息结构
                if models:
                    model = models[0]
                    self.assertIn('model_path', model, "模型信息缺少model_path")
                    self.assertIn('model_type', model, "模型信息缺少model_type")
                    self.assertIn('model_name', model, "模型信息缺少model_name")
            else:
                print(f"⚠️  {model_type}: {result['data'].get('msg', '未知错误')}")
    
    def test_05_get_invalid_model_type(self):
        """测试获取无效模型类型"""
        print("\n🧪 测试获取无效模型类型")
        
        result = self._make_request('GET', '/api/model/list/invalid_type')
        # 这里可能返回空列表或错误，根据实际实现调整断言
        print(f"📝 无效模型类型响应: {result['data']}")

    # ==================== 变化检测接口测试 ====================
    
    def test_06_change_detection_basic(self):
        """测试变化检测 - 基础功能"""
        print("\n🧪 测试变化检测 - 基础功能")
        
        # 先获取可用模型
        models_result = self._make_request('GET', '/api/model/list/change_detection')
        if not models_result['success'] or not models_result['data'].get('success'):
            self.skipTest("无法获取变化检测模型")
        
        models = models_result['data']['data']
        if not models:
            self.skipTest("没有可用的变化检测模型")
        
        model_path = models[0]['model_path']
        
        # 上传测试图片对
        if not (os.path.exists(self.test_images['pair_1']) and os.path.exists(self.test_images['pair_2'])):
            self.skipTest("测试图片对不存在")
        
        img1 = self._upload_file(self.test_images['pair_1'], "变化检测")
        img2 = self._upload_file(self.test_images['pair_2'], "变化检测")
        
        if not (img1 and img2):
            self.skipTest("图片上传失败")
        
        # 执行变化检测
        payload = {
            "model_path": model_path,
            "list": [
                {
                    "first": img1['src'],
                    "second": img2['src']
                }
            ],
            "prehandle": 0,
            "denoise": 0,
            "window_size": 256,
            "stride": 128
        }
        
        result = self._make_request('POST', '/api/analysis/change_detection', 
                                  json=payload, 
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "变化检测请求失败")
        print(f"✅ 变化检测请求成功: {result['data']}")
    
    def test_07_change_detection_all_params(self):
        """测试变化检测 - 所有参数组合"""
        print("\n🧪 测试变化检测 - 所有参数组合")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/change_detection')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用变化检测模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 准备图片
        if not (os.path.exists(self.test_images['pair_1']) and os.path.exists(self.test_images['pair_2'])):
            self.skipTest("测试图片对不存在")
        
        img1 = self._upload_file(self.test_images['pair_1'], "变化检测")
        img2 = self._upload_file(self.test_images['pair_2'], "变化检测")
        
        if not (img1 and img2):
            self.skipTest("图片上传失败")
        
        # 测试不同参数组合
        test_cases = [
            {"prehandle": 0, "denoise": 0, "window_size": 256, "stride": 128, "desc": "无预处理无降噪"},
            {"prehandle": 1, "denoise": 0, "window_size": 256, "stride": 128, "desc": "直方图匹配"},
            {"prehandle": 4, "denoise": 0, "window_size": 256, "stride": 128, "desc": "锐化处理"},
            {"prehandle": 0, "denoise": 3, "window_size": 256, "stride": 128, "desc": "中值滤波降噪"},
            {"prehandle": 0, "denoise": 5, "window_size": 256, "stride": 128, "desc": "高斯滤波降噪"},
            {"prehandle": 1, "denoise": 3, "window_size": 512, "stride": 256, "desc": "组合处理大窗口"},
            {"prehandle": 0, "denoise": 0, "window_size": 128, "stride": 64, "desc": "小窗口处理"}
        ]
        
        for i, case in enumerate(test_cases):
            payload = {
                "model_path": model_path,
                "list": [{"first": img1['src'], "second": img2['src']}],
                **{k: v for k, v in case.items() if k != 'desc'}
            }
            
            result = self._make_request('POST', '/api/analysis/change_detection',
                                      json=payload,
                                      headers={'Content-Type': 'application/json'})
            
            print(f"  {i+1}. {case['desc']}: {'✅' if result['success'] else '❌'}")
            if not result['success']:
                print(f"     错误: {result['data']}")
            
            # 添加延时避免请求过快
            time.sleep(1)

    # ==================== 目标检测接口测试 ====================
    
    def test_08_object_detection_basic(self):
        """测试目标检测 - 基础功能"""
        print("\n🧪 测试目标检测 - 基础功能")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/object_detection')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用目标检测模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 上传测试图片
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
        
        img = self._upload_file(self.test_images['single'], "目标检测")
        if not img:
            self.skipTest("图片上传失败")
        
        # 执行目标检测
        payload = {
            "model_path": model_path,
            "list": [img['src']],
            "prehandle": 0,
            "denoise": 0
        }
        
        result = self._make_request('POST', '/api/analysis/object_detection',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "目标检测请求失败")
        print(f"✅ 目标检测请求成功: {result['data']}")
    
    def test_09_object_detection_all_params(self):
        """测试目标检测 - 所有参数组合"""
        print("\n🧪 测试目标检测 - 所有参数组合")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/object_detection')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用目标检测模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 准备多张图片
        test_images = []
        for img_key in ['single', 'batch_1', 'batch_2']:
            if os.path.exists(self.test_images[img_key]):
                uploaded = self._upload_file(self.test_images[img_key], "目标检测")
                if uploaded:
                    test_images.append(uploaded['src'])
        
        if not test_images:
            self.skipTest("没有可用的测试图片")
        
        # 测试不同参数组合
        test_cases = [
            {"prehandle": 0, "denoise": 0, "desc": "无预处理无降噪"},
            {"prehandle": 2, "denoise": 0, "desc": "CLAHE预处理"},
            {"prehandle": 4, "denoise": 0, "desc": "锐化预处理"},
            {"prehandle": 0, "denoise": 3, "desc": "中值滤波降噪"},
            {"prehandle": 0, "denoise": 5, "desc": "高斯滤波降噪"},
            {"prehandle": 2, "denoise": 3, "desc": "CLAHE+中值滤波"}
        ]
        
        for i, case in enumerate(test_cases):
            payload = {
                "model_path": model_path,
                "list": test_images[:2],  # 使用前两张图片
                **{k: v for k, v in case.items() if k != 'desc'}
            }
            
            result = self._make_request('POST', '/api/analysis/object_detection',
                                      json=payload,
                                      headers={'Content-Type': 'application/json'})
            
            print(f"  {i+1}. {case['desc']}: {'✅' if result['success'] else '❌'}")
            if not result['success']:
                print(f"     错误: {result['data']}")
            
            time.sleep(1)

    # ==================== 语义分割接口测试 ====================
    
    def test_10_semantic_segmentation_basic(self):
        """测试语义分割 - 基础功能"""
        print("\n🧪 测试语义分割 - 基础功能")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/semantic_segmentation')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用语义分割模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 上传测试图片
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
        
        img = self._upload_file(self.test_images['single'], "地物分类")
        if not img:
            self.skipTest("图片上传失败")
        
        # 执行语义分割
        payload = {
            "model_path": model_path,
            "list": [img['src']],
            "prehandle": 0,
            "denoise": 0
        }
        
        result = self._make_request('POST', '/api/analysis/semantic_segmentation',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "语义分割请求失败")
        print(f"✅ 语义分割请求成功: {result['data']}")

    # ==================== 场景分类接口测试 ====================
    
    def test_11_classification_basic(self):
        """测试场景分类 - 基础功能"""
        print("\n🧪 测试场景分类 - 基础功能")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/classification')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用分类模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 上传测试图片
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
        
        img = self._upload_file(self.test_images['single'], "场景分类")
        if not img:
            self.skipTest("图片上传失败")
        
        # 执行场景分类
        payload = {
            "model_path": model_path,
            "list": [img['src']]
        }
        
        result = self._make_request('POST', '/api/analysis/classification',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "场景分类请求失败")
        print(f"✅ 场景分类请求成功: {result['data']}")
    
    def test_12_classification_batch(self):
        """测试场景分类 - 批量处理"""
        print("\n🧪 测试场景分类 - 批量处理")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/classification')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用分类模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 准备多张图片
        test_images = []
        for img_key in ['single', 'batch_1', 'batch_2', 'batch_3']:
            if os.path.exists(self.test_images[img_key]):
                uploaded = self._upload_file(self.test_images[img_key], "场景分类")
                if uploaded:
                    test_images.append(uploaded['src'])
        
        if len(test_images) < 2:
            self.skipTest("测试图片数量不足")
        
        # 执行批量分类
        payload = {
            "model_path": model_path,
            "list": test_images
        }
        
        result = self._make_request('POST', '/api/analysis/classification',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "批量场景分类请求失败")
        print(f"✅ 批量场景分类请求成功，处理了 {len(test_images)} 张图片")

    # ==================== 图像复原接口测试 ====================
    
    def test_13_image_restoration_basic(self):
        """测试图像复原 - 基础功能"""
        print("\n🧪 测试图像复原 - 基础功能")
        
        # 获取模型
        models_result = self._make_request('GET', '/api/model/list/image_restoration')
        if not models_result['success'] or not models_result['data'].get('success') or not models_result['data']['data']:
            self.skipTest("无可用图像复原模型")
        
        model_path = models_result['data']['data'][0]['model_path']
        
        # 上传测试图片
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
        
        img = self._upload_file(self.test_images['single'], "图像复原")
        if not img:
            self.skipTest("图片上传失败")
        
        # 执行图像复原
        payload = {
            "model_path": model_path,
            "list": [img['src']]
        }
        
        result = self._make_request('POST', '/api/analysis/image_restoration',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "图像复原请求失败")
        print(f"✅ 图像复原请求成功: {result['data']}")

    # ==================== 图像预处理接口测试 ====================
    
    def test_14_histogram_match(self):
        """测试直方图匹配预处理"""
        print("\n🧪 测试直方图匹配预处理")
        
        # 准备图片对
        if not (os.path.exists(self.test_images['pair_1']) and os.path.exists(self.test_images['pair_2'])):
            self.skipTest("测试图片对不存在")
        
        img1 = self._upload_file(self.test_images['pair_1'], "变化检测")
        img2 = self._upload_file(self.test_images['pair_2'], "变化检测")
        
        if not (img1 and img2):
            self.skipTest("图片上传失败")
        
        # 执行直方图匹配
        payload = {
            "list": [
                {
                    "first": img1['src'],
                    "second": img2['src']
                }
            ],
            "prehandle": 1
        }
        
        result = self._make_request('POST', '/api/analysis/histogram_match',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        self.assertTrue(result['success'], "直方图匹配请求失败")
        print(f"✅ 直方图匹配请求成功: {result['data']}")
    
    def test_15_image_preprocessing(self):
        """测试图像预处理"""
        print("\n🧪 测试图像预处理")
        
        # 上传测试图片
        if not os.path.exists(self.test_images['single']):
            self.skipTest("测试图片不存在")
        
        img = self._upload_file(self.test_images['single'], "目标检测")
        if not img:
            self.skipTest("图片上传失败")
        
        # 测试不同预处理类型
        preprocess_types = [2, 4]  # CLAHE, 锐化
        
        for prehandle in preprocess_types:
            payload = {
                "list": [img['src']],
                "prehandle": prehandle,
                "type": 2
            }
            
            result = self._make_request('POST', '/api/analysis/image_pre',
                                      json=payload,
                                      headers={'Content-Type': 'application/json'})
            
            preprocess_name = "CLAHE" if prehandle == 2 else "锐化"
            print(f"  {preprocess_name}: {'✅' if result['success'] else '❌'}")
            if not result['success']:
                print(f"     错误: {result['data']}")
            
            time.sleep(1)

    # ==================== 历史记录接口测试 ====================
    
    def test_16_history_list(self):
        """测试获取历史记录列表"""
        print("\n🧪 测试获取历史记录列表")
        
        # 测试基础历史记录查询
        result = self._make_request('GET', '/api/history/list')
        self.assertTrue(result['success'], "获取历史记录失败")
        print(f"✅ 获取历史记录成功: {len(result['data'].get('data', []))} 条记录")
        
        # 测试分页查询
        params = {'page': 1, 'limit': 5}
        result = self._make_request('GET', '/api/history/list', params=params)
        self.assertTrue(result['success'], "分页查询历史记录失败")
        print(f"✅ 分页查询成功")
        
        # 测试按类型查询
        analysis_types = ["变化检测", "目标检测", "地物分类", "场景分类", "图像复原"]
        for analysis_type in analysis_types:
            params = {'type': analysis_type}
            result = self._make_request('GET', '/api/history/list', params=params)
            if result['success']:
                count = len(result['data'].get('data', []))
                print(f"  {analysis_type}: {count} 条记录")
    
    def test_17_show_analysis_results(self):
        """测试获取特定类型分析结果"""
        print("\n🧪 测试获取特定类型分析结果")
        
        analysis_types = ["变化检测", "目标检测", "地物分类", "场景分类", "图像复原"]
        
        for analysis_type in analysis_types:
            result = self._make_request('GET', f'/api/analysis/show/{analysis_type}')
            if result['success']:
                data = result['data'].get('data', [])
                print(f"  {analysis_type}: {len(data)} 条结果")
            else:
                print(f"  {analysis_type}: 查询失败 - {result['data']}")

    # ==================== 错误处理测试 ====================
    
    def test_18_error_handling(self):
        """测试错误处理"""
        print("\n🧪 测试错误处理")
        
        # 测试无效模型路径
        payload = {
            "model_path": "invalid/model/path",
            "list": ["/_uploads/photos/test.jpg"]
        }
        
        result = self._make_request('POST', '/api/analysis/classification',
                                  json=payload,
                                  headers={'Content-Type': 'application/json'})
        
        print(f"  无效模型路径: {'✅' if not result['data'].get('success', True) else '❌'}")
        
        # 测试空图片列表
        models_result = self._make_request('GET', '/api/model/list/classification')
        if models_result['success'] and models_result['data'].get('success') and models_result['data']['data']:
            model_path = models_result['data']['data'][0]['model_path']
            
            payload = {
                "model_path": model_path,
                "list": []
            }
            
            result = self._make_request('POST', '/api/analysis/classification',
                                      json=payload,
                                      headers={'Content-Type': 'application/json'})
            
            print(f"  空图片列表: {'✅' if not result['data'].get('success', True) else '❌'}")
        
        # 测试无效窗口大小（变化检测）
        if models_result['success'] and models_result['data'].get('success'):
            models_cd = self._make_request('GET', '/api/model/list/change_detection')
            if models_cd['success'] and models_cd['data'].get('success') and models_cd['data']['data']:
                model_path = models_cd['data']['data'][0]['model_path']
                
                payload = {
                    "model_path": model_path,
                    "list": [{"first": "test1.jpg", "second": "test2.jpg"}],
                    "window_size": 100,
                    "stride": 200  # stride > window_size
                }
                
                result = self._make_request('POST', '/api/analysis/change_detection',
                                          json=payload,
                                          headers={'Content-Type': 'application/json'})
                
                print(f"  无效窗口参数: {'✅' if not result['data'].get('success', True) else '❌'}")

    # ==================== 性能测试 ====================
    
    def test_19_performance_concurrent_requests(self):
        """测试并发请求性能"""
        print("\n🧪 测试并发请求性能")
        
        # 获取模型列表的并发请求
        import threading
        import time
        
        results = []
        start_time = time.time()
        
        def make_concurrent_request():
            result = self._make_request('GET', '/api/model/list/classification')
            results.append(result['success'])
        
        # 创建5个并发请求
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_concurrent_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        success_count = sum(results)
        
        print(f"  并发请求结果: {success_count}/5 成功")
        print(f"  总耗时: {end_time - start_time:.2f} 秒")
        
        self.assertGreaterEqual(success_count, 3, "并发请求成功率过低")

    def tearDown(self):
        """测试清理"""
        # 这里可以添加清理逻辑，比如删除上传的测试文件
        pass


def run_comprehensive_test():
    """运行全面测试"""
    print("\n" + "="*60)
    print("🚀 cugrs 后端 API 全面测试开始")
    print("="*60)
    
    # 检查服务是否可用
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        print("✅ 后端服务连接正常")
    except requests.exceptions.RequestException:
        print("❌ 无法连接到后端服务，请确保服务已启动 (python app.py)")
        return
    
    # 运行测试套件
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*60)
    print("🎉 测试完成")
    print("="*60)


if __name__ == '__main__':
    run_comprehensive_test()