from flask import Flask, request, render_template, redirect, url_for, jsonify
app = Flask(__name__)

@app.route("/")
def root():
    return render_template('root.html')

@app.route("/eval")
def evaluate():
    computation_id=db.create_cell(request.values['commands'])
    return jsonify(computation_id=computation_id)

@app.route("/answers")
def answers():
    results = db.get_evaluated_cells()
    return render_template('answers.html', results=results)

if __name__ == "__main__":
    import sys
    import misc
    db = misc.select_db(sys.argv)
    app.run(debug=True)
