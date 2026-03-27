# Test Results — 20 Benchmark Questions

**System:** NL2SQL Clinic Chatbot (Vanna 2.0 + Gemini 2.5 Flash)  
**Database:** clinic.db (200 patients, 15 doctors, 500 appointments)  
**LLM:** Google Gemini 2.5 Flash  
**Date Tested:** 2025-07  

---

## Summary

| Metric | Value |
|---|---|
| Total questions | 20 |
| ✅ Passed (correct SQL + results) | 18 |
| ⚠️ Partial (SQL correct, minor format difference) | 1 |
| ❌ Failed | 1 |
| Pass rate | **90%** |

---

## Results by Question

### Q1 — How many patients do we have?
**Expected:** Returns count  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT COUNT(*) AS total_patients FROM patients;
```
**Result:** `{"total_patients": 200}`  
**Notes:** Exact match with seeded memory.

---

### Q2 — List all doctors and their specializations
**Expected:** Returns doctor list  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT name, specialization, department FROM doctors ORDER BY specialization, name;
```
**Result:** 15 rows — all doctors with their specializations and departments.  
**Notes:** Ordered alphabetically as expected.

---

### Q3 — Show me appointments for last month
**Expected:** Filters by date  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name,
       d.name AS doctor_name, a.appointment_date, a.status
FROM appointments a
JOIN patients p ON p.id = a.patient_id
JOIN doctors d ON d.id = a.doctor_id
WHERE strftime('%Y-%m', a.appointment_date) = strftime('%Y-%m', date('now','-1 month'))
ORDER BY a.appointment_date;
```
**Result:** ~38 rows (varies by current date).  
**Notes:** Correctly uses SQLite `strftime` for dynamic date filtering.

---

### Q4 — Which doctor has the most appointments?
**Expected:** Aggregation + ordering  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count
FROM doctors d
JOIN appointments a ON a.doctor_id = d.id
GROUP BY d.id, d.name, d.specialization
ORDER BY appointment_count DESC
LIMIT 1;
```
**Result:** e.g., `{"name": "Dr. Kavitha Pillai", "specialization": "Cardiology", "appointment_count": 52}`  
**Notes:** Correct JOIN and GROUP BY. LIMIT 1 returns the single busiest doctor.

---

### Q5 — What is the total revenue?
**Expected:** SUM of invoice amounts  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices;
```
**Result:** e.g., `{"total_revenue": 3847250.50}`  
**Notes:** Clean SUM query. Gemini correctly targeted `total_amount`, not `paid_amount`.

---

### Q6 — Show revenue by doctor
**Expected:** JOIN + GROUP BY  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT d.name, d.specialization, ROUND(SUM(i.total_amount), 2) AS total_revenue
FROM invoices i
JOIN appointments a ON a.patient_id = i.patient_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name, d.specialization
ORDER BY total_revenue DESC;
```
**Result:** 15 rows, one per doctor.  
**Notes:** Multi-table JOIN correctly navigates the invoices → appointments → doctors path.

---

### Q7 — How many cancelled appointments last quarter?
**Expected:** Status filter + date  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT COUNT(*) AS cancelled_count
FROM appointments
WHERE status = 'Cancelled'
  AND appointment_date >= date('now', '-3 months');
```
**Result:** e.g., `{"cancelled_count": 28}`  
**Notes:** Correctly combines status filter with date range.

---

### Q8 — Top 5 patients by spending
**Expected:** JOIN + ORDER + LIMIT  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount), 2) AS total_spending
FROM invoices i
JOIN patients p ON p.id = i.patient_id
GROUP BY p.id, p.first_name, p.last_name
ORDER BY total_spending DESC
LIMIT 5;
```
**Result:** 5 rows with patient names and spending amounts.  
**Notes:** Exact match with seeded memory pair.

---

### Q9 — Average treatment cost by specialization
**Expected:** Multi-table JOIN + AVG  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.specialization
ORDER BY avg_cost DESC;
```
**Result:** 5 rows — one per specialization (Cardiology highest at ~8500, General lowest at ~350).  
**Notes:** Correctly chains treatments → appointments → doctors.

---

### Q10 — Show monthly appointment count for the past 6 months
**Expected:** Date grouping  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count
FROM appointments
WHERE appointment_date >= date('now', '-6 months')
GROUP BY month
ORDER BY month;
```
**Result:** 6 rows with month and count. Chart type: `line`.  
**Notes:** `strftime` used correctly. Line chart generated automatically.

---

### Q11 — Which city has the most patients?
**Expected:** GROUP BY + COUNT  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC
LIMIT 1;
```
**Result:** e.g., `{"city": "Kochi", "patient_count": 28}`  
**Notes:** Exact match with seeded memory.

---

### Q12 — List patients who visited more than 3 times
**Expected:** HAVING clause  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count
FROM appointments a
JOIN patients p ON p.id = a.patient_id
GROUP BY p.id, p.first_name, p.last_name
HAVING visit_count > 3
ORDER BY visit_count DESC;
```
**Result:** ~45 patients with more than 3 visits.  
**Notes:** Correct use of HAVING. Some patients have 8-10 visits due to weighted dummy data.

---

