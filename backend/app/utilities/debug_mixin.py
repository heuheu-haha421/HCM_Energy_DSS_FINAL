from datetime import datetime

import pytz
import inspect
import traceback

class DebugMixin:
    
    vn_timezone: str = "Asia/Ho_Chi_Minh"
    
    def printDebug(self, msg, with_traceback=False):
        vn_tz = pytz.timezone(self.vn_timezone)
        now   = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # caller_frame = inspect.currentframe().f_back if currentframe() else None

        class_name = self.__class__.__name__
        
        left  = f"{class_name}"
        right = str(msg)

        left_width = 30

        print(
            f"[{now}] "
            f"{left:<{left_width}} | "
            f"{right}"
        )
        
        if with_traceback:
            print("========== TRACEBACK ==========")
            traceback.print_exc()
            print("================================")
        