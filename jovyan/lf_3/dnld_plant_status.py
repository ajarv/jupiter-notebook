import logging
from web_util import  LittleFieldWebSite,SimSettings,SimStatus

LOG_NAME = "plant-status"
logging.basicConfig(format='<%(asctime)s> <%(name)s> <%(levelname)s> <%(message)s>',
                    level=logging.INFO,
                    filename="%s.log"%LOG_NAME)

# competition_id,institution,username,password = 'littlefield','demo','operators','goteam'
competition_id,institution,username,password = 'opscom','opscom','encinitas','7rosemary'

if __name__ == "__main__":
    _LFWebSite = LittleFieldWebSite(competition_id,institution,username,password )
    _SIMStatus = SimStatus(_LFWebSite,competition_id,institution,username,password )
    _SIMSettings = SimSettings(_LFWebSite,competition_id,institution,username,password )
    _SIMStatus.fetch_plant_status()
    _SIMSettings.plantsettings
