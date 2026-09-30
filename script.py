"""
Scaper di FIPAV Vicenza per generare un file .ics per il calendario delle partite di una squadra specifica.
Estrae i dettagli delle partite: data, ora, sede e coordinate geografiche.
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- CONFIGURATION ---------------------------------------
TEAM_NAME = "NEW VOLLEY CARTIGLIANO"
CHAMPIONSHIP_ID = "92936"
OUTPUT_FILE = "calendario.ics"
MATCH_DURATION_HOURS = 2
ALERT_TRIGGERS = ["-P1D", "-PT3H"]
# ----------------------------------------------------------------

BASE_URL = "https://www.fipavvicenza.it/mobile/risultati.asp"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEZONE_ROME = ZoneInfo("Europe/Rome")

# Sessione con tentativi automatici: se una richiesta fallisce (timeout, errori del server) riprova fino a 3 volte, aspettando sempre di più tra un tentativo e l'altro.
SESSION = requests.Session()
SESSION.headers.update(REQUEST_HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504]
)))


@dataclass
class MatchEvent:
    """Dati singola gara."""
    match_id: str
    start_time: datetime
    home_team: str
    away_team: str
    round_info: str
    venue_name: str
    address: str
    maps_url: str
    waze_url: str
    apple_maps_url: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None


def fetch_html(url: str) -> BeautifulSoup:
    """
    Esegue una richiesta HTTP GET e restituisce l'albero DOM parsato.
    """
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean_text(text: str) -> str:
    """Normalizza le stringhe rimuovendo spazi multipli e caratteri non-breaking (NBSP)."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def extract_first_text(element) -> str:
    """Estrae e normalizza il primo nodo testuale utile da un elemento BeautifulSoup."""
    return clean_text(next(element.stripped_strings, "")) if element else ""


def get_team_match_ids(soup: BeautifulSoup, team_name: str) -> List[str]:
    """
    Scansiona il calendario completo del campionato e filtra gli ID delle gare 
    in cui è coinvolta la squadra specificata.
    """
    match_ids = []
    for link in soup.select("a.gara"):
        href = link.get("href", "")
        match_id_search = re.search(r"GaraId=(\d+)", href)
        
        home_node = link.select_one(".squadraCasa")
        away_nodes = link.select(".squadraOspite")
        
        teams = [extract_first_text(home_node)] if home_node else []
        teams.extend(extract_first_text(node) for node in away_nodes)
        
        # Non case sensitive match per il nome della squadra
        if match_id_search and team_name.upper() in [t.upper() for t in teams]:
            match_ids.append(match_id_search.group(1))
            
    return match_ids


def parse_match_details(soup: BeautifulSoup, match_id: str) -> Optional[MatchEvent]:
    """
    Analizza la pagina di dettaglio di una singola gara per estrarre le varie informazioni.
    Ritorna None se la data della partita non è ancora stata definita.
    """
    raw_text = clean_text(soup.get_text(" "))

    # Estrazione pattern temporale (es. "Sab 17/10/2026 ore 19:30")
    time_match = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+ore\s+(\d{1,2}):(\d{2})", raw_text)
    if not time_match:
        return None  

    day, month, year, hour, minute = map(int, time_match.groups())
    start_time = datetime(year, month, day, hour, minute, tzinfo=TIMEZONE_ROME)

    home_node = soup.select_one(".gara .squadraCasa")
    away_node = soup.select_one(".gara .squadraOspite")
    if not home_node or not away_node:
        return None

    round_match = re.search(r"Giornata \d+ - Gara N.\s*\d+", raw_text)
    round_info = round_match.group(0) if round_match else ""

    # Estrazione dati impianto sportivo e coordinate Google/Waze/Apple
    venue_name, address, maps_url, waze_url, apple_maps_url = "", "", "", "", ""
    lat, lon = None, None
    
    venue_node = soup.select_one(".divImpianto")
    if venue_node:
        lines = [clean_text(r) for r in venue_node.get_text("\n").split("\n") if clean_text(r)]
        venue_name = lines[0] if lines else ""
        address = ", ".join(lines[1:])
        
        link_node = venue_node.find_parent("a")
        if link_node and link_node.get("href"):
            maps_url = link_node["href"]
            coords_match = re.search(r"q=(-?\d+\.\d+),(-?\d+\.\d+)", maps_url)
            if coords_match:
                lat, lon = coords_match.groups()
                # Generazione Deep Link universali
                waze_url = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
                apple_maps_url = f"https://maps.apple.com/?daddr={lat},{lon}"

    return MatchEvent(
        match_id=match_id,
        start_time=start_time,
        home_team=extract_first_text(home_node),
        away_team=extract_first_text(away_node),
        round_info=round_info,
        venue_name=venue_name,
        address=address,
        maps_url=maps_url,
        waze_url=waze_url,
        apple_maps_url=apple_maps_url,
        latitude=lat,
        longitude=lon
    )

