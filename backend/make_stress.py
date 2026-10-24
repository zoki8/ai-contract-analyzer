"""Generate long synthetic contracts that stress the chunking pipeline.

    python make_stress.py

Writes to ../eval/stress/:
    contracts/<name>.pdf and <name>.txt   the contract
    expected/<name>.json                  must_find / must_not_flag (same format as eval/expected)

Every risky clause is planted on purpose, so we know exactly where it is:
    stress_long      ~150k chars, 70 short sections. Clauses spread from the first to the very last sentence.
    stress_giant     one Article with no sub-headings (~45k chars), so chunking falls back to the
                     character split. Clauses are placed ACROSS the cut lines and INSIDE the overlap.
    stress_sr        ~70k chars, Serbian, "Član" headings.

The contracts are fictional. Party names are invented.
"""
import json
import random
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from pdf_utils import extract_text

OUT = Path(__file__).parent.parent / "eval" / "stress"
MAX_CHARS, OVERLAP = 6000, 500  # must match the defaults of pdf_utils.chunk()

# ---------------------------------------------------------------- planted clauses

RISKY_EN = {
    "late_fee": ("penalty",
        "If the Customer fails to pay any invoice when due, the Customer shall pay a late fee of "
        "two and a half percent (2.5%) of the outstanding amount for each week of delay, without any cap."),
    "withdrawal_fee": ("penalty",
        "Should the Customer withdraw any Work Order after signature, the Customer shall pay "
        "liquidated damages equal to forty percent (40%) of the total value of that Work Order."),
    "pay_7_days": ("payment_terms",
        "All invoices are payable in full within seven (7) days of the invoice date, and the Customer "
        "may not withhold or set off any amount for any reason, including disputed deliverables."),
    "renew_36": ("auto_renewal",
        "Upon expiry of the Initial Term, this Agreement shall automatically renew for successive periods "
        "of thirty-six (36) months unless the Customer gives written notice of non-renewal at least one "
        "hundred and eighty (180) days before the end of the then-current term."),
    "supplier_quits": ("termination",
        "The Supplier may terminate this Agreement or any Work Order at any time, for any reason or no "
        "reason, with immediate effect by written notice to the Customer, and no refund of prepaid fees shall be due."),
    "cap_1_month": ("liability",
        "In no event shall the Supplier's total aggregate liability under this Agreement exceed the fees "
        "paid by the Customer in the one (1) month preceding the event giving rise to the claim."),
    "gross_negligence": ("liability",
        "The Supplier shall not be liable for any loss of data, loss of profits or business interruption, "
        "even where such loss results from the Supplier's gross negligence or wilful misconduct."),
}

# Longer than OVERLAP on purpose: when it sits across a cut line it cannot be whole in any chunk.
LONG_LIABILITY = ("liability",
    "Notwithstanding any other provision of this Agreement, and to the maximum extent permitted by "
    "applicable law, the Supplier, its affiliates, subcontractors and licensors shall not be liable to "
    "the Customer or to any third party for any indirect, incidental, special, exemplary, punitive or "
    "consequential damages of any kind, including without limitation damages for loss of revenue, loss "
    "of anticipated savings, loss of goodwill, loss or corruption of data, cost of procurement of "
    "substitute services or business interruption, whether arising in contract, tort, strict liability "
    "or otherwise, and regardless of whether the Supplier was advised of the possibility of such "
    "damages, and the Customer hereby irrevocably waives any right to claim such damages.")

SAFE_EN = {
    "governing_law": "This Agreement shall be governed by and construed in accordance with the laws of "
                     "the Republic of Serbia, without regard to its conflict of laws rules.",
    "pay_30_days": "Each undisputed invoice shall be paid within thirty (30) days of receipt by bank "
                   "transfer to the account stated on the invoice.",
}

