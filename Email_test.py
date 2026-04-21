import streamlit as st

from pages.helper.email_service import _get_email_credentials, _send_email


st.title("Email Test Tool")
st.caption("Use this page to verify SMTP configuration and send a test email.")

sender_email, _, cred_error = _get_email_credentials()
if cred_error:
    st.error(f"Configuration error: {cred_error}")
else:
    st.success(f"Sender loaded: {sender_email}")

with st.form("email_test_form"):
    to_email = st.text_input("Recipient Email", placeholder="test@example.com")
    subject = st.text_input("Subject", value="Test Email from Missing Person App")
    message = st.text_area("Message", value="Hello! This is a test email.")
    submit = st.form_submit_button("Send Test Email")

if submit:
    if not to_email or "@" not in to_email:
        st.error("Enter a valid recipient email.")
    else:
        html_body = f"""
        <html>
        <body style="font-family: Arial; padding: 16px;">
            <h3>{subject}</h3>
            <p>{message}</p>
        </body>
        </html>
        """
        result = _send_email(to_email.strip(), subject.strip(), html_body)
        if result.get("status"):
            st.success(f"Email sent to {to_email.strip()}")
        else:
            st.error(f"Email failed: {result.get('error', 'unknown error')}")
# import streamlit as st
# from pages.helper.email_service import _send_email, _get_email_credentials

# st.set_page_config(page_title="Email Test")
# st.title("📧 Email Test Tool")

# sender_email, _, err = _get_email_credentials()
# if err:
#     st.error(f"Config issue: {err}")
# else:
#     st.success(f"Sender loaded: {sender_email}")

# with st.form("email_test_form"):
#     to_email = st.text_input("Recipient Email", placeholder="test@example.com")
#     subject = st.text_input("Subject", value="Test Email from Missing Person App")
#     body = st.text_area("Message", value="Hello! This is a test email.")
#     submit = st.form_submit_button("Send Test Email")

# if submit:
#     if not to_email or "@" not in to_email:
#         st.error("Enter a valid recipient email.")
#     else:
#         html_body = f"""
#         <html><body style="font-family: Arial; padding: 16px;">
#         <h3>{subject}</h3>
#         <p>{body}</p>
#         </body></html>
#         """
#         result = _send_email(to_email.strip(), subject.strip(), html_body)
#         if result.get("status"):
#             st.success(f"Email sent to {to_email}")
#         else:
#             st.error(f"Email failed: {result.get('error', 'unknown error')}")

