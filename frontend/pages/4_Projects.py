import streamlit as st
import requests

st.set_page_config(page_title="Projects | Multi-Agent Code Analysis", layout="wide")
st.title("📂 My Projects")

if not st.session_state.get("token"):
    st.warning("⚠️ Please **Login** first (use the sidebar).")
    st.stop()

st.markdown("---")

if st.button("🔄 Refresh"):
    st.rerun()

# ── Fetch all projects from backend ───────────────────────────────────────────
try:
    resp = requests.get("http://localhost:8000/projects/list", timeout=10)
except Exception as e:
    st.error(f"Could not connect to backend: {e}")
    st.stop()

if resp.status_code != 200:
    st.error(f"Failed to load projects: {resp.text}")
    st.stop()

projects = resp.json().get("projects", [])

if not projects:
    st.info("No projects found. Upload your first project using **Upload Project** in the sidebar.")
    st.stop()

st.success(f"Found **{len(projects)}** project(s).")
st.markdown("---")

for proj in projects:
    project_id = proj.get("project_id") or proj.get("id") or "Unknown"
    repo_type  = proj.get("repo_type") or "Unknown"
    created_at = proj.get("created_at") or "N/A"

    with st.expander(f"📁 Project `{project_id}`  —  _{repo_type}_", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Repo Type",   repo_type)
        col2.metric("Files",       proj.get("file_count", "N/A"))
        col3.metric("Created At",  created_at)

        if proj.get("entry_points"):
            st.markdown("**Entry Points:**")
            for ep in proj["entry_points"]:
                st.write(f"  • {ep}")

        if proj.get("config_files"):
            st.markdown("**Config Files:**")
            for cf in proj["config_files"]:
                st.write(f"  • {cf}")

        if proj.get("important_files"):
            st.markdown("**Important Files:**")
            for imf in proj["important_files"]:
                st.write(f"  • {imf}")

        # ── Live progress state ────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📊 Current State")
        try:
            state_resp = requests.get(f"http://localhost:8000/projects/state/{project_id}", timeout=5)
            if state_resp.status_code == 200:
                state = state_resp.json()
                status_icon = {"running": "🟢", "paused": "🟡", "completed": "✅", "not_started": "⚪"}.get(state.get("status", ""), "❓")
                st.write(f"Status: {status_icon} **{state.get('status', 'N/A').title()}**")
            else:
                st.write("State: _unavailable_")
        except Exception:
            st.write("State: _could not fetch_")

        # ── Pause / Resume controls ────────────────────────────────────────
        pcol, rcol = st.columns(2)
        with pcol:
            if st.button("⏸ Pause", key=f"pause_{project_id}"):
                requests.post(f"http://localhost:8000/projects/pause/{project_id}", timeout=5)
                st.success("Paused ✓")
        with rcol:
            if st.button("▶ Resume", key=f"resume_{project_id}"):
                requests.post(f"http://localhost:8000/projects/resume/{project_id}", timeout=5)
                st.success("Resumed ✓")

        # ── Semantic search ────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🔎 Search Code")
        q = st.text_input("Keyword / function name", key=f"search_{project_id}")
        if q:
            sr = requests.post(
                "http://localhost:8000/projects/search",
                json={"project_id": project_id, "query": q, "max_results": 10},
                timeout=10,
            )
            if sr.status_code == 200:
                matches = sr.json().get("matches", [])
                if matches:
                    for m in matches:
                        st.write(f"• {m['type'].capitalize()} `{m['name']}` — {m['file']} (L{m['lineno']}–{m['end_lineno']})")
                else:
                    st.info("No matches found.")
            else:
                st.error("Search error.")

        # ── Q&A ───────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("💬 Ask a Question")
        question = st.text_input("Question", key=f"qa_{project_id}")
        if question:
            qa = requests.post(
                "http://localhost:8000/projects/qa",
                json={"project_id": project_id, "question": question},
                timeout=10,
            )
            if qa.status_code == 200:
                st.markdown(f"**Answer:** {qa.json()['answer']}")
            else:
                st.error("Q&A failed.")
