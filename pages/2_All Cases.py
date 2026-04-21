import streamlit as st
from pages.helper import db_queries
from pages.helper.streamlit_helpers import require_login
from pages.helper.case_views import render_public_submission_card


# ---------------- CASE VIEWER ----------------
def case_viewer(case):
    case = list(case)
    case_id = case.pop(0)
    matched_with_id = case.pop(-1)
    matched_with_details = None

    try:
        matched_with_id = matched_with_id.replace("{", "").replace("}", "")
    except:
        matched_with_id = None

    if matched_with_id:
        matched_with_details = db_queries.get_public_case_detail(matched_with_id)

    data_col, image_col, action_col = st.columns(3)

    # Show data
    for text, value in zip(["Name", "Age", "Status", "Last Seen", "Phone"], case):
        if value == "F":
            value = "Found"
        elif value == "NF":
            value = "Not Found"
        data_col.write(f"{text}: {value}")

    # Image
    try:
        image_col.image("./resources/" + str(case_id) + ".jpg", width=120)
    except:
        image_col.warning("Image not found")

    # -------- ACTION BUTTON (OPTION 9) --------
    
    if case[2] == "NF":  # status

        if action_col.button("✅ Mark as Found", key=f"found_{case_id}"):

            try:
                # Case 1: If match exists → use existing function
                if matched_with_id:
                    db_queries.update_found_status(case_id, matched_with_id)

                # Case 2: No match → update manually here
                else:
                    from sqlmodel import Session, select
                    from pages.helper.db_queries import engine
                    from pages.helper.data_models import RegisteredCases

                    with Session(engine) as session:
                        case_obj = session.exec(
                            select(RegisteredCases).where(RegisteredCases.id == str(case_id))
                        ).one()

                        case_obj.status = "F"
                        session.add(case_obj)
                        session.commit()

                st.success("✅ Case marked as Found!")
                st.rerun()

            except Exception as e:
                st.error(f"Error updating case: {str(e)}")


# ---------------- MAIN ----------------
if "login_status" not in st.session_state:
    st.write("You don't have access to this page")

elif st.session_state["login_status"]:
    user = st.session_state.user

    st.title("View Submitted Cases")

    status_col, date_col = st.columns(2)
    status = status_col.selectbox(
        "Filter", options=["All", "Not Found", "Found", "Public Cases"]
    )
    date = date_col.date_input("Date")

    # ---------------- FETCH DATA ----------------
    if status == "Public Cases":
        cases_data = db_queries.fetch_public_sightings()
    else:
        cases_data = db_queries.fetch_registered_cases(user, status)

    # ---------------- DASHBOARD STATS ----------------
    if status != "Public Cases":
        total = len(cases_data)
        found = len([c for c in cases_data if c[3] == "F"])
        not_found = len([c for c in cases_data if c[3] == "NF"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cases", total)
        col2.metric("Found", found)
        col3.metric("Not Found", not_found)

    st.write("---")

    # ---------------- DISPLAY ----------------
    for case in cases_data:
        if status == "Public Cases":
            render_public_submission_card(case)
        else:
            case_viewer(case)

else:
    st.write("You don't have access to this page")