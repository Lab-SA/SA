import time
from openpyxl import load_workbook
from ast import literal_eval

def writeToExcel(filename, run_data):
    write_wb = load_workbook(filename)
    write_ws = write_wb.create_sheet(str(int(time.time())))
    for data in run_data:
        write_ws.append(data)
    write_wb.save(filename)
    write_wb.close()

def writeWeightsToFile(weights):
    # WARN: STATIC FILE PATH!
    # weights must be 1-dim list
    f = open('../../results/model.txt', 'w')
    f.write(str(weights))
    f.close()

def readWeightsFromFile():
    # WARN: STATIC FILE PATH!
    # return 1-dim list (weights)
    f = open('../../results/model.txt', 'r')
    weights = f.readline()
    f.close()
    return literal_eval(weights)
