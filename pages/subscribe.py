# pages/6_Subscribe_to_Alerts.py
"""
Public Subscription Page - Simple
People subscribe with their email + area to get alerts
"""

import streamlit as st
from pages.helper import db_queries
from pages.helper.data_models import NotificationSubscribers
from sqlmodel import Session, select
from uuid import uuid4

st.set_page_config(page_title="Subscribe to Alerts", page_icon="📬")

st.title("📬 Get Missing Person Alerts")

st.write("""
Subscribe to receive email alerts when someone goes missing in your area.  
Help save lives by staying informed.
""")

# Subscription Form
with st.form("subscribe"):
    name = st.text_input("Your Name *", placeholder="Ram Kumar")
    email = st.text_input("Email *", placeholder="ram@gmail.com")
    area = st.selectbox("Area *", [
        "Delhi",
        "Mumbai",
        "Noida",
        "Gurgaon",
        "Bangalore",
        "Hyderabad",
        "Chennai",
        "Pune",
        "Kolkata"
    ])
    
    submit = st.form_submit_button("Subscribe")
    
    if submit:
        if not name or not email:
            st.error("Please fill all fields")
        elif "@" not in email:
            st.error("Invalid email")
        else:
            try:
                # Check if already subscribed
                with Session(db_queries.engine) as session:
                    existing = session.exec(
                        select(NotificationSubscribers)
                        .where(NotificationSubscribers.email == email)
                    ).first()
                    
                    if existing:
                        st.warning("This email is already subscribed!")
                    else:
                        # Add new subscriber
                        new_sub = NotificationSubscribers(
                            id=str(uuid4()),
                            name=name,
                            email=email,
                            area=area,
                            is_active=True
                        )
                        session.add(new_sub)
                        session.commit()
                        
                        st.success(f"✅ Subscribed! You'll get alerts for {area}")
                        st.balloons()
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()

# Unsubscribe
with st.expander("Unsubscribe"):
    unsub_email = st.text_input("Email to unsubscribe")
    if st.button("Unsubscribe"):
        try:
            with Session(db_queries.engine) as session:
                sub = session.exec(
                    select(NotificationSubscribers)
                    .where(NotificationSubscribers.email == unsub_email)
                ).first()
                
                if sub:
                    sub.is_active = False
                    session.add(sub)
                    session.commit()
                    st.success("Unsubscribed successfully")
                else:
                    st.warning("Email not found")
        except Exception as e:
            st.error(str(e))