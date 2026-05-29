import queue
import websocket
import time
import json
import pandas as pd
from abc import abstractmethod
from collections import defaultdict, deque
from decimal import Decimal
from typing import Literal
import threading

from ...base_thread import Base
from ...constants import LogLevel, Symbol, CandleInterval, BotAction, ContractType
from ...exceptions import BotError
from ...log_handle import LogHandle
from .market_stream_schema import (
    KlineStreamStatus, RoutingTable, StreamBuffer, EndPoint,
    ContKlineParams, KlineStatus, ContKlineReturn, P, R, StreamEndpointCollection,
    OrderBookTickerParams, OrderBookTickerReturn, SymbolPriceTickerReturn
)
from ..rest_api import RestEndpointCollection, BinanceRestapi

# DOCUMENT:
# https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams

# mapping
URL = "wss://fstream.binance.com"
TEST_URL = "wss://fstream.binancefuture.com"

SINGLE_STREAM = "ws"
COMBINED_STREAM = "stream"

CRITICAL=False

class WSManager(Base):
    def __init__(self, test:bool):
        super().__init__(CRITICAL)
        self.base = TEST_URL if test else URL 
        self.current_connection = None

        # path->ws
        self._ws:dict[str, websocket.WebSocketApp] = {"public":None, "market":None, "private":None}
        self._routing_table = RoutingTable()
        # just in case of python garbage collector
        self._ws_th:dict[str, threading.Thread] = {}
        self.start()
        for _ in range(10):
            for k, ws in self._ws.items():
                if not self.connect(ws, k):
                    time.sleep(0.5)
                    break
            else:
                break # if all connected exit
        else:
            self._log_handle.write_log("websocket init timeout", LogLevel.WARNING)

    def connect(self, ws:websocket.WebSocketApp, name:str=" "):
        res = ws is not None and ws.sock and ws.sock.connected
        if res != self.current_connection:
            level = LogLevel.DEBUG if res else LogLevel.WARNING
            self._log_handle.write_log(f"ws stream {name} connected={res}", level)
            self.current_connection = res
        return res

    def _on_message(self, ws:websocket.WebSocketApp, message:str):
        res:dict = json.loads(message)
        # print(message)
        # handle combined streams
        if "stream" in message and "data" in message:
            endpoint = res.get("stream")
            data = res.get("data")
            self._routing_table.dispatch(endpoint, data)
            return

        # handle response message
        if "result" in res and "id" in res:
            self._log_handle.write_log(f"ws stream {ws.url} response: {message}", LogLevel.INFO)
            return
        
        # handle error message
        if "code" in message and "msg" in message:
            self._log_handle.write_log(f"ws stream {ws.url} error: {message}", LogLevel.WARNING)
            return
        
        self._log_handle.write_log(f"ws stream {ws.url} unhandled: {message}", LogLevel.CRITICAL)
        
    def _on_error(self, ws:websocket.WebSocketApp, error:str):
        self._log_handle.write_log(f"websocket {ws.url} error: {error}", LogLevel.WARNING)

    def _on_close(self, ws:websocket.WebSocketApp, close_status_code, close_msg):
        self._log_handle.write_log(f"websocket {ws.url} closed: status_code={close_status_code}, msg={close_msg}", LogLevel.INFO)

    def _on_open(self, ws:websocket.WebSocketApp):
        msg = {
            "method": "SET_PROPERTY",
            "params": ["combined", True],
            "id": 1
        }
        ws.send(json.dumps(msg))
        
        # safty for reconnecting
        self._routing_table = RoutingTable()
        self._log_handle.write_log(f"websocket {ws.url} opened", LogLevel.INFO)

    def _loop(self):
        for k in self._ws.keys():
            # access value
            ws = self._ws[k]

            for _ in range(10):
                if self.connect(ws, k):
                    break
                
                # case create websocket
                if ws is None:
                    self._log_handle.write_log(f"creating new websocket for {k}")
                    ws = websocket.WebSocketApp(
                        self.base+"/"+k+"/"+SINGLE_STREAM,
                        on_message=self._on_message,
                        on_close=self._on_close,
                        on_error=self._on_error,
                        on_open=self._on_open,
                    )
                    th = threading.Thread(
                        target=ws.run_forever,
                        kwargs={
                            'ping_interval': 20, 
                            'ping_timeout': 10
                        }
                    )
                    th.start()

                    self._ws_th[k] = th
                    self._ws[k] = ws
                time.sleep(0.5)

            else:
                self._log_handle.write_log(f"ws connect timeout for {k}", LogLevel.WARNING)
                # resets the ws if timeout for reconnection
                self._ws[k] = None

        # check connection every 1s and reconnect
        time.sleep(1)

    def _sub_unsub(self, endpoint:EndPoint, stream:str, sub:bool=True):
        method = "SUBSCRIBE" if sub else "UNSUBSCRIBE"

        msg = {
            "method":method,
            "params":[stream],
            "id":int(time.time()*1000)
        }

        ws = self._ws[endpoint.path]
        if self.connect(ws):
            data = json.dumps(msg)
            ws.send(data)
            self._log_handle.write_log(f"ws stream send: {data} to endpoint: {endpoint.path}", LogLevel.INFO)

        else:
            self._log_handle.write_log(f"ws {endpoint.path} endpoint not connected")

    def add_route(self, mode:Literal["queue", "sampling"], endpoint:EndPoint[P, R], params:P)->StreamBuffer[P, R]:
        '''return buff'''
        if self._routing_table.endpoint_exist(params.endpoint) == False:
            self._sub_unsub(endpoint, params.endpoint)

        # create buffer
        buff = StreamBuffer(mode, endpoint)
        self._routing_table.add_route(buff, params)
        return buff

    def close(self):
        for k in self._ws.keys():
            if self._ws[k] is not None:
                self._ws[k].close()
                
            self._ws[k] = None
        self.stop()
        
