from __future__ import annotations
import numpy as np
import pandas as pd
from decimal import Decimal
from typing import Literal
from core import CandleInterval
from core.schema.bot_schema import SignalSettings
from pydantic import BaseModel

# store as {"df name": {"view name":smaView(),} }
class SmaView(BaseModel):
    open_price:str
    close_price:str
    high_price:str
    low_price:str
    base_price:str ### set default to close price
    window:int
    interval:CandleInterval
    name:str # sma name

    @property
    def pre_name(self)->str:
        return f"{self.name}_pre"
    
class SmaCalc:
    # ---- sma index config ----
    @staticmethod
    def _get_sma(df:pd.DataFrame, view:SmaView)->pd.Series[float]:
        '''
        Returns:
            simple mean average index

        Dependency:
            None
        '''
        return df[view.base_price].rolling(view.window).mean()

    @staticmethod
    def _get_sma_pre(sma:pd.Series[float], view:SmaView)->pd.Series[float]:
        '''
        Returns:
            the previous simple mean average index
        
        Dependency:
            sma index configed (get_sma)
        '''
        return sma.shift(1)

    # ---- sma cross config ----
    @staticmethod
    def get_cross_standard(df:pd.DataFrame, view1:SmaView, view2:SmaView)->pd.Series[float]:
        '''
        Returns:
            the price that's needed for two sma index to cross

        Dependency:
            sma index configed (get_sma)

        extra restriction:
            for view1 and view2:
                1. base price must be the same (high)
                2. base price must be the same
                3. do not work under merge df
        '''
        dx = view1.window*view2.window*(df[view2.name]-df[view1.name])/(view2.window-view1.window)
        res =  df[view1.base_price]+dx
        res.name = "cross_standard"
        return res
    
    @staticmethod
    def get_cross_type(df:pd.DataFrame, view1:SmaView, view2:SmaView, cross_standard:pd.Series[float])->pd.Series[int]:
        '''
        Returns:
            2 if both cross
            1 if golden (view1 < view2 to view1 > view2)
            0 if no cross
            -1 if death

        Dependency:
            cross standard
            sma index
            sma index pre
        '''

        golden_cross:pd.Series = (df[view1.pre_name] <= df[view2.pre_name]) & (df[view1.high_price] >= cross_standard)
        death_cross:pd.Series = (df[view1.pre_name] > df[view2.pre_name]) & (df[view1.low_price] <= cross_standard)
        # get case 1/0/-1 
        res = (golden_cross.astype("int8") - death_cross.astype("int8"))

        # get case 2
        both_cross = golden_cross & death_cross
        res.loc[both_cross] = 1 # TODO: currently disable case 2 need to implement handle for other function before activate
        res.name = "cross_type"
        return res

    @staticmethod
    def get_sma_cross_price(df:pd.DataFrame, view:SmaView, cross_type:pd.Series[int], cross_standard:pd.Series[float])->pd.Series[float]:
        '''
        Description:
            filter sma cross price standard 
            and adjust the price 
            to be the price when crossing in theory
        Returns:
            0 if no cross=0
            cross price if !=0
        '''
        golden_price = np.where(df[view.low_price] > cross_standard, df[view.open_price], cross_standard)
        death_price = np.where(df[view.high_price] <= cross_standard, df[view.open_price], cross_standard)
        conditions = [
            (cross_type == 1),
            (cross_type == -1)
        ]
        choices = [golden_price, death_price]
        res = pd.Series(np.select(conditions, choices, default=0), index=df.index)
        res.name = "cross_price"
        return res

    # ---- sma trend config ----
    @staticmethod
    def get_trend_maint_price(df:pd.DataFrame, view:SmaView)->pd.Series[float]:
        res = (df[view.base_price]+view.window*(df[view.pre_name]-df[view.name]))
        res.name = "trend_maint_price"
        return res
    
    @staticmethod
    def get_simple_trend(df:pd.DataFrame, view:SmaView)->pd.Series[int]:
        '''
        Returns:
            1 if long
            0 if flat
            -1 if short

        dtype: int8
        '''
        long = df[view.name] >= df[view.pre_name]
        short = df[view.name] < df[view.pre_name]
        res = (long.astype("int8") - short.astype("int8"))
        res.name = "simple_trend"
        return res

    @staticmethod
    def get_trend_type(df:pd.DataFrame, simple_trend:pd.Series, trend_len:int)->pd.Series:
        '''
        Returns:
            1  if Bullish Streak
            -1 if Bearish Streak
        '''
        if trend_len <= 2: # set to trend_len <= 1 if want to see 0 
            return simple_trend.rename("trend_type")
        
        signs = pd.Series(np.sign(simple_trend))
        rolling_sum = signs.rolling(window=trend_len-1).sum()

        conditions = [
            (rolling_sum == trend_len-1),
            (rolling_sum == -(trend_len-1)),
        ]
        choices = [1, -1]

        # this is the past n-1 th res
        res = pd.Series(np.select(conditions, choices, default=0), index=df.index).shift(1) ### .astype("Int8")

        # compare to current simple trend if equal
        res = np.where(res == simple_trend, simple_trend, 0)
        res = pd.Series(res, index=df.index)

        res.name = "trend_type"
        return res
    
    @staticmethod
    def get_trend_price(df:pd.DataFrame, view:SmaView, trend_maint_price:pd.Series, trend_type:pd.Series)->pd.Series[float]:
        long_price = np.where(df[view.low_price]>trend_maint_price, df[view.open_price], trend_maint_price)
        long_price = np.where(df[view.high_price]<trend_maint_price, 0, long_price)

        short_price = np.where(df[view.high_price]<trend_maint_price, df[view.open_price], trend_maint_price)
        short_price = np.where(df[view.low_price]>trend_maint_price, 0, short_price)
        
        conditions = [
            (trend_type==1),
            (trend_type==-1)
        ]
        choices = [long_price, short_price]
        res = pd.Series(np.select(conditions, choices, default=0), index=df.index)
        res.name = "trend_price"
        return res
    
    # ---- other utils ----
    @staticmethod
    def adjust(df:pd.DataFrame, orig:SmaView, adj_price:str, mask:str|None=None)->pd.Series[float]:
        adjustment = (df[adj_price] - df[orig.base_price]) / orig.window
        adjusted_sma = df[orig.name] + adjustment

        if mask is not None:
            adjusted_sma = pd.Series(np.where(df[mask], adjusted_sma, df[orig.name]), index=df.index)

        adjusted_sma.name = "adjusted_sma"
        return adjusted_sma
    
