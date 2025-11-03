"""
빠른 적 데이터 검증 (Pyxel 창 없이)
"""
import sys
import os

# sys.path 설정
current_dir = os.path.dirname(__file__)
project_root = os.path.join(current_dir, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rl.environment import GameEnvironment
from components.entity_types import EntityType

# 간단한 테스트 데이터
class MockEntity:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class MockPlayer:
    def __init__(self):
        self.x = 100
        self.y = 100
        self.current_hp = 3
        self.hp = 3

class MockGameState:
    def __init__(self):
        self.player = MockPlayer()
        # 실제 적 객체
        self.enemy_a = [
            MockEntity(120, 80),
            MockEntity(140, 90),
        ]
        # 탄환 (이전에는 적으로 잘못 분류됨)
        self.enemy_shots = [
            MockEntity(110, 105),
            MockEntity(115, 110),
            MockEntity(125, 95),
        ]

class MockGameVars:
    def __init__(self):
        self.kills = 5
        self.score = 1000
        self.lives = 3

class MockGame:
    def __init__(self):
        self.state = MockGameState()
        self.game_vars = MockGameVars()

class MockGameInstance:
    def __init__(self):
        self.game = MockGame()

print("=" * 80)
print("🔍 적 데이터 추출 로직 검증")
print("=" * 80)

# 환경 생성
env = GameEnvironment()

# 테스트 데이터로 추출
game_instance = MockGameInstance()
game_log_data = env.extract_game_log_data(game_instance, skill_level=0.6)

print(f"\n📊 추출된 엔티티 ({len(game_log_data.entities)}개):")

# 엔티티 타입별 카운트
counts = {"PLAYER": 0, "ENEMY": 0, "ENEMY_SHOT": 0}
for entity in game_log_data.entities:
    if entity.entity_type == EntityType.PLAYER:
        counts["PLAYER"] += 1
        print(f"  [플레이어] ({entity.x:.1f}, {entity.y:.1f})")
    elif entity.entity_type == EntityType.ENEMY:
        counts["ENEMY"] += 1
        print(f"  [적] ({entity.x:.1f}, {entity.y:.1f})")
    elif entity.entity_type == EntityType.ENEMY_SHOT:
        counts["ENEMY_SHOT"] += 1
        print(f"  [탄환] ({entity.x:.1f}, {entity.y:.1f})")

print(f"\n📈 타입별 집계:")
print(f"  플레이어: {counts['PLAYER']}개 (기대: 1개)")
print(f"  적: {counts['ENEMY']}개 (기대: 2개)")
print(f"  탄환: {counts['ENEMY_SHOT']}개 (기대: 3개)")

# 검증
print(f"\n✅ 검증 결과:")
all_good = True

if counts["PLAYER"] != 1:
    print(f"  ❌ 플레이어 수 불일치: {counts['PLAYER']} != 1")
    all_good = False
else:
    print(f"  ✅ 플레이어 정상")

if counts["ENEMY"] != 2:
    print(f"  ❌ 적 수 불일치: {counts['ENEMY']} != 2")
    all_good = False
else:
    print(f"  ✅ 적 정상")

if counts["ENEMY_SHOT"] != 3:
    print(f"  ❌ 탄환 수 불일치: {counts['ENEMY_SHOT']} != 3")
    all_good = False
else:
    print(f"  ✅ 탄환 정상")

if all_good:
    print(f"\n🎉 모든 검증 통과! 적 데이터가 정확하게 추출되고 있습니다.")
    sys.exit(0)
else:
    print(f"\n❌ 검증 실패! 위 오류를 확인해주세요.")
    sys.exit(1)

