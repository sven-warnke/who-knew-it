import pathlib

import streamlit as st
import streamlit_authenticator as stauth  # type: ignore
import yaml
from yaml.loader import SafeLoader

CREDENTIALS_FILE = pathlib.Path(__file__).parent.parent / "config.yaml"


def authenticated() -> bool:

    with open(CREDENTIALS_FILE) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        CREDENTIALS_FILE.as_posix(),
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    with st.sidebar:
        if st.session_state.get('authentication_status'):
            authenticator.logout()
            return True
        else:
            try:
                authenticator.login()
            except Exception as e:
                st.error(e)

            if st.session_state.get('authentication_status') is False:
                st.error('Username/password is incorrect')
            else:
                st.warning('Please enter admin credentials')

    return False
