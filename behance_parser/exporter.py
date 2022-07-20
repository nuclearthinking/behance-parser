import os
from pathlib import Path

from behance_parser import storage


def export_data_to(path: str) -> None:
    path = _generate_exporting_path(path)
    path.mkdir(parents=True, exist_ok=True)
    agencies = storage.get_all_agencies()
    for agency in agencies:
        _export_agency_data(agency=agency, path=path)


def _export_agency_data(agency: storage.Agency, path: Path) -> None:
    agency_folder = path / agency.name
    agency_folder.mkdir(exist_ok=True)
    projects = storage.get_tasks_by_agency_id(agency_id=agency.id)
    for project in projects:
        _export_project_data(project, agency_folder)


def _export_project_data(project: storage.Task, path: Path) -> None:
    project_folder = path / str(project.behance_id)
    project_folder.mkdir(exist_ok=True)
    images = storage.get_task_images(project.id)
    _export_images(images, project_folder)
    texts = storage.get_task_texts(project.id)
    _export_texts(texts, project_folder)
    videos = storage.get_task_videos(project.id)
    _export_videos(videos, project_folder)


def _export_images(images: list[storage.Image], path: Path) -> None:
    images_folder = path / "images"
    images_folder.mkdir(exist_ok=True)
    for image in images:
        file_path = images_folder / f"{image.uuid}.jpg"
        if file_path.exists():
            continue
        with open(str(file_path), "wb") as _img_file:
            _img_file.write(image.image)


def _export_texts(texts: list[storage.Text], path: Path) -> None:
    file_path = path / "texts.txt"
    if file_path.exists():
        os.remove(file_path)
    content = [i.text for i in texts]
    content = "\n".join(content)
    with open(file_path, "w") as _text_file:
        _text_file.write(content)


def _export_videos(videos: list[storage.Video], path: Path) -> None:
    file_path = path / "videos.txt"
    if file_path.exists():
        os.remove(file_path)
    links = [i.link for i in videos]
    links = "\n".join(links)
    with open(file_path, "w") as _links_file:
        _links_file.write(links)


def _generate_exporting_path(path) -> Path:
    if path is None:
        return Path(os.getcwd()) / "behance_parsing_result"
    path = Path(path)
    if path.is_absolute():
        return path
    return Path(os.getcwd()) / path
