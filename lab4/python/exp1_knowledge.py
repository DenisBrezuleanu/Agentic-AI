from llm import ask, QuotaExhausted

PROBES = [
    "What is today's date?",
    'What is the cheapest flight from Iasi to Rome next Tuesday, and how much does it cost?',
    'Which concerts are on in Rome in the second week of May 2027?',
    'Is the Borghese Gallery in Rome open on Mondays, and how do you get tickets?',
]

if __name__ == '__main__':
    for question in PROBES:
        try:
            print(f'\n{question}\n{ask(question).text.strip()[:600]}')
        except TimeoutError as e:
            print(f'Timeout: {e}')
        except QuotaExhausted as e:
            print(f'Stopped: {e}')
            break
