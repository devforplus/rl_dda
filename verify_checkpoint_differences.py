#!/usr/bin/env python3
"""
체크포인트 파일들이 실제로 다른 가중치를 가지고 있는지 확인하는 스크립트
"""

import torch
import os
import numpy as np


def compare_checkpoints():
    """체크포인트 간 가중치 차이 분석"""
    
    checkpoints = [
        ('초급 (0.1)', 'src/src/models/ppo/stages/초급-목표-330스텝-3킬-skill-0.1/latest.pth'),
        ('중하급 (0.3)', 'src/src/models/ppo/stages/중하급-목표-590스텝-9킬-skill-0.3/latest.pth'),
        ('중상급 (0.6)', 'src/src/models/ppo/stages/중상급-목표-980스텝-18킬-skill-0.6/latest.pth'),
        ('고급 (1.0)', 'src/src/models/ppo/stages/고급-목표-1500스텝-30킬-skill-1.0/latest.pth'),
    ]
    
    print("=" * 80)
    print("🔍 체크포인트 가중치 차이 분석")
    print("=" * 80)
    print()
    
    # 각 체크포인트 로드
    loaded_checkpoints = []
    for name, path in checkpoints:
        if os.path.exists(path):
            try:
                checkpoint = torch.load(path, map_location='cpu')
                loaded_checkpoints.append((name, checkpoint))
                print(f"✅ {name}: {path}")
                print(f"   키 개수: {len(checkpoint.keys())}")
                print(f"   키 목록: {list(checkpoint.keys())}")
                
                # network_state_dict에서 가중치 확인
                state_dict_key = 'network_state_dict' if 'network_state_dict' in checkpoint else 'actor'
                if state_dict_key in checkpoint:
                    # 첫 번째 레이어의 가중치 일부만 샘플링
                    first_param = None
                    for key in checkpoint[state_dict_key].keys():
                        if 'weight' in key:
                            first_param = checkpoint[state_dict_key][key]
                            break
                    if first_param is not None:
                        flat = first_param.flatten()
                        print(f"   샘플 가중치 (첫 5개): {flat[:5].numpy()}")
                        print(f"   가중치 범위: [{flat.min().item():.4f}, {flat.max().item():.4f}]")
                        print(f"   가중치 평균: {flat.mean().item():.4f}")
                print()
            except Exception as e:
                print(f"❌ {name}: 로드 실패 - {e}\n")
        else:
            print(f"⚠️  {name}: 파일 없음 - {path}\n")
    
    print("=" * 80)
    print()
    
    if len(loaded_checkpoints) < 2:
        print("❌ 비교할 체크포인트가 부족합니다.")
        return
    
    # 연속된 체크포인트 간 차이 비교
    print("📊 연속 스테이지 간 가중치 차이")
    print("-" * 80)
    print()
    
    for i in range(len(loaded_checkpoints) - 1):
        name1, ckpt1 = loaded_checkpoints[i]
        name2, ckpt2 = loaded_checkpoints[i + 1]
        
        print(f"▶ {name1} → {name2}")
        
        # network_state_dict 또는 actor 키 사용
        state_key = 'network_state_dict' if 'network_state_dict' in ckpt1 else 'actor'
        
        if state_key not in ckpt1 or state_key not in ckpt2:
            print(f"  ⚠️  {state_key} 가중치 없음")
            continue
        
        # 각 레이어별 차이 계산
        total_diff = 0
        total_params = 0
        layer_diffs = []
        
        for key in ckpt1[state_key].keys():
            if key in ckpt2[state_key]:
                param1 = ckpt1[state_key][key].flatten()
                param2 = ckpt2[state_key][key].flatten()
                
                # L2 차이
                diff = torch.norm(param2 - param1).item()
                norm1 = torch.norm(param1).item()
                
                # 상대 차이 (%)
                rel_diff = (diff / norm1 * 100) if norm1 > 0 else 0
                
                layer_diffs.append({
                    'key': key,
                    'diff': diff,
                    'rel_diff': rel_diff,
                })
                
                total_diff += diff
                total_params += param1.numel()
        
        print(f"  총 파라미터 수: {total_params:,}")
        print(f"  총 L2 차이: {total_diff:.4f}")
        print(f"  평균 차이: {total_diff / len(layer_diffs):.4f}")
        print()
        
        # 가장 많이 변한 레이어 3개
        layer_diffs.sort(key=lambda x: x['diff'], reverse=True)
        print("  가장 많이 변한 레이어:")
        for j, layer in enumerate(layer_diffs[:3], 1):
            print(f"    {j}. {layer['key']}: L2={layer['diff']:.4f}, "
                  f"상대 차이={layer['rel_diff']:.2f}%")
        print()
        
        # 판단
        if total_diff < 0.1:
            print("  ❌ 거의 변화 없음! 전이학습이 작동하지 않았을 가능성 높음")
        elif total_diff < 1.0:
            print("  ⚠️  약간의 변화만 있음 (학습이 매우 느리거나 조기 종료)")
        else:
            print("  ✅ 유의미한 변화 있음 (학습이 진행됨)")
        
        print()
        print("-" * 80)
        print()
    
    # 첫 번째와 마지막 비교
    if len(loaded_checkpoints) >= 2:
        name1, ckpt1 = loaded_checkpoints[0]
        name2, ckpt2 = loaded_checkpoints[-1]
        
        print(f"▶ 전체 변화: {name1} → {name2}")
        
        state_key = 'network_state_dict' if 'network_state_dict' in ckpt1 else 'actor'
        
        if state_key in ckpt1 and state_key in ckpt2:
            total_diff = 0
            for key in ckpt1[state_key].keys():
                if key in ckpt2[state_key]:
                    param1 = ckpt1[state_key][key].flatten()
                    param2 = ckpt2[state_key][key].flatten()
                    diff = torch.norm(param2 - param1).item()
                    total_diff += diff
            
            print(f"  총 L2 차이: {total_diff:.4f}")
            
            if total_diff < 1.0:
                print("  ❌ 전체 학습 진행이 거의 없음!")
            elif total_diff < 5.0:
                print("  ⚠️  제한적인 학습만 진행됨")
            else:
                print("  ✅ 상당한 학습 진행")
        
        print()
    
    print("=" * 80)


