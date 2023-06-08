# hanbook
HANBOOK 백엔드

## Setup

0. Install docker, docker-compose

1. Copy `.env` file.
```sh
cp .env.sample .env
```

2. Set environ (config, naver openapi key)

3. Run / Stop
```sh
./run.sh
./stop.sh
```

4. Reset
```sh
./stop.sh
docker volume prune
```
