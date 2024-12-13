import json
import openai
import requests
from .args_schemas import *
from shared.models.common import Common
from shared.models.interfaces import Output
from shared.configs import CONFIG as config
from shared.models.constants import TimeFormats
from shared.db.chat import get_system_prompts_collection


class WaChatHelper:
    def __init__(self, phoneNumber: str) -> None:
        self.context = 'wa_webhook'
        self.phoneNumber = phoneNumber
        self.system_prompts_collection = get_system_prompts_collection()

    def get_available_sarathis(self, page: int, size: int) -> list:
        url = config.URL + '/actions/expert'
        params = {'filter_field': 'status', 'filter_value': 'online'}
        params['page'] = page
        params['size'] = size
        response = requests.get(url, params=params)
        output = Output(**response.json())
        data = output.output_details
        experts = []

        for expert in data:
            experts.append({
                'name': expert.get('name'),
                'persona': json.dumps(expert.get('persona'))
            })

        return experts

    def upcoming_events(self, arguments: dict = None) -> list:
        url = config.URL + '/actions/list_events'
        params = {'fromToday': 'true'}
        response = requests.get(url, params=params)
        output = Output(**response.json())
        data = output.output_details.get('data', [])
        return data

    def get_user_details(self, arguments: dict = None) -> dict:
        url = config.URL + '/actions/user'
        params = {'phoneNumber': self.phoneNumber}
        response = requests.get(url, params=params)
        output = Output(**response.json())
        user = output.output_details

        return {
            'name': user.get('name', ''),
            'city': user.get('city', ''),
            'birthDate': user.get('birthDate', '').strftime('%Y-%m-%d') if user.get('birthDate') else '',
            'persona': user.get('customerPersona', '')
        }

    def register_user(self, name: str = None, city: str = None, birthDate: str = None) -> dict:
        url = config.URL + '/actions/user'
        payload = {
            'phoneNumber': self.phoneNumber,
            'name': name,
        }
        if birthDate:
            payload['birthDate'] = birthDate
        if city:
            payload['city'] = city
        response = requests.post(url, json=payload)
        return response.json()

    def get_tools(self) -> list:
        return [
            openai.pydantic_function_tool(
                GetAvailableSarathis, description="Get the list of available sarathis. Call this whenever the user wants to speak to a sarathi. or wants to know who is available to speak to. It returns a list of sarathis with their names, descriptions, and personas. You can use the persona to recommend a sarathi to the user based on the user's persona. Do not return the list as it is or all at once. Use the page and size arguments to paginate the list as the full list may be too large. Keep the size to 3 at max."),
            openai.pydantic_function_tool(
                GetUpcomingEvents, description="Get the list of upcoming events. Call this whenever the user wants to know about the upcoming events. It returns a list of events with their main title, sub title, hosted by, guest speaker, event start date time, event type, prize money, event price, and event registration link. Do not return the list as it is or all at once."),
            openai.pydantic_function_tool(
                GetUserDetails, description="Get the user details. Call this whenever you want to know about the user's profile details. It returns the user's name, persona, city and birthDate. Use this to check if the user is registered or not."),
            openai.pydantic_function_tool(
                SaveUserCity, description="Save the user's city."),
            openai.pydantic_function_tool(
                SaveUserName, description="Save the user's name."),
            openai.pydantic_function_tool(
                SaveUserBirthDate, description="Save the user's birth date."),
        ]

    def handle_function_call(self, function_name: str, arguments: str):
        print(
            f"Function Name: {function_name}, Arguments: {arguments}"
        )
        function_map = {
            "GetAvailableSarathis": lambda args: self.get_available_sarathis(page=args.get('page'), size=args.get('size')),
            "GetUpcomingEvents": self.upcoming_events,
            "GetUserDetails": self.get_user_details,
            "SaveUserCity": lambda args: self.register_user(city=args.get('city')),
            "SaveUserName": lambda args: self.register_user(name=args.get('name')),
            "SaveUserBirthDate": lambda args: self.register_user(birthDate=args.get('birthDate'))
        }

        arguments = json.loads(arguments) if arguments else {}
        response = function_map[function_name](
            arguments) if function_name in function_map else {}
        print(f"Response: {response}")
        return json.dumps(response)

    def get_current_time(self) -> str:
        current_time = Common.get_current_utc_time()
        return current_time.strftime('%Y-%m-%d %H:%M:%S')

    def get_system_message(self) -> str:
        prompt = f"""
        You are a customer service chatbot for 'Sukoon Unlimited'(called 'Sukoon' at times), a company dedicated to enriching the lives of senior citizens by fostering meaningful connections,
        emotional well-being, and community engagement. Sukoon Unlimited provides conversation-based activities, therapist-led support groups, and expert advice in
        areas like mental health, financial planning, and spirituality. Sukoon Sarathis are mentors or facilitators associated with Sukoon Unlimited. They are individuals
        trained to guide and support senior citizens within the platform’s community. Sarathis lead conversation-based activities, facilitate group discussions, and provide
        a compassionate ear for seniors looking to share their experiences or seek guidance.
        Their role is crucial in creating a warm, supportive, and engaging environment for the platform’s users. Sarathis might also help seniors navigate challenges,
        connect with resources, or participate in community-driven activities aimed at enhancing emotional and mental well-being.

        Your role is to:
            1.	Answer user queries about Sukoon Unlimited’s services.
            2.	Provide empathetic and clear communication, catering especially to seniors and their families.
            3.	Help users navigate the Sukoon Unlimited platform, including signing up, accessing resources, and other such tasks.
            4.	Share details about Sukoon’s core values: trust, safety, and availability.
            5.  Guide the user to the right resources, events, sarathis or membership details.

        You are to maintain a warm, respectful, and approachable tone, ensuring clarity and understanding. When faced with complex questions or topics outside your
        scope, direct users to Sukoon Unlimited’s support team for further assistance. Always prioritize user well-being and promote the company’s mission to make
        senior lives happier and more connected.

        Current Time: {self.get_current_time()}
        Use this time to compare with the event timings or sarathi availability.
        Remember to convert all times to Indian Standard Time (IST) before sharing them with the user.

        You will be provided with the list of available sarathis and you can recommend or show the list to the user if needed.
        Or can also recommend a sarathi based on the user query and the sarathi's personas.

        You are only to provide the details of the sarathis and the events when asked by the user.
        Remember to format the details properly, use bullet points, and keep the message clean and engaging.
        And you will only describe them briefly and answer further queries if asked by the user.
        You will not share entire list at once, but share few events by relevance of time and few sarathis by their personas.

        Name, City, and Birthdate are the details that the user is to provide to register on the platform.
        If any of these details are missing, you can ask the user to provide them once at the start of the conversation and once at the end.
        The user is marked as registered only when all the details are provided but remember to save whatever details are provided by the user immediately.
        Also make sure to capture these details when user is talking about them in any context.
        Do not ask for these details again if we already have them. You can use the `GetUserDetails` function to check if the user is registered or not.

        - Use the `GetUserDetails` function to check if the user is registered or not. The function returns the user's name, persona, and whether the user is registered or not.
        - Always greet the user with their name if they are registered else ask them to register by providing their name, city, and birthdate.
        - Remember to greet the user with a brief introduction and a overview of your capabilities.
        - One of your main objective is to register the user on the platform by asking for their name, city, and birthdate if they are not registered.
        - Call the appropriate function to fetch specific information like Available Sarathis, Upcoming Events, or User Details.
        - While dealing with date strings when you want to call functions, always use this format: {TimeFormats.ANTD_TIME_FORMAT}.
        - Try to converse in the language user is speaking in.
        - Only show the events that are fetched using the 'GetUpcomingEvents' function. DO NOT HALLUCINATE.
        - Do not share the event's `meetingLink` or `meetingId` with the user at any cost.
        - Sharing `meetingLink` or `meetingId` or zoom link with the user is strictly prohibited.
        - You are allowed to share the event's registration link with `slug` in place of [event_slug] like this: https://sukoonunlimited.com/[event_slug]

        Here are some important links that you can share with the user when needed:
        This is the URL of the platform: https://sukoonunlimited.com/
        This is the URL of the platform's events page: https://sukoonunlimited.com/events
        This is the URL of the platform's sarathis page: https://sukoonunlimited.com/speak
        This is the URL of the platform's club membership page: https://sukoonunlimited.com/subscription

        If the user has any further queries or needs assistance, you can asure them that the support team is available from 9am-9pm and will contact them soon.
        You are only to converse and help the user with the queries related to the platform and the services provided by Sukoon Unlimited and nothing else.
        Make sure to keep the conversation engaging and informative. Remember to use emojis whenever necessary to make the conversation more engaging and friendly.
        Keep the message clean and format it properly before sending it to the user. Try to use bullet points and paragraphs to make the message more readable.
        Keep the message as detailed and informative as possible but do not share any information that is not provided by the user or the system.
        """

        system_prompt = self.system_prompts_collection.find_one(
            {'context': self.context})
        if system_prompt:
            prompt += "\n Here's everything you need to know about Sukoon Unlmited:\n"
            prompt += system_prompt['content']
        prompt += "\n\n IMPORTANT NOTE: ONLY SHARE AND ANSWER THE QUESTIONS ABOUT THE INFORMATION YOU HAVE BEEN PROVIDED WITH. DO NOT SHARE ANY OTHER INFORMATION OR ENGAGE IN ANY OTHER CONVERSATION WITH THE USER. YOU ARE PROHIBHITED FROM ASSUMING ANYTHING THAT YOU DON'T KNOW ABOUT THE COMPANY OR THE SERVICES PROVIDED BY THE COMPANY. IF YOU ARE UNSURE ABOUT ANYTHING, PLEASE DIRECT THE USER TO THE SUPPORT TEAM. \n\n"
        return prompt
