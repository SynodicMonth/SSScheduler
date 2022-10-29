import os
import sys

from numpy import int0
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # __file__如果不行，就改成'file'
sys.path.append(os.path.dirname(SCRIPT_DIR))
import string
from abc import ABCMeta, abstractmethod
import json
from typing import Dict, List
import math
from memory_profiler import psutil

# worst score: -172600.5
# now score: -609.0
# now score: -541.0
# now score: -476.0
# now score: 399.5

URGENT = "URGENT"
noURGENT = "noURGENT"
ABANDON = "ABANDON"

class Scheduler(metaclass=ABCMeta):
    @abstractmethod
    def init(self, driver_num: int) -> None:
        pass

    @abstractmethod
    def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
        pass

class ReqStructure():
    def __init__(self) -> None:
        self.RequestID: int
        self.RequestType: string
        self.SLA: int
        self.Driver: List[int]
        self.RequestSize: int
        self.LogicalClock: int
        # parameters define by ourselves
        self.now_sla: int
        self.type: string
        self.score: int
        self.selected_driver: int

class DriverStructure():
    def __init__(self) -> None:
        self.DriverID: int
        self.Capacity: int
        self.LogicalClock: int


class DemoScheduler(Scheduler):
    def __init__(self):
        self.requests: List[ReqStructure] = []
        self.driver_status: List[DriverStructure] = []
        self.remain_cap: List[int] = []
        self.memory: List[int] = []
        self.driver_num = 0
        self.num_URGENT = 0
        self.logical_clock = 0
        self.score = 0

    def init(self, driver_num: int) -> None:
        self.driver_num = driver_num

    def get_memory(self) -> int:
        """
        get memory process has occupied
        """
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
    def set_type(self, request:ReqStructure) -> string:
        """
        set request's type to URGENT or noURGENT
        return: type
        """
        if request.now_sla > 1 :
            return noURGENT
        elif request.now_sla <= 1 and request.now_sla >= -10:  
            return URGENT 
        else:   
            # "FE" or "EM" <=-11 means req has over 12 hours, 
            # req has get biggest deduction, we can abandon it immediately
            if request.RequestType != "BE":
                return ABANDON
            else:
                return URGENT

    def set_score(self, request:ReqStructure) -> int:
        """
        computing score of the request

        return: score
        """
        if request.type == URGENT:
            if request.now_sla > 1: # set type error
               return 0
            # minus_hours = -(request.now_sla-2)
            if request.RequestType == "FE":
                return math.ceil(request.RequestSize / 50)
            elif request.RequestType == "BE":
                return 0.5 * math.ceil(request.RequestSize / 50)
            else:
                return 2 *  math.ceil(request.RequestSize / 50)
       
        else:
            if request.now_sla <= 1: # set type error
                return 10000
            if request.RequestType == "FE":
                return  math.ceil(request.RequestSize / 50)
            elif request.RequestType == "BE":
                return  0.5 * math.ceil(request.RequestSize / 50)
            else:
                return  2 * math.ceil(request.RequestSize / 50)


    def sort(self):
        """
        computing request's score and insert it to request dict, 
        and then sort requests.
        """
        # divide requests list into two lists by type
        num_urg = 0
        urg_requests = []
        nourg_requests = []
        for r in self.requests:
            if r.type == URGENT:
                urg_requests.append(r)
                num_urg += 1
            else:
                nourg_requests.append(r)
        self.num_URGENT = num_urg

        # sort URGENT firstly, high score, small size requests are in the frontier
        for i in range(len(urg_requests)):
            for j in range(i+1, len(urg_requests)):
                if urg_requests[i].score < urg_requests[j].score or \
                  (urg_requests[i].score == urg_requests[j].score and \
                    urg_requests[i].RequestSize > urg_requests[j].RequestSize):
                    tmp = urg_requests[i]
                    urg_requests[i] = urg_requests[j]
                    urg_requests[j] = tmp
        # sort noURGENT secondly
        for i in range(len(nourg_requests)):
            for j in range(i+1, len(nourg_requests)):
                if nourg_requests[i].score < nourg_requests[j].score or \
                  (nourg_requests[i].score == nourg_requests[j].score and \
                    nourg_requests[i].RequestSize > nourg_requests[j].RequestSize):
                    tmp = nourg_requests[i]
                    nourg_requests[i] = nourg_requests[j]
                    nourg_requests[j] = tmp
        
        self.requests = urg_requests + nourg_requests
        # print(f'after sort, self.request:')
        # for r in self.requests:
        #     print(r)
    
    def wfac_algo(self, requests:List[ReqStructure], driver_cap:list):
        """
        wfac bin-packing algorithm

        return: results(set the selected_driver of all self.requests), 
                sum of score, remain capacity of drivers
        """
        assert len(driver_cap) == self.driver_num

        score = 0
        results = requests
        driver_remain = driver_cap
        for i in range(len(results)):
            # find if there are drivers can hold the request, 
            # if true, select the driver with biggest capcity,
            # set the request's "Driver" as [driver_id].
            max_cap = 0
            driver = -1
            for d in results[i].Driver:
                if driver_remain[d] > results[i].RequestSize and driver_remain[d] > max_cap:
                    max_cap = driver_remain[d]
                    driver = d
            if driver != -1:
                results[i].selected_driver = driver
                driver_remain[driver] = driver_remain[driver] - results[i].RequestSize
                score += results[i].score
        # print(f'wfac driver_remain:{driver_remain}')
        # print('results:')
        # for r in results:
        #     print(r.selected_driver)
        return results, score, driver_remain
        

    def alns_algo(self, requests:List[ReqStructure], driver_cap:list):
        """
        alns algorithm, num of iterator is decided by remain time, at most 2s

        return: results(set the selected_driver of all self.requests), 
                sum of score, remain capacity of drivers
        """
        # using the same code with function wfac_algo provisionally
        assert len(driver_cap) == self.driver_num

        score = 0
        results = requests
        driver_remain = driver_cap
        for r in results:
            # find if there are drivers can hold the request, 
            # if true, select the driver with biggest capcity,
            # set the request's "Driver" as [driver_id].
            max_cap = 0
            driver = -1
            for d in r.Driver:
                if driver_remain[d] > r.RequestSize and driver_remain[d] > max_cap:
                    max_cap = driver_remain[d]
                    driver = d
            if driver != -1:
                r.selected_driver = driver
                driver_remain[driver] = driver_remain[driver] - r.RequestSize
                score += r.score
        # print(f'wfac driver_remain:{driver_remain}')
        # print('results:')
        # for r in results:
        #     print(r)
        return results, score, driver_remain
    
    def select_type(self, type:string) -> list:
        """
        get one type of requests from the self.requests

        return: list of reqs belong to the type
        """
        if type == URGENT:
            return self.requests[:self.num_URGENT]
        else:
            return self.requests[self.num_URGENT:]

    def set_type_reqs(self, results:list, type:string):
        """
        after the results is certain, 
        set one type of requests' selected_driver from the self.requests
        """
        reqs_len = len(self.requests)
        if type == URGENT:
            self.requests[:self.num_URGENT] = results
        else:
            self.requests[self.num_URGENT:] = results
        assert len(self.requests) == reqs_len

    def type_schedule(self, type:string):
        """
        make schedule for a type of requests, 
        don't forget delete requests will be commited in self.requests

        return: some requests in self.requests's selected_driver has been sure 
        """
        # run all algoritym and get the best results
        assert len(self.remain_cap) == self.driver_num

        requests = self.select_type(type)
        wfac_results, wfac_score, wfac_remain_cap = self.wfac_algo(requests, self.remain_cap)
        self.remain_cap = wfac_remain_cap
        self.set_type_reqs(wfac_results, type)
        self.score = wfac_score
        self.memory.append(self.get_memory())
        


    def excu_reqs(self) -> list:
        """
        translate requests will be commited into formal excu_reqs of drivers

        return: excu_reqs
        """
        all_driver_req = [[] for _ in range(self.driver_num)]
        commit_results = []

        for r in self.requests:
            if r.selected_driver != -1:
                all_driver_req[r.selected_driver].append(r.RequestID)
        
        for l in range(self.driver_num):
            driver_json = json.dumps({"DriverID":l, "RequestList":all_driver_req[l], "LogicalClock":self.logical_clock})
            commit_results.append(driver_json)
        return commit_results

    def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
        """
        add new keys ("now_sla", "type", "score") into request dict
        """
        for r in self.requests:
            r.now_sla -= 1
        
        requests_dict = [json.loads(i) for i in request_list]
        drivers_dict = [json.loads(i) for i in driver_statues]
        for r_d in requests_dict:
            r = ReqStructure()
            r.RequestID = r_d["RequestID"]
            r.RequestType = r_d["RequestType"]
            r.SLA = r_d["SLA"]
            r.Driver = r_d["Driver"]
            r.RequestSize = r_d["RequestSize"]
            r.LogicalClock = r_d["LogicalClock"]
            r.now_sla = r_d["SLA"]
            self.requests.append(r)

        assert len(drivers_dict) == self.driver_num
        self.driver_status = []
        for d_d in drivers_dict:
            d = DriverStructure()
            d.DriverID = d_d["DriverID"]
            d.Capacity = d_d["Capacity"]
            d.LogicalClock = d_d["LogicalClock"]
            self.driver_status.append(d)

        self.logical_clock = logical_clock
        
        for i in range(len(self.requests)-1, -1, -1):
            self.requests[i].type = self.set_type(self.requests[i])
            if self.requests[i].type == ABANDON:
                self.requests.remove(self.requests[i])
                continue
            self.requests[i].score = self.set_score(self.requests[i])
            self.requests[i].selected_driver = -1
        
        self.remain_cap = [d.Capacity for d in self.driver_status]
        # print(f'self.remain_cap: {self.remain_cap}') 

        self.sort()

        self.type_schedule(URGENT)
        self.type_schedule(noURGENT)
        
        excu = self.excu_reqs()

#         for r in self.requests:
#             print(f'"RequestID": {r.RequestID}, "RequestType": {r.RequestType}, "SLA": {r.SLA}, \
# "Driver": {r.Driver}, "RequestSize": {r.RequestSize}, "score": {r.score}, \
# "now_sla": {r.now_sla}, "type": {r.type}, "selected_driver": {r.selected_driver} ')

        for i in range(len(self.requests)-1, -1, -1):
            if self.requests[i].selected_driver != -1:
                self.requests.remove(self.requests[i])

        return excu
        