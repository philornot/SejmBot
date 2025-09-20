from SejmBotScraper.api.client import SejmAPIInterface

api = SejmAPIInterface()
proceedings = api.get_proceedings(10)

if proceedings and len(proceedings) > 0:
    print("Pierwsze posiedzenie:")
    print("Klucze:", proceedings[0].keys())
    for key, value in proceedings[0].items():
        if key != 'agenda':  # agenda jest bardzo długie
            print(f"{key}: {value}")
else:
    print("Brak posiedzeń")