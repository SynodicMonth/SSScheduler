from time import perf_counter
from typing import Dict, List
import scheduler
from math import ceil
import json

# worst score: -172600.5
# now score: -609.0
# now score: -541.0
# now score: -476.0
class Runner:
    def __init__(self, filename, debug=True) -> None:  
        """init runner object

        Args:
            filename (str): logfile location
            debug (bool): toggle debug mode
        """
        self.log_file = open(filename, "r+")
        self.line = self.log_file.readline().strip()
        if not self.line:
            raise EOFError
        self.scheduler = scheduler.DemoScheduler()
        self.drivers: List[Dict] = []
        self.requests: List[Dict] = []
        self.hour_reqs: List[Dict] = []
        self.clock = 0
        self.score = 0
        self.debug = debug
        self.initialized = False
        self.total_ref_time = 0
    
    def __del__(self) -> None:
        """close file
        
        """
        self.log_file.close()
        
    def read_tick(self) -> None:
        """read a tick of logfile

        Raises:
            EOFError: reach the end of file
        """
        if not self.line:
            raise EOFError
        self.drivers = []
        self.hour_reqs = []
        while self.line and self.line[0] == 'd':
            self.drivers.append(eval(self.line[1:]))
            self.line = self.log_file.readline().strip()
        while self.line and self.line[0] == 'r':
            assert self.clock == int(self.line[1:9])
            new_req = eval(self.line[9:])
            new_req["Done"] = False
            self.hour_reqs.append(new_req)
            self.line = self.log_file.readline().strip()
        self.requests = self.requests + self.hour_reqs
        self.clock += 1
        return
    
    def judge(self) -> float:
        """score a scheduler

        Raises:
            TimeoutError: reference time excceds 5s within one tick

        Returns:
            float: score
        """
        while True:
            try:
                self.read_tick()
                if self.debug:
                    caps = [x["Capacity"] for x in self.drivers]
                    print(f"CLK:{self.clock} CAP:{caps} NUM_REQ:{len(self.hour_reqs)}")
                if not self.initialized:
                    start_time = perf_counter()
                    self.scheduler.init(len(self.drivers))
                    duration = perf_counter() - start_time
                    if self.debug:
                        print(f"initialize time: {duration:.6f}s")
                    self.initialized = True
                requests_json = [json.dumps(x) for x in self.hour_reqs]
                drivers_json = [json.dumps(x) for x in self.drivers]
                start_time = perf_counter()
                scheduled_json = self.scheduler.schedule(self.clock, requests_json, drivers_json)
                duration = perf_counter() - start_time
                scheduled = [json.loads(x) for x in scheduled_json]
                self.total_ref_time += duration
                if self.debug:
                    print(f"reference time: {duration:.6f}s")
                if duration > 5:
                    raise TimeoutError
                for idx, assign in enumerate(scheduled):
                    capacity = self.drivers[idx]["Capacity"]
                    driver_id = assign["DriverID"]
                    print(f'driver:{driver_id}, request:{assign["RequestList"]}')
                    for req in assign["RequestList"]:
                        req_driver = self.requests[req]["Driver"]
                        req_size = self.requests[req]["RequestSize"]
                        req_type = self.requests[req]["RequestType"]
                        req_sla = self.requests[req]["SLA"]
                        req_clock = self.requests[req]["LogicalClock"]
                        if driver_id not in req_driver:
                            if self.debug:
                                print(f"DriverID={driver_id} not in {req_driver}")
                            self.score -= 24 * ceil(req_size / 50)
                        else:
                            if capacity >= req_size:
                                self.requests[req]["Done"] = True
                                capacity -= req_size
                                if req_type == "FE":
                                    if self.clock - req_clock > req_sla:
                                        self.score -= min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                elif req_type == "BE":
                                    if self.clock - req_clock <= req_sla:
                                        self.score += 0.5 * ceil(req_size / 50)
                                else: # EM
                                    if self.clock - req_clock > req_sla:
                                        self.score -= 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                            else:
                                if self.debug:
                                    print(f"DriverID={driver_id} has a size of {req_size} lager than capacity remained")
                                    raise AttributeError(f'over capacity')
                                self.score -= 24 * ceil(req_size / 50)      
            except EOFError:
                if self.debug:
                    print("Final calculation")  
                    for req in self.requests:
                        req_size = req["RequestSize"]
                        req_type = req["RequestType"]
                        req_clock = req["LogicalClock"]
                        req_sla = req["SLA"]
                        if not req["Done"]:
                            if req_type == "FE":
                                if self.clock - req_clock > req_sla:
                                    self.score -= min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                            elif req_type == "EM":
                                if self.clock - req_clock > req_sla:
                                    self.score -= 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                            else: # BE
                                pass
                    print(f"Total reference time:{self.total_ref_time:.6f}s")               
                    print(f"Memory occupied every schedule(MB): {self.scheduler.memory}")
                return self.score
                
if __name__ == '__main__':
    r = Runner("demo.log")
    score = r.judge()
    print(score)
        
        
        
        