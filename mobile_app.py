
# import uuid
# import json
# import re
# import io

# import streamlit as st
# import numpy as np

# from pages.helper import db_queries, email_service
# from pages.helper.data_models import PublicSubmissions, NotificationSubscribers
# from pages.helper.case_views import render_public_submission_card
# from pages.helper.utils import (
#     image_obj_to_numpy,
#     extract_face_mesh_landmarks,
#     check_duplicate_public_case,
#     check_against_registered_cases,   # 🔥 NEW
#     extract_face_embedding,
# )
# from sqlmodel import Session, select

# st.set_page_config("Missing Persons Portal", initial_sidebar_state="expanded")


# def apply_ui_theme():
#     st.markdown(
#         """
#         <style>
#             .portal-banner {
#                 border-radius: 12px;
#                 padding: 0.9rem 1rem;
#                 background: linear-gradient(90deg, #0f766e 0%, #0ea5e9 100%);
#                 color: #ffffff;
#                 margin-bottom: 0.8rem;
#             }
#             .panel {
#                 border: 1px solid #e2e8f0;
#                 border-radius: 10px;
#                 padding: 0.8rem;
#                 background: #f8fafc;
#             }
#             .sighting-card {
#                 border: 1px solid #e2e8f0;
#                 border-radius: 12px;
#                 padding: 1rem 1.2rem;
#                 background: #ffffff;
#                 margin-bottom: 1rem;
#                 box-shadow: 0 1px 4px rgba(0,0,0,0.06);
#             }
#             .sighting-badge {
#                 display: inline-block;
#                 background: #e0f2fe;
#                 color: #0369a1;
#                 border-radius: 999px;
#                 padding: 2px 10px;
#                 font-size: 0.78rem;
#                 font-weight: 600;
#                 margin-bottom: 0.4rem;
#             }
#             .sighting-location {
#                 font-size: 1.05rem;
#                 font-weight: 600;
#                 color: #0f172a;
#             }
#             .sighting-meta {
#                 color: #64748b;
#                 font-size: 0.85rem;
#                 margin-top: 0.2rem;
#             }
#             .case-card {
#                 border: 1px solid #e2e8f0;
#                 border-radius: 14px;
#                 padding: 1rem;
#                 background: #fff;
#                 margin-bottom: 1.2rem;
#                 box-shadow: 0 1px 6px rgba(0,0,0,0.05);
#             }
#             .already-registered-box {
#                 border: 2px solid #f59e0b;
#                 border-radius: 12px;
#                 padding: 1rem 1.2rem;
#                 background: #fffbeb;
#                 margin-top: 1rem;
#             }
#             .already-registered-box h4 {
#                 color: #92400e;
#                 margin-bottom: 0.5rem;
#             }
#             .detail-row {
#                 font-size: 0.92rem;
#                 color: #1e293b;
#                 margin-bottom: 0.25rem;
#             }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )


# # ---------------- VALIDATION ----------------
# def is_valid_name(name):
#     return len(name.strip()) >= 3

# def is_valid_mobile(mobile):
#     return mobile.isdigit() and len(mobile) == 10

# def is_valid_email(email):
#     pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
#     return re.match(pattern, email)


# # ---------------- SIDEBAR ----------------
# apply_ui_theme()
# st.sidebar.title("📱 Public Portal")
# page = st.sidebar.radio("Navigate", [
#     "Submit Sighting",
#     "View Missing Persons",
#     "View Sightings",
#     "Subscribe Alerts"
# ])


# # ==================== PAGE 1: SUBMIT SIGHTING ====================
# if page == "Submit Sighting":
#     st.title("Report a Sighting")
#     st.markdown(
#         '<div class="portal-banner"><b>Community Sighting Form</b><br/>Share accurate details and clear photos to improve matching quality.</div>',
#         unsafe_allow_html=True,
#     )

#     image_col, form_col = st.columns(2)
#     image_obj = None
#     save_flag = 0
#     face_mesh = None
#     face_embedding = None
#     embedding_model = ""
#     embedding_dim = 0
#     embedding_status = "pending"
#     already_registered_case = None   # holds matched registered case if found

#     with image_col:
#         st.markdown('<div class="panel"><b>Step 1: Photo Evidence</b></div>', unsafe_allow_html=True)
#         image_source = st.radio(
#             "Photo Source",
#             ["Upload Image", "Capture Photo"],
#             horizontal=True,
#             key="public_photo_source",
#         )
#         if image_source == "Upload Image":
#             image_obj = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
#         else:
#             image_obj = st.camera_input("Capture Photo")

#         if image_obj:
#             unique_id = str(uuid.uuid4())
#             image_bytes = image_obj.getvalue()
#             with open(f"./resources/{unique_id}.jpg", "wb") as f:
#                 f.write(image_bytes)

#             st.image(image_bytes, width=200)

#             with st.spinner("Analyzing face..."):
#                 image_numpy = image_obj_to_numpy(io.BytesIO(image_bytes))
#                 face_mesh = extract_face_mesh_landmarks(image_numpy)
#                 embedding_result = extract_face_embedding(image_numpy, model_name="Facenet512")
#                 face_embedding = embedding_result.get("embedding")
#                 embedding_model = embedding_result.get("embedding_model", "")
#                 embedding_dim = embedding_result.get("embedding_dim", 0)
#                 embedding_status = embedding_result.get("status", "failed")

