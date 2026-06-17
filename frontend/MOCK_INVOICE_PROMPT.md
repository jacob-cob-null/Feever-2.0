# Mock Philippine Hospital Invoice Generator — Prompt for Claude

Copy everything below the line and paste it into Claude (browser).

---

You are a document designer generating realistic Philippine hospital billing invoices as images for demonstration purposes. Generate a STATEMENT OF ACCOUNT image that looks like a real scanned hospital invoice — complete with layout imperfections, slightly misaligned text, and the visual characteristics of a document that has been photographed or scanned.

## Output Format

Generate the invoice as a single HTML page wrapped in an `<artifact>` with the type `text/html`. The HTML should render as a realistic-looking hospital invoice that can be screenshotted. Use inline CSS. The page should be approximately 8.5" x 13" (legal size, standard in Philippine hospitals). Use a white background with subtle scan artifacts (very faint gray noise/spots, slight rotation of 0.3-0.5 degrees to simulate a scan).

## Hospital — Pick ONE at Random

Use one of these real Philippine hospitals (pick randomly each time):

1. **Dr. Andres M. Luciano District Hospital** — Brgy. San Jose, Bongabon, Nueva Ecija
2. **Mexico Community Hospital** — San Carlos, Mexico, Pampanga
3. **Diosdado P. Macapagal Memorial Hospital** — Brgy. Lourdes Sur, Angeles City, Pampanga
4. **Ospital ng Angeles** — Mac Arthur Highway, Angeles City, Pampanga

## Document Layout (Top to Bottom)

### Header
- Hospital name in bold, large font (16-18pt), centered
- Hospital address below in smaller font (9-10pt)
- "STATEMENT OF ACCOUNT" as the document title, centered, underlined or bold, 14pt
- Optional: TIN number (format: `XXX-XXX-XXX-XXX`), hospital phone number

### Patient Information Block (two-column layout)
Left column:
- **Patient Name:** Generate a realistic Filipino full name (e.g., "DELA CRUZ, MARIA SANTOS", "REYES, JUAN CARLOS P.", "VILLANUEVA, ANA MARIE D."). Use LASTNAME, FIRSTNAME MIDDLE format. Use common Filipino surnames: Dela Cruz, Santos, Reyes, Garcia, Ramos, Cruz, Bautista, Aquino, Mendoza, Torres, Gonzales, Villanueva, Castillo, Fernandez, Rivera
- **Age/Sex:** (e.g., "45/F", "32/M", "67/F")
- **Address:** Use a real-sounding Philippine barangay address (e.g., "Brgy. San Nicolas, Mexico, Pampanga")
- **Attending Physician:** "Dr. [Filipino name]"

Right column:
- **Date Admitted:** Use format "MM/DD/YYYY" or "MONTH DD, YYYY" — pick dates within 2025-2026
- **Time Admitted:** (e.g., "10:30 AM")
- **Date Discharged:** 1-7 days after admission
- **Time Discharged:** (e.g., "2:00 PM")
- **Room/Ward:** (e.g., "Ward B-3", "Room 201", "Pay Ward", "ICU")
- **Account No.:** 6-digit number

### PhilHealth Information (optional — include in ~60% of invoices)
- **PhilHealth No.:** 12-digit number with dashes (e.g., "01-234567891-2")
- **Member Type:** "Member" / "Dependent"
- **Employer:** Company name or "Self-Employed" / "OFW" / "Senior Citizen"

### Itemized Charges Table

This is the MAIN TABLE. Use this exact column structure:

| PARTICULARS | QTY | UNIT PRICE | AMOUNT |
|---|---|---|---|

Generate 5-20 line items from the following categories. Mix items from multiple categories. Prices MUST be in Philippine Peso (no peso sign in the table, just numbers with 2 decimal places).

