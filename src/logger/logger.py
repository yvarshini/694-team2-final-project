import logging
 
# creating and configuring logger
logging.basicConfig(filename="logfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
 
logger = logging.getLogger()
 
# set the threshold of the logger to level DEBUG
logger.setLevel(logging.INFO)