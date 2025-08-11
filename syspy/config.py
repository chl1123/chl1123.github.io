try:
    with open('/etc/srcname', 'r') as f:
        output = f.read().strip()
        if output == "SRC5000":
            rbk_version = 4
        else:
            rbk_version = 3  # 默认版本
except FileNotFoundError:
    rbk_version = 4