#             if face_mesh is None:
#                 st.error("❌ No face detected")
#                 st.stop()
#             elif len(face_mesh) != 1404:
#                 st.error("❌ Invalid face data")
#                 st.stop()
#             else:
#                 st.success("✅ Face detected")
#                 if embedding_status == "success":
#                     st.info(f"Embedding ready ({embedding_dim} dimensions)")
#                 else:
#                     err = embedding_result.get("error", "")
#                     st.warning(
#                         "Embedding generation failed. Submission can still proceed with face mesh."
#                         + (f" DeepFace error: {err}" if err else "")
#                     )

#                 # 🔥 CHECK AGAINST REGISTERED CASES RIGHT AFTER FACE IS DETECTED
#                 with st.spinner("Checking existing records..."):
#                     reg_check = check_against_registered_cases(
#                         face_mesh=face_mesh,
#                         face_embedding=face_embedding,
#                         embedding_model=embedding_model,
#                     )

#                 if reg_check.get("match"):
#                     already_registered_case = reg_check.get("case")

#     # 🔥 IF ALREADY A REGISTERED CASE — show details and block the form
#     if already_registered_case:
#         c = already_registered_case
#         st.markdown("---")
#         st.warning("⚠️ This person is **already registered** as a missing case.")
#         st.markdown(
#             f"""
#             <div class="already-registered-box">
#                 <h4>📋 Existing Missing Case Found</h4>
#                 <div class="detail-row">👤 <b>Name:</b> {c.get('name', 'N/A')}</div>
#                 <div class="detail-row">🎂 <b>Age:</b> {c.get('age', 'N/A')}</div>
#                 <div class="detail-row">📍 <b>Last Seen:</b> {c.get('last_seen', 'N/A')}</div>
#                 <div class="detail-row">🏠 <b>Address:</b> {c.get('address', 'N/A')}</div>
#                 <div class="detail-row">🔖 <b>Identifying Marks:</b> {c.get('birth_marks', 'N/A')}</div>
#                 <div class="detail-row">📞 <b>Contact (Complainant):</b> {c.get('contact', 'N/A')}</div>
                
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )
#         st.info("💡 If you have **seen this person**, go to **View Missing Persons** to report a sighting linked to this case.")

#     # ✅ SHOW FORM ONLY IF NOT ALREADY REGISTERED
#     elif image_obj and face_mesh:
#         with form_col.form("submit"):
#             st.markdown("**Step 2: Sighting Details**")

#             name = st.text_input("Your Name *")
#             mobile = st.text_input("Mobile *")
#             email = st.text_input("Email (Optional)")
#             location = st.text_input("Location *")
#             birth_marks = st.text_input("Features / Identifying Marks")

#             submit = st.form_submit_button("Submit Sighting", use_container_width=True)

#             if submit:
#                 if not name or not mobile or not location:
#                     st.error("⚠️ Fill required fields")
#                 elif not is_valid_name(name):
#                     st.error("⚠️ Name too short")
#                 elif not is_valid_mobile(mobile):
#                     st.error("⚠️ Invalid mobile — must be 10 digits")
#                 elif email and not is_valid_email(email):
#                     st.error("⚠️ Invalid email")
#                 else:
#                     result = check_duplicate_public_case(
#                         face_mesh=face_mesh,
#                         name=name,
#                         face_embedding=face_embedding,
#                         embedding_model=embedding_model,
#                     )

#                     if result.get("match"):
#                         st.warning("⚠️ Similar public report already exists!")
#                         st.write(f"Similarity distance: {round(result.get('distance', 0), 2)}")
#                         if result.get("name_match"):
#                             st.success("✔ Name also matches")
#                         else:
#                             st.info("Name does not match — please verify")
#                         confirm = st.checkbox("I still want to submit this report")
#                         if confirm:
#                             data = PublicSubmissions(
#                                 id=unique_id,
#                                 submitted_by=name.strip(),
#                                 location=location.strip(),
#                                 email=email.strip().lower() if email else "",
#                                 face_mesh=json.dumps(face_mesh),
#                                 face_embedding=json.dumps(face_embedding) if face_embedding else None,
#                                 embedding_model=embedding_model,
#                                 embedding_dim=embedding_dim,
#                                 embedding_status=embedding_status,
#                                 mobile=mobile,
#                                 birth_marks=birth_marks if birth_marks else "",
#                                 status="NF",
#                             )
#                             db_queries.new_public_case(data)
#                             saved_location = location.strip()
#                             saved_name = name.strip()
#                             saved_mobile = mobile
#                             saved_birthmarks = birth_marks if birth_marks else ""
#                             save_flag = 1
#                     else:
#                         data = PublicSubmissions(
#                             id=unique_id,
#                             submitted_by=name.strip(),
#                             location=location.strip(),
#                             email=email.strip().lower() if email else "",
#                             face_mesh=json.dumps(face_mesh),
#                             face_embedding=json.dumps(face_embedding) if face_embedding else None,
#                             embedding_model=embedding_model,
#                             embedding_dim=embedding_dim,
#                             embedding_status=embedding_status,
#                             mobile=mobile,
#                             birth_marks=birth_marks if birth_marks else "",
#                             status="NF",
#                             linked_case_id=""
#                         )
#                         db_queries.new_public_case(data)
#                         saved_location = location.strip()
#                         saved_name = name.strip()
#                         saved_mobile = mobile
#                         saved_birthmarks = birth_marks if birth_marks else ""
#                         save_flag = 1

