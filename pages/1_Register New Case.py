import uuid
import numpy as np
import streamlit as st
import json
import base64
import io

from pages.helper.data_models import RegisteredCases
from pages.helper import db_queries, email_service
from pages.helper.utils import (
    image_obj_to_numpy,
    extract_face_mesh_landmarks,
    extract_face_embedding,
)

from pages.helper.utils import DeepFaceModelCache
from pages.helper.streamlit_helpers import require_login

st.set_page_config(page_title="Case New Form")


def apply_ui_theme():
    st.markdown(
        """
        <style>
            .section-card {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 0.9rem 1rem;
                background: #f8fafc;
                margin-bottom: 0.75rem;
            }
            .muted-caption {
                color: #64748b;
                font-size: 0.9rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def image_to_base64(image):
    return base64.b64encode(image).decode("utf-8")


# ---------------- AUTH CHECK ----------------

if "login_status" not in st.session_state:
    st.write("You don't have access to this page")

elif st.session_state["login_status"]:
    apply_ui_theme()

    user = st.session_state.user
    st.title("Register New Case")
    st.caption("Upload or capture a clear face photo, then fill case details.")

    image_col, form_col = st.columns(2)
    image_obj = None
    save_flag = 0
    face_mesh = None
    face_embedding = None
    embedding_model = ""
    embedding_dim = 0
    embedding_status = "pending"
    unique_id = None

    # ---------------- IMAGE SECTION ----------------

    with image_col:
        st.markdown('<div class="section-card"><b>Step 1: Add Photo</b><p class="muted-caption">Choose image source and verify face detection.</p></div>', unsafe_allow_html=True)
        image_source = st.radio(
            "Photo Source",
            ["Upload Image", "Capture Photo"],
            horizontal=True,
            key="new_case_photo_source",
        )
        if image_source == "Upload Image":
            image_obj = st.file_uploader(
                "Image", type=["jpg", "jpeg", "png"], key="new_case"
            )
        else:
            image_obj = st.camera_input("Capture Photo", key="new_case_camera")

        if image_obj:
            unique_id = str(uuid.uuid4())
            image_bytes = image_obj.getvalue()
            uploaded_file_path = "./resources/" + unique_id + ".jpg"
            with open(uploaded_file_path, "wb") as output_file:
                output_file.write(image_bytes)

            with st.spinner("Processing..."):
                st.image(image_bytes)
                image_numpy = image_obj_to_numpy(io.BytesIO(image_bytes))
                face_mesh = extract_face_mesh_landmarks(image_numpy)
                embedding_result = extract_face_embedding(image_numpy, model_name="Facenet512")
                face_embedding = embedding_result.get("embedding")
                embedding_model = embedding_result.get("embedding_model", "")
                embedding_dim = embedding_result.get("embedding_dim", 0)
                embedding_status = embedding_result.get("status", "failed")

                # Face validation
                if face_mesh is None:
                    st.error("❌ No face detected. Upload a clear image.")
                    st.stop()

                elif len(face_mesh) != 1404:
                    st.error("❌ Invalid face data.")
                    st.stop()

                else:
                    st.success("✅ Face detected successfully!")
                    if embedding_status == "success":
                        st.info(f"Embedding ready ({embedding_dim} dimensions)")
                    else:
                        err = embedding_result.get("error", "") if "embedding_result" in locals() else ""
                        st.warning(
                            "Embedding generation failed for this image. Case can still be saved with face mesh."
                            + (f" DeepFace error: {err}" if err else "")
                        )

    # ---------------- FORM SECTION ----------------

    if image_obj and face_mesh:
        with form_col.form(key="new_case"):
            st.markdown("**Step 2: Case Details**")

            name = st.text_input("Name *")
            age = st.number_input("Age *", min_value=1, max_value=120, value=25)
            mobile_number = st.text_input("Contact Number *")
            last_seen = st.text_input("Last Seen Location *")

            with st.expander("Additional Details (Optional)", expanded=False):
                fathers_name = st.text_input("Father's Name")
                address = st.text_input("Home Address")
                adhaar_card = st.text_input("Adhaar Card")
                birthmarks = st.text_input("Identifying Marks")
                complainant_name = st.text_input("Complainant Name")

            submit_bt = st.form_submit_button("Register Case", use_container_width=True)

            if submit_bt:

                if not name or not mobile_number or not last_seen:
                    st.error("⚠️ Fill all required fields")

                elif face_mesh is None:
                    st.error("⚠️ Face data missing")

                else:
                    new_case_details = RegisteredCases(
                        id=unique_id,
                        submitted_by=user,
                        name=name.strip(),
                        father_name=fathers_name if fathers_name else "",
                        age=age,
                        complainant_mobile=mobile_number,
                        complainant_name=complainant_name if complainant_name else "",
                        face_mesh=json.dumps(face_mesh),
                        face_embedding=json.dumps(face_embedding) if face_embedding else "",
                        embedding_model=embedding_model,
                        embedding_dim=embedding_dim,
                        embedding_status=embedding_status,
                        adhaar_card=adhaar_card if adhaar_card else "",
                        birth_marks=birthmarks if birthmarks else "",
                        address=address if address else "",
                        last_seen=last_seen.strip().lower(),
                        status="NF",
                        matched_with="",
                    )

                    db_queries.register_new_case(new_case_details)

                    # ✅ Save attributes to plain variables BEFORE session closes
                    saved_name = name.strip()
                    saved_age = age
                    saved_last_seen = last_seen.strip().lower()
                    saved_mobile = mobile_number
                    saved_birthmarks = birthmarks if birthmarks else ""

                    save_flag = 1

        # ---------------- SUCCESS + EMAIL ----------------

        if save_flag:
            st.success("✅ Case Registered Successfully!")
            st.info("💡 You can now check for matches in the 'Match Cases' section")
            st.balloons()

            print("\n" + "="*70)
            print("🔍 DEBUG: About to send email alert...")
            print("="*70)

            try:
                print(f"Case name: {saved_name}")
                print(f"Last seen: {saved_last_seen}")

                mail_result = email_service.send_missing_person_alert({
                    "name": saved_name,
                    "age": saved_age,
                    "last_seen": saved_last_seen,
                    "complainant_mobile": saved_mobile,
                    "birth_marks": saved_birthmarks
                })

                print(f"Email result: {mail_result}")

                if mail_result and mail_result.get("status"):
                    st.success(f"✅ Email sent to {mail_result.get('sent_count')} subscribers")
                else:
                    error = mail_result.get('error', 'unknown') if mail_result else 'no result'
                    st.error(f"❌ Email failed: {error}")

            except Exception as e:
                import traceback
                print(f"❌ EXCEPTION: {e}")
                print(traceback.format_exc())
                st.error(f"❌ Email error: {e}")

    else:
        st.write("You don't have access to this page")