**Laboratory Services** (pick 2-5):
- COMPLETE BLOOD COUNT W/ PLATELET CT. — 250.00
- HEMOGLOBIN — 100.00
- URINALYSIS — 100.00
- BLOOD TYPING (ABO-Rh) — 150.00
- SERUM CREATININE — 200.00
- BLOOD UREA NITROGEN — 200.00
- FASTING BLOOD SUGAR — 150.00
- LIPID PROFILE — 500.00
- SGPT/ALT — 200.00
- SGOT/AST — 200.00
- HBA1C — 600.00
- TROPONIN I — 800.00
- PROTHROMBIN TIME — 350.00
- THYROID FUNCTION TEST (FT3, FT4, TSH) — 1,500.00
- HEPATITIS B SCREENING — 350.00
- HIV SCREENING — 250.00
- SERUM ELECTROLYTES (Na, K, Cl) — 600.00
- BLOOD CULTURE AND SENSITIVITY — 1,200.00
- SPUTUM AFB STAIN — 200.00

**Imaging/Radiology** (pick 1-3):
- CHEST PA — 350.00
- CHEST PA/L — 480.00
- PELVIS AP — 100.00
- PELVIS CROSS-TABLE (RIGHT) — 100.00
- PLAIN CRANIAL — 3,980.00
- WHOLE ABDOMINAL ULTRASOUND — 1,500.00
- CRANIAL CT SCAN PLAIN — 5,500.00
- CRANIAL CT SCAN WITH CONTRAST — 8,000.00
- WHOLE ABDOMEN CT SCAN WITH CONTRAST — 15,710.00
- CHEST CT SCAN — 8,500.00
- 2D ECHOCARDIOGRAPHY — 3,500.00
- ECG/EKG (12-LEAD) — 250.00
- PELVIC ULTRASOUND — 1,200.00

**Drugs and Medicines** (pick 3-8):
- AMOXICILLIN 500MG CAP — 3.50 (qty 21-30)
- METFORMIN 500MG TAB — 4.00 (qty 30-60)
- LOSARTAN 50MG TAB — 5.50 (qty 30)
- AMLODIPINE 5MG TAB — 3.00 (qty 30)
- OMEPRAZOLE 20MG CAP — 8.00 (qty 14-30)
- CEFTRIAXONE 1G INJ — 120.00 (qty 3-7)
- PARACETAMOL 500MG TAB — 1.50 (qty 10-20)
- TRAMADOL 50MG CAP — 12.00 (qty 10)
- CIPROFLOXACIN 500MG TAB — 15.00 (qty 14)
- METRONIDAZOLE 500MG TAB — 4.50 (qty 14)
- SALBUTAMOL NEBULE 2.5MG — 25.00 (qty 6-12)
- INSULIN GLARGINE 100IU/ML — 1,200.00 (qty 1-2)
- ENOXAPARIN 60MG INJ — 850.00 (qty 3-5)
- IV FLUID D5LR 1L — 95.00 (qty 3-8)
- IV FLUID PNSS 1L — 85.00 (qty 2-6)
- MULTIVITAMINS 100 TABS/BOX (DONATION) — 1.64 (qty 1)

**Medical Supplies** (pick 1-4):
- SYRINGE 5CC — 15.00 (qty 5-10)
- IV CANNULA G22 — 45.00 (qty 2-3)
- ALCOHOL SWAB — 2.00 (qty 10-20)
- SURGICAL GLOVES (PAIR) — 25.00 (qty 4-10)
- CATHETER FOLEY #16 — 180.00 (qty 1)
- URINE BAG — 85.00 (qty 1-2)
- OXYGEN MASK — 120.00 (qty 1)
- NEBULIZER KIT — 150.00 (qty 1)
- SUTURE MATERIAL (SILK 3-0) — 95.00 (qty 1-3)
- SURGICAL TAPE — 35.00 (qty 2)
- DRESSING SET — 75.00 (qty 2-5)

**Room and Board** (pick 1):
- WARD — 300.00 to 500.00 per day (multiply by days of stay)
- SEMI-PRIVATE ROOM — 800.00 to 1,200.00 per day
- PRIVATE ROOM — 1,500.00 to 2,500.00 per day
- ICU — 3,000.00 to 5,000.00 per day

**Other Charges** (pick 0-3):
- NURSING CARE — 200.00 to 500.00 per day
- OPERATING ROOM FEE — 3,000.00 to 8,000.00
- RECOVERY ROOM — 500.00 to 1,500.00
- OXYGEN (per hour) — 50.00 (qty 12-48)
- AMBULANCE — 1,500.00 to 3,000.00
- PROFESSIONAL FEE (Surgeon) — 5,000.00 to 15,000.00
- PROFESSIONAL FEE (Anesthesiologist) — 3,000.00 to 8,000.00
- PROFESSIONAL FEE (Attending Physician) — 2,500.00 to 5,000.00