#         if save_flag:
#             st.success("✅ Submitted successfully!")
#             st.balloons()
#         #     try:
#         #         mail_result = email_service.send_sighting_alert({
#         #             "location": saved_location,
#         #             "reported_by": saved_name,
#         #             "mobile": saved_mobile,
#         #             "features": saved_birthmarks
#         #         })
#         #         if mail_result and mail_result.get("status"):
#         #             st.info(f"📧 Alert sent to {mail_result.get('sent_count', 0)} subscriber(s).")
#         #         else:
#         #             st.warning(f"📧 Alert not sent: {mail_result.get('error', 'unknown') if mail_result else 'unknown'}")
#         #     except:
#         #         pass


# # ==================== PAGE 2: VIEW MISSING PERSONS ====================
# elif page == "View Missing Persons":
#     st.title("🔍 Missing Persons")
#     st.caption("Active cases. If you've seen someone, click Report to submit a sighting.")

#     from pages.helper.db_queries import engine
#     cases = db_queries.fetch_combined_not_found_cases()

#     if len(cases) == 0:
#         st.info("No active missing cases at this time.")
#     else:
#         for c in cases:
#             with st.container():
#                 st.markdown('<div class="case-card">', unsafe_allow_html=True)
#                 col1, col2, col3 = st.columns([1, 2, 1])

#                 with col1:
#                     try:
#                         st.image(f"./resources/{c['id']}.jpg", width=120)
#                     except:
#                         st.caption("No image")

#                 with col2:
#                     source_label = "🏛️ Admin Case" if c["source"] == "registered" else "👤 Public Case"
#                     st.caption(source_label)
#                     st.subheader(c["display_name"])
#                     if c.get("age") not in [None, ""]:
#                         st.write(f"**Age:** {c['age']}")
#                     if c.get("last_seen"):
#                         st.write(f"**Last Seen:** {c['last_seen']}")
#                     if c.get("birth_marks"):
#                         st.write(f"**Features:** {c['birth_marks']}")

#                     if c["source"] == "registered":
#                         from pages.helper.data_models import PublicSubmissions
#                         with Session(engine) as session:
#                             sightings = session.exec(
#                                 select(PublicSubmissions)
#                                 .where(PublicSubmissions.linked_case_id == c["id"])
#                             ).all()
#                         if sightings:
#                             st.write(f"📍 **Last seen at:**")
#                             for s in sightings[-2:]:
#                                 st.write(f"• {s.location} _(reported by {s.submitted_by}, 📞 {s.mobile})_")

#                 with col3:
#                     if c["source"] == "registered":
#                         if st.button("📍 Report Sighting", key=f"report_{c['id']}"):
#                             current = st.session_state.get(f"show_form_{c['id']}", False)
#                             st.session_state[f"show_form_{c['id']}"] = not current

#                 st.markdown('</div>', unsafe_allow_html=True)

#             if c["source"] == "registered" and st.session_state.get(f"show_form_{c['id']}"):
#                 with st.form(key=f"sighting_form_{c['id']}"):
#                     st.info(f"📋 Report sighting for **{c['display_name']}**")

#                     loc = st.text_input("Location *", key=f"loc_{c['id']}")
#                     details = st.text_input("Details / Features", key=f"det_{c['id']}")
#                     mob = st.text_input("Your Mobile *", key=f"mob_{c['id']}")
#                     image = st.file_uploader("Photo (Optional)", type=["jpg","jpeg","png"], key=f"img_{c['id']}")

#                     form_submit = st.form_submit_button("✅ Submit Sighting", use_container_width=True)

#                     if form_submit:
#                         if not loc or not mob:
#                             st.error("⚠️ Location and Mobile are required")
#                         elif not mob.isdigit() or len(mob) != 10:
#                             st.error("⚠️ Invalid mobile number")
#                         else:
#                             sight_id = str(uuid.uuid4())
#                             sight_face_mesh = None
#                             sight_embedding_result = {
#                                 "embedding": None,
#                                 "embedding_model": "",
#                                 "embedding_dim": 0,
#                                 "status": "pending"
#                             }

#                             if image:
#                                 image_bytes = image.getvalue()
#                                 with open(f"./resources/{sight_id}.jpg", "wb") as f:
#                                     f.write(image_bytes)
#                                 img_np = image_obj_to_numpy(io.BytesIO(image_bytes))
#                                 mesh = extract_face_mesh_landmarks(img_np)
#                                 sight_embedding_result = extract_face_embedding(img_np, model_name="Facenet512")
#                                 if mesh:
#                                     sight_face_mesh = json.dumps(mesh)

#                             if sight_face_mesh and image:
#                                 duplicate = check_duplicate_public_case(
#                                     face_mesh=mesh,
#                                     name="Public User",
#                                     face_embedding=sight_embedding_result.get("embedding"),
#                                     embedding_model=sight_embedding_result.get("embedding_model", ""),
#                                 )
#                                 if duplicate.get("match"):
#                                     st.warning("⚠️ Similar sighting already exists.")
#                                     st.info(f"Distance: {round(duplicate.get('distance', 0), 3)}")
#                                     st.stop()

