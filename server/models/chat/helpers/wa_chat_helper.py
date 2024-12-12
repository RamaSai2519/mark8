import json
import openai
import requests
from .args_schemas import *
from shared.models.common import Common
from datetime import datetime, timedelta
from shared.models.interfaces import Output
from shared.configs import CONFIG as config
from shared.models.constants import TimeFormats


class WaChatHelper:
    def __init__(self, phoneNumber: str) -> None:
        self.context = 'wa_webhook'
        self.phoneNumber = phoneNumber

    def get_available_sarathis(self, arguments: dict = None) -> list:
        url = config.URL + '/actions/expert'
        params = {'filter_field': 'status', 'filter_value': 'online'}
        response = requests.get(url, params=params)
        output = Output(**response.json())
        data = output.output_details
        experts = []

        for expert in data:
            experts.append({
                'name': expert.get('name'),
                'description': expert.get('description'),
                'persona': expert.get('persona')
            })

        return json.dumps(experts)

    def upcoming_events(self, arguments: dict = None) -> list:
        url = config.URL + '/actions/list_events'
        params = {'fromToday': 'true'}
        response = requests.get(url, params=params)
        output = Output(**response.json())
        data = output.output_details.get('data', [])
        events = []

        for event in data:
            eventStartDateTime = event.get(
                'startEventDate', event.get('validUpto'))
            if eventStartDateTime:
                eventStartDateTime = datetime.strptime(
                    eventStartDateTime, TimeFormats.ANTD_TIME_FORMAT)
                eventStartDateTime += timedelta(hours=5, minutes=30)
                eventStartDateTime = eventStartDateTime.strftime(
                    '%Y-%m-%d %H:%M:%S')

            events.append({
                'mainTitle': event.get('mainTitle', ''),
                'subTitle': event.get('subTitle', ''),
                'hostedBy': event.get('hostedBy', ''),
                'guestSpeaker': event.get('guestSpeaker', ''),
                'eventStartDateTime': eventStartDateTime,
                'eventType': event.get('eventType', 'online'),
                'prizeMoney': event.get('prizeMoney', None),
                'eventPrice': event.get('eventPrice', 'Free'),
                'eventRegistrationLink': f'https://sukoonunlimited.com/{event.get("slug", "")}'
            })

        return json.dumps(events)

    def get_user_details(self, arguments: dict = None) -> dict:
        url = config.URL + '/actions/user'
        params = {'phoneNumber': self.phoneNumber}
        response = requests.get(url, params=params)
        output = Output(**response.json())
        user = output.output_details

        return {
            'name': user.get('name', ''),
            'persona': user.get('customerPersona', ''),
            'user_registered': True if user.get('profileCompleted') == True else False
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
                GetAvailableSarathis, description="Get the list of available sarathis. Call this whenever the user wants to speak to a sarathi. or wants to know who is available to speak to. It returns a list of sarathis with their names, descriptions, and personas. You can use the persona to recommend a sarathi to the user based on the user's persona. Do not return the list as it is or all at once."),
            openai.pydantic_function_tool(
                GetUpcomingEvents, description="Get the list of upcoming events. Call this whenever the user wants to know about the upcoming events. It returns a list of events with their main title, sub title, hosted by, guest speaker, event start date time, event type, prize money, event price, and event registration link. Do not return the list as it is or all at once."),
            openai.pydantic_function_tool(
                GetUserDetails, description="Get the user details. Call this whenever the user wants to know about their profile details. It returns the user's name, persona, and whether the user is registered or not."),
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
            "get_available_sarathis": self.get_available_sarathis,
            "upcoming_events": self.upcoming_events,
            "GetUserDetails": self.get_user_details,
            "SaveUserCity": lambda args: self.register_user(city=args.get('city')),
            "SaveUserName": lambda args: self.register_user(name=args.get('name')),
            "SaveUserBirthDate": lambda args: self.register_user(birthDate=args.get('birthDate'))
        }

        arguments = json.loads(arguments) if arguments else {}
        response = function_map[function_name](
            arguments) if function_name in function_map else {}
        return json.dumps(response)

    def get_current_time(self) -> str:
        current_time = Common.get_current_utc_time()
        current_time += timedelta(hours=5, minutes=30)
        return current_time.strftime('%Y-%m-%d %H:%M:%S')

    def get_system_message(self) -> str:
        return f"""
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

        Current Local Time: {self.get_current_time()}
        Use this time to compare with the event timings or sarathi availability.
        All times mentioned are in Indian Standard Time (IST).

        You will be provided with the list of available sarathis and you can recommend or show the list to the user if needed.
        Or can also recommend a sarathi based on the user query and the sarathi's personas.

        You are not to disclose the exact list of sarathis or the upcoming events to the user. You are only to provide the details of the sarathis and the events when asked by the user.
        And you will only describe them briefly and answer further queries if asked by the user.
        You will not share entire list at once, but share few events by relevance of time and few sarathis by their personas.

        If user is not registered, you can guide them to register by providing their name, city, and birthdate. The user is marked as registered only when all the details are provided but remember to save whatever details are provided by the user immediately.

        - Call the appropriate function to fetch specific information like Available Sarathis, Upcoming Events, or User Details.
        - While dealing with date strings when you want to call functions, always use this format: {TimeFormats.ANTD_TIME_FORMAT}.

        Here are some important links that you can share with the user when needed:
        This is the URL of the platform: https://sukoonunlimited.com/
        This is the URL of the platform's events page: https://sukoonunlimited.com/events
        This is the URL of the platform's sarathis page: https://sukoonunlimited.com/speak
        This is the URL of the platform's club membership page: https://sukoonunlimited.com/subscription

        If the user has any further queries or needs assistance, you can asure them that the support team is available from 9am-9pm and will contact them soon.
        You are only to converse and help the user with the queries related to the platform and the services provided by Sukoon Unlimited and nothing else.
        Make sure to keep the conversation engaging and informative. Remember to use emojis whenever necessary to make the conversation more engaging and friendly.
        Keep the message clean and format it properly before sending it to the user. Try to use bullet points and paragraphs to make the message more readable.
        """
