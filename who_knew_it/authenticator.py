import pathlib

import streamlit as st
import streamlit_authenticator as stauth  # type: ignore
import yaml
from yaml.loader import SafeLoader

CREDENTIALS_FILE = pathlib.Path(__file__).parent.parent / "config.yaml"


def get_authenticator() -> stauth.Authenticate:

    with open(CREDENTIALS_FILE) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        CREDENTIALS_FILE.as_posix(),
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    return authenticator
