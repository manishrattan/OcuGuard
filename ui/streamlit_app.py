import streamlit as st


pages = {
    "Studio": [
        st.Page(
            "studio.py",
            title="OcuGuard Studio",
            icon=":material/dashboard:",
            default=True,
        )
    ],
    "Recovery Companion": [
        st.Page(
            "recovery_companion_page.py",
            title="Recovery Companion",
            icon=":material/accessibility_new:",
        )
    ],
    "Documentation": [
        st.Page(
            "pages/1_FAQ_and_Capabilities.py",
            title="FAQ & Capabilities",
            icon=":material/menu_book:",
        )
    ],
}
selected_page = st.navigation(pages, position="sidebar")
selected_page.run()
