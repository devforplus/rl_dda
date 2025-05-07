import unittest
from .score_config import MAX_SCORE, ENEMY_SCORE_NORMAL, ENEMY_SCORE_BOSS

class TestScoreConfig(unittest.TestCase):
    def test_max_score(self):
        """최대 점수 값이 올바른지 테스트"""
        self.assertEqual(MAX_SCORE, 999999)
        self.assertIsInstance(MAX_SCORE, int)
        self.assertGreater(MAX_SCORE, 0)
        self.assertLess(MAX_SCORE, 1000000)  # 6자리 숫자 확인

    def test_enemy_scores(self):
        """적 처치 점수 값들이 올바른지 테스트"""
        # 일반 적 처치 점수 테스트
        self.assertEqual(ENEMY_SCORE_NORMAL, 100)
        self.assertIsInstance(ENEMY_SCORE_NORMAL, int)
        self.assertGreater(ENEMY_SCORE_NORMAL, 0)

        # 보스 처치 점수 테스트
        self.assertEqual(ENEMY_SCORE_BOSS, 5000)
        self.assertIsInstance(ENEMY_SCORE_BOSS, int)
        self.assertGreater(ENEMY_SCORE_BOSS, 0)
        self.assertGreater(ENEMY_SCORE_BOSS, ENEMY_SCORE_NORMAL)  # 보스 점수가 일반 적 점수보다 높은지 확인

    def test_score_relationships(self):
        """점수들 간의 관계가 올바른지 테스트"""
        # 보스 처치 점수가 일반 적 처치 점수의 50배인지 확인
        self.assertEqual(ENEMY_SCORE_BOSS, ENEMY_SCORE_NORMAL * 50)
        
        # 최대 점수가 보스 처치 점수의 199배 이상인지 확인 (999999 / 5000 ≈ 199.9998)
        self.assertGreaterEqual(MAX_SCORE, ENEMY_SCORE_BOSS * 199)

if __name__ == '__main__':
    unittest.main() 