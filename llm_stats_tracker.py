# llm_stats_tracker.py
# Unified LLM statistics tracking across multiple model types

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from terminal_formatter import TerminalFormatter

@dataclass
class LLMCallStats:
    """Statistics for a single LLM call"""
    model_name: str
    model_type: str  # dialogue, profile, guide_selection, command_interpretation
    total_time: float
    time_to_first_token: Optional[float]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class LLMTypeStats:
    """Aggregated statistics for a specific LLM type"""
    model_type: str
    current_model: Optional[str] = None
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_time: float = 0.0
    last_call_stats: Optional[LLMCallStats] = None
    first_call_time: float = field(default_factory=time.time)

    def add_call_stats(self, stats: LLMCallStats):
        """Add statistics from a new call"""
        if stats.error:
            return  # Don't track error calls in aggregates
            
        self.total_calls += 1
        self.total_input_tokens += stats.input_tokens
        self.total_output_tokens += stats.output_tokens
        self.total_time += stats.total_time
        self.last_call_stats = stats
        self.current_model = stats.model_name

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_call_time(self) -> float:
        return self.total_time / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def avg_throughput(self) -> float:
        return self.total_output_tokens / self.total_time if self.total_time > 0 else 0.0

class LLMStatsTracker:
    """Unified tracker for all LLM model usage"""
    
    def __init__(self):
        self.session_start_time = time.time()
        self.type_stats: Dict[str, LLMTypeStats] = {}
        self.all_calls: List[LLMCallStats] = []
        
    def record_call(self, model_name: str, model_type: str, stats_dict: Dict[str, Any]) -> LLMCallStats:
        """Record statistics from an LLM call"""
        call_stats = LLMCallStats(
            model_name=model_name,
            model_type=model_type,
            total_time=stats_dict.get('total_time', 0.0),
            time_to_first_token=stats_dict.get('time_to_first_token'),
            input_tokens=stats_dict.get('input_tokens', 0),
            output_tokens=stats_dict.get('output_tokens', 0),
            total_tokens=stats_dict.get('total_tokens', stats_dict.get('input_tokens', 0) + stats_dict.get('output_tokens', 0)),
            error=stats_dict.get('error')
        )
        
        self.all_calls.append(call_stats)
        
        # Update type-specific stats
        if model_type not in self.type_stats:
            self.type_stats[model_type] = LLMTypeStats(model_type=model_type)
        
        self.type_stats[model_type].add_call_stats(call_stats)
        return call_stats
    
    def get_last_stats_by_type(self, model_type: str) -> Optional[LLMCallStats]:
        """Get the last call stats for a specific model type"""
        if model_type in self.type_stats:
            return self.type_stats[model_type].last_call_stats
        return None
    
    def get_last_stats(self) -> Optional[LLMCallStats]:
        """Get the most recent call stats regardless of type"""
        return self.all_calls[-1] if self.all_calls else None
    
    def format_last_stats(self, model_type: Optional[str] = None) -> str:
        """Format the last call statistics for display"""
        stats = self.get_last_stats_by_type(model_type) if model_type else self.get_last_stats()
        
        if not stats:
            return f"{TerminalFormatter.DIM}Statistiche non disponibili.{TerminalFormatter.RESET}"
        
        lines = [f"{TerminalFormatter.BOLD}Statistiche Ultima Chiamata ({stats.model_type.title()}):{TerminalFormatter.RESET}"]
        lines.append(f"{TerminalFormatter.DIM}- Modello: {stats.model_name}{TerminalFormatter.RESET}")
        lines.append(f"{TerminalFormatter.DIM}- Tempo Totale: {stats.total_time:.2f}s{TerminalFormatter.RESET}")
        
        if stats.time_to_first_token is not None:
            lines.append(f"{TerminalFormatter.DIM}- Tempo al Primo Token: {stats.time_to_first_token:.2f}s{TerminalFormatter.RESET}")
        
        lines.append(f"{TerminalFormatter.DIM}- Tokens (Input/Output/Total): {stats.input_tokens} / {stats.output_tokens} / {stats.total_tokens}{TerminalFormatter.RESET}")
        
        if stats.total_time > 0 and stats.output_tokens > 0:
            throughput = stats.output_tokens / stats.total_time
            lines.append(f"{TerminalFormatter.DIM}- Throughput Output: {throughput:.2f} tokens/s{TerminalFormatter.RESET}")
        
        if stats.error:
            lines.append(f"{TerminalFormatter.DIM}- Errore: {stats.error}{TerminalFormatter.RESET}")
            
        return "\n".join(lines)
    
    def format_session_stats(self, model_type: Optional[str] = None) -> str:
        """Format session-wide statistics"""
        session_runtime = time.time() - self.session_start_time
        
        if model_type and model_type in self.type_stats:
            # Stats for specific model type
            type_stats = self.type_stats[model_type]
            lines = [f"{TerminalFormatter.BOLD}Statistiche Sessione - {model_type.title()} ({type_stats.current_model or 'N/A'}):{TerminalFormatter.RESET}"]
            lines.append(f"{TerminalFormatter.DIM}- Chiamate {model_type.title()}: {type_stats.total_calls}{TerminalFormatter.RESET}")
            
            if type_stats.total_calls > 0:
                lines.append(f"{TerminalFormatter.DIM}- Tempo Totale in LLM: {type_stats.total_time:.2f}s{TerminalFormatter.RESET}")
                lines.append(f"{TerminalFormatter.DIM}- Tempo Medio per Chiamata: {type_stats.avg_call_time:.2f}s{TerminalFormatter.RESET}")
                lines.append(f"{TerminalFormatter.DIM}- Tokens Totali (In/Out/Sum): {type_stats.total_input_tokens} / {type_stats.total_output_tokens} / {type_stats.total_tokens}{TerminalFormatter.RESET}")
                if type_stats.avg_throughput > 0:
                    lines.append(f"{TerminalFormatter.DIM}- Throughput Medio Output: {type_stats.avg_throughput:.2f} tokens/s{TerminalFormatter.RESET}")
        else:
            # Overall session stats
            lines = [f"{TerminalFormatter.BOLD}Statistiche Sessione Completa:{TerminalFormatter.RESET}"]
            lines.append(f"{TerminalFormatter.DIM}- Durata Sessione: {session_runtime:.2f}s{TerminalFormatter.RESET}")
            
            total_calls = len(self.all_calls)
            lines.append(f"{TerminalFormatter.DIM}- Chiamate LLM Totali: {total_calls}{TerminalFormatter.RESET}")
            
            if self.type_stats:
                lines.append(f"{TerminalFormatter.DIM}Breakdown per Tipo:{TerminalFormatter.RESET}")
                for model_type, stats in self.type_stats.items():
                    emoji = self._get_type_emoji(model_type)
                    model_short = stats.current_model.split('/')[-1] if stats.current_model and '/' in stats.current_model else (stats.current_model or 'N/A')
                    lines.append(f"{TerminalFormatter.DIM}  {emoji} {model_type.title()}: {stats.total_calls} chiamate, {stats.total_tokens} tokens ({model_short}){TerminalFormatter.RESET}")
        
        return "\n".join(lines)
    
    def _get_type_emoji(self, model_type: str) -> str:
        """Get emoji for model type"""
        emoji_map = {
            'dialogue': '🟢',
            'profile': '🟡', 
            'guide_selection': '🔵',
            'command_interpretation': '🟠'
        }
        return emoji_map.get(model_type, '⚪')
    
    def get_status_indicators(self) -> str:
        """Get colored status indicators for each LLM type"""
        indicators = []
        
        for model_type in ['dialogue', 'command_interpretation', 'profile', 'guide_selection']:
            emoji = self._get_type_emoji(model_type)
            if model_type in self.type_stats and self.type_stats[model_type].total_calls > 0:
                status = emoji  # Active
            else:
                status = '🔴'  # Inactive
            indicators.append(f"{status} {model_type.title()}")
        
        return " • ".join(indicators)

# Global instance for the session
_global_stats_tracker: Optional[LLMStatsTracker] = None

def get_global_stats_tracker() -> LLMStatsTracker:
    """Get or create the global stats tracker instance"""
    global _global_stats_tracker
    if _global_stats_tracker is None:
        _global_stats_tracker = LLMStatsTracker()
    return _global_stats_tracker

def reset_global_stats_tracker():
    """Reset the global stats tracker"""
    global _global_stats_tracker
    _global_stats_tracker = LLMStatsTracker()