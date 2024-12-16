from dataclasses import dataclass
from pydantic import BaseModel
from typing import Optional


class ScoreDetails(BaseModel):
    flow: int
    timeSplit: int
    timeSpent: int
    probability: int
    explanation: str
    userSentiment: int
    openingGreeting: int
    closingGreeting: int


class Topic(BaseModel):
    topic: str
    sub_topic: str


class Topics(BaseModel):
    topics: list[Topic]


class Demographics(BaseModel):
    age: int
    gender: str
    income: str
    hobbies: str
    location: str
    religion: str
    ethnicity: str
    education: str
    occupation: str
    techComfort: str
    workStatus: str
    birthPlace: str
    nationality: str
    lastCompany: str
    housingType: str
    livingStatus: str
    petOwnership: str
    maritalStatus: str
    smokingHabits: str
    familyMembers: str
    physicalState: str
    medicalHistory: str
    politicalViews: str
    drinkingHabits: str
    favoriteCuisine: str
    travelFrequency: str
    socialMediaUsage: str
    standardOfLiving: str
    exerciseFrequency: str
    languagePreference: str
    dietaryPreferences: str
    transportationMode: str
    favoriteMusicGenre: str
    favoriteMovieGenre: str


class Psychographics(BaseModel):
    needs: str
    goals: str
    fears: str
    values: str
    opinions: str
    interests: str
    attitudes: str
    lifestyle: str
    behaviors: str
    painPoints: str
    motivators: str
    challenges: str
    aspirations: str
    preferences: str
    brandLoyalty: str
    buyingBehavior: str
    socialInfluences: str
    mediaConsumption: str
    personalityTraits: str
    decisionMakingStyle: str


class Persona(BaseModel):
    confidence: float
    explanation: str
    personality: str
    demographics: Demographics
    psychographics: Psychographics


class UserInterest(BaseModel):
    explanation: str
    not_interested: bool
    not_interested_in_calls: bool

@dataclass
class JsonPrompts:
    prompt: str
    rformat: Optional[BaseModel] = None


@dataclass
class EvaluationPrompts:
    score_prompt: str
    summary_prompt: str
    callback_prompt: str
    feedback_prompt: str
    guidelines_prompt: str
    score_details_prompt: JsonPrompts