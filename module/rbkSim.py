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
#TODO 加入当前要下发的速度，以及发送下发速度
class SimModule:
    def __init__(self):
        pass
    @check
    def setDO(self, id:int, status:bool)->bool:
        """控制DO的开关

        Args:
            id (int): DO的id
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        print("func: {0} id: {1}  status: {2} ".format(get_function_name(), id, status))
        return True
    @check
    def setMotorSpeed(self, name:str, vel:float, stopDI:int)->bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            name (str): 电机名称
            vel (float): 电机速度
            stopDI (int): 到位DI

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        print("func: {0} name: {1}  vel: {2} stopDI {3}".format(get_function_name(), name, vel, stopDI))
        return True
    @check
    def setMotorPosition(self, motor_name:str, pos:float, maxVel:float, stopDI:int)->bool:
        """控制线性电机到特定位置

        Args:
            motor_name (str): 模型文件中的电机名称
            pos (float): 发送目标点位置也可能是角度
            maxVel (float): 运行过程中的最大速度不能超过模型文件中的最大速度
            stopDI (int): 如果这个StopDI触发则表示运动到位

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        print("func: {0} name: {1}  pos: {2} maxVel: {3} stopDI: {4}".format(get_function_name(), motor_name, pos, maxVel, stopDI))
        return True
    @check
    def setLocalShelfArea(self, object_model_path:str)->bool:
        """加载顶升上的货物模型

        Args:
            object_model_path (str): 货架模型文件名称

        Returns:
            bool: 如果不存在这个货架模型则报错
        """
        print("func: {0} object_model_path: {1}".format(get_function_name(), object_model_path))
        return True
    @check
    def resetMotor(self, motor_name:str)->bool:
        """将电机重置为不启用状态

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果不存在这个电机则报错
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True
    @check
    def isAllMotorsReached(self)->bool:
        """所有电机是否到位

        Returns:
            bool: 如果所有电机到位则为True
        """
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def isMotorReached(self, motor_name:str)->bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果到位则返回True
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True  
    @check
    def isMotorPositionReached(self, motor_name:str, pos:float, stopDI:int)->bool:
        """电机是否到达特定位置

        Args:
            motor_name (str): 电机名称
            pos (float): 位置
            stopDI (int): 到位DI

        Returns:
            bool: 如果到位则返回True
        """
        print("func: {0} name: {1}  pos: {2} stopDI: {3}".format(get_function_name(), motor_name, pos, stopDI))
        return True
    @check
    def isMotorStop(self, motor_name:str)->bool:
        """控制电机停止

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果电机不存在则返回False
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return True  
    @check
    def publishSpeed(self)->bool:
        """将当前电机控制方案，进行速度规划然后下发

        Returns:
            bool: 如果规划电机速度失败则返回False
        """
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def resetLocalShelfArea(self)->bool:
        """取消顶升上的货架

        Returns:
            bool: [description]
        """
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def getMsg(self, type_name:str)->dict:
        """获取消息名称

        Args:
            type_name (str): 消息名称

        Returns:
            dict: 以字典的类型返回消息
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check 
    def getCount(self)->int:
        """获得当前任务已经循环的次数

        Returns:
            int: 循环的次数
        """
        print("func: {0}".format(get_function_name()))
        return 0
    @check
    def odo(self)->dict:
        """获得里程数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def loc(self)->dict:
        """获得定位数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def navSpeed(self)->dict:
        """获得当前速度数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def battery(self)->dict:
        """获得电池数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def rfid(self)->dict:
        """获得rfid数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def magnetic(self)->dict:
        """获得磁条数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Di(self)->dict:
        """获得Di数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Do(self)->dict:
        """获得Do数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def pgv(self)->dict:
        """获得pgv数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def sound(self)->dict:
        """获得音频数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def controller(self)->dict:
        """获得控制器数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def fork(self)->dict:
        """获得货叉数据

        Returns:
            dict: 具体数据已字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()        
    @check
    def logInfo(self, ss:str):
        """将字符串输出到log文件中，等级为Info

        Args:
            ss (str): 输入的字符串
        """
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logWarn(self, ss:str):
        """将字符串输出到log文件中，等级为Warning

        Args:
            ss (str): 输入的字符串
        """        
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logError(self, ss:str):
        """将字符串输出到log文件中，等级为Error

        Args:
            ss (str): 输入的字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def logDebug(self, ss:str):
        """将字符串输出到log文件中，等级为Debug

        Args:
            ss (str): 输入的字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setError(self, ss:str):
        """输出53000的Error

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setWarning(self, ss:str):
        """输出55300的Warning

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setNotice(self, ss:str):
        """输出57300的Notice

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def clearError(self, code:int):
        """清除特定编号的Error

        Args:
            code (int): Error的编号
        """
        print("func: {0} code: {1}".format(get_function_name(), code))
    @check
    def clearWarning(self, code:int):
        """清除特定编号的Warning

        Args:
            code (int): Warning的编号
        """
        print("func: {0} code: {1}".format(get_function_name(), code))
    @check
    def errorExits(self, code:int)->bool:
        """查询特定编号的Error是否存在

        Args:
            code (int): Error编号

        Returns:
            bool: 如果存在则返回True
        """
        print("func: {0} code: {1}".format(get_function_name(), code))
        return True
    @check
    def warningExits(self, code:int)->bool:
        """查询特定编号的Warning是否存在

        Args:
            code (int): Warning编号

        Returns:
            bool: 如果存在则返回True
        """        
        print("func: {0} code: {1}".format(get_function_name(), code))
        return True     
    @check
    def setPathOnRobot(self,x:list, y:list, angle:float):
        """让agv在agv坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """
        print("func: {0} x: {1} y:{2} angle:{3}".format(get_function_name(), x, y, angle))
    @check
    def setPathOnWorld(self,x:list, y:list, angle:float):
        """让agv在世界坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """        
        print("func: {0} x: {1} y:{2} angle:{3}".format(get_function_name(), x, y, angle))
    @check
    def isPathReached(self)->bool:
        """agv是否完成线路

        Returns:
            bool: 如果完成则返回True
        """
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def goPath(self):
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def resetPath(self):
        """让agv沿着规划的线路行驶
        """
        print("func: {0}".format(get_function_name()))
    @check
    def stopRobot(self, flag:bool):
        """让agv停下来

        Args:
            flag (bool): 如果是True就是急停，如果是False则以StopAcc停下来
        """
        print("func: {0} stop: {1}".format(get_function_name(), flag))
    @check
    def setInfo(self, ss:str):
        """输出脚本调试信息

        Args:
            ss (str): 脚本调试信息
        """
        print("func: {0} info: {1}".format(get_function_name(), ss))
    @check
    def getNextSpeed(self)->dict:
        """获取当前NavSpeed的速度

        Returns:
            dict: 返回一个字典包含NavSpeed中所有的速度
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def setNextSpeed(self, nav:str)->bool:
        """设置准备下发的速度

        Args:
            nav (str): 下发的速度，格式与从getNextSpeed或者navSpeed获得的格式相同

        Returns:
            bool: 如果成功转成下发速度则返回True
        """
        print("func: {0} nav: {1}".format(get_function_name(), nav))
        return True
    @check
    def speedDecomposition(self, nav:str)->str:
        """将导航速度速度分解，目前只有单舵轮和双舵轮有效

        Args:
            nav (str): 导航速度，格式与从getNextSpeed或者navSpeed获得的格式相同

        Returns:
            dict: 返回速度分解后的速度
        """
        print("func: {0} nav: {1}".format(get_function_name(), nav))
        return nav 
    @check     
    def setPathReachDist(self, a:float)->None:
        """路径导航的到点精度

        Args:
            a (float): 单位m
        """
        print("func: {0} reach_dist: {1}".format(get_function_name(), a))
    @check
    def setPathReachAngle(self, a:float):
        """路径导航的到点角度精度

        Args:
            a (float): 单位rad

        """
        print("func: {0} reach_angle: {1}".format(get_function_name(), a))
    @check
    def setPathUseOdo(self, a:bool):
        """路径导航是否用里程定位

        Args:
            a (bool): 如果用里程定位则为True
        """
        print("func: {0} usdOdo: {1}".format(get_function_name(), a))
    @check
    def setPathBackMode(self, a:bool)->None:
        """路径导航是否倒走

        Args:
            a (bool): 如果倒走则为True
        """
        print("func: {0} backMode: {1}".format(get_function_name(), a))     
    @check
    def setSound(self, name:str, flag:bool)->None:
        """播放音乐

        Args:
            name (str): 音频名称
            flag (bool): 是否循环播放
        """
        print("func: {0} sound name: {1} loop: {2}".format(get_function_name(), name, flag))
    def stopSound(self, flag:bool)->None:
        """停止播放音乐

        Args:
            flag (bool): 如果为True则为停止播放音乐
        """
        print("func: {0} stop sound: {1}".format(get_function_name(), flag))
    def setForkHeight(self, h:float)->None:
        """设置货叉高度

        Args:
            h (double): 货叉高度，单位m
        """
        print("func: {0} fork height: {1}".format(get_function_name(), h))
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
    r.fork()
    r.logInfo("data")
    r.logWarn("data")
    r.logError("data")
    r.logDebug("data")
    r.setError("data")
    r.setWarning("data")
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
    r.getNextSpeed()
    r.setNextSpeed(json.dumps({"x":0.3}))
    r.speedDecomposition(json.dumps({"x":0.3}))
    r.setPathReachAngle(1.0)
    r.setPathReachDist(1.0)
    r.setPathUseOdo(True)
    r.setPathBackMode(True)
    r.setSound("hello", True)
    r.stopSound(True)
    r.setForkHeight(1.0)
    print("Success!!!")


        
