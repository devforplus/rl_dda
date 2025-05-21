# game_config.py

# 객체 탐지 모델 학습을 위한 클래스 목록
# 이 순서가 YOLO 학습 시 클래스 ID가 됩니다.
CLASS_LIST = [
    "player",
    "enemy_a", "enemy_b", "enemy_c", "enemy_d", "enemy_e", "enemy_f", "enemy_g", "enemy_h",
    "enemy_i", "enemy_j", "enemy_k", "enemy_l", "enemy_m", "enemy_n", "enemy_o", "enemy_p",
    # 필요한 다른 적 타입이나 보스 타입이 있다면 여기에 추가
    # 예: "boss_type_1", "powerup_shield", "powerup_weapon"
    # 현재는 플레이어와 기본 적 타입들만 포함
]

# 클래스 이름을 클래스 ID로 매핑
CLASS_MAP = {cls_name: i for i, cls_name in enumerate(CLASS_LIST)}

# 게임 내 엔티티 타입(EntityType enum)을 문자열 클래스 이름으로 매핑
# src/components/entity_types.py 의 EntityType을 참고하여 작성해야 합니다.
# 이 부분은 EntityType enum 정의를 보고 정확하게 채워야 합니다.
# 예시:
# ENTITY_TYPE_TO_CLASS_NAME = {
#     EntityType.PLAYER: "player",
#     EntityType.ENEMY_A: "enemy_a",
#     EntityType.ENEMY_B: "enemy_b",
#     # ... 기타 등등
# }
# 이 매핑은 GameStateStage에서 적 객체의 타입을 문자열로 변환할 때 사용됩니다.
# 현재는 GameStateStage에서 enemy.type.name.lower()를 직접 사용하고 있으므로,
# 이 매핑이 CLASS_LIST의 이름과 일치하는지 확인이 중요합니다. 