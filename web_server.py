from flask import Flask, request, render_template, redirect, url_for
app = Flask(__name__)

@app.route("/")
def root():
    return render_template('root.html')

@app.route("/eval")
def evaluate():
    db.create_cell(request.values['input'])
    return redirect(url_for('answers'))

@app.route("/answers")
def answers():
    results = db.get_evaluated_cells()
    return render_template('answers.html', results=results)

url_for('static', filename='jquery-1.5.min.js')
url_for('static', filename='compute_server.js')

if __name__ == "__main__":
    import sys
    import misc
    db = misc.select_db(sys.argv)
    app.run(debug=True)
