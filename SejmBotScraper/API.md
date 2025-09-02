# API Sejmu RP - SejmBot Scraper

**Base URL:** `https://api.sejm.gov.pl/`

## Podstawowe endpointy

### Kadencje
```
GET /sejm/term
GET /sejm/term{term}
```

### Posiedzenia
```
GET /sejm/term{term}/proceedings
GET /sejm/term{term}/proceedings/current
GET /sejm/term{term}/proceedings/{id}
```

## Transkrypty i wypowiedzi

### PDF transkryptów (główne)
```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts/pdf
```

### Metadane wypowiedzi
```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts
```

### Pojedyncza wypowiedź HTML
```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts/{statementNum}
```

## Posłowie i kluby

### Posłowie
```
GET /sejm/term{term}/MP
GET /sejm/term{term}/MP/{id}
GET /sejm/term{term}/MP/{id}/photo
```

### Kluby parlamentarne
```
GET /sejm/term{term}/clubs
GET /sejm/term{term}/clubs/{id}
GET /sejm/term{term}/clubs/{id}/logo
```

## Głosowania

### Lista głosowań
```
GET /sejm/term{term}/votings
GET /sejm/term{term}/votings/{sitting}
GET /sejm/term{term}/votings/{sitting}/{num}
GET /sejm/term{term}/votings/search
```

### Statystyki głosowań posła
```
GET /sejm/term{term}/MP/{id}/votings/stats
GET /sejm/term{term}/MP/{id}/votings/{sitting}/{date}
```

## Komisje

### Lista komisji
```
GET /sejm/term{term}/committees
GET /sejm/term{term}/committees/{code}
```

### Posiedzenia komisji
```
GET /sejm/term{term}/committees/{code}/sittings
GET /sejm/term{term}/committees/{code}/sittings/{num}
GET /sejm/term{term}/committees/sittings/{date}
```

### Transkrypty komisji
```
GET /sejm/term{term}/committees/{code}/sittings/{num}/html
GET /sejm/term{term}/committees/{code}/sittings/{num}/pdf
```

## Interpelacje i zapytania

### Interpelacje
```
GET /sejm/term{term}/interpellations
GET /sejm/term{term}/interpellations/{num}
GET /sejm/term{term}/interpellations/{num}/body
```

### Zapytania pisemne
```
GET /sejm/term{term}/writtenQuestions
GET /sejm/term{term}/writtenQuestions/{num}
GET /sejm/term{term}/writtenQuestions/{num}/body
```

## Druki i procesy legislacyjne

### Druki sejmowe
```
GET /sejm/term{term}/prints
GET /sejm/term{term}/prints/{num}
GET /sejm/term{term}/prints/{num}/{attach_name}
```

### Procesy legislacyjne
```
GET /sejm/term{term}/processes
GET /sejm/term{term}/processes/passed
GET /sejm/term{term}/processes/{num}
```

## Wideo

### Transmisje wideo
```
GET /sejm/term{term}/videos
GET /sejm/term{term}/videos/today
GET /sejm/term{term}/videos/{date}
GET /sejm/term{term}/videos/{unid}
```

## Parametry URL

- `{term}` - numer kadencji (np. 10)
- `{id}` - numer posiedzenia
- `{date}` - data w formacie YYYY-MM-DD
- `{num}` - numer elementu
- `{code}` - kod komisji
- `{sitting}` - numer posiedzenia

## Parametry query

Większość endpointów wspiera:
- `limit` - maksymalna liczba wyników (domyślnie 50)
- `offset` - przesunięcie w wynikach
- `sort_by` - sortowanie (dodaj `-` dla malejącego)
- `since` / `till` - filtrowanie dat
- `modifiedSince` - tylko zmienione od daty

## Uwagi techniczne

- Format daty: YYYY-MM-DD
- Format datetime: YYYY-MM-DDTHH:mm:ss