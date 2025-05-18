import os
import time
import cv2
import numpy as np
from screen_capture import ScreenCapture
from label_generator import LabelGenerator

class DataCollector:
    def __init__(self, window_name, save_dir="data"):
        self.screen_capture = ScreenCapture(window_name)
        self.label_generator = LabelGenerator(os.path.join(save_dir, "labels"))
        self.frame_count = 0
        self.save_dir = save_dir
        os.makedirs(os.path.join(save_dir, "images"), exist_ok=True)
        
    def find_bbox_by_color(self, image, lower_color, upper_color):
        mask = cv2.inRange(image, lower_color, upper_color)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bboxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            bboxes.append((x, y, w, h))
        return bboxes

    def load_manual_bboxes(self, label_path, img_width, img_height):
        bboxes = []
        if not os.path.exists(label_path):
            return bboxes
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cls, xc, yc, w, h = map(float, parts)
                x = int(xc * img_width - w * img_width / 2)
                y = int(yc * img_height - h * img_height / 2)
                w = int(w * img_width)
                h = int(h * img_height)
                bboxes.append((int(cls), x, y, w, h))
        return bboxes

    def visualize_bboxes(self, frame, auto_bboxes, manual_bboxes):
        # 자동 bbox (파란색)
        for x, y, w, h in auto_bboxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        # 직접 라벨링 bbox (빨간색)
        for cls, x, y, w, h in manual_bboxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.imshow('Compare BBoxes', frame)
        cv2.waitKey(0)

    def collect_frame(self):
        """
        현재 프레임을 캡처하고 라벨을 자동으로 추출하여 저장합니다.
        """
        # 화면 캡처
        frame = self.screen_capture.capture_window()
        img_height, img_width = frame.shape[:2]
        # 플레이어(흰색)와 적(파란색) 색상 범위 정의 (BGR)
        lower_white = np.array([200, 200, 200])
        upper_white = np.array([255, 255, 255])
        lower_blue = np.array([180, 100, 100])
        upper_blue = np.array([255, 200, 200])
        # 플레이어 bbox 추출
        player_bboxes = self.find_bbox_by_color(frame, lower_white, upper_white)
        # 적 bbox 추출 (여러 개 가능)
        enemy_bboxes = self.find_bbox_by_color(frame, lower_blue, upper_blue)
        # 이미지 저장
        image_filename = f"frame_{self.frame_count:06d}.png"
        image_path = os.path.join(self.save_dir, "images", image_filename)
        cv2.imwrite(image_path, frame)
        # 라벨 생성 및 저장
        labels = []
        auto_bboxes = []
        # 플레이어: 가장 큰 bbox 1개만 사용
        if player_bboxes:
            px, py, pw, ph = max(player_bboxes, key=lambda b: b[2]*b[3])
            labels.append((0, (px, py), (pw, ph)))
            auto_bboxes.append((px, py, pw, ph))
        # 적: 여러 개 모두 사용
        for ex, ey, ew, eh in enemy_bboxes:
            labels.append((1, (ex, ey), (ew, eh)))
            auto_bboxes.append((ex, ey, ew, eh))
        # YOLO 라벨 생성
        yolo_labels = []
        for cls, pos, bbox in labels:
            norm = self.label_generator.normalize_coordinates(
                pos[0] + bbox[0]/2, pos[1] + bbox[1]/2, bbox[0], bbox[1]
            )
            yolo_labels.append(f"{cls} {norm[0]:.6f} {norm[1]:.6f} {norm[2]:.6f} {norm[3]:.6f}")
        label_filename = f"frame_{self.frame_count:06d}.txt"
        label_path = os.path.join(self.save_dir, "images", label_filename)
        self.label_generator.save_label(yolo_labels, label_filename)
        # 직접 라벨링 파일이 있으면 덮어쓰기
        manual_label_path = os.path.join(r"c:/Users/easy/Desktop/1/images", label_filename)
        if os.path.exists(manual_label_path):
            with open(manual_label_path, 'r') as f:
                manual_lines = f.readlines()
            with open(label_path, 'w') as f:
                f.writelines(manual_lines)
        # 직접 라벨링 bbox 불러오기 (같은 이름의 txt 파일이 있으면)
        manual_bboxes = self.load_manual_bboxes(manual_label_path, img_width, img_height)
        # 시각화 (자동 bbox: 파란색, 직접 라벨링 bbox: 빨간색)
        self.visualize_bboxes(frame.copy(), auto_bboxes, manual_bboxes)
        self.frame_count += 1
        return frame

def main():
    # 윈도우 이름 설정 (실제 게임 윈도우 이름으로 변경 필요)
    window_name = "Your Game Window Name"
    
    # 데이터 수집기 초기화
    collector = DataCollector(window_name)
    
    try:
        while True:
            # 여기에 실제 게임에서 플레이어와 적의 위치/바운딩 박스 정보를 가져오는 코드 추가
            # 예시 데이터
            player_pos = (128, 80)  # 중앙 위치
            player_bbox = (32, 32)  # 예시 크기
            enemy_pos = (64, 40)    # 예시 위치
            enemy_bbox = (32, 32)   # 예시 크기
            
            # 프레임 수집
            frame = collector.collect_frame()
            
            # 화면에 표시 (선택사항)
            cv2.imshow("Captured Frame", frame)
            
            # 'q' 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # 프레임 레이트 제한 (선택사항)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Data collection stopped by user")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 