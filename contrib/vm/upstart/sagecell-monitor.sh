start on started sagecell

stop on stopped sagecell

script 
set -e
while /home/sageserver/sage/devel/sagecell/contrib/sagecell-client/sagecell-service.py http://localhost:8080; do
    echo Continuing monitor service
    sleep 30
end script
