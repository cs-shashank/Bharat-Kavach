"""
Smoke tests for database.py

Test 1 — Import smoke test:
    Verifies that `import database` succeeds with no ImportError or AttributeError.

Test 2 — Table existence and queryability:
    Creates an isolated in-memory SQLite database, runs Base.metadata.create_all,
    and confirms both `case_reports` and `forensic_documents` tables exist and
    return an empty list (not an error) when queried.

Requirements covered:
    - Requirement 1.1: database.py imports cleanly
    - Requirement 1.3: tables are created and queryable
"""


def test_database_import_no_errors():
    """Smoke test: importing the database module raises no ImportError or AttributeError."""
    try:
        import database  # noqa: F401
    except ImportError as exc:
        raise AssertionError(f"database module raised ImportError: {exc}") from exc
    except AttributeError as exc:
        raise AssertionError(f"database module raised AttributeError: {exc}") from exc


def test_tables_exist_and_queryable():
    """
    After Base.metadata.create_all on a fresh in-memory SQLite engine,
    both case_reports and forensic_documents tables exist and return
    an empty list when queried.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base, CaseReport, ForensicDocument

    # Use an isolated in-memory engine — never touches the real .db file
    in_memory_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=in_memory_engine)

    Session = sessionmaker(bind=in_memory_engine)
    db = Session()
    try:
        case_reports = db.query(CaseReport).all()
        assert case_reports == [], (
            f"Expected empty list for case_reports, got {case_reports}"
        )

        forensic_docs = db.query(ForensicDocument).all()
        assert forensic_docs == [], (
            f"Expected empty list for forensic_documents, got {forensic_docs}"
        )
    finally:
        db.close()
