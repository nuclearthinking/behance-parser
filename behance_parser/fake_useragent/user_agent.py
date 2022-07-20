import json
import random

user_agents: list[str] | None = []


def __init_user_agents():
    with open('behance_parser/fake_useragent/ua.json', 'r') as ua_file:
        file_data = ua_file.read()
    user_agents_data = json.loads(file_data)
    user_agents.extend(user_agents_data['browsers'])


def get_random_user_agent() -> str:
    if not user_agents:
        __init_user_agents()
    return random.choice(user_agents)
