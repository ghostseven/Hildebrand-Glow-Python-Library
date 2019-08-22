from os import getenv
from os.path import expanduser, exists
import json, time
import warnings
import logging
import urllib.parse, urllib.request
from datetime import datetime, timedelta

######################## AUTHENTICATION INFORMATION ######################

# Authentication use :
#  1 - Values hard coded in the library
#  2 - The .hildebrand.credentials file in JSON format in your home directory
#  3 - Values defined in environment variables : APP_ID, USERNAME, PASSWORD
#      Note: The USERNAME environment variable may interfer with the envvar used by Windows for login name
#            if you have this issue, do not forget to "unset USERNAME" before running your program

# Each level override values defined in the previous level. 

# 1 : Embedded credentials
cred = {                    # You can hard code authentication information in the following lines
        "APP_ID" :  "",     # Your applicationId as provided by Hildebrand
        "USERNAME" : "",    # Your account username
        "PASSWORD" : ""     # Your account password
        }

# Other authentication setup management (optionals)

CREDENTIALS = expanduser("~/.hildebrand.credentials")

def getParameter(key, default):
    return getenv(key, default[key])

# 2 : Override hard coded values with credentials file if any
if exists(CREDENTIALS) :
    with open(CREDENTIALS, "r") as f:
        cred.update({k.upper():v for k,v in json.loads(f.read()).items()})

# 3 : Override final value with content of env variables if defined
_APP_ID     = getParameter("APP_ID", cred)
_USERNAME      = getParameter("USERNAME", cred)
_PASSWORD      = getParameter("PASSWORD", cred)

#########################################################################

# API Endpoints

_BASE_URL = "https://api.glowmarkt.com/"
_AUTH_REQ       = _BASE_URL + "api/v0-1/auth"
_RESOURCE_REQ   = _BASE_URL + "api/v0-1/resource"

# Logging
logger = logging.getLogger("hildebrand")

class AuthFailure( Exception ):
    pass

