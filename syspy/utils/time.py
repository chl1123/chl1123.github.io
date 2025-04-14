import time


def get_uuid():
    import uuid
    return uuid.uuid4().hex


class Timer:
    """
    机构脚本时间工具接口类
    """
    start_time = None

    @staticmethod
    def delay(second):
        """
        延时 second 秒
        :param second:
        :return: 延时完成返回True
        """
        if Timer.start_time is None:
            Timer.start_time = time.time()
        if time.time() - Timer.start_time > second:
            Timer.start_time = None
            return True
        return False

    @staticmethod
    def get_now_date():
        return time.strftime('%Y-%m-%d %H:%M:%S')


def cost_time(func):
    def fun(*args, **kwargs):
        t = time.perf_counter()
        result = func(*args, **kwargs)
        print(f'func {func.__name__} cost time:{time.perf_counter() - t:.8f} s')
        return result

    async def func_async(*args, **kwargs):
        t = time.perf_counter()
        result = await func(*args, **kwargs)
        print(f'func {func.__name__} cost time:{time.perf_counter() - t:.8f} s')
        return result

    from asyncio.coroutines import iscoroutinefunction
    if iscoroutinefunction(func):
        return func_async
    else:
        return fun