RISKY_SR = {
    "kazna_sr": ("penalty",
        "Ukoliko Naručilac kasni sa plaćanjem, dužan je da Pružaocu plati ugovornu kaznu u iznosu od "
        "jedan odsto (1%) od dugovanog iznosa za svaki dan kašnjenja, bez gornje granice."),
    "obnova_sr": ("auto_renewal",
        "Ovaj ugovor se automatski produžava za naredni period od dve (2) godine, ukoliko Naručilac "
        "najkasnije šest (6) meseci pre isteka ne dostavi pisano obaveštenje da ne želi produženje."),
    "raskid_sr": ("termination",
        "Pružalac može jednostrano raskinuti ovaj ugovor u bilo kom trenutku, bez otkaznog roka i bez "
        "navođenja razloga, pri čemu Naručilac nema pravo na povraćaj unapred plaćenih iznosa."),
    "odgovornost_sr": ("liability",
        "Ukupna odgovornost Pružaoca po ovom ugovoru ni u kom slučaju ne može preći iznos naknade "
        "koju je Naručilac platio u poslednjih trideset (30) dana pre nastanka štete."),
}

SAFE_SR = {
    "pravo_sr": "Na ovaj ugovor primenjuje se pravo Republike Srbije.",
}

# ---------------------------------------------------------------- filler text

TOPICS_EN = [
    "Definitions", "Scope of Services", "Work Orders", "Personnel", "Service Levels", "Reporting",
    "Acceptance", "Change Requests", "Confidentiality", "Data Protection", "Intellectual Property",
    "Warranties", "Insurance", "Audit", "Subcontracting", "Compliance with Laws", "Notices",
    "Assignment", "Force Majeure", "Dispute Resolution", "Records", "Security", "Cooperation",
    "Project Governance", "Escalation", "Documentation", "Training", "Transition", "Publicity",
    "Non-Solicitation", "Anti-Bribery", "Export Control", "Severability", "Entire Agreement",
]

SUBJ = ["Each Party", "The Supplier", "The Customer", "The Project Board", "Either Party",
        "The Supplier's project manager", "The Customer's representative"]
VERB = ["shall maintain", "shall provide", "shall keep", "shall document", "shall review",
        "shall make available", "shall promptly notify the other Party of", "shall cooperate in good faith regarding"]
OBJ = ["accurate records of the Services performed", "a written status report every two weeks",
       "the list of key personnel assigned to the project", "all reasonable information requested in writing",
       "the agreed security and access procedures", "the minutes of each steering committee meeting",
       "any material change in the delivery plan", "the documentation reasonably needed to use the Deliverables",
       "an up-to-date register of open risks and issues", "the results of each acceptance test"]
TAIL = ["in accordance with the Statement of Work", "within a reasonable time",
        "as agreed in the applicable Work Order", "during the Term and for one year thereafter",
        "using the template in Annex B", "at its own cost", "without undue delay",
        "subject to the confidentiality obligations of this Agreement"]

SUBJ_SR = ["Svaka ugovorna strana", "Pružalac", "Naručilac", "Projektni odbor", "Rukovodilac projekta"]
VERB_SR = ["je dužan da vodi", "je dužan da dostavi", "će redovno ažurirati", "će pregledati",
           "će bez odlaganja obavestiti drugu stranu o", "će učiniti dostupnim"]
OBJ_SR = ["evidenciju o pruženim uslugama", "pisani izveštaj o statusu na svake dve nedelje",
          "spisak ključnog osoblja na projektu", "zapisnike sa sastanaka upravnog odbora",
          "registar otvorenih rizika", "rezultate testiranja prijema", "dokumentaciju potrebnu za korišćenje isporuka"]
TAIL_SR = ["u skladu sa Specifikacijom usluga", "u razumnom roku", "o sopstvenom trošku",
           "tokom trajanja ugovora i godinu dana nakon toga", "prema obrascu iz Priloga B"]

TOPICS_SR = ["Predmet ugovora", "Obim usluga", "Osoblje", "Nivo usluga", "Izveštavanje", "Prijem",
             "Izmene", "Poverljivost", "Zaštita podataka", "Intelektualna svojina", "Garancije",
             "Osiguranje", "Kontrola", "Podugovarači", "Obaveštenja", "Ustupanje", "Viša sila",
             "Rešavanje sporova", "Bezbednost", "Saradnja", "Dokumentacija", "Obuka", "Završne odredbe"]


