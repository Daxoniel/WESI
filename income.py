"""Estimated income, independent of Tk and the system clock.

Accrues only during a configured Monday-Friday daytime work schedule. This is an estimate,
not a payroll calculation; public holidays and salary history are not included.
"""
import math
from datetime import datetime


def validate_income(salary, weekly_hours, employment_start):
    salary, weekly_hours = float(salary), float(weekly_hours)
    if not math.isfinite(salary) or salary <= 0:
        raise ValueError("月净收入必须为有限的正数。")
    if not math.isfinite(weekly_hours) or not 0 < weekly_hours <= 168:
        raise ValueError("每周工作时间必须大于 0 且不超过 168 小时。")
    start = datetime.strptime(employment_start, "%Y-%m-%d %H:%M:%S")
    return salary, weekly_hours, start


def count_workdays(start, end):
    days = max(0, (end - start).days)
    weeks, remainder = divmod(days, 7)
    return weeks * 5 + sum((start.weekday() + i) % 7 < 5 for i in range(remainder))


def validate_schedule(work_start, work_end):
    begin = datetime.strptime(work_start, "%H:%M").time()
    finish = datetime.strptime(work_end, "%H:%M").time()
    if finish <= begin:
        raise ValueError("下班时间必须晚于上班时间，当前支持当日班次。")
    return begin, finish


def weekday_earnings(start, end, daily_target, work_start="09:00", work_end="17:00"):
    if end <= start:
        return 0.0
    first_midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    last_midnight = end.replace(hour=0, minute=0, second=0, microsecond=0)
    begin, finish = validate_schedule(work_start, work_end)
    def fraction(moment):
        shift_start = datetime.combine(moment.date(), begin)
        shift_end = datetime.combine(moment.date(), finish)
        return min(1.0, max(0.0, (moment - shift_start).total_seconds() /
                            (shift_end - shift_start).total_seconds()))
    days = float(count_workdays(first_midnight.date(), last_midnight.date()))
    if start.weekday() < 5:
        days -= fraction(start)
    if end.weekday() < 5:
        days += fraction(end)
    return max(0.0, days * daily_target)


def calculate_income(income, now=None):
    now = datetime.now() if now is None else now
    salary, hours, start = validate_income(
        income["monthly_net_salary"], income.get("weekly_work_hours", 40), income["employment_start"]
    )
    daily = salary * 12 / (52 * 5)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    work_start, work_end = income.get("work_start", "09:00"), income.get("work_end", "17:00")
    begin, finish = validate_schedule(work_start, work_end)
    shift_seconds = (datetime.combine(now.date(), finish) - datetime.combine(now.date(), begin)).total_seconds()
    active = now >= start and now.weekday() < 5 and begin <= now.time() < finish
    stats = {
        "rate": daily / shift_seconds if active else 0.0,
        "hourly_rate": daily / (shift_seconds / 3600),
        "daily_target": daily if now >= start and now.weekday() < 5 else 0.0,
    }
    for key, begin in (("today", day), ("month", day.replace(day=1)),
                       ("year", day.replace(month=1, day=1)), ("joined", start)):
        stats[key] = weekday_earnings(max(begin, start), now, daily, work_start, work_end)
    return stats
