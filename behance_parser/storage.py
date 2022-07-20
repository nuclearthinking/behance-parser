import logging

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from behance_parser.fetcher import Project

logger = logging.getLogger(__name__)

engine = sa.create_engine("sqlite:///data.db", echo=False)
db_session = scoped_session(sessionmaker(autocommit=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class Agency(Base):
    __tablename__ = "agency"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name: str = sa.Column(sa.Text, unique=True)


class Task(Base):
    __tablename__ = "task"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    agency_id: int = sa.Column(sa.Integer, sa.ForeignKey("agency.id"), nullable=False)
    agency: Agency = sa.orm.relationship("Agency", uselist=False, foreign_keys=[agency_id])
    behance_id: int = sa.Column(sa.Integer, nullable=False, unique=True)
    name: str = sa.Column(sa.Text, nullable=False)
    url: str = sa.Column(sa.Text, nullable=False)
    is_parsed: bool = sa.Column(sa.Boolean, default=False)


class Text(Base):
    __tablename__ = "text"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    task_id: int = sa.Column(sa.Integer, sa.ForeignKey('task.id'), nullable=False)
    task: 'Task' = sa.orm.relationship('Task', uselist=False, foreign_keys=[task_id])
    text: str = sa.Column(sa.Text, nullable=False)
    uuid: str = sa.Column(sa.Text, nullable=False)

    __table_args__ = (
        sa.Index('text_task_id__uuid__uidx', task_id, uuid, unique=True),
    )


class Image(Base):
    __tablename__ = "image"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    task_id: int = sa.Column(sa.Integer, sa.ForeignKey('task.id'), nullable=False)
    task: 'Task' = sa.orm.relationship('Task', uselist=False, foreign_keys=[task_id])
    image: bytes = sa.Column(sa.BLOB, nullable=False)
    uuid: str = sa.Column(sa.Text, nullable=False)

    __table_args__ = (
        sa.Index('image_task_id__uuid__uidx', task_id, uuid, unique=True),
    )


class Video(Base):
    __tablename__ = "video"
    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    task_id: int = sa.Column(sa.Integer, sa.ForeignKey('task.id'), nullable=False)
    task: 'Task' = sa.orm.relationship('Task', uselist=False, foreign_keys=[task_id])
    link: str = sa.Column(sa.Text, nullable=False)
    uuid: str = sa.Column(sa.Text, nullable=False)

    __table_args__ = (
        sa.Index('video_task_id__uuid__uidx', task_id, uuid, unique=True),
    )


Base.metadata.create_all(engine, checkfirst=True)


def _save_project(project: Project, agency_id: int) -> None:
    query = sa.select(Task).where(Task.behance_id == project.id)
    task = db_session.execute(query).scalar_one_or_none()
    if task:
        return
    db_session.add(
        Task(
            behance_id=project.id,
            name=project.name,
            url=project.url,
            agency_id=agency_id,
        )
    )
    db_session.commit()
    logger.info("Saved task for behance project: %s", project.id)


def store_projects(projects: list[Project], agency_name: str) -> None:
    agency = _get_agency(agency_name=agency_name)
    for project in projects:
        _save_project(project, agency_id=agency.id)


def _get_agency(agency_name: str) -> Agency | None:
    query = sa.select(Agency).where(Agency.name == agency_name)
    agency = db_session.execute(query).scalar_one_or_none()
    if agency:
        return agency
    agency = Agency(name=agency_name)
    db_session.add(agency)
    db_session.commit()
    db_session.refresh(agency)
    return agency


def create_agencies(agencies: list[str]) -> None:
    for agency in agencies:
        _get_agency(agency)


def get_all_agencies() -> list[Agency]:
    query = sa.select(Agency)
    return db_session.execute(query).unique().scalars().all()


def get_task_by_id(id_: int) -> Task | None:
    query = sa.select(Task).where(Task.id == id_)
    return db_session.execute(query).scalar_one_or_none()


def store_image(uuid: str, data: bytes, task: Task) -> None:
    if is_image_exist(uuid, task.id):
        return
    img = Image(
        task=task,
        image=data,
        uuid=uuid,
    )
    db_session.add(img)
    db_session.commit()


def is_image_exist(uuid: str, task_id: int) -> bool:
    query = sa.select(Image).where(sa.and_(
        Image.uuid == uuid,
        Image.task_id == task_id,
    ))
    img = db_session.execute(query).scalar_one_or_none()
    return bool(img)


def is_text_exist(uuid: str, task_id: int) -> bool:
    query = sa.select(Text).where(sa.and_(
        Text.uuid == uuid,
        Text.task_id == task_id,
    ))
    text = db_session.execute(query).scalar_one_or_none()
    return bool(text)


def store_text(uuid: str, text: str, task: Task) -> None:
    if is_text_exist(uuid, task.id):
        return
    text_model = Text(
        task=task,
        text=text,
        uuid=uuid,
    )
    db_session.add(text_model)
    db_session.commit()


def is_video_exist(uuid: str, task_id: int) -> bool:
    query = sa.select(Video).where(sa.and_(
        Video.uuid == uuid,
        Video.task_id == task_id
    ))
    return db_session.execute(query).scalar_one_or_none()


def store_video(uuid: str, link: str, task: Task) -> None:
    if is_video_exist(uuid, task_id=task.id):
        return
    video = Video(
        uuid=uuid,
        link=link,
        task=task
    )
    db_session.add(video)
    db_session.commit()
    logger.info('Stored video link with uuid: %s', uuid)


def set_task_parsing_status(task: Task, is_parsed: bool) -> None:
    task.is_parsed = is_parsed
    db_session.add(task)
    db_session.commit()


def get_tasks_by_agency_id(agency_id: int) -> list[Task]:
    query = sa.select(Task).where(sa.and_(
        Task.agency_id == agency_id,
        Task.is_parsed.is_(True)
    ))
    return db_session.execute(query).scalars().all()


def get_next_tasks_for_parsing(limit: int = 10) -> list[Task]:
    query = sa.select(Task).where(Task.is_parsed.is_(False)).limit(limit)
    return db_session.execute(query).scalars().all()


def get_task_images(task_id: int) -> list[Image]:
    query = sa.select(Image).where(Image.task_id == task_id)
    return db_session.execute(query).scalars().all()


def get_task_texts(task_id: int) -> list[Text]:
    query = sa.select(Text).where(Text.task_id == task_id)
    return db_session.execute(query).scalars().all()


def get_task_videos(task_id: int) -> list[Video]:
    query = sa.select(Video).where(Video.task_id == task_id)
    return db_session.execute(query).scalars().all()
