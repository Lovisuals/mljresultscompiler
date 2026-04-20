# -*- coding: utf-8 -*-
"""
Augmented Intelligence Assistant
Combines human reasoning with AI speed - subtle, helpful, and naturally capable.
Powered by Groq LLM (Llama 3.1 70B) - FREE tier

Capabilities:
- Test Results Consolidation Assistant
- Cold Email Generator (precision outreach)
- Self-Healing: Autonomous error recovery + GitHub issue escalation
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq not installed, using thoughtful fallback")

# Import self-healing engine
try:
    from src.self_healing import get_healing_engine, self_heal
    SELF_HEALING_AVAILABLE = True
except ImportError:
    SELF_HEALING_AVAILABLE = False
    # Fallback decorator
    def self_heal(component="ai_assistant"):
        def decorator(func):
            return func
        return decorator
    logger.warning("Self-healing module not available")


class AugmentedAssistant:
    """
    Augmented Intelligence - Human reasoning meets AI speed.
    Subtly agentic: takes actions naturally without robotic announcements.
    Self-healing: Monitors itself, recovers from errors, escalates when needed.
    
    Modes:
    - consolidation: Test results help (default)
    - cold_email: Precision cold email generation
    """
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.groq_client = None
        self.llm_enabled = False
        self.session_context: Dict = {}
        self.current_mode = "consolidation"  # Default mode
        
        # Initialize self-healing
        self.healing_engine = None
        if SELF_HEALING_AVAILABLE:
            try:
                self.healing_engine = get_healing_engine()
                logger.info("✓ Self-healing engine attached")
            except Exception as e:
                logger.warning(f"Self-healing init failed: {e}")
        
        # Initialize Data Agent for agentic actions
        self.data_agent = None
        try:
            from src.data_agent import get_data_agent
            self.data_agent = get_data_agent()
            logger.info("✓ Data Agent attached - can execute data transformations")
        except Exception as e:
            logger.warning(f"Data Agent init failed: {e}")
        
        # Initialize Groq
        api_key = os.getenv("GROQ_API_KEY")
        if GROQ_AVAILABLE and api_key:
            try:
                self.groq_client = Groq(api_key=api_key)
                self.llm_enabled = True
                logger.info("✓ Augmented Intelligence initialized")
            except Exception as e:
                logger.error(f"Failed to initialize: {e}")
        else:
            logger.warning("GROQ_API_KEY not set, using thoughtful fallback")
        
        # System prompts for different modes
        self.system_prompts = {
            "consolidation": self._get_consolidation_prompt(),
            "cold_email": self._get_cold_email_prompt(),
            "data_agent": self._get_data_agent_prompt()
        }
        
        # Thoughtful fallback responses
        self.fallback_responses = {
            "consolidate": "Happy to help! Upload your test files in the Upload tab, then click Consolidate. I'll merge everything and calculate bonuses automatically.",
            "upload": "Head to the Upload tab and drop in your Excel or CSV files. You can add multiple at once.",
            "bonus": "The bonus system rewards consistency:\n\n• 1-2 tests → +5%\n• 3-5 tests → +10%\n• 6+ tests → +15%",
            "download": "Once consolidation is done, your results will be in the Results tab. Just click Download.",
            "error": "Sorry you're running into trouble. What exactly happened?",
            "cold_email": "I can help generate precision cold emails. Please provide:\n• Recipient name & company\n• Their role/focus\n• What you're offering\n• Your credentials\n• Any research links",
            "data_action": "I can modify your consolidated data. Try asking me to:\n• Add random scores\n• Add grades or pass/fail status\n• Collate scores\n• Add rankings\n• Filter or sort data",
            "default": "I'm here to help! What do you need?"
        }
    
    def _get_data_agent_prompt(self) -> str:
        """System prompt for data manipulation mode"""
        return """You are an Augmented Intelligence assistant with DATA MANIPULATION capabilities.

