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
    agency_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("agency.id"),
        nullable=False,
    )
    agency: Agency = sa.orm.relationship(
        "Agency",
        uselist=False,
        foreign_keys=[agency_id],
    )
    behance_id: int = sa.Column(sa.Integer, nullable=False, unique=True)
    name: str = sa.Column(sa.Text, nullable=False)
    url: str = sa.Column(sa.Text, nullable=False)
    is_parsed: bool = sa.Column(sa.Boolean, default=False)


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


def store_projects(projects: list[Project], agency_name: str) -> None:
    agency = _get_agency(agency_name=agency_name)
    for project in projects:
        _save_project(project, agency_id=agency.id)
        logger.info("Saved task for behance project: %s", project.id)


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


def get_all_agencies() -> list[str]:
    query = sa.select(Agency)
    return db_session.execute(query).unique().scalars().all()