#                             data = PublicSubmissions(
#                                 id=sight_id,
#                                 submitted_by="Public User",
#                                 location=loc,
#                                 email="",
#                                 face_mesh=sight_face_mesh if sight_face_mesh else None,
#                                 face_embedding=json.dumps(sight_embedding_result.get("embedding")) if image and sight_embedding_result.get("embedding") else None,
#                                 embedding_model=sight_embedding_result.get("embedding_model", "") if image else "",
#                                 embedding_dim=sight_embedding_result.get("embedding_dim", 0) if image else 0,
#                                 embedding_status=sight_embedding_result.get("status", "pending") if image else "pending",
#                                 mobile=mob,
#                                 birth_marks=details if details else "",
#                                 status="NF",
#                                 linked_case_id=c["id"]
#                             )
#                             db_queries.new_public_case(data)
#                             st.success("✅ Sighting submitted!")
#                             st.session_state[f"show_form_{c['id']}"] = False
#                             st.rerun()

#             st.write("---")


# # ==================== PAGE 3: VIEW SIGHTINGS ====================
# elif page == "View Sightings":
#     st.title("👁️ Community Sightings")
#     st.caption("All crowd-sourced sighting reports submitted by the public.")

#     data = db_queries.fetch_public_sightings()

#     if not data:
#         st.info("No sightings reported yet.")
#     else:
#         st.markdown(f"**{len(data)} sighting(s) on record**")
#         st.write("")

#         for s in data:
#             with st.container():
#                 st.markdown('<div class="sighting-card">', unsafe_allow_html=True)
#                 col1, col2 = st.columns([1, 3])

#                 with col1:
#                     try:
#                         sid = s.id if hasattr(s, 'id') else s.get('id', '')
#                         st.image(f"./resources/{sid}.jpg", width=90)
#                     except:
#                         st.markdown("📷")

#                 with col2:
#                     location   = s.location if hasattr(s, 'location') else s.get('location', 'Unknown')
#                     submitted_by = s.submitted_by if hasattr(s, 'submitted_by') else s.get('submitted_by', 'Anonymous')
#                     mobile     = s.mobile if hasattr(s, 'mobile') else s.get('mobile', '')
#                     birth_marks = s.birth_marks if hasattr(s, 'birth_marks') else s.get('birth_marks', '')
#                     status     = s.status if hasattr(s, 'status') else s.get('status', 'NF')
#                     linked     = s.linked_case_id if hasattr(s, 'linked_case_id') else s.get('linked_case_id', '')

#                     status_label = "🟢 Matched" if status == "F" else "🔴 Unmatched"
#                     st.markdown(f'<span class="sighting-badge">{status_label}</span>', unsafe_allow_html=True)
#                     st.markdown(f'<div class="sighting-location">📍 {location}</div>', unsafe_allow_html=True)
#                     st.markdown(
#                         f'<div class="sighting-meta">Reported by: <b>{submitted_by}</b> &nbsp;|&nbsp; 📞 {mobile}</div>',
#                         unsafe_allow_html=True
#                     )
#                     if birth_marks:
#                         st.markdown(f'<div class="sighting-meta">Features: {birth_marks}</div>', unsafe_allow_html=True)
#                     if linked:
#                         st.markdown(f'<div class="sighting-meta">🔗 Linked to case: {linked[:8]}...</div>', unsafe_allow_html=True)

#                 st.markdown('</div>', unsafe_allow_html=True)


# # ==================== PAGE 4: SUBSCRIBE ALERTS ====================
# elif page == "Subscribe Alerts":
#     st.title("📬 Subscribe for Alerts")
#     st.caption("Get notified when new missing-person alerts are posted for your area.")

#     with st.form("subscribe"):
#         name = st.text_input("Name *")
#         email = st.text_input("Email *")
#         area = st.selectbox("Area", [
#             "Delhi", "Mumbai", "Noida", "Gurgaon",
#             "Bangalore", "Hyderabad", "Chennai",
#             "Pune", "Kolkata"
#         ])

#         submit = st.form_submit_button("Subscribe", use_container_width=True)

#         if submit:
#             if not name or not email:
#                 st.error("⚠️ Fill all fields")
#             elif not is_valid_name(name):
#                 st.error("⚠️ Name too short")
#             elif not is_valid_email(email):
#                 st.error("⚠️ Invalid email")
#             else:
#                 with Session(db_queries.engine) as session:
#                     existing = session.exec(
#                         select(NotificationSubscribers)
#                         .where(NotificationSubscribers.email == email)
#                         .where(NotificationSubscribers.is_active == True)
#                     ).first()

#                     if existing:
#                         st.warning("⚠️ This email is already subscribed.")
#                     else:
#                         sub = NotificationSubscribers(
#                             id=str(uuid.uuid4()),
#                             name=name.strip(),
#                             email=email.strip().lower(),
#                             area=area,
#                             is_active=True
#                         )
#                         session.add(sub)
#                         session.commit()

#                         st.success("✅ Subscribed successfully!")
#                         st.balloons()

