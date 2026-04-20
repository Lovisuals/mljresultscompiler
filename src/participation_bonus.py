"""
Participation Bonus Scoring Module (Grade 6)
Intelligently rewards participants based on test participation and previous performance
Feature: Mental rewarding system that incentivizes participation

Bonus Rules:
- 4-5 tests: 85-93% (random based on previous scores)
- 3 tests: 80%
- 2 tests: 70-75% (based on previous scores)
- 1 test: No bonus
"""

import logging
import random
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ParticipationBonusCalculator:
    """Calculate participation bonus scores (Grade 6)"""
    
    # Dynamic Bonus score ranges based on completion percentage:
    # >= 80% tests completed: 85-93%
    # >= 60% tests completed: 80% (fixed)
    # >= 40% tests completed: 70-75%
    # < 40% tests completed: Flat 50% (handled as default assignment)
    
    def __init__(self):
        """Initialize calculator"""
        self.logger = logger
    
    def calculate_previous_score_percentile(self, scores: List[float]) -> float:
        """
        Calculate where a participant's average score falls in their own distribution
        This helps determine which end of the bonus range to award
        
        Args:
            scores (List[float]): List of scores the participant got
            
        Returns:
            float: Percentile (0-1) representing their performance level
        """
        if not scores:
            return 0.5  # Middle range if no scores
        
        valid_scores = [s for s in scores if s is not None and s > 0]
        
        if not valid_scores:
            return 0.5
        
        avg_score = sum(valid_scores) / len(valid_scores)
        
        # Normalize to 0-1 range (assuming 0-100 scale, but cap at reasonable range)
        # If their average is below 50%, give lower bonus
        # If their average is above 80%, give higher bonus
        if avg_score >= 85:
            return 0.9  # Top tier: higher bonus
        elif avg_score >= 75:
            return 0.7  # Good performance: mid-high bonus
        elif avg_score >= 65:
            return 0.5  # Average performance: mid range
        elif avg_score >= 55:
            return 0.3  # Below average: lower bonus
        else:
            return 0.1  # Struggling: lowest bonus
    
    def calculate_bonus_score(self, 
                             participant_email: str,
                             participant_name: str,
                             participant_scores: Dict[int, float],
                             test_numbers: List[int]) -> Tuple[Optional[float], Dict]:
        """
        Calculate participation bonus score (Grade 6) for a participant
        
        Args:
            participant_email (str): Participant email
            participant_name (str): Participant name
            participant_scores (Dict[int, float]): {test_num: score} dict
            test_numbers (List[int]): All test numbers available
            
        Returns:
            Tuple[float, Dict]: (bonus_score, bonus_info_dict)
        """
        # Count how many tests the participant completed
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
        
        # Determine dynamic bonus range based on percentage of tests completed
        if completion_ratio >= 0.8:
            bonus_range = (85, 93)
        elif completion_ratio >= 0.6:
            bonus_range = (80, 80)
        elif completion_ratio >= 0.4:
            bonus_range = (70, 75)
        else:
            bonus_range = None
        
        if bonus_range is None:
            # Under 40% completion gets no bonus based on this logic
            return None, {
                'email': participant_email,
                'name': participant_name,
                'participation_count': participation_count,
                'bonus_score': None,
                'bonus_range': None,
                'reason': f'Completed {participation_count}/{total_tests} tests ({completion_ratio*100:.0f}%) - beneath bonus threshold'
            }
        
        # Calculate bonus score within the range
        min_bonus, max_bonus = bonus_range
        
        if min_bonus == max_bonus:
            # Fixed bonus (like 3 tests = 80%)
            bonus_score = float(min_bonus)
            calculation_method = f"Fixed bonus for {participation_count} tests"
        else:
            # Range-based bonus - determine position within range based on previous scores
            scores_list = [
                participant_scores.get(test_num) 
                for test_num in completed_tests 
                if participant_scores.get(test_num) is not None
            ]
            
            percentile = self.calculate_previous_score_percentile(scores_list)
            
            # Use percentile to pick position within range
            bonus_score = min_bonus + (max_bonus - min_bonus) * percentile
            bonus_score = round(bonus_score, 1)  # Round to 1 decimal
            
            avg_previous = sum(scores_list) / len(scores_list) if scores_list else 0
            calculation_method = (
                f"Range {min_bonus}-{max_bonus}% based on previous avg ({avg_previous:.1f}%)"
            )
        
        bonus_info = {
            'email': participant_email,
            'name': participant_name,
            'participation_count': participation_count,
            'bonus_score': bonus_score,
            'bonus_range': (min_bonus, max_bonus),
            'previous_average': sum([participant_scores.get(t) for t in completed_tests 
                                    if participant_scores.get(t) is not None]) / len(completed_tests) 
                               if completed_tests else 0,
            'calculation_method': calculation_method,
            'reason': f'Completed {participation_count} tests - eligible for bonus'
        }
        
        return bonus_score, bonus_info
    
    def apply_bonuses_to_consolidated(self,
                                      consolidated_data: Dict,
                                      test_numbers: List[int]) -> Dict:
        """
        Apply assignment scores and calculate final averages for all participants.
        
        Scoring rules:
        - Missing test scores count as 0 (not ignored)
        - Final average = (sum of all test scores + assignment score) / (num_tests + 1)
        - Assignment score for students with 4+ missing tests = 50% (flat)
        - Assignment score for others = participation-based bonus (existing logic)
        - Pass mark = 50%
        
        Args:
            consolidated_data (Dict): {email: {name, test_1_score, test_2_score, ...}}
            test_numbers (List[int]): List of test numbers
            
        Returns:
            Dict: Updated consolidated data with assignment_score, final_average, status
        """
        total_tests = len(test_numbers)
        
        for email, data in consolidated_data.items():
            # Extract test scores (None = missing = 0)
            participant_scores = {}
            completed_count = 0
            
            for test_num in test_numbers:
                score_key = f'test_{test_num}_score'
                score = data.get(score_key)
                participant_scores[test_num] = score
                if score is not None and score > 0:
                    completed_count += 1
            
            completion_ratio = completed_count / total_tests if total_tests > 0 else 0
            
            # Calculate assignment score
            if completion_ratio < 0.4:
                # Under 40% tests completed → flat 50% assignment score
                assignment_score = 50.0
                assignment_reason = f'Only {completed_count}/{total_tests} tests completed — flat 50% assignment'
            else:
                # Use normal bonus logic for students who did enough tests
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
            
            # Store assignment score (renamed from Grade_6_bonus)
            data['Grade_6_bonus'] = round(assignment_score, 2)
            
            # Calculate final average:
            # Sum ALL test scores (0 for missing) + assignment score, divided by (total_tests + 1)
            total_score = 0.0
            for test_num in test_numbers:
                score = participant_scores.get(test_num)
                total_score += score if (score is not None and score > 0) else 0.0
            
            total_score += assignment_score
            final_average = total_score / (total_tests + 1)  # +1 for assignment
            
            # Determine pass/fail (50% is pass mark)
            passed = final_average >= 50
            
            data['final_average'] = round(final_average, 2)
            data['num_tests_for_average'] = total_tests + 1
            data['passed'] = passed
            data['status'] = 'PASS' if passed else 'FAIL'
            
            logger.debug(
                f"  {data['name']}: {completed_count}/{total_tests} tests, "
                f"assignment={assignment_score:.1f}%, avg={final_average:.1f}% → {data['status']}"
            )
        
        # Log summary
        pass_count = sum(1 for d in consolidated_data.values() if d.get('status') == 'PASS')
        fail_count = len(consolidated_data) - pass_count
        logger.info(
            f"Scoring complete: {len(consolidated_data)} participants, "
            f"{pass_count} PASS, {fail_count} FAIL"
        )
        
        return consolidated_data


def add_participation_bonuses(consolidated_data: Dict, test_numbers: List[int]) -> Dict:
    """
    Convenience function to add participation bonuses
    
    Args:
        consolidated_data (Dict): Consolidated results data
        test_numbers (List[int]): Available test numbers
        
    Returns:
        Dict: Updated data with bonuses and final averages
    """
    calculator = ParticipationBonusCalculator()
    return calculator.apply_bonuses_to_consolidated(consolidated_data, test_numbers)
