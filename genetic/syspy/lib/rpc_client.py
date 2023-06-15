import zmq,json

class zmqClient(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
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
            try:
                d = {'method_name': function, 'method_args': args, 'method_kwargs': kwargs}
                self.send(json.dumps(d).encode('utf-8'))
                events = dict(self.poller.poll(5000))
                if self.socket in events:
                    data = self.recv()
                    reply = json.loads(data.decode())
                    return reply["res"]
                else:
                    print("poller Timeout")
            except Exception as e:
                print('client error', e)

        setattr(self, function, _func)
        return _func

class rpcClient(zmqClient, rpcStub):
    pass


