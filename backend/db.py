from datetime import datetime, timezone
from sqlalchemy import create_engine, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine = create_engine(
    "sqlite:///jobs.db",
    connect_args={"check_same_thread": False},  # background thread koristi svoju sesiju
)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="queued")
    done: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    result: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


def init_db():
    Base.metadata.create_all(engine)
    # jobovi koji su bili u toku kad je server pao ne mogu se nastaviti
    with Session(engine) as s:
        s.query(Job).filter(Job.status.in_(["queued", "running"])).update(
            {"status": "error", "error": "Server restarted"},
            synchronize_session=False,
        )
        s.commit()