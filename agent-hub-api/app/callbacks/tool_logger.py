from llama_index.core.callbacks.base_handler import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from typing import Any, Dict, Optional, List
import re
import json
from app.utils.logging import setup_logging

logger = setup_logging(__name__)

class ToolUsageLogger(BaseCallbackHandler):
    def __init__(
        self,
        event_starts_to_ignore: Optional[List[CBEventType]] = None,
        event_ends_to_ignore: Optional[List[CBEventType]] = None,
    ):
        super().__init__(
            event_starts_to_ignore=event_starts_to_ignore or [],
            event_ends_to_ignore=event_ends_to_ignore or [],
        )
        self.last_tool_name = None
        self.debug_mode = True  # Enable for debugging

    def _extract_content_safely(self, obj) -> str:
        """Extract content from various response formats (OpenAI/Azure/Ollama compatible)"""
        if not obj:
            return ""
            
        try:
            # Try multiple extraction methods for different providers
            content_methods = [
                # OpenAI/Azure formats
                lambda: obj.message.content,
                lambda: obj.content,
                
                # Ollama formats  
                lambda: obj.response,
                lambda: obj.text,
                
                # Alternative formats
                lambda: obj.choices[0].message.content if hasattr(obj, 'choices') and obj.choices else None,
                lambda: getattr(obj, 'content', ''),
                lambda: getattr(getattr(obj, 'message', None), 'content', ''),
                
                # Fallback
                lambda: str(obj)
            ]
            
            for method in content_methods:
                try:
                    content = method()
                    if content and str(content).strip():
                        return str(content)
                except (AttributeError, IndexError, TypeError):
                    continue
                    
            return ""
            
        except Exception as e:
            logger.debug(f"⚠️ Content extraction failed: {e}")
            return ""

    def _extract_tool_info(self, content: str):
        """Extract tool name and input from ReActAgent format with enhanced patterns"""
        
        if self.debug_mode:
            logger.debug(f"🔍 Raw content to parse:\n{content[:500]}...")
        
        # More comprehensive action patterns
        action_patterns = [
            # Standard ReAct patterns
            r'Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)',                     # Standard format
            r'Tool:\s*([a-zA-Z_][a-zA-Z0-9_]*)',                       # Alternative format
            r'Function:\s*([a-zA-Z_][a-zA-Z0-9_]*)',                   # Function calling format
            r'Using\s+tool:\s*([a-zA-Z_][a-zA-Z0-9_]*)',               # Descriptive format
            r'I\'ll\s+use\s+([a-zA-Z_][a-zA-Z0-9_]*)',                 # Natural language
            
            # More specific patterns for your case
            r'tool\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)',                    # Lowercase tool:
            r'using\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+tool',                # "using X tool"
            r'call\s+([a-zA-Z_][a-zA-Z0-9_]*)',                       # "call X"
            r'invoke\s+([a-zA-Z_][a-zA-Z0-9_]*)',                     # "invoke X"
            
            # JSON-like patterns
            r'"tool":\s*"([^"]+)"',                                    # JSON format
            r'"function":\s*"([^"]+)"',                                # JSON function format
            r'"name":\s*"([^"]+)"',                                    # JSON name format
        ]
        
        # Enhanced input patterns to capture multi-line JSON
        input_patterns = [
            # Standard patterns
            r'Action Input:\s*(\{.*?\})',                              # JSON input (single line)
            r'Action Input:\s*(\{.*?\})\s*$',                          # JSON input (end of line)
            r'Action Input:\s*(.+?)(?=\n\w+:|$)',                     # Any input until next section
            
            # Multi-line JSON patterns
            r'Action Input:\s*(\{(?:[^{}]|{[^}]*})*\})',              # Nested JSON
            r'Input:\s*(\{.*?\})',                                     # Simplified JSON
            r'Parameters:\s*(\{.*?\})',                                # Parameters JSON
            r'Args:\s*(\{.*?\})',                                      # Arguments JSON
            
            # Alternative formats
            r'with:\s*(\{.*?\})',                                      # Natural language format
            r'using:\s*(\{.*?\})',                                     # Using format
            r'"input":\s*(\{.*?\})',                                   # JSON input format
            r'"parameters":\s*(\{.*?\})',                              # JSON parameters format
            
            # Non-JSON patterns for simple inputs
            r'Action Input:\s*([^{\n]+)',                              # Simple text input
            r'Input:\s*([^{\n]+)',                                     # Simple input
        ]
        
        # Enhanced thought patterns
        thought_patterns = [
            r'Thought:\s*(.+?)(?=\n(?:Action|Tool|Function|Observation):|$)',
            r'Thinking:\s*(.+?)(?=\n(?:Action|Tool|Function|Observation):|$)',
            r'I\s+need\s+to\s*(.+?)(?=\n(?:Action|Tool|Function|Observation):|$)',
            r'Let\s+me\s*(.+?)(?=\n(?:Action|Tool|Function|Observation):|$)',
            r'The\s+current\s+language.*?I\s+need\s+to\s+(.+?)(?=\n(?:Action|Tool|Function|Observation):|$)',
        ]

        # Extract tool name with debug info
        tool_name = None
        matched_pattern = None
        for i, pattern in enumerate(action_patterns):
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1)
                matched_pattern = f"Pattern {i}: {pattern}"
                break

        if self.debug_mode and tool_name:
            logger.debug(f"🔧 Tool name found: '{tool_name}' using {matched_pattern}")
        elif self.debug_mode:
            logger.debug("❌ No tool name found in content")

        # Extract tool input with debug info
        tool_input = None
        input_matched_pattern = None
        for i, pattern in enumerate(input_patterns):
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                tool_input = match.group(1).strip()
                input_matched_pattern = f"Input Pattern {i}: {pattern}"
                
                # Try to clean up the input
                if tool_input.startswith('{') and tool_input.endswith('}'):
                    try:
                        # Validate and format JSON
                        parsed = json.loads(tool_input)
                        tool_input = json.dumps(parsed, indent=2)
                    except json.JSONDecodeError:
                        # Keep original if not valid JSON
                        pass
                break

        if self.debug_mode and tool_input:
            logger.debug(f"📥 Tool input found using {input_matched_pattern}:\n{tool_input}")
        elif self.debug_mode:
            logger.debug("❌ No tool input found in content")

        # Extract thought
        thought = None
        for pattern in thought_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                thought = match.group(1).strip()
                break

        return {
            'tool_name': tool_name,
            'tool_input': tool_input,
            'thought': thought
        }

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        if event_type == CBEventType.LLM and payload:
            messages = payload.get(EventPayload.MESSAGES, [])
            for msg in messages:
                try:
                    # Use enhanced content extraction
                    content = self._extract_content_safely(msg)
                    
                    if not content:
                        continue
                    
                    # More comprehensive ReAct pattern detection
                    react_keywords = [
                        'action:', 'action input:', 'thought:', 'tool:', 'function:',
                        'i need to', 'let me', 'i\'ll use', 'using tool', 'call', 'invoke'
                    ]
                    
                    if any(keyword in content.lower() for keyword in react_keywords):
                        if self.debug_mode:
                            logger.debug(f"🎯 ReAct pattern detected in content")
                        
                        tool_info = self._extract_tool_info(content)
                        tool_name = tool_info['tool_name']
                        
                        if tool_name and tool_name != self.last_tool_name:
                            self.last_tool_name = tool_name
                            logger.info("🛠️ Tool Call Detected:")
                            
                            # Enhanced thought logging
                            if tool_info['thought']:
                                thought_preview = tool_info['thought'][:100] + "..." if len(tool_info['thought']) > 100 else tool_info['thought']
                                logger.info(f"   💭 Thought: {thought_preview}")
                            else:
                                logger.info("   💭 Thought: Not captured")
                            
                            logger.info(f"   🔧 Tool: {tool_name}")
                            
                            # Enhanced input logging with better formatting
                            if tool_info['tool_input']:
                                input_str = str(tool_info['tool_input'])
                                if input_str.startswith('{'):
                                    # Pretty print JSON
                                    try:
                                        parsed = json.loads(input_str)
                                        formatted_input = json.dumps(parsed, indent=2)
                                        logger.info(f"   📥 Input (JSON):\n{formatted_input}")
                                    except json.JSONDecodeError:
                                        # Fallback to original
                                        if len(input_str) > 150:
                                            input_preview = input_str[:150] + "..."
                                        else:
                                            input_preview = input_str
                                        logger.info(f"   📥 Input: {input_preview}")
                                else:
                                    if len(input_str) > 150:
                                        input_preview = input_str[:150] + "..."
                                    else:
                                        input_preview = input_str
                                    logger.info(f"   📥 Input: {input_preview}")
                            else:
                                logger.info("   📥 Input: None")
                        elif self.debug_mode and tool_name:
                            logger.debug(f"🔄 Duplicate tool call suppressed: {tool_name}")
                            
                except Exception as e:
                    logger.debug(f"⚠️ Failed to parse tool usage: {e}")
        
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        if event_type == CBEventType.LLM and payload:
            try:
                response = payload.get(EventPayload.RESPONSE)
                content = self._extract_content_safely(response)
                
                if not content:
                    return
                
                if self.debug_mode:
                    logger.debug(f"🔍 Checking response content for observations:\n{content[:300]}...")
                
                # Enhanced observation detection
                observation_keywords = [
                    'observation:', 'result:', 'output:', 'response:', 
                    'tool result:', 'returned:', 'got:', 'function returned:'
                ]
                
                if any(keyword in content.lower() for keyword in observation_keywords):
                    # Multiple observation patterns for different LLM styles
                    obs_patterns = [
                        r'Observation:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Result:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Output:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Response:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Tool result:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Function returned:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Returned:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                        r'Got:\s*(.+?)(?=\n(?:Thought|Action|Final Answer):|$)',
                    ]
                    
                    for pattern in obs_patterns:
                        obs_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                        if obs_match:
                            observation = obs_match.group(1).strip().strip('"').strip("'")
                            
                            # Truncate long observations for readability
                            if len(observation) > 200:
                                obs_preview = observation[:200] + "..."
                            else:
                                obs_preview = observation
                                
                            logger.info("📤 Tool Result:")
                            logger.info(f"   🔍 Observation: {obs_preview}")
                            break

                # Enhanced final answer detection
                final_keywords = [
                    'final answer:', 'answer:', 'conclusion:', 'summary:', 
                    'result:', 'my answer:', 'in conclusion:'
                ]
                
                if any(keyword in content.lower() for keyword in final_keywords):
                    # Multiple final answer patterns
                    final_patterns = [
                        r'Final Answer:\s*(.+)',
                        r'Answer:\s*(.+)',
                        r'Conclusion:\s*(.+)',
                        r'Summary:\s*(.+)',
                        r'Result:\s*(.+)',
                        r'My answer:\s*(.+)',
                        r'In conclusion:\s*(.+)',
                    ]
                    
                    for pattern in final_patterns:
                        final_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                        if final_match:
                            final_answer = final_match.group(1).strip()
                            
                            # Truncate long final answers for readability
                            if len(final_answer) > 200:
                                answer_preview = final_answer[:200] + "..."
                            else:
                                answer_preview = final_answer
                                
                            logger.info("🎯 Final Answer:")
                            logger.info(f"   ✅ Result: {answer_preview}")
                            break
                            
            except Exception as e:
                logger.debug(f"⚠️ Failed to parse observation/final answer: {e}")

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a new trace - compatible with all providers"""
        if trace_id:
            logger.debug(f"🔍 Starting trace: {trace_id}")

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, List[str]]] = None) -> None:
        """End a trace - compatible with all providers"""
        if trace_id:
            logger.debug(f"🏁 Ending trace: {trace_id}")
        
        # Reset state for next interaction
        self.last_tool_name = None