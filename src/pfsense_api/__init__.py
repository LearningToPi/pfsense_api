'''
The file defines a Python class PfsenseApi that encapsulates functionality for interacting with 
a PfSense firewall. It includes methods for logging in, collecting system stats, handling HTTP 
requests, and managing sessions. The class is designed to facilitate communication with the 
PfSense API using various supported APIs and parsers. The code follows a modular and organized 
structure with appropriate comments for clarity.

Constants:

    TIMEOUT: Default timeout value set to 30 seconds for HTTP requests.
    RETRY: Default number of retries set to 3 for HTTP requests.
    ACCESS_DEINED_REDIRECT: Regular expression pattern to identify denied access redirects.

Class: PfsenseApi

    A class designed to handle login and data querying from a PfSense firewall.

    Attributes:

        host: PfSense host address.
        port: PfSense port (default is 443).
        supported_read_apis: List of READ API's supported by this release
        verify_ssl: Boolean flag to verify SSL certificates (default is True).
        log_level: Logging level (default is INFO).
        ca_cert_path: Path to CA certificate file (default is None).
        _logger: Logger object for logging.
        _session: Requests session object for maintaining a session with PfSense.
        __csrf_token: CSRF token used in requests.

    Methods:

    __init__(self, host, username, password, port=443, log_level=INFO, verify_ssl=True, ca_cert_path=None)
        Initializes a PfsenseApi instance, establishes a session, and logs in.
    
    login(self, username, password) -> bool
        Logs into the PfSense firewall using the provided username and password.

    system_stats(self) -> dict
        Collects system stats and general info from the firewall using supported APIs and returns the data as a dictionary.

    def call_api(self, api_name:str) -> list|dict
        Call a specific API and return the data

    _access_deined(self, response) -> bool
        Checks if an access denied redirect is present in the HTTP response.

    _url_base(self) -> str
        Returns the base portion of the URL.

    get_response(self, method='get', path='/index.php', data=None, headers=None, parameters=None, retry=RETRY, timeout=TIMEOUT) -> requests.Response
        Executes an HTTP request with optional parameters, data, and headers.

    __get_csrf_token(self) -> None
        Retrieves a CSRF token from the firewall.  Used internally

MIT License

Copyright (c) 2023 LearningToPi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

from copy import deepcopy
from urllib.parse import urlencode
import re
import requests
from logging_handler import create_logger, INFO, DEBUG
import validators
from .parser import ContentParserRegex, ContentParserJson, ContentParser, ContentParserHtmlMatrix
# load the supported API's with parsers
from .supported_api import SUPPORTED_READ_API

VERSION = (0, 1, 1)

TIMEOUT = 30
RETRY = 3

# PfSense doesn't return error codes if access is denied. POST request that is deined will return a redirect
ACCESS_DEINED_REDIRECT = r"^\ndocument.location.href\s*=\s*'https://"


class PfsenseError(Exception):
    """ Class to represent errors from the PfsenseApi class """


class PfsenseApi:
    """ Class to handle login and query of data from PfSense """
    __slots__ = ('host', 'port', 'verify_ssl', '_logger', 'log_level', '_session', '__csrf_token', '__session', 'ca_cert_path')
    def __init__(self, host:str, username:str, password:str, port:int=443, log_level=INFO, verify_ssl:bool=True, ca_cert_path:str|None=None):
        """Initialize PfsenseApi instance.

        Args:
            host (str): PfSense host.
            username (str): PfSense username.
            password (str): PfSense password.
            port (int): PfSense port (default is 443).
            log_level: Logging level (default is INFO).
            verify_ssl (bool): Verify SSL certificate (default is True).
            ca_cert_path (str | None): Path to CA certificate file (default is None).
        """
        self.host, self.port, self.verify_ssl, self.log_level, self.ca_cert_path = host, port, verify_ssl, log_level, ca_cert_path
        self._logger = create_logger(log_level, name=f"{self.__class__.__name__}:{host}")
        self.__session = requests.Session()
        self.__csrf_token = ''
        self.__get_csrf_token()
        self.login(username=username, password=password)

    def login(self, username:str, password:str) -> bool:
        """Login to the PfSense firewall.

        Args:
            username (str): PfSense username.
            password (str): PfSense password.

        Returns:
            bool: True if login is successful.
        
        Raises:
            PfsenseError: If login fails.
        """
        self._session = requests.Session()
        response = self.get_response(method='post', data={'usernamefld': username, 'passwordfld': password, 'login': 'Sign In'})
        self.__get_csrf_token()
        if response.status_code == 200:
            return True
        raise PfsenseError(f"Error logging into {self.host}:{self.port}. Response code {response.status_code}")

    def all_system_stats(self) -> dict:
        """Collects the system stats and general info from the firewall and returns as a dict.

        Returns:
            dict: System stats and general info.
        
        Raises:
            PfsenseError: If an API call fails.
        """
        return_data = {}
        for api, settings in SUPPORTED_READ_API.items():
            try:
                response = self.get_response(**settings['request'])
                if response.status_code != 200:
                    self._logger.error(f"API call to {self.host}:{self.port} with {settings['request']} returned: {response.status_code}")
                    raise PfsenseError(f"API call to {self.host}:{self.port} with {settings['request']} returned: {response.status_code}")
                elif self._access_deined(response):
                    self._logger.error(f"API call failed to {self.host}:{self.port}, received redirect, typically means access deined.")
                    raise PfsenseError(f"API call failed to {self.host}:{self.port}, received redirect, typically means access deined.")
                return_data[api] = settings.get('parser', ContentParser()).parse(response.text)
            except Exception as e:
                self._logger.error(f"API call to {self.host}:{self.port} with {settings['request']} ERROR: {e}")
                raise e
        return return_data

    @property
    def supported_read_apis(self) -> list:
        """Returns a list of supported API's in the current release.

        Returns:
            list: list of API names
        """
        return list(SUPPORTED_READ_API.keys())

    def call_api(self, api_name:str) -> list|dict:
        """Execeute the selected API (must be a part of the supported API's)

        Returns:
            varies: Dict, list or string depending on the API
        """
        return_data = None
        try:
            response = self.get_response(**SUPPORTED_READ_API[api_name]['request'])
            if response.status_code != 200:
                self._logger.error(f"API call to {self.host}:{self.port} with {SUPPORTED_READ_API[api_name]['request']} returned: {response.status_code}")
                raise PfsenseError(f"API call to {self.host}:{self.port} with {SUPPORTED_READ_API[api_name]['request']} returned: {response.status_code}")
            elif self._access_deined(response):
                self._logger.error(f"API call failed to {self.host}:{self.port}, received redirect, typically means access deined.")
                raise PfsenseError(f"API call failed to {self.host}:{self.port}, received redirect, typically means access deined.")
            return_data = SUPPORTED_READ_API[api_name].get('parser', ContentParser()).parse(response.text)
        except Exception as e:
            self._logger.error(f"API call to {self.host}:{self.port} with {SUPPORTED_READ_API[api_name]['request']} ERROR: {e}")
            raise e
        return return_data

    def _access_deined(self, response:requests.Response):
        """Return True if an access denied redirect was returned.

        Args:
            response (requests.Response): HTTP response object.

        Returns:
            bool: True if access denied.
        """
        if re.search(ACCESS_DEINED_REDIRECT, response.text):
            return True
        return False

    @property
    def _url_base(self) -> str:
        """Return the base portion of the URL.

        Returns:
            str: Base URL.
        """
        return f"https://{self.host}:{self.port}"

    def get_response(self, method:str='get', path:str='/index.php', data:str|dict|None=None, headers:dict|None=None, parameters:dict|None=None, retry=RETRY, timeout=TIMEOUT) -> requests.Response:
        """Execute the request.

        Args:
            method (str): HTTP method (default is 'get').
            path (str): URL path (default is '/index.php').
            data (str | dict | None): Request data (default is None).
            headers (dict | None): Request headers (default is None).
            parameters (dict | None): Request parameters (default is None).
            retry (int): Number of retries (default is 3).
            timeout (int): Request timeout (default is 30).

        Returns:
            requests.Response: HTTP response object.

        Raises:
            PfsenseError: If request fails.
        """
        x = 0
        url = self._url_base + '/' + path.lstrip('/')
        if not validators.url(url):
            raise PfsenseError(f'URL "{url}" failed validation!')
        # populate parameters, post data and headers as needed
        if parameters is not None and isinstance(parameters, dict):
            url += f"?{urlencode(parameters)}"
        if isinstance(data, dict) and method.lower() == 'post':
            send_data = deepcopy(data)
            send_data['__csrf_magic'] = self.__csrf_token
            send_data['ajax'] = 'ajax'
        elif method.lower() == 'post':
            send_data = {'__csrf_magic': self.__csrf_token, 'ajax': 'ajax'}
        else:
            send_data = None
        if isinstance(headers, dict) and method.lower() == 'post':
            send_headers = deepcopy(headers)
            send_headers['X-Requested-With'] = 'XMLHttpRequest'
        elif method.lower() == 'post':
            send_headers = {'X-Requested-With': 'XMLHttpRequest'}
        else:
            send_headers = None
        while x < retry:
            x += 1
            self._logger.debug(f"({x}/{retry}) {method.upper()} to {url}...")
            try:
                if self.__session is None:
                    self._logger.error("Session does not exist!")
                    raise PfsenseError("Session does not exist!")
                response = self.__session.request(method=method,
                                                  url=url,
                                                  timeout=timeout,
                                                  data=send_data,
                                                  verify=self.ca_cert_path if self.ca_cert_path is not None else self.verify_ssl,
                                                  headers=send_headers)
                self._logger.debug(f"Response from {method} {url}: {response.status_code}")
                if 'CSRF check failed' in response.text:
                    raise PfsenseError('CSRF check failed!')
                return response
            except requests.exceptions.ConnectTimeout as e:
                self._logger.warning(f"Connection timeout {method.upper()} to {url} try {x}/{retry}: {e}")
                raise e
            except requests.exceptions.SSLError as e:
                self._logger.error(f"SSL Error {method.upper()} to {url} try {x}/{retry}: {e}")
                raise e
            except requests.exceptions.ConnectionError as e:
                self._logger.error(f"Connection Error {method.upper()} to {url} try {x}/{retry}: {e}")
                raise e
            except Exception as e:
                self._logger.error(f"General exception {method.upper()} to {url}: {e}")
                raise e
        # if we got here, all retries failed
        self._logger.error(f"Retries exceeded for {method.upper()} to {url}")
        raise PfsenseError(f"Retries exceeded for {method.upper()} to {url}")

    def __get_csrf_token(self) -> None:
        ''' Get a CSRF token for the request '''
        response = self.get_response()
        csrf_search = re.search(r'sid:[^;"]*', response.text)
        if not csrf_search:
            return
        self.__csrf_token = response.text[csrf_search.span()[0]:csrf_search.span()[1]]
