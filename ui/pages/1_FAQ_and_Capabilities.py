from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="FAQ & Capabilities | OcuGuard",
    page_icon=":material/menu_book:",
    layout="wide",
)

DOC_ROOT = Path(__file__).parents[1] / "docs" / "agents"
DOCS = {
    "eye-sentinel": {
        "title": "Eye Sentinel",
        "mode": "EYE_SENTINEL",
        "group": "Studio agents",
        "file": "eye-sentinel.md",
    },
    "ocuguard-core": {
        "title": "OcuGuard Core",
        "mode": "OCUGUARD_CORE",
        "group": "Studio agents",
        "file": "ocuguard-core.md",
    },
    "gaze-compass": {
        "title": "Gaze Compass",
        "mode": "GAZE_COMPASS",
        "group": "Studio agents",
        "file": "gaze-compass.md",
    },
    "tabular-layout-speech": {
        "title": "Tabular Layout Speech",
        "mode": "TABULAR_LAYOUT_SPEECH",
        "group": "Studio agents",
        "file": "tabular-layout-speech.md",
    },
    "ergonomic-schedule": {
        "title": "Ergonomic Schedule",
        "mode": "ERGONOMIC_SCHEDULE",
        "group": "Studio agents",
        "file": "ergonomic-schedule.md",
    },
    "ambient-luminance": {
        "title": "Ambient Luminance",
        "mode": "AMBIENT_LUMINANCE",
        "group": "Studio agents",
        "file": "ambient-luminance.md",
    },
    "be-my-eyes": {
        "title": "Be My Eyes (local prototype mode)",
        "mode": "BE_MY_EYES",
        "group": "Studio agents",
        "file": "be-my-eyes.md",
    },
    "aniseikonia-scaling": {
        "title": "Aniseikonia Scaling",
        "mode": "ANISEIKONIA_SCALING",
        "group": "Studio agents",
        "file": "aniseikonia-scaling.md",
    },
    "metamorphopsia-grid-remapper": {
        "title": "Metamorphopsia Grid Remapper",
        "mode": "METAMORPHOPSIA_GRID_REMAPPER",
        "group": "Studio agents",
        "file": "metamorphopsia-grid-remapper.md",
    },
    "biofeedback-anxiety-sentinel": {
        "title": "Biofeedback Anxiety Sentinel",
        "mode": "BIOFEEDBACK_ANXIETY_SENTINEL",
        "group": "Studio agents",
        "file": "biofeedback-anxiety-sentinel.md",
    },
    "supervisor": {
        "title": "Supervisor",
        "mode": "REST API platform component",
        "group": "Platform modules",
        "file": "supervisor.md",
    },
    "preop-waitlist": {
        "title": "Pre-Op Waitlist",
        "mode": "Experimental module · not selectable in Studio",
        "group": "Platform modules",
        "file": "preop-waitlist.md",
    },
}

DOC_CONTENT = {
    key: (DOC_ROOT / doc["file"]).read_text(encoding="utf-8")
    for key, doc in DOCS.items()
}
GROUPS = ("Studio agents", "Platform modules")


def _matches_search(query: str, key: str, doc: dict[str, str]) -> bool:
    return not query or any(
        query in value
        for value in (doc["title"].lower(), doc["mode"].lower(), DOC_CONTENT[key].lower())
    )


if "faq_active_doc" not in st.session_state:
    st.session_state["faq_active_doc"] = "overview"

with st.sidebar:
    st.markdown("## OcuGuard docs")
    st.caption("Browse agent capabilities, inputs, and boundaries.")
    search_query = st.text_input("Search documentation", key="faq_search").strip().lower()
    if st.button("Documentation home", use_container_width=True):
        st.session_state["faq_active_doc"] = "overview"

    for group in GROUPS:
        group_docs = [
            (key, doc)
            for key, doc in DOCS.items()
            if doc["group"] == group and _matches_search(search_query, key, doc)
        ]
        if not group_docs:
            continue
        st.markdown(f"#### {group}")
        for key, doc in group_docs:
            if st.button(
                doc["title"],
                key=f"faq-nav-{key}",
                type=(
                    "primary"
                    if st.session_state["faq_active_doc"] == key
                    else "secondary"
                ),
                use_container_width=True,
            ):
                st.session_state["faq_active_doc"] = key

matching_doc_keys = {
    key
    for key, doc in DOCS.items()
    if _matches_search(search_query, key, doc)
}
active_doc = st.session_state["faq_active_doc"]
if active_doc != "overview" and active_doc not in DOCS:
    raise ValueError(f"Unknown FAQ documentation page: {active_doc}")

if active_doc == "overview":
    st.title("FAQ & Capabilities")
    st.caption("OcuGuard Studio documentation · prototype scope and agent reference")
    st.markdown(
        "Browse what each mode currently does, what inputs it uses, and what it "
        "does **not** do. The first collection lists the ten selectable Studio "
        "modes; platform modules are listed separately so code that is not "
        "available as a Studio mode is clearly identified."
    )
    st.warning(
        "Prototype documentation only. No agent is a medical device, diagnostic "
        "service, or substitute for instructions from a qualified care team."
    )

    if search_query and not matching_doc_keys:
        st.info("No documentation matched your search.")

    for group in GROUPS:
        group_docs = [
            (key, doc)
            for key, doc in DOCS.items()
            if doc["group"] == group and key in matching_doc_keys
        ]
        if not group_docs:
            continue
        st.subheader(group)
        columns = st.columns(2)
        for index, (key, doc) in enumerate(group_docs):
            with columns[index % 2]:
                with st.container(border=True):
                    st.markdown(f"### {doc['title']}")
                    st.caption(doc["mode"])
                    if st.button(
                        f"Open {doc['title']} FAQ",
                        key=f"faq-home-{key}",
                        use_container_width=True,
                    ):
                        st.session_state["faq_active_doc"] = key
                        st.rerun()
else:
    doc = DOCS[active_doc]
    st.caption(f"FAQ & Capabilities / {doc['group']} / {doc['title']}")
    st.title(doc["title"])
    st.caption(doc["mode"])
    st.markdown(DOC_CONTENT[active_doc])

st.caption(
    "The agent pages describe the checked-in prototype implementation. "
    "They are not clinical, legal, privacy, or regulatory assurances."
)
