import os
from dotenv import load_dotenv

load_dotenv()


def get_setting(name, default=""):
    value = os.getenv(name)
    if value is not None:
        return value
    import streamlit as st
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default
