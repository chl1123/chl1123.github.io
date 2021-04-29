import zmq,json,threading,sys,time

class zmqServer(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.bind("ipc:///tmp/dsp2python_rpc.ipc")
        self.data = None
        self.__should_close = False
        self.msg_thread = threading.Thread(target=self.__loop, name="loop")
        self.msg_thread.start()
    
    def close(self):
        print("close the socket")
        self.socket.close()
    
    def send(self, data):
        self.socket.send(data)

    def recv(self):
        data = self.socket.recv()
        return data

    def __loop(self):
        while True:
            try:
                message = self.socket.recv()
                self.data = json.loads(message.decode('utf-8'))
                method_name = self.data['method_name']
                res = self.funs[method_name]()
                data = {"res": res}
                self.socket.send(json.dumps(data).encode('utf-8'))
                if self.__should_close:
                    break
            except Exception as e:
                print('loop error',e)
    
    def shoutDown(self):
        self.__should_close = True

class rpcStub(object):
    def __init__(self):
        self.funs = {}

    def registerFunction(self, function, name=None):
        if name is None:
            name = function.__name__
        self.funs[name] = function

class rpcServer(zmqServer, rpcStub):
    def __init__(self):
        zmqServer.__init__(self)
        rpcStub.__init__(self)

if __name__ == '__main__':
    class Test:
        def setOn(self):
            print("is me ")
        
        def exit(self):
            print("exit")
            sys.exit()

    a = Test()
    test = rpcServer()
    test.registerFunction(a.setOn, "setOn")
    test.registerFunction(a.exit, "exit")


