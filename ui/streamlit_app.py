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
