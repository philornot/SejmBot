import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope='module')
def api_client_and_cache():
    # Import inside fixture
    try:
        from SejmBotScraper.api.sejm_client import SejmAPIClient
        from SejmBotScraper.cache.manager import CacheInterface
    except Exception:
        pytest.skip('SejmBotScraper components not importable')

    cache = CacheInterface()
    client = SejmAPIClient(cache)

    # Run basic connection test
    try:
        res = client.test_connection()
    except Exception:
        pytest.skip('API connection test failed or network unavailable')

    return client, cache


def test_transcripts_and_fetching(api_client_and_cache):
    api_client, cache = api_client_and_cache

    term = 10
    proceedings = api_client.get_proceedings(term)
    assert isinstance(proceedings, list)
    assert proceedings

    # pick a proceeding with dates
    test_proc = None
    test_date = None
    from datetime import datetime, date as _date

    today = _date.today()
    for p in proceedings:
        if p.get('dates'):
            for d in p['dates']:
                try:
                    if datetime.strptime(d, '%Y-%m-%d').date() < today:
                        test_proc = p
                        test_date = d
                        break
                except Exception:
                    continue
        if test_proc:
            break

    assert test_proc and test_date

    proc_id = test_proc.get('number') or test_proc.get('id')
    statements_data = api_client.get_transcripts_list(term, proc_id, test_date)
    assert isinstance(statements_data, dict)
    assert 'statements' in statements_data and statements_data['statements']

    # attempt to fetch up to 5 statements' full text
    count = 0
    for stmt in statements_data['statements'][:5]:
        num = stmt.get('num')
        if not num:
            continue
        html = api_client.get_statement_html(term, proc_id, test_date, num)
        # html may be None in some cases; accept both
        assert html is None or isinstance(html, str)

        full = api_client.get_statement_full_text(term, proc_id, test_date, num)
        assert full is None or isinstance(full, str)
        count += 1

    assert count > 0


def test_specific_statement_methods(api_client_and_cache):
    api_client, cache = api_client_and_cache
    # This test uses default parameters and checks that helper methods exist
    assert hasattr(api_client, 'get_transcripts_list')
    assert hasattr(api_client, 'get_statement_html')
    assert hasattr(api_client, 'get_statement_full_text')