class Glow:
    """Hildebrand Glow API"""
    def __init__(self, appId=_APP_ID,
                       username=_USERNAME,
                       password=_PASSWORD):
        """
        Args:
            appID:      Application ID as defined in API docs, this is technically fixed for now but may change in the future.
            username:   User name as per your account 
            password:   Password as per your account
        """
        head = {
            "applicationId": appId
        }

        body = {
            "username" : username,
            "password" : password
        }

        resp = postRequest(_AUTH_REQ, head, body)
        if not resp: raise AuthFailure("Authentication request rejected")

        self._appId = appId
        self._username = username
        self._password = password
        self._accessToken = resp['token']
        self.accountId = resp['accountId']
        self.expiration = resp['exp']
        self.functionalGroupAccounts = resp['functionalGroupAccounts']
        self.userGroups = resp['userGroups']
        self.getResources

    @property
    def accessToken(self):
        """
        Desc:
            Allways up to date access token, if it reaches expiry it triggers a request to get a new one and then returns that.

        Args:
            None
        """
        if self.expiration <= time.time(): # Token should be renewed
            head = {
                "applicationId": self._appId
            }
            body = {
                "username" : self._username,
                "password" : self._password
            }            
            resp = postRequest(_AUTH_REQ, head, body)
            self._accessToken = resp['token']
            self.accountId = resp['accountId']
            self.expiration = resp['exp']
            self.functionalGroupAccounts = resp['functionalGroupAccounts']
            self.userGroups = resp['userGroups']
            self.getResources
        return self._accessToken

    @property
    def getResources(self):
        """
        Desc:
            Returns available resource list, at the current time it should contain four different resources as follows;
            electricity.consumption         - Electricity in energy units (Wh. / kWh.)
            electricity.consumption.cost    - Electricity in monetary units (pence) NOTE: Broken if used for /current, work around in place.
            gas.consumption                 - Gas in energy units (Wh. / kWh.)
            gas.consumption.cost            - Gas in monetary units (pence) NOTE: Broken if used for /current, work around in place.
            
            It also updates two variables to store the id's of electricity.consumption and gas.consumption for use later.
        Args:
            None
        """   
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        resp = postRequest(_RESOURCE_REQ, head)
        for r in resp:
            if r['classifier'] == 'electricity.consumption': self.elecConsumptionId = r['resourceId']
            if r['classifier'] == 'gas.consumption': self.gasConsumptionId = r['resourceId']
        return resp

    def getReading(self, id, dfrom, dto, period='P1D', offset=0, func='sum'):
        """
        Desc:
            Returns time series data of a given resource.
        Args:
            id:     resourceId to take the reading against
            dfrom:  date from syntax is yyyy-mm-ddThh:mm:ss (i.e. 2017-09-19T10:00:00)
            dto:    date to syntax is yyyy-mm-ddThh:mm:ss (i.e. 2017-09-19T10:00:00)
            period: The aggregation level in which the data is to be returned (ISO 8601).
                        PT1M (minute level, only elec) 
                        PT30M (30 minute level) 
                        PT1H (hour level) 
                        P1D (day level) 
                        P1W (week level, starting Monday) 
                        P1M (month level) 
                        P1Y (year level)
            offset: offset in minutes from UTC for timestamps use this to adjust to local timezone
            fun:    function to apply to returned data such as sum, avg 
        """    
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        params = {
            "from": dfrom,
            "to": dto,
            "period": period,
            "offset": offset,
            "function": func
        }
        _res_url = _RESOURCE_REQ + "/" + id + "/readings?" + urllib.parse.urlencode(params)
        resp = postRequest(_res_url, head)
        return resp

    def getCurResource(self, id):
        """
        Desc:
            Returns the current data of a given resource.
        Args:
            id: resourceId to return 
        """  
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        _res_url = _RESOURCE_REQ + "/" + id + "/current"
        resp = postRequest(_res_url, head)
        return resp        

    @property
    def getElecCurrent(self):
        """
        Desc:
            Returns the current electrical usage, both W/kWh, cost and current tariff rate.
        NOTE:
            A call requesting the unit cost (for current usage) is broken in the API so we work around by taking usage plus 
            tariff and manually calculating.
        Args:
            None
        """  
        _return = self.getCurResource(self.elecConsumptionId)
        _tariff = self.getElecTariff['data'][0]['plan'][0]['planDetail']
        _return['rate'] = _tariff[0]['rate']
        _return['standing'] = _tariff[1]['standing']
        _return['cost'] = toCost(_return['rate'], _return['data'][0][1], _return['units'])
        return _return

    @property
    def getGasCurrent(self):
        """
        Desc:
            Returns the current electrical usage, both W/kWh, cost and current tariff rate.
        NOTE:
            Gas readings are taken every 30 minutes so this is a realtime as it gets, this is also a back 
            hack of broken API function.  If you call the standard current usage you get a meter read rather 
            than the current usage, but you can use /reading to look at the last hour and work out the diff, this is done here.

            Also a call requesting the unit cost (for current usage) is broken in the API so we work around by taking usage and 
            tariff and manually calculating.
        Args:
            None
        """  
        _today = datetime.today()
        _todayM30M = _today - timedelta(minutes=30)
        _dtTo = _today.strftime('%Y-%m-%dT%H:%M:00')
        _dtFrom = _todayM30M.strftime('%Y-%m-%dT%H:%M:00')
        _gu = self.getReading(self.gasConsumptionId, _dtFrom, _dtTo, 'PT30M', 0, 'sum')
        _return = self.getCurResource(self.gasConsumptionId)
        _return['data'][0] = _gu['data'][0]  
        _tariff = self.getGasTariff['data'][0]['plan'][0]['planDetail']
        _return['rate'] = _tariff[0]['rate']
        _return['standing'] = _tariff[1]['standing']
        _return['cost'] = toCost(_return['rate'], _return['data'][0][1], _return['units'])
        return _return 

    @property
    def getElecTariff(self):
        """
        Desc:
            Returns the current electrical tariff details.
        Args:
            None
        """  
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        _res_url = _RESOURCE_REQ + "/" + self.elecConsumptionId + "/tariff"
        resp = postRequest(_res_url, head)
        return resp    

    @property
    def getGasTariff(self):
        """
        Desc:
            Returns the current gas tariff details.
        Args:
            None
        """  
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        _res_url = _RESOURCE_REQ + "/" + self.gasConsumptionId + "/tariff"
        resp = postRequest(_res_url, head)
        return resp   

    @property
    def getElecMeterRead(self):
        """
        Desc:
            Returns the current electrical meter reading.
        Args:
            None
        """  
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        _res_url = _RESOURCE_REQ + "/" + self.elecConsumptionId + "/meterread"
        resp = postRequest(_res_url, head)
        return resp     

    @property
    def getGasMeterRead(self):
        """
        Desc:
            Returns the current gas meter reading.
        NOTE:
            The actual function in the API to do this is broken, it appear to return the electrical reading again for gas
            it is worked around as the gas current consuption check returns a meter read rather than current consumption
            happy little bugs working to fix themselves. /bobrossclouds
        Args:
            None
        """  
        head = { 
            "applicationId": self._appId,
            "token": self.accessToken
        }
        _res_url = _RESOURCE_REQ + "/" + self.gasConsumptionId + "/meterread"
        _return = postRequest(_res_url, head)
        _gComp = self.getCurResource(self.gasConsumptionId)
        _return['data'][0][0] = _gComp['data'][0][0]
        _return['data'][0][1] = _gComp['data'][0][1] * 1000
        return _return
        
# Utility Functions 
def toCost(rate, ammount, unit):
    try:
        if unit == 'W': ammount = ammount/1000
        return ammount * rate
    except:
        return 0

def postRequest(url, head=None, body=None, timeout=10):
    req = urllib.request.Request(url)
    req.add_header("Content-Type", "application/json")
    if head:
        for k in head:
            req.add_header(k,head[k])
    if body:
        body = json.dumps(body).encode('utf-8')
    try:
        resp = urllib.request.urlopen(req, body, timeout=timeout) if body else urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as err:
        logger.error("code=%s, reason=%s" % (err.code, err.reason))
        return None
    data = b""
    for buff in iter(lambda: resp.read(65535), b''): data += buff
    returnedContentType = resp.getheader("Content-Type")
    return json.loads(data.decode("utf-8")) if "application/json" in returnedContentType else data

# Testing - Direct Call
if __name__ == "__main__":
    from sys import exit, stdout, stderr
    
    if not _USERNAME or not _PASSWORD :
           stderr.write("Missing authentication params, check source, config or env")
           exit(1)

    glow = Glow()
    print("Access Token: {}\n".format(glow.accessToken))
    print("Account ID {}\n".format(glow.accountId))
    print("Expires: {}\n".format(glow.expiration))
    print("Resources: {}\n".format(glow.getResources))
    print("Gas Consumption ID: {}\n".format(glow.gasConsumptionId))
    print("Elec Consumption ID: {}\n".format(glow.elecConsumptionId))
    print("Elec Current: {}\n".format(glow.getElecCurrent))
    print("Gas Current: {}\n".format(glow.getGasCurrent))
    print("Elec Tariff: {}\n".format(glow.getElecTariff))
    print("Gas Tariff: {}\n".format(glow.getGasTariff))
    print("Elec Meter Read: {}\n".format(glow.getElecMeterRead))
    print("Gas Meter Read: {}\n".format(glow.getGasMeterRead))