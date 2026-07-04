"""Basic authentication for Streamlit app."""

from __future__ import annotations
import os
import streamlit as st

DEFAULT_USERNAME = "regcheck"
DEFAULT_PASSWORD = "regcheck"

def check_auth() -> bool:
    return st.session_state.get("authenticated", False)

def login_form():
    return check_auth()
