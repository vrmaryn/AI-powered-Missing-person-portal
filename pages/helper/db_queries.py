# import sqlite3
# from sqlmodel import create_engine, Session, select

# from pages.helper.data_models import RegisteredCases, PublicSubmissions


# sqlite_url = "sqlite:///sqlite_database.db"
# engine = create_engine(sqlite_url)


# def create_db():
#     try:
#         RegisteredCases.__table__.create(engine)
#         PublicSubmissions.__table__.create(engine)
#     except:
#         pass


# def register_new_case(case_details: RegisteredCases):
#     with Session(engine) as session:
#         session.add(case_details)
#         session.commit()


# def fetch_registered_cases(submitted_by: str, status: str):
#     if status == "All":
#         status = ["F", "NF"]
#     elif status == "Found":
#         status = ["F"]
#     elif status == "Not Found":
#         status = ["NF"]

#     with Session(engine) as session:
#         result = session.exec(
#             select(
#                 RegisteredCases.id,
#                 RegisteredCases.name,
#                 RegisteredCases.age,
#                 RegisteredCases.status,
#                 RegisteredCases.last_seen,
#                 RegisteredCases.matched_with,
#             )
#             .where(RegisteredCases.submitted_by == submitted_by)
#             .where(RegisteredCases.status.in_(status))
#         ).all()
#         return result


# def fetch_public_cases(train_data: bool, status: str):
#     if train_data:
#         with Session(engine) as session:
#             result = session.exec(
#                 select(
#                     PublicSubmissions.id,
#                     PublicSubmissions.face_mesh,
#                 ).where(PublicSubmissions.status == status)
#             ).all()
#             return result

#     with Session(engine) as session:
#         result = session.exec(
#             select(
#                 PublicSubmissions.id,
#                 PublicSubmissions.status,
#                 PublicSubmissions.location,
#                 PublicSubmissions.mobile,
#                 PublicSubmissions.birth_marks,
#                 PublicSubmissions.submitted_on,
#                 PublicSubmissions.submitted_by,
#             )
#         ).all()
#         return result


# def get_not_confirmed_registered_cases(submitted_by: str):
#     with Session(engine) as session:
#         result = session.query(RegisteredCases).all()
#         return result


# def get_training_data(submitted_by: str):
#     with Session(engine) as session:
#         result = session.exec(
#             select(RegisteredCases.id, RegisteredCases.face_mesh)
#             .where(RegisteredCases.submitted_by == submitted_by)
#             .where(RegisteredCases.status == "NF")
#         ).all()
#         return result


# def new_public_case(public_case_details: PublicSubmissions):
#     with Session(engine) as session:
#         session.add(public_case_details)
#         session.commit()


# def get_public_case_detail(case_id: str):
#     with Session(engine) as session:
#         result = session.exec(
#             select(
#                 PublicSubmissions.location,
#                 PublicSubmissions.submitted_by,
#                 PublicSubmissions.mobile,
#                 PublicSubmissions.birth_marks,
#             ).where(PublicSubmissions.id == case_id)
#         ).all()
#         return result


# def get_registered_case_detail(case_id: str):
#     print(case_id)
#     with Session(engine) as session:
#         result = session.exec(
#             select(
#                 RegisteredCases.name,
#                 RegisteredCases.complainant_mobile,
#                 RegisteredCases.age,
#                 RegisteredCases.last_seen,
#                 RegisteredCases.birth_marks,
#             ).where(RegisteredCases.id == case_id)
#         ).all()
#         print(result)
#         return result


# def list_public_cases():
#     with Session(engine) as session:
#         result = session.exec(select(PublicSubmissions)).all()
#         return result


# def update_found_status(register_case_id: str, public_case_id: str):
#     with Session(engine) as session:
#         registered_case_details = session.exec(
#             select(RegisteredCases).where(RegisteredCases.id == str(register_case_id))
#         ).one()
#         registered_case_details.status = "F"
#         registered_case_details.matched_with = str(public_case_id)

#         public_case_details = session.exec(
#             select(PublicSubmissions).where(PublicSubmissions.id == str(public_case_id))
#         ).one()
#         public_case_details.status = "F"

#         session.add(registered_case_details)
#         session.add(public_case_details)
#         session.commit()