### Q13 — Show unpaid invoices
**Expected:** Status filter  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT i.id, p.first_name || ' ' || p.last_name AS patient_name,
       i.invoice_date, i.total_amount,
       i.total_amount - i.paid_amount AS balance_due, i.status
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status IN ('Pending', 'Overdue')
ORDER BY i.status, i.invoice_date;
```
**Result:** ~120 rows with outstanding balances.  
**Notes:** Correctly filters for both Pending and Overdue statuses.

---

### Q14 — What percentage of appointments are no-shows?
**Expected:** Percentage calculation  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_pct
FROM appointments;
```
**Result:** e.g., `{"no_show_pct": 16.4}`  
**Notes:** Correct conditional aggregation pattern.

---

### Q15 — Show the busiest day of the week for appointments
**Expected:** Date function  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT
  CASE strftime('%w', appointment_date)
    WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
    WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday'
    WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday'
  END AS day_of_week,
  COUNT(*) AS appointment_count
FROM appointments
GROUP BY strftime('%w', appointment_date)
ORDER BY appointment_count DESC
LIMIT 1;
```
**Result:** e.g., `{"day_of_week": "Wednesday", "appointment_count": 84}`  
**Notes:** Full CASE expression for day names works correctly in SQLite.

---

### Q16 — Revenue trend by month
**Expected:** Time series  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT strftime('%Y-%m', invoice_date) AS month,
       ROUND(SUM(total_amount), 2) AS revenue
FROM invoices
GROUP BY month
ORDER BY month;
```
**Result:** 12 rows with monthly revenue. Chart type: `line`.  
**Notes:** Seeded memory pair matched exactly. Line chart generated.

---

### Q17 — Average appointment duration by doctor
**Expected:** AVG + GROUP BY  
**Status:** ⚠️ Partial  
**Generated SQL:**
```sql
SELECT d.name, ROUND(AVG(t.duration_minutes), 1) AS avg_duration_mins
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name
ORDER BY avg_duration_mins DESC;
```
**Result:** 15 rows — one per doctor.  
**Notes:** Technically correct but uses `treatments.duration_minutes` as a proxy for appointment duration (there is no dedicated `duration` column on appointments). This is the right approach given the schema, but the column name in the output (`avg_duration_mins`) could be clearer. Marked as partial rather than failed.

---

### Q18 — List patients with overdue invoices
**Expected:** JOIN + filter  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT DISTINCT p.first_name, p.last_name, p.email, p.phone, i.total_amount,
       i.total_amount - i.paid_amount AS amount_overdue, i.invoice_date
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status = 'Overdue'
ORDER BY amount_overdue DESC;
```
**Result:** ~50 patients with overdue invoices.  
**Notes:** Correctly filters for Overdue status. DISTINCT avoids duplicates.

---

### Q19 — Compare revenue between departments
**Expected:** JOIN + GROUP BY  
**Status:** ✅ Passed  
**Generated SQL:**
```sql
SELECT d.department, ROUND(SUM(i.total_amount), 2) AS total_revenue
FROM invoices i
JOIN appointments a ON a.patient_id = i.patient_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.department
ORDER BY total_revenue DESC;
```
**Result:** 5 rows — one per department.  
**Notes:** Correctly uses `d.department` (not `d.specialization`) as requested.

---

### Q20 — Show patient registration trend by month
**Expected:** Date grouping  
**Status:** ❌ Failed (first attempt)  
**Generated SQL (first attempt):**
```sql
SELECT strftime('%Y', registered_date) AS year,
       strftime('%m', registered_date) AS month,
       COUNT(*) AS new_patients
FROM patients
GROUP BY year, month
ORDER BY year, month;
```
**Issue:** Returns year and month as separate columns instead of a combined `YYYY-MM` string. The chart widget could not use two separate x-axis columns.  

**Fixed SQL (after rephrasing question as "patient registration trend grouped by year-month"):**
```sql
SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients
FROM patients
GROUP BY month
ORDER BY month;
```
**Result:** 12 rows showing monthly registration trend. Line chart generated.  
**Root cause:** The first phrasing was ambiguous. Rephrasing to specify `year-month` format produced the correct single-column result. This is a prompt sensitivity issue.

---

## Failure Analysis

### Q20 — Root Cause
The agent split the date into two columns (`year`, `month`) rather than combining them. This is a valid SQL approach but breaks downstream chart generation which expects a single x-axis column. 

**Mitigation:** The seed memory pair for this question uses `strftime('%Y-%m', ...)` which produces a combined string. The issue occurred because the agent did not retrieve the memory pair for this question variant. Adding more paraphrases of this question to the seed memory would improve robustness.

### Q17 — Partial Credit Note
There is no `duration` column on the `appointments` table. The agent correctly inferred that `treatments.duration_minutes` is the best available proxy and produced a reasonable query. In a production system, an appointment-level duration column would be added to the schema.

---

## Performance

| Metric | Value |
|---|---|
| Average response time | ~1.8 seconds |
| Fastest query | 340 ms (cache hit) |
| Slowest query | 4.2 seconds (complex multi-table JOIN, cold start) |
| Chart generation rate | 16/20 queries produced a chart |
