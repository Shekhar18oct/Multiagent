import streamlit as st
import requests

st.set_page_config(page_title="Login | Multi-Agent Code Analysis", layout="centered")
st.title("🔐 Login")

if st.session_state.get("token"):
    st.success(f"Already logged in as **{st.session_state.get('username')}** ({st.session_state.get('role')})")
    if st.button("Logout"):
        for key in ["token", "role", "username"]:
            st.session_state.pop(key, None)
        st.rerun()
else:
    with st.form("login_form"):
        username = st.text_input("Email / Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            try:
                resp = requests.post(
                    "http://localhost:8000/auth/login",
                    json={"username": username, "password": password, "role": "user"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["role"] = data["role"]
                    st.session_state["username"] = username
                    st.success(f"✅ Logged in as **{username}** (role: {data['role']})")
                    st.info("Navigate to **Upload Project** or **Projects** from the sidebar.")
                else:
                    st.error(resp.json().get("detail", "Login failed. Check your credentials."))
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")

    st.markdown("---")
    st.caption("Don't have an account? Go to **Signup** in the sidebar.")
