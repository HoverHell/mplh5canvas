"""Matplotlib HTML5 Canvas backend."""

import logging
import logging.handlers

###################### Modify these at your own risk #############################

MANAGEMENT_PORT_BASE = 9000
 # base port from which to start management interfaces.
 # each management instance started on the same machine assigns 100 ports. 2 for management and 98 for websocket connections.
 # e.g. MANAGEMENT_PORT_BASE = 9000
 #      first manager will spawn with port 9000. Up to 98 figures will use websocket port 9002 - 9099 inclusive.
 #      second manager will spawn with port 9100 and so on...
 #
 # **** Make sure that you don't clobber other services with higher port numbers... ****

MANAGEMENT_LIMIT = 10
 # the maximum number of managers to spawn on this host at any one time...

FIGURE_LIMIT = 98
 # the maximum number of figures per manager. Mostly here to prevent figure spamming bringing down a server

LOG_LEVEL = "warning"
LOG_FILE = None

######################## End of user variable section ############################

logger = logging.getLogger()
logger.setLevel(logging.getLevelName(LOG_LEVEL.upper()))
if LOG_FILE:
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, 'a')
else:
    import sys
    handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("initialisation complete")

def set_log_level(log_level):
    logger.setLevel(logging.getLevelName(log_level.upper()))

