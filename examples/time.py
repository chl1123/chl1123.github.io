from syspy.v4.lib.rbk import time


now_time = time.Now()
print(f"now string: {now_time.ToString()}")
print(f"now second: {now_time.ToSecond()}")
print(f"now microsecond: {now_time.ToMicrosecond()}")
print(f"now nanosecond: {now_time.ToNanosecond()}")

sleep_duration = time.Duration(1.0)
wake_time = now_time + sleep_duration

print(f"sleep until: {wake_time.ToString()}")
time.SleepUntil(wake_time)

end_time = time.Now()
elapsed = end_time - now_time
print(f"elapsed second: {elapsed.ToSecond()}")
print(f"elapsed nanosecond: {elapsed.ToNanosecond()}")