def sentence(rng, lang="en"):
    if lang == "sr":
        return f"{rng.choice(SUBJ_SR)} {rng.choice(VERB_SR)} {rng.choice(OBJ_SR)} {rng.choice(TAIL_SR)}."
    return f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(TAIL)}."


def paragraph(rng, n_sent, lang="en"):
    return " ".join(sentence(rng, lang) for _ in range(n_sent))


def filler(rng, n_chars, lang="en"):
    """Plain filler of roughly n_chars characters (ends on a sentence)."""
    out = ""
    while len(out) < n_chars:
        out += (" " if out else "") + sentence(rng, lang)
    return out

# ---------------------------------------------------------------- writing


def write_pdf(path: Path, title: str, blocks: list[tuple[str, str]]):
    """blocks: list of ("h" | "p", text)."""
    styles = getSampleStyleSheet()
    # built-in PDF fonts have no č, ć, đ; a Unicode font keeps Serbian text extractable
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    for st in ("BodyText", "Heading3"):
        styles[st].fontName = "DejaVu"
    styles["Title"].fontName = "DejaVu-Bold"
    flow = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for kind, text in blocks:
        style = styles["Heading3"] if kind == "h" else styles["BodyText"]
        flow.append(Paragraph(text.replace("&", "&amp;"), style))
    SimpleDocTemplate(str(path), pagesize=A4).build(flow)


