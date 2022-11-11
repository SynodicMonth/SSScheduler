import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # __file__如果不行，就改成'file'
sys.path.append(os.path.dirname(SCRIPT_DIR))
import string
from abc import ABCMeta, abstractmethod
import json
from typing import List
import math
from memory_profiler import psutil
import copy
from alns import alns

# worst score: -172600.5
# now score: -609.0
# now score: -541.0
# now score: -476.0
# now score: 399.5
# now score: 475.5
# now score: 485.5, 496.0, 487.5
# now score: 607.0
# now score: 632.5

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
        self.score: float
        self.selected_driver: int
    
    def __lt__(self, other):
        if (self.score > other.score):
            return True
        elif self.score == other.score and self.RequestSize < other.RequestSize:
            return True
        else:
            return False


    def __cmp__(self, other):
        if (self.score > other.score):
            return -1
        elif self.score == other.score and self.RequestSize < other.RequestSize:
            return -1
        elif self.score == other.score and self.RequestSize == other.RequestSize:
            return 0
        else:
            return 1

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
        self.real_cap: List[int] = []
        self.memory: List[int] = []
        self.driver_num = 0
        self.num_URGENT = 0
        self.logical_clock = 0
        self.score = 0
        
        # parameters
        self.max_iteration = 2000
        self.max_runtime = 2
        self.start_temp = 1000 # 100
        self.end_temp = 10  # 10
        self.temp_step = 0.99 # 0.997
        self.temp_s1 = 120     # 10 # ajust to bigger, acception prob will be smaller

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
            if request.RequestType == "BE" and request.now_sla <= 0:
                return ABANDON
            else:
                return URGENT 
        else:   
            return ABANDON
            # "FE" or "EM" <=-11 means req has over 12 hours, 
            # req has get biggest deduction, we can abandon it immediately

    def PDF(self, x: int, _lambda: float) -> float:
        """return exponential distribution pdf function value at point x, PDF(x)=_lambda*e^(-_lambda*x)

        Args:
            x (int): value of x
            _lambda (float): lambda

        Returns:
            float: exponential distribution pdf function value at point x
        """
        
        return _lambda * math.exp(-_lambda * x)
    
    def set_score(self, request:ReqStructure) -> int:
        """
        computing score of the request

        return: score
        """
        
        score = 0
        _lambda1 = 0.5
        _lambda2 = 0.2
        _lambda3 = 0.1
        
        if request.RequestType == "FE":
            multiplier = math.ceil(request.RequestSize / 50)
            transformed_sla = - request.now_sla
            total = sum([self.PDF(x, _lambda1) for x in range(transformed_sla, 13)])
            if transformed_sla <= 0:
                expectation = sum([x * self.PDF(x, _lambda1) for x in range(1, 13)]) / total
                score = multiplier * expectation
            else:
                expectation = sum([x * self.PDF(x, _lambda1) for x in range(transformed_sla, 13)]) / total
                score = multiplier * (expectation - transformed_sla)
        elif request.RequestType == "BE":
            multiplier = 0.5 * math.ceil(request.RequestSize / 50)
            transformed_sla = - request.now_sla
            total = sum([self.PDF(x, _lambda2) for x in range(transformed_sla, 13)])
            if transformed_sla <= 0:
                expectation = sum([self.PDF(x, _lambda2) for x in range(0, 13)]) / total
                score = multiplier * expectation
            else:
                expectation = sum([self.PDF(x, _lambda2) for x in range(transformed_sla, 13)]) / total
                score = 0
        else:
            multiplier = 2 * math.ceil(request.RequestSize / 50)
            transformed_sla = - request.now_sla
            total = sum([self.PDF(x, _lambda3) for x in range(transformed_sla, 13)])
            if transformed_sla <= 0:
                expectation = sum([x * self.PDF(x, _lambda3) for x in range(1, 13)]) / total
                score = multiplier * expectation
            else:
                expectation = sum([x * self.PDF(x, _lambda3) for x in range(transformed_sla, 13)]) / total
                score = multiplier * (expectation - transformed_sla)
        
        # print(f"{request.RequestType}, {sla}, {score}")

        return score
 
    def sort(self):
        """
        computing request's score and insert it to request dict, 
        and then sort requests.
        """
        # divide requests list into two lists by type
        num_urg = 0
        urg_requests: List[ReqStructure] = []
        nourg_requests: List[ReqStructure] = []
        for r in self.requests:
            # urg_requests.append(r)
            # num_urg += 1
            if r.type == URGENT:
                urg_requests.append(r)
                num_urg += 1
            else:
                nourg_requests.append(r)
        self.num_URGENT = num_urg

        # sort URGENT firstly, high score, small size requests are in the frontier
        urg_requests.sort()
        # sort noURGENT secondly
        nourg_requests.sort()
        
        self.requests = urg_requests + nourg_requests
        # print(f'after sort, self.request:')
        # for r in self.requests:
        #     print(r)

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

    def wfac_algo(self, requests:List[ReqStructure], driver_cap:list):
        """
        wfac bin-packing algorithm

        return: results(set the selected_driver of all self.requests), 
                sum of score, remain capacity of drivers
        """
        assert len(driver_cap) == self.driver_num

        score = 0
        results = copy.deepcopy(requests)
        driver_remain = copy.deepcopy(driver_cap)
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
        # print('results:')
        # for r in results:
        #     print(r.selected_driver)
        return results, score, driver_remain

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

        if type == URGENT:
            real_cap = self.real_cap
        else:
            real_cap = self.remain_cap
        try:
            alns_al = alns(ini_requests=wfac_results, remain_cap=wfac_remain_cap, ini_score=wfac_score, \
                    max_iteraion=self.max_iteration, max_runtime=self.max_runtime, real_cap=real_cap, \
                    start_temp=self.start_temp, end_temp=self.end_temp, temp_step=self.temp_step, temp_s1=self.temp_s1)
            alns_results, alns_score, alns_remain_cap = alns_al.iteration_alns()
            # raise AttributeError(f'only wfac')
        except:
            self.remain_cap = wfac_remain_cap
            self.set_type_reqs(wfac_results, type)
            self.score = wfac_score
            return
        
        self.memory.append(self.get_memory())
        print(f'wfac_score:{wfac_score}')
        print(f'alns_score:{alns_score}')
        if wfac_score >= alns_score:
            self.remain_cap = wfac_remain_cap
            self.set_type_reqs(wfac_results, type)
            self.score = wfac_score
        else:
            self.remain_cap = alns_remain_cap
            self.set_type_reqs(alns_results, type)
            self.score = alns_score
        

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
        self.real_cap = self.remain_cap
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
        
