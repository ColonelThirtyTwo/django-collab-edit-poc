# django-collab-poc

Proof-of-concept for collaborative editing in Django.

Uses YJS via the pycrdt package, with django-channels and pycrdt-websocket to provide communication, and
the TipTap rich text editor.

## Running

1. `docker compose build`
2. `docker compose run --rm build-frontend`, or, on the host, `cd` to `frontend` and run `npm run watch`
3. `docker compose run --rm django-server createsuperuser` to create a user
4. `docker compose up -d` then navigate to `localhost:8001`
