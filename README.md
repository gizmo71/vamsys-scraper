# vamsys-scraper

Logs into each of your active (vAMSYS)[https://vamsys.io/] airlines, pulls the route and activity data, and transforms them into a unified page for examining routes and seeing how soon your must file your PIREP for each airline.

Currently hardcoded to only show A20N and A339 routes, with some mappings where those types are shared with others.

## Credentials

- Create a `vamsys.py` with a `config` dictionary containing `username` and `password`.
- If using the GitHub action, create secrets of `VAMSYS_USERNAME` and `VAMSYS_PASSWORD`.

## Using podman

In WSL2 (using openSUSE Tumbleweed as at the time of writing it was one of the few with Podman 4).
Or
```sh
sudo apt install podman
podman build -t gizmo71/vamsys-scraper -f Dockerfile
podman run -it --rm -v.:/data --shm-size="2g" gizmo71/vamsys-scraper python3 /data/scrape.py
podman run -it --rm -v.:/data gizmo71/vamsys-scraper python3 /data/process.py
```
