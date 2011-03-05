from flask import Flask, request, render_template, redirect, url_for, jsonify
from time import time, sleep
from functools import wraps

app = Flask(__name__)

def print_exception(f):
    """
    This decorator prints any exceptions that occur to the webbrowser.  This printing works even for uwsgi and nginx.
    """
    import traceback
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except:
            return "<pre>%s</pre>"%traceback.format_exc()
    return wrapper

def get_db(f):
    """
    This decorator gets the database and passes it into the function as the first argument.
    """
    import misc, sys
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            # We see if db and fs are even defined yet by just referring to them.
            (db, fs)
        except NameError:
            db,fs=misc.select_db(sys.argv)
        args = (db,fs) + args
        return f(*args, **kwds)
    return wrapper

@app.route("/")
def root():
    return render_template('root.html')

@app.route("/eval")
@get_db
def evaluate(db,fs):
    computation_id=db.create_cell(request.values['commands'])
    return jsonify(computation_id=computation_id)

@app.route("/answers")
@print_exception
@get_db
def answers(db,fs):
    results = db.get_evaluated_cells()
    return render_template('answers.html', results=results)


@app.route("/output_poll")
@print_exception
@get_db
def output_poll(db,fs):
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
@print_exception
@get_db
def output_long_poll(db,fs):
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
    db, fs = misc.select_db(sys.argv)
    app.run(debug=True)
