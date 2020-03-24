import time
import collections
import os
import urllib
import httplib2
import pandas as pd
import numpy as np
import shelve
import re
import logging
from functools import wraps
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys
from dateutil.tz import tzlocal

LOG_NAME = "web_util"

LOGGER = logging.getLogger(LOG_NAME)

def config_logging(level=logging.INFO):
    logging.basicConfig(format='<%(asctime)s> <%(name)s> <%(levelname)s> <%(message)s>', level=level)
    fileHandler = logging.FileHandler(filename="%s.log"%LOG_NAME)
    fileHandler.setLevel(logging.WARN)
    fileHandler.setFormatter(logging.Formatter('<%(asctime)s> <%(name)s> <%(levelname)s> <%(message)s>'))
    LOGGER.addHandler(fileHandler)

TMP_DIR = "./tmp"
DATA_DIR = "."
if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)

def my_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            LOGGER.debug("Calling %r (%r, %r)"%(f.__name__,args,kwds))
            t0 = time.time()
            result = f(*args, **kwds)
            LOGGER.info("Completed in %.2d seconds"%(time.time()-t0))
            return  result
        except:
            LOGGER.warn("Failed %r (%r, %r)"%(f.__name__,args,kwds))
            raise
    return wrapper





http = httplib2.Http()
_cache = shelve.open("%s/.cache"%TMP_DIR)

class LittleFieldWebSite:
    def __init__(self,competition_id,institution,username,password):
        self.competition_id,self.username,self.password,self.institution= competition_id,username,password,institution
        pass
    def login(self):
        cookie_key = "{0}.cookie".format(self.competition_id)
        entry = _cache.get(cookie_key,None)
        if (entry) :
            xtime,cookie =  entry
            if time.time() - xtime  < 60 * 20:
                LOGGER.debug("Using cached cookie: %s"%(cookie))
                return  cookie
        # curl "http://ops.responsive.net/Littlefield/CheckAccess" -H "Cookie: JSESSIONID=2FF17B827D9431B512C575BA640EC3F2"
        # -H "Origin: http://ops.responsive.net" -H "Accept-Encoding: gzip, deflate" -H "Accept-Language: en-US,en;q=0.8" -H
        # "Upgrade-Insecure-Requests: 1" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
        #  Chrome/48.0.2564.103 Safari/537.36" -H "Content-Type: application/x-www-form-urlencoded" -H
        # "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" -H "Cache-Control: max-age=0"
        # -H "Referer: http://ops.responsive.net/lt/ucsd1/entry.html" -H "Connection: keep-alive"
        #  --data "institution=ucsd1&ismobile=false&id=group4&password=safari14" --compressed
        url = "http://{0}.responsive.net/Littlefield/CheckAccess".format(self.competition_id)
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        body = "institution={0}&ismobile=false&id={1}&password={2}".format(self.institution,self.username,self.password)
        LOGGER.debug("URL:%s ,Request:%s"%(url,body))
        resp, content = http.request(url, method="POST", body=body, headers=headers)

        htmltxt = BeautifulSoup(content,'lxml').get_text().replace("\\n","\n")
        LOGGER.debug(htmltxt)

        if resp['status'] != '200':
            LOGGER.warning("FATAL ERROR : Failed to login")
            raise Exception("login failed")
            return None
        cookie = resp['set-cookie'].split(";")[0].split('=')[1]
        _cache[cookie_key] = [time.time(),cookie]
        _cache.sync()
        LOGGER.debug("Login Successful: %s"%(cookie))
        return cookie

    def post_request(self,url,body):
        LOGGER.info("begin : post_request( %r , %r )"%(url,body))
        cookie = self.login()

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
                   'Cookie': "JSESSIONID=%s"%cookie}
        resp, content = http.request(url, method="POST", body=body, headers=headers)
        if resp['status'] != '200':
            LOGGER.warning("Failed post_request( %r , %r )"%(url,body))
            raise Exception("POST Failed")
        LOGGER.info("url: %s, status  OK"%(url))
        return content

    def get_request(self, url):
        LOGGER.info("begin : make_get( %r )"%(url))
        cookie = self.login()
        # cookie = 'CC5C8084A7ABC1E6445504FA0C40AD83'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
                   'Cookie': "JSESSIONID=%s"%cookie}
        resp, content = http.request(url, method="GET", headers=headers)
        if resp['status'] != '200':
            LOGGER.warning("Failed to GET :%r"%(url))
            raise Exception("GET Failed")
        LOGGER.info("url: %s, status  OK"%(url))
        return content





