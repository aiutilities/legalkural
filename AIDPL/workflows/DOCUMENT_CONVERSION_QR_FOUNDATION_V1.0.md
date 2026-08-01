# Document Conversion + QR Foundation v1.0

## Supported Inputs

- PDF
- DOC
- DOCX
- XLS
- XLSX
- CSV

## Processing Flow

```text
Upload
  ↓
Validate extension
  ↓
Preserve original privately
  ↓
Convert public copy to PDF
  ↓
Validate PDF and page count
  ↓
Create stable download URL
  ↓
Generate QR code
  ↓
Create source-document metadata
```

## Important Boundary

Word and spreadsheet conversion uses a local LibreOffice headless engine.

PDF inputs do not require conversion.

## Outputs

```text
documents/<document-id>/original/
documents/<document-id>/public/
documents/<document-id>/qr/
documents/<document-id>/document.json
```

## Not Yet Included

- Virus scanning
- Permanent object storage
- WordPress media upload
- Download endpoint
- Scheduled document release
- Journal QR placement
