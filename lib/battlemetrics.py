from time import strftime, localtime
from datetime import datetime, timedelta
from lib.components.player import Player
from lib.components.helpers import Helpers

class Battlemetrics:
    """Sets up the wrapper.

    Args:
        api_key (str): Your battlemetrics API token.

    Returns:
        None: Doesn't return anything.
    """

    def __init__(self, api_key: str) -> None:
        self.BASE_URL = "https://api.battlemetrics.com"
        self.api_key = api_key
        #self.response_data = None
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.helpers = Helpers(api_key=api_key)
        self.player = Player(helpers=self.helpers, BASE_URL=self.BASE_URL)