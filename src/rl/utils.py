"""
랜덤 에이전트 구현을 위한 유틸리티 함수
"""

import os
import torch
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
import matplotlib.pyplot as plt
from datetime import datetime

def create_log_dir(base_dir: str = "logs") -> str:
    """
    타임스탬프가 포함된 로그 디렉토리 생성
    
    Args:
        base_dir: 기본 로그 디렉토리 경로
        
    Returns:
        str: 생성된 로그 디렉토리 경로
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(base_dir, f"run_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def plot_metrics(
    metrics: Dict[str, Any],
    save_path: Optional[str] = None,
    show: bool = False
) -> None:
    """
    학습 메트릭 시각화
    
    Args:
        metrics: 메트릭 정보를 담은 딕셔너리
        save_path: 저장 경로 (None이면 저장하지 않음)
        show: 그래프 표시 여부
    """
    # Figure 생성
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # 보상 그래프
    axes[0].plot(metrics["episode_rewards"])
    axes[0].set_title("Episode Rewards")
    axes[0].set_ylabel("Reward")
    axes[0].grid(True)
    
    # 에피소드 길이 그래프
    axes[1].plot(metrics["episode_lengths"])
    axes[1].set_title("Episode Lengths")
    axes[1].set_xlabel("Episode")
    axes[1].set_ylabel("Steps")
    axes[1].grid(True)
    
    # 전체 그래프 타이틀
    plt.suptitle("Random Agent Performance", fontsize=16)
    plt.tight_layout()
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path)
    
    if show:
        plt.show()
    else:
        plt.close()

def format_action(action_tensor: torch.Tensor) -> str:
    """
    행동 텐서를 사람이 읽기 쉬운 형태로 변환
    
    Args:
        action_tensor: 행동 텐서 [movement, shooting]
        
    Returns:
        str: 행동 설명 문자열
    """
    if not isinstance(action_tensor, torch.Tensor):
        return "Invalid action format"
    
    # 텐서에서 값 추출
    movement = action_tensor[0].item()
    shooting = action_tensor[1].item()
    
    # 이동 방향 텍스트
    if movement == 0:
        move_text = "왼쪽"
    elif movement == 1:
        move_text = "정지"
    elif movement == 2:
        move_text = "오른쪽"
    else:
        move_text = f"알 수 없음({movement})"
    
    # 발사 여부 텍스트
    shoot_text = "발사" if shooting == 1 else "대기"
    
    # 최종 문자열 반환
    return f"{move_text} + {shoot_text}"

def extract_state_info(observation: Dict[str, torch.Tensor]) -> str:
    """
    관측값에서 주요 상태 정보 추출
    
    Args:
        observation: 관측값 딕셔너리
        
    Returns:
        str: 상태 정보 문자열
    """
    # 플레이어 위치
    player_pos = observation.get("player_pos", torch.zeros(2))
    player_x, player_y = player_pos[0].item(), player_pos[1].item()
    
    # 생명력
    lives = observation.get("player_lives", torch.zeros(1))[0].item()
    
    # 점수
    score = observation.get("score", torch.zeros(1))[0].item()
    
    # 스테이지
    stage = observation.get("game_stage", torch.zeros(1))[0].item()
    
    # 텍스트 형식으로 반환
    return (
        f"위치: ({player_x:.1f}, {player_y:.1f}), "
        f"생명: {lives}, "
        f"점수: {score:.1f}, "
        f"스테이지: {stage}"
    ) 