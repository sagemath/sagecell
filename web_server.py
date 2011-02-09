from flask import Flask, request, render_template, redirect, url_for, jsonify
from time import time, sleep

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


@app.route("/output_poll")
def output_poll():
    """
    Return the output of a computation id (passed in the request)

    If a computation id has output, then return to browser. If no
    output is entered, then return nothing.
    """
    computation_id=request.values['computation_id']
    results = db.get_evaluated_cells(id=computation_id)
    if results is not None and len(results)>0:
        return jsonify({'output':results['output']})
    return jsonify([])

@app.route("/output_long_poll")
def output_long_poll():
    """
    Implements long-polling to return answers.

    If a computation id has output, then return to browser. Otherwise,
    poll the database periodically to check to see if the computation id
    is done.  Return after a certain number of seconds whether or not
    it is done.

    This currently blocks (calls sleep), so is not very useful.
    """
    default_timeout=2 #seconds
    poll_interval=.1 #seconds
    end_time=float(request.values.get('timeout', default_timeout))+time()
    computation_id=request.values['computation_id']
    while time()<end_time:
        results = db.get_evaluated_cells(id=computation_id)
        if results is not None and len(results)>0:
            return jsonify({'output':results['output']})
        sleep(poll_interval)
    return jsonify([])


if __name__ == "__main__":
    import sys
    import misc
    db = misc.select_db(sys.argv)
    app.run(debug=True)
