import hashlib
import logging
import time

import bs4
from bs4 import Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from behance_parser import parser, storage

logger = logging.getLogger(__name__)

IMG_SELECTOR = "img[srcset]"
TEXT_SELECTOR = "div[class*=main-text]"
VIDEO_SELECTOR = "div[class*=project-module-video]"
PROJECT_ITEMS = "div#project-modules> div[class*=Project-projectModuleContainer]"

cookies: list[dict] | None = None


class ParsingException(Exception):
    ...


def get_page_html(url: str) -> str:
    driver = next(parser.get_driver())
    driver.get(url)
    WebDriverWait(driver, 10).until(
        ec.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'ProjectInfo-container')]")
        )
    )
    global cookies
    cookies = driver.get_cookies()
    return driver.page_source


def _parse_image(tag: Tag, task: storage.Task) -> None:
    img = tag.select_one(IMG_SELECTOR)
    srcset = img.attrs.get("srcset")
    sizes = srcset.split(",")
    higher_size_img_url = sizes[-1].strip().split(" ")[0]
    file_name = higher_size_img_url.split("/")[-1]
    uuid = file_name.replace(".jpg", "")
    if storage.is_image_exist(uuid, task.id):
        return
    img_data = parser.load_img(
        url=higher_size_img_url,
        cookies=cookies,
    )
    storage.store_image(
        uuid=uuid,
        data=img_data,
        task=task,
    )
    logger.info("Stored image with uuid: %s", uuid)
    time.sleep(1)


def _parse_text(tag: Tag, task: storage.Task) -> None:
    text = tag.select_one(TEXT_SELECTOR)
    extracted_content: list[str] = []
    for child in text.contents:
        content = child.text.strip()
        if content:
            content = content.replace(" ", " ")
            extracted_content.append(content)
    result = "\n".join(extracted_content)
    uuid = hashlib.sha1(result.encode()).hexdigest()
    storage.store_text(
        uuid=uuid,
        text=result,
        task=task,
    )
    logger.info("Stored text with uuid: %s", uuid)


def _parse_video(tag: Tag, task: storage.Task) -> None:
    video_container = tag.select_one(VIDEO_SELECTOR)
    iframe = video_container.select_one("iframe")
    url = iframe.attrs.get("src")
    uuid = hashlib.sha1(url.encode()).hexdigest()
    storage.store_video(
        uuid=uuid,
        link=url,
        task=task,
    )


def parse_project(task: storage.Task) -> None:
    html = get_page_html(task.url)
    soup = bs4.BeautifulSoup(html, "html.parser")
    container = soup.select_one(PROJECT_ITEMS)
    if not container:
        raise ParsingException("Cant find project-modules container")
    content = [i for i in container.contents if isinstance(i, Tag)]
    for tag in content:
        image = tag.select_one(IMG_SELECTOR)
        if image:
            _parse_image(tag, task)
            continue
        text = tag.select_one(TEXT_SELECTOR)
        if text:
            _parse_text(tag, task)
            continue
        video = tag.select_one(VIDEO_SELECTOR)
        if video:
            _parse_video(tag, task)
            continue
        logger.warning("Unknown tag found %s", tag)
    storage.set_task_parsing_status(task, is_parsed=True)


def process_tasks():
    while tasks := storage.get_next_tasks_for_parsing():
        for task in tasks:
            parse_project(task)
