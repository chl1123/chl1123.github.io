import zmq,json

class zmqClient(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.addr = "ipc:///tmp/dsp_serial_rpc_server.ipc"
        
    def close(self):
        print("close the socket")
        self.socket.close()
    
    def connect(self, addr):
        self.addr = addr
        self.socket.connect(addr)
    
    def send(self, data):
        self.socket.send(data)

    def recv(self):
        data = self.socket.recv()
        return data

class rpcStub(object):
    def __getattr__(self, function):
        def _func(*args, **kwargs):
            d = {'method_name': function, 'method_args': args, 'method_kwargs': kwargs}
            self.send(json.dumps(d).encode('utf-8'))
            data = self.recv()
            reply = json.loads(data.decode())
            return reply["res"]

        setattr(self, function, _func)
        return _func

class rpcClient(zmqClient, rpcStub):
    pass


