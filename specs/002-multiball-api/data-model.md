# Data Model: Destination « Multiball »

## Connexion Multiball (dans `config.json`, tableau `connections`)

```json
{
  "name": "OSC to Multiball API",
  "from": { "protocol": "osc", "address_pattern": "/mb" },
  "to": {
    "protocol": "multiball",
    "base_url": "https://multiball-admin.net/api/v1.0",
    "api_key": "<clé API>",
    "token": "<jeton>",
    "court_id": "2ea7a1479cf93f8182dc8d7e",
    "start_delay": 3
  },
  "response_to_osc": { "enabled": true, "ip": "192.168.50.248", "port": 12097, "address": "/mb/result" }
}
```

| Champ | Obligatoire | Défaut | Règle |
|---|---|---|---|
| `from.protocol` | oui | | doit valoir `osc` |
| `from.address_pattern` | oui | `/mb` proposé dans l'interface | préfixe, sans `/` final |
| `to.base_url` | non | `https://multiball-admin.net/api/v1.0` | `/` final retiré |
| `to.api_key` | oui pour agir | | texte |
| `to.token` | oui pour agir | | secret, jamais journalisé ni renvoyé à l'interface |
| `to.court_id` | oui pour agir | | texte |
| `to.start_delay` | non | 3 | nombre, 0 à 60 secondes |
| `response_to_osc` | non | | même format que pour HTTP |

Vue renvoyée par `/get_config` : identique, avec `to.token = ""` et `to.token_set = true|false`.

## Cible interne (`targets_dict`)

`expand_connections()` recopie `base_url`, `api_key`, `token`, `court_id`, `start_delay` dans la cible `{type: "multiball", ...}`. La route garde `response_to_osc`.

## État par terrain (RAM, `multiball.py`)

Clé : `(base_url, court_id)`.

| Champ | Mis à jour par |
|---|---|
| `last_loaded` | succès de `switch`, succès du chargement dans `start` |
| `last_started` | succès de `play`, succès du démarrage dans `start` |
| `cancel_event` | créé au début d'un `start` ; déclenché par `switch`, `stop` ou un nouveau `start` |

## Séquence `start`

```text
annuler la séquence précédente → switchGame ─échec→ fin (0)
   └─succès→ [setConfiguration si durée > 0 ou difficulté fournie] ─échec→ fin (0)
       └─→ pause start_delay (annulable) ─annulée→ fin (0, "cancelled")
           └─→ start ─succès→ fin (1)
                 └─échec→ pause start_delay (annulable) → start ─succès→ fin (1) / échec→ fin (0)
```
