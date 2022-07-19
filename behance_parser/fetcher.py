from urllib.parse import urlsplit

import requests
from pydantic import BaseModel


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
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
    "x-bcp": "b288dadf-5f18-478d-8ebd-fd356f175ffe",
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
    response = requests.get(
        url=request_url,
        headers={"referer": url, "cookie": cookie_value} | default_headers,
        verify=False,
    )
    response_data = response.json()
    parsed_response = ProjectsResponse.parse_obj(response_data)
    if work := parsed_response.profile.active_section.work:
        return work.projects, work.has_more
