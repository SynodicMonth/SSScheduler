import random
import string
import time
from abc import ABCMeta, abstractmethod
import json

URGENT = "URGENT"
noURGENT = "noURGENT"

class Scheduler(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.requests = []
        self.driver_status = []
        self.remain_cap = []
        self.driver_num = 0
        self.num_URGENT = 0
        self.num_noURGENT = 0
        self.logical_clock = 0

    # @abstractmethod
    def init(self, driver_num: int) -> None:
        self.driver_num = driver_num
        
    def set_type(self, request) -> string:
        """
        set request's type to URGENT or noURGENT

        return: type
        """
        if request["now_sla"] <= 1:
            return URGENT
        else:
            return noURGENT 

    def set_score(self, request) -> int:
        """
        computing score of the request

        return: score
        """
        if request["type"] == URGENT:
            if request["now_sla"] > 1: # set type error
               return 0

            minus_hours = -(request["now_sla"]-2)
            if request["RequestType"] == "FE":
                return min(12, minus_hours) * request["RequestSize"] / 50
            elif request["RequestType"] == "BE":
                return 0.5 * request["RequestSize"] / 50
            else:
                return 2 * min(12, minus_hours) * request["RequestSize"] / 50
       
        else:
            if request["now_sla"] <= 1: # set type error
                return 10000
            
            if request["RequestType"] == "FE":
                return request["RequestSize"] / 50
            elif request["RequestType"] == "BE":
                return 0.5 * request["RequestSize"] / 50
            else:
                return 2 * request["RequestSize"] / 50


    def sort(self):
        """
        computing request's score and insert it to request dict, 
        and then sort requests.
        """
        # divide requests list into two lists by type
        urg_requests = []; num_urg = 0
        nourg_requests = []; num_nourg = 0
        for r in self.requests:
            if r["type"] == URGENT:
                urg_requests.append(r)
                num_urg += 1
            else:
                nourg_requests.append(r)
                num_nourg += 1
        self.num_URGENT = num_urg
        self.num_noURGENT = num_nourg

        # sort URGENT firstly, high score requests in the frontier
        for i in range(len(urg_requests)):
            for j in range(i+1, len(urg_requests)):
                if urg_requests[i]["score"] < urg_requests[j]["score"]:
                    tmp = urg_requests[i]
                    urg_requests[i] = urg_requests[j]
                    urg_requests[j] = tmp
        # sort noURGENT secondly
        for i in range(len(nourg_requests)):
            for j in range(i+1, len(nourg_requests)):
                if nourg_requests[i]["score"] < nourg_requests[j]["score"]:
                    tmp = nourg_requests[i]
                    nourg_requests[i] = nourg_requests[j]
                    nourg_requests[j] = tmp
        
        self.requests = urg_requests + nourg_requests
    
    def wfac_algo(self, requests, driver_cap:list):
        """
        wfac bin-packing algorithm

        return: schedule results, sum of score, remain capacity of drivers
        """
        assert len(driver_cap) == self.driver_num

        results = []; score = 0
        for r in requests:
            # find if there are drivers can hold the request, 
            # if true, select the driver with biggest capcity,
            # set the request's "Driver" as [driver_id].
            max_cap = 0
            driver = -1
            for d in r["Driver"]:
                if driver_cap[d] > r["RequestSize"] and driver_cap[d] > max_cap:
                    max_cap = driver_cap[d]
                    driver = d
            if driver != -1:
                r["Driver"] = [driver]
                results.append(r)
                driver_cap[d] -= r["RequestSize"]
                score += r["score"]
        return results, score, driver_cap
        

    def alns_algo(self, requests, driver_cap:list):
        """
        alns algorithm, num of iterator is decided by remain time, at most 2s

        return: schedule results, sum of score, remain capacity of drivers
        """
        pass
    
    def type_schedule(self, type:string) -> list:
        """
        make schedule for a type of requests, 
        don't forget delete requests will be commited in self.requests

        return: schedule results, contain requests will be commit, and every request's "Driver" is certain
        """
        # run all algoritym and get the best results
        assert len(self.remain_cap) == self.driver_num

        if type == URGENT:
            requests = self.requests[:self.num_URGENT]
        else:
            requests = self.requests[self.num_URGENT:]
        
        wfac_results, wfac_score, wfac_remain_cap = self.wfac_algo(requests, self.remain_cap)
        alns_results, alns_score, alns_remain_cap = self.alns_algo(requests, self.remain_cap)
        if wfac_score > alns_score:
            self.remain_cap = wfac_remain_cap
            results = wfac_results
        else:
            self.remain_cap = alns_remain_cap
            results = alns_results
        
        # delete the requests will be commit in self.requests
        commit_id = []
        for r in results:
            commit_id.append(r["RequestID"])
        for i in range(len(self.requests)-1, -1, -1):
            if self.requests[i]["RequestID"] in commit_id:
                self.requests.remove(self.requests[i])
        
        return results

    def excu_reqs(self, commit_reqs:list) -> list:
        """
        translate commit_reqs into formal excu_reqs send to drivers

        return: excu_reqs
        """
        all_driver_req = [[] for _ in range(self.driver_num)]
        commit_results = []

        for r in commit_reqs:
            all_driver_req[r["Driver"][0]].append(r["RequestID"])
        
        for l in range(self.driver_num):
            driver_json = json.dumps({"DriverID":l, "RequestList":all_driver_req[l], "LogicalClock":self.logical_clock})
            commit_results.append(driver_json)
        return commit_results

    # @abstractmethod
    def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
        """
        add new keys ("now_sla", "type", "score") into request dict, 
        you need to delete them before the request is commited. 
        """
        
        for r in self.requests:
            r["now_sla"] -= 1
        
        requests = [json.loads(i) for i in request_list]
        drivers = [json.loads(i) for i in driver_statues]
        for r in requests:
            r["now_sla"] = r["SLA"]

        assert len(drivers) == self.driver_num
        self.driver_status = drivers
        self.requests = self.requests + requests
        self.logical_clock = logical_clock
        
        for r in self.requests:
            r["type"] = self.set_type(r)
            r["score"] = self.set_score(r)
        self.remain_cap = []
        for d in self.driver_status:
            self.remain_cap.append(d["Capacity"]) 

        self.sort()
        urg_commit_reqs = self.type_schedule(URGENT)
        nourg_commit_reqs = self.type_schedule(noURGENT)
        
        commit_reqs = urg_commit_reqs + nourg_commit_reqs
        return self.excu_reqs(commit_reqs)
        
        
        

# class DemoScheduler():
#     def __init__(self):
#         pass

#     def init(self, driver_num: int):
#         self.driver_num = driver_num
#         pass

#     def schedule(self, logical_clock: int, request_list: list, driver_statues: list) -> list:
#         arr = []
#         print(type(request_list[0]))
#         print(type(driver_statues[0]))
#         request_list = [json.loads(r) for r in request_list]
#         driver_statues = [json.loads(r) for r in driver_statues]
#         print(type(request_list[0]))
#         print(type(driver_statues[0]))
#         # for i in range(self.driver_num):
#         #     d = {"LogicalClock": logical_clock}
#         #     d["DriverID"] = i
#         #     d["RequestList"] = [x["RequestID"] for x in random.choices(request_list, k=4)]
#         #     arr.append(d)
#         return arr

# request = [{"RequestID": 0, "RequestType": "BE", "SLA": 12, "Driver": [1], "RequestSize": 111, "LogicalClock": 0},
#         {"RequestID": 1, "RequestType": "FE", "SLA": 12, "Driver": [1], "RequestSize": 80, "LogicalClock": 0}]

# driver = [{"DriverID": 0, "Capacity": 100, "LogicalClock": 0},
#         {"DriverID": 1, "Capacity": 100, "LogicalClock": 0}]

# r = [json.dumps(i) for i in request]
# d = [json.dumps(i) for i in driver]
# print(r)
# print(d)
# s = DemoScheduler()
# s.schedule(0, r, d)