class WSKlineDF(Base):
    def __init__(self, manager:WSManager, rest_api:BinanceRestapi):
        super().__init__(CRITICAL)
        self.manager = manager
        self.status = KlineStreamStatus()
        self.rest_api = rest_api
        self.limit = 1500 # hard max limit on server side
        self.start()
        
    def _add_stream(self, params:ContKlineParams, buff:StreamBuffer|None=None):
        # get stream record
        res = self.rest_api.request(
            RestEndpointCollection.CONT_KLINE.value, 
            {"pair":params.pair, "interval":params.interval, "contractType":params.contractType, "limit":self.limit}
        )
            
        # add to manager
        if buff is None:
            buff = self.manager.add_route("queue", StreamEndpointCollection.CONT_KLINE.value, params)

        # add to status
        self.status.set_kline_status(False, res.df["open_time"].iloc[-1], res.df, buff, params)
    
    def _loop(self):
        for status in self.status.values():
            payload = status.buff.pop()
            # if no payload
            if payload is None:
                time.sleep(0.1)
                continue
            
            self._log_handle.write_log("start process data")
            if not payload.valid: 
                self._log_handle.write_log("timestamp out of bound, skip payload", LogLevel.WARNING)
                continue

            # snapshot
            is_close = status.is_close
            cur_open = status.cur_open
            df = status.df
            buff = status.buff
            params = ContKlineParams(pair=payload.symbol, contractType=payload.contract_type, interval=payload.kline.interval)

            # update data
            is_close = payload.kline.is_close

            # case same kline
            if payload.kline.open_time == status.cur_open:
                df.iloc[-1, :] = payload.kline.df_clean.iloc[-1].values

            # case switch kline
            elif payload.kline.open_time == status.next_open and status.is_close:
                df = pd.concat([df, payload.kline.df_clean], ignore_index=True)
                df = df.iloc[1:].reset_index(drop=True)
                cur_open = status.next_open
                
            # case delayed payload (for safty)
            elif payload.kline.open_time < status.cur_open:
                self._log_handle.write_log(f"delayed payload for {params.endpoint}, skip", LogLevel.WARNING)
                continue

            # case when shit goes wrong
            else:
                self._log_handle.write_log(f"resetting dataframe, skip payload", LogLevel.WARNING)
                self._add_stream(params, buff)
                continue

            # update kline status
            self._log_handle.write_log(f"before: {[x.event_time for x in self.status.values()]}")
            self.status.set_kline_status(is_close, cur_open, df, buff, params)
            self._log_handle.write_log(f"after: {[x.event_time for x in self.status.values()]}")
            self._log_handle.write_log(f"size: {[x.buff.size() for x in self.status.values()]}")

    def get_df(self, symbol:Symbol, interval:CandleInterval)->pd.DataFrame|None:
        params = ContKlineParams(pair=symbol, contractType=ContractType.PERPETUAL, interval=interval)

        for _ in range(10):
            # because update block and update frequency set to 30s time diff
            if (res := self.status.get(params.endpoint)) and (time_diff:=abs(int(time.time()*1000) - res.event_time)) < 5000: 
                # DEBUG
                self._log_handle.write_log(f"diff: {time_diff}")
                return res.df.copy()
            elif res is None:
                self._log_handle.write_log("add stream", LogLevel.INFO)
                self._add_stream(params)
            else:
                self._log_handle.write_log(f"diff: {time_diff}")

            self._log_handle.write_log("ws kline wait", LogLevel.INFO)
            time.sleep(0.5)
            
        self._log_handle.write_log(f"get df timeout for {symbol}, {interval}", LogLevel.WARNING)
        return None

class WSFetch:
    '''
    will need warm up calls to populate the stream data
    '''
    def __init__(self, manager:WSManager):
        self.manager = manager
        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)
        self.streams:dict[str, StreamBuffer] = {}

    def get_data(self, endpoint:EndPoint[P, R], params:P)->R|None:
        if (buff:=self.streams.get(params.endpoint)) is None:
            buff = self.manager.add_route("sampling", endpoint, params)
            self.streams[params.endpoint] = buff

        for _ in range(5):
            if (data := buff.pop()) is not None and data.valid: return data
            time.sleep(1)
            
        self._log_handle.write_log("fail to fetch data", LogLevel.WARNING)
