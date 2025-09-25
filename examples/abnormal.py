from syspy import Abnormal


Abnormal.setTask(53300, "task error", "task error", "check", "test task")
exist = Abnormal.exists(53300)
num = Abnormal.getNum()
print(f"[setTask(53300)|exists(53300)|{exist}|getNum|{num}]")

Abnormal.setTask(53301, "task error", "task error", "check", "test task")
exist = Abnormal.exists([53300, 53301])
num = Abnormal.getNum()
print(f"[setTask(53301)|exists([53300, 53301])|{exist}|getNum|{num}]")

Abnormal.clear(53300)
exist = Abnormal.exists([53300, 53301])
num = Abnormal.getNum()
print(f"[clear(53300)|exists([53300, 53301])|{exist}|getNum|{num}]")
