import os
from applications.interface import hf_inference_caller

def execute(data_path, out_dir, names):
    """
    Execute Registration
    names: list of dicts [{'first': 'a.jpg', 'second': 'b.jpg'}, ...]
    """
    # Simply route to HF caller
    return hf_inference_caller.call_hf_registration(
        data_path=data_path,
        out_dir=out_dir,
        pairs=names
    )
