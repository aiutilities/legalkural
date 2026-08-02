from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SourceDocument:
    title:str
    pdf_url:str
    qr_image_url:str

def qr_download_block(doc:SourceDocument)->str:
    return (
        "<section class='lk-source-document'>"
        "<h3>Source Document</h3>"
        "<p>Scan the QR code in the journal or use the PDF link.</p>"
        f"<p><strong>{doc.title}</strong></p>"
        f"<img src='{doc.qr_image_url}' alt='QR Code for source document download' />"
        f"<p><a href='{doc.pdf_url}'>Download PDF</a></p>"
        "</section>"
    )

def assemble_article(body_html:str,doc:SourceDocument|None)->str:
    if doc is None:
        return body_html
    return body_html + "\n\n" + qr_download_block(doc)
