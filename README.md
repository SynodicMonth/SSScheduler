# SSScheduler
Smart Storage Scheduler for 2022 Massive Storage Competition

## train of thoughts v1.0:

![](./images/algorithm.png)

## alns:
<font color=#ff0000>score: 399.5 -> 490.0</font>
![](./images/alns.png)

- BPR算子：随机选择一个driver，选择其中一个request（根据它的requests的size来设置概率，size越大的被选择概率越大），将该request移除，从等待队列里面重新选择request放入该driver中。

- shift算子：随机选择一个driver，根据上述概率选择一个request移到另一个driver上面去，如果目标driver的capacity超出，则先选择一部分他的request移到其它driver上面去，如果依然超出，则移除部分requests，知道capacity不超出为止，最后从等待队列里面重新选择request放入这两个driver中。

- 退火算法计算接收概率：
  ![](./images/anneal.png)

- 一定要防止提交的driver的capacity被超出！为此我修改了runner.py，当出现capacity超出的情况会直接报错停止运行。
  
##  expectation criteria
  
假定每个Request在提交时超时的时长(transformed_sla，>0表示超时，<0未超时)近似遵循指数分布
<p align="center"><img src="https://latex.codecogs.com/gif.latex?pdf(x)=&#x5C;lambda%20e^{-&#x5C;lambda%20x}"/></p>  
  
此处暂时进行离散化和归一化（实际上是我没找到理论上合理的归一化方法，这里可能有问题），令
<p align="center"><img src="https://latex.codecogs.com/gif.latex?P&#x5C;{X=x&#x5C;}=&#x5C;frac{pdf(x)}{&#x5C;sum_{i=-12}^{12}pdf(i)}"/></p>  
  
对于每一个Req，设它最终提交时超时的时长为x（可以小于0），现在已知这一轮已经超时y，则有
<p align="center"><img src="https://latex.codecogs.com/gif.latex?f(x)=P&#x5C;{X=x|X&#x5C;ge%20y&#x5C;}=%20%20&#x5C;begin{cases}%20%20%20%20&#x5C;frac{pdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20x&#x5C;ge%20y&#x5C;&#x5C;%20%20%20%200%20&amp;%20x%20&lt;%20y%20%20&#x5C;end{cases}"/></p>  
  
而超时扣分量
<p align="center"><img src="https://latex.codecogs.com/gif.latex?g(x)=%20&#x5C;begin{cases}%20%20x%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20x&gt;0,FE%20&#x5C;&#x5C;%20%20%200.5&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20x&gt;0,BE&#x5C;&#x5C;%20%20%202x%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20x&gt;0,EM&#x5C;&#x5C;%20%200%20&amp;%20otherwise&#x5C;end{cases}"/></p>  
  
则在已知这一轮已经超时y下的扣分期望
<p align="center"><img src="https://latex.codecogs.com/gif.latex?E(X)=&#x5C;sum_{x=-12}^{12}g(x)f(x)=&#x5C;begin{cases}%20%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y%20&#x5C;le%200,FE&#x5C;&#x5C;%20%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=y}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y&gt;0,FE&#x5C;&#x5C;%20%20%200.5&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}pdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y%20&#x5C;le%200,BE&#x5C;&#x5C;%20%20%200.5&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20y&gt;0%20,BE&#x5C;&#x5C;%20%20%202&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y%20&#x5C;le%200%20,EM&#x5C;&#x5C;%20%202&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=y}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y&gt;0,EM&#x5C;&#x5C;%20%200%20&amp;%20otherwise&#x5C;end{cases}"/></p>  
  
这一轮上交Request的扣分
<p align="center"><img src="https://latex.codecogs.com/gif.latex?C(y)=&#x5C;begin{cases}%20%20y%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20y&gt;0,FE&#x5C;&#x5C;%20%20%200.5&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20y&gt;0,BE&#x5C;&#x5C;%20%20%202y%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil%20&amp;%20y&gt;0,EM&#x5C;&#x5C;%20%200%20&amp;%20otherwise&#x5C;end{cases}"/></p>  
  
则本轮上交期望提升为
<p align="center"><img src="https://latex.codecogs.com/gif.latex?E_{improvement}(y)=&#x5C;begin{cases}%20%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y&#x5C;le0,FE%20&#x5C;&#x5C;%20%20&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil(&#x5C;frac{&#x5C;sum_{x=y}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}-y)%20&amp;%20y&gt;0,FE%20&#x5C;&#x5C;%20%20%200.5&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}pdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y&#x5C;le0,BE&#x5C;&#x5C;%20%20%200%20&amp;%20y&gt;0,BE&#x5C;&#x5C;%20%20%202&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil&#x5C;frac{&#x5C;sum_{x=0}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}%20&amp;%20y&#x5C;le0,EM&#x5C;&#x5C;%20%202&#x5C;lceil&#x5C;frac{size}{50}&#x5C;rceil(&#x5C;frac{&#x5C;sum_{x=y}^{12}xpdf(x)}{&#x5C;sum_{i=y}^{12}pdf(i)}-2y)%20&amp;%20y&gt;0,EM&#x5C;&#x5C;%20%200%20&amp;%20otherwise&#x5C;end{cases}"/></p>  
  
  
  