## Bullpen CSV Ingestion (API Output)

- Place API-delivered CSVs into `Trackman Bullpens/`.
- Expected env vars (store in a local `.env`, not committed):
  - `PORTABLE_B1_API_KEY`
  - `PORTABLE_B1_IDENTIFIER`
  - `PORTABLE_B1_NAME`
  - `PORTABLE_B1_USERNAME`
  - `PORTABLE_B1_PASSWORD`

### Filename convention (recommended)
- `Last_First_YYYY-MM-DD.csv` or `First_Last_YYYY-MM-DD.csv`

### Minimum columns (case-insensitive, normalized internally)
- `pitch_type`
- `pitch_no` (or `pitch_number`)
- `pitch_speed_mph`
- `total_spin_rpm`
- `ivb_in` (induced vertical break)
- `hb_in` (horizontal break/movement)
- `extension_ft`
- `release_height_ft`
- `release_side_ft`
- `tilt_sec` (or `spin_axis`)
- `spin_efficiency_pct` (optional)

Other columns will be ignored safely. Unknown/filler players (e.g., Largaespada placeholder) should be skipped.
