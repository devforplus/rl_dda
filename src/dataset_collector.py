import os
import pyautogui
import cv2
import numpy as np
from datetime import datetime

class DatasetCollector:
    def __init__(self, image_dir='datasets/images', label_dir='datasets/labels', app_width=256, app_height=192):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.app_width = app_width
        self.app_height = app_height
        self.is_collecting = False
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.label_dir, exist_ok=True)

    def start_collection(self):
        self.is_collecting = True

    def stop_collection(self):
        self.is_collecting = False

    def toggle_collection(self):
        self.is_collecting = not self.is_collecting

    def capture_screen(self):
        # Capture the region of the game window (top-left at (0,0), size app_width x app_height)
        img = pyautogui.screenshot(region=(0, 0, self.app_width, self.app_height))
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img

    def save_image(self, img, timestamp):
        img_name = f"frame_{timestamp}.png"
        img_path = os.path.join(self.image_dir, img_name)
        cv2.imwrite(img_path, img)
        return img_name

    def save_labels(self, detections, timestamp):
        # detections: list of (class_id, x_min, y_min, x_max, y_max)
        label_name = f"frame_{timestamp}.txt"
        label_path = os.path.join(self.label_dir, label_name)
        with open(label_path, 'w') as f:
            for det in detections:
                class_id, x_min, y_min, x_max, y_max = det
                yolo_line = self.to_yolo_format(class_id, x_min, y_min, x_max, y_max)
                f.write(yolo_line + '\n')
        return label_name

    def to_yolo_format(self, class_id, x_min, y_min, x_max, y_max):
        # Convert to YOLO format: class cx cy w h (all normalized)
        cx = (x_min + x_max) / 2.0 / self.app_width
        cy = (y_min + y_max) / 2.0 / self.app_height
        w = (x_max - x_min) / self.app_width
        h = (y_max - y_min) / self.app_height
        return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

    def update(self, detections=None):
        if not self.is_collecting or detections is None:
            return
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        img = self.capture_screen()
        self.save_image(img, timestamp)
        self.save_labels(detections, timestamp) 