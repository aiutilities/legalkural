from publishing.article_assembly import SourceDocument,assemble_article

def test_article_without_document():
    html="<p>Hello</p>"
    assert assemble_article(html,None)==html

def test_article_with_document():
    doc=SourceDocument(
        title="Judgment",
        pdf_url="https://example.com/j.pdf",
        qr_image_url="https://example.com/j.png",
    )
    html=assemble_article("<p>Hello</p>",doc)
    assert "Download PDF" in html
    assert "QR Code" in html
    assert "Judgment" in html
