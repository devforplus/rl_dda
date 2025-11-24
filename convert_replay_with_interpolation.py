#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리플레이 파일 보간 변환 - 누락된 프레임을 채워서 실제 스텝 수와 일치시킴

사용법:
    python convert_replay_with_interpolation.py <input.json> [output.json]
"""

import json
import sys
import os
from typing import Dict, List, Any
import copy

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def interpolate_position(start_pos: float, end_pos: float, ratio: float) -> float:
    """두 위치 사이를 선형 보간
    
    Args:
        start_pos: 시작 위치
        end_pos: 끝 위치
        ratio: 보간 비율 (0.0 ~ 1.0)
        
    Returns:
        보간된 위치
    """
    return start_pos + (end_pos - start_pos) * ratio


def interpolate_frame(frame1: Dict[str, Any], frame2: Dict[str, Any], ratio: float) -> Dict[str, Any]:
    """두 프레임 사이를 보간
    
    Args:
        frame1: 시작 프레임
        frame2: 끝 프레임
        ratio: 보간 비율 (0.0 ~ 1.0)
        
    Returns:
        보간된 프레임
    """
    interpolated = copy.deepcopy(frame1)
    
    # 플레이어 위치 보간
    if 'player' in frame1 and 'player' in frame2:
        if frame1['player']['x'] is not None and frame2['player']['x'] is not None:
            interpolated['player']['x'] = round(interpolate_position(
                frame1['player']['x'], frame2['player']['x'], ratio
            ))
        if frame1['player']['y'] is not None and frame2['player']['y'] is not None:
            interpolated['player']['y'] = round(interpolate_position(
                frame1['player']['y'], frame2['player']['y'], ratio
            ))
        
        # HP와 lives는 변경 시점에만 즉시 반영 (보간 안 함)
        if ratio < 0.5:
            interpolated['player']['hp'] = frame1['player']['hp']
            interpolated['player']['lives'] = frame1['player']['lives']
        else:
            interpolated['player']['hp'] = frame2['player']['hp']
            interpolated['player']['lives'] = frame2['player']['lives']
    
    # 적 보간 - 간단한 방식: 가까운 프레임의 데이터 사용
    if ratio < 0.5:
        interpolated['enemies'] = copy.deepcopy(frame1.get('enemies', []))
    else:
        interpolated['enemies'] = copy.deepcopy(frame2.get('enemies', []))
    
    # 탄환 보간 - 이동 속도가 빠르므로 선형 보간
    interpolated['player_bullets'] = []
    interpolated['enemy_bullets'] = []
    
    # 플레이어 탄환
    if 'player_bullets' in frame1 and 'player_bullets' in frame2:
        # 프레임1과 프레임2의 탄환 개수가 비슷하면 보간, 아니면 가까운 쪽 사용
        if abs(len(frame1['player_bullets']) - len(frame2['player_bullets'])) <= 2:
            for b1, b2 in zip(frame1['player_bullets'], frame2['player_bullets']):
                interpolated['player_bullets'].append({
                    'x': round(interpolate_position(b1['x'], b2['x'], ratio)),
                    'y': round(interpolate_position(b1['y'], b2['y'], ratio))
                })
        else:
            if ratio < 0.5:
                interpolated['player_bullets'] = copy.deepcopy(frame1['player_bullets'])
            else:
                interpolated['player_bullets'] = copy.deepcopy(frame2['player_bullets'])
    
    # 적 탄환
    if 'enemy_bullets' in frame1 and 'enemy_bullets' in frame2:
        if abs(len(frame1['enemy_bullets']) - len(frame2['enemy_bullets'])) <= 2:
            for b1, b2 in zip(frame1['enemy_bullets'], frame2['enemy_bullets']):
                interpolated['enemy_bullets'].append({
                    'x': round(interpolate_position(b1['x'], b2['x'], ratio)),
                    'y': round(interpolate_position(b1['y'], b2['y'], ratio))
                })
        else:
            if ratio < 0.5:
                interpolated['enemy_bullets'] = copy.deepcopy(frame1['enemy_bullets'])
            else:
                interpolated['enemy_bullets'] = copy.deepcopy(frame2['enemy_bullets'])
    
    # 점수와 킬 수는 변경 시점에 즉시 반영
    if ratio < 0.5:
        interpolated['score'] = frame1.get('score', 0)
        interpolated['kills'] = frame1.get('kills', 0)
    else:
        interpolated['score'] = frame2.get('score', 0)
        interpolated['kills'] = frame2.get('kills', 0)
    
    # 액션은 frame1의 것을 유지 (다음 프레임까지 지속) - 액션이 있는 경우에만
    if 'action' in frame1:
        interpolated['action'] = frame1['action']
    elif 'action' in interpolated:
        # frame1에 액션이 없는데 interpolated에 있으면 제거
        del interpolated['action']
    
    return interpolated


def expand_frames_to_target_steps(frames: List[Dict[str, Any]], target_steps: int) -> List[Dict[str, Any]]:
    """프레임을 목표 스텝 수로 확장
    
    Args:
        frames: 원본 프레임 리스트
        target_steps: 목표 스텝 수
        
    Returns:
        확장된 프레임 리스트
    """
    if len(frames) >= target_steps:
        print(f"⚠️  이미 충분한 프레임이 있습니다: {len(frames)} >= {target_steps}")
        return frames
    
    print(f"🔄 프레임 보간 중: {len(frames)} → {target_steps} 프레임")
    
    expanded_frames = []
    original_count = len(frames)
    
    # 각 원본 프레임 사이에 보간 프레임 삽입
    for i in range(original_count - 1):
        frame1 = frames[i]
        frame2 = frames[i + 1]
        
        # 현재 위치에서 다음 위치까지 필요한 프레임 수 계산
        # 전체적으로 균등하게 분배
        current_step = len(expanded_frames)
        next_original_step = int((i + 1) / (original_count - 1) * (target_steps - 1))
        frames_to_insert = next_original_step - current_step
        
        # 첫 번째 프레임 추가
        frame1_copy = copy.deepcopy(frame1)
        frame1_copy['step'] = len(expanded_frames)
        expanded_frames.append(frame1_copy)
        
        # 중간 프레임 보간
        if frames_to_insert > 1:
            for j in range(1, frames_to_insert):
                ratio = j / frames_to_insert
                interpolated = interpolate_frame(frame1, frame2, ratio)
                interpolated['step'] = len(expanded_frames)
                expanded_frames.append(interpolated)
        
        # 진행률 표시
        if (i + 1) % 50 == 0:
            progress = (i + 1) / original_count * 100
            print(f"   진행률: {progress:.1f}% ({len(expanded_frames)}/{target_steps} 프레임)")
    
    # 마지막 프레임 추가
    last_frame = copy.deepcopy(frames[-1])
    
    # 남은 프레임 수만큼 마지막 프레임 복제
    while len(expanded_frames) < target_steps:
        frame_copy = copy.deepcopy(last_frame)
        frame_copy['step'] = len(expanded_frames)
        expanded_frames.append(frame_copy)
    
    print(f"✅ 보간 완료: {len(expanded_frames)} 프레임")
    return expanded_frames


def convert_to_web_format(frame: Dict[str, Any]) -> Dict[str, Any]:
    """웹 리플레이 형식으로 변환
    
    Args:
        frame: 원본 프레임
        
    Returns:
        웹 형식 프레임
    """
    # 탄환 통합
    bullets = []
    
    if 'enemy_bullets' in frame:
        for bullet in frame['enemy_bullets']:
            bullets.append({
                'x': bullet['x'],
                'y': bullet['y'],
                'type': 'enemy'
            })
    
    if 'player_bullets' in frame:
        for bullet in frame['player_bullets']:
            bullets.append({
                'x': bullet['x'],
                'y': bullet['y'],
                'type': 'player'
            })
    
    # 적 데이터
    enemies = []
    if 'enemies' in frame:
        for enemy in frame['enemies']:
            enemy_data = {
                'x': enemy['x'],
                'y': enemy['y']
            }
            if 'type' in enemy:
                enemy_data['type'] = enemy['type']
            enemies.append(enemy_data)
    
    # 웹 형식으로 변환
    web_frame = {
        'step': frame['step'],
        'player': frame['player'],
        'enemies': enemies,
        'bullets': bullets,
        'score': frame.get('score', 0)
    }
    
    # 액션이 있는 프레임에만 액션 추가
    if 'action' in frame:
        web_frame['action'] = frame['action']
    
    return web_frame


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python convert_replay_with_interpolation.py <input.json> [output.json]")
        print("\n예시:")
        print("  python convert_replay_with_interpolation.py replay_ep345_steps_1000.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_path):
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    try:
        print(f"📖 리플레이 파일 읽는 중: {input_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data['metadata']
        frames = data['frames']
        
        print(f"\n📊 원본 데이터:")
        print(f"   - 보고된 스텝: {metadata.get('episode_steps_reported', 'N/A')}")
        print(f"   - 저장된 프레임: {len(frames)}")
        print(f"   - 누락된 프레임: {metadata.get('episode_steps_reported', 0) - len(frames)}")
        
        # 목표 스텝 수 결정
        target_steps = metadata.get('episode_steps_reported', len(frames))
        
        if target_steps <= len(frames):
            print(f"\n⚠️  보간이 필요하지 않습니다. 일반 변환을 수행합니다.")
            expanded_frames = frames
        else:
            print(f"\n🎯 목표: {target_steps} 프레임으로 확장")
            expanded_frames = expand_frames_to_target_steps(frames, target_steps)
        
        # 웹 형식으로 변환
        print(f"\n🔄 웹 리플레이 형식으로 변환 중...")
        web_frames = []
        for i, frame in enumerate(expanded_frames):
            web_frame = convert_to_web_format(frame)
            web_frames.append(web_frame)
            
            if (i + 1) % 200 == 0:
                print(f"   {i + 1}/{len(expanded_frames)} 프레임 변환됨...")
        
        # 메타데이터 변환
        web_metadata = {
            'model_name': f"ep{metadata.get('episode_number', 0)}",
            'skill_level': metadata.get('skill_level', 0.5),
            'total_steps': len(web_frames),
            'episode_number': metadata.get('episode_number', 0),
            'timestamp': metadata.get('timestamp', '').replace(':', '').replace('-', '').replace('T', '_').split('.')[0],
            'episode_score': metadata.get('episode_score', 0),
            'episode_kills': metadata.get('episode_kills', 0),
            'target_category': metadata.get('target_category', 'unknown'),
            'interpolated': target_steps > len(frames)
        }
        
        output_data = {
            'metadata': web_metadata,
            'frames': web_frames
        }
        
        # 출력 경로 결정
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_interpolated_web{ext}"
        
        # 저장
        print(f"\n💾 저장 중: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 변환 완료!")
        print(f"\n📊 결과:")
        print(f"   - 최종 프레임 수: {len(web_frames)}")
        print(f"   - 보간 여부: {'예' if target_steps > len(frames) else '아니오'}")
        print(f"   - 파일 크기: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
        print(f"\n🎉 성공! 변환된 파일: {output_path}")
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


