from websocket import create_connection
import json
import time
import os
import dotenv
import hashlib
import hmac
from pydantic import TypeAdapter

from .ws_api_schema import EndPoint, P, R, ReturnSchema
from ...decorators import error_handle

CRITICAL = False
URL = "wss://ws-fapi.binance.com/ws-fapi/v1"
TEST_URL = "wss://testnet.binancefuture.com/ws-fapi/v1"

# Load .env file
dotenv.load_dotenv()

# API keys
KEY = os.getenv("KEY", "")
SECRET = os.getenv("SECRET", "")
TEST_KEY = os.getenv("TEST_KEY", "")
TEST_SECRET = os.getenv("TEST_SECRET", "")

class WSapi:
    def __init__(self, test:bool):
        self.ws = create_connection(TEST_URL if test else URL, timeout=5)
        # print("Connected successfully!")

        # load api key
        if test:
            self._key = TEST_KEY
            self._secret = TEST_SECRET
        else:
            self._key = KEY
            self._secret = SECRET

    @staticmethod
    def _timestamp(offset:int=0)->int:
        '''
        Params
            offset: in milliseconds
        '''
        return int(time.time()*1000+offset) # 13 dig timestamp
    
    @error_handle
    def send(self, endpoint:EndPoint[P, R], param:P=None)->ReturnSchema[R]:
        param = param or {}
        param:dict = {k:v for k,v in dict(param).items() if v is not None}

        if endpoint.signed:
            param |= {"apiKey":self._key, "timestamp":self._timestamp()}
            # config query for signature
            lst = [f"{k}={v}" for k, v in param.items()]
            lst.sort()
            query = "&".join(lst)

            # add sign to query
            signature = hmac.new(
                self._secret.encode("utf-8"), 
                query.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            param |= {"signature":signature}
        payload = {
            "id":str(int(time.time()*1000)),
            "method":endpoint.method,
            "params":param
        }
        
        self.ws.send(json.dumps(TypeAdapter(dict).dump_python(payload, mode="json")))
        res = json.loads(self.ws.recv())
        # not sure what formate it is for error
        ### need to add error handle

        return endpoint.return_type.model_validate(res)

    def close(self):
        self.ws.close()
        
# also create price alert for ws api

if __name__ == "__main__":
    temp = WSapi()
    print(temp.account_balance())
    