import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

plt.style.use('fivethirtyeight')

def animate(i):
    data = pd.read_csv(r"C:\Users\snesa\Desktop\info-proc-labs\lab4\task2\src\Golden_Top\software\lab4_task2\data.csv")
    x = data['sample']
    y = data['value']


    plt.cla()

    plt.plot(x, y)

    plt.tight_layout()


ani = FuncAnimation(plt.gcf(), animate, interval=100)

plt.tight_layout()
plt.show()
