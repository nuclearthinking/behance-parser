import logging
from urllib.parse import urlsplit

import requests
from pydantic import BaseModel

from behance_parser.exceptions import ParsingException
from behance_parser.fake_useragent import user_agent

logger = logging.getLogger(__name__)


def to_lower_camel_case(string: str) -> str:
    if string.startswith("_"):
        return string
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class Base(BaseModel):
    class Config:
        alias_generator = to_lower_camel_case


class Project(Base):
    id: int
    name: str
    url: str
    fields: list[dict]
    covers: dict


class Work(Base):
    has_more: bool
    projects: list[Project]


class ActiveSection(Base):
    work: Work


class Profile(Base):
    active_section: ActiveSection


class ProjectsResponse(Base):
    profile: Profile


default_headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "if-modified-since": "Tue, 19 Jul 2022 16:40:27 +0000",
    "sec-ch-ua": '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-newrelic-id": "VgUFVldbGwsFU1BRDwUBVw==",
    "x-requested-with": "XMLHttpRequest",
}


def _build_cookie(cookies: list[dict]) -> str:
    _cookie = [f'{i["name"]}={i["value"]}' for i in cookies]
    return "; ".join(_cookie)


def get_data(
    url: str,
    cookies: list[dict],
    offset: int,
) -> tuple[list[Project], bool]:
    scheme, host, path, *_ = urlsplit(url)
    request_url = f"{scheme}://{host}{path}/projects?offset={offset}"
    cookie_value = _build_cookie(cookies)
    headers = {
        "referer": url,
        "cookie": cookie_value,
        "user-agent": user_agent.get_random_user_agent(),
    }
    headers = default_headers | headers
    response = requests.get(
        url=request_url,
        headers=headers,
        verify=False,
    )
    response_data = response.json()
    parsed_response = ProjectsResponse.parse_obj(response_data)
    if work := parsed_response.profile.active_section.work:
        return work.projects, work.has_more
    return [], False


def load_img(url: str, cookies: list[dict]) -> bytes:
    cookie_value = _build_cookie(cookies)
    headers = {
        "referer": "https://www.behance.net/",
        "cookie": cookie_value,
        "user-agent": user_agent.get_random_user_agent(),
    }
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as exc:
        logging.exception('Error while downloading image for url %s', url)
        raise ParsingException('Cant download image') from exc

    return response.content
