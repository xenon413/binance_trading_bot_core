import requests
import json
import time
import os
import dotenv
import traceback
import hashlib
import hmac
from .rest_api_schema import RestEndpointCollection, EndPoint, P, R
from ...log_handle import LogHandle
from ...decorators import error_handle
from ...constants import BotAction, LogLevel
from ...exceptions import BotError, BinanceError


# Load .env file
dotenv.load_dotenv()

# endpoints
URL="https://fapi.binance.com"
TEST_URL="https://testnet.binancefuture.com"

# API keys
KEY = os.getenv("KEY", "")
SECRET = os.getenv("SECRET", "")
TEST_KEY = os.getenv("TEST_KEY", "")
TEST_SECRET = os.getenv("TEST_SECRET", "")
RECV_WINDOW = 5000

class BinanceRestapi:
    def __init__(self, test:bool, recvWindow:int|None=None):
        # setup log handle
        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)

        self.recvWindow = recvWindow or RECV_WINDOW

        # load api key
        if test:
            self.url = TEST_URL
            self.key = TEST_KEY
            self.secret = TEST_SECRET
        
        else:
            self.url = URL
            self.key = KEY
            self.secret = SECRET

        # setup session
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY":self.key})

    @error_handle
    def request(self, endpoint: EndPoint[P, R], param: P = None) -> R:
        param:dict = (param or {}).copy()
        try:
            # add param for signed
            if endpoint.signed:
                param |= {"timestamp": self._timestamp(), "recvWindow": self.recvWindow}

                # config query
                query = "&".join([f"{k}={v}" for k, v in param.items() if v is not None])

                # add sign to query
                signature = hmac.new(
                    self.secret.encode("utf-8"), 
                    query.encode('utf-8'), 
                    hashlib.sha256
                ).hexdigest()
                param |= {"signature":signature}

            # construct full url
            full_url = f"{self.url}{endpoint.name}"

            # actual request
            start = time.perf_counter()
            r = self.session.request(endpoint.method, full_url, params=param)
            end = time.perf_counter()

            self._log_handle.write_log(f"method: {endpoint.method}, url: {full_url}, param:{param}, fetch time: {end-start}", LogLevel.DEBUG)
        
        except Exception as e:
            # usually internet disconnect
            raise BotError(f"http error: {e}\n{traceback.format_exc()}", BotAction.RETRY, 10, 30, 3)

        res = json.loads(r.text)
        ### check for request limit record header info

        # check for error
        err = BinanceError.get_by_code(res["code"]) if isinstance(res, dict) and res.get("code", 200) != 200 else None        
        if err is not None:
            raise err.get_error_config()
        return endpoint.return_type.model_validate(res)
    
    @staticmethod
    def _timestamp(offset:int=0)->int:
        '''
        Params
            offset: in milliseconds
        '''
        return int(time.time()*1000+offset) # 13 dig timestamp
    
    def set_recvWindow(self, recvWindow:int=RECV_WINDOW)->None:
        self.recvWindow = recvWindow

    def close(self):
        self.session.close()

# also create price alert for rest api
__all__ = ["BinanceRestapi"]

if __name__ == "__main__":
    # Example usage:
    api = BinanceRestapi(test=True)
    res = api.request(RestEndpointCollection.CONT_KLINE.value, {})