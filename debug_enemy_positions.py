"""
적 위치 데이터 추출 검증 스크립트

게임 인스턴스에서 적들의 위치 데이터가 정확하게 추출되는지 확인합니다.
"""
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rl.environment import GameEnvironment
from src.components.entity_types import EntityType


def validate_enemy_data(game_instance, skill_level: float = 0.6):
    """적 데이터 추출 검증
    
    Args:
        game_instance: 게임 인스턴스
        skill_level: 실력값
    """
    env = GameEnvironment()
    
    print("=" * 80)
    print("🔍 적 위치 데이터 추출 검증 시작")
    print("=" * 80)
    
    # 1. 게임 인스턴스 구조 확인
    print("\n📦 게임 인스턴스 구조:")
    if hasattr(game_instance, "game"):
        print("  ✅ game_instance.game 존재")
        game = game_instance.game
        
        if hasattr(game, "state"):
            print("  ✅ game.state 존재")
            game_state = game.state
            
            # 2. game_state의 모든 속성 출력
            print("\n📋 game_state 속성 목록:")
            enemy_attrs = [attr for attr in dir(game_state) if attr.startswith("enemy")]
            print(f"  Enemy 관련 속성 ({len(enemy_attrs)}개): {enemy_attrs}")
            
            # 3. 플레이어 위치 확인
            print("\n👤 플레이어 정보:")
            if hasattr(game_state, "player"):
                player = game_state.player
                player_x = getattr(player, "x", 0)
                player_y = getattr(player, "y", 0)
                print(f"  위치: ({player_x:.1f}, {player_y:.1f})")
                print(f"  HP: {getattr(player, 'current_hp', 'N/A')}")
            else:
                print("  ❌ player 속성 없음")
                player_x, player_y = 0, 0
            
            # 4. 적 정보 상세 분석
            print("\n👾 적 데이터 상세:")
            total_enemies = 0
            
            for attr in enemy_attrs:
                enemy_group = getattr(game_state, attr, None)
                if enemy_group and hasattr(enemy_group, "__iter__"):
                    try:
                        enemy_list = list(enemy_group)
                        count = len(enemy_list)
                        total_enemies += count
                        print(f"\n  📍 {attr}: {count}개")
                        
                        # 처음 3개만 상세 출력
                        for i, enemy in enumerate(enemy_list[:3]):
                            if hasattr(enemy, "x") and hasattr(enemy, "y"):
                                enemy_x = getattr(enemy, "x", 0)
                                enemy_y = getattr(enemy, "y", 0)
                                distance = ((enemy_x - player_x)**2 + (enemy_y - player_y)**2)**0.5
                                
                                print(f"    Enemy {i+1}:")
                                print(f"      위치: ({enemy_x:.1f}, {enemy_y:.1f})")
                                print(f"      플레이어로부터 거리: {distance:.1f}px")
                                
                                # 추가 속성 확인
                                extra_attrs = []
                                for check_attr in ["hp", "type", "speed", "alive"]:
                                    if hasattr(enemy, check_attr):
                                        value = getattr(enemy, check_attr)
                                        extra_attrs.append(f"{check_attr}={value}")
                                if extra_attrs:
                                    print(f"      속성: {', '.join(extra_attrs)}")
                            else:
                                print(f"    Enemy {i+1}: ❌ x, y 속성 없음")
                        
                        if count > 3:
                            print(f"    ... 외 {count - 3}개 더")
                    except Exception as e:
                        print(f"  ❌ {attr} 처리 실패: {e}")
            
            print(f"\n  📊 총 적 수: {total_enemies}개")
            
            # 5. 탄환 정보 확인
            print("\n💥 탄환 데이터:")
            if hasattr(game_state, "enemy_shots"):
                enemy_shots = getattr(game_state, "enemy_shots", [])
                if enemy_shots and hasattr(enemy_shots, "__iter__"):
                    try:
                        shot_list = list(enemy_shots)
                        print(f"  총 {len(shot_list)}개의 탄환")
                        
                        nearby_count = 0
                        for i, shot in enumerate(shot_list[:5]):
                            if hasattr(shot, "x") and hasattr(shot, "y"):
                                shot_x = getattr(shot, "x", 0)
                                shot_y = getattr(shot, "y", 0)
                                distance = ((shot_x - player_x)**2 + (shot_y - player_y)**2)**0.5
                                
                                if distance < 40:
                                    nearby_count += 1
                                    
                                print(f"    탄환 {i+1}: ({shot_x:.1f}, {shot_y:.1f}) - 거리: {distance:.1f}px")
                        
                        if len(shot_list) > 5:
                            print(f"    ... 외 {len(shot_list) - 5}개 더")
                        
                        print(f"  ⚠️  위험한 탄환 (40px 이내): {nearby_count}개")
                    except Exception as e:
                        print(f"  ❌ 탄환 처리 실패: {e}")
            else:
                print("  ❌ enemy_shots 속성 없음")
        else:
            print("  ❌ game.state 없음")
    else:
        print("  ❌ game_instance.game 없음")
        return False
    
    # 6. extract_game_log_data 실행 및 검증
    print("\n" + "=" * 80)
    print("🔄 extract_game_log_data() 실행 결과")
    print("=" * 80)
    
    game_log_data = env.extract_game_log_data(game_instance, skill_level)
    
    print(f"\n📊 추출된 데이터:")
    print(f"  총 엔티티 수: {len(game_log_data.entities)}개")
    
    # 엔티티 타입별 분류
    entity_counts = {
        "PLAYER": 0,
        "ENEMY": 0,
        "ENEMY_SHOT": 0,
    }
    
    for entity in game_log_data.entities:
        if entity.entity_type == EntityType.PLAYER:
            entity_counts["PLAYER"] += 1
        elif entity.entity_type == EntityType.ENEMY:
            entity_counts["ENEMY"] += 1
        elif entity.entity_type == EntityType.ENEMY_SHOT:
            entity_counts["ENEMY_SHOT"] += 1
    
    print(f"  - 플레이어: {entity_counts['PLAYER']}개")
    print(f"  - 적: {entity_counts['ENEMY']}개")
    print(f"  - 적 탄환: {entity_counts['ENEMY_SHOT']}개")
    
    # 처음 10개 엔티티 상세 출력 (거리순 정렬 확인)
    print(f"\n  📍 가까운 엔티티 Top 10 (거리순):")
    for i, entity in enumerate(game_log_data.entities[:10]):
        type_name = {
            EntityType.PLAYER: "플레이어",
            EntityType.ENEMY: "적",
            EntityType.ENEMY_SHOT: "탄환",
        }.get(entity.entity_type, "Unknown")
        
        print(f"    {i+1}. {type_name}: ({entity.x:.1f}, {entity.y:.1f})")
    
    # 7. to_state_vector() 실행 및 검증
    print("\n" + "=" * 80)
    print("🔄 to_state_vector() 실행 결과")
    print("=" * 80)
    
    state_vector = game_log_data.to_state_vector(max_entities=50)
    
    print(f"\n📊 상태 벡터 정보:")
    print(f"  벡터 크기: {len(state_vector)}차원")
    print(f"  값 범위: [{state_vector.min():.4f}, {state_vector.max():.4f}]")
    print(f"  0이 아닌 값: {(state_vector != 0).sum()}개")
    
    # 엔티티 데이터 부분만 추출 (첫 150차원)
    entity_data = state_vector[:150]
    non_zero_entities = (entity_data != 0).sum() // 3  # x, y, type 3개씩
    print(f"  인코딩된 엔티티 수: {non_zero_entities}개")
    
    # 첫 5개 엔티티 상세 출력
    print(f"\n  📍 인코딩된 엔티티 샘플:")
    for i in range(min(5, non_zero_entities)):
        base_idx = i * 3
        x_norm = entity_data[base_idx]
        y_norm = entity_data[base_idx + 1]
        type_norm = entity_data[base_idx + 2]
        
        # 역정규화
        x_actual = x_norm * 256.0
        y_actual = y_norm * 256.0
        type_actual = type_norm * 2.0
        
        type_name = {
            0.0: "플레이어",
            0.5: "적",
            1.0: "탄환",
        }.get(type_norm, f"Unknown({type_norm:.2f})")
        
        print(f"    {i+1}. {type_name}: ({x_actual:.1f}, {y_actual:.1f})")
        print(f"       정규화: x={x_norm:.4f}, y={y_norm:.4f}, type={type_norm:.4f}")
    
    # 8. 검증 결과 요약
    print("\n" + "=" * 80)
    print("✅ 검증 결과")
    print("=" * 80)
    
    issues = []
    
    if entity_counts["PLAYER"] == 0:
        issues.append("❌ 플레이어 데이터 없음")
    elif entity_counts["PLAYER"] > 1:
        issues.append(f"⚠️  플레이어가 {entity_counts['PLAYER']}개 (1개여야 함)")
    else:
        print("✅ 플레이어 데이터 정상")
    
    if entity_counts["ENEMY"] == 0:
        issues.append("⚠️  적 데이터 없음 (게임 초기 상태일 수 있음)")
    else:
        print(f"✅ 적 데이터 정상: {entity_counts['ENEMY']}개")
    
    if entity_counts["ENEMY_SHOT"] == 0:
        print("⚠️  탄환 데이터 없음 (아직 발사 전일 수 있음)")
    else:
        print(f"✅ 탄환 데이터 정상: {entity_counts['ENEMY_SHOT']}개")
    
    if len(game_log_data.entities) != entity_counts["PLAYER"] + entity_counts["ENEMY"] + entity_counts["ENEMY_SHOT"]:
        issues.append("❌ 엔티티 수 불일치")
    else:
        print("✅ 엔티티 수 일치")
    
    if state_vector.min() < -0.1 or state_vector.max() > 2.1:
        issues.append(f"⚠️  정규화 범위 이상: [{state_vector.min():.4f}, {state_vector.max():.4f}]")
    else:
        print("✅ 정규화 범위 정상")
    
    if issues:
        print("\n⚠️  발견된 문제:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n🎉 모든 검증 통과!")
    
    print("\n" + "=" * 80)
    
    return len(issues) == 0


if __name__ == "__main__":
    print("⚠️  이 스크립트는 실제 게임 인스턴스가 필요합니다.")
    print("train_ppo_real_game.py나 다른 학습 스크립트에서 호출해주세요.")
    print("\n사용 예시:")
    print("```python")
    print("from debug_enemy_positions import validate_enemy_data")
    print("validate_enemy_data(game_instance, skill_level=0.6)")
    print("```")

