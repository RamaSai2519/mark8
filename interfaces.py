from dataclasses import dataclass
from typing import Optional


class Constants:
    user = "user"


@dataclass
class TranscriptPrompts:
    init_prompt: str
    analysis_prompt: str
    transcript_prompt: str


@dataclass
class EvaluationPrompts:
    score_prompt: str
    summary_prompt: str
    callback_prompt: str
    feedback_prompt: str
    guidelines_prompt: str
    score_details_prompt: str


@dataclass
class AnalyserOutput:
    topics: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    user_callback: Optional[str] = None
    saarthi_feedback: Optional[str] = None
    customer_persona: Optional[str] = None
    conversation_score: Optional[float] = None
    conversation_score_details: Optional[str] = None
