# SageCell in a Container Using docker

### Network

This command creates an isolated network that allows the containers to comunnicate between each other without exposing more than is necessary to the outside.

```
docker network create sage_net
```

### Volume for SSH Keys

This command creates a volume for sharing SSH keys between the server and any workers. It is in-memory only within the container. The volume only retains files as long as at least one container has it mounted. The contents of the volume are discarded when the last container is removed.

```
docker volume create --driver local --opt type=tmpfs --opt device=tmpfs --opt o=size=1m,uid=1000,gid=1000 sage_keys
```

### Building the Image

```
docker build -t sagemath:10.7-sagecell .
```

### Creating an Instance of the Server
```
docker run -d --name server --rm \
  --volume sage_keys:/pubkey:rw \
  --network sage_net \
  --entrypoint server \
  sagemath:10.7-sagecell 
