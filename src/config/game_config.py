# game_config.py

# 객체 탐지 모델 학습을 위한 클래스 목록
# 이 순서가 YOLO 학습 시 클래스 ID가 됩니다.
CLASS_LIST = [
    "player",
    "player_shot",
    "enemy_a", "enemy_b", "enemy_c", "enemy_d", "enemy_e", "enemy_f", "enemy_g", "enemy_h",
    "enemy_i", "enemy_j", "enemy_k", "enemy_l", "enemy_m", "enemy_n", "enemy_o", "enemy_p",
    "enemy_shot",
    "powerup",
    # 필요한 다른 적 타입이나 보스 타입, 파워업 종류가 있다면 여기에 추가
    # EntityType enum의 이름과 일치하도록 소문자로 작성
]

# 클래스 이름을 클래스 ID로 매핑
CLASS_MAP = {cls_name: i for i, cls_name in enumerate(CLASS_LIST)}

# 게임 내 엔티티 타입(EntityType enum)을 문자열 클래스 이름으로 매핑
# src/components/entity_types.py 의 EntityType을 참고하여 작성해야 합니다.
# 현재 방식은 entity.type.name.lower()를 CLASS_MAP의 키로 사용하는 것입니다.
# 따라서 EntityType enum 멤버 이름의 소문자 버전이 CLASS_LIST에 포함되어야 합니다.
# 예시:
# ENTITY_TYPE_TO_CLASS_NAME = {
#     EntityType.PLAYER: "player",
#     EntityType.ENEMY_A: "enemy_a",
#     # ... 기타 등등
# }
# 이 매핑은 GameStateStage에서 적 객체의 타입을 문자열로 변환할 때 사용됩니다.
# 현재는 GameStateStage에서 enemy.type.name.lower()를 직접 사용하고 있으므로,
# 이 매핑이 CLASS_LIST의 이름과 일치하는지 확인이 중요합니다. 