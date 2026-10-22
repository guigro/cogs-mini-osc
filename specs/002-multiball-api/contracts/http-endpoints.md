# Contract: routes HTTP (interface web)

## `GET /get_config` (modifiée)

Renvoie la configuration avec, pour chaque connexion `to.protocol == "multiball"` : `token: ""` et `token_set: bool`.

## `POST /add_connection`, `POST /update_connection` (modifiées)

- `to.token_set` est ignoré et retiré.
- `update_connection` : si `to.protocol == "multiball"` et `to.token` vide, le jeton déjà enregistré pour cet index (si c'était une connexion Multiball) est conservé.

## `GET /export_config` (modifiée)

- Par défaut : jetons Multiball vidés.
- `?include_secrets=1` : fichier tel quel. L'interface n'appelle cette URL qu'après une case cochée et une confirmation d'avertissement.

## `POST /import_config` (modifiée)

Après validation : chaque connexion Multiball sans jeton reprend le jeton d'une connexion Multiball de la configuration actuelle ayant la même `api_key`.

## `POST /multiball_list` (nouvelle, lecture seule)

Requête :

```json
{ "what": "courts" | "games", "base_url": "...", "api_key": "...", "token": "...", "court_id": "...", "index": 3 }
```

- `token` vide et `index` fourni : le serveur utilise le jeton, la clé et l'adresse d'API enregistrés pour cette connexion (l'adresse saisie est ignorée dans ce cas).
- `what: "games"` exige `court_id`.

Réponses :

```json
{ "ok": true, "courts": [ { "id": "...", "title": "...", "description": "..." } ] }
{ "ok": true, "games": [ { "id": "...", "name": "...", "dispName": "...", "versions": [ ... ] } ] }
{ "ok": false, "status": 401, "error": "Invalid api key!" }
```

Code HTTP 200 dans tous les cas traités (l'erreur est dans `ok/error`), 400 si la requête est incomplète.
