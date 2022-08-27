from flask import Flask, render_template
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from client.BasicSAClient import sendRequestAndReceive

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello Lab-SA!'

csaTable = []
@app.route('/csa')
def csa():
    global csaTable
    try:
        response = sendRequestAndReceive("localhost", 8000, "table", {})
        csaTable = response['data']
    except:
        pass
    s = sum(item[-1] for item in csaTable)
    return render_template('process.html', name='CSA', rows=csaTable, sum=s)

if __name__ == '__main__':
    app.run(debug=True)