class SignalHandle:
    def __init__(self, signal_settings:SignalSettings):
        self.df_config = signal_settings.df_config
        self.df_config_order = signal_settings.df_config_order

    @staticmethod
    def sma_index(name:str, df:pd.DataFrame, view:SmaView)->pd.DataFrame:
        sma = SmaCalc._get_sma(df, view)
        sma_pre = SmaCalc._get_sma_pre(sma, view)

        sma.name = name
        sma_pre.name = f"{name}_pre"

        return pd.concat([sma, sma_pre], axis=1)
    
    @staticmethod
    def cross(name:str, df:pd.DataFrame, view1:SmaView, view2:SmaView)->pd.DataFrame:
        cross_standard = SmaCalc.get_cross_standard(df, view1, view2)
        cross_type = SmaCalc.get_cross_type(df, view1, view2, cross_standard)
        cross_price = SmaCalc.get_sma_cross_price(df, view1, cross_type, cross_standard)
        
        cross_standard.name = f"{name}_standard"
        cross_type.name = f"{name}_type"
        cross_price.name = f"{name}_price"

        return pd.concat([cross_standard, cross_type, cross_price], axis=1)
    
    @staticmethod
    def trend(name:str, df:pd.DataFrame, view:SmaView, length:int)->pd.DataFrame:
        trend_maint_price = SmaCalc.get_trend_maint_price(df, view)
        simple_trend = SmaCalc.get_simple_trend(df, view)
        trend_type = SmaCalc.get_trend_type(df, simple_trend, length)
        trend_price = SmaCalc.get_trend_price(df, view, trend_maint_price, trend_type)

        trend_maint_price.name = f"{name}_maint_price"
        simple_trend.name = f"{name}_simple"
        trend_type.name = f"{name}_type"
        trend_price.name = f"{name}_price"

        return pd.concat([trend_maint_price, simple_trend, trend_type, trend_price], axis=1)
    
    @staticmethod
    def adjust(name:str, df:pd.DataFrame, orig:SmaView, adj_price:str, mask:str|None=None)->pd.DataFrame:
        adj = SmaCalc.adjust(df, orig, adj_price, mask)
        return adj.to_frame(name)
    
    @staticmethod
    def relative_position(name:str, df:pd.DataFrame, col1:str, col2:str)->pd.DataFrame:
        """
        Returns:
            1  if series_1 > series_2
            -1  if series_1 < series_2
            0  if equal
        """
        result = (df[col1] > df[col2]).astype("int8") - (df[col1] < df[col2]).astype("int8")
        return result.to_frame(name)

    @staticmethod
    def window_min_max(name:str, df:pd.DataFrame, col:str, window:int):
        imax = df[col].rolling(window).max()
        imin = df[col].rolling(window).min()
        imax.name = f"{name}_max"
        imin.name = f"{name}_min"
        return pd.concat([imax, imin], axis=1)

    @staticmethod
    def window_exclude_count(name:str, df:pd.DataFrame, col:str, window:int, exclude:int|float=0)->pd.DataFrame:
        return (df[col] != exclude).astype(int).rolling(window=window).sum().to_frame(name)

    # TODO: currently use left merge but when merging two df that's 
    # uncompatible it would have issue, (e.g. 3m and 5m interval)
    # and also no checks for data integrity (e.g. gaps, timestamp missalignment)
    @staticmethod
    def merge(dfs:list[pd.DataFrame], intervals:list[int])->pd.DataFrame:
        if len(dfs)<2:
            return dfs[0]
        
        base_df = dfs[0]
        sub_df = dfs[1:]
        base_interval = intervals[0]
        sub_interval = intervals[1:]

        for df, interval in zip(sub_df, sub_interval, strict=True):
            base_df = pd.merge(base_df, df, left_index=True, right_index=True, how="left")

        is_full_row = base_df.notna().all(axis=1)
        first_full_index = is_full_row.idxmax() if is_full_row.any() else None
        
        if first_full_index is not None:
            base_df = base_df.loc[first_full_index:].copy()
        else:
            raise RuntimeError("Warning: No fully complete rows found!")

        for df, interval in zip(sub_df, sub_interval, strict=True):
            # use ffill to fill gap because using open time
            sub_col = df.columns
            base_df[sub_col] = base_df[sub_col].ffill(limit=interval-base_interval)

        return base_df

    def config_signal(self, dfs:dict[str, pd.DataFrame])->pd.DataFrame:
        sma_views:dict[str, dict[str, SmaView]] = {}

        # setup
        for key, val in dfs.items():
            dfs[key].set_index("open_time", inplace=True)

            # temp solution convert all Decimal to float for calculation
            dfs[key] = dfs[key].map(lambda x: float(x) if isinstance(x, Decimal) else x)

            sma_views[key] = {}

        # config
        for df_name, index_type, index_name in self.df_config_order:
            # print(df_name, index_type, index_name)

            # case: first merge create merge df
            ### make merge to be in cofing so i could merge multipule time if needed?
            if df_name == "merge" and dfs.get("merge") is None:
                # create shallow copy of df as merge
                df0 = (dfs["main"].add_suffix("_main"), self.df_config.main.interval.seconds)
                df_sub = [(v.add_suffix(f"_{k}"), self.df_config.others[k].interval.seconds) for k, v in dfs.items() if self.df_config.others and k != "main" and k != "merge"]
                df_list = [df0]
                df_list.extend(df_sub)
                dfs["merge"] = self.merge(*zip(*df_list))

                # create copy of sma index as merge
                sma_views["merge"] = {}
                for timeframe_key, timeframe_dict in sma_views.items():
                    if timeframe_key == "merge": continue
                    for sma_key, sma_instance in timeframe_dict.items():
                        sma_views["merge"][f"{sma_key}_{timeframe_key}"] = SmaView(
                            open_price=f"{sma_instance.open_price}_{timeframe_key}",
                            close_price=f"{sma_instance.close_price}_{timeframe_key}",
                            low_price=f"{sma_instance.low_price}_{timeframe_key}",
                            high_price=f"{sma_instance.high_price}_{timeframe_key}",
                            base_price=f"{sma_instance.base_price}_{timeframe_key}",
                            name=f"{sma_instance.name}_{timeframe_key}",
                            window=sma_instance.window,
                            interval=sma_instance.interval,
                            
                        )
                
                if index_type == "" and index_name == "":
                    continue

            current_df = dfs[df_name]
            # print(current_df.columns)
            index_config = self.df_config.get_config(df_name, index_type, index_name)
            df_interval = self.df_config.get_df_interval(df_name)

            # case: sma index
            if index_type == "sma_index":
                # add sma views
                
                view = SmaView(
                    open_price="open_price",
                    close_price="close_price",
                    high_price="high_price",
                    low_price="low_price",
                    base_price=index_config.base_price,
                    window=index_config.window,
                    interval=df_interval,
                    name=index_name,
                )
                sma_views[df_name][index_name] = view

                # add column
                sma_df = self.sma_index(index_name, current_df, view)
                dfs[df_name] = pd.concat([current_df, sma_df], axis=1)

            # case: cross
            elif index_type == "sma_cross":
                view1 = sma_views[df_name][index_config.sma1]
                view2 = sma_views[df_name][index_config.sma2]
                cross_df = self.cross(index_name, current_df, view1, view2)

                dfs[df_name] = pd.concat([current_df, cross_df], axis=1)

            # case: trend
            elif index_type == "sma_trend":
                view = sma_views[df_name][index_config.sma]
                trend_df = self.trend(index_name, current_df, view, index_config.length)
                dfs[df_name] = pd.concat([current_df, trend_df], axis=1)

            # case: adjust
            elif index_type == "sma_adjust":
                view = sma_views[df_name][index_config.sma]
                adjust_df = self.adjust(index_name, current_df, view,index_config.new_price, index_config.mask)
                dfs[df_name] = pd.concat([current_df, adjust_df], axis=1)

            # case: relative position
            elif index_type == "rel_pos":
                pos_df = self.relative_position(index_name, current_df, index_config.s1, index_config.s2,)
                dfs[df_name] = pd.concat([current_df, pos_df], axis=1)

            # case: get min max
            elif index_type == "extreme":
                ext_df = self.window_min_max(index_name, current_df, index_config.col, index_config.window)
                dfs[df_name] = pd.concat([current_df, ext_df], axis=1)

            # case: counter
            elif index_type == "exclude_count":
                cnt_df = self.window_exclude_count(index_name, current_df, index_config.col, index_config.window, index_config.exclude)
                dfs[df_name] = pd.concat([current_df, cnt_df], axis=1)
                
        df = dfs["merge"] if dfs.get("merge") is not None else dfs["main"]
        df = df.map(lambda x: Decimal(f"{x:.8f}") if isinstance(x, float) else x)
        return df