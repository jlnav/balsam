import logging
import time
from datetime import datetime, timedelta

import click
import dateutil.parser
from requests.exceptions import ConnectionError

from .requests_client import RequestsClient
from .rest_base_client import AuthError

logger = logging.getLogger(__name__)


class BasicAuthRequestsClient(RequestsClient):
    def __init__(
        self,
        api_root,
        username,
        password=None,
        token=None,
        token_expiry=None,
        connect_timeout=3.1,
        read_timeout=60,
        retry_count=3,
    ):
        super().__init__(
            api_root,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retry_count=retry_count,
        )
        self.username = username
        self.password = password
        self.token = token
        self.token_expiry = token_expiry
        self.expires_in = timedelta(hours=240)
        if self.token is not None:
            self.session.auth = None
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self._authenticated = True
        if self.token_expiry:
            self.expires_in = self.token_expiry - datetime.utcnow()
            if self.expires_in.total_seconds() <= 1:
                self._authenticated = False
                logger.warning("Auth Token is expired; please refresh with `balsam login`")
            elif self.expires_in < timedelta(hours=24):
                logger.warning(f"Auth Token will expire in {self.expires_in}; please refresh with `balsam login`")

    def refresh_auth(self):
        if self.password is None:
            raise ValueError("Cannot refresh_auth: self.password is None. Please provide a password")
        # Login with HTTPBasic Auth to get a token:
        url = "users/login"
        cred = {"username": self.username, "password": self.password}
        resp = None
        for _ in range(3):
            try:
                resp = self.request(url, "POST", data=cred, authenticating=True)
            except ConnectionError as e:
                logger.warning(f"ConnectionError: {e}")
                time.sleep(1)
            else:
                break
        if resp is not None and "access_token" in resp:
            self.token = resp["access_token"]
            self.token_expiry = dateutil.parser.parse(resp["expiration"])
        else:
            raise AuthError(f"Could not authenticate: {resp}")

        # Unset BasicAuth; set Token Authorization header
        self.session.auth = None
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        self._authenticated = True

    def interactive_login(self):
        """Initiate interactive login flow"""
        self.password = click.prompt("Balsam password", hide_input=True)
        self.refresh_auth()
        click.echo("Logged In")
        return {"token": self.token, "token_expiry": self.token_expiry}
