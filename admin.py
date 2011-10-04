
def get_commands():
    from cgi import escape
    import misc
    db, fs = misc.select_db(None)


    with open('commands.html','w') as f:
        f.write("""
<html>
<STYLE TYPE="text/css">
  pre { border: 1px solid}
</STYLE>
<body>""")
        for m in db.database.input_messages.find():
            f.write("<pre>")
            f.write("<b>"+str(m.get('timestamp',None))+"</b>")
            f.write("\n")
            code=m['content']['code']
            
            s=escape(code if code is not None else 'None')
            f.write(s.encode('utf-8'))
            f.write("</pre>")
        f.write("</body></html>")
    

if __name__ == "__main__":
    get_commands()
