import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from behance_parser import fetcher, storage

service = Service(executable_path=ChromeDriverManager().install())
logger = logging.getLogger(__name__)


def get_driver():
    driver = webdriver.Chrome(service=service)
    yield driver
    driver.quit()


behance_url = "https://www.behance.net/"
cookies: list[dict] = []


def get_page_cookies(url: str) -> list[dict[str, str]]:
    driver = get_driver()
    driver.get(url)
    return driver.get_cookies()


def _do(
    url: str,
    offset: int,
    cookies: list[dict[str, str]],
    agency_name: str,
) -> tuple[bool, int]:
    projects, has_more = fetcher.get_data(
        url=url,
        cookies=cookies,
        offset=offset,
    )
    logging.info("Found %s projects", len(projects))
    storage.store_projects(projects, agency_name=agency_name)
    time.sleep(2)
    return has_more, offset + 12


def parse_agency(agency_name: str) -> None:
    url = f"{behance_url}{agency_name}"
    cookies = get_page_cookies(url)

    has_more, offset = _do(
        url=url,
        cookies=cookies,
        offset=0,
        agency_name=agency_name,
    )
    while has_more:
        has_more, offset = _do(
            url=url,
            cookies=cookies,
            offset=offset,
            agency_name=agency_name,
        )


def collect_tasks_for_parsing():
    agencies = storage.get_all_agencies()
    for agency in agencies:
        parse_agency(agency.name)
