import os
from applications.interface import hf_inference_caller

def execute(input_path, out_dir, rect):
    """
    Execute Tracking
    input_path: video file or folder
    out_dir: output directory
    rect: [x, y, w, h]
    """
    # Output path
    import time
    timestamp = int(time.time())
    output_filename = f"track_{timestamp}.mp4"
    output_path = os.path.join(out_dir, output_filename)
    
    return hf_inference_caller.call_hf_tracking(
        input_path=input_path,
        output_path=output_path,
        rect=rect
    )
