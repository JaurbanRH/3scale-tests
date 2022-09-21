"""Selenium factory for creating  Threescale browser instances to run UI tests. """


from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from testsuite.ui.exception import WebDriverError


class _Chrome:
    """Factory class for Chrome browser"""

    def __init__(self, source, ssl_verify, remote_url=None, binary_path=None):
        self.source = source
        self.remote_url = remote_url
        self.binary_path = binary_path
        self.webdriver = None
        self.options = ChromeOptions()

        if not ssl_verify:
            self.options.set_capability("acceptInsecureCerts", True)

    def install(self):
        """Installs the web driver"""
        if self.source == 'local':
            self.binary_path = ChromeDriverManager().install()

    def start_session(self):
        """Initializes and starts web browser"""
        if self.source == 'remote':
            self.webdriver = webdriver.Remote(command_executor=self.remote_url + '/wd/hub',
                                              options=self.options)
        elif self.source in ('local', 'binary'):
            self.webdriver = webdriver.Chrome(service=ChromeService(executable_path=self.binary_path),
                                              options=self.options)
        else:
            raise ValueError(
                '"{}" source is not supported. Please use one of {}'
                .format(self.source, ('local', 'binary', 'remote'))
            )

        return self.webdriver


class _Firefox:
    """Factory class for Firefox browser"""

    def __init__(self, source, ssl_verify, remote_url=None, binary_path=None):
        self.source = source
        self.remote_url = remote_url
        self.binary_path = binary_path
        self.webdriver = None
        self.options = FirefoxOptions()
        self.options.set_preference("browser.link.open_newwindow", 3)
        self.options.set_preference("webdriver_accept_untrusted_certs", ssl_verify)

    def install(self):
        """Installs the web driver"""
        if self.source == 'local':
            self.binary_path = GeckoDriverManager().install()

    def start_session(self):
        """Initializes and starts web browser"""
        if self.source == 'remote':
            self.webdriver = webdriver.Remote(command_executor=self.remote_url + '/wd/hub',
                                              options=self.options)
        elif self.source in ('local', 'binary'):
            self.webdriver = webdriver.Firefox(service=FirefoxService(executable_path=self.binary_path),
                                               options=self.options)
        else:
            raise ValueError(
                '"{}" source is not supported. Please use one of {}'
                .format(self.source, ('local', 'binary', 'remote'))
            )

        return self.webdriver


class ThreescaleWebdriver:
    """
    Selenium web driver of the desired provider.
    Usage:
        # Init
        correct driver factory classes (`_Chrome` and `_Firefox`) are initialized based on the required `driver`.
        This will the call correct `DriverManager` and install the web driver if the local `source` is selected.

        # Execution
        `start_session()` calls respective factory class, which initialize installed WebDriver
        (`webdriver.Remote` if the `source` is remote) and returns an instance of WebDriver with
        running browser session.

        # Finalize
        to clean-up after tests, perform `finalize()`. This quits the driver and closes every associated window.
        Note that the installed web driver is not removed by this action.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, driver, source, ssl_verify, remote_url=None, binary_path=None):
        """
        Initializes factory with either specified or fetched from settings values.
        :param str driver: Browser name. One of ('chrome', 'firefox')
        :param str source: Browser source name. One of  ('local', 'binary', 'remote')
        :param str ssl_verify: option for certificates ignore
        :param str optional remote_url: URL of remote webdriver
        """
        self.driver = driver
        self.source = source
        self.remote_url = remote_url or 'http://127.0.0.1:4444'
        self.binary_path = binary_path
        self.webdriver = None
        self.session = None

        if self.driver == 'chrome':
            self.webdriver = _Chrome(source, ssl_verify, remote_url, binary_path)
        elif self.driver == 'firefox':
            self.webdriver = _Firefox(source, ssl_verify, remote_url, binary_path)
        else:
            raise ValueError(
                '"{}" webdriver is not supported. Please use one of {}'
                .format(self.driver, ('chrome', 'firefox'))
            )
        self.webdriver.install()

    def start_session(self):
        """
        Starts installed webdriver session.
        """
        self.session = self.webdriver.start_session()
        self.post_init()
        return self.session

    def post_init(self):
        """
        Perform all required post-init actions.
        """
        self.session.maximize_window()

    def finalize(self):
        """
        Finalize handling of webdriver.
        :raises: WebDriverError: If problem with browser happens finalization occurs.
        """
        try:
            self.session.quit()
        except Exception as exception:
            raise WebDriverError("Problem with browser finalization") from exception
