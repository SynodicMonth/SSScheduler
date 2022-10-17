from time import time
from typing import Dict, List
import scheduler
from math import ceil

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
        self.clock = 0
        self.score = 0
        self.debug = debug
        self.initialized = False
    
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
        while self.line and self.line[0] == 'd':
            self.drivers.append(eval(self.line[1:]))
            self.line = self.log_file.readline().strip()
        while self.line and self.line[0] == 'r':
            assert self.clock == int(self.line[1:9])
            new_req = eval(self.line[9:])
            new_req["Done"] = False
            self.requests.append(new_req)
            self.line = self.log_file.readline().strip()
        self.clock += 1
        return
    
    def judge(self) -> float:
        """score a scheduler

        Returns:
            float: score
        """
        while True:
            try:
                self.read_tick()
                if self.debug:
                    caps = [x["Capacity"] for x in self.drivers]
                    print(f"CLK:{self.clock} CAP:{caps} REQ:{len(self.requests)}")
                if not self.initialized:
                    self.scheduler.init(len(self.drivers))
                    self.initialized = True
                start_time = time()
                scheduled = self.scheduler.schedule(self.clock, self.requests, self.drivers)
                if self.debug:
                    print(f"reference time: {time() - start_time:.6f}ms")
                for idx, assign in enumerate(scheduled):
                    assert assign['LogicalClock'] == self.clock
                    capacity = self.drivers[idx]["Capacity"]
                    driver_id = assign["DriverID"]
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
                return self.score

r = Runner("demo.log")
score = r.judge()
print(score)
        
        
        
        