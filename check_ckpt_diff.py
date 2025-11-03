import torch
import os

print("Checking checkpoint differences...")
print("="*70)

paths = [
    ("Beginner 0.1", r"src\src\models\ppo\stages\초급-목표-330스텝-3킬-skill-0.1\latest.pth"),
    ("Lower-Mid 0.3", r"src\src\models\ppo\stages\중하급-목표-590스텝-9킬-skill-0.3\latest.pth"),
    ("Upper-Mid 0.6", r"src\src\models\ppo\stages\중상급-목표-980스텝-18킬-skill-0.6\latest.pth"),
    ("Advanced 1.0", r"src\src\models\ppo\stages\고급-목표-1500스텝-30킬-skill-1.0\latest.pth"),
]

ckpts = []
for name, path in paths:
    if os.path.exists(path):
        ckpt = torch.load(path, map_location='cpu')
        ckpts.append((name, ckpt))
        param = list(ckpt['network_state_dict'].values())[0]
        print(f"{name:15s}: {param.flatten()[:3].tolist()}")
    else:
        print(f"{name:15s}: FILE NOT FOUND")

print("\n" + "="*70)
print("Weight Differences (L2 norm)")
print("="*70)

def calc_diff(ckpt1, ckpt2):
    total = 0
    for key in ckpt1['network_state_dict'].keys():
        p1 = ckpt1['network_state_dict'][key]
        p2 = ckpt2['network_state_dict'][key]
        total += torch.norm(p1 - p2).item()
    return total

for i in range(len(ckpts)-1):
    name1, ckpt1 = ckpts[i]
    name2, ckpt2 = ckpts[i+1]
    diff = calc_diff(ckpt1, ckpt2)
    print(f"{name1:15s} -> {name2:15s}: {diff:10.4f}")

print("\n" + "="*70)
print("Total change (First -> Last):", calc_diff(ckpts[0][1], ckpts[-1][1]))
print("="*70)

# Verdict
diff_1_2 = calc_diff(ckpts[0][1], ckpts[1][1])
diff_2_3 = calc_diff(ckpts[1][1], ckpts[2][1])
diff_3_4 = calc_diff(ckpts[2][1], ckpts[3][1])

print("\nVERDICT:")
if diff_1_2 < 0.1:
    print("  X Stage 1->2: Almost NO change! Transfer learning likely NOT working")
else:
    print(f"  O Stage 1->2: Meaningful change ({diff_1_2:.4f})")
    
if diff_2_3 < 0.1:
    print("  X Stage 2->3: Almost NO change! Transfer learning likely NOT working")
else:
    print(f"  O Stage 2->3: Meaningful change ({diff_2_3:.4f})")
    
if diff_3_4 < 0.1:
    print("  X Stage 3->4: Almost NO change! Transfer learning likely NOT working")
else:
    print(f"  O Stage 3->4: Meaningful change ({diff_3_4:.4f})")



