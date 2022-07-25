import json
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
    videos = storage.get_task_videos(project.id)
    _export_data(
        project=project,
        videos=videos,
        texts=texts,
        path=project_folder,
    )


def _export_images(images: list[storage.Image], path: Path) -> None:
    images_folder = path / "images"
    images_folder.mkdir(exist_ok=True)
    for image in images:
        file_path = images_folder / image.uuid
        if file_path.exists():
            continue
        with open(str(file_path), "wb") as _img_file:
            _img_file.write(image.image)


def _export_data(project: storage.Task, videos: list[storage.Video], texts: list[storage.Text], path: Path) -> None:
    data_file_path = path / 'data.json'
    text_data = [i.text for i in texts]
    video_data = [i.link for i in videos]
    data = dict(
        name=project.name,
        id=project.behance_id,
        url=project.url,
        agency=project.agency.name,
        text=text_data,
        videos=video_data,
    )
    with open(data_file_path, 'w') as data_file:
        data_file.write(json.dumps(data, indent=4))


def _generate_exporting_path(path) -> Path:
    if path is None:
        return Path(os.getcwd()) / "behance_parsing_result"
    path = Path(path)
    if path.is_absolute():
        return path
    return Path(os.getcwd()) / path
