# Contract: messages OSC (COGS vers Mini-OSC, et retour)

Préfixe d'exemple : `/mb`. Les arguments sont positionnels.

## Entrants

| Message | Arguments | Appels API |
|---|---|---|
| `/mb/start` | `gameId` (texte), `duration` (s, optionnel, 0 = non fourni), `difficulty` (0 à 1, optionnel) | switchGame, [setConfiguration], pause, start (+ 1 nouvelle tentative) |
| `/mb/switch` | `gameId` | switchGame |
| `/mb/play` | `gameId` optionnel (défaut : dernier chargé, puis jeu en cours sur le terrain) | start |
| `/mb/stop` | `gameId` optionnel (défaut : dernier lancé, puis jeu en cours sur le terrain) | stop |
| `/mb/status` | aucun | GET court |

Rejetés sans appel (log clair, retour `0` si activé) : `/mb` seul, `/mb/<inconnu>`, `/mb/a/b`, gameId manquant, durée non numérique, difficulté hors 0 à 1, connexion sans clé, jeton ou terrain.

## Retour (si `response_to_osc.enabled`)

| Cas | Message envoyé |
|---|---|
| succès d'une action | `<address> <action> 1 <message>` ex. `/mb/result start 1 "Game started"` |
| échec | `<address> <action> 0 <message d'erreur>` ex. `/mb/result start 0 "Invalid api key!"` |
| status | `<address> status 1 <status> <nom du jeu> <gameId>` ex. `/mb/result status 1 "online" "Eclipsium Drone Defense" "288b6480c62001f919d2736e"` |
| status en échec | `<address> status 0 <message d'erreur>` |

`<action>` est l'action reçue en minuscules (ou le texte brut pour une action inconnue, `""` pour le préfixe seul). `ok` est un entier OSC.
