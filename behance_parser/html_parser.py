import hashlib
import logging
import time

import bs4
from bs4 import Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from behance_parser import fetcher, image_loader, parser, storage
from behance_parser.exceptions import ParsingException

logger = logging.getLogger(__name__)

IMG_SELECTOR = "img[srcset]"
TEXT_SELECTOR = "div[class*=main-text]"
VIDEO_SELECTOR = "div[class*=project-module-video]"
VIDEO_EMBED_SELECTOR = "div[class*=project-module-embed]"
PROJECT_ITEMS = "div#project-modules>div[class*=Project-projectModuleContainer]"
SLIDER_SELECTOR = "script[class*=js-lightbox-slide-content]"
SKIP_ELEMENTS = [
    "div[class*=Module-blockGridPointerEvents]",
    "div.divider",
    "div.module-separator",
]

cookies: list[dict] | None = None


def get_page_html(url: str) -> str:
    driver = parser.get_driver()
    driver.get(url)
    time.sleep(1)
    WebDriverWait(driver, 10).until(
        ec.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'ProjectInfo-container')]")
        )
    )
    global cookies
    cookies = driver.get_cookies()
    return driver.page_source


def _parse_image(tag: Tag, task: storage.Task) -> None:
    images = tag.select(IMG_SELECTOR)
    for img in images:
        srcset = img.attrs.get("srcset")
        sizes = srcset.split(",")
        sizes = [i for i in sizes if i]
        higher_size_img_url = sizes[-1].strip().split(" ")[0]
        file_name = higher_size_img_url.split("/")[-1]
        if storage.is_image_exist(file_name.lower(), task.id):
            return
        img_data = fetcher.load_img(
            url=higher_size_img_url,
            cookies=cookies,
        )
        storage.store_image(
            uuid=file_name,
            data=img_data,
            task=task,
        )


def _extract_image_urls(tag: Tag) -> list[str]:
    images = tag.select(IMG_SELECTOR)
    urls = []
    for img in images:
        srcset = img.attrs.get("srcset")
        sizes = srcset.split(",")
        sizes = [i for i in sizes if i]
        higher_size_img_url = sizes[-1].strip().split(" ")[0]
        urls.append(higher_size_img_url)
    return urls


def _extract_slider_urls(tag: Tag) -> list[str]:
    urls = []
    slider = tag.select_one(SLIDER_SELECTOR)
    for slider_content in slider.contents:
        if isinstance(slider_content, bs4.element.Script):
            slider_content = bs4.BeautifulSoup(slider_content, "html.parser")
        image = slider_content.select_one(IMG_SELECTOR)
        if image:
            urls.extend(_extract_image_urls(slider_content))
    return urls


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


def _parse_video(tag: Tag, task: storage.Task) -> None:
    video_container = tag.select_one(VIDEO_SELECTOR) or tag.select_one(
        VIDEO_EMBED_SELECTOR
    )
    if "unsafe" in video_container.attrs["class"]:
        return
    iframe = video_container.select_one("iframe")
    url = iframe.attrs.get("src")
    uuid = hashlib.sha1(url.encode()).hexdigest()
    storage.store_video(
        uuid=uuid,
        link=url,
        task=task,
    )


def _is_pointless_element(tag: Tag) -> bool:
    for selector in SKIP_ELEMENTS:
        itm = tag.select_one(selector)
        if itm:
            return True
    return False


def _parse_slider(tag: Tag, task: storage.Task) -> None:
    slider = tag.select_one(SLIDER_SELECTOR)
    for slider_content in slider.contents:
        if isinstance(slider_content, bs4.element.Script):
            slider_content = bs4.BeautifulSoup(slider_content, "html.parser")
        image = slider_content.select_one(IMG_SELECTOR)
        if image:
            _parse_image(slider_content, task)


def parse_project(task: storage.Task) -> None:
    logger.info("Processing project: %s", task.id)
    html = get_page_html(task.url)
    soup = bs4.BeautifulSoup(html, "html.parser")
    content = soup.select(PROJECT_ITEMS)
    if not content:
        logger.warning("Can't find project-modules container")
        storage.set_task_error_status(task, is_error=True)
        return
    content = [i for i in content if isinstance(i, Tag)]
    logger.info("Found %s items", len(content))
    urls = []
    for tag in content:
        try:
            image = tag.select_one(IMG_SELECTOR)
            if image:
                urls.extend(_extract_image_urls(tag))
                # _parse_image(tag, task)
                continue
            text = tag.select_one(TEXT_SELECTOR)
            if text:
                _parse_text(tag, task)
                continue
            video = tag.select_one(VIDEO_SELECTOR) or tag.select_one(
                VIDEO_EMBED_SELECTOR
            )
            if video:
                _parse_video(tag, task)
                continue
            slider = tag.select_one(SLIDER_SELECTOR)
            if slider:
                urls.extend(_extract_slider_urls(tag))
                # _parse_slider(tag, task)
                continue
            if _is_pointless_element(tag):
                logger.info("Pointless element found, skip")
                continue
            logger.warning("Unknown tag found %s", tag)
            storage.set_task_error_status(task, is_error=True)
            return
        except ParsingException:
            logger.warning("Error while parsing tag %s", tag.prettify())
            storage.set_task_error_status(task, is_error=True)
            return
    images = image_loader.ImagesLoader(urls, cookies).load()
    for file_name, file_data in images.items():
        storage.store_image(file_name, file_data, task)
    storage.set_task_parsing_status(task, is_parsed=True)
    logger.info("Completed processing for project: %s", task.id)


def process_tasks():
    while tasks := storage.get_next_tasks_for_parsing():
        for task in tasks:
            parse_project(task)
