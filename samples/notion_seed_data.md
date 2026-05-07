# Datos de prueba para Notion

Carga estos registros manualmente en tus bases de Notion para reproducir los
escenarios del archivo `samples/authorize.http`.

## Medical Reports DB

| report_id | patient_id | patient_name | diagnosis | procedure_code | procedure_name | requested_date | attending_physician | clinical_notes | attachments |
|---|---|---|---|---|---|---|---|---|---|
| RPT-001 | PAT-123 | Ana Pérez | Apendicitis aguda | APE001 | Apendicectomía laparoscópica | 2026-05-10 | Dr. Ramírez | Dolor abdominal 24h, leucocitosis. | (sube PDF) |
| RPT-002 | PAT-456 | Luis Gómez | Hernia inguinal | HER010 | Herniorrafia inguinal | 2026-05-12 | Dra. Soto | (vacío) | (vacío) |
| RPT-003 | PAT-789 | Marta Díaz | Cataratas | OFT020 | Facoemulsificación | 2026-05-15 | Dr. Vega | Visión borrosa progresiva 6m. | (sube PDF) |
| RPT-004 | PAT-321 | Pedro Ruiz | Cirugía estética nariz | EST050 | Rinoplastia estética | 2026-05-20 | Dr. Salas | Procedimiento electivo. | (sube PDF) |

## Policies DB

| policy_id | patient_id | plan_name | effective_date | expiration_date | covered_procedures | excluded_procedures | waiting_periods_months | deductible | coverage_percentage | status |
|---|---|---|---|---|---|---|---|---|---|---|
| POL-A1 | PAT-123 | Premium Plus | 2024-01-01 | 2026-12-31 | APE001, COL015, APE002 | EST050 | APE001:6 | 200 | 80 | active |
| POL-B2 | PAT-456 | Estándar | 2025-03-01 | 2027-02-28 | HER010, APE001 | EST050 | HER010:6 | 150 | 70 | active |
| POL-C3 | PAT-789 | Estándar | 2026-01-15 | 2028-01-14 | OFT020, OFT021 | EST050 | OFT020:12 | 100 | 75 | active |
| POL-D4 | PAT-321 | Premium | 2023-01-01 | 2027-12-31 | APE001, HER010 | EST050, EST051 | (vacío) | 200 | 80 | active |

### Notas de los escenarios

- **RPT-001 / PAT-123** → debe salir `pre_approved`. Procedimiento cubierto, póliza
  vigente desde 2024 (carencia de 6 meses cumplida con creces), informe completo.
- **RPT-002 / PAT-456** → debe salir `missing_documents`. El informe no tiene
  notas clínicas ni adjuntos.
- **RPT-003 / PAT-789** → debe salir `rejected` por carencia incumplida.
  Póliza efectiva 2026-01-15, cirugía pedida 2026-05-15 (≈4 meses), pero
  `OFT020` requiere 12 meses de carencia.
- **RPT-004 / PAT-321** → debe salir `rejected`. `EST050` está en
  `excluded_procedures` de la póliza.
