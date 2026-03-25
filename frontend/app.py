import streamlit as st

st.set_page_config(
    page_title="Multi-Agent Code Analysis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Hero Section ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;padding:2rem 0 1rem">
      <h1 style="font-size:3rem;margin-bottom:0.3rem">🤖 Multi-Agent Code Analysis</h1>
      <p style="font-size:1.2rem;color:#888">
        Upload any codebase and let specialised AI agents analyse, document and
        answer questions about it — automatically.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Login Status ───────────────────────────────────────────────────────────────
if st.session_state.get("token"):
    st.success(f"✅ Logged in as **{st.session_state.get('username')}** ({st.session_state.get('role')})")
else:
    st.info("👋 You are not logged in. Use **Login** or **Signup** in the sidebar to get started.")

st.markdown("---")

# ── Feature Cards ──────────────────────────────────────────────────────────────
st.subheader("🚀 What Can You Do Here?")
c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    "### 🔐 Login / Signup\nSecurely sign in or create an account. Roles: **User** & **Admin**."
)
c2.markdown(
    "### 📁 Upload Project\nUpload a ZIP archive or paste a GitHub URL. Configure agent depth, personas & diagrams."
)
c3.markdown(
    "### 🤖 AI Agents\n5 specialised agents: **SDE**, **PM**, **Security**, **Docs**, and **Web-Augmentation**."
)
c4.markdown(
    "### 📂 Projects\nBrowse all your analysed projects, run semantic search, ask Q&A, and control analysis state."
)

st.markdown("---")

# ── Navigation Guide ──────────────────────────────────────────────────────────
st.subheader("📌 Navigation")
st.markdown(
    """
| Sidebar Page | Description |
|---|---|
| 🏠 **Home** _(this page)_ | Overview & login status |
| 🔐 **Login** | Sign in to your account |
| 📝 **Signup** | Create a new account |
| 📁 **Upload Project** | Submit a codebase for analysis |
| 📂 **Projects** | View & interact with analysed projects |
"""
)

st.markdown("---")
st.caption("Multi-Agent Code Analysis System · Built with FastAPI + Streamlit + ChromaDB Cloud")
