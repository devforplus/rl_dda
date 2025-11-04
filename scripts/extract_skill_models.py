"""
특정 skill_level에서의 체크포인트 추출 스크립트

학습 완료 후 skill 0.1, 0.5, 1.0 시점의 모델을 추출하여
별도의 파일로 저장합니다.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))


def find_checkpoint_files(checkpoint_dir: str = "src/models/ppo") -> List[Tuple[str, int]]:
    """체크포인트 파일들을 찾아 반환
    
    Returns:
        List of (filepath, episode_number) tuples
    """
    checkpoint_files = []
    checkpoint_path = Path(checkpoint_dir)
    
    if not checkpoint_path.exists():
        print(f"❌ 체크포인트 디렉토리를 찾을 수 없습니다: {checkpoint_dir}")
        return []
    
    # ppo_agent_episode_*.pth 패턴의 파일 찾기
    for file in checkpoint_path.glob("ppo_agent_episode_*.pth"):
        # 에피소드 번호 추출
        match = re.search(r'episode_(\d+)', file.name)
        if match:
            episode_num = int(match.group(1))
            checkpoint_files.append((str(file), episode_num))
    
    # 에피소드 번호로 정렬
    checkpoint_files.sort(key=lambda x: x[1])
    
    print(f"✅ {len(checkpoint_files)}개의 체크포인트 파일을 찾았습니다.")
    return checkpoint_files


def load_training_log(log_dir: str = "src/models/ppo") -> Optional[Dict]:
    """학습 로그 파일 로드
    
    학습 과정에서 각 에피소드의 skill_level을 기록한 로그를 로드합니다.
    """
    log_path = Path(log_dir)
    
    # 최신 curriculum_history JSON 파일 찾기
    json_files = list(log_path.glob("curriculum_history_*.json"))
    
    if not json_files:
        print("⚠️  커리큘럼 히스토리 파일을 찾을 수 없습니다.")
        return None
    
    # 가장 최신 파일 사용
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 커리큘럼 히스토리 로드: {latest_file.name}")
        return data
    except Exception as e:
        print(f"❌ 로그 파일 로드 실패: {e}")
        return None


def find_skill_transition_episodes(log_data: Optional[Dict]) -> Dict[float, int]:
    """각 skill_level이 시작된 에피소드 번호를 찾기
    
    Returns:
        Dict[skill_level, episode_number]
    """
    if not log_data or 'stages' not in log_data:
        return {}
    
    transitions = {}
    cumulative_episodes = 0
    
    for stage in log_data['stages']:
        skill = stage.get('skill_level')
        episodes_in_stage = stage.get('episodes', 0)
        
        if skill is not None:
            # 각 스테이지의 시작 에피소드
            transitions[skill] = cumulative_episodes
            cumulative_episodes += episodes_in_stage
    
    return transitions


def extract_models_for_skills(
    target_skills: List[float] = [0.1, 0.5, 1.0],
    checkpoint_dir: str = "src/models/ppo",
    output_dir: str = "src/models/ppo/skill_models"
) -> None:
    """특정 skill_level의 모델을 추출
    
    Args:
        target_skills: 추출할 skill_level 리스트
        checkpoint_dir: 체크포인트 디렉토리
        output_dir: 추출된 모델 저장 디렉토리
    """
    print("=" * 70)
    print("🔍 Skill Level별 모델 추출 시작")
    print("=" * 70)
    
    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 체크포인트 파일 찾기
    checkpoint_files = find_checkpoint_files(checkpoint_dir)
    if not checkpoint_files:
        print("❌ 체크포인트 파일이 없습니다.")
        return
    
    # 학습 로그 로드
    log_data = load_training_log(checkpoint_dir)
    transitions = find_skill_transition_episodes(log_data)
    
    if not transitions:
        print("⚠️  커리큘럼 히스토리를 찾을 수 없습니다.")
        print("   각 skill의 마지막 체크포인트를 추정합니다...")
        
        # 로그가 없는 경우 균등하게 분배 추정
        total_episodes = checkpoint_files[-1][1] if checkpoint_files else 0
        transitions = {
            0.1: int(total_episodes * 0.1),
            0.3: int(total_episodes * 0.25),
            0.5: int(total_episodes * 0.45),
            0.7: int(total_episodes * 0.65),
            0.9: int(total_episodes * 0.85),
            1.0: total_episodes
        }
    
    print(f"\n📊 Skill 전환 시점:")
    for skill, ep in sorted(transitions.items()):
        print(f"   Skill {skill:.1f}: 에피소드 {ep}")
    
    # 각 target skill에 대해 가장 가까운 체크포인트 찾기
    extracted_models = {}
    
    for skill in target_skills:
        print(f"\n🎯 Skill {skill:.1f} 모델 추출 중...")
        
        # 해당 skill의 마지막 에피소드 찾기
        target_episode = transitions.get(skill)
        
        if target_episode is None:
            # 다음 skill의 시작점 - 1을 사용
            next_skills = [s for s in transitions.keys() if s > skill]
            if next_skills:
                next_skill = min(next_skills)
                target_episode = transitions[next_skill] - 1
            else:
                # 마지막 skill이면 최종 체크포인트
                target_episode = checkpoint_files[-1][1]
        
        # 가장 가까운 체크포인트 찾기
        best_checkpoint = None
        min_distance = float('inf')
        
        for filepath, episode in checkpoint_files:
            if episode <= target_episode:
                distance = target_episode - episode
                if distance < min_distance:
                    min_distance = distance
                    best_checkpoint = (filepath, episode)
        
        # 정확한 에피소드가 없으면 다음 가까운 것 사용
        if best_checkpoint is None and checkpoint_files:
            for filepath, episode in checkpoint_files:
                distance = abs(episode - target_episode)
                if distance < min_distance:
                    min_distance = distance
                    best_checkpoint = (filepath, episode)
        
        if best_checkpoint:
            src_path, episode = best_checkpoint
            dst_filename = f"ppo_agent_skill_{skill:.1f}.pth"
            dst_path = output_path / dst_filename
            
            # 파일 복사
            shutil.copy2(src_path, dst_path)
            extracted_models[skill] = str(dst_path)
            
            print(f"   ✅ 추출 완료:")
            print(f"      소스: {Path(src_path).name} (에피소드 {episode})")
            print(f"      대상: {dst_filename}")
            print(f"      목표 에피소드: {target_episode}, 실제: {episode} (차이: {abs(episode - target_episode)})")
        else:
            print(f"   ❌ Skill {skill:.1f}에 해당하는 체크포인트를 찾을 수 없습니다.")
    
    # 요약
    print("\n" + "=" * 70)
    print("✅ 모델 추출 완료")
    print("=" * 70)
    print(f"\n추출된 모델 ({len(extracted_models)}개):")
    for skill, path in sorted(extracted_models.items()):
        print(f"   Skill {skill:.1f}: {path}")
    
    # 메타데이터 저장
    metadata = {
        "extracted_skills": list(extracted_models.keys()),
        "models": extracted_models,
        "transitions": transitions,
        "checkpoint_dir": checkpoint_dir,
        "output_dir": output_dir
    }
    
    metadata_path = output_path / "extraction_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n메타데이터 저장: {metadata_path}")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Skill별 모델 추출")
    parser.add_argument(
        "--skills",
        type=float,
        nargs="+",
        default=[0.1, 0.5, 1.0],
        help="추출할 skill levels (기본값: 0.1 0.5 1.0)"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="src/models/ppo",
        help="체크포인트 디렉토리"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="src/models/ppo/skill_models",
        help="추출된 모델 저장 디렉토리"
    )
    
    args = parser.parse_args()
    
    extract_models_for_skills(
        target_skills=args.skills,
        checkpoint_dir=args.checkpoint_dir,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()