# def get_registered_cases_count(submitted_by: str, status: str):
#     create_db()

#     with Session(engine) as session:
#         result = session.exec(
#             select(RegisteredCases)
#             .where(RegisteredCases.submitted_by == submitted_by)
#             .where(RegisteredCases.status == status)
#         ).all()
#         return result


# if __name__ == "__main__":
#     r = fetch_public_cases("NF")
#     print(r)


import sqlite3
import os
from sqlmodel import create_engine, Session, select
from dotenv import load_dotenv

from pages.helper.data_models import RegisteredCases, PublicSubmissions

# Load environment variables
load_dotenv()


# Database configuration
USE_POSTGRES = os.getenv("USE_POSTGRES", "False") == "True"

if USE_POSTGRES:
    # PostgreSQL/Supabase
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env file!")
    
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True to see SQL queries (for debugging)
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10
    )
    print(f"✅ Connected to PostgreSQL (Supabase)")
else:
    # SQLite (fallback)
    sqlite_url = "sqlite:///sqlite_database.db"
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )
    print(f"⚠️ Using SQLite (local database)")


def create_db():
    """Create all tables if they don't exist"""
    try:
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        pass


def register_new_case(case_details: RegisteredCases):
    with Session(engine) as session:
        session.add(case_details)
        session.commit()
    return None


def fetch_registered_cases(submitted_by: str, status: str):
    if status == "All":
        status = ["F", "NF"]
    elif status == "Found":
        status = ["F"]
    elif status == "Not Found":
        status = ["NF"]

    with Session(engine) as session:
        result = session.exec(
            select(
                RegisteredCases.id,
                RegisteredCases.name,
                RegisteredCases.age,
                RegisteredCases.status,
                RegisteredCases.last_seen,
                RegisteredCases.matched_with,
            )
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status.in_(status))
        ).all()
        return result


def fetch_public_cases(train_data: bool, status: str):
    if train_data:
        with Session(engine) as session:
            result = session.exec(
                select(
                    PublicSubmissions.id,
                    PublicSubmissions.face_mesh,
                ).where(PublicSubmissions.status == status)
            ).all()
            return result

    with Session(engine) as session:
        result = session.exec(
            select(
                PublicSubmissions.id,
                PublicSubmissions.status,
                PublicSubmissions.location,
                PublicSubmissions.mobile,
                PublicSubmissions.birth_marks,
                PublicSubmissions.submitted_on,
                PublicSubmissions.submitted_by,
            )
        ).all()
        return result


def get_not_confirmed_registered_cases(submitted_by: str):
    with Session(engine) as session:
        result = session.query(RegisteredCases).all()
        return result


def get_training_data(submitted_by: str):
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases.id, RegisteredCases.face_mesh)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == "NF")
        ).all()
        return result


def new_public_case(public_case_details: PublicSubmissions):
    with Session(engine) as session:
        session.add(public_case_details)
        session.commit()
    return None


def get_public_case_detail(case_id: str):
    with Session(engine) as session:
        result = session.exec(
            select(
                PublicSubmissions.location,
                PublicSubmissions.submitted_by,
                PublicSubmissions.mobile,
                PublicSubmissions.birth_marks,
            ).where(PublicSubmissions.id == case_id)
        ).all()
        return result


def get_registered_case_detail(case_id: str):
    print(case_id)
    with Session(engine) as session:
        result = session.exec(
            select(
                RegisteredCases.name,
                RegisteredCases.complainant_mobile,
                RegisteredCases.age,
                RegisteredCases.last_seen,
                RegisteredCases.birth_marks,
            ).where(RegisteredCases.id == case_id)
        ).all()
        print(result)
        return result


def list_public_cases():
    with Session(engine) as session:
        result = session.exec(select(PublicSubmissions)).all()
        return result


def fetch_public_sightings(status: str | None = None):
    """Return public submissions as model objects, optionally filtered by status."""
    with Session(engine) as session:
        query = select(PublicSubmissions)
        if status:
            query = query.where(PublicSubmissions.status == status)
        return session.exec(query).all()


def fetch_active_missing_cases():
    """Return Not Found registered cases ordered by newest first."""
    with Session(engine) as session:
        return session.exec(
            select(RegisteredCases)
            .where(RegisteredCases.status == "NF")
            .order_by(RegisteredCases.submitted_on.desc())
        ).all()


