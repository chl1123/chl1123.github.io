import inspect
import json
from os import strerror
def get_function_name():
    '''获取正在运行函数(或方法)名称'''
    return inspect.stack()[1][3]
def check(fn):
    def wrapper(*args,**kwargs):
        sig = inspect.signature(fn)
        params = sig.parameters          # parames 是形参  是一个元素为二元结构的有序字典,OrderedDict([('x', <Parameter "x:int">), ('y', <Parameter "y:int">), ('z', <Parameter "z:int=3">)])               # args,kwargs 是实参
        va = list(params.values())       # 把字典中的值(形参)取出,用做列表处理
        for arg, param in zip(args, va):
            if param.annotation != inspect._empty and  type(arg) !=  param.annotation:    #实参元素与形参元素进行对比判断类型
                raise TypeError("you must input {}, but the input is {}".format(param.annotation, type(arg)))
        for k, v in kwargs.items():
            if params[k].annotation != inspect._empty and type(v) != params[k].annotation:              #  实参中的K与形参中的K是一样的,K一样,只要进行value的类型判断即可
                raise TypeError("you must input {}, but the input is {}".format(params[k].annotation, type(arg)))  
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
        """查询电机是否停止

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
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def loc(self)->dict:
        """获得定位数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def navSpeed(self)->dict:
        """获得当前速度数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def battery(self)->dict:
        """获得电池数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def rfid(self)->dict:
        """获得rfid数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def magnetic(self)->dict:
        """获得磁条数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Di(self)->dict:
        """获得Di数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def Do(self)->dict:
        """获得Do数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def pgv(self)->dict:
        """获得pgv数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def sound(self)->dict:
        """获得音频数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def controller(self)->dict:
        """获得控制器数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    @check
    def fork(self)->dict:
        """获得货叉数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()   
    @check
    def jack(self)->dict:
        """获得货叉数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()        
    @check
    def moveTask(self)->dict:
        """获得任务信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        print("func: {0}".format(get_function_name()))
        args = dict()
        args["params"] = []
        script_insert = []
        script_insert.append({"name":"ScriptInsert", "type":"ScriptInsert"})
        script_insert.append({"hello":"world"})
        args["params"].append({"key":"armArgs", "string_value":"{}".format(json.dumps(script_insert))})
        args["params"].append({"key":"goodsId","string_value":"123"})
        print(args)
        return args   
    @check
    def getArmInfo(self)->dict:
        """返回机械臂信息

        Returns:
            dict: 具体机械臂信息
        """
        data = {"taskId":1,"task_status":2}
        print("func: {0}".format(get_function_name()))
        return data          
    @check
    def getDistanceSensor(self) -> dict:
        """获取距离节点信息

        Returns:
            dict: 具体的距离节点内容
        """
        a = [{"node":{'RSSI': 1000, 'aperture': 30, 'can_router': 3, 'dist': 0.2527, 'forbidden': False, 'header': {'data_nsec': '2218882847857', 'frame_id': '', 'pub_nsec': '0', 'seq': '0'}, 'id': 1, 'name': 'distanceSensor', 'pos_angle': 180, 'pos_x': -0.75, 'pos_y': 0.35, 'rs485': 0, 'valid': True}}]
        print("func: {0} {1}".format(get_function_name(), a))
        return a
    @check
    def sensorPointCloud(self)->dict:
        """获得后视激光点云信息以字典类型返回

        Returns:
            dict: 具体的任务信息
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
        print("func: {0} content: [{1}]".format(get_function_name(), ss))
    @check
    def logDebug(self, ss:str):
        """将字符串输出到log文件中，等级为Debug

        Args:
            ss (str): 输入的字符串
        """ 
        print("func: {0} content: [{1}]".format(get_function_name(), ss))
    @check
    def setError(self, ss:str):
        """输出53000的Error

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setUserError(self, code:int, ss:str):
        """用户报错码: 53900~53999
        Args:
            code(int): 报错码， 如果超过这个范围，则会报notice
            ss (str): 注释字符串
        """ 
        print("func: {0} code: {1}, content: {2}".format(get_function_name(), code, ss))
    @check
    def setPickRobotError(self, code:int, ss:str):
        """多料箱车专用报错码: 53800~53899
        Args:
            code(int): 报错码， 如果超过这个范围，则会报notice
            ss (str): 注释字符串
        """ 
        print("func: {0} code: {1}, content: {2}".format(get_function_name(), code, ss))
    @check
    def setWarning(self, ss:str):
        """输出55300的Warning

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def setUserWarning(self, code:int, ss:str):
        """用户报警码: 55900~55999

        Args:
            code(int): 报错码， 如果超过这个范围，则会报notice
            ss (str): 注释字符串
        """ 
        print("func: {0} code: {1}, content: {2}".format(get_function_name(), code, ss))
    @check
    def setPickRobotWarning(self, code:int, ss:str):
        """多料箱车报警码: 55800~55899

        Args:
            code(int): 报错码， 如果超过这个范围，则会报notice
            ss (str): 注释字符串
        """ 
        print("func: {0} code: {1}, content: {2}".format(get_function_name(), code, ss))
    @check
    def setNotice(self, ss:str):
        """输出57300的Notice

        Args:
            ss (str): 注释字符串
        """ 
        print("func: {0} content: {1}".format(get_function_name(), ss))
    @check
    def clearNotice(self, code:int):
        """清除Notice

        Args:
            code (int): Notice的编号
        """ 
        print("func: {0} content: {1}".format(get_function_name(), code))
    @check
    def noticeExits(self, code:int)->bool:
        """查询特定编号的Notice是否存在

        Args:
            code (int): Notice 编号

        Returns:
            bool: 如果存在则返回True
        """
        print("func: {0} code: {1}".format(get_function_name(), code))
        return False
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
        return False
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
        """将导航速度分解，目前只有单舵轮和双舵轮有效

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
    def setPathMaxSpeed(self, a:float):
        """路径导航的最大速度

        Args:
            a (float): 单位m/s

        """
        print("func: {0} max_speed: {1}".format(get_function_name(), a)) 
    @check
    def setPathMaxRot(self, a:float):
        """路径导航的最大角速度

        Args:
            a (float): 单位rad/s

        """
        print("func: {0} max_speed: {1}".format(get_function_name(), a)) 
    @check
    def setSound(self, name:str, flag:bool)->None:
        """播放音乐

        Args:
            name (str): 音频名称
            flag (bool): 是否循环播放
        """
        print("func: {0} sound name: {1} loop: {2}".format(get_function_name(), name, flag))
    @check
    def setSoundCount(self, name:str, count:int)->None:
        """播放音乐

        Args:
            name (str): 音频名称
            flag (int): 播放次数，需要大于0
        """
        print("func: {0} sound name: {1} count: {2}".format(get_function_name(), name, count))
    @check
    def stopSound(self, flag:bool)->None:
        """停止播放音乐

        Args:
            flag (bool): 如果为True则为停止播放音乐
        """
        print("func: {0} stop sound: {1}".format(get_function_name(), flag))
    # @check
    # def setForkHeight(self, h:float)->None:
    #     """设置货叉高度

    #     Args:
    #         h (double): 货叉高度，单位m
    #     """
    #     print("func: {0} fork height: {1}".format(get_function_name(), h))
    # @check
    # def stopFork(self)->None:
    #     """设置货叉高度

    #     Args:
    #         h (double): 货叉高度，单位m
    #     """
    #     print("func: {0} ".format(get_function_name()))
    @check
    def switchMap(self, map:str, switchPoint:str)->int:
        """切换地图

        Args:
            map (str): 地图名称
            switchPoint (str): 重定位点位
        Returns:
            int: 2没有进行切换，1切换中，0切换成功，-1不存在地图，-2切换失败
        """
        print("func: {0}: {1} {2}".format(get_function_name(), map, switchPoint))
        return 0
    @check
    def getTriggleScriptName(self)->str:
        """获取TriggleScript的名称

        Args:
            map (str): 地图名称
        
        Returns:
            str: scriptName
        """
        print("func: {0}".format(get_function_name()))
        return "scriptName"
    @check
    def getTriggleScriptArgs(self)->str:
        """获取TriggleScript的参数
        
        Returns:
            str: args
        """
        print("func: {0}".format(get_function_name()))
        return "{}"
    @check
    def hasTriggleScript(self)->bool:
        """监测是否有TriggleScript触发
        Returns:
            bool: scriptArgs
        """
        print("func: {0}".format(get_function_name()))
        return True
    @check
    def resetTriggleScript(self):
        """重置Triggle信息
        """
        print("func: {0}".format(get_function_name())) 
    @check
    def addMoveTask(self, msg:str):
        """增加任务，对应3051

        Args:
            msg (str): 任务
        
        Returns:
        """
        print("func: {0}: {1}".format(get_function_name(), msg))
        return 0     
    @check
    def addMoveTaskList(self, msg:str):
        """增加任务队列，对应3066

        Args:
            msg (str): 任务队列
        
        Returns:
        """
        print("func: {0}: {1}".format(get_function_name(), msg))
        return 0     
    @check
    def resetRec(self):
        """重置识别模块
        """
        print("func: {0}".format(get_function_name()))
    @check
    def getRecResult(self)->dict:
        """获取识别结果

        Returns:
            dict: 识别结果的结构体
        """
        print("func: {0}".format(get_function_name()))
        return dict()      
    @check 
    def doRec(self, filename:str):
        """进行识别

        Args:
            filename (str): 识别文件
        """
        print("func: {0}: {1}".format(get_function_name(), filename))
    @check 
    def doRecWithAngle(self, filename:str, a:float):
        """进行识别,包含识别机构在agv坐标系下的角度

        Args:
            filename (str): 识别文件
            a(float): 识别机构在agv坐标系下的角度
        """
        print("func: {0}: {1}".format(get_function_name(), filename, a))
    @check
    def getRecStatus(self)->int:
        """获取识别状态

        Returns:
            int: 0 刚刚初始化，1识别中，2.获得结果, 3识别出错, -1 未知错误
        """
        print("func: {0}".format(get_function_name()))
        return 0
    @check
    def setGoodsShape(self, head:float, tail:float, width:float):
        """设置货物形状，并且告诉rbk车上装载有货物了。
           如果head,tail, width都小于等于0，则没有货物形状。
           货物的0，0点与小车的0，0点一样
        Args:
            head (float): 货物头部长度
            tail (float): 货物的尾部长度
            width (float): 货物的宽度
        Returns:
        """
        print("func: {0} {1} {2} {3}".format(get_function_name(), head, tail, width))
        return 0
    @check
    def hasGoods(self)->bool:
        """获取身上是否有货物的状态
        Returns:
            bool: 是否有货物
        """
        print("func: {0}".format(get_function_name()))
        return 0
    @check
    def clearGoodsShape(self)->bool:
        """去除agv身上的状态
        """
        print("func: {0}".format(get_function_name()))
        return 0   
    @check
    def getForkPressure(self)->float:
        """货叉测得重量
        """
        print("func: {0}".format(get_function_name()))
        return 0 
    @check
    def getForkPressureADC(self)->float:
        """货叉压力传感器adc值
        """
        print("func: {0}".format(get_function_name()))
        return 0    
    @check
    def setBlockError(self):
        """设置阻挡52200错误
        """
        print("func: {0}".format(get_function_name()))
        return
    @check
    def clearBlockError(self):
        """清除阻挡52200错误
        """
        print("func: {0}".format(get_function_name()))
        return    
    @check        
    def setBlockReason(self, collision_type: int, x: float, y: float, id: int):
        """设置阻挡原因
        Args:
            collision_type (int): 阻挡原因见rbk.py脚本中的CollisionType类
            x (float): 障碍物位置
            y (float): 障碍物位置
            id (float): 障碍物id        
        """
        print("func: {0} {1} {2} {3} {4}".format(get_function_name(), collision_type, x, y, id))
        return  
    @check
    def getRecFileFromTask(self)->str:
        """通过任务获取识别文件
        Returns:
            str: 识别文件
        """        
        print("func: {0} ".format(get_function_name()))
        return ""
    @check
    def setContainer(self, container_name:str, goods_id:str, desc:str)->bool:
        """设置车子上库位或者背篓货物

        Args:
            container_name (str): 库位或者背篓名称
            goods_id (str): 货物的id
            desc (str): 描述

        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        print("func: {0} {1} {2} {3}".format(get_function_name(), container_name, goods_id, desc))
        return  True
    @check
    def getContainers(self)->list:
        """获取当前车子上库位或者背篓货物的状态

        Returns:
            list: 当前车子上库位或者背篓货物的状态
        """
        c= [{'container_name': '0', 'desc': '', 'goods_id': '1', 'has_goods': False}, {'container_name': '1', 'desc': '', 'goods_id': '123', 'has_goods': True}, {'container_name': '2', 'desc': 'by script', 'goods_id': 'goods2', 'has_goods': True}]
        print("func: {0} {1} ".format(get_function_name(), c))
        return c
    @check
    def clearContainer(self, container_name:str)->bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_name (str): 库位或者背篓名称，container_name如果为All则全部清除
        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        print("func: {0} {1}".format(get_function_name(), container_name))
        return  True
    @check
    def clearContainerByGoodsId(self, goods_id:str)->bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_name (str): 货物名称，货物名称如果为All则全部清除
        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        print("func: {0} {1}".format(get_function_name(), goods_id))
        return  True
    @check
    def robokitVersion(self)-> str:
        """获取 robokit 版本号, from: 3.3.5.11

        Returns:
            str: 版本号, 示例: 3.3.5.11
        """
        print("func: {0} {1}".format(get_function_name(), "3.3.5.11"))
        return  "3.3.5.11"
    @check
    def openSpeed(self, vx:float, vy:float, vw:float):
        """让agv按vx,vy,vw行走，此函数考虑了碰撞检测
        """
        print("func: {0} {1} {2} {3} ".format(get_function_name(), vx, vy, vw))
    @check
    def resetRecAndGoPathDi(self):
        """重置识别行走的动作
        """
        print("func: {0}".format(get_function_name()))
    @check
    def recAndGoPathDi(self, task:str) ->int:
        """识别并且行走
        Returns:
            int: 任务状态。和 MoveStatus 相同
        """
        print("func: {0} {1}".format(get_function_name(), task))
        return 4
    @check
    def resetRecAdjustYTheta(self):
        """在有限空间内来回调整,使车子对准目标点
        """
        print("func: {0}".format(get_function_name()))
    @check
    def recAdjustYTheta(self, task:str) ->int:
        """在有限空间内来回调整,使车子对准目标点
        Returns:
            int: 任务状态。和 MoveStatus 相同
        """
        print("func: {0} {1}".format(get_function_name(), task))
        return 4
    @check
    def resetGoMapPath(self):
        """行走的动作
        """
        print("func: {0}".format(get_function_name()))  
    @check      
    def goMapPath(self, task:str) ->int:
        """按地图路线行走
        Returns:
            int: 任务状态。和 MoveStatus 相同
        """
        print("func: {0} {1}".format(get_function_name(), task))
        return 4        
    @check
    def laserCollision(self, ids:list) ->bool:
        """检测激光点是否和自身碰撞
        Returns:
            bool: 激光点是否和自身碰撞
        """      
        print("func: {0} {1}".format(get_function_name(), ids))
        return False
    @check      
    def forkGoods(self, load:bool, recfile:str):
        """货叉上加载或者卸载货物模型及货物检测DI
        Returns:
        """
        print("func: {0} {1} {2}".format(get_function_name(), load, recfile))
        return 4
    @check
    def armBinTask(self,task_id:int, cmd:str):
        """调用机械臂动作的服务

        Args:
            task_id (int): 任务的id
            cmd (str): 任务的详细动作序列，是个json array类型
        """        
        print("func: {0} {1} {2}".format(get_function_name(), task_id, cmd))
    def armStop(self):
        print("func: {0}".format(get_function_name()))
    def armPause(self):
        print("func: {0}".format(get_function_name()))
    def armResume(self):
        print("func: {0}".format(get_function_name()))
    def scannerCode(self, task_id:int):
        """ 调用机械臂识别二维码的接口
        Args:
            task_id (int): _description_
        """
        print("func: {0} {1}".format(get_function_name(), task_id))
    def armControl(self, json_str:str):
        """ 调用控制机械臂运动状态接口，比如减速
        Args:
            json_str (str): 控制指令，是json 字符串
        """
        print("func: {0} {1}".format(get_function_name(), json_str))        
    def stopMotor(self):
        """停止所有非行走的电机
        """        
        print("func: {0}".format(get_function_name()))
    def getMinDynamicObs(self)->list:
        """获得离机器最近的一个动态障碍物坐标。 如果没有障碍物反馈0.,0.

        Returns:
            list: 两个元素，分别为x,y。单位为m
        """
        obs = [0.,0.]
        print("func: {0} {1}".format(get_function_name(), obs))
        return obs
    def getRobotFile(self)->dict:
        """获得模型文件的原始数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0}".format(get_function_name()))
        return dict()
    def getRecFile(self, name:str)->dict:
        """获得识别文件的原始数据
        Args:
            name (str): 识别文件名称，比如 shelf/s0001.shelf, pallet/p0001.pallet
        Returns:
            dict: 具体数据以字典类型返回
        """
        print("func: {0} {1}".format(get_function_name(), name))
        return dict()
    @check
    def getLM(self, name:str, flag:bool)->tuple:
        """获取点位坐标
         Args:
            name (str): 站点或者库位名称
            flag (bool): True 返回的坐标是地图坐标系， False返回的坐标是机器人坐标系
        Returns:
            tuple: 0-> x (m); 1->y (m); 2->theta (rad); 3-> id (-1 表示不存在) 
        """
        d = (0, 0, 0, -1)
        print("func: {0} {1} {2} {3}".format(get_function_name(), name, flag, d))
        return d
    @check
    def RecognizeBarCode(self, name:str, id:str)->str:
        """获取一维码信息

        Args:
            name (str): 其中输入为识别文件的目录，如: tag/t0001.tag
            id (str): 其中输入为识别任务的唯一id, 如: 123456
        Returns:
            dict: 识别结果. {"barCode":"string", "id":"string", "status": 0}
                status: 0 表示成功， 1表示识别中, 2表示识别失败
                id 为当前识别的任务 id
                barCode 表示识别的结果
        """
        d = {"barCode":"1234", "id":"123", "status": 0}
        print("func: {0} {1} {2}".format(get_function_name(), name, d))
        return d
    @check
    def stopCurrentBlock(self):
        """终止当前调度的动作块
        """
        print("func: {0}".format(get_function_name()))
        return
    @check
    def getCanFrame(self)->dict:
        """ 获取当前的 CanFrame
        """
        d = {'Canerror': [], 'Channel': 0, 'DLC': 0, 'Data': '', 'Direction': False, 'Extended': False, 'ID': 0, 'Remote': False, 'Timestamp': 0}
        print("func: {0} {1}".format(get_function_name(), d))
        return d
    @check
    def sendCanFrame(self, channel:int, can_id: int, dlc: int, extend: bool, can_string: str):
        """DSP提供sendCanFrame接口

        Args:
            channel (uint8_t): 使用的端口，有1和2,对应控制器的CAN通道
            can_id (uint16_t): 发送报文的canid, 如0x601
            dlc (uint8_t): 发送报文的数据长度，一般为8
            extend (bool): 报文是否为扩展型，一般为false
            can_string (string): 报文数据区，如"40 40 60 00 00 00 00 00"，十六进制，空格隔开
        """
        print("func: {0} {1} {2} {3} {4} {5}".format(get_function_name(), channel, can_id, dlc, extend, can_string))
    @check
    def resetGoForkPath(self, x:float, y:float, yaw:float, back_dist:float, ahead_dist:float):
        """重置叉车去往识别点的路径规划

        Args:
            x (float): 终点x坐标 m
            y (float): 终点y坐标 m
            yaw (float): 终点角度坐标 rad
            back_dist (float): 到终点后的后退距离
            ahead_dist (float): 到终点前的直线距离
        """
        print("func: {0} {1} {2} {3} {4} {5}".format(get_function_name(), x, y, yaw, back_dist, ahead_dist))
    @check
    def goForkPath(self):
        """叉车依据规划的路径导航，需要先调用 resetGoForkPath
        """
        print("func: {0} ".format(get_function_name()))

    def motorCalib(self, motor_name:str):
        """电机标零

        Args:
            motor_name (str): 电机名称
        """
        print("func: {0} {1}".format(get_function_name(), motor_name))        
