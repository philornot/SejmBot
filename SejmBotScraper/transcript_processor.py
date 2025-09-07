# transcript_processor.py
"""
Procesor transkryptów - łączy wypowiedzi z danymi posłów i tworzy finalne JSONy gotowe do analizy
"""

import json
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

from config import BASE_OUTPUT_DIR

logger = logging.getLogger(__name__)


class TranscriptProcessor:
    """Procesor do wzbogacania transkryptów o dane posłów i przygotowywania ich do analizy"""

    def __init__(self):
        self.base_dir = Path(BASE_OUTPUT_DIR)
        self.mps_cache = {}  # Cache dla danych posłów
        self.clubs_cache = {}  # Cache dla danych klubów

        # Statystyki przetwarzania
        self.processing_stats = {
            'processed_statements': 0,
            'matched_speakers': 0,
            'unmatched_speakers': 0,
            'enriched_statements': 0,
            'validation_errors': 0,
            'created_files': 0
        }

    def load_mps_data(self, term: int) -> bool:
        """
        Ładuje dane posłów dla danej kadencji do cache

        Args:
            term: numer kadencji

        Returns:
            True jeśli udało się załadować dane
        """
        try:
            mp_dir = self.base_dir / f"kadencja_{term:02d}" / "poslowie"

            if not mp_dir.exists():
                logger.error(f"Brak katalogu z danymi posłów dla kadencji {term}")
                return False

            # Ładowanie listy posłów
            mps_list_path = mp_dir / "lista_poslow.json"
            if not mps_list_path.exists():
                logger.error(f"Brak pliku lista_poslow.json w {mp_dir}")
                return False

            with open(mps_list_path, 'r', encoding='utf-8') as f:
                mps_list = json.load(f)

            self.mps_cache[term] = {}

            # Ładowanie szczegółowych danych posłów
            for mp in mps_list:
                mp_id = mp.get('id')
                if mp_id:
                    # Próbujemy załadować szczegółowe dane
                    mp_files = list(mp_dir.glob(f"posel_{mp_id:03d}_*.json"))
                    if mp_files:
                        try:
                            with open(mp_files[0], 'r', encoding='utf-8') as f:
                                detailed_mp = json.load(f)
                            self.mps_cache[term][mp_id] = detailed_mp
                        except Exception as e:
                            logger.warning(f"Nie można załadować szczegółów posła {mp_id}: {e}")
                            # Używamy podstawowych danych
                            self.mps_cache[term][mp_id] = mp
                    else:
                        # Używamy podstawowych danych z listy
                        self.mps_cache[term][mp_id] = mp

            logger.info(f"Załadowano dane {len(self.mps_cache[term])} posłów dla kadencji {term}")
            return True

        except Exception as e:
            logger.error(f"Błąd ładowania danych posłów: {e}")
            return False

    def load_clubs_data(self, term: int) -> bool:
        """
        Ładuje dane klubów dla danej kadencji do cache

        Args:
            term: numer kadencji

        Returns:
            True jeśli udało się załadować dane
        """
        try:
            clubs_dir = self.base_dir / f"kadencja_{term:02d}" / "poslowie" / "kluby"

            if not clubs_dir.exists():
                logger.warning(f"Brak katalogu z danymi klubów dla kadencji {term}")
                return False

            clubs_list_path = clubs_dir / "lista_klubow.json"
            if clubs_list_path.exists():
                with open(clubs_list_path, 'r', encoding='utf-8') as f:
                    clubs_list = json.load(f)

                self.clubs_cache[term] = {}
                for club in clubs_list:
                    club_id = club.get('id')
                    if club_id:
                        self.clubs_cache[term][club_id] = club

                logger.info(f"Załadowano dane {len(self.clubs_cache[term])} klubów dla kadencji {term}")
                return True

        except Exception as e:
            logger.error(f"Błąd ładowania danych klubów: {e}")

        return False

    def match_speakers_with_mps(self, statements: List[Dict], term: int) -> List[Dict]:
        """
        Łączy mówców z wypowiedzi z bazą danych posłów

        Args:
            statements: lista wypowiedzi
            term: numer kadencji

        Returns:
            Lista wypowiedzi z dodanymi dopasowaniami do posłów
        """
        if term not in self.mps_cache:
            if not self.load_mps_data(term):
                logger.error(f"Nie można załadować danych posłów dla kadencji {term}")
                return statements

        matched_statements = []

        for statement in statements:
            matched_statement = statement.copy()
            speaker_data = statement.get('speaker', {})
            speaker_name = speaker_data.get('name', '').strip()

            if not speaker_name:
                matched_statement['mp_match'] = {
                    'matched': False,
                    'reason': 'brak_nazwy_mowcy'
                }
                matched_statements.append(matched_statement)
                continue

            # Szukamy dopasowania
            mp_match = self._find_mp_match(speaker_name, speaker_data, term)
            matched_statement['mp_match'] = mp_match

            if mp_match['matched']:
                self.processing_stats['matched_speakers'] += 1
            else:
                self.processing_stats['unmatched_speakers'] += 1

            matched_statements.append(matched_statement)

        return matched_statements

    def _find_mp_match(self, speaker_name: str, speaker_data: Dict, term: int) -> Dict:
        """
        Znajduje dopasowanie mówcy do posła

        Args:
            speaker_name: nazwa mówcy
            speaker_data: dane mówcy z transkryptu
            term: numer kadencji

        Returns:
            Słownik z informacjami o dopasowaniu
        """
        # Wyczyść nazwę mówcy
        cleaned_name = self._clean_speaker_name(speaker_name)

        # Lista możliwych dopasowań z oceną
        matches = []

        for mp_id, mp_data in self.mps_cache[term].items():
            mp_full_name = f"{mp_data.get('firstName', '')} {mp_data.get('lastName', '')}".strip()
            mp_last_name = mp_data.get('lastName', '').strip()

            # Różne strategie dopasowywania
            score = 0
            match_type = None

            # 1. Dokładne dopasowanie pełnej nazwy
            if cleaned_name.lower() == mp_full_name.lower():
                score = 100
                match_type = 'pelna_nazwa_dokladna'

            # 2. Dokładne dopasowanie nazwiska
            elif cleaned_name.lower() == mp_last_name.lower():
                score = 90
                match_type = 'nazwisko_dokladne'

            # 3. Podobieństwo nazw (SequenceMatcher)
            else:
                similarity_full = SequenceMatcher(None, cleaned_name.lower(), mp_full_name.lower()).ratio()
                similarity_last = SequenceMatcher(None, cleaned_name.lower(), mp_last_name.lower()).ratio()

                if similarity_full > 0.85:
                    score = int(similarity_full * 80)
                    match_type = 'pelna_nazwa_podobna'
                elif similarity_last > 0.85:
                    score = int(similarity_last * 70)
                    match_type = 'nazwisko_podobne'
                elif speaker_name.lower() in mp_full_name.lower() or mp_full_name.lower() in speaker_name.lower():
                    score = 60
                    match_type = 'zawiera_nazwe'

            # Dodatkowe punkty za zgodność klubu (jeśli dostępne)
            speaker_club = speaker_data.get('club', '').strip()
            mp_club = mp_data.get('club', '').strip()

            if speaker_club and mp_club and speaker_club.lower() == mp_club.lower():
                score += 10
                if match_type:
                    match_type += '_klub_zgodny'

            if score > 50:  # Próg akceptacji dopasowania
                matches.append({
                    'mp_id': mp_id,
                    'mp_data': mp_data,
                    'score': score,
                    'match_type': match_type,
                    'similarity_info': {
                        'speaker_name': speaker_name,
                        'mp_full_name': mp_full_name,
                        'mp_last_name': mp_last_name
                    }
                })

        # Sortuj według najlepszego dopasowania
        matches.sort(key=lambda x: x['score'], reverse=True)

        if matches and matches[0]['score'] > 70:  # Próg pewności
            best_match = matches[0]
            return {
                'matched': True,
                'mp_id': best_match['mp_id'],
                'mp_data': best_match['mp_data'],
                'match_score': best_match['score'],
                'match_type': best_match['match_type'],
                'similarity_info': best_match['similarity_info'],
                'alternatives': matches[1:3] if len(matches) > 1 else []  # Top 2 alternatywy
            }
        else:
            return {
                'matched': False,
                'reason': 'brak_dopasowania_powyzej_progu',
                'attempted_matches': matches[:3] if matches else [],
                'speaker_name': speaker_name
            }

    def _clean_speaker_name(self, name: str) -> str:
        """
        Czyści nazwę mówcy z niepotrzebnych elementów

        Args:
            name: surowa nazwa mówcy

        Returns:
            Oczyszczona nazwa
        """
        # Usuń typowe prefiksy i sufiksy
        prefixes_to_remove = [
            'poseł', 'posłanka', 'pani poseł', 'pan poseł',
            'minister', 'pani minister', 'pan minister',
            'marszałek', 'pani marszałek', 'pan marszałek',
            'wicemarszałek', 'przewodniczący', 'przewodnicząca',
            'sekretarz', 'dr', 'prof.'
        ]

        cleaned = name.strip()

        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                break

        # Usuń dodatkowe białe znaki
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned

    def enrich_statements(self, statements: List[Dict], term: int) -> List[Dict]:
        """
        Wzbogaca wypowiedzi o dodatkowe metadane z danych posłów i klubów

        Args:
            statements: lista wypowiedzi (już dopasowanych do posłów)
            term: numer kadencji

        Returns:
            Lista wzbogaconych wypowiedzi
        """
        if term not in self.clubs_cache:
            self.load_clubs_data(term)

        enriched_statements = []

        for statement in statements:
            enriched_statement = statement.copy()
            mp_match = statement.get('mp_match', {})

            if mp_match.get('matched'):
                mp_data = mp_match.get('mp_data', {})

                # Dodaj wzbogacone informacje o pośle
                enriched_statement['enriched_speaker'] = {
                    'mp_id': mp_match.get('mp_id'),
                    'full_name': f"{mp_data.get('firstName', '')} {mp_data.get('lastName', '')}".strip(),
                    'first_name': mp_data.get('firstName', ''),
                    'last_name': mp_data.get('lastName', ''),
                    'club': mp_data.get('club', ''),
                    'club_id': mp_data.get('clubId'),
                    'voivodeship': mp_data.get('voivodeship', ''),
                    'district_name': mp_data.get('districtName', ''),
                    'district_num': mp_data.get('districtNum'),
                    'email': mp_data.get('email', ''),
                    'number_of_votes': mp_data.get('numberOfVotes'),
                    'is_mp': True,
                    'match_quality': mp_match.get('match_score', 0),
                    'match_type': mp_match.get('match_type', '')
                }

                # Dodaj informacje o klubie jeśli dostępne
                club_id = mp_data.get('clubId')
                if club_id and term in self.clubs_cache and club_id in self.clubs_cache[term]:
                    club_data = self.clubs_cache[term][club_id]
                    enriched_statement['enriched_speaker']['club_details'] = {
                        'id': club_id,
                        'name': club_data.get('name', ''),
                        'abbreviation': club_data.get('abbreviation', ''),
                        'phone': club_data.get('phone', ''),
                        'fax': club_data.get('fax', ''),
                        'email': club_data.get('email', '')
                    }

                self.processing_stats['enriched_statements'] += 1
            else:
                # Dla niedopasowanych mówców - zachowaj podstawowe informacje
                enriched_statement['enriched_speaker'] = {
                    'mp_id': None,
                    'full_name': statement.get('speaker', {}).get('name', ''),
                    'club': statement.get('speaker', {}).get('club', ''),
                    'function': statement.get('speaker', {}).get('function', ''),
                    'is_mp': False,
                    'match_quality': 0,
                    'unmatch_reason': mp_match.get('reason', 'nieznany')
                }

            enriched_statements.append(enriched_statement)
            self.processing_stats['processed_statements'] += 1

        return enriched_statements

    def validate_transcript_data(self, transcript_data: Dict) -> Dict:
        """
        Sprawdza kompletność i poprawność danych transkryptu

        Args:
            transcript_data: dane transkryptu do walidacji

        Returns:
            Słownik z wynikami walidacji
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_statements': 0,
                'matched_mps': 0,
                'unmatched_speakers': 0,
                'empty_content': 0,
                'missing_timing': 0,
                'duplicate_statement_nums': []
            }
        }

        try:
            # Sprawdź strukturę podstawową
            if 'metadata' not in transcript_data:
                validation_result['errors'].append("Brak sekcji 'metadata'")
                validation_result['is_valid'] = False

            if 'statements' not in transcript_data:
                validation_result['errors'].append("Brak sekcji 'statements'")
                validation_result['is_valid'] = False
                return validation_result

            statements = transcript_data['statements']
            validation_result['stats']['total_statements'] = len(statements)

            # Sprawdź duplikaty numerów wypowiedzi
            statement_nums = [stmt.get('num') for stmt in statements if stmt.get('num') is not None]
            duplicates = [num for num in set(statement_nums) if statement_nums.count(num) > 1]
            if duplicates:
                validation_result['stats']['duplicate_statement_nums'] = duplicates
                validation_result['warnings'].append(f"Znaleziono duplikaty numerów wypowiedzi: {duplicates}")

            # Sprawdź każdą wypowiedź
            for i, statement in enumerate(statements):
                statement_errors = []

                # Sprawdź obecność kluczowych pól
                required_fields = ['num', 'speaker', 'content']
                for field in required_fields:
                    if field not in statement:
                        statement_errors.append(f"Brak pola '{field}' w wypowiedzi {i}")

                # Sprawdź dane mówcy
                if 'enriched_speaker' in statement:
                    if statement['enriched_speaker'].get('is_mp'):
                        validation_result['stats']['matched_mps'] += 1
                    else:
                        validation_result['stats']['unmatched_speakers'] += 1

                # Sprawdź treść wypowiedzi
                content = statement.get('content', {})
                if not content.get('text', '').strip():
                    validation_result['stats']['empty_content'] += 1
                    statement_errors.append(f"Pusta treść wypowiedzi {statement.get('num', i)}")

                # Sprawdź informacje czasowe
                timing = statement.get('timing', {})
                if not timing.get('start_datetime') or not timing.get('end_datetime'):
                    validation_result['stats']['missing_timing'] += 1
                    statement_errors.append(f"Brak informacji czasowych w wypowiedzi {statement.get('num', i)}")

                if statement_errors:
                    validation_result['errors'].extend(statement_errors)

            # Ocena ogólna
            if validation_result['stats']['empty_content'] > len(statements) * 0.5:
                validation_result['warnings'].append("Ponad 50% wypowiedzi ma pustą treść")

            if validation_result['stats']['unmatched_speakers'] > len(statements) * 0.3:
                validation_result['warnings'].append("Ponad 30% mówców nie zostało dopasowanych do posłów")

            if validation_result['errors']:
                validation_result['is_valid'] = False
                self.processing_stats['validation_errors'] += len(validation_result['errors'])

        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Błąd podczas walidacji: {str(e)}")
            self.processing_stats['validation_errors'] += 1

        return validation_result

    def create_analysis_ready_json(self, transcript_data: Dict, output_path: Path,
                                   include_validation: bool = True) -> Optional[str]:
        """
        Tworzy finalny plik JSON zoptymalizowany do analizy

        Args:
            transcript_data: wzbogacone dane transkryptu
            output_path: ścieżka do zapisu pliku
            include_validation: czy dołączyć wyniki walidacji

        Returns:
            Ścieżka do utworzonego pliku lub None w przypadku błędu
        """
        try:
            # Przygotuj strukturę danych dla analizy
            analysis_data = {
                'format_version': '1.0',
                'processing_info': {
                    'created_at': datetime.now().isoformat(),
                    'processor_version': '1.0',
                    'processing_stats': self.processing_stats.copy()
                },
                'session_metadata': transcript_data.get('metadata', {}),
                'statements': [],
                'summary': {
                    'total_statements': len(transcript_data.get('statements', [])),
                    'matched_mps': 0,
                    'unique_speakers': set(),
                    'clubs_present': set(),
                    'session_duration_minutes': None,
                    'avg_statement_length': 0
                }
            }

            # Walidacja (jeśli wymagana)
            if include_validation:
                validation_result = self.validate_transcript_data(transcript_data)
                analysis_data['validation'] = validation_result

            # Przetwórz wypowiedzi dla analizy
            total_text_length = 0
            session_start = None
            session_end = None

            for statement in transcript_data.get('statements', []):
                enriched_speaker = statement.get('enriched_speaker', {})

                # Struktura zoptymalizowana dla analizy
                analysis_statement = {
                    'id': statement.get('num'),
                    'speaker': {
                        'name': enriched_speaker.get('full_name', ''),
                        'is_mp': enriched_speaker.get('is_mp', False),
                        'mp_id': enriched_speaker.get('mp_id'),
                        'party': enriched_speaker.get('club', ''),
                        'voivodeship': enriched_speaker.get('voivodeship', ''),
                        'district': enriched_speaker.get('district_name', ''),
                        'function': statement.get('speaker', {}).get('function', ''),
                        'match_quality': enriched_speaker.get('match_quality', 0)
                    },
                    'content': {
                        'text': statement.get('content', {}).get('text', ''),
                        'word_count': len(statement.get('content', {}).get('text', '').split()),
                        'char_count': len(statement.get('content', {}).get('text', ''))
                    },
                    'timing': statement.get('timing', {}),
                    'metadata': {
                        'original_speaker_data': statement.get('speaker', {}),
                        'match_info': statement.get('mp_match', {}) if 'mp_match' in statement else None
                    }
                }

                analysis_data['statements'].append(analysis_statement)

                # Aktualizuj statystyki
                if enriched_speaker.get('is_mp'):
                    analysis_data['summary']['matched_mps'] += 1

                speaker_name = enriched_speaker.get('full_name', '')
                if speaker_name:
                    analysis_data['summary']['unique_speakers'].add(speaker_name)

                club = enriched_speaker.get('club', '')
                if club:
                    analysis_data['summary']['clubs_present'].add(club)

                # Długość tekstu
                text_length = analysis_statement['content']['char_count']
                total_text_length += text_length

                # Czas sesji
                start_time = statement.get('timing', {}).get('start_datetime')
                end_time = statement.get('timing', {}).get('end_datetime')

                if start_time:
                    if not session_start or start_time < session_start:
                        session_start = start_time

                if end_time:
                    if not session_end or end_time > session_end:
                        session_end = end_time

            # Finalizuj statystyki
            analysis_data['summary']['unique_speakers'] = len(analysis_data['summary']['unique_speakers'])
            analysis_data['summary']['clubs_present'] = sorted(list(analysis_data['summary']['clubs_present']))
            analysis_data['summary']['clubs_count'] = len(analysis_data['summary']['clubs_present'])

            if analysis_data['summary']['total_statements'] > 0:
                analysis_data['summary']['avg_statement_length'] = total_text_length // analysis_data['summary'][
                    'total_statements']

            # Oblicz czas trwania sesji
            if session_start and session_end:
                try:
                    start_dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
                    duration_minutes = (end_dt - start_dt).total_seconds() / 60
                    analysis_data['summary']['session_duration_minutes'] = int(duration_minutes)
                except:
                    pass

            # Zapisz plik
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Utworzono plik gotowy do analizy: {output_path}")
            self.processing_stats['created_files'] += 1

            return str(output_path)

        except Exception as e:
            logger.error(f"Błąd tworzenia pliku do analizy: {e}")
            return None

    def process_transcript_file(self, transcript_path: Path, term: int,
                                output_dir: Optional[Path] = None) -> Optional[str]:
        """
        Przetwarza pojedynczy plik transkryptu od początku do końca

        Args:
            transcript_path: ścieżka do pliku transkryptu
            term: numer kadencji
            output_dir: katalog wyjściowy (domyślnie obok oryginalnego)

        Returns:
            Ścieżka do przetworzonego pliku lub None
        """
        try:
            # Załaduj dane transkryptu
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)

            logger.info(f"Przetwarzanie transkryptu: {transcript_path}")

            # Załaduj dane posłów jeśli nie są w cache
            if term not in self.mps_cache:
                if not self.load_mps_data(term):
                    logger.error(f"Nie można załadować danych posłów dla kadencji {term}")
                    return None

            # Dopasuj mówców do posłów
            statements = transcript_data.get('statements', [])
            matched_statements = self.match_speakers_with_mps(statements, term)

            # Wzbogać wypowiedzi
            enriched_statements = self.enrich_statements(matched_statements, term)

            # Aktualizuj dane transkryptu
            transcript_data['statements'] = enriched_statements

            # Określ ścieżkę wyjściową
            if output_dir is None:
                output_dir = transcript_path.parent / "processed"

            output_filename = transcript_path.stem + "_processed.json"
            output_path = output_dir / output_filename

            # Utwórz finalny plik JSON
            result_path = self.create_analysis_ready_json(transcript_data, output_path)

            if result_path:
                logger.info(f"Pomyślnie przetworzono transkrypt: {result_path}")
                logger.info(f"Statystyki: dopasowano {self.processing_stats['matched_speakers']} mówców, "
                            f"nie dopasowano {self.processing_stats['unmatched_speakers']}")

            return result_path

        except Exception as e:
            logger.error(f"Błąd przetwarzania transkryptu {transcript_path}: {e}")
            return None

    def get_processing_stats(self) -> Dict:
        """Zwraca statystyki przetwarzania"""
        return self.processing_stats.copy()

    def reset_stats(self):
        """Resetuje statystyki przetwarzania"""
        for key in self.processing_stats:
            self.processing_stats[key] = 0
