from flask import Flask, request, render_template, redirect, url_for
app = Flask(__name__)

@app.route("/")
def root():
    return render_template('root.html')

@app.route("/eval")
def evaluate():
    import pymongo
    db = pymongo.Connection().demo
    db.code.insert({'input':request.values['input']})
    return redirect(url_for('answers'))

@app.route("/answers")
def answers():
    import pymongo
    db = pymongo.Connection().demo
    results = db.code.find({'output':{'$exists': True}})
    return render_template('answers.html', results=results)

if __name__ == "__main__":
    app.run(debug=True)