#                         try:
#                             mail_result = email_service.send_subscription_confirmation(email, area)
#                             if mail_result and mail_result.get("status"):
#                                 st.info("📧 Confirmation email sent.")
#                             else:
#                                 st.warning(
#                                     f"📧 Subscribed, but email not sent: "
#                                     f"{mail_result.get('error', 'unknown') if mail_result else 'unknown'}"
#                                 )
#                         except:
#                             pass


import uuid
import json
import re
import io
import random
import time

import streamlit as st
import numpy as np

from pages.helper import db_queries, email_service
from pages.helper.data_models import PublicSubmissions, NotificationSubscribers
from pages.helper.case_views import render_public_submission_card
from pages.helper.utils import (
    image_obj_to_numpy,
    extract_face_mesh_landmarks,
    check_duplicate_public_case,
    check_against_registered_cases,
    extract_face_embedding,
)
from sqlmodel import Session, select

st.set_page_config("Missing Persons Portal", initial_sidebar_state="expanded")


def apply_ui_theme():
    st.markdown(
        """
        <style>
            .portal-banner {
                border-radius: 12px;
                padding: 0.9rem 1rem;
                background: linear-gradient(90deg, #0f766e 0%, #0ea5e9 100%);
                color: #ffffff;
                margin-bottom: 0.8rem;
            }
            .panel {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 0.8rem;
                background: #f8fafc;
            }
            .sighting-card {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1rem 1.2rem;
                background: #ffffff;
                margin-bottom: 1rem;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            }
            .sighting-badge {
                display: inline-block;
                background: #e0f2fe;
                color: #0369a1;
                border-radius: 999px;
                padding: 2px 10px;
                font-size: 0.78rem;
                font-weight: 600;
                margin-bottom: 0.4rem;
            }
            .sighting-location {
                font-size: 1.05rem;
                font-weight: 600;
                color: #0f172a;
            }
            .sighting-meta {
                color: #64748b;
                font-size: 0.85rem;
                margin-top: 0.2rem;
            }
            .case-card {
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 1rem;
                background: #fff;
                margin-bottom: 1.2rem;
                box-shadow: 0 1px 6px rgba(0,0,0,0.05);
            }
            .already-registered-box {
                border: 2px solid #f59e0b;
                border-radius: 12px;
                padding: 1rem 1.2rem;
                background: #fffbeb;
                margin-top: 1rem;
            }
            .already-registered-box h4 {
                color: #92400e;
                margin-bottom: 0.5rem;
            }
            .detail-row {
                font-size: 0.92rem;
                color: #1e293b;
                margin-bottom: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------- VALIDATION ----------------
def is_valid_name(name):
    return len(name.strip()) >= 3

def is_valid_mobile(mobile):
    return mobile.isdigit() and len(mobile) == 10

def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)


# ---------------- SIDEBAR ----------------
apply_ui_theme()
st.sidebar.title("📱 Public Portal")
page = st.sidebar.radio("Navigate", [
    "Submit Sighting",
    "View Missing Persons",
    "View Sightings",
    "Subscribe Alerts"
])


# ==================== PAGE 1: SUBMIT SIGHTING ====================
if page == "Submit Sighting":
    st.title("Report a Sighting")
    st.markdown(
        '<div class="portal-banner"><b>Community Sighting Form</b><br/>Share accurate details and clear photos to improve matching quality.</div>',
        unsafe_allow_html=True,
    )

    # ── OTP SESSION STATE INIT ──
    if "otp_verified" not in st.session_state:
        st.session_state.otp_verified = False
    if "otp_code" not in st.session_state:
        st.session_state.otp_code = None
    if "otp_expiry" not in st.session_state:
        st.session_state.otp_expiry = 0
    if "otp_email" not in st.session_state:
        st.session_state.otp_email = ""

    image_col, form_col = st.columns(2)
    image_obj = None
    face_mesh = None
    face_embedding = None
    embedding_model = ""
    embedding_dim = 0
    embedding_status = "pending"
    already_registered_case = None
    unique_id = None

    with image_col:
        st.markdown('<div class="panel"><b>Step 1: Photo Evidence</b></div>', unsafe_allow_html=True)
        image_source = st.radio(
            "Photo Source",
            ["Upload Image", "Capture Photo"],
            horizontal=True,
            key="public_photo_source",
        )
        if image_source == "Upload Image":
            image_obj = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
        else:
            image_obj = st.camera_input("Capture Photo")

        if image_obj:
            unique_id = str(uuid.uuid4())
            image_bytes = image_obj.getvalue()
            with open(f"./resources/{unique_id}.jpg", "wb") as f:
                f.write(image_bytes)

            st.image(image_bytes, width=200)

            with st.spinner("Analyzing face..."):
                image_numpy = image_obj_to_numpy(io.BytesIO(image_bytes))
                face_mesh = extract_face_mesh_landmarks(image_numpy)
                embedding_result = extract_face_embedding(image_numpy, model_name="Facenet512")
                face_embedding = embedding_result.get("embedding")
                embedding_model = embedding_result.get("embedding_model", "")
                embedding_dim = embedding_result.get("embedding_dim", 0)
                embedding_status = embedding_result.get("status", "failed")

            if face_mesh is None:
                st.error("❌ No face detected")
                st.stop()
            elif len(face_mesh) != 1404:
                st.error("❌ Invalid face data")
                st.stop()
            else:
                st.success("✅ Face detected")
                if embedding_status == "success":
                    st.info(f"Embedding ready ({embedding_dim} dimensions)")
                else:
                    err = embedding_result.get("error", "")
                    st.warning(
                        "Embedding generation failed. Submission can still proceed with face mesh."
                        + (f" DeepFace error: {err}" if err else "")
                    )

                with st.spinner("Checking existing records..."):
                    reg_check = check_against_registered_cases(
                        face_mesh=face_mesh,
                        face_embedding=face_embedding,
                        embedding_model=embedding_model,
                    )

                if reg_check.get("match"):
                    already_registered_case = reg_check.get("case")

    # ── IF ALREADY A REGISTERED CASE — show details and block the form ──
    if already_registered_case:
        c = already_registered_case
        st.markdown("---")
        st.warning("⚠️ This person is **already registered** as a missing case.")
        st.markdown(
            f"""
            <div class="already-registered-box">
                <h4>📋 Existing Missing Case Found</h4>
                <div class="detail-row">👤 <b>Name:</b> {c.get('name', 'N/A')}</div>
                <div class="detail-row">🎂 <b>Age:</b> {c.get('age', 'N/A')}</div>
                <div class="detail-row">📍 <b>Last Seen:</b> {c.get('last_seen', 'N/A')}</div>
                <div class="detail-row">🏠 <b>Address:</b> {c.get('address', 'N/A')}</div>
                <div class="detail-row">🔖 <b>Identifying Marks:</b> {c.get('birth_marks', 'N/A')}</div>
                <div class="detail-row">📞 <b>Contact (Complainant):</b> {c.get('contact', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("💡 If you have **seen this person**, go to **View Missing Persons** to report a sighting linked to this case.")

    # ── SHOW FORM ONLY IF FACE DETECTED AND NOT ALREADY REGISTERED ──
    elif image_obj and face_mesh:
        with form_col:
            st.markdown("**Step 2: Verify Email & Submit**")

            name      = st.text_input("Your Name *", key="pub_name")
            mobile    = st.text_input("Mobile *", key="pub_mobile")
            email     = st.text_input("Email * (OTP will be sent here)", key="pub_email")
            location  = st.text_input("Location *", key="pub_location")
            birth_marks = st.text_input("Features / Identifying Marks", key="pub_bm")

            # ── SEND OTP ──
            if not st.session_state.otp_verified:
                if st.button("📧 Send OTP", use_container_width=True):
                    if not name or not mobile or not location:
                        st.error("⚠️ Fill Name, Mobile and Location before sending OTP")
                    elif not is_valid_name(name):
                        st.error("⚠️ Name too short (min 3 characters)")
                    elif not is_valid_mobile(mobile):
                        st.error("⚠️ Invalid mobile — must be 10 digits")
                    elif not email or not is_valid_email(email):
                        st.error("⚠️ Enter a valid email to receive OTP")
                    else:
                        otp = str(random.randint(100000, 999999))
                        result = email_service.send_otp_email(email.strip().lower(), otp)
                        if result.get("status"):
                            st.session_state.otp_code   = otp
                            st.session_state.otp_expiry = time.time() + 300  # 5 minutes
                            st.session_state.otp_email  = email.strip().lower()
                            st.success(f"✅ OTP sent to {email}")
                        else:
                            st.error(f"❌ Failed to send OTP: {result.get('error')}")

                # ── OTP INPUT (shown after OTP is sent) ──
                if st.session_state.otp_code:
                    st.markdown("---")
                    otp_input = st.text_input("Enter 6-digit OTP *", max_chars=6, key="otp_input")
                    col_verify, col_resend = st.columns(2)

                    with col_verify:
                        if st.button("✅ Verify OTP", use_container_width=True):
                            if time.time() > st.session_state.otp_expiry:
                                st.error("⏰ OTP expired. Please click Send OTP again.")
                                st.session_state.otp_code = None
                            elif otp_input == st.session_state.otp_code:
                                st.session_state.otp_verified = True
                                st.success("✅ Email verified!")
                                st.rerun()
                            else:
                                st.error("❌ Incorrect OTP. Try again.")

                    with col_resend:
                        if st.button("🔄 Resend OTP", use_container_width=True):
                            otp = str(random.randint(100000, 999999))
                            result = email_service.send_otp_email(st.session_state.otp_email, otp)
                            if result.get("status"):
                                st.session_state.otp_code   = otp
                                st.session_state.otp_expiry = time.time() + 300
                                st.success("✅ New OTP sent!")
                            else:
                                st.error(f"❌ {result.get('error')}")

            # ── SUBMIT (only after OTP verified) ──
            if st.session_state.otp_verified:
                st.success(f"✅ Email verified: {st.session_state.otp_email}")
                st.markdown("---")

                if st.button("🚀 Submit Sighting", use_container_width=True, type="primary"):

                    def do_save():
                        data = PublicSubmissions(
                            id=unique_id,
                            submitted_by=name.strip(),
                            location=location.strip(),
                            email=st.session_state.otp_email,
                            face_mesh=json.dumps(face_mesh),
                            face_embedding=json.dumps(face_embedding) if face_embedding else None,
                            embedding_model=embedding_model,
                            embedding_dim=embedding_dim,
                            embedding_status=embedding_status,
                            mobile=mobile,
                            birth_marks=birth_marks if birth_marks else "",
                            status="NF",
                            linked_case_id=None,
                        )
                        db_queries.new_public_case(data)
                        # Reset OTP state after successful submit
                        st.session_state.otp_verified = False
                        st.session_state.otp_code     = None
                        st.session_state.otp_email    = ""

                    dup_result = check_duplicate_public_case(
                        face_mesh=face_mesh,
                        name=name,
                        face_embedding=face_embedding,
                        embedding_model=embedding_model,
                    )

                    if dup_result.get("match"):
                        st.warning("⚠️ Similar public report already exists!")
                        st.write(f"Similarity distance: {round(dup_result.get('distance', 0), 2)}")
                        if dup_result.get("name_match"):
                            st.success("✔ Name also matches")
                        else:
                            st.info("Name does not match — please verify")
                        confirm = st.checkbox("I still want to submit this report", key="confirm_dup")
                        if confirm:
                            do_save()
                            st.success("✅ Submitted!")
                            st.balloons()
                    else:
                        do_save()
                        st.success("✅ Submitted successfully!")
                        st.balloons()
                        try:
                            email_service.send_sighting_alert({
                                "location": location.strip(),
                                "reported_by": name.strip(),
                                "mobile": mobile,
                                "features": birth_marks
                            })
                        except:
                            pass


# ==================== PAGE 2: VIEW MISSING PERSONS ====================
elif page == "View Missing Persons":
    st.title("🔍 Missing Persons")
    st.caption("Active cases. If you've seen someone, click Report to submit a sighting.")

    from pages.helper.db_queries import engine
    cases = db_queries.fetch_combined_not_found_cases()

    if len(cases) == 0:
        st.info("No active missing cases at this time.")
    else:
        for c in cases:
            with st.container():
                st.markdown('<div class="case-card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1, 2, 1])

                with col1:
                    try:
                        st.image(f"./resources/{c['id']}.jpg", width=120)
                    except:
                        st.caption("No image")

                with col2:
                    source_label = "🏛️ Admin Case" if c["source"] == "registered" else "👤 Public Case"
                    st.caption(source_label)
                    st.subheader(c["display_name"])
                    if c.get("age") not in [None, ""]:
                        st.write(f"**Age:** {c['age']}")
                    if c.get("last_seen"):
                        st.write(f"**Last Seen:** {c['last_seen']}")
                    if c.get("birth_marks"):
                        st.write(f"**Features:** {c['birth_marks']}")

                    if c["source"] == "registered":
                        from pages.helper.data_models import PublicSubmissions
                        with Session(engine) as session:
                            sightings = session.exec(
                                select(PublicSubmissions)
                                .where(PublicSubmissions.linked_case_id == c["id"])
                            ).all()
                        if sightings:
                            st.write(f"📍 **Last seen at:**")
                            for s in sightings[-2:]:
                                st.write(f"• {s.location} _(reported by {s.submitted_by}, 📞 {s.mobile})_")

                with col3:
                    if c["source"] == "registered":
                        if st.button("📍 Report Sighting", key=f"report_{c['id']}"):
                            current = st.session_state.get(f"show_form_{c['id']}", False)
                            st.session_state[f"show_form_{c['id']}"] = not current

                st.markdown('</div>', unsafe_allow_html=True)

            if c["source"] == "registered" and st.session_state.get(f"show_form_{c['id']}"):
                with st.form(key=f"sighting_form_{c['id']}"):
                    st.info(f"📋 Report sighting for **{c['display_name']}**")

                    loc     = st.text_input("Location *", key=f"loc_{c['id']}")
                    details = st.text_input("Details / Features", key=f"det_{c['id']}")
                    mob     = st.text_input("Your Mobile *", key=f"mob_{c['id']}")
                    image   = st.file_uploader("Photo (Optional)", type=["jpg","jpeg","png"], key=f"img_{c['id']}")

                    form_submit = st.form_submit_button("✅ Submit Sighting", use_container_width=True)

                    if form_submit:
                        if not loc or not mob:
                            st.error("⚠️ Location and Mobile are required")
                        elif not mob.isdigit() or len(mob) != 10:
                            st.error("⚠️ Invalid mobile number")
                        else:
                            sight_id = str(uuid.uuid4())
                            sight_face_mesh = None
                            sight_embedding_result = {
                                "embedding": None,
                                "embedding_model": "",
                                "embedding_dim": 0,
                                "status": "pending"
                            }

                            if image:
                                image_bytes = image.getvalue()
                                with open(f"./resources/{sight_id}.jpg", "wb") as f:
                                    f.write(image_bytes)
                                img_np = image_obj_to_numpy(io.BytesIO(image_bytes))
                                mesh = extract_face_mesh_landmarks(img_np)
                                sight_embedding_result = extract_face_embedding(img_np, model_name="Facenet512")
                                if mesh:
                                    sight_face_mesh = json.dumps(mesh)

                            if sight_face_mesh and image:
                                duplicate = check_duplicate_public_case(
                                    face_mesh=mesh,
                                    name="Public User",
                                    face_embedding=sight_embedding_result.get("embedding"),
                                    embedding_model=sight_embedding_result.get("embedding_model", ""),
                                )
                                if duplicate.get("match"):
                                    st.warning("⚠️ Similar sighting already exists.")
                                    st.info(f"Distance: {round(duplicate.get('distance', 0), 3)}")
                                    st.stop()

                            data = PublicSubmissions(
                                id=sight_id,
                                submitted_by="Public User",
                                location=loc,
                                email="",
                                face_mesh=sight_face_mesh if sight_face_mesh else None,
                                face_embedding=json.dumps(sight_embedding_result.get("embedding")) if image and sight_embedding_result.get("embedding") else None,
                                embedding_model=sight_embedding_result.get("embedding_model", "") if image else "",
                                embedding_dim=sight_embedding_result.get("embedding_dim", 0) if image else 0,
                                embedding_status=sight_embedding_result.get("status", "pending") if image else "pending",
                                mobile=mob,
                                birth_marks=details if details else "",
                                status="NF",
                                linked_case_id=c["id"]
                            )
                            db_queries.new_public_case(data)
                            st.success("✅ Sighting submitted!")
                            st.session_state[f"show_form_{c['id']}"] = False
                            st.rerun()

            st.write("---")


# ==================== PAGE 3: VIEW SIGHTINGS ====================
elif page == "View Sightings":
    st.title("👁️ Community Sightings")
    st.caption("All crowd-sourced sighting reports submitted by the public.")

    data = db_queries.fetch_public_sightings()

    if not data:
        st.info("No sightings reported yet.")
    else:
        st.markdown(f"**{len(data)} sighting(s) on record**")
        st.write("")

        for s in data:
            with st.container():
                st.markdown('<div class="sighting-card">', unsafe_allow_html=True)
                col1, col2 = st.columns([1, 3])

                with col1:
                    try:
                        sid = s.id if hasattr(s, 'id') else s.get('id', '')
                        st.image(f"./resources/{sid}.jpg", width=90)
                    except:
                        st.markdown("📷")

                with col2:
                    location     = s.location if hasattr(s, 'location') else s.get('location', 'Unknown')
                    submitted_by = s.submitted_by if hasattr(s, 'submitted_by') else s.get('submitted_by', 'Anonymous')
                    mobile       = s.mobile if hasattr(s, 'mobile') else s.get('mobile', '')
                    birth_marks  = s.birth_marks if hasattr(s, 'birth_marks') else s.get('birth_marks', '')
                    status       = s.status if hasattr(s, 'status') else s.get('status', 'NF')
                    linked       = s.linked_case_id if hasattr(s, 'linked_case_id') else s.get('linked_case_id', '')

                    status_label = "🟢 Matched" if status == "F" else "🔴 Unmatched"
                    st.markdown(f'<span class="sighting-badge">{status_label}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="sighting-location">📍 {location}</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="sighting-meta">Reported by: <b>{submitted_by}</b> &nbsp;|&nbsp; 📞 {mobile}</div>',
                        unsafe_allow_html=True
                    )
                    if birth_marks:
                        st.markdown(f'<div class="sighting-meta">Features: {birth_marks}</div>', unsafe_allow_html=True)
                    if linked:
                        st.markdown(f'<div class="sighting-meta">🔗 Linked to case: {linked[:8]}...</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)


# ==================== PAGE 4: SUBSCRIBE ALERTS ====================
elif page == "Subscribe Alerts":
    st.title("📬 Subscribe for Alerts")
    st.caption("Get notified when new missing-person alerts are posted for your area.")

    with st.form("subscribe"):
        name  = st.text_input("Name *")
        email = st.text_input("Email *")
        area  = st.selectbox("Area", [
            "Delhi", "Mumbai", "Noida", "Gurgaon",
            "Bangalore", "Hyderabad", "Chennai",
            "Pune", "Kolkata"
        ])

        submit = st.form_submit_button("Subscribe", use_container_width=True)

        if submit:
            if not name or not email:
                st.error("⚠️ Fill all fields")
            elif not is_valid_name(name):
                st.error("⚠️ Name too short")
            elif not is_valid_email(email):
                st.error("⚠️ Invalid email")
            else:
                with Session(db_queries.engine) as session:
                    existing = session.exec(
                        select(NotificationSubscribers)
                        .where(NotificationSubscribers.email == email)
                        .where(NotificationSubscribers.is_active == True)
                    ).first()

                    if existing:
                        st.warning("⚠️ This email is already subscribed.")
                    else:
                        sub = NotificationSubscribers(
                            id=str(uuid.uuid4()),
                            name=name.strip(),
                            email=email.strip().lower(),
                            area=area,
                            is_active=True
                        )
                        session.add(sub)
                        session.commit()

                        st.success("✅ Subscribed successfully!")
                        st.balloons()

                        try:
                            mail_result = email_service.send_subscription_confirmation(email, area)
                            if mail_result and mail_result.get("status"):
                                st.info("📧 Confirmation email sent.")
                            else:
                                st.warning(
                                    f"📧 Subscribed, but email not sent: "
                                    f"{mail_result.get('error', 'unknown') if mail_result else 'unknown'}"
                                )
                        except:
                            pass