def fetch_combined_not_found_cases():
    with Session(engine) as session:
        reg_cases = session.exec(
            select(RegisteredCases).where(RegisteredCases.status == "NF")
        ).all()
        pub_cases = session.exec(
            select(PublicSubmissions)
            .where(PublicSubmissions.status == "NF")
            .where(
                (PublicSubmissions.linked_case_id == None) |
                (PublicSubmissions.linked_case_id == "")
            )  # 👈 exclude sightings linked to existing cases
        ).all()

    merged = []

    for c in reg_cases:
        merged.append(
            {
                "source": "registered",
                "id": c.id,
                "display_name": c.name,
                "age": c.age,
                "last_seen": c.last_seen,
                "birth_marks": c.birth_marks,
                "submitted_on": c.submitted_on,
            }
        )

    for p in pub_cases:
        merged.append(
            {
                "source": "public",
                "id": p.id,
                "display_name": p.submitted_by if p.submitted_by else "Public report",
                "age": "",
                "last_seen": p.location,
                "birth_marks": p.birth_marks,
                "submitted_on": p.submitted_on,
            }
        )

    merged.sort(key=lambda x: x.get("submitted_on"), reverse=True)
    return merged


def update_found_status(register_case_id: str, public_case_id: str):
    with Session(engine) as session:
        registered_case_details = session.exec(
            select(RegisteredCases).where(RegisteredCases.id == str(register_case_id))
        ).one()
        registered_case_details.status = "F"
        registered_case_details.matched_with = str(public_case_id)

        public_case_details = session.exec(
            select(PublicSubmissions).where(PublicSubmissions.id == str(public_case_id))
        ).one()
        public_case_details.status = "F"

        session.add(registered_case_details)
        session.add(public_case_details)
        session.commit()


def get_registered_cases_count(submitted_by: str, status: str):
    create_db()

    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == status)
        ).all()
        return result
    
# ==================== NOTIFICATION SUBSCRIBER FUNCTIONS ====================
# ADD THESE AT THE END OF db_queries.py

def add_subscriber(subscriber):
    """Add a new notification subscriber"""
    with Session(engine) as session:
        session.add(subscriber)
        session.commit()


def get_subscribers_by_area(area: str):
    """
    Get all active subscribers for a specific area
    
    Args:
        area: Location/area (e.g., "Delhi", "Mumbai")
        
    Returns:
        List of NotificationSubscribers
    """
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        result = session.exec(
            select(NotificationSubscribers)
            .where(NotificationSubscribers.area == area)
            .where(NotificationSubscribers.is_active == True)
        ).all()
        return result


def get_all_subscribers():
    """Get all subscribers (active and inactive)"""
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        result = session.exec(select(NotificationSubscribers)).all()
        return result


def get_subscriber_by_email(email: str):
    """Get subscriber by email address"""
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        result = session.exec(
            select(NotificationSubscribers)
            .where(NotificationSubscribers.email == email)
        ).first()
        return result


def unsubscribe_user(email: str):
    """Unsubscribe a user from notifications"""
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        subscriber = session.exec(
            select(NotificationSubscribers)
            .where(NotificationSubscribers.email == email)
        ).first()
        
        if subscriber:
            subscriber.is_active = False
            session.add(subscriber)
            session.commit()
            return True
        return False


def resubscribe_user(email: str):
    """Reactivate a subscription"""
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        subscriber = session.exec(
            select(NotificationSubscribers)
            .where(NotificationSubscribers.email == email)
        ).first()
        
        if subscriber:
            subscriber.is_active = True
            session.add(subscriber)
            session.commit()
            return True
        return False


def get_subscriber_count_by_area():
    """Get count of active subscribers per area"""
    from pages.helper.data_models import NotificationSubscribers
    
    with Session(engine) as session:
        subscribers = session.exec(
            select(NotificationSubscribers)
            .where(NotificationSubscribers.is_active == True)
        ).all()
        
        counts = {}
        for sub in subscribers:
            counts[sub.area] = counts.get(sub.area, 0) + 1
        
        return counts


if __name__ == "__main__":
    # Test connection
    print("Testing database connection...")
    create_db()
    print("✅ Connection successful!")