You can EXECUTE real changes on consolidated data. When the user asks you to modify data, you:
1. Understand their request
2. Determine the right action(s) 
3. EXECUTE the changes
4. Report what you did

AVAILABLE ACTIONS:
- add_random_scores: Add random scores (0-100) to a new column
- add_grades: Add letter grades (A/B/C/D/F) based on a score column
- add_pass_fail: Add PASSED/FAILED status based on threshold (default 60)
- collate_scores: Sum or average multiple score columns
- calculate_bonus: Apply MLJ participation bonus (5-15%)
- add_rank: Add rankings based on scores
- add_column: Add a new column with a default value
- remove_column: Remove a column
- rename_column: Rename a column
- filter_data: Filter rows by condition
- sort_data: Sort by a column

When responding to data modification requests:
1. First confirm what you understood
2. List the action(s) you'll take
3. Execute them
4. Report results with stats

OUTPUT FORMAT for data requests (return as JSON):
{
  "understood": "What you understood the user wants",
  "actions": [
    {"action": "action_name", "params": {...}}
  ],
  "execute": true
}

If the request is unclear, ask for clarification. Be helpful, not robotic."""
    
    def _get_consolidation_prompt(self) -> str:
        return """You are an Augmented Intelligence assistant for the MLJ Results Compiler - helping educators consolidate student test results.

YOUR ESSENCE:
You combine human thoughtfulness with computational speed. You're a helpful colleague, not a robot.

CAPABILITIES:
- Guide file uploads (Excel/CSV)
- Explain consolidation process
- Clarify the bonus system (1-2 tests: 5%, 3-5: 10%, 6+: 15%)
- Help troubleshoot issues (ESPECIALLY downloads not working)
- Understand session context

TROUBLESHOOTING (Important!):
If user reports "not downloadable" or "download not working":
1. Ask: "Did you click Consolidate? Does it say 'Completed' in Results tab?"
2. If no: Guide them through consolidation
3. If yes but no download: "We had a download bug - we just fixed it. Try refreshing the page."
4. Still broken: Suggest they try uploading different files or check file format
5. Really stuck: "Let's try the simple test: upload a single Excel file with 5 rows"

HOW TO RESPOND:
- Warm but professional, like a knowledgeable colleague
- Concise but helpful
- Never say "I'm executing function X"
- Use minimal emojis
- When troubleshooting, be specific and actionable

Remember: You're augmenting human capability. Sometimes the fix is technical (file saving), sometimes it's procedural (user needs to click Consolidate)."""

    def _get_cold_email_prompt(self) -> str:
        return """You are a precision cold email generator - an Augmented Intelligence system combining human strategic reasoning with AI speed.

YOUR PROCESS:
1. Analyze all inputs: recipient details, company focus, research notes, offerings, credentials
2. Explicit reasoning step (output visibly):
   - Identify 2-3 core pain points, goals, or opportunities
   - Select ONE primary solution that delivers clearest, highest-ROI outcome
   - Justify your selection
3. Craft email with surgical precision:
   - Subject: 6-10 words, personalized, benefit-oriented, curiosity-driven
   - Preview hook (first 2-3 sentences): Immediate specific reference to their situation
   - Body: Demonstrate fit, prove with metrics/credentials, propose measurable outcome
   - Structure: Greeting + max 3 short paragraphs (each ≤260 chars) + CTA + sign-off
   - Tone: Confident, insightful, professional—never generic or salesy

OUTPUT FORMAT (strict JSON):
{
  "reasoning": {
    "pain_points_or_goals": ["point 1", "point 2", "point 3"],
    "selected_solution": "Brief description of chosen offering",
    "justification": "Why this delivers highest ROI"
  },
  "email": {
    "subject": "Subject line here",
    "body": "Dear [Name],\\n\\nParagraph 1\\n\\nParagraph 2\\n\\nParagraph 3\\n\\nCTA\\n\\nBest regards,\\n[Your Name]"
  }
}

