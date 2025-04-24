import time
from multiprocessing import Process

from syspy import Logger


def log_example(n):
    log = Logger("log_example_" + str(n))
    for i in range(100000000):
        time.sleep(0.0001)
        log.info(i)


if __name__ == '__main__':
    thread_list = []
    # 模拟5个脚本进程
    for i in range(5):
        t = Process(target=log_example, args=(i,))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()
