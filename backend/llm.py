import requests
from schemas import ChunkAnalysis
import time
from pydantic import ValidationError


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"
MAX_ATTEMPTS = 3


SYSTEM = (
    "You are a contract review assistant. From the given part of a contract, "
    "extract risky clauses: penalties, payment terms, auto-renewal, termination "
    "conditions, and limitations of liability. For each finding give the EXACT "
    "quote copied from the text, a severity (low, medium, high), and a short "
    "explanation of why it is risky. If there are no risky clauses, return an "
    "empty list. Do not invent clauses that are not in the text. "
    "Categories: "
    "penalty = any fine, fee, interest or percentage charged as punishment "
    "for breaking the contract, INCLUDING late payment penalties. "
    "payment_terms = deadlines and method of payment only; late payment "
    "penalties are NOT payment_terms, they are penalty. "
    "auto_renewal = the contract renews or extends automatically unless "
    "someone cancels it. "
    "termination = conditions under which a party can end the contract, "
    "especially one-sided termination or termination without notice. "
    "liability = limits or exclusions of a party's responsibility for damage "
    "or losses. "
    "other = risky clauses that fit none of the categories above. "
    "Only report clauses that actually appear in the text. Never add placeholder "
    "findings such as 'Not applicable'; if there is no risky clause, return an "
    "empty findings list. "
    "Standard, fair and mutual clauses are NOT risky and must not be reported."
)


class ChunkAnalysisError(Exception):
    """Odeljak nije uspeo da se analizira ni posle svih pokušaja."""


def analyze_chunk(text: str) -> ChunkAnalysis:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": text},
    ]
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        payload = {
            "model": MODEL,
            "stream": False,
            "format": ChunkAnalysis.model_json_schema(),
            "options": {"num_ctx": 8192, "temperature": 0},
            "messages": messages,
        }

        # 1) poziv Ollame (mrežne greške, timeout, loš HTTP status)
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=300)
            r.raise_for_status()
            content = r.json()["message"]["content"]
        except (requests.RequestException, KeyError, ValueError) as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)  # 2s, 4s
            continue

        # 2) validacija odgovora
        try:
            return ChunkAnalysis.model_validate_json(content)
        except ValidationError as e:
            last_error = e
            # model vidi svoj loš odgovor i grešku, pa ima šta da ispravi
            messages = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "Your previous answer was invalid: "
                        f"{str(e)[:500]}\n"
                        "Return corrected JSON that matches the schema."
                    ),
                },
            ]

    raise ChunkAnalysisError(
        f"Failed after {MAX_ATTEMPTS} attempts: {last_error}"
    )
