# Quickstart: valider la destination Multiball

## Tests automatiques (aucun appel réel)

```bash
.venv-desktop/bin/python -m pytest tests
.venv-desktop/bin/python desktop.py --smoke-test
```

Attendu : tous les tests passent, dont `tests/test_multiball.py` (requêtes, séquence `start`, nouvelle tentative, mémoire, annulation, secrets, action inconnue, routes `/get_config`, export, import, `/multiball_list`).

## Vérification dans l'interface

1. Lancer `python desktop.py` (ou l'app), onglet Connections, « Add Connection ».
2. Source OSC, préfixe `/mb` ; destination « Multiball (LYMB API) ».
3. Saisir la clé API et le jeton, cliquer « Test and list » : la liste des terrains s'affiche (lecture seule). Cliquer « Eclipsium-Nantes » : l'identifiant du terrain se remplit et les 49 jeux s'affichent avec leurs identifiants.
4. Enregistrer. Dans la table, la destination affiche `MULTIBALL` et le terrain. Recharger la page puis « Edit » : le champ jeton est vide avec l'indication « token saved ».
5. Onglet Logs : aucune ligne ne contient le jeton.

## Vérification avec le mur (uniquement avec l'accord de l'exploitant)

Depuis COGS ou un client OSC de test vers le port OSC de Mini-OSC :

```text
/mb/status                                  → log du statut, retour "status 1 online <jeu> <id>"
/mb/start "288b6480c62001f919d2736e"        → switchGame, pause 3 s, start
/mb/stop                                    → stop du jeu lancé
```
