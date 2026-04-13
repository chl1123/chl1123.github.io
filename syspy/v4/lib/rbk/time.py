from .pymodule import PyModule


Time = PyModule.Time
Duration = PyModule.Duration


def Now() -> Time:
    return Time.Now()


def SleepUntil(time_obj: Time):
    Time.SleepUntil(time_obj)
