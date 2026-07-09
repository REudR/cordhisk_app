import os
import shutil
from config import APP_DATA_DIR

def copy_memory_file(src, mid):
    new_path = os.path.join(APP_DATA_DIR, f"{mid}_{os.path.basename(src)}")
    shutil.copy(src, new_path)
    return new_path
