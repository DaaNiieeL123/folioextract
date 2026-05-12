# Conversion Quality Examples

## DOCX (high-fidelity strategy)

Current implementation keeps `pdf2docx` as primary engine because it remains the most practical open-source option for preserving layout, tables, and embedded images in editable DOCX output.

Improvements applied:

- Source PDF page geometry is propagated into DOCX sections.
- DOCX integrity validation prevents empty/corrupt outputs.

### Alternative evaluation

- `Aspose.PDF` / `Adobe` SDKs can improve fidelity in some documents, but introduce commercial licensing and heavier integration.
- Given project constraints (no external complex tooling), `pdf2docx` + geometry/integrity post-check is the most balanced option.

## Markdown Example

Input-like content in PDF:

- Numbered sections
- Bulleted lists
- Table-like rows

Output (improved):

```md
## 1 Introduccion

## 1.1 Objetivos

- Alcance funcional
- Requisitos de calidad

| Columna A | Columna B |
| --- | --- |
| valor 1 | valor 2 |
```

## TXT Example

Raw extraction artifact:

```text
Docu-
mento   con   ruido
Parrafo
continuado en
lineas cortas
```

Output (normalized):

```text
Documento con ruido
Parrafo continuado en lineas cortas
```
