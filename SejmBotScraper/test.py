from SejmBotScraper.api.client import SejmAPIInterface

# Testuj API krok po kroku
api = SejmAPIInterface()

# Test 1: Czy API w ogóle działa?
print("Test 1: Lista kadencji")
terms = api.get_terms()
print(f"terms = {terms}")

# Test 2: Info o kadencji 10
print("\nTest 2: Info kadencji 10")
term_info = api.get_term_info(10)
print(f"term_info = {term_info}")

# Test 3: Posiedzenia kadencji 10
print("\nTest 3: Posiedzenia kadencji 10")
proceedings = api.get_proceedings(10)
print(f"proceedings = {proceedings}")
if proceedings:
    print(f"Liczba posiedzeń: {len(proceedings)}")