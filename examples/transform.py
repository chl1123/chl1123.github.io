from syspy.v4.lib.rbk import transform


while True:
    tf_type = input("please choose transform type <static (s) / change (c)>: ")
    if tf_type.lower() not in ["s", "static", "c", "change"]:
        print("wrong input, please choose <static / change>")
        continue

    target_frame = input("please input target frame name: ")
    source_frame = input("please input source frame name: ")
    try:
        time_sec = float(input("please input time in seconds: "))
    except ValueError:
        print("wrong input, please input time in seconds")
        continue

    if tf_type in ["s", "static"]:
        if transform.canTransformStatic(target_frame, source_frame, time_sec):
            msg_tf = transform.lookupTransformStatic(
                target_frame, source_frame, time_sec
            )
            print(msg_tf)
        else:
            print(
                f"cannot get static tf from {source_frame} to {target_frame} at time {time_sec}"
            )
    elif tf_type in ["c", "change"]:
        if transform.canTransform(target_frame, source_frame, time_sec):
            msg_tf = transform.lookupTransform(target_frame, source_frame, time_sec)
            print(msg_tf)
        else:
            print(
                f"cannot get change tf from {source_frame} to {target_frame} at time {time_sec}"
            )
