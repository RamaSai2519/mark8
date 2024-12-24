from shared.models.interfaces import TranscriptPrompts
from shared.schemas import ScoreDetails, Topics, Persona, UserInterest, JsonPrompts, EvaluationPrompts


class Prompts:
    @staticmethod
    def get_transcript_prompts(user_name: str, expert_name: str, transcript: str) -> TranscriptPrompts:
        init_prompt = "I'll give you a call transcript between the user {user} and the sarathi {expert}. You have to correctly identify which Speaker is the User and which Speaker is the Sarathi (Generally Sarathi will be the one who ask the User questions about their routine and how they are doing. Also you can identify which speaker is Sarathi by their name). The user and sarathi connected via a website called 'Sukoon.Love', a platform for people to have conversations and seek guidance from Sarathis. Analyze the transcript and answer the questions I ask accordingly."
        init_prompt = init_prompt.format(user=user_name, expert=expert_name)

        transcript_prompt = "{transcript} \nThis is the transcript for the call"
        transcript_prompt = transcript_prompt.format(transcript=transcript)

        analysis_prompt = 'Analyze the transcript and flag any instances of inappropriate language or behavior. Detect any offensive language, insults, harassment, discrimination,religious or any other form of inappropriate communication. Just say "All good" if nothing is wrong or give a summary of flagged content if found anything wrong,  with the confidence score between 0 to 1.  Please be strict in analysing and give correct data only'

        prompts = {"init_prompt": init_prompt,
                   "transcript_prompt": transcript_prompt, "analysis_prompt": analysis_prompt}

        return TranscriptPrompts(**prompts)

    @staticmethod
    def get_evaluation_prompts(guidelines: str) -> EvaluationPrompts:
        guidelines_prompt = "These are the guidelines for evaluating the call: {guidelines}. Remember these while replying to the next prompts."
        guidelines_prompt = guidelines_prompt.format(guidelines=guidelines)

        callback_prompt = "Calculate probability of the user calling back only on the basis of the transcript given to you. Give the reason also."

        summary_prompt = "Summarize the transcript with a confidence score between 0 to 1."

        feedback_prompt = "Give me feedback for the sarathi or the expert with a confidence score between 0 to 1."

        details_prompt = """
                Please analyze the call transcript based on the given parameters.
                Opening Greeting(_/10)- Evaluate if the guidelines are followed.
                Time split between Saarthi and User(_/15) - Evaluate if the guidelines are followed.
                User Sentiment(_/20) - Evaluate the sentiment of the user based on the transcript.
                Flow Of Conversation(_/15) - Evaluate if the guidelines are followed.
                Time Spent on Call(_/10) - If time spent is more than 15 minutes, its good. Use the transcript provided initially for this.
                Probability of the User Calling Back(_/20) - The User should explicitly state that they would call back or the user and sarathi should mutually decide for a future date for the call for a higher score. Also mention the instance.
                Closing Greeting(_/10) - Evaluate if the guidelines are followed.
                
                Find the section relating to the parameters in the guidelines before you give a score. Higher score if the guidelines are followed. With the confidence score between 0 to 1.
                """
        details_prompt = JsonPrompts(details_prompt, ScoreDetails)

        score_prompt = "Give me a total score out of 100. Return only the number."

        prompts = {"callback_prompt": callback_prompt, "summary_prompt": summary_prompt, "feedback_prompt": feedback_prompt,
                   "guidelines_prompt": guidelines_prompt, "score_details_prompt": details_prompt, "score_prompt": score_prompt}

        return EvaluationPrompts(**prompts)

    @staticmethod
    def get_topics_prompt(topics: str) -> str:
        prompt = "\n Identify the topics they are talking about from the topics below."
        prompt += "\n\n" + "Topics:\n" + topics
        prompt = JsonPrompts(prompt, Topics)
        return prompt

    @staticmethod
    def get_persona_prompt(persona: str | None, person: str = "user") -> str:
        old_persona_prompt = "This is the {person} persona derived from previous call transcripts: {persona}. \n"
        persona_prompt = """
                Generate a {person} persona from the transcript provided above. 
                Remember which speaker was the {person} and use only that speaker lines from the transcript to generate this persona. 
                Make sure to take into account the old values also and then compare it to the new values you want to update.
                Update the explanation field with the reasons and instances from the transcript.
                Be sure to provide elaborate values for each property in the persona.
                Please be strict in analysing and give correct data only.
                """

        if persona:
            prompt = old_persona_prompt.format(
                persona=persona, person=person) + persona_prompt.format(person=person)
        else:
            prompt = persona_prompt.format(person=person)

        prompt = JsonPrompts(prompt, Persona)

        return prompt

    @staticmethod
    def get_interest_prompt() -> JsonPrompts:
        prompt = "Identify if the user has stated they are not interested in the platform, i.e. Sukoon Unlimited. Or if the user indicated they are not interested in calls from the platform. If not interested, return the respective value as 'true', else 'false'. State your reason and the instance as the explanation."
        prompt = JsonPrompts(prompt, UserInterest)
        return prompt
