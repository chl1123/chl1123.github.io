
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
import importlib
import os,sys 
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
sys.path.insert(0,parentdir)  
"""
####BEGIN DEFAULT ARGS####
{
    "scriptName": {
        "value": "",
        "tips": "脚本名称",
        "unit": "",
        "type": "string"
    },
    "ScriptArgs":{
        "value": "",
        "tips": "脚本参数",
        "unit": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True    
        self.status = MoveStatus.NONE
        self.sName = None
        self.sArgs = None
        self.init_module = True
        self.m = None
    def run(self, r:SimModule,args:json):
        """主函数，每个运行周期都会执行run函数

        Args:
            r (SimModule): 是MoveFactory的类，包含了基本的电机控制，状态查询，消息查询的功能
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，MoveStatus,用于表明脚本的运行状态
        """
        if self.status == MoveStatus.FINISHED:
            return self.status.value
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.init_module = True
            self.sName = args.get('scriptName')
            tmp_args = args.get('scriptArgs')
            if tmp_args is not None:
                self.sArgs = args.get('scriptArgs')
            else:
                self.sArgs = None
        if self.sName is None:
            if r.hasTriggleScript():
                self.sName = r.getTriggleScriptName()
                self.sArgs = r.getTriggleScriptArgs()
                r.resetTriggleScript()
        if self.sName is not None:
            self.runModule(r)
        return self.status

    def runModule(self, r:SimModule):
        if self.init_module:
            self.init_module = False
            if self.sArgs is not None:
                orgArgs = self.sArgs
                try:
                    self.sArgs = json.loads(orgArgs)
                except:
                    r.setError("scriptArgs is wrong: {}".format(orgArgs))
                    self.status = MoveStatus.FAILED
                    return
            else:
                self.sArgs = dict()
            org_name = self.sName
            tmp_name = org_name.split(".")[0]
            tmp_names = tmp_name.split("/")
            self.sName = tmp_names[-1]
            print(org_name, tmp_names, self.sName)
            try:
                py = importlib.import_module(self.sName)
                self.m = py.Module(r, self.sArgs)
            except:
                self.m = None
                r.setError("scriptName is wrong: {}".format(org_name))
                self.status = MoveStatus.FAILED
                return
                
        if self.m is not None:
            self.m.run(r, self.sArgs)
            self.status = self.m.status

if __name__ == '__main__':
    import rbkSim, json
    r = rbkSim.SimModule()
    m = Module(r,None)
    args = dict()
    args["name"] = "navigation"
    args["loop"] = False
    data = {}
    print(m.run(r, data))