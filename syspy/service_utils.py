import inspect
from .lib.rpc_client import rpcClient
from functools import wraps

def get_function_name():
    """
    获取正在运行函数(或方法)名称
    """
    return inspect.stack()[1][3]


def check(fn):
    def wrapper(*args, **kwargs):
        sig = inspect.signature(fn)
        params = sig.parameters  # params 是形参  是一个元素为二元结构的有序字典,OrderedDict([('x', <Parameter "x:int">), ('y', <Parameter "y:int">), ('z', <Parameter "z:int=3">)])               # args,kwargs 是实参
        va = list(params.values())  # 把字典中的值(形参)取出,用做列表处理
        for arg, param in zip(args, va):
            if param.annotation != inspect.Parameter.empty and type(arg) != param.annotation:  # 实参元素与形参元素进行对比判断类型
                raise TypeError("you must input {}, but the input is {}".format(param.annotation, type(arg)))
        for k, v in kwargs.items():
            if params[k].annotation != inspect.Parameter.empty and type(v) != params[
                k].annotation:  # 实参中的K与形参中的K是一样的,K一样,只要进行value的类型判断即可
                raise TypeError("you must input {}, but the input is {}".format(params[k].annotation, type(arg)))
        cc = fn(*args, **kwargs)
        return cc
    return wrapper

def default_plugin(name=None):
    def decorator(cls):
        cls.default_plugin = name
        return cls
    return decorator

def call_service(plugin_name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            # 类型检查
            sig = inspect.signature(func)

            params = sig.parameters
            value = list(params.values())[1:]  # 忽略 'cls' 参数
            for arg, param in zip(args, value):
                if param.annotation != inspect.Parameter.empty and not isinstance(arg, param.annotation):
                    raise TypeError(f"you must input {param.annotation}, but the input is {type(arg)}")
            # 检查关键字参数
            for k, v in kwargs.items():
                if k in params and params[k].annotation != inspect.Parameter.empty and not isinstance(v, params[k].annotation):
                    raise TypeError(f"you must input {params[k].annotation}, but the input is {type(v)}")

            # 使用提供的 plugin_name 或者从对象获取
            service_plugin = plugin_name or getattr(cls, 'default_plugin')
            # 调用原始函数
            result = func(cls, *args, **kwargs)

            # 判断是否为 Motor 类的实例，并且具有 get_service_plugin 方法
            if hasattr(cls, 'rpc_client') and isinstance(cls.rpc_client, rpcClient):
                print(f"plugin:{service_plugin}, func:{func.__name__}, args:{args}, kwargs:{kwargs}")
                return cls.rpc_client.call_service(service_plugin, func.__name__, *args, **kwargs)
            return result

        return wrapper

    return decorator