def check_transfer_learning_evidence():
    """전이학습의 증거를 찾기"""
    
    print()
    print("🔍 전이학습 증거 확인")
    print("-" * 80)
    print()
    
    # 1. 체크포인트 메타데이터 확인
    print("▶ 체크포인트 메타데이터:")
    checkpoints = [
        'src/src/models/ppo/stages/초급-목표-330스텝-3킬-skill-0.1/latest.pth',
        'src/src/models/ppo/stages/중하급-목표-590스텝-9킬-skill-0.3/latest.pth',
    ]
    
    for path in checkpoints:
        if os.path.exists(path):
            try:
                ckpt = torch.load(path, map_location='cpu')
                print(f"\n  {os.path.basename(os.path.dirname(path))}:")
                print(f"    키: {list(ckpt.keys())}")
                
                # episode, step 등의 메타데이터가 있는지 확인
                for key in ['episode', 'step', 'total_steps', 'skill_level']:
                    if key in ckpt:
                        print(f"    {key}: {ckpt[key]}")
            except Exception as e:
                print(f"  ❌ {path}: {e}")
    
    print()
    print("-" * 80)


def main():
    print()
    compare_checkpoints()
    check_transfer_learning_evidence()
    
    print()
    print("💡 결론:")
    print()
    print("  전이학습이 제대로 작동했다면:")
    print("  1. 각 스테이지의 체크포인트가 서로 다른 가중치를 가져야 함")
    print("  2. 연속된 스테이지 간 유의미한 차이가 있어야 함")
    print("  3. 전체적으로 초급 → 고급으로 갈수록 누적된 변화가 있어야 함")
    print()
    print("  만약 차이가 거의 없다면:")
    print("  → 체크포인트가 저장은 되었지만 로드되지 않았을 가능성")
    print("  → 또는 매우 짧은 학습으로 인해 변화가 미미함")
    print()


if __name__ == "__main__":
    main()

