import base64
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

class CreatorContractPDF(FPDF):
    def header(self):
        # Professional top header
        self.set_text_color(30, 30, 40)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, "BRAND COLLABORATION AGREEMENT", ln=True, align="C")
        
        # Primary accent line (Trendrop Red #E63946 / rgb(230, 57, 70))
        self.set_draw_color(230, 57, 70)
        self.set_line_width(1)
        self.line(15, 20, 195, 20)
        self.ln(10)

    def footer(self):
        # Footer with page numbers
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Trendrop Creator-Brand Contract Suite", align="C")

def generate_contract_pdf(
    creator_email: str,
    brand_name: str,
    deliverables: str,
    rate_amount: float,
    currency: str = "INR",
    usage_rights: str = "",
    exclusivity_clause: str = "",
    timeline_start: str = "",
    timeline_end: str = "",
    milestones: list = None,
    cover_note_type: str = "english"
) -> str:
    """
    Generates a professional creator contract PDF and returns it as a base64 encoded string.
    """
    pdf = CreatorContractPDF()
    pdf.alias_nb_pages()
    pdf.set_margins(15, 22, 15)
    pdf.add_page()
    
    # --- COVER NOTE SECTION ---
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(40, 40, 50)
    pdf.cell(0, 6, "CAMPAIGN COVER NOTE / BRIEFING STATEMENT", ln=True)
    pdf.ln(2)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(60, 60, 70)
    
    # Date formatting
    today_str = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 5, f"Date: {today_str}", ln=True)
    pdf.cell(0, 5, f"From: {creator_email}", ln=True)
    pdf.cell(0, 5, f"To: {brand_name} Marketing Team", ln=True)
    pdf.ln(4)
    
    # Choose English or Hinglish cover note
    if cover_note_type.lower() == "hinglish":
        cover_note_text = (
            f"Hi {brand_name} Team,\n\n"
            f"Humare upcoming brand collaboration ke terms and deliverables ko formalize karne ke liye "
            f"maine yeh collaboration agreement prepare kiya hai. Humare agreement ke mutabik saare details, "
            f"deliverables scope, payment milestones aur timelines niche contract table mein set kar diye hain.\n\n"
            f"Aap ek baar saare points check kar lijiye. Agar sab sahi hai, toh please complete the signature "
            f"so that hum jaldi se campaign and content creation shuru kar sakein!\n\n"
            f"Looking forward to creating something amazing together!"
        )
    else:
        cover_note_text = (
            f"Dear {brand_name} Team,\n\n"
            f"To formalize our upcoming collaboration for this campaign, I have prepared this brand collaboration agreement "
            f"based on our discussion. All deliverables, timelines, exclusivity details, and payment milestones have been "
            f"outlined in the contract below.\n\n"
            f"Please review the specifications and return a signed copy so that we can schedule the deliverables and kick off the creation process.\n\n"
            f"Best regards,\n{creator_email}"
        )
        
    pdf.multi_cell(0, 5, cover_note_text)
    pdf.ln(10)
    
    # Divider Line
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.2)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)
    
    # --- CONTRACT MAIN TERMS ---
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(30, 30, 40)
    pdf.cell(0, 6, "COLLABORATION TERMS & CONDITIONS", ln=True)
    pdf.ln(4)
    
    # Part 1: Parties
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(40, 5, "1. PARTIES:")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 5, f"Creator ({creator_email}) and Advertiser ({brand_name})", ln=True)
    pdf.ln(2)
    
    # Part 2: Campaign Period
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(40, 5, "2. CAMPAIGN PERIOD:")
    pdf.set_font("helvetica", "", 10)
    start_date = timeline_start.split("T")[0] if timeline_start else "TBD"
    end_date = timeline_end.split("T")[0] if timeline_end else "TBD"
    pdf.cell(0, 5, f"{start_date} to {end_date}", ln=True)
    pdf.ln(2)
    
    # Part 3: Deliverables
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 5, "3. DELIVERABLES SCOPE:", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 5, deliverables)
    pdf.ln(2)
    
    # Part 4: Total Compensation
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(40, 5, f"4. CAMPAIGN RATE:")
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(230, 57, 70) # Red Rate
    pdf.cell(0, 5, f"{currency.upper()} {rate_amount:,.2f}", ln=True)
    pdf.set_text_color(60, 60, 70)
    pdf.ln(2)
    
    # Part 5: Usage Rights
    if usage_rights:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 5, "5. USAGE RIGHTS SCOPE:", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, usage_rights)
        pdf.ln(2)
        
    # Part 6: Exclusivity
    if exclusivity_clause:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 5, "6. EXCLUSIVITY CLAUSE:", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, exclusivity_clause)
        pdf.ln(2)
        
    # Part 7: Payment Milestones Table
    if milestones:
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 5, "7. PAYMENT MILESTONES SCHEDULE:", ln=True)
        pdf.ln(2)
        
        # Table Header
        pdf.set_fill_color(240, 240, 245)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(80, 6, " Milestone Name", border=1, fill=True)
        pdf.cell(50, 6, " Amount", border=1, fill=True)
        pdf.cell(50, 6, " Due Date", border=1, fill=True, ln=True)
        
        # Table Rows
        pdf.set_font("helvetica", "", 9)
        for m in milestones:
            due_str = m.get("due_date", "").split("T")[0] if m.get("due_date") else "Upon Invoice"
            pdf.cell(80, 6, f" {m.get('milestone_name')}", border=1)
            pdf.cell(50, 6, f" {currency.upper()} {float(m.get('amount')):,.2f}", border=1)
            pdf.cell(50, 6, f" {due_str}", border=1, ln=True)
        pdf.ln(4)
        
    # Part 8: Disputes & Governing Law (Indian Context)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 5, "8. DISPUTE RESOLUTION & GOVERNING LAW:", ln=True)
    pdf.set_font("helvetica", "", 10)
    dispute_text = (
        "This Agreement shall be governed by and construed in accordance with the laws of the Republic of India. "
        "Any dispute, controversy, or claim arising out of or relating to this agreement shall first be resolved through "
        "friendly and good faith discussions. If the parties are unable to resolve the dispute, it shall be subject to "
        "the exclusive jurisdiction of the competent courts of India."
    )
    pdf.multi_cell(0, 5, dispute_text)
    pdf.ln(12)
    
    # --- SIGNATURES ---
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(90, 5, "CREATOR SIGNATURE")
    pdf.cell(90, 5, "BRAND REPRESENTATIVE", ln=True)
    pdf.ln(12)
    
    # Signature Lines
    pdf.set_draw_color(100, 100, 100)
    pdf.line(15, pdf.get_y(), 85, pdf.get_y())
    pdf.line(110, pdf.get_y(), 180, pdf.get_y())
    
    pdf.set_font("helvetica", "", 9)
    pdf.cell(90, 5, f"Email: {creator_email}")
    pdf.cell(90, 5, f"For: {brand_name}", ln=True)
    
    # Output to Bytes and Encode to Base64
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    b64_encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    return b64_encoded
