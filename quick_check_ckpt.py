import torch

ckpt1_path = 'src/src/models/ppo/stages/초급-목표-330스텝-3킬-skill-0.1/latest.pth'
ckpt2_path = 'src/src/models/ppo/stages/중하급-목표-590스텝-9킬-skill-0.3/latest.pth'
ckpt3_path = 'src/src/models/ppo/stages/중상급-목표-980스텝-18킬-skill-0.6/latest.pth'
ckpt4_path = 'src/src/models/ppo/stages/고급-목표-1500스텝-30킬-skill-1.0/latest.pth'

print("체크포인트 가중치 차이 분석\n")

ckpt1 = torch.load(ckpt1_path, map_location='cpu')
ckpt2 = torch.load(ckpt2_path, map_location='cpu')
ckpt3 = torch.load(ckpt3_path, map_location='cpu')
ckpt4 = torch.load(ckpt4_path, map_location='cpu')

print("=== 초급 (skill=0.1) ===")
print(f"키: {list(ckpt1.keys())}")
param1 = list(ckpt1['network_state_dict'].values())[0]
print(f"첫 파라미터 shape: {param1.shape}")
print(f"첫 5개 값: {param1.flatten()[:5].tolist()}\n")

print("=== 중하급 (skill=0.3) ===")
param2 = list(ckpt2['network_state_dict'].values())[0]
print(f"첫 파라미터 shape: {param2.shape}")
print(f"첫 5개 값: {param2.flatten()[:5].tolist()}\n")

print("=== 중상급 (skill=0.6) ===")
param3 = list(ckpt3['network_state_dict'].values())[0]
print(f"첫 파라미터 shape: {param3.shape}")
print(f"첫 5개 값: {param3.flatten()[:5].tolist()}\n")

print("=== 고급 (skill=1.0) ===")
param4 = list(ckpt4['network_state_dict'].values())[0]
print(f"첫 파라미터 shape: {param4.shape}")
print(f"첫 5개 값: {param4.flatten()[:5].tolist()}\n")

print("="*60)
print("가중치 차이 비교")
print("="*60)

diff_1_2 = torch.norm(param1 - param2).item()
diff_2_3 = torch.norm(param2 - param3).item()
diff_3_4 = torch.norm(param3 - param4).item()
diff_1_4 = torch.norm(param1 - param4).item()

print(f"초급 → 중하급: L2 차이 = {diff_1_2:.6f}")
print(f"중하급 → 중상급: L2 차이 = {diff_2_3:.6f}")
print(f"중상급 → 고급:   L2 차이 = {diff_3_4:.6f}")
print(f"초급 → 고급:     L2 차이 = {diff_1_4:.6f}")
print()

# 동일 여부 체크
print("완전 동일 체크:")
print(f"초급 == 중하급: {torch.equal(param1, param2)}")
print(f"초급 == 중상급: {torch.equal(param1, param3)}")
print(f"초급 == 고급:   {torch.equal(param1, param4)}")
print()

# 전체 네트워크 차이
print("="*60)
print("전체 네트워크 가중치 차이")
print("="*60)

def compute_total_diff(ckpt_a, ckpt_b):
    total_diff = 0
    for key in ckpt_a['network_state_dict'].keys():
        param_a = ckpt_a['network_state_dict'][key]
        param_b = ckpt_b['network_state_dict'][key]
        diff = torch.norm(param_a - param_b).item()
        total_diff += diff
    return total_diff

total_diff_1_2 = compute_total_diff(ckpt1, ckpt2)
total_diff_2_3 = compute_total_diff(ckpt2, ckpt3)
total_diff_3_4 = compute_total_diff(ckpt3, ckpt4)
total_diff_1_4 = compute_total_diff(ckpt1, ckpt4)

print(f"초급 → 중하급: 총 L2 차이 = {total_diff_1_2:.4f}")
print(f"중하급 → 중상급: 총 L2 차이 = {total_diff_2_3:.4f}")
print(f"중상급 → 고급:   총 L2 차이 = {total_diff_3_4:.4f}")
print(f"초급 → 고급:     총 L2 차이 = {total_diff_1_4:.4f}")
print()

print("="*60)
print("판정")
print("="*60)

if total_diff_1_2 < 0.01:
    print("❌ 초급 → 중하급: 거의 차이 없음! 전이학습 미작동 의심")
else:
    print(f"✅ 초급 → 중하급: 유의미한 차이 ({total_diff_1_2:.4f})")

if total_diff_2_3 < 0.01:
    print("❌ 중하급 → 중상급: 거의 차이 없음! 전이학습 미작동 의심")
else:
    print(f"✅ 중하급 → 중상급: 유의미한 차이 ({total_diff_2_3:.4f})")

if total_diff_3_4 < 0.01:
    print("❌ 중상급 → 고급: 거의 차이 없음! 전이학습 미작동 의심")
else:
    print(f"✅ 중상급 → 고급: 유의미한 차이 ({total_diff_3_4:.4f})")
    
if total_diff_1_4 < 0.1:
    print("\n⚠️  전체 학습 진행이 거의 없습니다!")
    print("   → 체크포인트는 저장되었지만 실제 학습이 거의 안 됨")
else:
    print(f"\n✅ 전체적으로 학습이 진행됨 (총 차이: {total_diff_1_4:.4f})")