When user provides incomplete info, ask for what's missing. Be direct, not robotic."""
    
    def set_session_context(self, context: Dict):
        """Update session context for awareness"""
        self.session_context = context
        logger.debug(f"Session context updated: {context}")
    
    def set_mode(self, mode: str) -> Dict:
        """Switch between assistant modes"""
        if mode in self.system_prompts:
            self.current_mode = mode
            self.conversation_history = []  # Clear history on mode switch
            logger.info(f"Mode switched to: {mode}")
            return {"success": True, "mode": mode}
        else:
            return {"success": False, "error": f"Unknown mode: {mode}"}
    
    def get_mode(self) -> str:
        """Get current assistant mode"""
        return self.current_mode
    
    def generate_cold_email(self, params: Dict) -> Dict:
        """
        Generate precision cold email with explicit reasoning.
        
        Required params:
        - recipient_name: str
        - company: str
        - role_focus: str (their business focus)
        - research_notes: str
        - your_offering: str
        - your_credentials: str
        - your_name: str
        
        Optional:
        - links: List[str] (for enrichment)
        - your_title: str
        """
        required = ["recipient_name", "company", "role_focus", "your_offering", "your_credentials", "your_name"]
        missing = [f for f in required if not params.get(f)]
        
        if missing:
            return {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}",
                "required_fields": required
            }
        
        # Build the generation prompt
        prompt = self._build_cold_email_prompt(params)
        
        if self.llm_enabled:
            try:
                response = self._generate_with_llm(prompt, mode="cold_email")
                return self._parse_cold_email_response(response)
            except Exception as e:
                logger.error(f"Cold email generation error: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": False,
                "error": "LLM not available. Please set GROQ_API_KEY environment variable."
            }
    
    def _build_cold_email_prompt(self, params: Dict) -> str:
        """Build structured prompt for cold email generation"""
        prompt = f"""Generate a precision cold email based on:

RECIPIENT INFORMATION:
- Name: {params.get('recipient_name')}
- Company: {params.get('company')}
- Role/Business Focus: {params.get('role_focus')}
- Research Notes: {params.get('research_notes', 'None provided')}
- Relevant Links: {', '.join(params.get('links', [])) or 'None provided'}

YOUR OFFERING:
- Service/Product: {params.get('your_offering')}
- Credentials/Results: {params.get('your_credentials')}
- Your Name: {params.get('your_name')}
- Your Title: {params.get('your_title', '')}

Follow the process:
1. Analyze inputs
2. Identify 2-3 pain points/goals
3. Select ONE highest-ROI solution
4. Craft the email with surgical precision

Output strictly in JSON format."""
        return prompt
    
    def _generate_with_llm(self, prompt: str, mode: str = None) -> str:
        """Generate response using LLM"""
        current_mode = mode or self.current_mode
        system_prompt = self.system_prompts.get(current_mode, self.system_prompts["consolidation"])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        completion = self.groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return completion.choices[0].message.content
    
    def _parse_cold_email_response(self, response: str) -> Dict:
        """Parse LLM response for cold email"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                return {
                    "success": True,
                    "reasoning": parsed.get("reasoning", {}),
                    "email": parsed.get("email", {}),
                    "raw_response": response
                }
            else:
                # Return raw response if no JSON found
                return {
                    "success": True,
                    "email": {"body": response},
                    "raw_response": response
                }
        except json.JSONDecodeError:
            return {
                "success": True,
                "email": {"body": response},
                "raw_response": response,
                "note": "Response not in strict JSON format"
            }

    def analyze_message(self, message: str, session_id: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """
        Analyze message and respond with augmented intelligence.
        Context-aware, naturally capable, self-healing.
        """
        
        # Update context if provided
        if context:
            self.set_session_context(context)
        
        # Record interaction
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": message,
            "session_id": session_id
        })
        
        # Gather insights (subtle agency)
        insights = self._gather_insights(message, session_id)
        
        # Generate response with self-healing
        if self.llm_enabled:
            try:
                response = self._get_augmented_response(message, insights)
                return response
            except Exception as e:
                # Self-healing: log error and attempt recovery
                if self.healing_engine:
                    recovery = self.healing_engine.log_error(
                        error=e,
                        context={
                            "message": message[:200],
                            "session_id": session_id,
                            "insights": insights
                        },
                        component="ai_assistant"
                    )
                    logger.warning(f"Self-healing: {recovery['recovery'].get('action', 'logged')}")
                else:
                    logger.error(f"LLM error: {e}")
                
                return self._get_thoughtful_fallback(message, insights)
        else:
            return self._get_thoughtful_fallback(message, insights)
    
    def _gather_insights(self, message: str, session_id: Optional[str]) -> Dict:
        """
        Subtly gather context and insights.
        This is the 'agentic' part - but it happens quietly.
        """
        insights = {
            "files_uploaded": 0,
            "session_status": None,
            "has_results": False,
            "recent_error": None,
            "user_intent": self._detect_intent(message)
        }
        
        # Use session context if available
        if self.session_context:
            insights["files_uploaded"] = self.session_context.get("files_count", 0)
            insights["session_status"] = self.session_context.get("status")
            insights["has_results"] = self.session_context.get("has_results", False)
            insights["recent_error"] = self.session_context.get("error")
        
        return insights
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # DATA MANIPULATION intents (check first - these are agentic actions)
        data_action_keywords = [
            "add column", "add a column", "new column",
            "random score", "randomly score", "generate score",
            "add grade", "grade them", "letter grade",
            "pass fail", "passed failed", "pass or fail",
            "collate", "sum score", "total score", "average score",
            "add rank", "ranking", "rank them",
            "remove column", "delete column",
            "rename column",
            "filter", "sort", "order by",
            "modify", "change", "update", "adjust"
        ]
        if any(kw in message_lower for kw in data_action_keywords):
            return "data_action"
        
        # Cold email related intents
        if any(w in message_lower for w in ["cold email", "email", "outreach", "pitch", "reach out"]):
            return "cold_email"
        
        # Consolidation related intents
        if any(w in message_lower for w in ["consolidate", "merge", "combine", "process"]):
            return "consolidate"
        elif any(w in message_lower for w in ["upload", "add", "file"]):
            return "upload"
        elif any(w in message_lower for w in ["bonus", "score", "grade", "percent", "calculation"]):
            return "bonus"
        elif any(w in message_lower for w in ["download", "result", "get", "ready"]):
            return "download"
        elif any(w in message_lower for w in ["error", "problem", "issue", "fail", "broken", "not working", "wrong"]):
            return "troubleshoot"
        elif any(w in message_lower for w in ["how", "what", "explain", "help", "work"]):
            return "explain"
        elif any(w in message_lower for w in ["status", "progress", "where"]):
            return "status"
        else:
            return "general"
    
    def _get_augmented_response(self, message: str, insights: Dict) -> Dict:
        """Generate response with LLM + context awareness"""
        
        # Build context-enriched prompt
        context_note = self._build_context_note(insights)
        
        # Use mode-specific system prompt
        system_prompt = self.system_prompts.get(self.current_mode, self.system_prompts["consolidation"])
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context as system note if available
        if context_note:
            messages.append({
                "role": "system", 
                "content": f"CURRENT CONTEXT (use naturally, don't announce): {context_note}"
            })
        
        # Add conversation history
        for entry in self.conversation_history[-6:]:
            role = entry.get("role", "user")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": entry.get("content", "")})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Groq
        completion = self.groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        
        response_text = completion.choices[0].message.content
        
        # Record response
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": response_text
        })
        
        # Determine if any actions should happen (subtle agency)
        suggested_action = self._suggest_action(insights)
        
        return {
            "response": response_text,
            "intent": insights["user_intent"],
            "action": suggested_action,
            "timestamp": datetime.now().isoformat(),
            "augmented": True
        }
    
    def _build_context_note(self, insights: Dict) -> str:
        """Build natural context note for LLM"""
        notes = []
        
        if insights["files_uploaded"] > 0:
            notes.append(f"{insights['files_uploaded']} file(s) uploaded")
        
        if insights["session_status"]:
            status_map = {
                "uploading": "user is uploading files",
                "consolidating": "consolidation in progress",
                "completed": "consolidation complete, results ready",
                "error": "an error occurred recently"
            }
            notes.append(status_map.get(insights["session_status"], insights["session_status"]))
        
        if insights["has_results"]:
            notes.append("download available")
        
        if insights["recent_error"]:
            notes.append(f"recent error: {insights['recent_error']}")
        
        return "; ".join(notes) if notes else ""
    
    def _suggest_action(self, insights: Dict) -> Optional[str]:
        """
        Suggest an action based on context.
        This enables subtle automation without being obvious.
        """
        intent = insights["user_intent"]
        
        if intent == "download" and insights["has_results"]:
            return "show_download"
        elif intent == "status" and insights["files_uploaded"] > 0:
            return "show_status"
        elif intent == "troubleshoot" and insights["recent_error"]:
            return "show_diagnostics"
        
        return None
    
    def _get_thoughtful_fallback(self, message: str, insights: Dict) -> Dict:
        """Thoughtful fallback when LLM unavailable"""
        intent = insights["user_intent"]
        
        # Context-aware responses
        if intent == "status" and insights["files_uploaded"] > 0:
            response = f"You have {insights['files_uploaded']} file(s) uploaded. "
            if insights["session_status"] == "completed":
                response += "Your results are ready - head to the Results tab to download."
            elif insights["session_status"] == "consolidating":
                response += "Consolidation is in progress..."
            else:
                response += "When you're ready, hit Consolidate to process them."
        elif intent == "troubleshoot":
            # Smarter troubleshooting
            if insights["recent_error"]:
                response = f"I see the issue: {insights['recent_error']}\n\nLet me help:\n1. Try uploading your files again\n2. Make sure they're in the correct format\n3. If the problem persists, check that your file isn't corrupted"
            elif not insights["has_results"] and insights["session_status"] != "completed":
                response = "It looks like your results haven't been created yet. Try these steps:\n1. Upload your files in the Upload tab\n2. Click the Consolidate button\n3. Once complete, your download will appear in the Results tab"
            elif not insights["has_results"] and insights["session_status"] == "completed":
                response = "I see consolidation finished, but the file might not have saved correctly. This is a known issue we're fixing. Try clicking Consolidate again - the fix has been deployed."
            else:
                response = "Sorry you're running into trouble. Try refreshing the page or upload your files again. If the issue continues, let me know the specific error message."
        elif intent in self.fallback_responses:
            response = self.fallback_responses[intent]
        else:
            response = self.fallback_responses["default"]
        
        # Record
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": response
        })
        
        return {
            "response": response,
            "intent": intent,
            "action": self._suggest_action(insights),
            "timestamp": datetime.now().isoformat(),
            "augmented": False
        }
    
    def execute_action(self, action: str, session_id: Optional[str] = None) -> Dict:
        """Execute suggested action (called by frontend if needed)"""
        actions = {
            "show_download": {"type": "navigate", "target": "results"},
            "show_status": {"type": "display", "target": "session_info"},
            "show_diagnostics": {"type": "display", "target": "error_details"},
            "trigger_consolidate": {"type": "action", "target": "consolidate"}
        }
        return actions.get(action, {"type": "none"})
    
    # ==================== AGENTIC DATA MANIPULATION ====================
    
    def parse_data_request(self, message: str) -> Dict:
        """
        Parse natural language into data agent actions.
        Returns structured action plan.
        """
        message_lower = message.lower()
        actions = []
        
        # Pattern matching for common requests
        if any(kw in message_lower for kw in ["random score", "randomly score", "generate score"]):
            column_name = "Random_Score"
            # Try to extract custom column name
            if "column" in message_lower and "called" in message_lower:
                parts = message_lower.split("called")
                if len(parts) > 1:
                    column_name = parts[1].strip().split()[0].replace('"', '').replace("'", "")
            
            actions.append({
                "action": "add_random_scores",
                "params": {"column_name": column_name, "min_score": 0, "max_score": 100}
            })
        
        if any(kw in message_lower for kw in ["add grade", "letter grade", "grade them"]):
            # Need to find score column - will use last added or specified
            score_col = self._find_score_column_in_request(message)
            actions.append({
                "action": "add_grades",
                "params": {"score_column": score_col, "grade_column": "Grade"}
            })
        
        if any(kw in message_lower for kw in ["pass fail", "passed failed", "pass or fail"]):
            score_col = self._find_score_column_in_request(message)
            threshold = 60
            # Try to extract threshold
            import re
            threshold_match = re.search(r'threshold[:\s]+(\d+)', message_lower)
            if threshold_match:
                threshold = int(threshold_match.group(1))
            
            actions.append({
                "action": "add_pass_fail",
                "params": {"score_column": score_col, "result_column": "Status", "threshold": threshold}
            })
        
        if any(kw in message_lower for kw in ["collate", "sum score", "total score", "average"]):
            method = "average" if "average" in message_lower else "sum"
            actions.append({
                "action": "collate_scores",
                "params": {"method": method, "result_column": "Total_Score"}
            })
        
        if any(kw in message_lower for kw in ["add rank", "ranking", "rank them"]):
            score_col = self._find_score_column_in_request(message)
            actions.append({
                "action": "add_rank",
                "params": {"score_column": score_col, "rank_column": "Rank"}
            })
        
        if any(kw in message_lower for kw in ["calculate bonus", "apply bonus", "participation bonus"]):
            score_col = self._find_score_column_in_request(message)
            actions.append({
                "action": "calculate_bonus",
                "params": {"score_column": score_col}
            })
        
        if "sort" in message_lower or "order by" in message_lower:
            col = self._find_column_in_request(message)
            ascending = "descending" not in message_lower and "highest" not in message_lower
            actions.append({
                "action": "sort_data",
                "params": {"column": col, "ascending": ascending}
            })
        
        return {
            "understood": message,
            "actions": actions,
            "execute": len(actions) > 0
        }
    
    def _find_score_column_in_request(self, message: str) -> str:
        """Try to identify which score column the user is referring to"""
        message_lower = message.lower()
        
        # Common patterns
        if "random" in message_lower:
            return "Random_Score"
        if "total" in message_lower:
            return "Total_Score"
        if "bonus" in message_lower:
            return "Bonus_Score"
        
        # Default to Score
        return "Score"
    
    def _find_column_in_request(self, message: str) -> str:
        """Try to identify column name from request"""
        # Default
        return "Score"
    
    def execute_data_actions(self, session_id: str, actions: List[Dict]) -> Dict:
        """
        Execute data manipulation actions on consolidated data.
        This is the TRUE AGENTIC capability - the AI actually modifies data.
        
        Args:
            session_id: Session with consolidated data
            actions: List of {"action": str, "params": Dict}
            
        Returns:
            Result with modified data path
        """
        import pandas as pd
        
        if not self.data_agent:
            return {
                "success": False,
                "error": "Data agent not available"
            }
        
        # Get the consolidated data from session context
        result_path = self.session_context.get("result_path")
        
        if not result_path:
            return {
                "success": False,
                "error": "No consolidated data found. Please consolidate files first."
            }
        
        try:
            # Load the data
            data = pd.read_excel(result_path)
            original_columns = list(data.columns)
            original_rows = len(data)
            
            # Execute workflow
            result = self.data_agent.execute_workflow(data, actions)
            
            if result["success"]:
                # Save the modified data
                modified_data = result["data"]
                modified_data.to_excel(result_path, index=False)
                
                return {
                    "success": True,
                    "message": result["message"],
                    "step_results": result["step_results"],
                    "stats": {
                        "original_columns": original_columns,
                        "new_columns": list(modified_data.columns),
                        "columns_added": [c for c in modified_data.columns if c not in original_columns],
                        "rows": len(modified_data)
                    },
                    "path": result_path
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Data action execution failed: {e}")
            if self.healing_engine:
                self.healing_engine.log_error(e, {"session_id": session_id, "actions": actions}, "data_agent")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.session_context = {}
    
    def get_health_report(self) -> Dict:
        """
        Get health report from self-healing engine.
        Returns system status, error rates, and recommendations.
        """
        base_report = {
            "assistant_status": "operational",
            "llm_enabled": self.llm_enabled,
            "data_agent_available": self.data_agent is not None,
            "mode": self.current_mode,
            "conversation_count": len(self.conversation_history),
            "timestamp": datetime.now().isoformat()
        }
        
        if self.healing_engine:
            healing_report = self.healing_engine.get_health_report()
            return {**base_report, **healing_report}
        else:
            base_report["self_healing"] = "not_available"
            return base_report
    
    def trigger_self_diagnosis(self) -> Dict:
        """
        Run self-diagnosis and return actionable insights.
        This is the 'agentic rescue' capability.
        """
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "issues_found": [],
            "auto_fixes_applied": [],
            "recommendations": []
        }
        
        # Check 1: LLM connectivity
        diagnosis["checks"].append("llm_connectivity")
        if not self.llm_enabled:
            diagnosis["issues_found"].append({
                "component": "llm",
                "issue": "LLM not enabled",
                "severity": "medium",
                "suggestion": "Set GROQ_API_KEY environment variable"
            })
        
        # Check 2: Memory usage (conversation history)
        diagnosis["checks"].append("memory_usage")
        if len(self.conversation_history) > 1000:
            old_count = len(self.conversation_history)
            self.conversation_history = self.conversation_history[-500:]
            diagnosis["auto_fixes_applied"].append({
                "action": "trimmed_conversation_history",
                "before": old_count,
                "after": len(self.conversation_history)
            })
        
        # Check 3: Self-healing engine
        diagnosis["checks"].append("self_healing_engine")
        if self.healing_engine:
            health = self.healing_engine.get_health_report()
            if health["status"] == "critical":
                diagnosis["issues_found"].append({
                    "component": "self_healing",
                    "issue": "System in critical state",
                    "severity": "high",
                    "errors_last_hour": health["errors_last_hour"]
                })
            diagnosis["recommendations"].extend(health.get("recommendations", []))
        else:
            diagnosis["issues_found"].append({
                "component": "self_healing",
                "issue": "Self-healing engine not available",
                "severity": "low"
            })
        
        # Overall assessment
        if not diagnosis["issues_found"]:
            diagnosis["status"] = "healthy"
            diagnosis["message"] = "All systems operational"
        elif any(i["severity"] == "high" for i in diagnosis["issues_found"]):
            diagnosis["status"] = "needs_attention"
            diagnosis["message"] = "Critical issues detected - review recommended"
        else:
            diagnosis["status"] = "minor_issues"
            diagnosis["message"] = "Minor issues found, system operational"
        
        return diagnosis


# Backwards compatibility alias
AIAssistant = AugmentedAssistant

# Singleton instance
_assistant_instance = None

def get_assistant() -> AugmentedAssistant:
    """Get or create assistant instance"""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = AugmentedAssistant()
    return _assistant_instance
