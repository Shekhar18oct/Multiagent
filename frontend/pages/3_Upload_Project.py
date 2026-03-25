import time
import streamlit as st
import requests

st.set_page_config(page_title="Upload Project | Multi-Agent Code Analysis", layout="wide")
st.title("📁 Upload Project")

if not st.session_state.get("token"):
    st.warning("⚠️ Please **Login** first (use the sidebar).")
    st.stop()

st.success(f"Logged in as **{st.session_state.get('username')}** ({st.session_state.get('role')})")
st.markdown("---")

# ── Agent Configuration ───────────────────────────────────────────────────────
with st.expander("⚙️ Agent Configuration", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        analysis_depth = st.selectbox("Analysis Depth", ["Quick", "Standard", "Deep"], index=1)
        verbosity = st.selectbox("Documentation Verbosity", ["Low", "Medium", "High"], index=1)
    with col2:
        enable_diagrams = st.checkbox("Generate Diagrams", value=True)
        enable_feature_analysis = st.checkbox("Enable Feature Analysis", value=True)

st.markdown("---")

# ── Upload Form ───────────────────────────────────────────────────────────────
with st.form("upload_form"):
    st.subheader("Project Source")
    personas = st.multiselect("Select Personas", ["SDE", "PM"], default=["SDE", "PM"])
    upload_tab, github_tab = st.tabs(["📦 Upload ZIP", "🔗 GitHub URL"])
    with upload_tab:
        zip_file = st.file_uploader("Upload ZIP file (max 100 MB)", type=["zip"])
    with github_tab:
        github_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/user/repo")
    submitted = st.form_submit_button("🚀 Start Analysis", type="primary")

# ── Handle Submission ─────────────────────────────────────────────────────────
if submitted:
    if not personas:
        st.error("Please select at least one persona.")
        st.stop()
    if zip_file is None and not github_url.strip():
        st.error("Please upload a ZIP file or provide a GitHub URL.")
        st.stop()

    data = {
        "personas": personas,
        "analysis_depth": analysis_depth,
        "verbosity": verbosity,
        "enable_diagrams": str(enable_diagrams),
        "enable_feature_analysis": str(enable_feature_analysis),
    }
    files = None
    url = "http://localhost:8000/projects/upload"

    if zip_file is not None:
        files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
        data["github_url"] = ""
    else:
        data["github_url"] = github_url.strip()

    with st.spinner("Uploading and analysing your project…"):
        try:
            resp = requests.post(url, data=data, files=files, timeout=120) if files else requests.post(url, data=data, timeout=120)
        except Exception as e:
            st.error(f"Connection error: {e}")
            st.stop()

    if resp.status_code != 200:
        st.error(f"❌ {resp.json().get('detail', 'Upload failed.')}")
        st.stop()

    result = resp.json()
    project_id = result["project_id"]

    st.success(f"✅ Project created! **ID: `{project_id}`**")
    st.info(f"Status: **{result['status']}** — {result['message']}")

    # ── Live Progress Feed ────────────────────────────────────────────────────
    st.subheader("⏳ Live Progress")
    prog_bar = st.progress(0, text="Initialising…")
    feed_box = st.empty()
    pause_col, resume_col = st.columns(2)
    with pause_col:
        if st.button("⏸ Pause"):
            requests.post(f"http://localhost:8000/projects/pause/{project_id}", timeout=5)
    with resume_col:
        if st.button("▶ Resume"):
            requests.post(f"http://localhost:8000/projects/resume/{project_id}", timeout=5)

    for _ in range(60):
        try:
            prog_resp = requests.get(f"http://localhost:8000/projects/progress/{project_id}", timeout=5)
            if prog_resp.status_code == 200:
                prog = prog_resp.json()
                total = prog.get("total", 1) or 1
                current = prog.get("current", 0)
                pct = int(100 * current / total)
                prog_bar.progress(pct, text=f"Stage: {prog['stage']} ({current}/{total})")
                feed_box.markdown(
                    "**Activity Feed:**\n" + "\n".join(f"- {a}" for a in prog.get("activity", []))
                )
                if prog.get("done"):
                    prog_bar.progress(100, text="✅ Preprocessing complete!")
                    break
        except Exception:
            break
        time.sleep(0.5)

    st.markdown("---")

    # ── Repository Intelligence ───────────────────────────────────────────────
    st.subheader("🔍 Repository Intelligence")
    cols = st.columns(3)
    cols[0].metric("Repo Type", result.get("repo_type") or "Unknown")
    cols[1].metric("Entry Points", len(result.get("entry_points") or []))
    cols[2].metric("Code Chunks", len(result.get("code_chunks") or []))

    if result.get("config_files"):
        st.markdown("**Config Files:**")
        st.write(result["config_files"])
    if result.get("important_files"):
        st.markdown("**Important Files:**")
        st.write(result["important_files"])

    st.markdown("---")

    # ── Code Chunks ────────────────────────────────────────────────────────────
    if result.get("code_chunks"):
        with st.expander(f"📦 Code Chunks ({len(result['code_chunks'])} found)", expanded=False):
            for chunk in result["code_chunks"][:50]:
                st.write(f"• {chunk['type'].capitalize()} `{chunk['name']}` — {chunk['file']} (L{chunk['lineno']}–{chunk['end_lineno']})")
            if len(result["code_chunks"]) > 50:
                st.caption(f"…and {len(result['code_chunks']) - 50} more.")

    # ── Semantic Search ────────────────────────────────────────────────────────
    st.subheader("🔎 Semantic Code Search")
    search_query = st.text_input("Search code chunks by name or keyword", key="code_search")
    if search_query:
        search_resp = requests.post(
            "http://localhost:8000/projects/search",
            json={"project_id": project_id, "query": search_query, "max_results": 10},
            timeout=10,
        )
        if search_resp.status_code == 200:
            matches = search_resp.json().get("matches", [])
            if matches:
                for m in matches:
                    st.write(f"• {m['type'].capitalize()} `{m['name']}` in {m['file']} (L{m['lineno']}–{m['end_lineno']})")
            else:
                st.info("No matches found.")
        else:
            st.error("Search failed.")

    st.markdown("---")

    # ── Q&A ────────────────────────────────────────────────────────────────────
    st.subheader("💬 Ask a Question About This Project")
    question = st.text_input("Your question", key="qa_input")
    context = st.text_area("Add extra context (optional)", key="qa_context", height=80)
    if question:
        qa_resp = requests.post(
            "http://localhost:8000/projects/qa",
            json={"project_id": project_id, "question": question, "context": context or None},
            timeout=10,
        )
        if qa_resp.status_code == 200:
            st.markdown(f"**Answer:** {qa_resp.json()['answer']}")
        else:
            st.error("Q&A failed.")

    st.markdown("---")

    # ── Agent Outputs ──────────────────────────────────────────────────────────
    if result.get("agent_outputs"):
        st.subheader("🤖 Multi-Agent Outputs")
        tabs = st.tabs(list(result["agent_outputs"].keys()))
        for tab, (persona, output) in zip(tabs, result["agent_outputs"].items()):
            with tab:
                st.json(output)

    if result.get("agent_activity"):
        with st.expander("📋 Agent Activity Log"):
            for act in result["agent_activity"]:
                st.write(f"- {act}")

    # Save project_id to session for Projects page
    if "project_ids" not in st.session_state:
        st.session_state["project_ids"] = []
    if project_id not in st.session_state["project_ids"]:
        st.session_state["project_ids"].append(project_id)
