import argparse
import torch
import numpy as np
from PIL import Image
from transformers import Swin2SRForImageSuperResolution, Swin2SRImageProcessor

def super_resolve(img_path, output_path):
    print(f"Loading image: {img_path}")
    image = Image.open(img_path).convert("RGB")
    
    model_name = "caidas/swin2SR-classical-sr-x2-64"
    processor = Swin2SRImageProcessor.from_pretrained(model_name)
    model = Swin2SRForImageSuperResolution.from_pretrained(model_name)
    
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available; refusing CPU inference")
    device = torch.device('cuda')
    model = model.to(device)

    inputs = processor(image, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    output = outputs.reconstruction.data.squeeze().float().cpu().clamp_(0, 1).numpy()
    output = np.moveaxis(output, 0, -1)
    output = (output * 255.0).round().astype(np.uint8)
    
    output_image = Image.fromarray(output)
    output_image.save(output_path)
    print(f"Super resolved image saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Super Resolution Runner')
    parser.add_argument('--img', required=True, help='Path to input image')
    parser.add_argument('--output', required=True, help='Path to save super resolved image')
    
    args = parser.parse_args()
    
    try:
        super_resolve(args.img, args.output)
    except Exception as e:
        print(f"Error: {e}")
