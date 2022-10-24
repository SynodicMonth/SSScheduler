import random
import time
from abc import ABCMeta, abstractmethod
import json


class Scheduler(metaclass=ABCMeta):
    @abstractmethod
    def init(self, driver_num: int) -> None:
        pass

    @abstractmethod
    def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
        pass


class DemoScheduler(Scheduler):
    def __init__(self):
        pass

    def init(self, driver_num: int):
        self.driver_num = driver_num
        # pass

    def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
        arr = []
        for i in range(self.driver_num):
            d = {"LogicalClock": logical_clock}
            d["DriverID"] = i
            request = [json.loads(x) for x in request_list]
            d["RequestList"] = [x["RequestID"] for x in random.choices(request, k=4)]
            arr.append(json.dumps(d))
        return arr
