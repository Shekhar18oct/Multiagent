import streamlit as st
import requests

st.set_page_config(page_title="Signup | Multi-Agent Code Analysis", layout="centered")
st.title("📝 Signup")

if st.session_state.get("token"):
    st.success(f"Already logged in as **{st.session_state.get('username')}**.")
    st.info("Navigate using the sidebar.")
else:
    with st.form("signup_form"):
        username = st.text_input("Email / Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submitted = st.form_submit_button("Create Account")

    if submitted:
        if not username or not password:
            st.error("Please fill in all fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                resp = requests.post(
                    "http://localhost:8000/auth/signup",
                    json={"username": username, "password": password, "role": role},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["role"] = data["role"]
                    st.session_state["username"] = username
                    st.success(f"✅ Account created! Logged in as **{username}** (role: {data['role']})")
                    st.info("Navigate to **Upload Project** from the sidebar to get started.")
                else:
                    st.error(resp.json().get("detail", "Signup failed."))
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")

    st.markdown("---")
    st.caption("Already have an account? Go to **Login** in the sidebar.")
