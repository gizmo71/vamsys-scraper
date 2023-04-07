# vamsys-scraper

Create a `vamsys.py` with a `config` dictionary containing `username` and `password`.

## Using podman

In WSL2 (using openSUSE Tumbleweed as at the time of writing it was one of the few with Podman 4).
Or
```sh
sudo apt install podman
podman build -t gizmo71/vamsys-scraper -f Dockerfile
podman run -it --rm -v.:/data --shm-size="2g" gizmo71/vamsys-scraper python3 /data/scrape.py
podman run -it --rm -v.:/data gizmo71/vamsys-scraper python3 /data/process.py
```