def save(name, title, blocks, must_find, must_not_flag, note):
    (OUT / "contracts").mkdir(parents=True, exist_ok=True)
    (OUT / "expected").mkdir(parents=True, exist_ok=True)
    text = title + "\n" + "\n".join(t for _, t in blocks)
    (OUT / "contracts" / f"{name}.txt").write_text(text, encoding="utf-8")
    write_pdf(OUT / "contracts" / f"{name}.pdf", title, blocks)
    expected = {
        "source": f"synthetic stress test ({note})",
        "must_find": [{"category": c, "quote_contains": [q], "id": i} for i, (c, q) in must_find.items()],
        "must_not_flag": [{"quote_contains": [q], "id": i} for i, q in must_not_flag.items()],
    }
    (OUT / "expected" / f"{name}.json").write_text(
        json.dumps(expected, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(text)


# ---------------------------------------------------------------- 1. long contract

def make_long():
    rng = random.Random(1)
    n_sections = 70
    plant = {3: "late_fee", 12: "pay_7_days", 27: "withdrawal_fee", 35: "renew_36",
             50: "supplier_quits", 68: "cap_1_month", 70: "gross_negligence"}
    safe = {20: "pay_30_days", 66: "governing_law"}
    blocks = [("p", "This Master Services Agreement is entered into between Brightfield Logistics Ltd. "
                    "(the \"Customer\") and Northwind Analytics d.o.o. (the \"Supplier\").")]
    for n in range(1, n_sections + 1):
        topic = TOPICS_EN[(n - 1) % len(TOPICS_EN)]
        blocks.append(("h", f"Section {n}. {topic}"))
        paras = [paragraph(rng, rng.randint(5, 9)) for _ in range(rng.randint(3, 5))]
        if n in plant:
            pos = len(paras) if n == n_sections else rng.randint(0, len(paras))  # last section: very end
            paras.insert(pos, RISKY_EN[plant[n]][1])
        if n in safe:
            paras.insert(rng.randint(0, len(paras)), SAFE_EN[safe[n]])
        blocks += [("p", p) for p in paras]
    return save("stress_long", "MASTER SERVICES AGREEMENT", blocks,
                {k: RISKY_EN[k] for k in plant.values()}, {k: SAFE_EN[k] for k in safe.values()},
                "70 sections, clauses from the first section to the last sentence")

# ---------------------------------------------------------------- 2. one giant section

def cut_lines(section_len):
    """Start offsets of the character-split pieces of one section (mirrors _split_chars)."""
    starts, s = [], 0
    while s < section_len:
        starts.append(s)
        if s + MAX_CHARS >= section_len:
            break
        s += MAX_CHARS - OVERLAP
    return starts


def make_giant():
    """One Article, no sub-headings. Positions are relative to the start of the Article text.
    pieces start at 0, 5500, 11000, 16500, 22000, ...  and end 6000 chars later, so:
      - a cut line is at 6000, 11500, 17000, 22500, ...
      - the overlap zones are [5500,6000), [11000,11500), [16500,17000), [22000,22500), ...
    """
    rng = random.Random(2)
    short_across = RISKY_EN["late_fee"]          # ~200 chars across cut 6000 -> whole in piece 2
    long_across = LONG_LIABILITY                 # ~800 chars covering overlap [11000,11500) -> whole in NO piece
    in_overlap = RISKY_EN["renew_36"]            # ~320 chars inside overlap [16500,17000) -> in 2 pieces
    in_overlap2 = RISKY_EN["supplier_quits"]     # inside overlap [22000,22500)
    plain = RISKY_EN["cap_1_month"]              # safely in the middle of a piece

    heading = "Article 1. General Terms and Conditions "
    plan = [  # (target start offset in the article, text)
        (6000 - len(short_across[1]) // 2, short_across[1]),
        # centred on the overlap [11000,11500): starts before piece 3, ends after piece 2
        (11250 - len(long_across[1]) // 2, long_across[1]),
        (16500 + 80, in_overlap[1]),
        (22000 + 60, in_overlap2[1]),
        (30000, plain[1]),
        (33000, SAFE_EN["governing_law"]),
    ]
    total_len = 45000

    # Build the article as one string so offsets are exact in the .txt version.
    body = heading
    for target, clause in plan:
        while True:  # whole sentences while they fit
            s = sentence(rng) + " "
            if len(body) + len(s) > target:
                break
            body += s
        rest = target - len(body)
        if rest > 1:  # one shortened sentence lands the clause exactly on target
            body += s[: rest - 2].rstrip().ljust(rest - 2, "x") + ". "
        body += clause + " "
    body += filler(rng, total_len - len(body))

    preamble = ("This Services Agreement is entered into between Brightfield Logistics Ltd. "
                "(the \"Customer\") and Northwind Analytics d.o.o. (the \"Supplier\").")
    blocks = [("p", preamble), ("p", body)]
    must = {"late_fee": short_across, "long_liability": long_across, "renew_36": in_overlap,
            "supplier_quits": in_overlap2, "cap_1_month": plain}
    return save("stress_giant", "SERVICES AGREEMENT", blocks, must, {"governing_law": SAFE_EN["governing_law"]},
                "one 45k-char Article; clauses across cut lines and inside overlaps")

# ---------------------------------------------------------------- 3. Serbian

def make_sr():
    rng = random.Random(3)
    n = 40
    plant = {2: "kazna_sr", 15: "obnova_sr", 29: "raskid_sr", 40: "odgovornost_sr"}
    blocks = [("p", "Ugovor o pružanju usluga zaključen između Brightfield Logistics Ltd. (Naručilac) "
                    "i Northwind Analytics d.o.o. (Pružalac).")]
    for i in range(1, n + 1):
        blocks.append(("h", f"Član {i}. {TOPICS_SR[(i - 1) % len(TOPICS_SR)]}"))
        paras = [paragraph(rng, rng.randint(6, 10), "sr") for _ in range(rng.randint(3, 5))]
        if i in plant:
            paras.insert(len(paras) if i == n else rng.randint(0, len(paras)), RISKY_SR[plant[i]][1])
        if i == 38:
            paras.append(SAFE_SR["pravo_sr"])
        blocks += [("p", p) for p in paras]
    return save("stress_sr", "UGOVOR O PRUŽANJU USLUGA", blocks,
                {k: RISKY_SR[k] for k in plant.values()}, SAFE_SR, "Serbian, 40 'Član' sections")


if __name__ == "__main__":
    for make in (make_long, make_giant, make_sr):
        print(make.__name__, make(), "chars")
    for pdf in sorted((OUT / "contracts").glob("*.pdf")):
        print(pdf.name, len(extract_text(pdf.read_bytes())), "chars after PDF extraction")
