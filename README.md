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
  
## expectation criteria
假定每个Request在提交时超时的时长(transformed_sla，>0表示超时，<0未超时)近似遵循指数分布
$$pdf(x)=\lambda e^{-\lambda x}$$
此处暂时进行离散化和归一化（实际上是我没找到理论上合理的归一化方法，这里可能有问题），令
$$P(X=x)=\frac{pdf(x)}{\sum_{i=-12}^{12}pdf(i)}$$
对于每一个Req，设它最终提交时超时的时长为x（可以小于0），现在已知这一轮已经超时y，则有
$$f(x)=P(X=x|X\ge y)=
  \begin{cases}
    \frac{pdf(x)}{\sum_{i=y}^{12}pdf(i)} & x\ge y \ ,\\
    0 & x < y \ .
  \end{cases}$$
而超时扣分量
$$g(x)= 
\begin{cases}
  x \lceil\frac{size}{50}\rceil & x>0,FE  \ ,\\ 
  0.5\lceil\frac{size}{50}\rceil & x>0,BE \ ,\\ 
  2x \lceil\frac{size}{50}\rceil & x>0,EM \ ,\\
  0 & otherwise \ .
\end{cases}$$
则在已知这一轮已经超时y下的扣分期望
$$E(X)=\sum_{x=-12}^{12}g(x)f(x)=
\begin{cases}
  \lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & FE  \ ,\\
  \lceil\frac{size}{50}\rceil\frac{\sum_{x=y}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y>0 & FE  \ ,\\ 
  0.5\lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}pdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & BE \ ,\\ 
  0.5\lceil\frac{size}{50}\rceil & y>0 & BE \ ,\\ 
  2\lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & EM \ ,\\
  2\lceil\frac{size}{50}\rceil\frac{\sum_{x=y}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y>0 & EM \ ,\\
  0 & otherwise \ .
\end{cases}$$
这一轮上交Request的扣分
$$C(y)=\begin{cases}
  y \lceil\frac{size}{50}\rceil & y>0,FE  \ ,\\ 
  0.5\lceil\frac{size}{50}\rceil & y>0,BE \ ,\\ 
  2y \lceil\frac{size}{50}\rceil & y>0,EM \ ,\\
  0 & otherwise \ .
\end{cases}$$
则本轮上交期望提升为
$$E_{improvement}(y)=\begin{cases}
  \lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & FE  \ ,\\
  \lceil\frac{size}{50}\rceil(\frac{\sum_{x=y}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)}-y) & y>0 & FE  \ ,\\ 
  0.5\lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}pdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & BE \ ,\\ 
  0 & y>0 & BE \ ,\\ 
  2\lceil\frac{size}{50}\rceil\frac{\sum_{x=0}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)} & y\le0 & EM \ ,\\
  2\lceil\frac{size}{50}\rceil(\frac{\sum_{x=y}^{12}xpdf(x)}{\sum_{i=y}^{12}pdf(i)}-2y) & y>0 & EM \ ,\\
  0 & otherwise \ .
\end{cases}$$

