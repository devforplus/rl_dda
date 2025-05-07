import cv2
import numpy as np
import os

class GameDetector:
    def __init__(self, model_path='models/yolov3.weights', config_path='models/yolov3.cfg', classes_path='models/coco.names'):
        self.model_loaded = False
        try:
            if os.path.exists(model_path) and os.path.exists(config_path) and os.path.exists(classes_path):
                self.net = cv2.dnn.readNet(model_path, config_path)
                with open(classes_path, 'r') as f:
                    self.classes = [line.strip() for line in f.readlines()]
                self.layer_names = self.net.getLayerNames()
                self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
                self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
                self.model_loaded = True
            else:
                print("Warning: YOLO model files not found. Using dummy detection mode.")
                self.classes = ['player', 'enemy']
                self.colors = np.random.uniform(0, 255, size=(2, 3))
        except Exception as e:
            print(f"Warning: Failed to load YOLO model. Using dummy detection mode. Error: {e}")
            self.classes = ['player', 'enemy']
            self.colors = np.random.uniform(0, 255, size=(2, 3))

    def get_sprite_positions(self, game_state):
        """Get sprite positions from game state for dummy detection mode."""
        detections = []
        # Add player detection if exists
        if hasattr(game_state, 'player') and game_state.player:
            player = game_state.player
            if hasattr(player, 'x') and hasattr(player, 'y') and hasattr(player, 'w') and hasattr(player, 'h'):
                detections.append((0, int(player.x), int(player.y), int(player.x + player.w), int(player.y + player.h)))
        # Add enemy detections if exists
        if hasattr(game_state, 'enemies'):
            for enemy in game_state.enemies:
                if hasattr(enemy, 'x') and hasattr(enemy, 'y') and hasattr(enemy, 'w') and hasattr(enemy, 'h') and hasattr(enemy, 'type'):
                    # Use enemy type id for class_id
                    class_id = int(getattr(enemy.type, 'value', 1))
                    detections.append((class_id, int(enemy.x), int(enemy.y), int(enemy.x + enemy.w), int(enemy.y + enemy.h)))
        return detections

    def detect_objects(self, frame, game_state=None):
        if not self.model_loaded:
            # Dummy detection mode - use sprite positions
            if game_state:
                detections = self.get_sprite_positions(game_state)
                return detections, frame
            return [], frame

        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        class_ids = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        detections = []
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                detections.append((class_ids[i], int(x), int(y), int(x + w), int(y + h)))
        return detections, frame

    def draw_detections(self, frame, detections):
        for det in detections:
            class_id, x_min, y_min, x_max, y_max = det
            # class_id가 self.classes 범위 내에 있으면 사용, 아니면 "enemy_{class_id}" 또는 "player"
            if 0 <= class_id < len(self.classes):
                label = str(self.classes[class_id])
                color = tuple(map(int, self.colors[class_id]))
            else:
                label = f"enemy_{class_id}" if class_id != 0 else "player"
                color = (0, 0, 255) if class_id != 0 else (0, 255, 0)
            cv2.rectangle(frame, (int(x_min), int(y_min)), (int(x_max), int(y_max)), color, 2)
            cv2.putText(frame, label, (int(x_min), int(y_min - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame 