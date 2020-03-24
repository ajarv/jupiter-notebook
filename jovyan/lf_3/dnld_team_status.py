import logging
from web_util import  LittleFieldWebSite,SimSettings,SimStatus
import shutil
LOG_NAME = "team-status"
logging.basicConfig(format='<%(asctime)s> <%(name)s> <%(levelname)s> <%(message)s>',
                    level=logging.INFO,
                    filename="%s.log"%LOG_NAME)


competition_id,institution,username,password = 'opscom','opscom','encinitas','7rosemary'

if __name__ == "__main__":
    _LFWebSite = LittleFieldWebSite(competition_id,institution,username,password )
    _SIMStatus = SimStatus(_LFWebSite,competition_id,institution,username,password )
    _SIMStatus.fetch_team_standings()
    _SIMStatus.fetch_cash_standing()
    shutil.copy("./tmp/team_standings.csv",'team_standings.csv')
    shutil.copy("./tmp/cash.csv",'cash.csv')
