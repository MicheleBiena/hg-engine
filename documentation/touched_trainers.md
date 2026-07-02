# Touched Trainers

Ultimo aggiornamento: 2026-06-27

Formato lista trainer: `numero: Classe allenatore - Nome (percorso/area)`

## Regole Area Export

Obiettivo CSV/XLSX/HTML finale: allenatori divisi chiaramente per area, in
ordine di esplorazione del gioco, non in ordine di id allenatore.

Ordine aree: definito manualmente dal user. Non inferire da trainer id.

Area di ogni trainer: commento compatto accanto all'initializer del trainer in
`data/Trainers.c`.

Formato:

```c
[24] = { // Route4
```

Esempi:

```c
[24] = { // Route4
[256] = { // Gym1
[19] = { // HeritagePark
```

Regole:

- Ogni trainer esportato deve avere commento area sulla riga `[id] = {`.
- Area id compatta e leggibile: esempi `Route4`, `Gym1`, `HeritagePark`.
- Il tool deve ordinare per lista aree manuale, poi per ordine delle righe in
  questo file dentro la stessa area.
- Se manca commento area, o area non esiste nella lista manuale, il tool deve
  avvisare o fallire.
- CSV: row separatore area ben visibile. XLSX/HTML: separatore colorato.

## Ordine Aree

1. `Route2` = Route 2
2. `Route3` = Route 3
3. `Gym1` = Gym 1
4. `RavagedPath` = Ravaged Path
5. `R3PostCave` = R3 Post Cave
6. `HeritagePark` = Heritage Park
7. `Gym2` = Gym 2
8. `Route4` = Route 4

## Elenco

4: School Kid - Alex (Route 2)
5: Lass - Victoria (Route 2)
8: Youngster - Joey (Route 2)
9: Bug Catcher - Leo (Route 2)
11: Hiker - Aiden (Route 3, Ravaged Path)
12: Elder - Marcus (Route 3, Ravaged Path)
13: Lass - Sarah (Route 3)
14: Ace Trainer - Michelle (Route 3, lato post-grotta)
15: Beauty - Belle (Route 3, lato post-grotta)
16: Black Belt - Simon (Route 3, lato post-grotta)
17: Picnicker - Solana (Route 3, lato post-grotta)
18: Hiker - Justin (Route 3, Ravaged Path)
19: Fisherman - John (Heritage Park, evento pescatore)
20: Fisherman - John (Heritage Park, evento pescatore)
21: Fisherman - John (Heritage Park, evento pescatore)
22: Fisherman - John (Heritage Park, evento pescatore)
23: Fisherman - John (Heritage Park, evento pescatore)
24: Ace Trainer - Gavin (Route 4, verso Newport)
25: Poke Kid - Poppy (Route 4, verso Newport)
26: Black Belt - Takeshi (Route 4, verso Newport)
27: Bird Keeper - Corbin (Route 4, verso Newport)
28: Bug Catcher - Milo (Route 4, verso Newport)
29: Sailor - Ronan (Route 4, verso Newport)
36: Black Belt - Daichi (Route 4, verso Newport, script battle Hitmonlee)
37: Black Belt - Daichi (Route 4, verso Newport, script battle Hitmonchan)
253: Gym Leader - Kaseki (Palestra Roccia, Gym 2)
256: Gym Leader - Erika (Palestra Erba, Gym 1)
308: Camper - Jerry (Palestra Roccia, Gym 2)
346: Beauty - Julia (Palestra Erba, Gym 1)
356: Lass - Michelle (Palestra Erba, Gym 1)
685: Hiker - Edwin (Palestra Roccia, Gym 2)

## Da Confermare

Nessuno al momento.