# ---------- ICALENDAR (.ics) GENERATION ----------
VTIMEZONE_ROME = [
    "BEGIN:VTIMEZONE",
    "TZID:Europe/Rome",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0200",
    "TZNAME:CEST",
    "DTSTART:19700329T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0100",
    "TZNAME:CET",
    "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]

def escape_ics_text(text: str) -> str:
    """Effettua l'escape dei caratteri speciali riservati nello standard iCalendar."""
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def format_utc_datetime(dt: datetime) -> str:
    """Converte un oggetto datetime in formato UTC stringa compatibile con RFC 5545."""
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fold_ics_line(line: str) -> List[str]:
    """
    Implementa il 'line folding' (RFC 5545).
    """
    limit = 60
    segments = [line[:limit]]
    remaining = line[limit:]
    while remaining:
        segments.append(" " + remaining[:limit])
        remaining = remaining[limit:]
    return segments


def build_ics_event(match: MatchEvent, current_time_utc: str) -> List[str]:
    """Costruisce i blocchi VEVENT per il file .ics includendo estensioni per Apple Maps."""
    end_time = match.start_time + timedelta(hours=MATCH_DURATION_HOURS)
    
    location_parts = [part for part in (match.venue_name, match.address) if part]
    location_str = ", ".join(location_parts)
    
    # Costruzione dinamica della Descrizione con tutti i link ai navigatori
    description = match.round_info
    if match.maps_url:
        description += f"\n\nGoogle Maps: {match.maps_url}"
    if match.apple_maps_url:
        description += f"\nApple Maps: {match.apple_maps_url}"
    if match.waze_url:
        description += f"\nWaze: {match.waze_url}"

    summary = f"{match.home_team.title()} - {match.away_team.title()}"

    lines = [
        "BEGIN:VEVENT",
        f"UID:gara-{match.match_id}@fipav-calendario",
        f"DTSTAMP:{current_time_utc}",
        f"DTSTART;TZID=Europe/Rome:{match.start_time:%Y%m%dT%H%M%S}",
        f"DTEND;TZID=Europe/Rome:{end_time:%Y%m%dT%H%M%S}",
        f"SUMMARY:{escape_ics_text(summary)}",
        f"LOCATION:{escape_ics_text(location_str)}",
        f"DESCRIPTION:{escape_ics_text(description)}",
    ]
    
    if match.latitude and match.longitude:
        # Estensione proprietaria Apple per la gestione nativa delle posizioni in iOS/macOS
        safe_title = match.venue_name.replace('"', "'")
        safe_addr = location_str.replace('"', "'")
        lines.append(
            f'X-APPLE-STRUCTURED-LOCATION;VALUE=URI;X-ADDRESS="{safe_addr}";'
            f'X-APPLE-RADIUS=100;X-TITLE="{safe_title}":geo:{match.latitude},{match.longitude}'
        )
        
    if match.maps_url:
        lines.append(f"URL:{match.maps_url}")
        
    # Notifiche
    for trigger in ALERT_TRIGGERS:
        lines.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{escape_ics_text(summary)}",
            f"TRIGGER:{trigger}",
            "END:VALARM",
        ])

    lines.append("END:VEVENT")
    return lines


def generate_ics_calendar(matches: List[MatchEvent]) -> str:
    """Assembla l'intero calendario e applica il line folding a tutte le righe."""
    current_time_utc = format_utc_datetime(datetime.now(timezone.utc))
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FIPAV-Calendar-Scraper//IT",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape_ics_text(TEAM_NAME.title())}",
        "X-WR-TIMEZONE:Europe/Rome",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    
    lines.extend(VTIMEZONE_ROME)

    for match in matches:
        lines.extend(build_ics_event(match, current_time_utc))
        
    lines.append("END:VCALENDAR")
    
    folded_lines = [segment for line in lines for segment in fold_ics_line(line)]
    return "\r\n".join(folded_lines) + "\r\n"


def main() -> None:
    print(f"Recupero l'elenco gare per il campionato {CHAMPIONSHIP_ID}...")
    
    list_url = f"{BASE_URL}?CampionatoId={CHAMPIONSHIP_ID}"
    match_ids = get_team_match_ids(fetch_html(list_url), TEAM_NAME)
    
    print(f"Identificate {len(match_ids)} partite per '{TEAM_NAME}'.\n")

    matches: List[MatchEvent] = []
    errors: List[str] = []
    
    for match_id in match_ids:
        time.sleep(0.5)
        
        try:
            detail_url = f"{BASE_URL}?CampionatoId={CHAMPIONSHIP_ID}&GaraId={match_id}"
            match_event = parse_match_details(fetch_html(detail_url), match_id)
        except requests.RequestException as e:
            print(f"[!] Gara {match_id}: errore di rete ({e})")
            errors.append(match_id)
            continue
        
        if not match_event:
            print(f"[-] Gara {match_id}: Data non ancora definita (Skipped)")
            continue
            
        matches.append(match_event)
        print(f"[+] {match_event.start_time:%d/%m/%Y %H:%M} | {match_event.home_team} vs {match_event.away_team}")

    if errors:
        raise SystemExit(f"\n{len(errors)} gare non lette: file NON aggiornato, per non perdere partite dal calendario.")

    if not matches:
        raise SystemExit("\nNessun evento valido trovato. Il file di output non verrà sovrascritto.")

    # Ordinamento cronologico degli eventi prima del salvataggio
    matches.sort(key=lambda x: x.start_time)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as file:
        file.write(generate_ics_calendar(matches))
        
    print(f"\nOperazione completata: {len(matches)} eventi esportati con successo in '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()