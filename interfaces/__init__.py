from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class Constants:
    user = "user"
    persona_dict = {
        "demographics": {
            "gender": "",
            "ethnicity": "",
            "education": "",
            "maritalStatus": "",
            "income": "",
            "livingStatus": "",
            "medicalHistory": "",
            "location": "",
            "techComfort": "",
            "standardOfLiving": "",
            "familyMembers": "",
            "workStatus": "",
            "lastCompany": "",
            "languagePreference": "",
            "physicalState": ""
        },
        "psychographics": {
            "needs": "",
            "values": "",
            "painPoints": "",
            "motivators": ""
        },
        "personality": ""
    }


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
    topics: Optional[dict] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    user_callback: Optional[str] = None
    expert_persona: Optional[dict] = None
    saarthi_feedback: Optional[str] = None
    customer_persona: Optional[dict] = None
    conversation_score: Optional[float] = None
    conversation_score_details: Optional[dict] = None


@dataclass
class Call:
    type: Optional[str] = None
    callId: Optional[str] = None
    status: Optional[str] = None
    _id: Optional[ObjectId] = None
    duration: Optional[str] = None
    user: Optional[ObjectId] = None
    expert: Optional[ObjectId] = None
    scheduledId: Optional[str] = None
    failedReason: Optional[str] = None
    recording_url: Optional[str] = None
    user_requested: Optional[bool] = None
    transferDuration: Optional[str] = None
    conversationScore: Optional[int] = None
    initiatedTime: Optional[datetime] = None


@dataclass
class User:
    phoneNumber: str = None
    createdDate: datetime = field(default_factory=datetime.now)

    name: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    refCode: Optional[str] = None
    active: Optional[bool] = None
    isBusy: Optional[bool] = None
    _id: Optional[ObjectId] = None
    refSource: Optional[str] = None
    isBlocked: Optional[bool] = None
    isPaidUser: Optional[bool] = None
    wa_opt_out: Optional[bool] = None
    numberOfGames: Optional[int] = None
    numberOfCalls: Optional[int] = None
    birthDate: Optional[datetime] = None
    customerPersona: Optional[dict] = None
    profileCompleted: Optional[bool] = None


@dataclass
class Expert:
    phoneNumber: str
    _id: Optional[str] = None
    otp: Optional[str] = None
    name: Optional[str] = None
    flow: Optional[int] = None
    type: Optional[str] = None
    video: Optional[str] = None
    score: Optional[int] = None
    score: Optional[int] = None
    topics: Optional[str] = None
    status: Optional[str] = None
    persona: Optional[str] = None
    active: Optional[bool] = None
    profile: Optional[str] = None
    isBusy: Optional[bool] = None
    tonality: Optional[int] = None
    fcmToken: Optional[str] = None
    timeSpent: Optional[int] = None
    languages: Optional[str] = None
    timeSplit: Optional[int] = None
    isDeleted: Optional[bool] = None
    probability: Optional[int] = None
    description: Optional[str] = None
    total_score: Optional[int] = None
    displayScore: Optional[str] = None
    repeat_score: Optional[int] = None
    isGamesPlay: Optional[bool] = None
    daysLoggedIn: Optional[int] = None
    calls_share: Optional[float] = None
    userSentiment: Optional[int] = None
    closingGreeting: Optional[int] = None
    openingGreeting: Optional[int] = None
    expiresOtp: Optional[datetime] = None
    createdDate: Optional[datetime] = None
    categories: Optional[List[str]] = None
    profileCompleted: Optional[bool] = None
