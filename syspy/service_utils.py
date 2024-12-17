import inspect


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