if __name__ == '__main__':
    r = SimModule()
    r.setDO(1,True)
    r.setMotorSpeed("motor", 1.0, 1)
    r.setMotorPosition("doMotor", 1.0, 2.0, 1)
    r.setLocalShelfArea("shelf")
    r.resetMotor("motor")
    r.isAllMotorsReached()
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
    r.setSoundCount("hello", 1)
    r.stopSound(True)
    # r.setForkHeight(1.0)
    # r.stopFork()
    r.switchMap("hello","LM1")
    r.getTriggleScriptArgs()
    r.getTriggleScriptName()
    r.hasTriggleScript()
    r.resetTriggleScript()
    r.resetRec()
    r.doRec("shelf.shelf")
    r.getRecResult()
    r.getRecStatus()
    r.getForkPressure()
    r.getForkPressureADC()
    r.setPathMaxSpeed(1.0)
    r.setPathMaxRot(1.0)
    r.setBlockError()
    r.clearBlockError()
    r.setBlockReason(0,0.,0.,0)
    r.getRecFileFromTask()
    r.setContainer("1","goods1","")
    r.getContainers()
    r.clearContainer("1")
    r.clearContainerByGoodsId("1")
    r.setUserError(53900, "error")
    r.setUserWarning(55900, "warning")
    r.sensorPointCloud()
    r.openSpeed(0.,0.,0.)
    r.resetRecAndGoPathDi()
    r.recAndGoPathDi(task="{\"operation\":\"load\"}")
    r.laserCollision([1,2])
    r.getDistanceSensor()
    r.resetGoMapPath()
    r.goMapPath(task="{\"operation\":\"load\"}")
    r.forkGoods(True, "shelf/s0001.shelf")
    r.getArmInfo()
    r.armBinTask(1, "[]")
    r.armStop()
    r.armPause()
    r.armResume()
    data =  {"type": "set_speed_slider"}
    r.armControl(json.dumps(data))
    r.stopMotor()
    r.setPickRobotError(53800, "error")
    r.setPickRobotWarning(55800, "warning")
    r.getMinDynamicObs()
    r.scannerCode(1)
    r.getRobotFile()
    r.getRecFile("shelf/s0001.shelf")
    r.clearNotice(533000)
    r.noticeExits(533000)
    r.getLM("AP1", True)
    r.RecognizeBarCode("tag/t0001.tag", "123")
    r.stopCurrentBlock()
    r.getCanFrame()
    r.sendCanFrame(1,1,1,False,"40 40 60 00 00 00 00 00")
    r.resetGoForkPath(0.0,0.0,0.0,0.0,0.0)
    r.goForkPath()
    print("Success!!!")