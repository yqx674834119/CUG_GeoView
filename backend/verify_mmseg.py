import sys
import os

# Add relevant paths to sys.path
sys.path.append("/home/livablecity/GeoView/backend")

from applications.interface.mmseg_inference_caller import call_mmseg_inference

def test_inference():
    model_ref = "backend/model/semantic_segmentation/mmseg_cugrs"
    data_path = "/home/livablecity/GeoView/TestData/Seg"
    out_dir = "/home/livablecity/GeoView/TestData/Seg/output"
    
    # Get all files in the test directory
    try:
        files = [f for f in os.listdir(data_path) if f.lower().endswith(('.png', '.tif', '.tiff', '.jpg', '.jpeg'))]
        print(f"Found {len(files)} images to process: {files}")
    except FileNotFoundError:
        print(f"Error: Test directory not found: {data_path}")
        return

    if not files:
        print("No image files found in test directory.")
        return

    try:
        print("Starting inference...")
        results = call_mmseg_inference(
            model_ref=model_ref,
            data_path=data_path,
            out_dir=out_dir,
            names=files,
            device="cuda:0", # Assuming cuda is available as per previous context
            timeout=300
        )
        print("Inference completed successfully!")
        print("Results:", results)
        
    except Exception as e:
        print(f"Inference failed with error: {e}")

if __name__ == "__main__":
    test_inference()
