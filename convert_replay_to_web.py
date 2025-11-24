#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RL 학습 중 생성된 리플레이 JSON을 웹 리플레이 형식으로 변환

사용법:
    python convert_replay_to_web.py <input.json> [output.json]
"""

import json
import sys
import os
from typing import Dict, List, Any

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def convert_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    """단일 프레임을 웹 리플레이 형식으로 변환
    
    Args:
        frame: 원본 프레임 데이터
        
    Returns:
        변환된 프레임 데이터
    """
    # 탄환 통합: player_bullets와 enemy_bullets를 하나로
    bullets = []
    
    # 적 탄환 추가 (웹에서는 주로 enemy_bullets만 표시)
    if 'enemy_bullets' in frame:
        for bullet in frame['enemy_bullets']:
            bullets.append({
                'x': bullet['x'],
                'y': bullet['y'],
                'type': 'enemy'  # 타입 표시 (선택사항)
            })
    
    # 플레이어 탄환도 추가 (필요시)
    if 'player_bullets' in frame:
        for bullet in frame['player_bullets']:
            bullets.append({
                'x': bullet['x'],
                'y': bullet['y'],
                'type': 'player'  # 타입 표시
            })
    
    # 적 데이터 변환 (type 필드 제거 또는 유지)
    enemies = []
    if 'enemies' in frame:
        for enemy in frame['enemies']:
            enemy_data = {
                'x': enemy['x'],
                'y': enemy['y']
            }
            # enemy type 정보 유지 (웹에서 필요하면)
            if 'type' in enemy:
                enemy_data['type'] = enemy['type']
            enemies.append(enemy_data)
    
    # 웹 리플레이 형식으로 변환
    converted = {
        'step': frame['step'],
        'player': frame['player'],
        'enemies': enemies,
        'bullets': bullets,
        'score': frame.get('score', 0)
    }
    
    # 액션이 있는 프레임에만 액션 추가 (프레임 단위 리플레이 대응)
    if 'action' in frame:
        converted['action'] = frame['action']
    
    return converted


def convert_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """메타데이터를 웹 리플레이 형식으로 변환
    
    Args:
        metadata: 원본 메타데이터
        
    Returns:
        변환된 메타데이터
    """
    return {
        'model_name': f"ep{metadata.get('episode_number', 0)}",
        'skill_level': metadata.get('skill_level', 0.5),
        'total_steps': metadata.get('episode_steps', 0),
        'episode_number': metadata.get('episode_number', 0),
        'timestamp': metadata.get('timestamp', '').replace(':', '').replace('-', '').replace('T', '_').split('.')[0],
        # 추가 정보 (선택사항)
        'episode_score': metadata.get('episode_score', 0),
        'episode_kills': metadata.get('episode_kills', 0),
        'target_category': metadata.get('target_category', 'unknown')
    }


def convert_replay(input_path: str, output_path: str = None) -> str:
    """리플레이 파일을 변환
    
    Args:
        input_path: 입력 JSON 파일 경로
        output_path: 출력 JSON 파일 경로 (None이면 자동 생성)
        
    Returns:
        출력 파일 경로
    """
    print(f"📖 리플레이 파일 읽는 중: {input_path}")
    
    # 입력 파일 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ {len(data['frames'])} 프레임 로드됨")
    
    # 변환
    print("🔄 프레임 변환 중...")
    converted_frames = []
    for i, frame in enumerate(data['frames']):
        converted_frame = convert_frame(frame)
        converted_frames.append(converted_frame)
        
        # 진행률 표시
        if (i + 1) % 100 == 0:
            print(f"   {i + 1}/{len(data['frames'])} 프레임 변환됨...")
    
    print(f"✅ 모든 프레임 변환 완료")
    
    # 메타데이터 변환
    converted_metadata = convert_metadata(data['metadata'])
    
    # 출력 데이터 구성
    output_data = {
        'metadata': converted_metadata,
        'frames': converted_frames
    }
    
    # 출력 경로 결정
    if output_path is None:
        # 입력 파일명에 _web 추가
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_web{ext}"
    
    # 출력 파일 저장
    print(f"💾 웹 리플레이 파일 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 변환 완료!")
    print(f"\n📊 변환 정보:")
    print(f"   - 총 프레임: {len(converted_frames)}")
    print(f"   - 에피소드: {converted_metadata['episode_number']}")
    print(f"   - Skill Level: {converted_metadata['skill_level']}")
    print(f"   - 최종 점수: {converted_metadata['episode_score']}")
    print(f"   - 총 킬: {converted_metadata['episode_kills']}")
    
    return output_path


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python convert_replay_to_web.py <input.json> [output.json]")
        print("\n예시:")
        print("  python convert_replay_to_web.py src/src/replays/replay_ep3_steps_400.json")
        print("  python convert_replay_to_web.py input.json output.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_path):
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    try:
        output_file = convert_replay(input_path, output_path)
        print(f"\n🎉 성공! 변환된 파일: {output_file}")
        print(f"\n웹에서 재생하려면:")
        print(f"  1. 이 파일을 src/web/agentic-game/replays/ 디렉토리로 복사")
        print(f"  2. 웹 리플레이 시스템에서 불러오기")
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

