from time import perf_counter
from typing import Dict, List
import scheduler
from math import ceil
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.pyplot import MultipleLocator

plt.rcParams['font.sans-serif']=['SimSun'] # 用来正常显示中文标签

count: Dict[str, Dict[int, int]] = {}
count['FE']:Dict[int, int] = {}
count['BE']:Dict[int, int] = {}
count['EM']:Dict[int, int] = {}
for i in range(-12, 12+1):
    count["FE"][i] = 0
    count["BE"][i] = 0
    count["EM"][i] = 0

deduct: Dict[str, Dict[int, int]] = {}
deduct['FE']:Dict[int, int] = {}
deduct['BE']:Dict[int, int] = {}
deduct['EM']:Dict[int, int] = {}
for i in range(-12, 12+1):
    deduct["FE"][i] = 0
    deduct["BE"][i] = 0
    deduct["EM"][i] = 0

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
    
    def judge(self):
        """score a scheduler

        Returns:
            float: score
        """
        while True:
            try:
                self.read_tick()
                print(self.clock)
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
                scheduled_json = self.scheduler.schedule(self.clock - 1, requests_json, drivers_json)
                duration = perf_counter() - start_time
                scheduled = [json.loads(x) for x in scheduled_json]
                self.total_ref_time += duration
                if self.debug:
                    print(f"reference time: {duration:.6f}s")
                if duration > 5  :
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
                                raise AttributeError('driver_id not in req_driver')
                            self.score -= 24 * ceil(req_size / 50)
                        else:
                            if capacity >= req_size:
                                self.requests[req]["Done"] = True
                                capacity -= req_size
                                now_sla = req_sla - (self.clock - req_clock)
                                if now_sla < -12:
                                    now_sla = -12
                                count[req_type][now_sla] += 1
                                if req_type == "FE":
                                    if self.clock - req_clock > req_sla:
                                        self.score -= min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                        deduct["FE"][now_sla] += min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                elif req_type == "BE":
                                    if self.clock - req_clock <= req_sla:
                                        self.score += 0.5 * ceil(req_size / 50)
                                    else:
                                        deduct["BE"][now_sla] += 0.5 * ceil(req_size / 50)
                                else: # EM
                                    if self.clock - req_clock > req_sla:
                                        self.score -= 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                        deduct["EM"][now_sla] += 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
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
                            now_sla = req_sla - (self.clock - req_clock)
                            if now_sla < -12:
                                now_sla = -12
                            count[req_type][now_sla] += 1
                            if req_type == "FE":
                                if self.clock - req_clock > req_sla:
                                    self.score -= min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                    deduct["FE"][now_sla] += min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                            elif req_type == "EM":
                                if self.clock - req_clock > req_sla:
                                    self.score -= 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                                    deduct["EM"][now_sla] += 2 * min(12, self.clock - req_clock - req_sla) * ceil(req_size / 50)
                            elif req_type == "BE": # BE
                                if self.clock - req_clock > req_sla:
                                    deduct["BE"][now_sla] += 0.5 * ceil(req_size / 50)
                            else:
                                pass
                    print(f"Total reference time:{self.total_ref_time:.6f}s")               
                    print(f"Memory occupied every schedule(MB): {self.scheduler.memory}")
                print(f'********count********')
                print(count)
                print(deduct)
                return self.score, count, deduct

def fig(count: Dict[str, Dict[int, int]], ylabel:str) -> None:
    fe_count: List[int] = []
    be_count: List[int] = []
    em_count: List[int] = []

    for i in range(-12, 12+1):
        fe_count.append(count['FE'][i])
        be_count.append(count['BE'][i])
        em_count.append(count['EM'][i])

    fig = plt.figure(figsize=(10, 6))

    ax1 = fig.add_subplot(311)
    ax1.bar(list(range(-12, 12+1)), fe_count)
    ax1.set_title('FE')
    x_major_locator = MultipleLocator(1.0)  # 设置刻度间隔
    ax1.xaxis.set_major_locator(x_major_locator)
    plt.xlabel('提交时剩余时间')
    plt.ylabel(ylabel)
    for a,b in zip(np.arange(-12, 12+1), fe_count):   #柱子上的数字显示
        plt.text(a,b,'%.d'%(b),ha='center',va='bottom',fontsize=10)

    ax2 = fig.add_subplot(312)
    ax2.bar(list(range(-12, 12+1)), be_count)
    ax2.set_title('BE')
    x_major_locator = MultipleLocator(1.0)  # 设置刻度间隔
    ax2.xaxis.set_major_locator(x_major_locator)
    plt.xlabel('提交时剩余时间')
    plt.ylabel(ylabel)
    for a,b in zip(np.arange(-12, 12+1), be_count):   #柱子上的数字显示
        plt.text(a,b,'%.d'%(b),ha='center',va='bottom',fontsize=10)

    ax3 = fig.add_subplot(313)
    ax3.bar(list(range(-12, 12+1)), em_count)
    ax3.set_title('EM')
    x_major_locator = MultipleLocator(1.0)  # 设置刻度间隔
    ax3.xaxis.set_major_locator(x_major_locator)
    plt.xlabel('提交时剩余时间')
    plt.ylabel(ylabel)
    for a,b in zip(np.arange(-12, 12+1), em_count):   #柱子上的数字显示
        plt.text(a,b,'%.d'%(b),ha='center',va='bottom',fontsize=10)

    fig.subplots_adjust(hspace=1.0)

    plt.show()

r = Runner("demo.log")
score, count, deduct = r.judge()
print(score)
fig(count, '提交数量')
fig(deduct, '扣分')


        
        
        
        