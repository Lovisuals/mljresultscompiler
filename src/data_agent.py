# -*- coding: utf-8 -*-
"""
Agentic Data Manipulation Module
Allows AI to execute actual data transformations based on natural language requests.

Capabilities:
- Add/remove columns
- Random scoring
- Grade calculation (pass/fail)
- Score collation
- Custom formulas
- Data filtering
"""

import os
import json
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class DataAgent:
    """
    Agentic data manipulation - executes real changes on consolidated data.
    
    The AI doesn't just advise - it ACTS.
    """
    
    def __init__(self):
        self.action_history: List[Dict] = []
        self.available_actions = {
            "add_column": self.add_column,
            "add_random_scores": self.add_random_scores,
            "add_grades": self.add_grades,
            "collate_scores": self.collate_scores,
            "add_pass_fail": self.add_pass_fail,
            "calculate_bonus": self.calculate_bonus,
            "filter_data": self.filter_data,
            "sort_data": self.sort_data,
            "remove_column": self.remove_column,
            "rename_column": self.rename_column,
            "add_formula_column": self.add_formula_column,
            "add_rank": self.add_rank,
        }
        
        # Grading thresholds (configurable)
        self.grade_thresholds = {
            "A": 90,
            "B": 80,
            "C": 70,
            "D": 60,
            "F": 0
        }
        self.pass_threshold = 60
        
        logger.info("✓ DataAgent initialized with %d actions", len(self.available_actions))
    
    def execute(self, action: str, data: pd.DataFrame, params: Dict) -> Dict:
        """
        Execute an action on the data.
        
        Args:
            action: Action name (e.g., "add_random_scores")
            data: DataFrame to manipulate
            params: Action parameters
            
        Returns:
            Dict with success status, modified data, and message
        """
        if action not in self.available_actions:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": list(self.available_actions.keys())
            }
        
        try:
            result = self.available_actions[action](data, params)
            
            # Log action
            self.action_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "params": params,
                "success": result["success"],
                "rows_affected": len(result.get("data", data)) if result["success"] else 0
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Action {action} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    # ==================== COLUMN OPERATIONS ====================
    
    def add_column(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add a new column with a default value"""
        column_name = params.get("column_name", "New_Column")
        default_value = params.get("default_value", "")
        
        data[column_name] = default_value
        
        return {
            "success": True,
            "data": data,
            "message": f"Added column '{column_name}' with default value '{default_value}'",
            "column_added": column_name
        }
    
    def remove_column(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Remove a column"""
        column_name = params.get("column_name")
        
        if column_name not in data.columns:
            return {
                "success": False,
                "error": f"Column '{column_name}' not found",
                "available_columns": list(data.columns)
            }
        
        data = data.drop(columns=[column_name])
        
        return {
            "success": True,
            "data": data,
            "message": f"Removed column '{column_name}'"
        }
    
    def rename_column(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Rename a column"""
        old_name = params.get("old_name")
        new_name = params.get("new_name")
        
        if old_name not in data.columns:
            return {
                "success": False,
                "error": f"Column '{old_name}' not found",
                "available_columns": list(data.columns)
            }
        
        data = data.rename(columns={old_name: new_name})
        
        return {
            "success": True,
            "data": data,
            "message": f"Renamed column '{old_name}' to '{new_name}'"
        }
    
    # ==================== SCORING OPERATIONS ====================
    
    def add_random_scores(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add random scores to participants"""
        column_name = params.get("column_name", "Random_Score")
        min_score = params.get("min_score", 0)
        max_score = params.get("max_score", 100)
        
        data[column_name] = [random.randint(min_score, max_score) for _ in range(len(data))]
        
        return {
            "success": True,
            "data": data,
            "message": f"Added random scores ({min_score}-{max_score}) in column '{column_name}'",
            "column_added": column_name,
            "score_range": {"min": min_score, "max": max_score}
        }
    
    def add_grades(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add letter grades based on a score column"""
        score_column = params.get("score_column")
        grade_column = params.get("grade_column", "Grade")
        thresholds = params.get("thresholds", self.grade_thresholds)
        
        if score_column not in data.columns:
            return {
                "success": False,
                "error": f"Score column '{score_column}' not found",
                "available_columns": list(data.columns)
            }
        
        def get_grade(score):
            try:
                score = float(score)
                for grade, threshold in sorted(thresholds.items(), key=lambda x: x[1], reverse=True):
                    if score >= threshold:
                        return grade
                return "F"
            except (ValueError, TypeError):
                return "N/A"
        
        data[grade_column] = data[score_column].apply(get_grade)
        
        return {
            "success": True,
            "data": data,
            "message": f"Added grades in '{grade_column}' based on '{score_column}'",
            "column_added": grade_column,
            "thresholds_used": thresholds
        }
    
    def add_pass_fail(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add pass/fail status based on score threshold"""
        score_column = params.get("score_column")
        result_column = params.get("result_column", "Status")
        threshold = params.get("threshold", self.pass_threshold)
        
        if score_column not in data.columns:
            return {
                "success": False,
                "error": f"Score column '{score_column}' not found",
                "available_columns": list(data.columns)
            }
        
        def get_status(score):
            try:
                return "PASSED" if float(score) >= threshold else "FAILED"
            except (ValueError, TypeError):
                return "N/A"
        
        data[result_column] = data[score_column].apply(get_status)
        
        # Calculate stats
        passed = (data[result_column] == "PASSED").sum()
        failed = (data[result_column] == "FAILED").sum()
        
        return {
            "success": True,
            "data": data,
            "message": f"Added pass/fail status (threshold: {threshold})",
            "column_added": result_column,
            "stats": {
                "passed": int(passed),
                "failed": int(failed),
                "pass_rate": f"{(passed / len(data) * 100):.1f}%"
            }
        }
    
    def collate_scores(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Collate (sum/average) multiple score columns into one"""
        score_columns = params.get("score_columns", [])
        result_column = params.get("result_column", "Total_Score")
        method = params.get("method", "sum")  # sum, average, max, min
        
        # Auto-detect score columns if not specified
        if not score_columns:
            score_columns = [col for col in data.columns 
                           if any(kw in col.lower() for kw in ['score', 'test', 'exam', 'quiz', 'mark'])]
        
        if not score_columns:
            return {
                "success": False,
                "error": "No score columns found or specified",
                "available_columns": list(data.columns)
            }
        
        # Validate columns exist
        missing = [c for c in score_columns if c not in data.columns]
        if missing:
            return {
                "success": False,
                "error": f"Columns not found: {missing}",
                "available_columns": list(data.columns)
            }
        
        # Convert to numeric
        numeric_data = data[score_columns].apply(pd.to_numeric, errors='coerce')
        
        if method == "sum":
            data[result_column] = numeric_data.sum(axis=1)
        elif method == "average":
            data[result_column] = numeric_data.mean(axis=1).round(2)
        elif method == "max":
            data[result_column] = numeric_data.max(axis=1)
        elif method == "min":
            data[result_column] = numeric_data.min(axis=1)
        else:
            data[result_column] = numeric_data.sum(axis=1)
        
        return {
            "success": True,
            "data": data,
            "message": f"Collated {len(score_columns)} columns using {method}",
            "column_added": result_column,
            "columns_used": score_columns,
            "method": method
        }
    
    def calculate_bonus(self, data: pd.DataFrame, params: Dict) -> Dict:
        """
        Calculate participation bonus based on test count.
        Uses the original MLJ bonus system:
        - 1-2 tests: +5%
        - 3-5 tests: +10%
        - 6+ tests: +15%
        """
        score_column = params.get("score_column")
        test_count_column = params.get("test_count_column", "Tests_Taken")
        bonus_column = params.get("bonus_column", "Bonus_Score")
        
        if score_column not in data.columns:
            return {
                "success": False,
                "error": f"Score column '{score_column}' not found",
                "available_columns": list(data.columns)
            }
        
        def apply_bonus(row):
            try:
                score = float(row[score_column])
                test_count = int(row.get(test_count_column, 1))
                
                if test_count >= 6:
                    bonus_rate = 0.15
                elif test_count >= 3:
                    bonus_rate = 0.10
                else:
                    bonus_rate = 0.05
                
                return round(score * (1 + bonus_rate), 2)
            except (ValueError, TypeError):
                return row[score_column]
        
        data[bonus_column] = data.apply(apply_bonus, axis=1)
        
        return {
            "success": True,
            "data": data,
            "message": f"Applied participation bonus (5-15% based on test count)",
            "column_added": bonus_column,
            "bonus_rates": {"1-2 tests": "5%", "3-5 tests": "10%", "6+ tests": "15%"}
        }
    
    # ==================== DATA OPERATIONS ====================
    
    def filter_data(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Filter data based on conditions"""
        column = params.get("column")
        operator = params.get("operator", "equals")  # equals, greater, less, contains
        value = params.get("value")
        
        if column not in data.columns:
            return {
                "success": False,
                "error": f"Column '{column}' not found",
                "available_columns": list(data.columns)
            }
        
        original_count = len(data)
        
        if operator == "equals":
            data = data[data[column] == value]
        elif operator == "greater":
            data = data[pd.to_numeric(data[column], errors='coerce') > float(value)]
        elif operator == "less":
            data = data[pd.to_numeric(data[column], errors='coerce') < float(value)]
        elif operator == "contains":
            data = data[data[column].astype(str).str.contains(str(value), case=False, na=False)]
        elif operator == "not_equals":
            data = data[data[column] != value]
        
        return {
            "success": True,
            "data": data,
            "message": f"Filtered: {column} {operator} {value}",
            "rows_before": original_count,
            "rows_after": len(data),
            "rows_removed": original_count - len(data)
        }
    
    def sort_data(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Sort data by column"""
        column = params.get("column")
        ascending = params.get("ascending", True)
        
        if column not in data.columns:
            return {
                "success": False,
                "error": f"Column '{column}' not found",
                "available_columns": list(data.columns)
            }
        
        data = data.sort_values(by=column, ascending=ascending).reset_index(drop=True)
        
        return {
            "success": True,
            "data": data,
            "message": f"Sorted by '{column}' ({'ascending' if ascending else 'descending'})"
        }
    
    def add_rank(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add ranking based on a score column"""
        score_column = params.get("score_column")
        rank_column = params.get("rank_column", "Rank")
        ascending = params.get("ascending", False)  # False = highest score = rank 1
        
        if score_column not in data.columns:
            return {
                "success": False,
                "error": f"Score column '{score_column}' not found",
                "available_columns": list(data.columns)
            }
        
        data[rank_column] = data[score_column].rank(ascending=ascending, method='min').astype(int)
        
        return {
            "success": True,
            "data": data,
            "message": f"Added rankings based on '{score_column}'",
            "column_added": rank_column
        }
    
    def add_formula_column(self, data: pd.DataFrame, params: Dict) -> Dict:
        """Add a column with a custom formula"""
        column_name = params.get("column_name", "Calculated")
        formula = params.get("formula")  # e.g., "col_a + col_b * 0.5"
        
        try:
            # Create safe evaluation context with column data
            context = {col: data[col] for col in data.columns}
            context['pd'] = pd
            
            data[column_name] = eval(formula, {"__builtins__": {}}, context)
            
            return {
                "success": True,
                "data": data,
                "message": f"Added calculated column '{column_name}'",
                "formula": formula
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Formula error: {e}",
                "formula": formula
            }
    
    # ==================== COMPOSITE OPERATIONS ====================
    
    def execute_workflow(self, data: pd.DataFrame, workflow: List[Dict]) -> Dict:
        """
        Execute multiple actions in sequence.
        
        Args:
            data: Initial DataFrame
            workflow: List of {"action": str, "params": Dict}
            
        Returns:
            Final result with all changes applied
        """
        results = []
        current_data = data.copy()
        
        for step in workflow:
            action = step.get("action")
            params = step.get("params", {})
            
            result = self.execute(action, current_data, params)
            results.append({
                "action": action,
                "success": result["success"],
                "message": result.get("message", result.get("error"))
            })
            
            if result["success"]:
                current_data = result["data"]
            else:
                return {
                    "success": False,
                    "error": f"Workflow failed at step: {action}",
                    "step_results": results,
                    "data": current_data
                }
        
        return {
            "success": True,
            "data": current_data,
            "message": f"Workflow completed: {len(workflow)} actions executed",
            "step_results": results
        }
    
    def get_available_actions(self) -> Dict:
        """Return list of available actions with descriptions"""
        return {
            "add_column": "Add a new column with default value",
            "add_random_scores": "Add random scores (0-100) to participants",
            "add_grades": "Add letter grades (A-F) based on scores",
            "add_pass_fail": "Add PASSED/FAILED status based on threshold",
            "collate_scores": "Sum/average multiple score columns",
            "calculate_bonus": "Apply MLJ participation bonus (5-15%)",
            "filter_data": "Filter rows by condition",
            "sort_data": "Sort by column",
            "remove_column": "Remove a column",
            "rename_column": "Rename a column",
            "add_formula_column": "Add calculated column with formula",
            "add_rank": "Add rankings based on scores"
        }
    
    def get_action_history(self) -> List[Dict]:
        """Return history of executed actions"""
        return self.action_history
    
    # ==================== PREVIEW/DRY-RUN MODES ====================
    
    def preview_action(self, action: str, data: pd.DataFrame, params: Dict) -> Dict:
        """
        Preview action without modifying original data.
        Returns before/after comparison.
        
        Args:
            action: Action name
            data: DataFrame
            params: Action parameters
            
        Returns:
            Dict with before/after samples and statistics
        """
        # Store original state
        original_shape = data.shape
        original_columns = list(data.columns)
        
        # Execute on copy
        result = self.execute(action, data.copy(), params)
        
        if not result.get("success", False):
            return {
                "success": False,
                "action": action,
                "error": result.get("error", "Unknown error"),
                "preview": None
            }
        
        modified_data = result.get("data")
        
        # Analyze changes
        new_columns = list(modified_data.columns)
        added_columns = [c for c in new_columns if c not in original_columns]
        removed_columns = [c for c in original_columns if c not in new_columns]
        
        preview = {
            "action": action,
            "status": "preview_only",
            "changes": {
                "shape_before": original_shape,
                "shape_after": modified_data.shape,
                "columns_before": original_columns,
                "columns_after": new_columns,
                "columns_added": added_columns,
                "columns_removed": removed_columns
            },
            "samples": {
                "before": data.head(3).to_dict('records') if len(data) > 0 else [],
                "after": modified_data.head(3).to_dict('records') if len(modified_data) > 0 else []
            },
            "statistics": {
                "rows": len(modified_data),
                "columns": len(modified_data.columns),
                "memory_before": f"{data.memory_usage(deep=True).sum() / 1024:.2f} KB",
                "memory_after": f"{modified_data.memory_usage(deep=True).sum() / 1024:.2f} KB"
            },
            "description": result.get("message", "Action executed successfully"),
            "confirmed": False
        }
        
        return {
            "success": True,
            "preview": preview,
            "action": action
        }
    
    def preview_workflow(self, data: pd.DataFrame, workflow: List[Dict]) -> Dict:
        """
        Preview entire workflow without executing.
        Shows cumulative changes.
        
        Args:
            data: Initial DataFrame
            workflow: List of action steps
            
        Returns:
            Dict with step-by-step previews
        """
        step_previews = []
        current_data = data.copy()
        
        for idx, step in enumerate(workflow):
            action = step.get("action")
            params = step.get("params", {})
            
            # Preview this step
            preview = self.preview_action(action, current_data, params)
            
            if preview["success"]:
                step_previews.append({
                    "step": idx + 1,
                    "action": action,
                    "preview": preview["preview"]
                })
                # Execute for next iteration
                result = self.execute(action, current_data, params)
                if result["success"]:
                    current_data = result["data"]
                else:
                    break
            else:
                step_previews.append({
                    "step": idx + 1,
                    "action": action,
                    "error": preview.get("error"),
                    "preview": None
                })
                break
        
        return {
            "success": True,
            "workflow_preview": {
                "total_steps": len(workflow),
                "steps": step_previews,
                "final_shape": current_data.shape,
                "confirmed": False
            }
        }
    
    def execute_confirmed(self, data: pd.DataFrame, workflow: List[Dict], 
                         confirmed: bool = False) -> Dict:
        """
        Execute workflow only if confirmed.
        Shows preview first, then executes on confirmation.
        
        Args:
            data: Initial DataFrame
            workflow: List of action steps
            confirmed: Whether user confirmed the preview
            
        Returns:
            Either preview or execution result
        """
        if not confirmed:
            # Show preview first
            return self.preview_workflow(data, workflow)
        
        # User confirmed - execute
        return self.execute_workflow(data, workflow)


# Singleton instance
_data_agent = None

def get_data_agent() -> DataAgent:
    """Get or create data agent instance"""
    global _data_agent
    if _data_agent is None:
        _data_agent = DataAgent()
    return _data_agent
