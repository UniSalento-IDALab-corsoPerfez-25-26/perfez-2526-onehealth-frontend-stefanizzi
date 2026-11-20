"""Sidebar navigation with persistent selection and visible active buttons."""

import streamlit as st


def sidebar_menu(label: str, options: tuple[str, ...], *, key: str) -> str:
    selected = st.session_state.get(key)
    if selected not in options:
        selected = options[0]
        st.session_state[key] = selected
    with st.sidebar, st.container(key=f"oh_submenu_{key}"):
        st.markdown(f"**{label}**")
        for option in options:
            st.button(
                option,
                key=f"{key}_button_{option}",
                type="primary" if option == selected else "secondary",
                use_container_width=True,
                on_click=st.session_state.__setitem__,
                args=(key, option),
            )
    return selected
