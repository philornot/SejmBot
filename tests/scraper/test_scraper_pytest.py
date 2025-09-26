import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope='module')
def api_client():
    # lazy import to allow tests to run from repo root
    from SejmBotScraper.api.sejm_client import SejmAPIClient

    client = SejmAPIClient()
    # Basic health check - if client cannot be created tests depending on network may be skipped
    try:
        test_result = client.test_connection()
    except Exception:
        pytest.skip('Sejm API client cannot be initialized or network unavailable')

    return client


def test_api_client_connection(api_client):
    # ensure the client test_connection returns a dict with total_score
    res = api_client.test_connection()
    assert isinstance(res, dict)
    assert 'total_score' in res


def test_content_fetching_sample(api_client):
    # pick a recent term and attempt to fetch proceedings list
    term = 10
    proceedings = api_client.get_proceedings(term)
    assert isinstance(proceedings, list)
    assert proceedings, 'Expected at least one proceeding'

    # find a proceeding with dates
    proc = None
    for p in proceedings:
        if p.get('dates'):
            proc = p
            break

    assert proc, 'No proceeding with dates found'

    proc_id = proc.get('number') or proc.get('id') or proc.get('proceeding_id')
    # choose first date
    date = proc['dates'][0]

    transcripts = api_client.get_transcripts_list(term, proc_id, date)
    assert isinstance(transcripts, dict)
    assert 'statements' in transcripts and transcripts['statements']

    # try fetching first statement content
    stmt = transcripts['statements'][0]
    num = stmt.get('num')
    assert num is not None

    html = api_client.get_statement_html(term, proc_id, date, num)
    assert html is None or isinstance(html, str)

    full = api_client.get_statement_full_text(term, proc_id, date, num)
    assert full is None or isinstance(full, str)


def test_scraper_integration_with_limits(api_client, tmp_path):
    # Import scraper implementation
    from SejmBotScraper.scraping.implementations.scraper import SejmScraper

    config = {
        'max_proceedings': 1,
        'max_dates_per_proceeding': 1,
        'max_statements_per_day': 5,
    }

    scraper = SejmScraper(api_client=api_client, config=config)

    stats = scraper.scrape_term(
        term=10,
        fetch_full_statements=True,
        max_proceedings=1,
        max_dates_per_proceeding=1,
        max_statements_per_day=5,
    )

    assert isinstance(stats, dict)
    # basic expectations: keys exist
    for key in ('proceedings_processed', 'statements_processed'):
        assert key in stats
