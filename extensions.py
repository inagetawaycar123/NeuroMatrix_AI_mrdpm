# extensions.py 【Flask项目首选】
import numpy as np
from json import JSONEncoder

# 定义numpy编码器
class NumpyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        elif isinstance(obj, np.floating): return float(obj)
        elif isinstance(obj, np.float32): return float(obj)
        elif isinstance(obj, np.float64): return float(obj)
        elif isinstance(obj, np.bool_): return bool(obj)
        elif isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)