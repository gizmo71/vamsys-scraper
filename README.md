# vamsys-scraper

Logs into each of your active [vAMSYS](https://vamsys.io/) airlines, pulls the route and activity data, and transforms them into a unified page for examining routes and seeing how soon your must file your PIREP for each airline.

- Needs git@github.com:ip2location/ip2location-iata-icao.git too.
- Also needs pages cloned into own folder.

## Credentials

- Create a `vamsys.py` with a `config` dictionary containing `username` and `password`.
- If using the GitHub action, create secrets of `VAMSYS_USERNAME` and `VAMSYS_PASSWORD`.

## Using podman

In WSL2 (using openSUSE Tumbleweed as at the time of writing it was one of the few with Podman 4).
Or
```sh
sudo apt install podman
podman build -t gizmo71/vamsys-scraper -f python.Dockerfile
podman run -it --rm -v.:/data --shm-size="2g" gizmo71/vamsys-scraper python3 /data/scrape.py
podman run -it --rm -v.:/data -v../vamsys-scraper-pages:/pages -v../ip2location-iata-icao/iata-icao.csv:/iata-icao.csv gizmo71/vamsys-scraper python3 /data/process.py
```
