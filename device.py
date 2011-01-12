import time
import pymongo

def run():
    code = pymongo.Connection().demo.code

    while True:
        # Query for all cells that don't have an output key.
        for X in code.find({'output':{'$exists': False}}):
            s = X['input']
            print "evaluating '%s'"%s
            try:
                output = str(eval(s))
            except Exception, mesg:
                output = str(mesg)
            except:
                output = "yikes"
            code.update({'_id':X['_id']}, {'$set':{'output':output}})
        time.sleep(.1)

if __name__ == "__main__":
    run()
