import unittest
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from applications import create_app
from applications.extensions import db

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['PROPAGATE_EXCEPTIONS'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Create a dummy image for testing
        import cv2
        import numpy as np
        from applications.common.path_global import up_dir
        
        # Ensure upload dir exists
        if not os.path.exists(up_dir):
            os.makedirs(up_dir, exist_ok=True)
            
        self.test_img_path = os.path.join(up_dir, "test.jpg")
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(self.test_img_path, dummy_img)
        
    def tearDown(self):
        self.ctx.pop()
        # Clean up dummy image
        if hasattr(self, 'test_img_path') and os.path.exists(self.test_img_path):
            os.remove(self.test_img_path)

    def test_registration_api_structure(self):
        """Test Registration API parameters validation"""
        # Missing 'list'
        response = self.client.post('/api/analysis/registration', json={})
        data = json.loads(response.data)
        self.assertEqual(data['code'], 1) 
        
        # Valid structure but mock execution
        # We can't easily mock the internal call without patching, but we can check if it tries to run.
        # If we send empty list, it fails.
        response = self.client.post('/api/analysis/registration', json={"list": []})
        data = json.loads(response.data)
        self.assertIn("上传图片", data['msg']) # "请上传图片"

    def test_tracking_api_structure(self):
        """Test Tracking API parameters validation"""
        response = self.client.post('/api/analysis/tracking', json={})
        data = json.loads(response.data)
        self.assertIn("请提供", data['msg'])

    def test_tracking_api_botsort_without_rect(self):
        """BoT-SORT should not require a manual init bbox."""
        payload = {
            "model_path": "backend/model/tracking/botsort",
            "list": [
                {"src": "/_uploads/photos/test_1.jpg", "filename": "test_1.jpg"},
                {"src": "/_uploads/photos/test_2.jpg", "filename": "test_2.jpg"},
            ],
        }
        from unittest.mock import patch

        mocked = {
            "status": "success",
            "runtime_variant": "engineering",
            "method_used": "ultralytics_botsort",
            "preview_path": "/_uploads/photos/res/preview.png",
            "output_video_path": "/_uploads/photos/res/result.mp4",
            "trajectory_path": "/_uploads/photos/res/trajectory.json",
            "summary": {"total_frames": 2, "tracked_frames": 1, "lost_frames": 1},
            "first_frame_input": "/_uploads/photos/test_1.jpg",
        }
        with patch('applications.interface.analysis.tracking', return_value=mocked):
            response = self.client.post('/api/analysis/tracking', json=payload)
            data = json.loads(response.data)
            self.assertEqual(data['code'], 0)
            self.assertEqual(data['data']['method_used'], 'ultralytics_botsort')
            self.assertEqual(data['data']['runtime_variant'], 'engineering')

    def test_tracking_api_botsort_official_without_rect(self):
        """Official BoT-SORT should also skip manual init bbox."""
        payload = {
            "model_path": "backend/model/tracking/botsort_official",
            "list": [
                {"src": "/_uploads/photos/test_1.jpg", "filename": "test_1.jpg"},
                {"src": "/_uploads/photos/test_2.jpg", "filename": "test_2.jpg"},
            ],
        }
        from unittest.mock import patch

        mocked = {
            "status": "success",
            "runtime_variant": "official",
            "method_used": "botsort_official_reid",
            "preview_path": "/_uploads/photos/res/preview.png",
            "output_video_path": "/_uploads/photos/res/result.mp4",
            "trajectory_path": "/_uploads/photos/res/trajectory.json",
            "summary": {"total_frames": 2, "tracked_frames": 1, "lost_frames": 1},
            "first_frame_input": "/_uploads/photos/test_1.jpg",
        }
        with patch('applications.interface.analysis.tracking', return_value=mocked):
            response = self.client.post('/api/analysis/tracking', json=payload)
            data = json.loads(response.data)
            self.assertEqual(data['code'], 0)
            self.assertEqual(data['data']['method_used'], 'botsort_official_reid')
            self.assertEqual(data['data']['runtime_variant'], 'official')

    def test_object_detection_mmrotate_routing(self):
        """Test Object Detection API routing for MMRotate"""
        # We just want to ensure the endpoint accepts the request.
        # Actual execution will fail because models/files might not exist, 
        # but we can check the error message to see if it reached the routing logic.
        
        payload = {
            "model_path": "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90",
            "list": ["test.jpg"],
            "prehandle": 0,
            "denoise": 0
        }
        
        # We expect a failure because test.jpg doesn't exist, OR 
        # because the model file download fails/execution fails.
        # But if it returns "模型类型不正确" (Model type incorrect), then it didn't route to MMRotate block.
        # If it returns "推理失败" (Inference failed), then it TRIED to run MMRotate.
        
        from unittest.mock import patch, MagicMock
        
        # Mock subprocess.run to return a success JSON
        mock_run_return = MagicMock()
        mock_run_return.returncode = 0
        mock_run_return.stdout = json.dumps({
            "status": "completed", 
            "results": [{"name": "det_test.jpg", "status": "success", "output_path": "/tmp/det_test.jpg"}]
        })
        
        # Patch md5_name in resize.py since it imports it directly
        with patch('applications.image_processing.resize.md5_name', side_effect=lambda x: x):
            with patch('subprocess.run', return_value=mock_run_return) as mock_run:
                response = self.client.post('/api/analysis/object_detection', json=payload)
                print(f"Response Status: {response.status_code}")
                try:
                    print(f"Response Data: {response.data.decode('utf-8')}")
                    data = json.loads(response.data)
                    print(f"MMRotate Response: {data}")
                    self.assertEqual(data['code'], 0) # Should be success (0) because we mocked success
                except Exception as e:
                    print(f"Failed to parse response: {e}")
                    self.fail(f"API call failed with response: {response.data}")
        # If it says "Inference failed" or similar, it means it tried to execute.
        # If it says "Parameter exception", check inputs.
        
if __name__ == '__main__':
    unittest.main()
