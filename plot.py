import matplotlib.pyplot as plt
from runner import Runner

r = Runner("demo.log")
score = r.judge()
with open("history/history.txt", 'a+') as history_file:
    history_file.writelines(str(score) + '\n')
with open("history/history.txt", 'r') as history_file:
    history = [eval(x.rstrip()) for x in history_file.readlines()]

plt.style.use('seaborn')
plt.rcParams['font.sans-serif'] = 'cmr10'
plt.rcParams['axes.unicode_minus']=False
plt.plot(history, 'o-')
for a, b in enumerate(history):
    plt.text(a, b, b, ha='center', va='bottom', fontsize=15)
plt.title('Test Score', fontsize=15)
plt.xlabel('Commits', fontsize=15)
plt.ylabel('Score', fontsize=15)
plt.tight_layout()
plt.savefig('images/score.png')