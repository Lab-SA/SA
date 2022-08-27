from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello Lab-SA!'

csaTable = [[1, 2, 3, 4], [2, 3, 4, 5]]
@app.route('/csa')
def csa():
    s = sum(item[-1] for item in csaTable)
    return render_template('process.html', name='CSA', rows=csaTable, sum=s)

if __name__ == '__main__':
    app.run(debug=True)
