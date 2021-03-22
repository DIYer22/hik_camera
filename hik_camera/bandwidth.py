import psutil
import time
from datetime import datetime
import curses
import argparse


def getNetworkData():
    # 获取网卡流量信息
    recv = {}
    sent = {}
    data = psutil.net_io_counters(pernic=True)
    interfaces = data.keys()
    for interface in interfaces:
        recv.setdefault(interface, data.get(interface).bytes_recv)
        sent.setdefault(interface, data.get(interface).bytes_sent)
    return interfaces, recv, sent


def getNetworkRate(num):
    # 计算网卡流量速率
    interfaces, oldRecv, oldSent = getNetworkData()
    time.sleep(num)
    interfaces, newRecv, newSent = getNetworkData()
    networkIn = {}
    networkOut = {}
    for interface in interfaces:
        networkIn.setdefault(
            interface,
            float("%.3f" % ((newRecv.get(interface) - oldRecv.get(interface)) / num)),
        )
        networkOut.setdefault(
            interface,
            float("%.3f" % ((newSent.get(interface) - oldSent.get(interface)) / num)),
        )
    return interfaces, networkIn, networkOut


def output(num, unit):
    # 将监控输出到终端
    stdscr = curses.initscr()
    curses.start_color()
    # curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.noecho()
    curses.cbreak()
    stdscr.clear()
    try:
        # 第一次初始化
        interfaces, _, _ = getNetworkData()
        currTime = datetime.now()
        timeStr = datetime.strftime(currTime, "%Y-%m-%d %H:%M:%S")
        stdscr.addstr(0, 0, timeStr)
        i = 1
        for interface in interfaces:
            if (
                interface != "lo"
                and bool(1 - interface.startswith("veth"))
                and bool(1 - interface.startswith("蓝牙"))
                and bool(1 - interface.startswith("VMware"))
            ):
                if unit == "K" or unit == "k":
                    netIn = "%12.2fKB/s" % 0
                    netOut = "%11.2fKB/s" % 0
                elif unit == "M" or unit == "m":
                    netIn = "%12.2fMB/s" % 0
                    netOut = "%11.2fMB/s" % 0
                elif unit == "G" or unit == "g":
                    netIn = "%12.3fGB/s" % 0
                    netOut = "%11.3fGB/s" % 0
                else:
                    netIn = "%12.1fB/s" % 0
                    netOut = "%11.1fB/s" % 0
                stdscr.addstr(i, 0, interface)
                stdscr.addstr(i + 1, 0, "Input:%s" % netIn)
                stdscr.addstr(i + 2, 0, "Output:%s" % netOut)
                stdscr.move(i + 3, 0)
                i += 4
                stdscr.refresh()
        # 第二次开始循环监控网卡流量
        while True:
            _, networkIn, networkOut = getNetworkRate(num)
            currTime = datetime.now()
            timeStr = datetime.strftime(currTime, "%Y-%m-%d %H:%M:%S")
            stdscr.erase()
            stdscr.addstr(0, 0, timeStr)
            i = 1
            for interface in interfaces:
                if (
                    interface != "lo"
                    and bool(1 - interface.startswith("veth"))
                    and bool(1 - interface.startswith("蓝牙"))
                    and bool(1 - interface.startswith("VMware"))
                ):
                    if unit == "K" or unit == "k":
                        netIn = "%12.2fKB/s" % (networkIn.get(interface) / 1024)
                        netOut = "%11.2fKB/s" % (networkOut.get(interface) / 1024)
                    elif unit == "M" or unit == "m":
                        netIn = "%12.2fMB/s" % (networkIn.get(interface) / 1024 / 1024)
                        netOut = "%11.2fMB/s" % (
                            networkOut.get(interface) / 1024 / 1024
                        )
                    elif unit == "G" or unit == "g":
                        netIn = "%12.3fGB/s" % (
                            networkIn.get(interface) / 1024 / 1024 / 1024
                        )
                        netOut = "%11.3fGB/s" % (
                            networkOut.get(interface) / 1024 / 1024 / 1024
                        )
                    else:
                        netIn = "%12.1fB/s" % networkIn.get(interface)
                        netOut = "%11.1fB/s" % networkOut.get(interface)
                    stdscr.addstr(i, 0, interface)
                    stdscr.addstr(i + 1, 0, "Input:%s" % netIn)
                    stdscr.addstr(i + 2, 0, "Output:%s" % netOut)
                    stdscr.move(i + 3, 0)
                    i += 4
                    stdscr.refresh()
    except KeyboardInterrupt:
        # 还原终端
        curses.echo()
        curses.nocbreak()
        curses.endwin()
    except Exception as e:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        print("ERROR: %s!" % e)
        print("Please increase the terminal size!")
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A command for monitoring the traffic of network interface! Ctrl + C: exit"
    )
    parser.add_argument(
        "-t", "--time", type=int, help="the interval time for ouput", default=1
    )
    parser.add_argument(
        "-u",
        "--unit",
        type=str,
        choices=["b", "B", "k", "K", "m", "M", "g", "G"],
        help="the unit for ouput",
        default="M",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="output version information and exit",
        action="store_true",
    )
    args = parser.parse_args()
    if args.version:
        print("v1.0")
        exit(0)
    num = args.time
    unit = args.unit
    output(num, unit)
