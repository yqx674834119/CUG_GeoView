import sys
import mmseg
from mmseg.models import backbones
from mmseg.registry import MODELS

print(f"MMSeg version: {mmseg.__version__}")
print(f"MMSeg path: {mmseg.__file__}")

try:
    print("Default Backbones:", dir(backbones))
except Exception as e:
    print(f"Error listing backbones: {e}")

if 'DINOv3SwinEncoder' in dir(backbones):
    print("Found DINOv3SwinEncoder in backbones module.")
else:
    print("DINOv3SwinEncoder NOT found in backbones module.")

# Check registry
print("\nRegistry check:")
try:
    if 'DINOv3SwinEncoder' in MODELS.module_dict:
         print("DINOv3SwinEncoder is registered in MODELS.")
    else:
         print("DINOv3SwinEncoder is NOT registered in MODELS.")
         # print("Available keys:", list(MODELS.module_dict.keys()))
except Exception as e:
    print(f"Error checking registry: {e}")
