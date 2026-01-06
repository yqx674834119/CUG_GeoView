try:
    from mmseg.models.utils import PatchEmbed, PatchMerging
    print("Found in mmseg.models.utils")
except ImportError:
    print("Not in mmseg.models.utils")

try:
    from mmcv.cnn.bricks.transformer import PatchEmbed, PatchMerging
    print("Found in mmcv.cnn.bricks.transformer")
except ImportError:
    print("Not in mmcv.cnn.bricks.transformer")
