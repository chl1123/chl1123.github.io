# -*- coding: utf-8 -*-
# @Date : 2026/04/10
# @Author : codex
# @Coding : none
# @Project: CKY-DG 称重设备模拟接收端测试（调用 weighingScale.py）

import argparse
import os
import sys

# 允许从仓库根目录直接运行该脚本
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_V3_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if TASK_V3_DIR not in sys.path:
    sys.path.insert(0, TASK_V3_DIR)

from tasks.v3.standard.example.weighingScale import CkyDgScale


def print_check(name: str, ok: bool, detail):
    status = "PASS" if ok else "FAIL"
    print(f"[receiver] {status} {name}: {detail}")


def run_basic_tests(scale: CkyDgScale, expected_raw_weight: int) -> bool:
    all_ok = True

    one = scale.read_weight_once()
    ok = ("value" in one) and ("unit" in one)
    print_check("read_weight_once", ok, one)
    if not ok:
        all_ok = False

    samples = scale.read_weight_samples(sample_count=5, sample_interval=0.02)
    ok = samples.get("sampleCount") == 5
    print_check(
        "read_weight_samples",
        ok,
        {
            "sampleCount": samples.get("sampleCount"),
            "averageValue": samples.get("averageValue"),
            "unit": samples.get("last", {}).get("unit"),
        },
    )
    if not ok:
        all_ok = False

    scale.tare()
    tare_read = scale.read_weight_once()
    ok = tare_read.get("raw") == 0
    print_check("tare", ok, tare_read)
    if not ok:
        all_ok = False

    scale.clear_tare()
    clear_read = scale.read_weight_once()
    ok = clear_read.get("raw") == int(expected_raw_weight)
    print_check("clear_tare", ok, clear_read)
    if not ok:
        all_ok = False

    scale.zero()
    zero_read = scale.read_weight_once()
    ok = zero_read.get("raw") == 0
    print_check("zero", ok, zero_read)
    if not ok:
        all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="调用 CkyDgScale 的基础功能验证")
    parser.add_argument("--port", type=str, required=True, help="串口路径，如 /dev/ttyUSB0 或 /dev/pts/3")
    parser.add_argument("--slave-id", type=int, default=1, help="从站ID")
    parser.add_argument("--baudrate", type=int, default=9600, help="波特率")
    parser.add_argument("--timeout", type=float, default=0.2, help="串口超时")
    parser.add_argument("--expected-raw-weight", type=int, default=1234, help="模拟器初始原始重量")
    args = parser.parse_args()

    print(f"[receiver] connect to port={args.port}, slave_id={args.slave_id}")

    scale = CkyDgScale(
        port=args.port,
        baudrate=args.baudrate,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
        slave_id=args.slave_id,
    )

    try:
        ok = run_basic_tests(scale, args.expected_raw_weight)
    finally:
        scale.close()

    if ok:
        print("[receiver] basic tests passed")
    else:
        print("[receiver] basic tests failed")


if __name__ == "__main__":
    main()
