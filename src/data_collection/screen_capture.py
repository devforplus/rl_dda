import win32gui
import win32ui
import win32con
import numpy as np
import cv2
from PIL import Image

class ScreenCapture:
    def __init__(self, window_name, width=256, height=160):
        self.window_name = window_name
        self.width = width
        self.height = height
        
    def get_window_handle(self):
        """윈도우 핸들을 가져옵니다."""
        return win32gui.FindWindow(None, self.window_name)
    
    def capture_window(self):
        """지정된 윈도우의 클라이언트 영역(게임 화면)만 정확히 캡처합니다."""
        hwnd = self.get_window_handle()
        if not hwnd:
            raise ValueError(f"Window '{self.window_name}' not found")
        
        # 클라이언트 영역 크기 구하기
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bottom - top

        # 클라이언트 DC 가져오기
        clientDC = win32gui.GetDC(hwnd)
        srcDC = win32ui.CreateDCFromHandle(clientDC)
        memDC = srcDC.CreateCompatibleDC()

        # 비트맵 생성
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcDC, w, h)
        memDC.SelectObject(bmp)

        # 클라이언트 영역만 복사 (0,0) 기준
        memDC.BitBlt((0, 0), (w, h), srcDC, (0, 0), win32con.SRCCOPY)

        # 비트맵을 numpy 배열로 변환
        signedIntsArray = bmp.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (h, w, 4)

        # 리소스 해제
        srcDC.DeleteDC()
        memDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, clientDC)
        win32gui.DeleteObject(bmp.GetHandle())

        # BGR로 변환
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img 