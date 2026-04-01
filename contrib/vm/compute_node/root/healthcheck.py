#!/usr/bin/env python3

from datetime import datetime
import os
import pwd
import random
import re
import shlex
import shutil
import subprocess
import sys
import time

import requests


RETRIES = 3
PROBE_TIMEOUT_SECONDS = 15
RETRY_SLEEP_SECONDS = 0.5
OOM_LOOKBACK_MINUTES = 5
CONTEXT_KEEP_LINES = 720
CONTEXT_LINES_ON_FAILURE = 3

SERVICE_NAME = "sagecell"
CONTEXT_LOG = "/root/healthcheck-context.log"
EVENT_LOG = "/root/healthcheck.log"
WORKER_USER = "{worker}"

OOM_PATTERNS = (
    "Out of memory",
    "Killed process",
    "oom-kill",
    "OOM killer",
    "Memory cgroup out of memory",
    "oom_reaper",
)
OOM_GREP = "|".join(re.escape(pattern) for pattern in OOM_PATTERNS)
KERNELS_LOOKBACK_MINUTES = 3


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def log_message(message):
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{timestamp()}  {message}\n")


def log_status_line(line):
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def update_context_log(line):
    lines = []
    if os.path.exists(CONTEXT_LOG):
        with open(CONTEXT_LOG, encoding="utf-8") as f:
            lines = f.read().splitlines()
    previous = lines[-CONTEXT_LINES_ON_FAILURE:]
    lines = (lines + [line])[-CONTEXT_KEEP_LINES:]
    with open(CONTEXT_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return previous


def try_output(command):
    """Return command output; treat errors as empty output."""
    try:
        return subprocess.check_output(
            shlex.split(command),
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def human_memory_from_kib(value_kib):
    value = float(value_kib) * 1024
    for unit in ("B", "K", "M", "G", "T", "P"):
        if value < 1024 or unit == "P":
            if unit in ("B", "K"):
                return f"{int(round(value)):4d}{unit}"
            return f"{value:4.1f}{unit}"
        value /= 1024
    return f"{value:4.1f}P"


def memory_topic():
    with open("/proc/meminfo", encoding="utf-8") as f:
        meminfo = {}
        for line in f:
            key, value = line.split(":", 1)
            meminfo[key] = int(value.strip().split()[0])
    used_kib = meminfo["MemTotal"] - meminfo["MemAvailable"]
    return f"M:{human_memory_from_kib(used_kib)}"


def oom_topic():
    try:
        worker_uid = str(pwd.getpwnam(WORKER_USER).pw_uid)
    except KeyError:
        return "OOM:?/?"
    worker_patterns = (
        WORKER_USER,
        f" uid {worker_uid}",
        f" uid={worker_uid}",
        f" UID: {worker_uid}",
        f" user {worker_uid}",
    )
    output = try_output(
        f"journalctl -k --since '{OOM_LOOKBACK_MINUTES} minutes ago' --no-pager -o cat --grep '{OOM_GREP}'"
    )
    total = 0
    worker_events = 0
    for line in output.splitlines():
        if not any(pattern in line for pattern in OOM_PATTERNS):
            continue
        total += 1
        if any(pattern in line for pattern in worker_patterns):
            worker_events += 1
    return f"OOM:{total}/{worker_events}"


def format_float(value, width, decimals):
    if value is None:
        return "?" * width
    return f"{value:{width}.{decimals}f}"


def format_integer(value, width):
    if value is None:
        return "?" * width
    return f"{int(round(value)):>{width}d}"


def kernels_topic():
    output = try_output(
        f"journalctl --since '{KERNELS_LOOKBACK_MINUTES} minutes ago' --no-pager -o cat --grep 'tracking [0-9]+ kernels' -n 1"
    )
    match = re.search(r"tracking ([0-9]+) kernels", output)
    tracking = format_integer(int(match.group(1)), 2) if match else "??"

    output = try_output(
        f"journalctl --since '{KERNELS_LOOKBACK_MINUTES} minutes ago' --no-pager -o cat --grep '[0-9]+ preforked kernels left' -n 1"
    )
    match = re.search(r"([0-9]+) preforked kernels left", output)
    preforked = format_integer(int(match.group(1)), 2) if match else "??"

    return f"K:{tracking}/{preforked}"


def disk_topics():
    if shutil.which("iostat") is None:
        return ["iostat not installed"]
    output = try_output("iostat -dx 1 1")
    lines = output.splitlines()
    header = None
    devices = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        columns = line.split()
        if columns[0] == "Device":
            header = columns
            continue
        if header is None:
            continue
        if columns[0].startswith(("loop", "ram", "sr")):
            continue
        if len(columns) != len(header):
            continue
        row = dict(zip(header, columns))
        devices.append(row)
    if not devices:
        return ["error calling iostat"]

    def parse_metric(row, name):
        try:
            return float(row[name])
        except (KeyError, ValueError):
            return None

    topics = []
    for row in sorted(devices, key=lambda device: device["Device"]):
        util = parse_metric(row, "%util")
        aqu = parse_metric(row, "aqu-sz")
        r_await = parse_metric(row, "r_await")
        w_await = parse_metric(row, "w_await")
        topics.append(
            "{}:{}% {}q {}r {}w".format(
                row["Device"],
                format_integer(util, 3),
                format_float(aqu, 3, 1),
                format_integer(r_await, 2),
                format_integer(w_await, 2),
            )
        )
    return topics


def status_line():
    """Return a compact one-line health snapshot.

    Example:
    2026-04-01 03:39:25.925167  K: 2/ 9  L:1.06 0.74 0.84  M: 1.4G OOM:0/0  sda:  1%% 0.1q  6r 13w  sdb:  3%% 0.3q  2r  2w

    Topics:
    timestamp  current local time
    K          tracked kernels / preforked kernels left
    L          1/5/15 minute load averages
    M          used RAM
    OOM        all recent OOM events / recent worker-related OOM events
    sda, sdb   per-disk util%%, queue size, read-await ms, write-await ms
    """
    load = os.getloadavg()
    topics = [
        timestamp(),
        kernels_topic(),
        "L:{} {} {}".format(
            format_float(load[0], 4, 2),
            format_float(load[1], 4, 2),
            format_float(load[2], 4, 2),
        ),
        memory_topic(),
        oom_topic(),
    ]
    topics.extend(disk_topics())
    return "  ".join(topics)


def run_probe(base_url):
    a = random.randint(-2**31, 2**31)
    b = random.randint(-2**31, 2**31)
    # The handling of temporary files in Sage 9.7 does not allow SageMathCell to
    # function properly if there are no regular requests producing temporary
    # files. To fight it, we'll generate one during health checks. See
    # https://groups.google.com/g/sage-devel/c/jpwUb8OCVVc/m/R4r5bnOkBQAJ
    code = "show(plot(sin)); print({} + {})".format(a, b)
    try:
        response = requests.post(
            base_url + "/service",
            data={"code": code, "accepted_tos": "true"},
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        reply = response.json()
        # Every few hours we have a request that comes back as executed, but the
        # stdout is not in the dictionary. It seems that the compute message
        # never actually gets sent to the kernel and it appears the problem is
        # in the zmq connection between the webserver and the kernel.
        #
        # Also sometimes reply is unsuccessful, yet the server keeps running
        # and other requests are serviced. Since a restart breaks all active
        # interacts, better not to restart the server that "mostly works" and
        # instead we'll just accumulate statistics on these random errors to
        # help resolve them.
        if (
            reply["success"]
            and "stdout" in reply
            and int(reply["stdout"].strip()) == a + b
        ):
            return True, None
        return False, str(reply)
    except Exception as exc:  # pylint: disable=broad-except
        return False, str(exc)


def main():
    if len(sys.argv) != 2:
        print("usage: healthcheck.py <base_url>")
        return 2

    previous_context = update_context_log(status_line())

    if subprocess.call(
        ["systemctl", "--quiet", "is-active", SERVICE_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) != 0:
        print(f"{timestamp()}  Service is not active, skipping check")
        return 0

    remaining_attempts = RETRIES
    first_failure = True
    while remaining_attempts:
        remaining_attempts -= 1
        ok, reason = run_probe(sys.argv[1])
        if ok:
            return 0

        current_line = status_line()
        if first_failure:
            for context_line in previous_context:
                log_status_line(context_line)
            first_failure = False
        log_status_line(current_line)
        log_message(f"healthcheck failed, {remaining_attempts} attempts left: {reason}")

        if remaining_attempts:
            time.sleep(RETRY_SLEEP_SECONDS)

    log_message(f"restarting {SERVICE_NAME}")
    try:
        subprocess.check_call(["systemctl", "restart", SERVICE_NAME])
        log_message("restart succeeded")
    except (FileNotFoundError, subprocess.CalledProcessError):
        log_status_line(status_line())
        log_message("restart failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
