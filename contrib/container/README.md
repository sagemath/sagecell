# SageCell in a Container

### docker

```
$ docker build -t sagemath:10.7-sagecell .
$ docker run -itd --name sagecell --rm -p 8888:8888 sagemath:10.7-sagecell
```


