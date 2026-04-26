import logging
import random
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ParticipationBonusCalculator:

    def __init__(self):
        self.logger = logger

    def calculate_previous_score_percentile(self, scores: List[float]) -> float:
        if not scores:
            return 0.5
        valid_scores = [s for s in scores if s is not None and s > 0]
        if not valid_scores:
            return 0.5
        avg_score = sum(valid_scores) / len(valid_scores)
        if avg_score >= 85:
            return 0.9
        elif avg_score >= 75:
            return 0.7
        elif avg_score >= 65:
            return 0.5
        elif avg_score >= 55:
            return 0.3
        else:
            return 0.1

    def calculate_bonus_score(self,
                             participant_email: str,
                             participant_name: str,
                             participant_scores: Dict[int, float],
                             test_numbers: List[int]) -> Tuple[Optional[float], Dict]:
        completed_tests = [
            test_num for test_num in test_numbers
            if participant_scores.get(test_num) is not None
            and participant_scores.get(test_num) > 0
        ]
        participation_count = len(completed_tests)
        total_tests = len(test_numbers)
        self.logger.info(
            f"  Bonus calc for {participant_name} ({participant_email}): "
            f"{participation_count}/{total_tests} tests completed"
        )
        if total_tests == 0:
            return None, {'reason': 'No tests available'}
        completion_ratio = participation_count / total_tests
        if completion_ratio >= 0.8:
            bonus_range = (85, 93)
        elif completion_ratio >= 0.6:
            bonus_range = (80, 80)
        elif completion_ratio >= 0.4:
            bonus_range = (70, 75)
        else:
            bonus_range = None
        if bonus_range is None:
            return None, {
                'email': participant_email,
                'name': participant_name,
                'tests_completed': participation_count,
                'bonus_score': None,
                'bonus_range': None,
                'reason': f'Completed {participation_count}/{total_tests} tests ({completion_ratio*100:.0f}%) - beneath bonus threshold'
            }
        min_bonus, max_bonus = bonus_range
        if min_bonus == max_bonus:
            bonus_score = float(min_bonus)
            calculation_method = f"Fixed bonus for {participation_count} tests"
        else:
            scores_list = [
                participant_scores.get(test_num)
                for test_num in completed_tests
                if participant_scores.get(test_num) is not None
            ]
            percentile = self.calculate_previous_score_percentile(scores_list)
            bonus_score = min_bonus + (max_bonus - min_bonus) * percentile
            bonus_score = round(bonus_score, 1)
            avg_previous = sum(scores_list) / len(scores_list) if scores_list else 0
            calculation_method = (
                f"Range {min_bonus}-{max_bonus}% based on previous avg ({avg_previous:.1f}%)"
            )
        bonus_info = {
            'email': participant_email,
            'name': participant_name,
            'tests_completed': participation_count,
            'bonus_score': bonus_score,
            'bonus_range': (min_bonus, max_bonus),
            'avg_raw_score': sum([participant_scores.get(t) for t in completed_tests
                                    if participant_scores.get(t) is not None]) / len(completed_tests)
                               if completed_tests else 0,
            'calculation_method': calculation_method,
            'reason': f'Completed {participation_count} tests - eligible for bonus'
        }
        return bonus_score, bonus_info

    def apply_bonuses_to_consolidated(self,
                                      consolidated_data: Dict,
                                      test_numbers: List[int]) -> Dict:
        total_tests = len(test_numbers)
        for email, data in consolidated_data.items():
            participant_scores = {}
            completed_count = 0
            for test_num in test_numbers:
                score_key = f'test_{test_num}_score'
                score = data.get(score_key)
                participant_scores[test_num] = score
                if score is not None and score > 0:
                    completed_count += 1
            completion_ratio = completed_count / total_tests if total_tests > 0 else 0
            if completion_ratio < 0.4:
                assignment_score = 50.0
                assignment_reason = f'Only {completed_count}/{total_tests} tests completed — flat 50% assignment'
            else:
                bonus_score, bonus_info = self.calculate_bonus_score(
                    participant_email=email,
                    participant_name=data.get('name', 'Unknown'),
                    participant_scores=participant_scores,
                    test_numbers=test_numbers
                )
                if bonus_score is not None:
                    assignment_score = bonus_score
                    assignment_reason = bonus_info.get('calculation_method', '')
                else:
                    assignment_score = 50.0
                    assignment_reason = 'Default assignment score'
            data['Grade_6_bonus'] = round(assignment_score, 2)
            total_score = 0.0
            for test_num in test_numbers:
                score = participant_scores.get(test_num)
                total_score += score if (score is not None and score > 0) else 0.0
            total_score += assignment_score
            final_average = total_score / (total_tests + 1)
            passed = final_average >= 50
            data['final_average'] = round(final_average, 2)
            data['num_tests_for_average'] = total_tests + 1
            data['passed'] = passed
            data['status'] = 'PASS' if passed else 'FAIL'
        pass_count = sum(1 for d in consolidated_data.values() if d.get('status') == 'PASS')
        fail_count = len(consolidated_data) - pass_count
        logger.info(
            f"Scoring complete: {len(consolidated_data)} participants, "
            f"{pass_count} PASS, {fail_count} FAIL"
        )
        return consolidated_data

def add_participation_bonuses(consolidated_data: Dict, test_numbers: List[int]) -> Dict:
    calculator = ParticipationBonusCalculator()
    return calculator.apply_bonuses_to_consolidated(consolidated_data, test_numbers)
