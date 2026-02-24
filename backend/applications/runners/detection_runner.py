import argparse
import os
import sys
import cv2
import torch
import subprocess

def download_model(config_name, checkpoint_name):
    # Use mim to download model
    try:
        subprocess.check_call(["mim", "download", "mmrotate", "--config", config_name, "--dest", "checkpoints"])
    except subprocess.CalledProcessError as e:
        print(f"Failed to download model: {e}")
        sys.exit(1)

def run_detection(img_path, output_path, config_name, device='cuda:0'):
    from mmrotate.apis import init_model, inference_detector
    from mmrotate.registry import VISUALIZERS
    
    # Determine config and checkpoint paths
    # Assuming downloaded to 'checkpoints'
    config_file = f"checkpoints/{config_name}.py"
    # Find checkpoint file in checkpoints dir that matches generic pattern if possible, 
    # but mim download usually returns the filename. 
    # Let's search for the .pth file corresponding to the config.
    
    if not os.path.exists("checkpoints"):
        os.makedirs("checkpoints")
        
    # Check if config exists, if not download
    if not os.path.exists(config_file):
        print(f"Downloading model {config_name}...")
        download_model(config_name, None)
    
    # Find checkpoint
    checkpoint_file = None
    for f in os.listdir("checkpoints"):
        if f.endswith(".pth") and (config_name in f or "oriented_rcnn" in f): # Simple heuristic
             checkpoint_file = os.path.join("checkpoints", f)
             break
             
    if not checkpoint_file:
        print("Checkpoint not found after download.")
        sys.exit(1)

    print(f"Initializing model with config: {config_file} and checkpoint: {checkpoint_file}")
    model = init_model(config_file, checkpoint_file, device=device)
    
    # Run inference
    print(f"Running inference on {img_path}...")
    result = inference_detector(model, img_path)
    
    # Visualize the results
    visualizer = VISUALIZERS.build(model.cfg.visualizer)
    visualizer.dataset_meta = model.dataset_meta
    
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    visualizer.add_datasample(
        'result',
        img,
        data_sample=result,
        draw_gt=False,
        show=False,
        out_file=output_path,
        pred_score_thr=0.3
    )
    print(f"Detection result saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MMRotate Detection Runner')
    parser.add_argument('--img', required=True, help='Path to input image')
    parser.add_argument('--output', required=True, help='Path to save detection result')
    parser.add_argument('--config', default='oriented_rcnn_r50_fpn_1x_dota_le90', help='Config name for mim download')
    
    args = parser.parse_args()
    
    try:
        run_detection(args.img, args.output, args.config)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
