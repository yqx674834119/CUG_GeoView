#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace Object Detection Inference Script

此脚本需要在 HFPyTorch310 conda 环境中运行。
用于处理 HuggingFace Hub 上的目标检测模型推理。

支持的模型:
    - Transformers 兼容模型 (e.g., DETR, Conditional DETR)
    - Ultralytics YOLO 模型 (e.g., WALDO30)
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime

# Configure logging
def log(msg: str, level: str = "INFO"):
    """统一日志格式"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [HF-OD] {msg}", file=sys.stderr, flush=True)


class ModelHandler:
    def __init__(self, model_id: str, device: str):
        self.model_id = model_id
        self.device = device
        self.type = "transformers"
        self.processor = None
        self.model = None
        self._load()

    def _load(self):
        log(f"Loading model: {self.model_id}")
        self._try_load_transformers()

    def _try_load_transformers(self):
        try:
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
            start_time = time.time()
            self.processor = AutoImageProcessor.from_pretrained(self.model_id)
            self.model = AutoModelForObjectDetection.from_pretrained(self.model_id)
            self.model = self.model.to(self.device).eval()
            self.type = "transformers"
            log(f"Loaded Transformer model in {time.time() - start_time:.2f}s")
        except Exception as e:
            log(f"Transformer load failed ({e}), trying Ultralytics...", level="WARNING")
            self._try_load_ultralytics()

    def _try_load_ultralytics(self):
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download
            
            # 尝试查找 .pt 文件
            weight_file = None
            possible_files = ["best.pt", "model.pt", "weights.pt"]
            
            # 特殊处理 WALDO30
            if "WALDO30" in self.model_id:
                possible_files = ["WALDO30_yolov8m_640x640.pt", "WALDO30_yolov8n_640x640.pt"] + possible_files

            for filename in possible_files:
                try:
                    log(f"Attempting to download {filename} from {self.model_id}...")
                    weight_file = hf_hub_download(repo_id=self.model_id, filename=filename)
                    log(f"Found weight file: {weight_file}")
                    break
                except Exception:
                    continue
            
            if not weight_file:
                raise RuntimeError("Could not find any suitable .pt file in the repository")

            start_time = time.time()
            self.model = YOLO(weight_file)
            self.type = "ultralytics"
            # Ultralytics manages device internally usually, but we can check
            log(f"Loaded Ultralytics model in {time.time() - start_time:.2f}s")
            
        except ImportError:
            log("Ultralytics package not installed", level="ERROR")
            raise
        except Exception as e:
            log(f"Ultralytics load failed: {e}", level="ERROR")
            raise RuntimeError(f"Failed to load model via both Transformers and Ultralytics: {e}")

    def predict(self, image_path: str, threshold: float = 0.5):
        if self.type == "transformers":
            return self._predict_transformers(image_path, threshold)
        elif self.type == "ultralytics":
            return self._predict_ultralytics(image_path, threshold)

    def _predict_transformers(self, image_path, threshold):
        import torch
        from PIL import Image
        
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=[image], return_tensors="pt", padding=True).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=threshold)[0]
        
        processed_results = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            box = [round(i, 2) for i in box.tolist()]
            label_name = self.model.config.id2label[label.item()]
            processed_results.append({
                "box": box,
                "label": label_name,
                "score": round(score.item(), 2)
            })
        return image, processed_results

    def _predict_ultralytics(self, image_path, threshold):
        # Ultralytics load image internally or accept path
        results = self.model.predict(image_path, conf=threshold, device=self.device)
        result = results[0]
        
        processed_results = []
        names = result.names
        
        for box in result.boxes:
            xyxy = box.xyxy[0].tolist() # [x1, y1, x2, y2]
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            label_name = names[cls_id]
            
            processed_results.append({
                "box": [round(i, 2) for i in xyxy],
                "label": label_name,
                "score": round(conf, 2)
            })
            
        # For consistency, reload image to return PIL object
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        return image, processed_results


def draw_results(image, results):
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except IOError:
        font = ImageFont.load_default()

    for item in results:
        box = item["box"]
        display_text = f"{item['label']}: {item['score']}"
        
        draw.rectangle(box, outline="red", width=3)
        text_bbox = draw.textbbox((box[0], box[1]), display_text, font=font)
        draw.rectangle(text_bbox, fill="red")
        draw.text((box[0], box[1]), display_text, fill="white", font=font)
    
    return image


def main():
    parser = argparse.ArgumentParser(description="HuggingFace Object Detection Inference")
    parser.add_argument("--model_id", type=str, required=True)
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--file_names", type=str, required=True)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--threshold", type=float, default=0.7)
    
    args = parser.parse_args()
    
    log("=== HuggingFace Object Detection Script Started ===")
    
    # Check device
    import torch
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    log(f"Device: {device}")
    
    os.makedirs(args.output_dir, exist_ok=True)
    file_names = [f.strip() for f in args.file_names.split(",") if f.strip()]
    
    try:
        handler = ModelHandler(args.model_id, device)
    except Exception as e:
        log(f"Critical error loading model: {e}", level="ERROR")
        log(traceback.format_exc(), level="ERROR")
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)
        
    final_results = []
    
    for name in file_names:
        input_path = os.path.join(args.input_dir, name)
        output_path = os.path.join(args.output_dir, name)
        
        if not os.path.exists(input_path):
            final_results.append({"name": name, "status": "error", "message": "File not found"})
            continue
            
        try:
            log(f"Processing {name}...")
            image, detections = handler.predict(input_path, args.threshold)
            result_img = draw_results(image, detections)
            result_img.save(output_path)
            
            log(f"Detected {len(detections)} objects. Saved to {output_path}")
            final_results.append({"name": name, "status": "success", "output_path": output_path})
        except Exception as e:
            log(f"Error processing {name}: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")
            final_results.append({"name": name, "status": "error", "message": str(e)})
            
    print(json.dumps({"status": "completed", "results": final_results}))


if __name__ == "__main__":
    main()
