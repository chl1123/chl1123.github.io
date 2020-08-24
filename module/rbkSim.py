import inspect
import json
def get_function_name():
    '''获取正在运行函数(或方法)名称'''
    return inspect.stack()[1][3]
def check(fn):
    def wrapper(*args,**kwargs):
        sig = inspect.signature(fn)
        params = sig.parameters          # parames 是形参  是一个元素为二元结构的有序字典,OrderedDict([('x', <Parameter "x:int">), ('y', <Parameter "y:int">), ('z', <Parameter "z:int=3">)])               # args,kwargs 是实参
        va = list(params.values())       # 把字典中的值(形参)取出,用做列表处理
        for arg, param in zip(args, va):
            if param.annotation != inspect._empty and  not isinstance(arg, param.annotation):    #实参元素与形参元素进行对比判断类型
                raise TypeError("you must input {}".format(param.annotation))
        for k, v in kwargs.items():
            if params[k].annotation != inspect._empty and not isinstance(v, params[k].annotation):              #  实参中的K与形参中的K是一样的,K一样,只要进行value的类型判断即可
                raise TypeError("you must input {}".format(params[k].annotation))  
        cc = fn(*args, **kwargs)
        return cc
    return wrapper
class SimModule:
    def __init__(self):
        pass
    @check
    def setDO(self, id:int, status:bool)->bool:
        print("func: {0} id: {1}  status: {2} ".format(get_function_name(), id, status))
        return True
    @check
    def setMotorSpeed(self, name:str, vel:float, stopDI:int)->bool:
        print("func: {0} name: {1}  vel: {2} stopDI {3}".format(get_function_name(), name, vel, stopDI))
        return True
    @check
    def setMotorPosition(self, motor_name:str, pos:float, maxVel:float, stopDI:int)->bool:
        print("func: {0} name: {1}  pos: {2} maxVel: {3} stopDI: {4}".format(get_function_name(), motor_name, pos, maxVel, stopDI))
        return True
    @check
    def setLocalShelfArea(self, object_model_path:str)->bool:
        print("func: {0} object_model_path: {1}".format(get_function_name(), object_model_path))
        return True
    @check
    def resetMotor(self, motor_name:str)->bool:
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True
    @check
    def isAllMotorsReached(self)->bool:
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def isMotorReached(self, motor_name:str)->bool:
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True  
    @check
    def isMotorPositionReached(self, motor_name:str, pos:float, stopDI:int)->bool:
        print("func: {0} name: {1}  pos: {2} stopDI: {3}".format(get_function_name(), motor_name, pos, stopDI))
        return True
    @check
    def isMotorStop(self, motor_name:str)->bool:
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True  
    @check
    def publishSpeed(self)->bool:
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def resetLocalShelfArea(self)->bool:
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def getMsg(self, type_name:str)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check 
    def getCount(self)->int:
        print("func: {0}".format(get_function_name()))
        return 0
    @check
    def odo(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def loc(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def navSpeed(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def battery(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def rfid(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def magnetic(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Di(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Do(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def pgv(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def sound(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def controller(self)->dict:
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def logInfo(self, ss:str):
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logWarn(self, ss:str):
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logError(self, ss:str):
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logDebug(self, ss:str):
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setError(self, code:int, ss:str):
        print("func: {0} code: {1} content: {2}".format(get_function_name(), code, ss))
    @check
    def setWarning(self, code:int, ss:str):
        print("func: {0} code: {1} content: {2}".format(get_function_name(), code, ss))
    @check
    def clearError(self, code:int):
        print("func: {0} code: {1}".format(get_function_name(), code))
    @check
    def clearWarning(self, code:int):
        print("func: {0} code: {1}".format(get_function_name(), code))
    @check
    def errorExits(self, code:int)->bool:
        print("func: {0} code: {1}".format(get_function_name(), code))
        return True
    @check
    def warningExits(self, code:int)->bool:
        print("func: {0} code: {1}".format(get_function_name(), code))
        return True     
    @check
    def setPathOnRobot(self,x:list, y:list, angle:float):
        print("func: {0} x: {1} y:{2} angle:{3}".format(get_function_name(), x, y, angle))
    @check
    def setPathOnWorld(self,x:list, y:list, angle:float):
        print("func: {0} x: {1} y:{2} angle:{3}".format(get_function_name(), x, y, angle))
    @check
    def isPathReached(self)->bool:
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def goPath(self):
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def resetPath(self):
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def stopRobot(self, flag:bool):
        print("func: {0} stop: {1}".format(get_function_name(), flag))

if __name__ == '__main__':
    r = SimModule()
    r.setDO(1,True)
    r.setMotorSpeed("motor", 1.0, 1)
    r.setMotorPosition("doMotor", 1.0, 2.0, 1)
    r.setLocalShelfArea("shelf")
    r.resetMotor("motor")
    r.isAllMotorsReached
    r.isMotorReached("motor")
    r.isMotorPositionReached("motor",1.0, 1)
    r.isMotorStop("motor")
    r.publishSpeed()
    r.resetLocalShelfArea()
    r.getMsg("loc")
    r.getCount()
    r.odo()
    r.loc()
    r.navSpeed()
    r.battery()
    r.rfid()
    r.magnetic()
    r.Di()
    r.Do()
    r.pgv()
    r.controller()
    r.logInfo("data")
    r.logWarn("data")
    r.logError("data")
    r.logDebug("data")
    r.setError(111111, "data")
    r.setWarning(111111, "data")
    r.clearError(111111)
    r.clearWarning(111111)
    r.errorExits(111111)
    r.warningExits(111111)
    r.setPathOnRobot([0,1],[0,1],0.0)
    r.setPathOnWorld([0,1],[0,1],0.0)
    r.isPathReached()
    r.goPath()
    r.resetPath()
    r.stopRobot(True)


        
