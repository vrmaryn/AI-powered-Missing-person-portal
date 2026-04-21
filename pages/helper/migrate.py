"""
Smart Migration Script: SQLite → Supabase
Auto-finds your database file regardless of where you run it from
"""

import os
import sqlite3
from datetime import datetime
from sqlmodel import create_engine, Session, SQLModel, select
from dotenv import load_dotenv
from pathlib import Path

# Import your models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_models import RegisteredCases, PublicSubmissions

load_dotenv()

print("=" * 70)
print("  SQLite → Supabase Migration (Smart)")
print("=" * 70)
print()

# Find SQLite database
print("🔍 Looking for SQLite database...")
possible_paths = [
    "sqlite_database.db",                    # Same directory
    "../sqlite_database.db",                 # Parent directory
    "../../sqlite_database.db",              # Two levels up
    Path(__file__).parent.parent / "sqlite_database.db",  # Project root
]

sqlite_path = None
for path in possible_paths:
    if os.path.exists(path):
        sqlite_path = str(path)
        break

if not sqlite_path:
    print("   ❌ ERROR: sqlite_database.db not found!")
    print("   Searched in:")
    for p in possible_paths:
        print(f"      - {p}")
    print("\n   Please run this script from your project root directory:")
    print("   cd D:\\AI\\Finding-missing-person-using-AI-master")
    print("   python migrate.py")
    exit(1)

print(f"   ✅ Found database: {sqlite_path}")
print()

# Connect to Supabase
print("☁️  Connecting to Supabase...")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("   ❌ ERROR: DATABASE_URL not found in .env file!")
    print("   Make sure you have a .env file with DATABASE_URL")
    exit(1)

supabase_engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
print("   ✅ Supabase connected")
print()

# Create tables in Supabase
# print("🔨 Creating tables in Supabase...")
# try:
#     SQLModel.metadata.create_all(supabase_engine)
#     print("   ✅ Tables created/verified")
# except Exception as e:
#     print(f"   ⚠️  {e}")
# print()

# Connect to SQLite
print("📂 Opening SQLite database...")
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()

# Check what tables exist
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in sqlite_cursor.fetchall()]
print(f"   Found tables: {tables}")
print()

# Migrate RegisteredCases
print("📦 Migrating Registered Cases...")
try:
    sqlite_cursor.execute("SELECT * FROM registeredcases")
    rows = sqlite_cursor.fetchall()
    columns = [desc[0] for desc in sqlite_cursor.description]
    
    print(f"   Found {len(rows)} cases")
    print(f"   Columns: {', '.join(columns)}")
    
    if len(rows) == 0:
        print("   ℹ️  No cases to migrate")
    else:
        migrated = 0
        with Session(supabase_engine) as session:
            for row in rows:
                case_dict = dict(zip(columns, row))
                
                try:
                    new_case = RegisteredCases(
                        id=case_dict.get('id'),
                        submitted_by=case_dict.get('submitted_by', ''),
                        name=case_dict.get('name', ''),
                        fathers_name=case_dict.get('fathers_name') or case_dict.get('father_name', ''),
                        age=case_dict.get('age', 0),
                        complainant_mobile=case_dict.get('complainant_mobile', ''),
                        complainant_name=case_dict.get('complainant_name', ''),
                        face_mesh=case_dict.get('face_mesh', ''),
                        adhaar_card=case_dict.get('adhaar_card', ''),
                        birth_marks=case_dict.get('birth_marks', ''),
                        address=case_dict.get('address', ''),
                        last_seen=case_dict.get('last_seen', ''),
                        status=case_dict.get('status', 'NF'),
                        matched_with=case_dict.get('matched_with', ''),
                        submitted_on=datetime.fromisoformat(case_dict['submitted_on']) if case_dict.get('submitted_on') else datetime.now()
                    )
                    session.add(new_case)
                    migrated += 1
                    print(f"   ✅ {migrated}/{len(rows)}: {case_dict.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"   ⚠️  Skipped case (might be duplicate): {str(e)[:50]}")
            
            session.commit()
        print(f"   ✅ Migrated {migrated} cases")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# Migrate PublicSubmissions
# print("📦 Migrating Public Submissions...")
# try:
#     sqlite_cursor.execute("SELECT * FROM publicsubmissions")
#     rows = sqlite_cursor.fetchall()
#     columns = [desc[0] for desc in sqlite_cursor.description]
    
#     print(f"   Found {len(rows)} submissions")
    
#     if len(rows) == 0:
#         print("   ℹ️  No submissions to migrate")
#     else:
#         migrated = 0
#         with Session(supabase_engine) as session:
#             for row in rows:
#                 sub_dict = dict(zip(columns, row))
                
#                 try:
#                     new_sub = PublicSubmissions(
#                         id=sub_dict.get('id'),
#                         submitted_by=sub_dict.get('submitted_by', ''),
#                         location=sub_dict.get('location', ''),
#                         email=sub_dict.get('email', ''),
#                         mobile=sub_dict.get('mobile', ''),
#                         birth_marks=sub_dict.get('birth_marks', ''),
#                         face_mesh=sub_dict.get('face_mesh', ''),
#                         status=sub_dict.get('status', 'NF'),
#                         submitted_on=datetime.fromisoformat(sub_dict['submitted_on']) if sub_dict.get('submitted_on') else datetime.now()
#                     )
#                     session.add(new_sub)
#                     migrated += 1
#                     print(f"   ✅ {migrated}/{len(rows)}: {sub_dict.get('location', 'Unknown')}")
#                 except Exception as e:
#                     print(f"   ⚠️  Skipped submission (might be duplicate): {str(e)[:50]}")
            
#             session.commit()
#         print(f"   ✅ Migrated {migrated} submissions")
        
# except Exception as e:
#     print(f"   ❌ Error: {e}")
# print()

# sqlite_conn.close()

# Verify
print("🔍 Verifying Supabase data...")
with Session(supabase_engine) as session:
    cases = session.exec(select(RegisteredCases)).all()
    subs = session.exec(select(PublicSubmissions)).all()
    
    print(f"   Supabase now has:")
    print(f"   • {len(cases)} registered cases")
    print(f"   • {len(subs)} public submissions")
    
    if cases:
        print(f"\n   Sample case: {cases[0].name}, Age {cases[0].age}")
    if subs:
        print(f"   Sample submission: Location {subs[0].location}")
print()

# Check resources folder
print("📸 Checking resources folder...")
resources_paths = [
    "./resources",
    "../resources", 
    "../../resources",
    str(Path(__file__).parent.parent / "resources")
]

resources_dir = None
for path in resources_paths:
    if os.path.exists(path):
        resources_dir = path
        break

if resources_dir:
    images = [f for f in os.listdir(resources_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    print(f"   ✅ Found {len(images)} images in {resources_dir}")
else:
    print("   ⚠️  Resources folder not found")
print()

print("=" * 70)
print("✅ MIGRATION COMPLETE!")
print("=" * 70)
print()
print("Next steps:")
print("1. Go to Supabase Dashboard → Table Editor")
print("2. Check 'registered_cases' and 'public_submissions' tables")
print("3. You should see your data there!")
print("4. Update .env: USE_POSTGRES=True")
print("5. Run: streamlit run Home.py")
print()