class SimSettings:
    def __init__(self,lfwebsite,competition_id="ops",institution="ucsd1",username="group4",password="safari14"):
        self.competition_id,self.username,self.password,self.institution= competition_id,username,password,institution
        self.lfwebsite = lfwebsite or LittleFieldWebSite(competition_id,institution,username,password)

    def get_order_settings(self):
        ''' Successful Parsed HTML looks like
Littlefield Technologies -
ORDERS MENU
 Name: group4
Maximum WIP Limit: 100 jobs
Number of kits in 1 job: 60
Lot size: 60 kits, or 1 lot per job
Current contract: 3
Quoted lead time: 0.5 day(s)
Maximum lead time: 1.0 day(s)
Revenue per order: 1250.0 dollars
Please click on a button...
        '''

        url = "http://{0}.responsive.net/Littlefield/OrdersMenu".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        LOGGER.info("get_current_contractOption : Sending Request")

        content = self.lfwebsite.get_request(url)
        htmltxt = BeautifulSoup(content,'lxml').get_text().replace("\\n","\n")
        LOGGER.debug(htmltxt)

        wip_limit = int(re.search('Maximum WIP Limit: (\d+) jobs',htmltxt) and re.search('Maximum WIP Limit: (\d+) jobs',htmltxt).group(1) or 999)
        contract_type = int(re.search('Current contract: (\d+)',htmltxt).group(1))
        kits_per_order = int(re.search('Number of kits in 1 job: (\d+)',htmltxt).group(1))
        lot_size = int(re.search('Lot size: (\d+) kits, or 1 lot per job',htmltxt).group(1))
        max_lead_time = float(re.search('Maximum lead time: (\d+[.]\d+) day',htmltxt).group(1))
        quoted_lead_time = float(re.search('Quoted lead time: (\d+[.]\d+) day',htmltxt).group(1))
        revenue_per_order = float(re.search('Revenue per order: (\d+[.]\d+) dollars',htmltxt).group(1))



        return dict(revenue_per_order=revenue_per_order,kits_per_order =kits_per_order ,wip_limit=wip_limit,contract_type=contract_type,
                    lot_size=lot_size,max_lead_time=max_lead_time,quoted_lead_time=quoted_lead_time)

    def get_inventory_settings(self):
        ''' Successful response looks like this

MATERIALS MENU
 Name: encinitas
Unit Cost:  $ 600.0
Order Cost:  $ 1000.0
Lead Time: 15 day(s)
Reorder Point: 141 kits
Order Quantity:
185 kits
Material order of 185  kits due to arrive in 5.2 simulated days
Please click on a button...

        '''

        url = "http://{0}.responsive.net/Littlefield/MaterialMenu".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        LOGGER.info("get_inventory_settings : Sending Request")

        content = self.lfwebsite.get_request(url)
        htmltxt = BeautifulSoup(content,'lxml').get_text().replace("\\n","\n")
        LOGGER.debug(htmltxt)

        outstanding_kits , outstanding_kits_eta = 0,999.0

        unit_cost =  float(re.search('Unit Cost:\s+[$]\s+(\d+[.]\d+)',htmltxt).group(1))
        order_cost = float(re.search('Order Cost:\s+[$]\s+(\d+[.]\d+)',htmltxt).group(1))
        lead_time =  float(re.search('Lead Time:\s+(.*?)\s+day',htmltxt).group(1))
        reoder_point =  int(re.search('Reorder Point:\s+(.*?)\s+kits',htmltxt).group(1))
        order_quantity = int(re.search('Order Quantity:\s+(.*?)\s+kits',htmltxt,re.DOTALL|re.I).group(1))
        if re.search('Material order of',htmltxt,re.DOTALL|re.I):
            outstanding_kits = int(re.search('Material order of (\d+)  kits due to arrive .*? simulated',htmltxt,re.DOTALL|re.I).group(1))
            outstanding_kits_eta = float(re.search('Material order of.*?kits due to arrive in (\d+[.]\d+|\d+) simulated days',htmltxt,re.DOTALL|re.I).group(1))


        return dict(unit_cost=unit_cost,order_quantity=order_quantity,order_cost=order_cost,
                    reoder_point=reoder_point,lead_time=lead_time,outstanding_kits_eta=outstanding_kits_eta,outstanding_kits=outstanding_kits)
    def get_station_settings(self,station_id):
        '''
        successful response looks like

Littlefield Technologies -
STATION 1 MENU
 Name: group4
 Number of Machines: 2
Scheduling Policy: FIFO
Purchase Price: $ 90,000
Retirement Price: $ 50,000


Please click on a button...
        :return:
        '''
        url = "http://{0}.responsive.net/Littlefield/StationMenu?id={1}".format(self.competition_id,station_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        LOGGER.info("get_station_settings : Sending Request")
        content = self.lfwebsite.get_request(url)
        htmltxt = BeautifulSoup(content,'lxml').get_text().replace("\\n","\n")
        LOGGER.debug(htmltxt)

        machine_count =  int(re.search('Number of Installed Machines:\s+(\d+)',htmltxt).group(1))
        sched_policy = re.search('Scheduling Policy:\s+(.*?)\n',htmltxt).group(1)
        cost_price =  float(re.search('Purchase Price:\s+[$]\s+(\d.*?)\s',htmltxt).group(1).replace(',','').strip())
        salvage_value =  float(re.search('Retirement Price:\s+[$]\s+(\d.*?)\s',htmltxt).group(1).replace(',','').strip())
        return dict(machine_count=machine_count,station_id=station_id,cost_price=cost_price,
                    salvage_value=salvage_value,sched_policy=sched_policy)

        pass


    def confirm_transaction(self,url,trans_content):
        LOGGER.warn("Begin transaction ( %r , %r )"%(url,trans_content))
        body = urllib.parse.urlencode(trans_content)
        initial_response = self.lfwebsite.post_request(url,body)

        htmltxt = BeautifulSoup(initial_response,'lxml').get_text().replace("\\n","\n")
        LOGGER.warning(htmltxt)

        html = str(initial_response).replace("\\\'",'"')
        trans = re.search('name="trans".*?value="(.*?)"',html).group(1)
        LOGGER.warn("First Phaze - Transaction Token :%r \n committing"%(trans))
        data = {'pwd': self.password, "submit":"confirm","cancel":"cancel",'trans':trans}
        body = urllib.parse.urlencode(data)
        LOGGER.info("switch_Contract: confirming transaction : %r"%trans)
        content = self.lfwebsite.post_request(url,body)
        LOGGER.warn("Transaction Completed ")

        htmltxt = BeautifulSoup(content,'lxml').get_text().replace("\\n","\n")
        LOGGER.warning(htmltxt)

    # maxwip=11&contractOpt=1&submit=ok&cancel=cancel
    def change_WIP(self,wip=0):
        LOGGER.info("switch_Contract: begin")
        contract_settings = self.get_order_settings()
        current_wip = contract_settings['wip_limit']
        LOGGER.info("Current wip_limit :{0}".format(current_wip))

        print  ("current_wip ",current_wip)
        if(current_wip == wip):
            LOGGER.info("No WIP Change Needed")
            return (wip,current_wip)

        LOGGER.warning("Changing WIP from %r To %r"%(current_wip,wip))


        #curl "http://ops.responsive.net/Littlefield/OrdersForm" -H "Cookie: JSESSIONID=35E78B550E908630A2FD18FD3C0A3C5E" -H
        #  "Origin: http://ops.responsive.net" -H "Accept-Encoding: gzip, deflate" -H "Accept-Language: en-US,en;q=0.8"
        #  -H "Upgrade-Insecure-Requests: 1" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36
        # (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36" -H "Content-Type: application/x-www-form-urlencoded"
        # -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" -H "Cache-Control:
        #  max-age=0" -H "Referer: http://ops.responsive.net/Littlefield/OrdersForm" -H "Connection: keep-alive" -
        # -data "contractOpt=2&submit=ok&cancel=cancel" --compressed
        url = "http://{0}.responsive.net/Littlefield/OrdersForm".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        data = {'maxwip':wip,"submit":"ok","cancel":"cancel"}

        LOGGER.info("switch_Contract: making request")

        self.confirm_transaction(url,data)

        LOGGER.warning("switch_Contract: Order confirmed")
        return (wip,current_wip)


    # maxwip=11&contractOpt=1&submit=ok&cancel=cancel
    def set_inventory_order_size(self,quant=230):
        LOGGER.info("Set Inventory Size: begin")


        LOGGER.warning("Inventory Size to %r"%(quant))

        #curl "http://ops.responsive.net/Littlefield/OrdersForm" -H "Cookie: JSESSIONID=35E78B550E908630A2FD18FD3C0A3C5E" -H
        #  "Origin: http://ops.responsive.net" -H "Accept-Encoding: gzip, deflate" -H "Accept-Language: en-US,en;q=0.8"
        #  -H "Upgrade-Insecure-Requests: 1" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36
        # (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36" -H "Content-Type: application/x-www-form-urlencoded"
        # -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" -H "Cache-Control:
        #  max-age=0" -H "Referer: http://ops.responsive.net/Littlefield/OrdersForm" -H "Connection: keep-alive" -
        # -data "contractOpt=2&submit=ok&cancel=cancel" --compressed

        # Request URL:http://opscom.responsive.net/Littlefield/MaterialForm

        url = "http://{0}.responsive.net/Littlefield/MaterialForm".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        #point=234&quant=230&submit=ok&cancel=cancel
        data = {'quant':quant,"submit":"ok","cancel":"cancel"}

        LOGGER.info("switch_Contract: making request")

        self.confirm_transaction(url,data)

        LOGGER.warning("switch_Contract: Order confirmed")



    def switch_Contract(self,contract_opt=2):
        LOGGER.info("switch_Contract: begin")
        contract_settings = self.get_order_settings()
        current_contract_type = contract_settings['contract_type']
        LOGGER.info("Current Contract Type :{0}".format(current_contract_type))

        print  ("current_contract_type ",current_contract_type )
        if(current_contract_type == contract_opt):
            LOGGER.info("No Contract Change Needed")
            return (current_contract_type,contract_opt)

        LOGGER.warning("Changing Contract from %r To %r"%(current_contract_type,contract_opt))


        #curl "http://ops.responsive.net/Littlefield/OrdersForm" -H "Cookie: JSESSIONID=35E78B550E908630A2FD18FD3C0A3C5E" -H
        #  "Origin: http://ops.responsive.net" -H "Accept-Encoding: gzip, deflate" -H "Accept-Language: en-US,en;q=0.8"
        #  -H "Upgrade-Insecure-Requests: 1" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36
        # (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36" -H "Content-Type: application/x-www-form-urlencoded"
        # -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" -H "Cache-Control:
        #  max-age=0" -H "Referer: http://ops.responsive.net/Littlefield/OrdersForm" -H "Connection: keep-alive" -
        # -data "contractOpt=2&submit=ok&cancel=cancel" --compressed
        url = "http://{0}.responsive.net/Littlefield/OrdersForm".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        data = {'contractOpt':contract_opt,"submit":"ok","cancel":"cancel"}

        LOGGER.info("switch_Contract: making request")

        self.confirm_transaction(url,data)

        LOGGER.warning("switch_Contract: Order confirmed")
        return (current_contract_type,contract_opt)


    def switch_station_priority(self,priority_option='pri4'):
        if(priority_option not in ['pri4','pri2','fifo']):
            raise Exception("Invalid Priority %r "%priority_option)
        #curl "http://ops.responsive.net/Littlefield/StationForm" -H "Cookie: JSESSIONID=2E44D5EF7A5EC915EC17302024F904FB"
        # -H "Origin: http://ops.responsive.net" -H "Accept-Encoding: gzip, deflate" -H "Accept-Language: en-US,en;q=0.8"
        # -H "Upgrade-Insecure-Requests: 1" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
        # Chrome/48.0.2564.116 Safari/537.36" -H "Content-Type: application/x-www-form-urlencoded"
        # -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        # -H "Cache-Control: max-age=0" -H "Referer: http://ops.responsive.net/Littlefield/StationForm?id=2"
        # -H "Connection: keep-alive" --data "count=5&rule=pri2&id=2&submit=ok&cancel=cancel" --compressed

        # url = "http://ops.responsive.net/Littlefield/StationMenu?id=2"
        # content = make_get(url)
        LOGGER.info("switch_station_priority :Begin")
        station2_info = self.get_station_settings(2)

        url = "http://{0}.responsive.net/Littlefield/StationForm".format(self.competition_id)
        trans_req = "count={0}&rule=pri2&id=2&submit=ok&cancel=cancel".format(station2_info['machine_count'])

        self.confirm_transaction(url,trans_req)

        LOGGER.info("switch_station_priority : Order Executed")

    @property
    def plantsettings(self):
        plant_settings = {}
        plant_settings['inventory'] = self.get_inventory_settings()
        plant_settings['order'] = self.get_order_settings()
        plant_settings['station_1'] = self.get_station_settings(1)
        plant_settings['station_2'] = self.get_station_settings(2)
        plant_settings['station_3'] = self.get_station_settings(3)
        plant_settings['plant_info'] ={"competition_id":self.competition_id}
        json_f = "%s/plant_settings.json"%DATA_DIR
        json.dump(plant_settings,open(json_f,'w'),indent=1)
        return plant_settings


class SimStatus:
    PLANT_CSV = '%s/lf.raw.csv'%(TMP_DIR )
    CASH_CSV = '%s/cash.csv'%(TMP_DIR )
    TEAMS_CSV = "%s/team_standings.csv"%TMP_DIR
    def __init__(self,lfwebsite,competition_id="ops",institution="ucsd1",username="group4",password="safari14"):
        self.competition_id,self.username,self.password,self.institution= competition_id,username,password,institution
        self.lfwebsite = lfwebsite or LittleFieldWebSite(competition_id,institution,username,password)
    def current_day(self):
        _df = pd.read_csv(self.PLANT_CSV)
        return int(_df['day'].max())
    def fetch_plant_status(self):

        dfs1 =[self.getPlot(plot) for plot in ['JOBIN','JOBQ','S1Q','S1UTIL','S2Q','S2UTIL','S3Q','S3UTIL','INV','CASH']]
        dfsk =[self.getPlotK(plot) for plot in ['JOBT','JOBOUT','JOBREV']]
        dfs = dfs1 +dfsk
        df = pd.concat(dfs,1)
        df['S1IN'] = df['JOBIN'] *60

        columns = ['CASH','INV', 'JOBIN', 'JOBQ', 'JOBOUT_075', 'JOBOUT_100', 'JOBOUT_125','JOBT_075', 'JOBT_100', 'JOBT_125',
                   'JOBREV_075', 'JOBREV_100', 'JOBREV_125','S1IN','S1Q', 'S1UTIL','S2Q', 'S2UTIL', 'S3Q', 'S3UTIL' ]
        df = df.reindex_axis(columns, axis=1)
        csv_file = self.PLANT_CSV
        df.to_csv(csv_file)
        with open(csv_file,'r') as f:
            lines = f.readlines()
        lines =[line for line in lines if line.find(",,,,,,,,,,") == -1]
        with open(csv_file,'w') as f:
            f.writelines(lines)
        df = pd.read_csv(csv_file)

        return df

    def fetch_cash_standing(self):
        '''
        successful response looks like

Littlefield Technologies -
STATION 1 MENU
 Name: group4
 Number of Machines: 2
Scheduling Policy: FIFO
Purchase Price: $ 90,000
Retirement Price: $ 50,000


Please click on a button...
        :return:
        '''

        url = "http://{0}.responsive.net/Littlefield/CashStatus".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        LOGGER.info("get_cash_standing : Sending Request")
        content = self.lfwebsite.get_request(url)
        htmltxt = BeautifulSoup(content,'lxml')
        LOGGER.debug(htmltxt)

        rows = []
        for row in htmltxt.find('table').find_all('tr'):
            _row =[cell.get_text().strip().replace(',','') for cell in  row.find_all("td")]
            rows.append(_row)

        cash_dict = dict(rows)
        '''
        {'revenue': '228362', 'Cash on Hand': '1096231', 'Description': 'Amount ($)', 'Cash Uses': '.',
         'Starting Cash': '1000000', 'debt interest': '0', 'Debt': '0', 'Cash Sources': '.',
         'interest': '13869', 'Cash Balance': '1096231', 'inventory': '146000'}
        dict_keys(['revenue', 'Starting Cash', 'Cash Sources', 'Description', 'Cash Balance', 'Cash Uses', 'interest'])
        '''
        current_day = self.current_day()

        nowTS = pd.Timestamp(datetime.now())
        df_data = {'TS':[nowTS],'day':[current_day],
                   'CASH':[float(cash_dict['Cash Balance'])],
                   'REVENUE':[float(cash_dict['revenue'])],
                   'INT':[float(cash_dict['interest'])]
                   }
        delta_frame = pd.DataFrame(data=df_data)

        csv_file = self.CASH_CSV
        df = None
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)


        if df is None:
            df = delta_frame
        else:
            df = df.append(delta_frame,ignore_index=False)

        colns = "TS,day,CASH,BALANCE,DEBT,INT_D,INT_I,INV,REVENUE".split(',')
        df = df.reindex_axis(colns,axis=1)


        df.to_csv(csv_file,index=False)

        return dict(cash_balance=float(cash_dict['Cash Balance']))
        pass


    def fetch_team_standings(self):
        url = "http://{0}.responsive.net/Littlefield/Standing".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        LOGGER.info("get_current_standings : Sending Request ")
        content = self.lfwebsite.get_request(url)

        current_day = self.current_day()
        # print("Current Day ",current_day)

        teams_data = []
        soup = BeautifulSoup(content,'lxml')
        table = soup.find('table')
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            teams_data.append([ele for ele in cols if ele]) #

        csv_file = self.TEAMS_CSV
        df = None
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)

        nowTS = pd.Timestamp(datetime.now())
        # print(nowTS)
        df_data = {'TS':[nowTS],'day':[current_day]}
        for row in teams_data[1:]:
            df_data[row[1]] = [float(row[2].replace(',',''))]
        delta_frame = pd.DataFrame(data=df_data)
        if df is None:
            df = delta_frame
        else:
            df = df.append(delta_frame,ignore_index=False)

        colns = [c for c in df.columns if c not in ['TS','day']]
        colns.sort()
        colns =['TS','day'] + colns
        df = df.reindex_axis(colns,axis=1)
        df.to_csv(csv_file,index=False)

        # data = {'time':time.time(),'day':days_elapsed}
        # for x in re.findall('<font face=arial>(group\d)</font>.*?<TD.*?<font face=arial>(.*?)</font>',html,re.DOTALL):
        #     group,cash = x[0],x[1].replace(',','')
        #     data[group] =cash
        #
        # csv_path = "group_stats.csv"
        #
        # with open(csv_path,"a") as f:
        #     print (data['time'],data['day'],data['group1'],data['group2'],data['group3'],data['group4'],data['group5'], file=f)

    def getPlotK(self,plotId):
        #Request URL:http://ops.responsive.net/Littlefield/Plotk
        url = "http://{0}.responsive.net/Littlefield/Plotk".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        data = {'download': 'download', 'data': plotId,'sets':'3'}
        body = urllib.parse.urlencode(data)
        content = self.lfwebsite.post_request(url,body)
        csv_file ='%s/%s.tsv'%(TMP_DIR ,plotId)
        with open(csv_file,'wb') as f:
            f.write(content)
        df = pd.read_csv(csv_file,sep='\t',index_col='day',header=1)
        df.columns =["%s_%s"%(plotId,ix) for ix in ['075','100','125']]
        df = df.replace(r'\s+', np.nan, regex=True)
        for c in df.columns:
            if df[c].dtype =='O':
                df[c] = df[c].apply(lambda x: x.replace(',','')).astype('float')
        df.fillna(0,inplace=True)
        return df

    def getPlot(self,plotId):
        url = "http://{0}.responsive.net/Littlefield/Plot1".format(self.competition_id) #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
        data = {'download': 'download', 'data': plotId}
        body = urllib.parse.urlencode(data)

        content = self.lfwebsite.post_request(url,body)
        csv_file ='%s/%s.tsv'%(TMP_DIR ,plotId)

        with open(csv_file,'wb') as f:
            f.write(content)
        df = pd.read_csv(csv_file,sep='\t',index_col='day')
        df.columns =[plotId]
        if df[plotId].dtype =='O':
            df[plotId] = df[plotId].astype('str')
            series = df[plotId].apply(lambda x: x.replace(',','')).astype('float')
            df[plotId] = series
        return df




if __name__ == "__main__":
    config_logging(level=logging.INFO)
    if len(sys.argv) < 2:
        competition_id,institution,username,password = 'opscom','opscom','encinitas','7rosemary'

        # competition_id,institution,username,password = 'littlefield','demo','operators','goteam'
    elif sys.argv[1] == 'ucsd' :
        competition_id,institution,username,password = 'ops','ucsd1','group4','safari14'
    else :
        competition_id,institution,username,password = 'mit','demo','encinitas','roasemary4'

    _LFWebSite = LittleFieldWebSite(competition_id,institution,username,password )
    _SIMSettings = SimSettings(_LFWebSite,competition_id,institution,username,password )
    _SIMStatus = SimStatus(_LFWebSite,competition_id,institution,username,password )
    # print(_SIMSettings.get_order_settings())
    # print(_SIMSettings.get_inventory_settings())
    # print(_SIMSettings.get_station_settings(1))
    # print(_SIMSettings.get_station_settings(2))
    # print(_SIMSettings.get_station_settings(3))
    _SIMStatus.fetch_plant_status()
    _SIMStatus.fetch_cash_standing()
    _SIMStatus.fetch_team_standings()
    _SIMSettings.plantsettings
