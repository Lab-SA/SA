import time
from openpyxl import Workbook

def writeToExcel(filename, run_data):
    write_wb = Workbook()
    write_ws = write_wb.create_sheet(str(int(time.time())))
    for data in run_data:
        write_ws.append(data)
    write_wb.save(filename)
