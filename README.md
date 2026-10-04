# 🏐 FIPAV to iCal (.ics) COMUNELLO VOLLEY ROSA' - Seconda divisione maschile

Scraper in Python che estrae il calendario FIPAV del COMUNELLO VOLLEY ROSA' (Seconda divisione maschile) e lo converte in un file .ics sincronizzato.

---

## Come aggiungerlo al calendario

```
https://yurilunardon.github.io/calendario-volley/calendario.ics
```

### Generale
Sia su iPhone che su Android dovrebbe bastare cliccare sul link per aggiungerlo in automatico.
Se non dovesse funzionare segui le guide qui sotto:

### iPhone
1. **Impostazioni -> Calendario -> Account -> Aggiungi account**
2. **Altro -> Aggiungi calendario sottoscritto**
3. Incolla il link e salva

### Google Calendar
1. Apri [calendar.google.com](https://calendar.google.com)
2. Nella colonna a sinistra, accanto a *Altri calendari*, premi **+ -> Da URL**
3. Incolla il link e premi **Aggiungi calendario**

---

## Dati singola partita:
- **Titolo:** squadra di casa contro squadra ospite
- **Data e ora**
- **Palazzetto** con la posizione sulla mappa
- **Link per le indicazioni** in Google Maps, Apple Maps e Waze, nelle note dell'evento
- **Due avvisi:** uno il giorno prima e uno 3 ore prima della partita

(Gli avvisi si possono togliere dalle impostazioni del calendario sottoscritto sul telefono.)

---

## Come funziona

```
Sito FIPAV Vicenza  ->  script Python  ->  file calendario.ics  ->  GitHub Pages  ->  telefono
```

1. **Lo script** (`script.py`) apre il sito FIPAV, trova le partite della squadra e ne legge data, ora e palazzetto.
2. **Scrive il file** `calendario.ics` (formato standard per i calendari).
3. **GitHub Actions** lancia lo script in automatico ogni 6 ore.
4. **GitHub Pages** mette il file online a un indirizzo fisso.
5. **Il telefono** scarica il file ogni tanto e aggiorna gli eventi.

> Il calendario viene rigenerato ogni 6 ore, ma è il telefono a decidere quando scaricare la nuova versione. Di solito l'iPhone impiega qualche ora. Google Calendar può metterci anche un giorno intero.

### In caso di errore
Se il sito non risponde o una partita non si legge, lo script **si ferma senza aggiornare il file**. Resta quindi online l'ultima versione buona e non sparisce nessuna partita dal calendario. Al giro successivo riprova.
Se il sito dovesse continuare a rifiutare le richieste di lettura il calendario potrebbe non aggiornarsi per molto tempo. È quindi buona norma controllare sempre gli orari e le posizioni prima di ogni partita.

---

## Per tracciare una squadra diversa

Apri `script.py` e cambia le impostazioni in alto, poi lancia lo script:

| Impostazione | Significato |
|---|---|
| `TEAM_NAME` | Nome della squadra, scritto come sul sito (case sensitive) |
| `CHAMPIONSHIP_ID` | Numero del campionato, lo trovi nell'indirizzo della pagina (`CampionatoId=...`) |
| `MATCH_DURATION_HOURS` | Durata dell'evento nel calendario |
| `ALERT_TRIGGERS` | Quando arrivano gli avvisi (`-P1D` = 1 giorno prima, `-PT3H` = 3 ore prima) |

> Per mantenere il calendario aggiornato in caso di modifiche sul sito, creare una repo e usare GitHub Actions e GitHub Pages.

---

## Da sapere

- Questo è un progetto personale e **non è ufficiale** (non è collegato alla FIPAV né alla società).
- I dati arrivano dal sito pubblico FIPAV Vicenza. Lo script fa una richiesta ogni mezzo secondo per non appesantirlo.
- Le partite senza una data fissata non compaiono finché il sito non ne indica una.
- Se il sito cambia struttura, lo script potrebbe smettere di funzionare.