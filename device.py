import sys, time

def run(db):
    print "Starting device loop..."
    while True:
        # Evaluate all cells that don't have an output key.
        for X in db.get_unevaluated_cells():
            s = X['input']
            print "evaluating '%s'"%s
            try:
                output = str(eval(s))
            except Exception, mesg:
                output = str(mesg)
            except:
                output = "yikes"
            # Store the resulting output
            db.set_output(X['_id'], output)
        time.sleep(.1)

if __name__ == "__main__":
    import misc
    db = misc.select_db(sys.argv)
    run(db)
