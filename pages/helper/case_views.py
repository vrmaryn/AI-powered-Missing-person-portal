import streamlit as st


def render_public_submission_card(submission) -> None:
    """Shared UI card for public submissions/sightings."""
    data_col, image_col, _ = st.columns(3)

    status_label = "Found" if getattr(submission, "status", "") == "F" else "Not Found"
    data_col.write(f"Status: {status_label}")
    data_col.write(f"Location: {getattr(submission, 'location', '')}")
    data_col.write(f"Mobile: {getattr(submission, 'mobile', '')}")
    data_col.write(f"Birth Marks: {getattr(submission, 'birth_marks', '')}")
    data_col.write(f"Submitted on: {getattr(submission, 'submitted_on', '')}")
    data_col.write(f"Submitted by: {getattr(submission, 'submitted_by', '')}")

    try:
        image_col.image(f"./resources/{submission.id}.jpg", width=120)
    except Exception:
        image_col.warning("Couldn't load image")

    st.write("---")
