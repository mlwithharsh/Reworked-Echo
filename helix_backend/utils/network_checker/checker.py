import socket
import logging
import time

class NetworkChecker:
    def __init__(self, check_target="8.8.8.8", port=53, timeout=3):
        self.check_target = check_target
        self.port = port
        self.timeout = timeout
        self.last_status = None
        self.last_check_time = 0
        self.logger = logging.getLogger(__name__)

    def is_online(self, force=False):
        """
        Check if the machine is online by attempting a socket connection.
        Caches the result for 10 seconds to avoid excessive network overhead.
        """
        current_time = time.time()
        if not force and (current_time - self.last_check_time < 10) and self.last_status is not None:
            return self.last_status

        try:
            socket.setdefaulttimeout(self.timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.check_target, self.port))
            self.last_status = True
        except socket.error as ex:
            self.logger.warning(f"Network indicator: Device appears to be OFFLINE. {ex}")
            self.last_status = False
        
        self.last_check_time = current_time
        return self.last_status

# Singleton instance
helper = NetworkChecker()
def is_online():
    return helper.is_online()