### Summary Section (below the table)

```
                              TOTAL HOSPITAL CHARGES:    ₱XX,XXX.XX
                              PROFESSIONAL FEES:         ₱X,XXX.XX
                              ────────────────────────────────────
                              GROSS TOTAL:               ₱XX,XXX.XX
                              LESS: PhilHealth Benefit:  (₱X,XXX.XX)    ← only if PhilHealth info present
                              LESS: Discount:            (₱X,XXX.XX)    ← occasionally, for senior citizen/PWD
                              ────────────────────────────────────
                              TOTAL AMOUNT DUE:          ₱XX,XXX.XX
```

### Footer
- **Prepared by:** "[Name], Billing Clerk"
- **Certified Correct:** "[Name], Administrative Officer"
- Signature lines (horizontal rules with name/title below)
- Date prepared

## Scenario Variants — Pick ONE

For each invoice, randomly pick one of these scenarios to make the data interesting for the Fee-Ver system:

### Scenario A: Clean Bill (30% chance)
- All prices match the reference prices listed above exactly
- Include a PhilHealth number and a valid-looking diagnosis
- Total is reasonable (₱5,000 - ₱25,000)

### Scenario B: Price Inflated (25% chance)
- Pick 1-3 items and inflate their prices by 15-40% above the reference prices listed
- Example: COMPLETE BLOOD COUNT listed as 350.00 instead of 250.00
- Keep other items at reference price
- Total is ₱10,000 - ₱40,000

### Scenario C: High-Value Case (20% chance)
- Include expensive procedures: CT scans, surgery, ICU stay
- Include professional fees for surgeon + anesthesiologist
- Total is ₱40,000 - ₱120,000
- May or may not have price discrepancies

### Scenario D: Medications-Heavy (15% chance)
- 8+ medication line items with various quantities
- Few lab/imaging items
- Include some items that won't be in the hospital database (uncommon drugs)
- Total is ₱8,000 - ₱20,000

### Scenario E: Minimal/Outpatient (10% chance)
- Only 3-5 line items
- No room and board (outpatient)
- Basic labs + 1-2 medications
- Total is ₱1,000 - ₱5,000

## Visual Styling Requirements

Make it look like a REAL scanned document, NOT a clean digital PDF:

1. **Font:** Use a monospace or serif font that looks like it came from a dot-matrix or laser printer. "Courier New" or "Times New Roman" are appropriate. Mix font sizes slightly between sections.

2. **Table:** Use simple borders (single-line). Align numbers to the right. Use consistent decimal alignment. Some cells may have slightly inconsistent spacing.

3. **Imperfections (subtle, not overdone):**
   - Very slight page rotation (0.3-0.5 degrees via CSS transform)
   - Faint gray speckle overlay (CSS radial-gradient noise)
   - Slightly uneven margins (left margin 0.7in, right margin 0.6in)
   - One or two items may have a slightly bolder print (like the printer pressed harder)
   - Bottom of page may be slightly lighter (faded toner effect)

4. **Paper:** Off-white background (#F8F6F0 to #FEFDFB). Legal size proportions (8.5 x 13 inches).

5. **Stamp/mark (optional, ~30% of invoices):** A faint "PAID" stamp in red at 30% opacity, rotated 15 degrees, somewhere in the summary section. Or a "COPY" watermark diagonally across the page at 5% opacity.

## Important Rules

- All amounts must be internally consistent (qty × unit price = amount, all amounts sum to total)
- Use UPPERCASE for patient names and most hospital service descriptions
- Dates should be between January 2025 and June 2026
- Currency is Philippine Peso (₱). Use the peso sign only in summary totals, not in the itemized table body
- Generate DIFFERENT invoices each time — vary the hospital, patient, items, scenario, and layout details
- The invoice should be visually complete enough to screenshot and use as a test image for OCR
- DO NOT include any watermark or text saying "mock", "sample", "demo", or "for testing"
- Make it look indistinguishable from a real hospital invoice photograph

Generate one invoice now.
