import time
import datetime
from pathlib import Path


def logging_thread(log_queue, global_start, timetag):
    # check if /log/ folder exists if not, create it
    log_folder = Path(__file__).resolve().parent / f"logs/log_{timetag}"
    if not log_folder.exists():
        print("Creating log folder")
        log_folder.mkdir()
    log_file_name = f"./logs/log_{timetag}/amica_log_{timetag}"
    log_file = open(log_file_name+".csv", "w")
    log_file_ELAN= open(log_file_name + "_ELAN.csv", "w")
    print("Log file started: ", log_file_name)
    log_file.write("date\ttime\ttime_start\ttime_end\tevent\tvalue_0\tvalue_1\n"
                   "YYYY-MM-DD\tHH:MM:SS\tms\tms\n")
    log_file.flush()

    log_file_ELAN.write("Tier\tBegin Time\tEnd Time\tAnnotation\n")
    log_file_ELAN.flush()

    while True:
        if log_queue.empty():
            time.sleep(0.1)
        else:
            start, end, event, values = log_queue.get()
            start_datetime = datetime.datetime.fromtimestamp(start)
            log_file.write(f"{start_datetime.strftime('%Y-%m-%d')}\t"
                           f"{start_datetime.strftime('%H:%M:%S.%f')[:-3]}\t"
                           f"{round(1000*(start - global_start))}\t"
                           f"{round(1000*(end - global_start))}\t"
                           f"{event}")
            for value in values:
                log_file.write(f"\t{value}")
            log_file.write("\n")
            log_file.flush()
            log_file_ELAN.write(f"{event}\t"
                                f"{round(1000*(start - global_start))}\t"
                                f"{round(1000*(end - global_start))}\t"
                                f"{values[0]}\n")
            log_file_ELAN.flush()
            if event == "logging_end":
                log_file.close()
                log_file_ELAN.close()
                break